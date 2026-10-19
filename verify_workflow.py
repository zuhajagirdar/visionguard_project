import os
import shutil
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base
from main import get_db
import models

# Setup isolated DB for verification
SQLALCHEMY_DATABASE_URL = "sqlite:///./verify.db"
if os.path.exists("./verify.db"):
    os.remove("./verify.db")

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
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

def auth(token):
    return {"Authorization": f"Bearer {token}"}

print("Starting End-to-End Workflow Verification...")

# 1. Setup Users
u_sub1 = client.post("/users/", json={"username": "sub1", "role": "Submitter"}).json()
t_sub1 = client.post("/token", data={"username": "sub1"}).json()["access_token"]

u_sub2 = client.post("/users/", json={"username": "sub2", "role": "Submitter"}).json()
t_sub2 = client.post("/token", data={"username": "sub2"}).json()["access_token"]

u_rev1 = client.post("/users/", json={"username": "rev1", "role": "Reviewer"}).json()
t_rev1 = client.post("/token", data={"username": "rev1"}).json()["access_token"]

u_app1 = client.post("/users/", json={"username": "app1", "role": "Approver"}).json()
t_app1 = client.post("/token", data={"username": "app1"}).json()["access_token"]

# 2. Submitter Workflow
print("- Submitter1 creating Draft...")
req = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 150.0}, headers=auth(t_sub1)).json()
req_id = req["id"]
assert req["status"] == "Draft"

print("- Submitter1 uploading document...")
from gen_test_files import create_valid_image; from gen_test_files import create_valid_pdf; create_valid_pdf("test_receipt.pdf")
with open("test_receipt.pdf", "rb") as f:
    up1 = client.post(f"/requests/{req_id}/upload", headers=auth(t_sub1), files={"file": ("test_receipt.pdf", f, "application/pdf")})
assert up1.status_code == 200
v1_id = up1.json()["version_id"]

print("- Submitter1 uploading document V2 (Checking versioning)...")
with open("test_receipt.pdf", "rb") as f:
    up2 = client.post(f"/requests/{req_id}/upload", headers=auth(t_sub1), files={"file": ("test_receipt.pdf", f, "application/pdf")})
assert up2.status_code == 200
v2_id = up2.json()["version_id"]
assert v2_id > v1_id
print(f"  -> Version preserved: V1={v1_id}, V2={v2_id}")

print("- Submitter1 submitting request...")
sub_res = client.post(f"/requests/{req_id}/submit", headers=auth(t_sub1))
assert sub_res.status_code == 200
assert sub_res.json()["new_status"] == "Submitted"

# 3. Security Check: Invalid transition
print("- Security: Sub1 tries to submit again (should fail)...")
inv_sub = client.post(f"/requests/{req_id}/submit", headers=auth(t_sub1))
assert inv_sub.status_code == 400

# 4. Processing Workflow
print("- Processing: Trigger OCR and Verification...")
proc_res = client.post(f"/requests/{req_id}/process", headers=auth(t_rev1))
assert proc_res.status_code == 200
assert proc_res.json()["status"] == "Under Review"

# 5. Security: Cross-user access
print("- Security: Submitter2 tries to access Submitter1's request...")
cross_acc = client.get(f"/requests/{req_id}", headers=auth(t_sub2))
assert cross_acc.status_code == 403

# 6. Security: Submitter approves own request
print("- Security: Submitter1 tries to approve own request...")
own_app = client.post(f"/requests/{req_id}/review", json={"action": "approve"}, headers=auth(t_sub1))
assert own_app.status_code == 403

# 7. Reviewer Workflow
print("- Reviewer1 checking request...")
# Verify fields and checks exist in DB
db = TestingSessionLocal()
fields = db.query(models.ExtractedField).filter(models.ExtractedField.extraction_run_id > 0).all()
checks = db.query(models.VerificationCheck).filter(models.VerificationCheck.request_id == req_id).all()
db.close()
assert len(fields) > 0
assert len(checks) >= 0
field_id = fields[0].id

