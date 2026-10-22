import requests
import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

BASE = "http://127.0.0.1:8000"

def log(step, status, details=""):
    badge = "[PASS]" if status else "[FAIL]"
    print(f"{badge} {step}: {details}")

print("=== VERIFLOW LIVE SMOKE TEST ===")

# 1. Login Submitter (alice)
try:
    res = requests.post(f"{BASE}/token", data={"username": "alice", "password": "password"})
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    token_sub = res.json()["access_token"]
    headers_sub = {"Authorization": f"Bearer {token_sub}"}
    log("1. Submitter Login", True, f"Token obtained for alice (id: {token_sub})")
except Exception as e:
    log("1. Submitter Login", False, str(e))
    sys.exit(1)

# 2. Submitter Dashboard
try:
    res = requests.get(f"{BASE}/dashboard", headers=headers_sub)
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    dash_data = res.json()
    assert "pending_count" in dash_data
    log("2. Dashboard Load", True, f"pending={dash_data['pending_count']}, approved={dash_data['approved_count']}")
except Exception as e:
    log("2. Dashboard Load", False, str(e))
    sys.exit(1)

# 3. Create Request
try:
    payload = {
        "type": "Travel",
        "merchant_name": "ACME Supplies",
        "expense_amount": 150.00,
        "expense_date": "2026-10-15",
        "category": "Office",
        "description": "Smoke test reimbursement request"
    }
    res = requests.post(f"{BASE}/requests", json=payload, headers=headers_sub)
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    req_data = res.json()
    req_id = req_data["id"]
    log("3. Create Request", True, f"Created Request #{req_id} status={req_data['status']}")
except Exception as e:
    log("3. Create Request", False, str(e))
    sys.exit(1)

# 4. Upload Document (PDF)
try:
    from backend.gen_test_files import create_valid_pdf
    tmp_pdf = os.path.join(os.path.dirname(__file__), "tmp_smoke_v1.pdf")
    create_valid_pdf(tmp_pdf)
    with open(tmp_pdf, "rb") as f:
        files = {"file": ("receipt.pdf", f, "application/pdf")}
        res = requests.post(f"{BASE}/requests/{req_id}/upload", files=files, headers=headers_sub)
    if os.path.exists(tmp_pdf): os.remove(tmp_pdf)
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    doc_res = res.json()
    log("4. PDF Upload (V1)", True, f"Uploaded V1 document id={doc_res.get('document_id', 'ok')}")
except Exception as e:
    log("4. PDF Upload (V1)", False, str(e))
    sys.exit(1)

# 5. Document Versioning (Upload V2 replacement with same filename)
try:
    tmp_pdf_v2 = os.path.join(os.path.dirname(__file__), "tmp_smoke_v2.pdf")
    create_valid_pdf(tmp_pdf_v2)
    with open(tmp_pdf_v2, "rb") as f:
        files_v2 = {"file": ("receipt.pdf", f, "application/pdf")}
        res = requests.post(f"{BASE}/requests/{req_id}/upload", files=files_v2, headers=headers_sub)
    if os.path.exists(tmp_pdf_v2): os.remove(tmp_pdf_v2)
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    log("5. Document Versioning (V2)", True, "Uploaded V2 replacement document cleanly")
except Exception as e:
    log("5. Document Versioning (V2)", False, str(e))
    sys.exit(1)

# 6. Submit Request
try:
    res = requests.post(f"{BASE}/requests/{req_id}/submit", headers=headers_sub)
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    log("6. Submit Request", True, f"Status changed to {res.json().get('status')}")
except Exception as e:
    log("6. Submit Request", False, str(e))
    sys.exit(1)

# 7. Reviewer Login (bob)
try:
    res = requests.post(f"{BASE}/token", data={"username": "bob", "password": "password"})
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    token_rev = res.json()["access_token"]
    headers_rev = {"Authorization": f"Bearer {token_rev}"}
    log("7. Reviewer Login", True, "Reviewer bob authenticated")
