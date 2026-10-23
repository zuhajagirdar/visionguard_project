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
    for p in ["test_submission_receipt.pdf"]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


def test_claim_submission_flow_and_validation():
    # Setup users
    sub_token = create_user_get_token("submitter_bob", "Submitter")
    rev_token = create_user_get_token("reviewer_rob", "Reviewer")
    sub_header = auth_header(sub_token)
    rev_header = auth_header(rev_token)

    # Generate a realistic test receipt
    pdf_path = "test_submission_receipt.pdf"
    gen_test_files.create_valid_pdf(pdf_path, merchant="CORNER CAFE", date="2026-09-18", total="380.00")

    # Step 1: Create a draft request with empty claim details
    create_res = client.post(
        "/requests/",
        json={"type": "Meals", "description": "Team lunch at Corner Cafe"},
        headers=sub_header
    )
    assert create_res.status_code == 200
    req_id = create_res.json()["id"]

    # Step 2: Upload receipt - automatic OCR triggers
    with open(pdf_path, "rb") as f:
        upload_res = client.post(
            f"/requests/{req_id}/upload",
            files={"file": ("sample-receipt.pdf", f, "application/pdf")},
            headers=sub_header
        )
    assert upload_res.status_code == 200

    # Step 3: Verify requirement 1 - A draft with empty claim fields cannot be submitted
    submit_fail = client.post(f"/requests/{req_id}/submit", headers=sub_header)
    assert submit_fail.status_code == 400
    assert "Must provide expense_amount, merchant_name, and expense_date to submit" in submit_fail.json()["detail"]
    assert "merchant_name" in submit_fail.json()["detail"]
    assert "expense_date" in submit_fail.json()["detail"]
    assert "expense_amount" in submit_fail.json()["detail"]

    # Check details endpoint reports missing claim fields
    details_before = client.get(f"/requests/{req_id}/details", headers=sub_header).json()
    missing_locs = [m["field"] for m in details_before.get("missing_fields", []) if m["location"] == "claim"]
    assert "merchant_name" in missing_locs
    assert "expense_date" in missing_locs
    assert "expense_amount" in missing_locs

    # Document readability must be PASS, not marked unreadable
    v_checks = details_before.get("verifications", [])
    readability = next((v for v in v_checks if v["rule_name"] == "Document Readability"), None)
    assert readability is not None
    assert readability["result"] == "PASS"

    # Step 4: Verify requirement 5 - Invalid dates, empty merchant names, and invalid amounts remain rejected
    # 5a. Empty/whitespace merchant name rejected
    res_empty_merchant = client.put(
        f"/requests/{req_id}",
        json={"merchant_name": "   ", "expense_date": "2026-09-18", "expense_amount": 380.00},
        headers=sub_header
    )
    assert res_empty_merchant.status_code == 422

    # 5b. Invalid date rejected
    res_invalid_date = client.put(
        f"/requests/{req_id}",
        json={"merchant_name": "CORNER CAFE", "expense_date": "invalid-date-string", "expense_amount": 380.00},
        headers=sub_header
    )
    assert res_invalid_date.status_code == 422

    # 5c. Invalid amount (<= 0) rejected
    res_invalid_amount = client.put(
        f"/requests/{req_id}",
        json={"merchant_name": "CORNER CAFE", "expense_date": "2026-09-18", "expense_amount": -10.00},
        headers=sub_header
    )
    assert res_invalid_amount.status_code == 422

    res_zero_amount = client.put(
        f"/requests/{req_id}",
        json={"merchant_name": "CORNER CAFE", "expense_date": "2026-09-18", "expense_amount": 0},
        headers=sub_header
    )
    assert res_zero_amount.status_code == 422

    # Step 5: Verify requirement 2 - Saving CORNER CAFE, 2026-09-18, and 380.00 persists all three values
    put_valid = client.put(
        f"/requests/{req_id}",
        json={"merchant_name": "CORNER CAFE", "expense_date": "2026-09-18", "expense_amount": 380.00},
        headers=sub_header
    )
    assert put_valid.status_code == 200
    saved_req = put_valid.json()
    assert saved_req["merchant_name"] == "CORNER CAFE"
    assert saved_req["expense_date"] == "2026-09-18"
    assert saved_req["expense_amount"] == 380.00

    # Step 6: Verify requirement 3 - Verification no longer reports these fields missing after a successful save
    details_after_save = client.get(f"/requests/{req_id}/details", headers=sub_header).json()
    missing_after = details_after_save.get("missing_fields", [])
    assert len(missing_after) == 0

    v_after = details_after_save.get("verifications", [])
    req_field_check = next((v for v in v_after if v["rule_name"] == "Required Field"), None)
    assert req_field_check is not None
    assert req_field_check["result"] == "PASS"

    amt_check = next((v for v in v_after if v["rule_name"] == "Amount Consistency"), None)
    assert amt_check is not None
    assert amt_check["result"] == "PASS"

    date_check = next((v for v in v_after if v["rule_name"] == "Date Consistency"), None)
    assert date_check is not None
    assert date_check["result"] == "PASS"

    merch_check = next((v for v in v_after if v["rule_name"] == "Merchant Consistency"), None)
    assert merch_check is not None
    assert merch_check["result"] == "PASS"

    # Step 7: Verify requirement 4 - Submitting works without requiring manual page refresh
    # Submit the saved request
    submit_res = client.post(f"/requests/{req_id}/submit", headers=sub_header)
    assert submit_res.status_code == 200
    assert submit_res.json()["new_status"] == "Submitted"

    # Verify audit trail records the submission
    details_submitted = client.get(f"/requests/{req_id}/details", headers=sub_header).json()
    assert details_submitted["request"]["status"] == "Submitted"
    actions = [h["action"] for h in details_submitted.get("history", [])]
    assert "submit" in actions

    # Step 8: Test submitting directly with payload on a new draft (immediate submit after filling form)
    req2 = client.post(
        "/requests/",
        json={"type": "Meals"},
        headers=sub_header
    ).json()
    req2_id = req2["id"]

    # Upload duplicate receipt to req2
    with open(pdf_path, "rb") as f:
        client.post(
            f"/requests/{req2_id}/upload",
            files={"file": ("sample-receipt.pdf", f, "application/pdf")},
            headers=sub_header
        )

    submit_with_payload = client.post(
        f"/requests/{req2_id}/submit",
        json={"merchant_name": "CORNER CAFE", "expense_date": "2026-09-18", "expense_amount": 380.00},
        headers=sub_header
    )
    assert submit_with_payload.status_code == 200
    assert submit_with_payload.json()["new_status"] == "Submitted"

    details_req2 = client.get(f"/requests/{req2_id}/details", headers=sub_header).json()
    assert details_req2["request"]["status"] == "Submitted"
    assert details_req2["request"]["merchant_name"] == "CORNER CAFE"
    assert details_req2["request"]["expense_date"] == "2026-09-18"
    assert details_req2["request"]["expense_amount"] == 380.00

    # Step 9: Verify duplicate detection still works
    # Both req_id and req2_id have same amount (380.00), date (2026-09-18), and merchant (CORNER CAFE)
    # The duplicate rule compares against existing requests in DB
    dup_check = next((v for v in details_req2.get("verifications", []) if v["rule_name"] == "Possible Duplicate"), None)
    assert dup_check is not None
    assert dup_check["result"] == "WARNING"

    # Step 10: Verify reviewer workflow and correction/resubmission
    # First, process the submitted request to transition to 'Under Review'
    proc_res = client.post(f"/requests/{req_id}/process", headers=rev_header)
    assert proc_res.status_code == 200
    assert proc_res.json()["status"] == "Under Review"

    # Reviewer requests correction
    rev_corr = client.post(
        f"/requests/{req_id}/review",
        json={"reviewer_id": 0, "action": "request_correction", "reason": "Please provide project code"},
        headers=rev_header
    )
    assert rev_corr.status_code == 200

    details_corr = client.get(f"/requests/{req_id}/details", headers=sub_header).json()
    assert details_corr["request"]["status"] == "More Information Required"

    # Resubmit with updated description/payload
    resub_res = client.post(
        f"/requests/{req_id}/resubmit",
        json={"merchant_name": "CORNER CAFE", "expense_date": "2026-09-18", "expense_amount": 380.00, "description": "Project Alpha lunch"},
        headers=sub_header
    )
    assert resub_res.status_code == 200
    assert resub_res.json()["new_status"] == "Submitted"

    # Process again after resubmission
    proc_res2 = client.post(f"/requests/{req_id}/process", headers=rev_header)
    assert proc_res2.status_code == 200
    assert proc_res2.json()["status"] == "Under Review"

    # Reviewer approves
    rev_app = client.post(
        f"/requests/{req_id}/review",
        json={"reviewer_id": 0, "action": "approve"},
        headers=rev_header
    )
    assert rev_app.status_code == 200
    details_app = client.get(f"/requests/{req_id}/details", headers=sub_header).json()
    assert details_app["request"]["status"] == "Approved"
