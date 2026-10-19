import pytest
from test_main import client, create_user_get_token, auth_header, TestingSessionLocal, engine
from database import Base
import models
import os
import shutil

@pytest.fixture(autouse=True)
def setup_teardown():
    """Recreate all tables before each test and clean up after."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    os.makedirs("../uploads", exist_ok=True)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("../uploads"):
        shutil.rmtree("../uploads")
        os.makedirs("../uploads", exist_ok=True)

def test_traceability_relationships():
    sub_token = create_user_get_token("sub_trace", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub_token)).json()
    
    from gen_test_files import create_valid_pdf
    create_valid_pdf("dummy_trace1.pdf")
    with open("dummy_trace1.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(sub_token), files={"file": ("dummy_trace1.pdf", f, "application/pdf")})
    
    create_valid_pdf("dummy_trace2.pdf")
    with open("dummy_trace2.pdf", "rb") as f:
        client.post(f"/requests/{req['id']}/upload", headers=auth_header(sub_token), files={"file": ("dummy_trace1.pdf", f, "application/pdf")})
        
    client.post(f"/requests/{req['id']}/submit", headers=auth_header(sub_token))
    
    rev_token = create_user_get_token("rev_trace", "Reviewer")
    client.post(f"/requests/{req['id']}/process", headers=auth_header(rev_token))
    
    db = TestingSessionLocal()
    ext = db.query(models.ExtractedField).join(models.ExtractionRun).join(models.DocumentVersion).join(models.Document).filter(models.Document.request_id == req['id']).first()
    client.post(f"/requests/{req['id']}/correct_field?field_id={ext.id}&new_value=CorrectedValue", headers=auth_header(rev_token))
    
    client.post(f"/requests/{req['id']}/review", json={"action": "request_correction", "reason": "Trace comment"}, headers=auth_header(rev_token))
    
    db.refresh(ext)
    
    request_obj = db.query(models.Request).filter(models.Request.id == req['id']).first()
    assert request_obj.submitter_id is not None
    user = db.query(models.User).filter(models.User.id == request_obj.submitter_id).first()
    assert user.username == "sub_trace"
    
    docs = request_obj.documents
    assert len(docs) == 1
    doc = docs[0]
    
    assert len(doc.versions) == 2
    assert doc.current_version == 2
    
    v1 = next(v for v in doc.versions if v.version_number == 1)
    v2 = next(v for v in doc.versions if v.version_number == 2)
    assert v1.uploader_id == user.id
    assert v2.uploader_id == user.id
    
    runs = v2.extraction_runs
    assert len(runs) == 1
    assert len(runs[0].extractions) > 0
    
    verifs = db.query(models.VerificationCheck).filter(models.VerificationCheck.request_id == req['id']).all()
    assert any(v.document_version_id == v2.id for v in verifs)
    
    assert ext.corrected_value == "CorrectedValue"
    assert ext.corrected_by_user_id is not None
    assert ext.corrected_at is not None
    
    comments = db.query(models.Comment).filter(models.Comment.request_id == req['id']).all()
    assert len(comments) == 1
    assert comments[0].user_id is not None
    assert comments[0].timestamp is not None
    
    logs = db.query(models.AuditLog).filter(models.AuditLog.request_id == req['id']).all()
    assert any(log.action == "request_correction" and log.reason == "Trace comment" and log.actor_id is not None for log in logs)
    
    if os.path.exists("dummy_trace1.pdf"): os.remove("dummy_trace1.pdf")
    if os.path.exists("dummy_trace2.pdf"): os.remove("dummy_trace2.pdf")
    db.close()

def test_legacy_null_data():
    sub_token = create_user_get_token("sub_legacy", "Submitter")
    req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0}, headers=auth_header(sub_token)).json()
    
    db = TestingSessionLocal()
    doc = models.Document(request_id=req['id'], original_filename="legacy.pdf", file_type="application/pdf", current_version=1)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    v1 = models.DocumentVersion(document_id=doc.id, version_number=1, filepath="fake.pdf", processing_state="Pending", uploader_id=None)
    db.add(v1)
    db.commit()
    
    res = client.get(f"/requests/{req['id']}/details", headers=auth_header(sub_token))
    assert res.status_code == 200
    db.close()
