import os
import sys
import time
import json
import difflib
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Add backend to path
sys.path.insert(0, os.path.abspath('backend'))
sys.path.insert(0, os.path.abspath('.'))

from backend import ocr
from backend.main import normalize_merchant, normalize_date

def create_receipt_image(path, merchant, date, amount, subtotal=None, tax=None, tip=None, tendered=None, change=None, comma_decimal=False, header_noise=True):
    img = Image.new('RGB', (800, 600), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    try:
        font_large = ImageFont.truetype("arial.ttf", 26)
        font_med = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font_large = ImageFont.load_default()
        font_med = ImageFont.load_default()

    y = 30
    if header_noise:
        d.text((50, y), "TAX INVOICE / OFFICIAL RECEIPT", fill=(100, 100, 100), font=font_med)
        y += 35
        d.text((50, y), "ORDER #4921  TABLE 12", fill=(120, 120, 120), font=font_med)
        y += 35

    d.text((50, y), str(merchant), fill=(0, 0, 0), font=font_large)
    y += 40
    d.text((50, y), "123 Business Way, Suite 400", fill=(120, 120, 120), font=font_med)
    y += 30
    d.text((50, y), "Tel: 555-0199  ROC NO: 987654-V", fill=(120, 120, 120), font=font_med)
    y += 35
    d.text((50, y), f"Date: {date} 14:32:00", fill=(0, 0, 0), font=font_med)
    y += 40

    if subtotal:
        d.text((50, y), f"Subtotal: ${subtotal}", fill=(50, 50, 50), font=font_med)
        y += 30
    if tax:
        d.text((50, y), f"Tax (10%): ${tax}", fill=(50, 50, 50), font=font_med)
        y += 30
    if tip:
        d.text((50, y), f"Tip / Gratuity: ${tip}", fill=(50, 50, 50), font=font_med)
        y += 30

    amt_str = f"{amount}".replace('.', ',') if comma_decimal else f"{amount}"
    d.text((50, y), f"TOTAL: ${amt_str}", fill=(0, 0, 0), font=font_large)
    y += 40

    if tendered:
        d.text((50, y), f"Cash Tendered: ${tendered}", fill=(80, 80, 80), font=font_med)
        y += 30
    if change:
        d.text((50, y), f"Change Due: ${change}", fill=(80, 80, 80), font=font_med)
        y += 30

    d.text((50, y), "Thank You For Your Business!", fill=(100, 100, 100), font=font_med)
    img.save(path)

def create_receipt_pdf(path, merchant, date, amount):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path)
    c.drawString(100, 750, "OFFICIAL RECEIPT")
    c.drawString(100, 725, str(merchant))
    c.drawString(100, 700, f"Date: {date}")
    c.drawString(100, 675, f"Subtotal: $450.00")
    c.drawString(100, 650, f"Tax: $70.00")
    c.drawString(100, 625, f"TOTAL: ${amount}")
    c.save()

