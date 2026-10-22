import pytest
import os

from fastapi.testclient import TestClient
from backend.main import app, run_verifications, get_db
from backend.database import Base
from backend import models
from tests.test_main import engine, TestingSessionLocal, create_user_get_token, auth_header
from gen_test_files import create_valid_pdf
from gen_test_files import create_valid_pdf

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    os.makedirs("../uploads", exist_ok=True)
    yield
    Base.metadata.drop_all(bind=engine)

def test_missing_required_field_and_document():
    token = create_user_get_token("sub", "Submitter")
    req = client.post("/requests/", json={"type": "Travel"}, headers=auth_header(token)).json()
    # No expense_amount, no docs
    # wait, process_request requires docs to be attached, else returns 400 immediately
    # Let's bypass submission logic and just run_verifications directly?
    # Actually, process_request creates the missing doc log before failing.
    pass # Wait, if process_request throws 400 when no docs, we can test it directly
    
def test_verifications_full():
    token = create_user_get_token("sub", "Submitter")
    req1 = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 150.0}, headers=auth_header(token)).json()
    create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req1['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    client.post(f"/requests/{req1['id']}/submit", headers=auth_header(token))
    
    rev_token = create_user_get_token("rev", "Reviewer")
    client.post(f"/requests/{req1['id']}/process", headers=auth_header(rev_token))
    
    db = TestingSessionLocal()
    checks = db.query(models.VerificationCheck).filter_by(request_id=req1['id']).all()
    # PASS required field
    assert any(c.rule_name == "Required Field" and c.result == "PASS" for c in checks)
    # PASS required doc
    assert any(c.rule_name == "Required Document" and c.result == "PASS" for c in checks)
    # PASS amount consistency
    assert any(c.rule_name == "Amount Consistency" and c.result == "PASS" for c in checks)
    db.close()
    
    # Test Amount Mismatch
    req2 = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 999.0}, headers=auth_header(token)).json()
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req2['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    client.post(f"/requests/{req2['id']}/submit", headers=auth_header(token))
    client.post(f"/requests/{req2['id']}/process", headers=auth_header(rev_token))
    
    db = TestingSessionLocal()
    checks2 = db.query(models.VerificationCheck).filter_by(request_id=req2['id']).all()
    assert any(c.rule_name == "Amount Consistency" and c.result == "INCONSISTENT" for c in checks2)
    
    # Test Duplicate Flag
    # req1 and req2 have the same merchant/date/amount extracted from dummy.pdf
    assert any(c.rule_name == "Possible Duplicate" and c.result == "WARNING" for c in checks2)
    db.close()

    # Test Corrected Value Being Used & Rerunning verification
    # For req2, reviewer corrects the extracted amount to 999.0 to match the form
    db = TestingSessionLocal()
    field = db.query(models.ExtractedField).join(models.ExtractionRun).join(models.DocumentVersion).join(models.Document).filter(
        models.Document.request_id == req2['id'], models.ExtractedField.field_name == "amount"
    ).first()
    field_id = field.id
    db.close()
    
    # Correct it
    client.post(f"/requests/{req2['id']}/correct_field?field_id={field_id}&new_value=999.0", headers=auth_header(rev_token))
    
    db = TestingSessionLocal()
    checks3 = db.query(models.VerificationCheck).filter_by(request_id=req2['id']).all()
    # Should now pass amount consistency
    assert any(c.rule_name == "Amount Consistency" and c.result == "PASS" for c in checks3)
    # Should no longer be a duplicate because amount changed
    assert not any(c.rule_name == "Possible Duplicate" for c in checks3)
    # Ensure no endless duplicates (only 1 Required Field check exists, not 2)
    assert len([c for c in checks3 if c.rule_name == "Required Field"]) == 1
    db.close()
    os.remove("dummy.pdf")
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from main import app, run_verifications
from database import Base
from main import get_db
import models
from tests.test_main import engine, TestingSessionLocal, create_user_get_token, auth_header
from gen_test_files import create_valid_pdf

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    os.makedirs("../uploads", exist_ok=True)
    yield
    Base.metadata.drop_all(bind=engine)
    
def test_missing_field_and_doc():
    token = create_user_get_token("sub", "Submitter")
    req = client.post("/requests/", json={"type": "Travel"}, headers=auth_header(token)).json()
    
    db = TestingSessionLocal()
    run_verifications(db, req['id'])
    
    checks = db.query(models.VerificationCheck).filter_by(request_id=req['id']).all()
    assert any(c.rule_name == "Required Field" and c.result == "CANNOT DETERMINE" and c.category == "missing" for c in checks)
    assert any(c.rule_name == "Required Document" and c.result == "CANNOT DETERMINE" and c.category == "missing" for c in checks)
    db.close()

def test_multiple_docs_and_versioning():
    token = create_user_get_token("sub", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "expense_amount": 150.0, "merchant_name": "Test", "expense_date": "2026-10-01"}, headers=auth_header(token)).json()
    create_valid_pdf("dummy.pdf")
    
    # upload doc1
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
        
    # upload doc2
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("doc2.pdf", f, "application/pdf")})
        
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    
    rev_token = create_user_get_token("rev", "Reviewer")
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    db = TestingSessionLocal()
    checks = db.query(models.VerificationCheck).filter_by(request_id=req['id']).all()
    assert any(c.rule_name == "Required Document" and "2 document(s)" in c.evidence for c in checks)
    db.close()
    os.remove("dummy.pdf")