except Exception as e:
    log("7. Reviewer Login", False, str(e))
    sys.exit(1)

# 8. Trigger Automated Processing (OCR + Verification)
try:
    res = requests.post(f"{BASE}/requests/{req_id}/process", headers=headers_rev)
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    log("8. Automated Processing", True, f"Processing result: {res.json()}")
except Exception as e:
    log("8. Automated Processing", False, str(e))
    sys.exit(1)

# 9. Get Full Request Details (Audit log, versions, verifications)
try:
    res = requests.get(f"{BASE}/requests/{req_id}/details", headers=headers_rev)
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    details = res.json()
    docs = details.get("documents", [])
    assert len(docs) > 0, "No documents found"
    versions = docs[0].get("versions", [])
    assert len(versions) == 2, f"Expected 2 versions, found {len(versions)}"
    assert versions[0].get("uploaded_at") is not None, "uploaded_at missing in version"
    log("9. Details & Version History", True, f"Versions count={len(versions)}, uploaded_at={versions[0]['uploaded_at']}")
except Exception as e:
    log("9. Details & Version History", False, str(e))
    sys.exit(1)

# 10. Correction Assistance API
try:
    res = requests.get(f"{BASE}/requests/{req_id}/corrections", headers=headers_rev)
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    corr_data = res.json()
    assert "suggestions" in corr_data
    assert "message" in corr_data
    log("10. Correction Assistance", True, f"Suggestions: {len(corr_data['suggestions'])}, Message: '{corr_data['message'][:60]}...'")
except Exception as e:
    log("10. Correction Assistance", False, str(e))
    sys.exit(1)

# 11. AI Q&A Endpoint
try:
    res = requests.post(f"{BASE}/requests/{req_id}/ask", json={"question": "Explain verification status"}, headers=headers_rev)
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    ans = res.json().get("answer", "")
    log("11. AI Q&A Grounded Response", True, f"Answer: '{ans[:70]}...'")
except Exception as e:
    log("11. AI Q&A Grounded Response", False, str(e))
    sys.exit(1)

# 12. Reviewer Correction Action (Request Correction)
try:
    res = requests.post(f"{BASE}/requests/{req_id}/review", json={
        "action": "request_correction",
        "reason": "Please verify the merchant tax ID"
    }, headers=headers_rev)
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    log("12. Review Action (Request Correction)", True, f"New status: {res.json().get('status')}")
except Exception as e:
    log("12. Review Action (Request Correction)", False, str(e))
    sys.exit(1)

# 13. Submitter Resubmission
try:
    res = requests.post(f"{BASE}/requests/{req_id}/resubmit", headers=headers_sub)
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    log("13. Submitter Resubmission", True, f"Status after resubmit: {res.json().get('status')}")
except Exception as e:
    log("13. Submitter Resubmission", False, str(e))
    sys.exit(1)

# 14. Approver Login (eve_app) & Final Approval
try:
    res = requests.post(f"{BASE}/token", data={"username": "eve_app", "password": "password"})
    assert res.status_code == 200, f"Status {res.status_code}: {res.text}"
    token_app = res.json()["access_token"]
    headers_app = {"Authorization": f"Bearer {token_app}"}
    
    # Needs to be reprocessed or Under Review
    # Let's trigger review process
    requests.post(f"{BASE}/requests/{req_id}/process", headers=headers_rev)
    res_app = requests.post(f"{BASE}/requests/{req_id}/review", json={"action": "approve", "reason": "All checks verified"}, headers=headers_app)
    assert res_app.status_code == 200, f"Status {res_app.status_code}: {res_app.text}"
    log("14. Final Approval", True, f"Final status: {res_app.json().get('status')}")
except Exception as e:
    log("14. Final Approval", False, str(e))
    sys.exit(1)

print("\n>>> ALL SMOKE TEST WORKFLOW STEPS PASSED WITH 100% SUCCESS! <<<")
