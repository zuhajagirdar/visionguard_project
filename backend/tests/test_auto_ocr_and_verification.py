import pytest
import os
import io
from fastapi.testclient import TestClient
from backend.main import app, get_db
from backend.database import Base
from backend import models, gen_test_files
from tests.test_main import engine, TestingSessionLocal, create_user_get_token, auth_header

client = TestClient(app)

def test_auto_ocr_pdf_upload():
    token = create_user_get_token("sub_pdf", "Submitter")
    req = client.post(
        "/requests/",
        json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 150.0},
        headers=auth_header(token)
    ).json()

    pdf_path = "test_auto_ocr.pdf"
    gen_test_files.create_valid_pdf(pdf_path, merchant="Acme Supplies", date="2026-10-01", total="150.00")
    try:
        with open(pdf_path, "rb") as f:
            res_upload = client.post(
                f"/requests/{req['id']}/upload",
                files={"file": (pdf_path, f, "application/pdf")},
                headers=auth_header(token)
            )
        assert res_upload.status_code == 200
        assert res_upload.json()["processing_state"] == "Completed"

        # Check DB directly without having called /process
        db = TestingSessionLocal()
        runs = db.query(models.ExtractionRun).all()
        assert len(runs) >= 1
        latest_run = runs[-1]
        assert latest_run.status == "Completed"

        # Extracted fields check
        extracted = {f.field_name: f.original_value for f in latest_run.extractions}
        assert extracted.get("amount") == "150.00"
        assert extracted.get("date") == "2026-10-01"

        # Verification checks should be automatically computed
        checks = db.query(models.VerificationCheck).filter_by(request_id=req['id']).all()
        assert any(c.rule_name == "Amount Consistency" and c.result == "PASS" for c in checks)
        assert any(c.rule_name == "Date Consistency" and c.result == "PASS" for c in checks)
        db.close()
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_auto_ocr_image_upload():
    token = create_user_get_token("sub_img", "Submitter")
    req = client.post(
        "/requests/",
        json={"type": "Travel", "merchant_name": "OfficeMart", "expense_date": "2026-09-15", "expense_amount": 75.50},
        headers=auth_header(token)
    ).json()

    img_path = "test_receipt.png"
    gen_test_files.create_valid_image(img_path, merchant="OfficeMart", date="2026-09-15", total="75.50")
    try:
        with open(img_path, "rb") as f:
            res_upload = client.post(
                f"/requests/{req['id']}/upload",
                files={"file": (img_path, f, "image/png")},
                headers=auth_header(token)
            )
        assert res_upload.status_code == 200
        assert res_upload.json()["processing_state"] == "Completed"

        # Details endpoint check
        details = client.get(f"/requests/{req['id']}/details", headers=auth_header(token)).json()
        assert len(details["extractions"]) > 0
        ext_map = {e["field_name"]: e["original_value"] for e in details["extractions"]}
        assert ext_map.get("merchant") == "OfficeMart"
        assert ext_map.get("date") == "2026-09-15"
        assert ext_map.get("amount") == "75.50"
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)


def test_amount_mismatch_verification():
    token = create_user_get_token("sub_mismatch", "Submitter")
    # Claimed amount 999.00 vs document amount 150.00
    req = client.post(
        "/requests/",
        json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 999.00},
        headers=auth_header(token)
    ).json()

    pdf_path = "test_mismatch.pdf"
    gen_test_files.create_valid_pdf(pdf_path, merchant="Test", date="2026-10-01", total="150.00")
    try:
        with open(pdf_path, "rb") as f:
            client.post(
                f"/requests/{req['id']}/upload",
                files={"file": (pdf_path, f, "application/pdf")},
                headers=auth_header(token)
            )

        details = client.get(f"/requests/{req['id']}/details", headers=auth_header(token)).json()
        verifs = details.get("verifications", [])
        mismatch_check = next((v for v in verifs if v["rule_name"] == "Amount Consistency"), None)
        assert mismatch_check is not None
        assert mismatch_check["result"] == "INCONSISTENT"
        assert mismatch_check["category"] == "inconsistent"
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_missing_unreadable_fields_detection():
    token = create_user_get_token("sub_missing", "Submitter")
    # Claim created with missing merchant, date, amount
    req = client.post(
        "/requests/",
        json={"type": "Travel"},
        headers=auth_header(token)
    ).json()

    pdf_path = "test_missing.pdf"
    gen_test_files.create_valid_pdf(pdf_path, merchant="Test", date="2026-10-01", total="150.00")
    try:
        with open(pdf_path, "rb") as f:
            client.post(
                f"/requests/{req['id']}/upload",
                files={"file": (pdf_path, f, "application/pdf")},
                headers=auth_header(token)
            )

        details = client.get(f"/requests/{req['id']}/details", headers=auth_header(token)).json()
        missing = details.get("missing_fields", [])
        field_names = [m["field"] for m in missing]
        assert "merchant_name" in field_names
        assert "expense_date" in field_names
        assert "expense_amount" in field_names
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_ocr_failure_corrupt_file():
    token = create_user_get_token("sub_corrupt", "Submitter")
    req = client.post(
        "/requests/",
        json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 100.0},
        headers=auth_header(token)
    ).json()

    # Upload corrupt file
    corrupt_data = b"NOT_A_VALID_PDF_HEADER_OR_IMAGE_DATA"
    res = client.post(
        f"/requests/{req['id']}/upload",
        files={"file": ("broken.pdf", corrupt_data, "application/pdf")},
        headers=auth_header(token)
    )
    assert res.status_code == 200
    assert res.json()["processing_state"] == "Failed"

    details = client.get(f"/requests/{req['id']}/details", headers=auth_header(token)).json()
    version = details["documents"][0]["versions"][0]
    assert version["processing_state"] == "Failed"
    assert version["error_message"] is not None


