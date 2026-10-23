import os
import shutil
import pytest
from fastapi.testclient import TestClient
from backend.main import app, resolve_filepath
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
    for p in ["test_sample_receipt.pdf", "test_sample_invoice.pdf"]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

def test_request_sample_receipt_and_scanned_invoice_workflow():
    token = create_user_get_token("alice_test_45", "Submitter")
    header = auth_header(token)

    receipt_sample = "test_sample_receipt.pdf"
    gen_test_files.create_valid_pdf(receipt_sample, merchant="CORNER CAFE", date="2026-09-18", total="380.00")
    invoice_sample = "test_sample_invoice.pdf"
    gen_test_files.create_valid_pdf(invoice_sample, merchant="Larkfield Stationers", date="2026-09-20", total="8.36")

    # Step 1: Create fresh draft request with empty claim details
    req = client.post(
        "/requests/",
        json={"type": "Meals", "description": "Client dinner test"},
        headers=header
    ).json()
    req_id = req["id"]

    # Step 2: Upload sample-receipt.pdf
    with open(receipt_sample, "rb") as f:
        upload_res = client.post(
            f"/requests/{req_id}/upload",
            files={"file": ("sample-receipt.pdf", f, "application/pdf")},
            headers=header
        )
    assert upload_res.status_code == 200

    # Step 3: Check details immediately after upload
    details = client.get(f"/requests/{req_id}/details", headers=header).json()

    # Check 1: OCR extracted CORNER CAFE, 2026-09-18, and 380.00
    doc_exts = details.get("document_extractions", [])
    assert len(doc_exts) == 1
    receipt_ext = doc_exts[0]
    assert receipt_ext["document_filename"] == "sample-receipt.pdf"
    field_map = {f["field_name"]: f["original_value"] for f in receipt_ext["fields"]}
    assert field_map.get("merchant") == "CORNER CAFE"
    assert field_map.get("date") == "2026-09-18"
    assert field_map.get("amount") == "380.00"

    # Check 2: Before copying values into claim form:
    # Required Field should report missing claim details, but Document Readability should pass
    verifs = details.get("verifications", [])
    req_field_check = next((v for v in verifs if v["rule_name"] == "Required Field"), None)
    assert req_field_check is not None
    assert req_field_check["result"] == "CANNOT DETERMINE"
    assert req_field_check["category"] == "missing"

    readability_check = next((v for v in verifs if v["rule_name"] == "Document Readability"), None)
    assert readability_check is not None
    assert readability_check["result"] == "PASS"

    # Check missing_fields reported in details:
    missing = details.get("missing_fields", [])
    missing_claim_fields = [m["field"] for m in missing if m.get("location") == "claim"]
    assert "merchant_name" in missing_claim_fields
    assert "expense_date" in missing_claim_fields
    assert "expense_amount" in missing_claim_fields
    # Must NOT report document unreadable since readability is PASS
    assert not any(m.get("field") == "document_unreadable" for m in missing)

    # Step 4: Simulate "Copy Extracted Data to Form" and Save Draft
    update_res = client.put(
        f"/requests/{req_id}",
        json={
            "merchant_name": field_map["merchant"],
            "expense_date": field_map["date"],
            "expense_amount": float(field_map["amount"])
        },
        headers=header
    )
    assert update_res.status_code == 200

    # Step 5: Check verification after saving matching values
    details_after_save = client.get(f"/requests/{req_id}/details", headers=header).json()
    verifs2 = details_after_save.get("verifications", [])

    assert any(v["rule_name"] == "Required Field" and v["result"] == "PASS" for v in verifs2)
    assert any(v["rule_name"] == "Amount Consistency" and v["result"] == "PASS" for v in verifs2)
    assert any(v["rule_name"] == "Date Consistency" and v["result"] == "PASS" for v in verifs2)
    assert any(v["rule_name"] == "Merchant Consistency" and v["result"] == "PASS" for v in verifs2)
    assert any(v["rule_name"] == "Document Readability" and v["result"] == "PASS" for v in verifs2)

    # Step 6: Upload sample-scanned-invoice.pdf as second document
    with open(invoice_sample, "rb") as f:
        upload_inv_res = client.post(
            f"/requests/{req_id}/upload",
            files={"file": ("sample-scanned-invoice.pdf", f, "application/pdf")},
            headers=header
        )
    assert upload_inv_res.status_code == 200

    # Step 7: Confirm extractions remain associated with the correct file/version
    details_two_docs = client.get(f"/requests/{req_id}/details", headers=header).json()
    doc_exts_two = details_two_docs.get("document_extractions", [])
    assert len(doc_exts_two) == 2

    doc_names = [d["document_filename"] for d in doc_exts_two]
    assert "sample-receipt.pdf" in doc_names
    assert "sample-scanned-invoice.pdf" in doc_names

    receipt_doc_ext = next(d for d in doc_exts_two if d["document_filename"] == "sample-receipt.pdf")
    invoice_doc_ext = next(d for d in doc_exts_two if d["document_filename"] == "sample-scanned-invoice.pdf")

    receipt_fields = {f["field_name"]: f["original_value"] for f in receipt_doc_ext["fields"]}
    invoice_fields = {f["field_name"]: f["original_value"] for f in invoice_doc_ext["fields"]}

    # Receipt fields must be unpolluted by the invoice
    assert receipt_fields.get("merchant") == "CORNER CAFE"
    assert receipt_fields.get("amount") == "380.00"

    # Invoice fields must be associated with the invoice document
    assert invoice_fields.get("merchant") == "Larkfield Stationers"
    assert invoice_fields.get("amount") == "8.36"

    # Step 8: Test genuinely unreadable / corrupt document
    req_corrupt = client.post("/requests/", json={"type": "Other"}, headers=header).json()
    client.post(
        f"/requests/{req_corrupt['id']}/upload",
        files={"file": ("broken.pdf", b"CORRUPTED_NOT_A_PDF_DATA", "application/pdf")},
        headers=header
    )
    details_corrupt = client.get(f"/requests/{req_corrupt['id']}/details", headers=header).json()
    v_corrupt = details_corrupt.get("verifications", [])
    readability_fail = next((v for v in v_corrupt if v["rule_name"] == "Document Readability"), None)
    assert readability_fail is not None
    assert readability_fail["result"] == "CANNOT DETERMINE"
    assert readability_fail["category"] == "unreadable"

    missing_corrupt = details_corrupt.get("missing_fields", [])
    assert any(m.get("field") == "document_unreadable" for m in missing_corrupt)
