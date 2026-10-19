import os
import sys
import json
import re
from datetime import datetime

sys.path.append(os.path.abspath('backend'))
import ocr

def normalize_merchant(val):
    if not val: return ""
    # lowercase, whitespace and punctuation normalization
    clean = re.sub(r'[^\w\s]', '', str(val))
    return re.sub(r'\s+', ' ', clean).strip().lower()

def normalize_date(val):
    if not val: return ""
    try:
        dt = datetime.strptime(str(val), '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        # SROIE dates often come as DD/MM/YYYY or YYYY-MM-DD
        # We enforce matching calendar dates via datetime parse
        # If it fails to parse as our app's target format, we fallback to attempting common parse
        try:
            # Fallback for SROIE common DD/MM/YYYY
            dt = datetime.strptime(str(val), '%d/%m/%Y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return ""

def normalize_amount(val):
    if not val: return None
    try:
        clean = re.sub(r'[^\d\.]', '', str(val))
        return float(clean)
    except ValueError:
        return None

def main():
    if not os.path.exists('eval/manifest.json'):
        print("ERROR: eval/manifest.json not found. Run eval/setup_manifest.py first (requires local SROIE data).")
        return

    with open('eval/manifest.json', 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    results = {
        "total_documents": len(manifest),
        "failed_unreadable": 0,
        "fields": {
            "merchant": {"exact": 0, "normalized": 0},
            "date": {"exact": 0, "normalized": 0},
            "amount": {"exact": 0, "normalized": 0}
        },
        "errors": []
    }

    for case in manifest:
        doc_id = case["document_id"]
        doc_path = case["document_path"]
        gt = case["ground_truth"]

        try:
            extracted = ocr.extract_fields(doc_path)
        except Exception as e:
            results["failed_unreadable"] += 1
            results["errors"].append({"document_id": doc_id, "reason": str(e)})
            continue

        # Merchant
        ex_merch = extracted.get("merchant", "")
        if ex_merch == gt["merchant"]:
            results["fields"]["merchant"]["exact"] += 1
        if normalize_merchant(ex_merch) == normalize_merchant(gt["merchant"]):
            results["fields"]["merchant"]["normalized"] += 1

        # Date
        ex_date = extracted.get("date", "")
        if ex_date == gt["date"]:
            results["fields"]["date"]["exact"] += 1
        if normalize_date(ex_date) == normalize_date(gt["date"]):
            results["fields"]["date"]["normalized"] += 1

        # Amount
        ex_amt = extracted.get("amount", "")
        if str(ex_amt) == str(gt["amount"]):
            results["fields"]["amount"]["exact"] += 1
        if normalize_amount(ex_amt) == normalize_amount(gt["amount"]):
            results["fields"]["amount"]["normalized"] += 1

    with open('eval/results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    # Generate Human Readable Report
    md = f"""# SROIE OCR Evaluation Report

## Dataset Information
- **Dataset:** D1: SROIE datasetv2
- **Subset:** Task 3 Key Information Extraction (Held-out Evaluation Subset)
- **Total Documents Evaluated:** {results["total_documents"]}

*Note: This evaluation was executed using the actual OCR pipeline \ackend/ocr.py\. This is isolated from the synthetic application demo data and workflow tests.*

## Summary Metrics
- **Failed / Unreadable Documents:** {results["failed_unreadable"]}

## Per-Field Accuracy
### Merchant
- Exact Match: {results["fields"]["merchant"]["exact"]} / {results["total_documents"]}
- Normalized Match: {results["fields"]["merchant"]["normalized"]} / {results["total_documents"]}

### Date
- Exact Match: {results["fields"]["date"]["exact"]} / {results["total_documents"]}
- Normalized Match: {results["fields"]["date"]["normalized"]} / {results["total_documents"]}

### Amount
- Exact Match: {results["fields"]["amount"]["exact"]} / {results["total_documents"]}
- Normalized Match: {results["fields"]["amount"]["normalized"]} / {results["total_documents"]}

## Failed Cases
"""
    for err in results["errors"]:
        md += f"- **{err['document_id']}**: {err['reason']}\n"
    
    if not results["errors"]:
        md += "None.\n"

    with open('eval/EVALUATION_REPORT.md', 'w', encoding='utf-8') as f:
        f.write(md)

    print("Evaluation complete. Results written to eval/results.json and eval/EVALUATION_REPORT.md.")

if __name__ == '__main__':
    main()
