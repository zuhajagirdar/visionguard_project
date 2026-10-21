import os, json, re, sys
from datetime import datetime

# Ensure backend is on PYTHONPATH for OCR import
sys.path.append(os.path.abspath('backend'))
import ocr

def normalize_merchant(val):
    if not val:
        return ''
    return re.sub(r'[^\w\s]', '', str(val)).lower().strip()

def normalize_amount(val):
    if not val:
        return None
    try:
        clean = re.sub(r'[^\d\.]', '', str(val))
        return float(clean)
    except ValueError:
        return None

def normalize_date(val):
    if not val:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%y', '%d.%m.%Y'):
        try:
            dt = datetime.strptime(str(val), fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def main():
    manifest_path = os.path.join('eval', 'manifest.json')
    if not os.path.exists(manifest_path):
        print('ERROR: manifest.json not found.')
        sys.exit(1)
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    if not isinstance(manifest, list) or len(manifest) == 0:
        print('ERROR: manifest is empty or malformed.')
        sys.exit(1)

    results = {
        'total_documents': len(manifest),
        'merchant': {'exact': 0, 'normalized': 0},
        'date': {'exact': 0, 'normalized': 0},
        'amount': {'exact': 0, 'normalized': 0},
        'error_cases': []
    }

    for entry in manifest:
        img_path = entry.get('file_path')
        if not img_path or not os.path.exists(img_path):
            results['error_cases'].append({
                'document_id': entry.get('source_id'),
                'error_type': 'missing_image',
                'detail': f"Image not found at {img_path}"
            })
            continue
        gt_merchant = entry.get('ground_truth_merchant')
        gt_date = entry.get('ground_truth_date')
        gt_amount = entry.get('ground_truth_amount')
        try:
            extracted = ocr.extract_fields(img_path)
        except Exception as e:
            results['error_cases'].append({
                'document_id': entry.get('source_id'),
                'error_type': 'ocr_failure',
                'detail': str(e)
            })
            continue
        # Merchant
        ex_merchant = extracted.get('merchant')
        if ex_merchant == gt_merchant:
            results['merchant']['exact'] += 1
        if normalize_merchant(ex_merchant) == normalize_merchant(gt_merchant):
            results['merchant']['normalized'] += 1
        # Date
        ex_date = extracted.get('date')
        if ex_date == gt_date:
            results['date']['exact'] += 1
        if normalize_date(ex_date) == normalize_date(gt_date):
            results['date']['normalized'] += 1
        # Amount
        ex_amount = extracted.get('amount')
        if ex_amount == gt_amount:
            results['amount']['exact'] += 1
        if normalize_amount(ex_amount) == normalize_amount(gt_amount):
            results['amount']['normalized'] += 1

    print(json.dumps(results, indent=2))
    out_path = os.path.join('eval', 'results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    main()
