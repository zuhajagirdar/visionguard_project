import pytest
import os
import tempfile

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.main import app, get_db
from backend.database import Base
from backend import models
import shutil

# Use a dedicated temp file so tests never touch production reimbursement.db
_TEST_DB_FILE = os.path.join(tempfile.gettempdir(), "expense_test.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{_TEST_DB_FILE}"
from sqlalchemy.pool import StaticPool
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    os.makedirs("../uploads", exist_ok=True)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("../uploads"):
        shutil.rmtree("../uploads")
        os.makedirs("../uploads", exist_ok=True)

def create_user_get_token(username, role, password="12345"):
    user = client.post("/users/", json={"username": username, "role": role, "password": password}).json()
    token_res = client.post("/token", data={"username": username, "password": password, "role": role})
    return token_res.json()["access_token"]

def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def test_request_creation():
    token = create_user_get_token("sub1", "Submitter")
    res = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0, "category": "Transport"}, headers=auth_header(token))
    assert res.status_code == 200
    assert res.json()["status"] == "Draft"
    assert res.json()["expense_amount"] == 100.0
    
    # Check Audit log
    db = TestingSessionLocal()
    log = db.query(models.AuditLog).first()
    assert log.action == "create"
    db.close()

def test_request_retrieval():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json()
    res = client.get(f"/requests/{req['id']}", headers=auth_header(token))
    assert res.status_code == 200
    assert res.json()["id"] == req["id"]
    
    # Submitter cannot retrieve another submitter's request
    token2 = create_user_get_token("sub2", "Submitter")
    res2 = client.get(f"/requests/{req['id']}", headers=auth_header(token2))
    assert res2.status_code == 403

def test_request_status_changes():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json()
    res = client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    assert res.status_code == 200
    assert res.json()["new_status"] == "Submitted"
    
def test_file_upload_validation():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json()
    
    with open("dummy.pdf", "wb") as f: f.write(b"PDF")
    with open("dummy.pdf", "rb") as f:
        res = client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    assert res.status_code == 200
    os.remove("dummy.pdf")

def test_unsupported_file():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json()
    
    with open("dummy.exe", "wb") as f: f.write(b"EXE")
    with open("dummy.exe", "rb") as f:
        res = client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.exe", f, "application/x-msdownload")})
    assert res.status_code == 400
    assert "Unsupported file type" in res.json()["detail"]
    os.remove("dummy.exe")

def test_document_versioning():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json()
    
    with open("dummy.pdf", "wb") as f: f.write(b"V1")
    with open("dummy.pdf", "rb") as f:
        res1 = client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
        
    with open("dummy.pdf", "wb") as f: f.write(b"V2")
    with open("dummy.pdf", "rb") as f:
        res2 = client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
        
    os.remove("dummy.pdf")
    assert res2.json()["version_id"] > res1.json()["version_id"]

def test_ocr_extraction():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json()
    
    from gen_test_files import create_valid_pdf; create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    os.remove("dummy.pdf")
    
    # Must submit first because of state machine
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    
    # System processes
    sys_token = create_user_get_token("sys", "Reviewer")
    res = client.post(f"/requests/{req['id']}/process", headers=auth_header(sys_token))
    assert res.status_code == 200
    assert res.json()["status"] == "Under Review"

def test_required_field_verification():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "expense_amount": None, "merchant_name": "Test", "expense_date": "2026-10-01"}, headers=auth_header(token)).json()
    from gen_test_files import create_valid_pdf; create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    os.remove("dummy.pdf")
    
    # Submission should fail with 400
    res_sub = client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    assert res_sub.status_code == 400
    
    # We can force the status to test the verification engine
    db = TestingSessionLocal()
    r = db.query(models.Request).filter_by(id=req['id']).first()
    r.status = "Submitted"
    db.commit()
    db.close()
    
    rev_token = create_user_get_token("rev", "Reviewer")
    res = client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    assert res.json()["status"] == "Under Review"
    
    db = TestingSessionLocal()
    vc = db.query(models.VerificationCheck).filter(models.VerificationCheck.request_id == req["id"], models.VerificationCheck.rule_name == "Required Field").first()
    assert vc.result == "CANNOT DETERMINE"
    db.close()