def run_repeatable_evaluation():
    test_dir = os.path.join("eval", "synthetic_test_assets")
    os.makedirs(test_dir, exist_ok=True)

    test_cases = [
        {
            "id": "SYN_01_CLEAN_PNG",
            "format": "PNG",
            "file": os.path.join(test_dir, "syn_01.png"),
            "generator": lambda p: create_receipt_image(p, "Global Logistics Corp", "2026-07-22", "345.80"),
            "claim": {"merchant": "Global Logistics Corp", "date": "2026-07-22", "amount": 345.80},
            "ground_truth": {"merchant": "Global Logistics Corp", "date": "2026-07-22", "amount": "345.80"},
            "expected_issue": None
        },
        {
            "id": "SYN_02_CLEAN_JPG",
            "format": "JPG",
            "file": os.path.join(test_dir, "syn_02.jpg"),
            "generator": lambda p: create_receipt_image(p, "Metro Tech Solutions LLC", "2026-08-15", "1250.00"),
            "claim": {"merchant": "Metro Tech Solutions LLC", "date": "2026-08-15", "amount": 1250.00},
            "ground_truth": {"merchant": "Metro Tech Solutions LLC", "date": "2026-08-15", "amount": "1250.00"},
            "expected_issue": None
        },
        {
            "id": "SYN_03_TAX_TIP_CASH_TRAP",
            "format": "PNG",
            "file": os.path.join(test_dir, "syn_03.png"),
            "generator": lambda p: create_receipt_image(
                p, "Bistro Del Arte", "2026-09-05", "100.00",
                subtotal="80.00", tax="8.00", tip="12.00", tendered="150.00", change="50.00"
            ),
            "claim": {"merchant": "Bistro Del Arte", "date": "2026-09-05", "amount": 100.00},
            "ground_truth": {"merchant": "Bistro Del Arte", "date": "2026-09-05", "amount": "100.00"},
            "expected_issue": None
        },
        {
            "id": "SYN_04_MONTH_NAME_COMMA_DECIMAL",
            "format": "JPG",
            "file": os.path.join(test_dir, "syn_04.jpg"),
            "generator": lambda p: create_receipt_image(
                p, "Nordic Supplies Enterprise", "14 Oct 2026", "284.50",
                subtotal="250.00", tax="34.50", comma_decimal=True
            ),
            "claim": {"merchant": "Nordic Supplies Enterprise", "date": "2026-10-14", "amount": 284.50},
            "ground_truth": {"merchant": "Nordic Supplies Enterprise", "date": "2026-10-14", "amount": "284.50"},
            "expected_issue": None
        },
        {
            "id": "SYN_05_NATIVE_PDF",
            "format": "PDF",
            "file": os.path.join(test_dir, "syn_05.pdf"),
            "generator": lambda p: create_receipt_pdf(p, "Summit Enterprises", "2026-06-15", "520.00"),
            "claim": {"merchant": "Summit Enterprises", "date": "2026-06-15", "amount": 520.00},
            "ground_truth": {"merchant": "Summit Enterprises", "date": "2026-06-15", "amount": "520.00"},
            "expected_issue": None
        },
        {
            "id": "SYN_06_SPELLING_TYPO_WARNING",
            "format": "PNG",
            "file": os.path.join(test_dir, "syn_06.png"),
            "generator": lambda p: create_receipt_image(p, "Pacific Retail Enterprises", "2026-09-10", "180.00"),
            "claim": {"merchant": "Pacifc Retal Enterprises", "date": "2026-09-10", "amount": 180.00}, # Typo in form
            "ground_truth": {"merchant": "Pacific Retail Enterprises", "date": "2026-09-10", "amount": "180.00"},
            "expected_issue": "spelling_mismatch"
        },
        {
            "id": "SYN_07_AMOUNT_MISMATCH",
            "format": "PNG",
            "file": os.path.join(test_dir, "syn_07.png"),
            "generator": lambda p: create_receipt_image(p, "Apex Logistics", "2026-08-20", "450.00"),
            "claim": {"merchant": "Apex Logistics", "date": "2026-08-20", "amount": 600.00}, # Wrong amount in claim
            "ground_truth": {"merchant": "Apex Logistics", "date": "2026-08-20", "amount": "450.00"},
            "expected_issue": "amount_mismatch"
        },
        {
            "id": "SYN_08_HIGH_VALUE_WARNING",
            "format": "PNG",
            "file": os.path.join(test_dir, "syn_08.png"),
            "generator": lambda p: create_receipt_image(p, "Enterprise Server Hardware", "2026-07-30", "7500.00"),
            "claim": {"merchant": "Enterprise Server Hardware", "date": "2026-07-30", "amount": 7500.00},
            "ground_truth": {"merchant": "Enterprise Server Hardware", "date": "2026-07-30", "amount": "7500.00"},
            "expected_issue": "unusual_amount"
        },
        {
            "id": "SYN_09_CORRUPTED_DOCUMENT",
            "format": "PNG",
            "file": os.path.join(test_dir, "syn_09.png"),
            "generator": lambda p: open(p, "wb").write(b"NOT_A_VALID_IMAGE_DATA_12345"),
            "claim": {"merchant": "Broken Store", "date": "2026-08-01", "amount": 50.00},
            "ground_truth": {"merchant": "Unknown", "date": "Unknown", "amount": "0.0"},
            "expected_issue": "unreadable"
        }
    ]

    total_cases = len(test_cases)
    merchant_matches = 0
    date_matches = 0
    amount_matches = 0
    latencies = []

    issue_expected_count = 0
    issue_detected_count = 0
    false_positives = 0

    eval_records = []

    for case in test_cases:
        # Generate file
        case["generator"](case["file"])

        start_time = time.perf_counter()
        failed_ocr = False
        ext = {}
        try:
            ext = ocr.extract_fields(case["file"])
        except Exception as exc:
            failed_ocr = True
            ext = {"merchant": "Unknown", "date": "Unknown", "amount": "0.0", "engine": "failed"}

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        latencies.append(duration_ms)

        # Accuracy vs Ground Truth
        m_ok = normalize_merchant(ext.get("merchant", "")) == normalize_merchant(case["ground_truth"]["merchant"])
        d_ok = normalize_date(ext.get("date", "")) == normalize_date(case["ground_truth"]["date"])
        a_ok = abs(float(ext.get("amount", 0.0) or 0.0) - float(case["ground_truth"]["amount"])) < 0.05

        if m_ok: merchant_matches += 1
        if d_ok: date_matches += 1
        if a_ok: amount_matches += 1

        # Simulated verification check
        detected_issue = None
        if failed_ocr or ext.get("engine") == "failed" or (ext.get("merchant") == "Unknown" and ext.get("amount") == "0.0"):
            detected_issue = "unreadable"
        elif case["claim"]["amount"] > 5000.0:
            detected_issue = "unusual_amount"
        elif not a_ok or abs(float(case["claim"]["amount"]) - float(ext.get("amount", 0.0) or 0.0)) >= 0.01:
            detected_issue = "amount_mismatch"
        else:
            c_m = normalize_merchant(case["claim"]["merchant"])
            e_m = normalize_merchant(ext.get("merchant", ""))
            if c_m != e_m:
                ratio = difflib.SequenceMatcher(None, c_m, e_m).ratio()
                if ratio >= 0.65:
                    detected_issue = "spelling_mismatch"
                else:
                    detected_issue = "merchant_mismatch"

        # Recall and false positive metrics
        exp_iss = case.get("expected_issue")
        if exp_iss:
            issue_expected_count += 1
            if detected_issue == exp_iss:
                issue_detected_count += 1
        else:
            if detected_issue is not None:
                false_positives += 1

        eval_records.append({
            "id": case["id"],
            "format": case["format"],
            "engine": ext.get("engine", "unknown"),
            "latency_ms": round(duration_ms, 2),
            "merchant_extracted": ext.get("merchant"),
            "date_extracted": ext.get("date"),
            "amount_extracted": ext.get("amount"),
            "merchant_match": m_ok,
            "date_match": d_ok,
            "amount_match": a_ok,
            "expected_issue": exp_iss,
            "detected_issue": detected_issue
        })

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    issue_recall = (issue_detected_count / issue_expected_count) * 100.0 if issue_expected_count else 100.0
    fp_rate = (false_positives / (total_cases - issue_expected_count)) * 100.0 if (total_cases - issue_expected_count) else 0.0

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_test_receipts": total_cases,
        "metrics": {
            "merchant_accuracy_pct": round((merchant_matches / total_cases) * 100.0, 1),
            "date_accuracy_pct": round((date_matches / total_cases) * 100.0, 1),
            "amount_accuracy_pct": round((amount_matches / total_cases) * 100.0, 1),
            "issue_detection_recall_pct": round(issue_recall, 1),
            "false_positive_rate_pct": round(fp_rate, 1),
            "avg_latency_ms": round(avg_latency, 1),
            "min_latency_ms": round(min(latencies), 1),
            "max_latency_ms": round(max(latencies), 1)
        },
        "records": eval_records
    }

    out_file = os.path.join("eval", "repeatable_eval_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "="*70)
    print("      VERIFLOW REPEATABLE RECEIPT EXTRACTION & VERIFICATION BENCHMARK      ")
    print("="*70)
    print(f"Total Test Receipts Evaluated: {total_cases}")
    print(f"Merchant Accuracy:            {summary['metrics']['merchant_accuracy_pct']}% ({merchant_matches}/{total_cases})")
    print(f"Date Accuracy:                {summary['metrics']['date_accuracy_pct']}% ({date_matches}/{total_cases})")
    print(f"Amount Accuracy:              {summary['metrics']['amount_accuracy_pct']}% ({amount_matches}/{total_cases})")
    print(f"Issue-Detection Recall:       {summary['metrics']['issue_detection_recall_pct']}% ({issue_detected_count}/{issue_expected_count})")
    print(f"False Positive Rate:          {summary['metrics']['false_positive_rate_pct']}% ({false_positives}/{total_cases - issue_expected_count})")
    print(f"Processing Latency (Avg):     {summary['metrics']['avg_latency_ms']} ms (Min: {summary['metrics']['min_latency_ms']} ms, Max: {summary['metrics']['max_latency_ms']} ms)")
    print("="*70)
    print(f"{'Test ID':<25} | {'Format':<6} | {'Engine':<12} | {'Time (ms)':<9} | {'Merch':<5} | {'Date':<5} | {'Amt':<5} | {'Detected Issue'}")
    print("-" * 70)
    for r in eval_records:
        m_s = "OK" if r['merchant_match'] else "FAIL"
        d_s = "OK" if r['date_match'] else "FAIL"
        a_s = "OK" if r['amount_match'] else "FAIL"
        iss = r['detected_issue'] or "None (Clean)"
        print(f"{r['id']:<25} | {r['format']:<6} | {r['engine']:<12} | {r['latency_ms']:<9} | {m_s:<5} | {d_s:<5} | {a_s:<5} | {iss}")
    print("="*70)
    print(f"Results written to: {out_file}\n")

if __name__ == "__main__":
    run_repeatable_evaluation()
