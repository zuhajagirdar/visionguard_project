import os
import sys
import json
import re
from datetime import datetime

sys.path.append(os.path.abspath('backend'))
import ocr

def normalize_merchant(val):
    if not val: return ""
    clean = re.sub(r'[^\w\s]', '', str(val))
    return re.sub(r'\s+', ' ', clean).strip().lower()

def normalize_date(val):
    if not val: return ""
    try:
        dt = datetime.strptime(str(val), '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        try:
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
        print("ERROR: eval/manifest.json not found.")
        return

    with open('eval/manifest.json', 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    results = {
        "dataset_used": "SROIE datasetv2 (Subset)",
        "total_documents": 0,
        "failed_unreadable": 0,
        "fields": {
            "merchant": {"exact": 0, "normalized": 0},
            "date": {"exact": 0, "normalized": 0},
            "amount": {"exact": 0, "normalized": 0}
        },
        "error_cases": []
    }

    # Filter out the example template if real data isn't provided
    valid_manifest = [m for m in manifest if not m['source_id'].startswith("EXAMPLE_ID")]
    results["total_documents"] = len(valid_manifest)

    for case in valid_manifest:
        doc_id = case["source_id"]
        doc_path = case["file_path"]
        gt_merchant = case["ground_truth_merchant"]
        gt_date = case["ground_truth_date"]
        gt_amount = case["ground_truth_amount"]

        try:
            extracted = ocr.extract_fields(doc_path)
        except Exception as e:
            results["failed_unreadable"] += 1
            results["error_cases"].append({"document_id": doc_id, "error_type": "document processing failure", "reason": str(e)})
            continue

        ex_merch = extracted.get("merchant", "")
        ex_date = extracted.get("date", "")
        ex_amt = extracted.get("amount", "")

        # Merchant
        if ex_merch == gt_merchant:
            results["fields"]["merchant"]["exact"] += 1
        elif normalize_merchant(ex_merch) == normalize_merchant(gt_merchant):
            results["fields"]["merchant"]["normalized"] += 1
        else:
            results["error_cases"].append({"document_id": doc_id, "error_type": "wrong merchant", "expected": gt_merchant, "extracted": ex_merch})

        # Date
        if ex_date == gt_date:
            results["fields"]["date"]["exact"] += 1
        elif normalize_date(ex_date) == normalize_date(gt_date):
            results["fields"]["date"]["normalized"] += 1
        else:
            results["error_cases"].append({"document_id": doc_id, "error_type": "wrong date", "expected": gt_date, "extracted": ex_date})

        # Amount
        if str(ex_amt) == str(gt_amount):
            results["fields"]["amount"]["exact"] += 1
        elif normalize_amount(ex_amt) == normalize_amount(gt_amount):
            results["fields"]["amount"]["normalized"] += 1
        else:
            results["error_cases"].append({"document_id": doc_id, "error_type": "wrong amount", "expected": gt_amount, "extracted": ex_amt})

    # Note: GenAI evaluation is completely separated and explicitly omitted here.

    with open('eval/results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print("Evaluation executed. Output written to eval/results.json.")

if __name__ == '__main__':
    main()