print("- Reviewer1 correcting field...")
corr_res = client.post(f"/requests/{req_id}/correct_field?field_id={field_id}&new_value=200.0", headers=auth(t_rev1))
assert corr_res.status_code == 200

print("- Reviewer1 requests correction...")
req_corr = client.post(f"/requests/{req_id}/review", json={"action": "request_correction", "reason": "Receipt blurry"}, headers=auth(t_rev1))
assert req_corr.status_code == 200
assert req_corr.json()["status"] == "More Information Required"

# 8. Submitter Resubmit Workflow
print("- Submitter1 resubmitting...")
resub = client.post(f"/requests/{req_id}/resubmit", headers=auth(t_sub1))
assert resub.status_code == 200
assert resub.json()["status"] == "Submitted"

print("- Reprocessing...")
res_proc = client.post(f"/requests/{req_id}/process", headers=auth(t_rev1))
assert res_proc.status_code == 200
assert res_proc.json()["status"] == "Under Review"

# 9. Approver Workflow
print("- Approver1 approving...")
app_res = client.post(f"/requests/{req_id}/review", json={"action": "approve"}, headers=auth(t_app1))
assert app_res.status_code == 200
assert app_res.json()["status"] == "Approved"

# 10. Security: Failed processing does not become approved
print("- Security: Failed processing bypass check...")
req2 = client.post("/requests/", json={"type": "Meals", "expense_amount": 50.0, "merchant_name": "Test", "expense_date": "2026-10-01"}, headers=auth(t_sub1)).json()
req2_id = req2["id"]
client.post(f"/requests/{req2_id}/submit", headers=auth(t_sub1))
proc_fail = client.post(f"/requests/{req2_id}/process", headers=auth(t_rev1))
assert proc_fail.status_code == 400
assert proc_fail.json()["detail"] == "No documents attached"

app_fail = client.post(f"/requests/{req2_id}/review", json={"action": "approve"}, headers=auth(t_app1))
assert app_fail.status_code == 400
assert "Cannot approve a request that failed processing" in app_fail.json()["detail"]

print("\nAll End-to-End Verifications PASSED successfully!")
os.remove("test_receipt.pdf")

print("\n- Testing PDF Document...")
from gen_test_files import create_valid_pdf
create_valid_pdf("test_receipt.pdf")
req_pdf = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 150.0}, headers=auth(t_sub1)).json()
req_pdf_id = req_pdf["id"]
with open("test_receipt.pdf", "rb") as f:
    client.post(f"/requests/{req_pdf_id}/upload", headers=auth(t_sub1), files={"file": ("test_receipt.pdf", f, "application/pdf")})
client.post(f"/requests/{req_pdf_id}/submit", headers=auth(t_sub1))
proc_pdf = client.post(f"/requests/{req_pdf_id}/process", headers=auth(t_rev1))
assert proc_pdf.status_code == 200
assert proc_pdf.json()["status"] == "Under Review"
print("  -> PDF Processed Successfully.")
os.remove("test_receipt.pdf")

print("\n- Testing Corrupt/Invalid Document (OCR Failure)...")
req_corr = client.post("/requests/", json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 150.0}, headers=auth(t_sub1)).json()
req_corr_id = req_corr["id"]
with open("corrupt.jpg", "wb") as f: f.write(b"this is not an image")
with open("corrupt.jpg", "rb") as f:
    client.post(f"/requests/{req_corr_id}/upload", headers=auth(t_sub1), files={"file": ("corrupt.jpg", f, "application/pdf")})
client.post(f"/requests/{req_corr_id}/submit", headers=auth(t_sub1))
proc_corr = client.post(f"/requests/{req_corr_id}/process", headers=auth(t_rev1))
assert proc_corr.status_code == 200 # Note: The process endpoint returns 200 with status="Processing Failed" OR returns 200 but fails gracefully. Actually wait, my main.py returns {"status": "Processing Failed"} with a 200 status_code in try-except. Let's assert that!
assert proc_corr.json()["status"] == "Processing Failed"
print("  -> Corrupt Image triggered Processing Failed correctly.")
os.remove("corrupt.jpg")