def test_document_versioning_and_extraction_association():
    token = create_user_get_token("sub_versioning", "Submitter")
    req = client.post(
        "/requests/",
        json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 200.0},
        headers=auth_header(token)
    ).json()

    pdf_v1 = "test_v1.pdf"
    pdf_v2 = "test_v2.pdf"
    gen_test_files.create_valid_pdf(pdf_v1, merchant="Store V1", date="2026-10-01", total="100.00")
    gen_test_files.create_valid_pdf(pdf_v2, merchant="Store V2", date="2026-10-01", total="200.00")

    try:
        # Upload version 1
        with open(pdf_v1, "rb") as f:
            client.post(
                f"/requests/{req['id']}/upload",
                files={"file": ("receipt.pdf", f, "application/pdf")},
                headers=auth_header(token)
            )

        # Upload version 2 (same filename)
        with open(pdf_v2, "rb") as f:
            client.post(
                f"/requests/{req['id']}/upload",
                files={"file": ("receipt.pdf", f, "application/pdf")},
                headers=auth_header(token)
            )

        details = client.get(f"/requests/{req['id']}/details", headers=auth_header(token)).json()
        doc = details["documents"][0]
        assert len(doc["versions"]) == 2

        # Extractions should reflect latest version (V2)
        ext_map = {e["field_name"]: e["original_value"] for e in details["extractions"]}
        assert ext_map.get("amount") == "200.00"
    finally:
        for p in (pdf_v1, pdf_v2):
            if os.path.exists(p): os.remove(p)


def test_ai_assistant_grounded_findings():
    token = create_user_get_token("sub_ai", "Submitter")
    req = client.post(
        "/requests/",
        json={"type": "Travel", "merchant_name": "Airline Co", "expense_date": "2026-10-01", "expense_amount": 300.0},
        headers=auth_header(token)
    ).json()

    pdf_path = "test_ai.pdf"
    gen_test_files.create_valid_pdf(pdf_path, merchant="Airline Co", date="2026-10-01", total="300.00")
    try:
        with open(pdf_path, "rb") as f:
            client.post(
                f"/requests/{req['id']}/upload",
                files={"file": (pdf_path, f, "application/pdf")},
                headers=auth_header(token)
            )

        # Ask question
        res_ask = client.post(
            f"/requests/{req['id']}/ask",
            json={"question": "Explain this request and verification findings"},
            headers=auth_header(token)
        )
        assert res_ask.status_code == 200
        answer = res_ask.json()["answer"]
        assert "Request #" in answer
        assert "Airline Co" in answer or "Extracted" in answer
        assert "300.00" in answer
        assert "Verification Findings:" in answer
        assert "Recommended Next Steps:" in answer
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_retry_ocr_endpoint():
    token = create_user_get_token("sub_retry_ocr", "Submitter")
    req = client.post(
        "/requests/",
        json={"type": "Travel", "merchant_name": "Test", "expense_date": "2026-10-01", "expense_amount": 150.0},
        headers=auth_header(token)
    ).json()

    pdf_path = "test_retry.pdf"
    gen_test_files.create_valid_pdf(pdf_path, merchant="Retry Merchant", date="2026-10-01", total="150.00")
    try:
        with open(pdf_path, "rb") as f:
            client.post(
                f"/requests/{req['id']}/upload",
                files={"file": (pdf_path, f, "application/pdf")},
                headers=auth_header(token)
            )

        # Call retry-ocr
        res_retry = client.post(f"/requests/{req['id']}/retry-ocr", headers=auth_header(token))
        assert res_retry.status_code == 200
        assert res_retry.json()["status"] == "success"
        assert res_retry.json()["processed_count"] >= 1
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