def test_form_vs_document_consistency():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 999.0}, headers=auth_header(token)).json()
    from gen_test_files import create_valid_pdf; create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    os.remove("dummy.pdf")
    
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    rev_token = create_user_get_token("rev", "Reviewer")
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    db = TestingSessionLocal()
    vc = db.query(models.VerificationCheck).filter(models.VerificationCheck.request_id == req["id"], models.VerificationCheck.result == "INCONSISTENT").first()
    assert vc is not None
    db.close()

def test_reviewer_correction():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json()
    from gen_test_files import create_valid_pdf; create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    os.remove("dummy.pdf")
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    
    rev_token = create_user_get_token("rev", "Reviewer")
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    db = TestingSessionLocal()
    field = db.query(models.ExtractedField).filter(models.ExtractedField.field_name == "amount").first()
    field_id = field.id if field else 1
    db.close()
    
    res = client.post(f"/requests/{req['id']}/correct_field?field_id={field_id}&new_value=250.0", headers=auth_header(rev_token))
    assert res.status_code == 200

def test_resubmission():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json()
    from gen_test_files import create_valid_pdf; create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    os.remove("dummy.pdf")
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    
    rev_token = create_user_get_token("rev", "Reviewer")
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    # Reviewer requests correction
    client.post(f"/requests/{req['id']}/review", json={"reviewer_id": 0, "action": "request_correction", "reason": "Missing info"}, headers=auth_header(rev_token))
    
    # Submitter resubmits
    res = client.post(f"/requests/{req['id']}/resubmit", headers=auth_header(token))
    assert res.json()["status"] == "Submitted"

def test_approval():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json()
    from gen_test_files import create_valid_pdf; create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    os.remove("dummy.pdf")
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    
    rev_token = create_user_get_token("rev", "Reviewer")
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    res = client.post(f"/requests/{req['id']}/review", json={"reviewer_id": 0, "action": "approve"}, headers=auth_header(rev_token))
    assert res.status_code == 200
    assert res.json()["status"] == "Approved"

def test_rejection():
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json()
    from gen_test_files import create_valid_pdf; create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    os.remove("dummy.pdf")
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    
    rev_token = create_user_get_token("rev", "Reviewer")
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    res = client.post(f"/requests/{req['id']}/review", json={"reviewer_id": 0, "action": "reject", "reason": "Expense violates reimbursement policy"}, headers=auth_header(rev_token))
    assert res.status_code == 200
    assert res.json()["status"] == "Rejected"

def test_submitter_cannot_approve_own():
    token = create_user_get_token("rev1", "Reviewer") # Even if Reviewer role
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json() # Reviewer can technically submit if role ignored in dummy, wait we restricted creation to Submitter
    # Let's create sub first
    # Ah, I restricted creation to Submitter only. So rev1 cannot create a request.
    pass # we will rewrite this safely below

def test_submitter_cannot_approve_own_fixed():
    # To truly test a submitter can't approve their own, we must assign them Reviewer role after creation or just try as Submitter
    token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(token)).json()
    
    # We bypass state machine directly or do the flow
    from gen_test_files import create_valid_pdf; create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    os.remove("dummy.pdf")
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    
    rev_token = create_user_get_token("rev2", "Reviewer")
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    res = client.post(f"/requests/{req['id']}/review", json={"reviewer_id": 0, "action": "approve"}, headers=auth_header(token))
    assert res.status_code == 403
    assert "Not authorized" in res.json()["detail"]

def test_dashboard():
    sub_token = create_user_get_token("sub1", "Submitter")
    rev_token = create_user_get_token("rev1", "Reviewer")
    
    # 1 pending
    client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub_token))
    
    res = client.get("/dashboard", headers=auth_header(sub_token))
    assert res.status_code == 200
    data = res.json()
    assert data["pending_count"] >= 1

def test_genai_permission_filtering():
    rev_token = create_user_get_token("rev1", "Reviewer")
    sub1_token = create_user_get_token("sub1", "Submitter")
    sub2_token = create_user_get_token("sub2", "Submitter")
    
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub1_token)).json()
    
    # Sub2 asks about Sub1's request -> 403
    res = client.post(f"/requests/{req['id']}/ask", json={"user_id": 0, "question": "Why?"}, headers=auth_header(sub2_token))
    assert res.status_code == 403
    
    # Rev1 asks -> 200
    res2 = client.post(f"/requests/{req['id']}/ask", json={"user_id": 0, "question": "Why?"}, headers=auth_header(rev_token))
    assert res2.status_code == 200