def test_merchant_and_date_matching():
    token = create_user_get_token("sub", "Submitter")
    # Matching exactly
    req = client.post("/requests/", json={"type": "Travel", "expense_amount": 150.0, "merchant_name": "Test", "expense_date": "2026-10-01"}, headers=auth_header(token)).json()
    create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    
    rev_token = create_user_get_token("rev", "Reviewer")
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    db = TestingSessionLocal()
    checks = db.query(models.VerificationCheck).filter_by(request_id=req['id']).all()
    assert any(c.rule_name == "Merchant Consistency" and c.result == "PASS" for c in checks)
    assert any(c.rule_name == "Date Consistency" and c.result == "PASS" for c in checks)
    db.close()

def test_merchant_and_date_mismatch():
    token = create_user_get_token("sub", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "expense_amount": 150.0, "merchant_name": "Wrong Merchant Inc", "expense_date": "2025-01-01"}, headers=auth_header(token)).json()
    create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(token))
    
    rev_token = create_user_get_token("rev", "Reviewer")
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    db = TestingSessionLocal()
    checks = db.query(models.VerificationCheck).filter_by(request_id=req['id']).all()
    assert any(c.rule_name == "Merchant Consistency" and c.result == "INCONSISTENT" for c in checks)
    assert any(c.rule_name == "Date Consistency" and c.result == "INCONSISTENT" for c in checks)
    
    # Now let's test form edit causing re-verification!
    # Request is 'Under Review'. We can't edit it directly via PUT because PUT is for Draft/More Info.
    # So Reviewer sets it to More Information Required.
    client.post(f"/requests/{req['id']}/review", json={"reviewer_id": 0, "action": "request_correction", "reason": "Fix merchant"}, headers=auth_header(rev_token))
    
    # Submitter updates the form
    client.put(f"/requests/{req['id']}", json={"merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 150.0}, headers=auth_header(token))
    
    db.close()
    db = TestingSessionLocal()
    checks2 = db.query(models.VerificationCheck).filter_by(request_id=req['id']).all()
    # It should have re-verified and now PASS
    assert any(c.rule_name == "Merchant Consistency" and c.result == "PASS" for c in checks2)
    assert any(c.rule_name == "Date Consistency" and c.result == "PASS" for c in checks2)
    
    db.close()
    
def test_null_legacy_values():
    token = create_user_get_token("sub", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "expense_amount": 150.0}, headers=auth_header(token)).json()
    
    # We simulate a legacy request by manually setting fields to null in DB, since create_request might not null them?
    # Actually they are null by default if not passed (except I patched the test fixtures).
    # Since I patched the test fixtures, I'll manually set them to null.
    db = TestingSessionLocal()
    r = db.query(models.Request).filter_by(id=req['id']).first()
    r.merchant_name = None
    r.expense_date = None
    db.commit()
    
    create_valid_pdf("dummy.pdf")
    with open("dummy.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(token), files={"file": ("dummy.pdf", f, "application/pdf")})
        
    # We can't submit a legacy request via endpoint if it blocks null, but we can process it!
    # Force status to Submitted to test processing
    r.status = "Submitted"
    db.commit()
    db.close()
    
    rev_token = create_user_get_token("rev", "Reviewer")
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    db = TestingSessionLocal()
    checks = db.query(models.VerificationCheck).filter_by(request_id=req['id']).all()
    # They should not crash, and should not raise INCONSISTENT. (It should skip or say missing).
    # My run_verifications logic just does if req.merchant_name is not None:
    # So if it's None, it won't even create a Merchant Consistency check.
    assert not any(c.rule_name == "Merchant Consistency" for c in checks)
    assert not any(c.rule_name == "Date Consistency" for c in checks)
    db.close()
    os.remove("dummy.pdf")










