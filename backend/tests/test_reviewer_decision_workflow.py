import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import Base
from backend import models, gen_test_files
from backend.tests.test_main import engine, TestingSessionLocal, create_user_get_token, auth_header

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    os.makedirs("../uploads", exist_ok=True)
    yield
    Base.metadata.drop_all(bind=engine)
    for p in ["test_review_receipt.pdf"]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


def helper_create_and_submit_request(submitter_token, reviewer_token, merchant="Corner Cafe", date="2026-09-18", amount=150.0):
    """Helper to create a request with valid PDF, submit it, and process it to 'Under Review'."""
    sub_header = auth_header(submitter_token)
    rev_header = auth_header(reviewer_token)

    req = client.post(
        "/requests/",
        json={"type": "Meals", "merchant_name": merchant, "expense_date": date, "expense_amount": amount},
        headers=sub_header
    ).json()
    req_id = req["id"]

    pdf_file = "test_review_receipt.pdf"
    gen_test_files.create_valid_pdf(pdf_file, merchant=merchant, date=date, total=f"{amount:.2f}")
    with open(pdf_file, "rb") as f:
        client.post(
            f"/requests/{req_id}/upload",
            files={"file": ("receipt.pdf", f, "application/pdf")},
            headers=sub_header
        )

    # Submit and process
    client.post(f"/requests/{req_id}/submit", headers=sub_header)
    client.post(f"/requests/{req_id}/process", headers=rev_header)
    return req_id


def test_reviewer_approval_with_comments():
    sub_token = create_user_get_token("sub_appr", "Submitter")
    rev_token = create_user_get_token("rev_appr", "Reviewer")
    req_id = helper_create_and_submit_request(sub_token, rev_token)

    # Reviewer approves with optional comments
    comment_text = "Receipt matches policy and all automated verification checks passed."
    res = client.post(
        f"/requests/{req_id}/review",
        json={"action": "approve", "reason": comment_text},
        headers=auth_header(rev_token)
    )
    assert res.status_code == 200
    assert res.json()["status"] == "Approved"

    # Verify database persistence
    details = client.get(f"/requests/{req_id}/details", headers=auth_header(sub_token)).json()
    assert details["request"]["status"] == "Approved"

    # Verify audit log
    history = details.get("history", [])
    approve_entry = next((h for h in history if h["action"] == "approve"), None)
    assert approve_entry is not None
    assert approve_entry["from_status"] == "Under Review"
    assert approve_entry["to_status"] == "Approved"
    assert approve_entry["reason"] == comment_text

    # Verify comments thread
    comments = details.get("comments", [])
    assert any("[Approved]" in c["text"] and comment_text in c["text"] for c in comments)


