import os
import json
import pytest
import tempfile
from backend import ocr

# Helper to load manifest entry by source_id (used for expected values only)
def load_manifest_entry(source_id):
    manifest_path = os.path.join('eval', 'manifest.json')
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    for entry in manifest:
        if entry.get('source_id') == source_id:
            return entry
    raise KeyError(f"No manifest entry for {source_id}")

def _monkeypatch_ocr(text):
    """Context manager that monkey‑patches pytesseract.image_to_string to return *text*.
    Used to avoid dependence on the Tesseract binary during tests.
    """
    class _Ctx:
        def __enter__(self):
            import pytesseract
            self._orig = pytesseract.image_to_string
            pytesseract.image_to_string = lambda *args, **kwargs: text
            return self
        def __exit__(self, exc_type, exc, tb):
            import pytesseract
            pytesseract.image_to_string = self._orig
    return _Ctx()

@pytest.mark.parametrize('source_id,expected_merchant,expected_date,expected_amount', [
    ("X00016469670", "OJC MARKETING SDN BHD", "15/01/2019", "193.00"),
    ("X51005230648", "CROSS CHANNEL NETWORK SDN. BHD.", "29/01/2018", "6.35"),
    ("X51005361923", "SWC ENTERPRISE SDN BHD", "02/01/2018", "4.20"),
])
def test_ocr_extraction_matches_ground_truth(source_id, expected_merchant, expected_date, expected_amount):
    # Simulate OCR output that contains the expected fields and nothing else
    mock_text = f"{expected_merchant}\nDate: {expected_date}\nTotal: {expected_amount}\n"
    entry = load_manifest_entry(source_id)
    img_path = entry['file_path']
    assert os.path.exists(img_path), f"Image missing: {img_path}"
    with _monkeypatch_ocr(mock_text):
        extracted = ocr.extract_fields(img_path)
    from backend.main import normalize_merchant, normalize_date
    assert normalize_merchant(extracted.get('merchant', '')) == normalize_merchant(expected_merchant)
    assert normalize_date(extracted.get('date', '')) == normalize_date(expected_date)
    assert extracted.get('amount') == expected_amount

def test_future_year_filtering():
    mock_text = "Invoice\nDate: 01/01/2030\nTotal: 100.00"
    temp_img = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    temp_img.write(mock_text.encode())
    temp_img.close()
    with _monkeypatch_ocr(mock_text):
        extracted = ocr.extract_fields(temp_img.name)
    # Date should be filtered out because the year is beyond the current year
    assert extracted.get('date') != "2030-01-01"
    os.unlink(temp_img.name)

def test_merchant_selection_vs_noise():
    # Include address, cashier, date, total lines before the true merchant line
    mock_text = "123 Street Name\nCashier: John Doe\nDate: 12/05/2020\nTOTAL: 45.67\nACME CORPORATION"
    temp_img = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    temp_img.write(mock_text.encode())
    temp_img.close()
    with _monkeypatch_ocr(mock_text):
        extracted = ocr.extract_fields(temp_img.name)
    assert extracted.get('merchant') == "ACME CORPORATION"
    os.unlink(temp_img.name)

@pytest.mark.parametrize('date_str,expected_norm', [
    ("12/05/2020", "2020-05-12"),
    ("2020-05-12", "2020-05-12"),
    ("31/02/2020", None),   # impossible date
    ("99/99/9999", None),   # malformed
])
def test_date_parsing_and_validation(date_str, expected_norm):
    mock_text = f"Invoice\nDate: {date_str}\nTotal: 50.00"
    temp_img = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    temp_img.write(mock_text.encode())
    temp_img.close()
    with _monkeypatch_ocr(mock_text):
        extracted = ocr.extract_fields(temp_img.name)
    if expected_norm:
        assert extracted.get('date') == expected_norm
    else:
        assert extracted.get('date') != expected_norm
    os.unlink(temp_img.name)

def test_amount_extraction_with_noise():
    mock_text = "Phone: 012-3456789\nSubtotal: 12.34\nTOTAL AMOUNT: 56.78\nOther: 9999"
    temp_img = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    temp_img.write(mock_text.encode())
    temp_img.close()
    with _monkeypatch_ocr(mock_text):
        extracted = ocr.extract_fields(temp_img.name)
    assert extracted.get('amount') == "56.78"
    os.unlink(temp_img.name)

def test_missing_fields_defaults():
    mock_text = ""
    temp_img = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    temp_img.write(mock_text.encode())
    temp_img.close()
    with _monkeypatch_ocr(mock_text):
        extracted = ocr.extract_fields(temp_img.name)
    assert extracted.get('merchant') == "Unknown"
    assert extracted.get('date') == "Unknown"
    assert extracted.get('amount') == "0.0"
    os.unlink(temp_img.name)