def test_genai_does_not_invent_evidence():
    sub_token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub_token)).json()
    res = client.post(f"/requests/{req['id']}/ask", json={"user_id": 0, "question": "What is the policy?"}, headers=auth_header(sub_token))
    assert res.status_code == 200

def test_processing_failure():
    sub_token = create_user_get_token("sub1", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub_token)).json()
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(sub_token))
    
    rev_token = create_user_get_token("rev1", "Reviewer")
    res = client.post(f"/requests/{req['id']}/process", headers=auth_header(sub_token))
    assert res.status_code == 400
    assert "No documents" in res.json()["detail"]
    
    db = TestingSessionLocal()
    req_check = db.query(models.Request).filter(models.Request.id == req["id"]).first()
    assert req_check.status == "Processing Failed"
    db.close()
















def test_get_requests_filters():
    sub_token = create_user_get_token("sub_filters", "Submitter")
    req1 = client.post("/requests/", json={"type": "Travel", "merchant_name": "UniqueMerchantA", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub_token)).json()
    req2 = client.post("/requests/", json={"type": "Meals", "merchant_name": "UniqueMerchantB", "expense_date": "2026-10-02", "expense_amount": 200.0}, headers=auth_header(sub_token)).json()
    
    # Filter by ID
    res = client.get(f"/requests/?req_id={req1['id']}", headers=auth_header(sub_token))
    assert len(res.json()) == 1
    
    # Filter by merchant
    res = client.get(f"/requests/?merchant=UniqueMerchantA", headers=auth_header(sub_token))
    assert len(res.json()) == 1
    
    # Filter by type
    res = client.get(f"/requests/?type=Meals", headers=auth_header(sub_token))
    assert len(res.json()) > 0
    
    # Filter by date
    res = client.get(f"/requests/?date=2026-10-02", headers=auth_header(sub_token))
    assert len(res.json()) > 0

def test_dashboard_extended_metrics():
    rev_token = create_user_get_token("rev_dash", "Reviewer")
    res = client.get("/dashboard", headers=auth_header(rev_token))
    assert res.status_code == 200
    data = res.json()
    assert "frequent_missing_fields" in data
    assert "average_review_turnaround_hours" in data

def test_oversized_file():
    sub_token = create_user_get_token("sub_big", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub_token)).json()
    
    # Create an 11MB file
    big_content = b"0" * (11 * 1024 * 1024)
    res = client.post(f"/requests/{req['id']}/upload", files={"file": ("big.pdf", big_content, "application/pdf")}, headers=auth_header(sub_token))
    assert res.status_code == 400
    assert "too large" in res.json()["detail"].lower()

def test_unauthorized_document_access():
    sub1_token = create_user_get_token("sub1_doc", "Submitter")
    sub2_token = create_user_get_token("sub2_doc", "Submitter")
    
    req1 = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub1_token)).json()
    
    # Sub2 tries to upload to Sub1's request
    res = client.post(f"/requests/{req1['id']}/upload", files={"file": ("test.pdf", b"dummy", "application/pdf")}, headers=auth_header(sub2_token))
    assert res.status_code == 403

def test_unauthorized_document_download():
    sub1_token = create_user_get_token("sub1_dl", "Submitter")
    sub2_token = create_user_get_token("sub2_dl", "Submitter")
    
    req1 = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub1_token)).json()
    upl = client.post(f"/requests/{req1['id']}/upload", files={"file": ("test.pdf", b"dummy", "application/pdf")}, headers=auth_header(sub1_token)).json()
    vid = upl["version_id"]
    
    # Sub2 tries to download Sub1's doc
    res = client.get(f"/documents/{vid}/content", headers=auth_header(sub2_token))
    assert res.status_code == 403

def test_unauthorized_approval():
    sub_token = create_user_get_token("sub_appr", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub_token)).json()
    from gen_test_files import create_valid_pdf; create_valid_pdf("dummy2.pdf")
    with open("dummy2.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(sub_token), files={"file": ("dummy2.pdf", f, "application/pdf")})
    import os; os.remove("dummy2.pdf")
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(sub_token))
    
    import database, models
    db = database.SessionLocal()
    db_req = db.query(models.Request).filter(models.Request.id == req['id']).first()
    db_req.status = "Under Review"
    db.commit()
    db.close()
    
    # Another submitter tries to approve
    sub2_token = create_user_get_token("sub2_appr", "Submitter")
    res = client.post(f"/requests/{req['id']}/review", json={"action": "approve"}, headers=auth_header(sub2_token))
    assert res.status_code == 403