def test_reviewer_rejection_requires_reason():
    sub_token = create_user_get_token("sub_rej", "Submitter")
    rev_token = create_user_get_token("rev_rej", "Reviewer")
    req_id = helper_create_and_submit_request(sub_token, rev_token)

    # Rejection without reason must fail with 400
    fail_res = client.post(
        f"/requests/{req_id}/review",
        json={"action": "reject", "reason": "   "},
        headers=auth_header(rev_token)
    )
    assert fail_res.status_code == 400
    assert "reason or explanation is required" in fail_res.json()["detail"].lower()

    # Rejection with valid reason must succeed
    rej_reason = "Expense not pre-approved per travel expense policy."
    ok_res = client.post(
        f"/requests/{req_id}/review",
        json={"action": "reject", "reason": rej_reason},
        headers=auth_header(rev_token)
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["status"] == "Rejected"

    # Verify audit log and comments
    details = client.get(f"/requests/{req_id}/details", headers=auth_header(sub_token)).json()
    assert details["request"]["status"] == "Rejected"
    history = details.get("history", [])
    rej_entry = next((h for h in history if h["action"] == "reject"), None)
    assert rej_entry is not None
    assert rej_entry["reason"] == rej_reason


def test_reviewer_request_more_information_requires_explanation():
    sub_token = create_user_get_token("sub_corr", "Submitter")
    rev_token = create_user_get_token("rev_corr", "Reviewer")
    req_id = helper_create_and_submit_request(sub_token, rev_token)

    # Request more info without explanation must fail with 400
    fail_res = client.post(
        f"/requests/{req_id}/review",
        json={"action": "request_correction", "reason": ""},
        headers=auth_header(rev_token)
    )
    assert fail_res.status_code == 400
    assert "reason or explanation is required" in fail_res.json()["detail"].lower()

    # Request more info with explanation succeeds and transitions to 'More Information Required'
    corr_reason = "The uploaded receipt is blurred. Please provide an itemized receipt with tax breakdown."
    ok_res = client.post(
        f"/requests/{req_id}/review",
        json={"action": "request_correction", "reason": corr_reason},
        headers=auth_header(rev_token)
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["status"] == "More Information Required"

    details = client.get(f"/requests/{req_id}/details", headers=auth_header(sub_token)).json()
    assert details["request"]["status"] == "More Information Required"

    # Submitter can now edit and resubmit
    resub_res = client.post(
        f"/requests/{req_id}/resubmit",
        json={"merchant_name": "Corner Cafe", "expense_date": "2026-09-18", "expense_amount": 150.0, "description": "Resubmitting with clarified details"},
        headers=auth_header(sub_token)
    )
    assert resub_res.status_code == 200
    assert resub_res.json()["new_status"] == "Submitted"


def test_unauthorized_user_cannot_make_decision():
    sub_token = create_user_get_token("sub_unauth", "Submitter")
    rev_token = create_user_get_token("rev_auth", "Reviewer")
    req_id = helper_create_and_submit_request(sub_token, rev_token)

    # Submitter attempting to approve their own request must return 403
    sub_decision = client.post(
        f"/requests/{req_id}/review",
        json={"action": "approve", "reason": "Self-approval"},
        headers=auth_header(sub_token)
    )
    assert sub_decision.status_code == 403


def test_invalid_status_transition_and_duplicate_decision():
    sub_token = create_user_get_token("sub_trans", "Submitter")
    rev_token = create_user_get_token("rev_trans", "Reviewer")
    req_id = helper_create_and_submit_request(sub_token, rev_token)

    # First approval
    first_appr = client.post(
        f"/requests/{req_id}/review",
        json={"action": "approve", "reason": "Approved once"},
        headers=auth_header(rev_token)
    )
    assert first_appr.status_code == 200

    # Attempting second decision on already Approved claim must fail with 400
    dup_decision = client.post(
        f"/requests/{req_id}/review",
        json={"action": "reject", "reason": "Trying to reject after approval"},
        headers=auth_header(rev_token)
    )
    assert dup_decision.status_code == 400
    assert "cannot review request in status approved" in dup_decision.json()["detail"].lower()

    # Attempting to review a Draft request must fail with 400
    draft_req = client.post("/requests/", json={"type": "Meals"}, headers=auth_header(sub_token)).json()
    draft_review = client.post(
        f"/requests/{draft_req['id']}/review",
        json={"action": "approve"},
        headers=auth_header(rev_token)
    )
    assert draft_review.status_code == 400
    assert "cannot review request in status draft" in draft_review.json()["detail"].lower()


def test_approver_role_workflow():
    sub_token = create_user_get_token("sub_appr_role", "Submitter")
    rev_token = create_user_get_token("rev_proc", "Reviewer")
    appr_token = create_user_get_token("chief_approver", "Approver")

    req_id = helper_create_and_submit_request(sub_token, rev_token)

    # User with role 'Approver' can review and approve
    appr_res = client.post(
        f"/requests/{req_id}/review",
        json={"action": "approve", "reason": "Executive sign-off"},
        headers=auth_header(appr_token)
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "Approved"