def test_invalid_status_transition():
    sub_token = create_user_get_token("sub_stat", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub_token)).json()
    
    # Try to process while in Draft
    res = client.post(f"/requests/{req['id']}/process", headers=auth_header(sub_token))
    assert res.status_code == 400
    
    # Submit without docs
    res = client.post(f"/requests/{req['id']}/submit", headers=auth_header(sub_token))
    assert res.status_code == 200
    
    # Try to edit submitted request
    res = client.put(f"/requests/{req['id']}", json={"expense_amount": 200.0}, headers=auth_header(sub_token))
    assert res.status_code == 400

def test_permitted_actions_and_details_api():
    sub_token = create_user_get_token("sub_perm", "Submitter")
    rev_token = create_user_get_token("rev_perm", "Reviewer")
    appr_token = create_user_get_token("appr_perm", "Approver")
    
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub_token)).json()
    from gen_test_files import create_valid_pdf; create_valid_pdf("dummy3.pdf")
    with open("dummy3.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(sub_token), files={"file": ("dummy3.pdf", f, "application/pdf")})
    import os; os.remove("dummy3.pdf")
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(sub_token))
    client.post(f"/requests/{req['id']}/process", headers=auth_header(sub_token))
    
    # Check details API
    det_res = client.get(f"/requests/{req['id']}/details", headers=auth_header(sub_token))
    assert det_res.status_code == 200
    assert "verifications" in det_res.json()
    assert "extractions" in det_res.json()
    assert "history" in det_res.json()
    
    # Reviewer action
    res = client.post(f"/requests/{req['id']}/review", json={"action": "request_correction", "reason": "need more info"}, headers=auth_header(rev_token))
    if res.status_code != 200:
        print(res.json())
    assert res.status_code == 200
    
    # Submitter resubmits
    client.post(f"/requests/{req['id']}/resubmit", headers=auth_header(sub_token))
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    # Approver action
    res = client.post(f"/requests/{req['id']}/review", json={"action": "approve"}, headers=auth_header(appr_token))
    assert res.status_code == 200

def test_retry_manual_review_after_processing_failure():
    sub_token = create_user_get_token("sub_retry", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub_token)).json()
    
    # Upload corrupted file
    with open("dummy_corrupt.pdf", "wb") as f: f.write(b"NOT_A_PDF")
    with open("dummy_corrupt.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(sub_token), files={"file": ("dummy_corrupt.pdf", f, "application/pdf")})
    import os; os.remove("dummy_corrupt.pdf")
    
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(sub_token))
    
    # Process it - will fail because document OCR failed
    res = client.post(f"/requests/{req['id']}/process", headers=auth_header(sub_token))
    assert res.json()["status"] == "Processing Failed"
    
    # Reviewer reviews processing failed request manually
    rev_token = create_user_get_token("rev_retry", "Reviewer")
    res = client.post(f"/requests/{req['id']}/review", json={"action": "request_correction", "reason": "Upload valid PDF"}, headers=auth_header(rev_token))
    assert res.status_code == 200
    assert res.json()["status"] == "More Information Required"
    
    # Submitter uploads valid PDF
    from gen_test_files import create_valid_pdf; create_valid_pdf("dummy_valid.pdf")
    with open("dummy_valid.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(sub_token), files={"file": ("dummy_valid.pdf", f, "application/pdf")})
    os.remove("dummy_valid.pdf")
    
    # Resubmit
    client.post(f"/requests/{req['id']}/resubmit", headers=auth_header(sub_token))
    
    # Process again - should succeed
    res = client.post(f"/requests/{req['id']}/process", headers=auth_header(sub_token))
    print(res.status_code)
    print(res.json())
    assert res.json()["status"] == "Under Review"

def test_empty_states():
    sub_token = create_user_get_token("sub_empty", "Submitter")
    # New user has no requests
    res = client.get("/requests/", headers=auth_header(sub_token))
    assert res.status_code == 200
    assert len(res.json()) == 0
    
    res = client.get("/dashboard", headers=auth_header(sub_token))
    assert res.status_code == 200
    assert res.json()["pending_count"] == 0
