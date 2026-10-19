import os
import json
import sys
import glob
import re
from datetime import datetime

sys.path.append(os.path.abspath('backend'))
import ocr

def normalize_merchant(val):
    if val is None: return None
    return str(val).strip().lower()

def normalize_amount(val):
    if val is None: return None
    try:
        clean_val = re.sub(r'[^\d\.]', '', str(val))
        return float(clean_val)
    except ValueError:
        return None

def normalize_date(val):
    if val is None or str(val).lower() == 'unknown': return None
    try:
        dt = datetime.strptime(str(val), '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        return None

def main():
    sroie_img_dir = 'eval/sroie_data/img'
    sroie_key_dir = 'eval/sroie_data/key'
    
    if not os.path.exists(sroie_img_dir) or not os.path.exists(sroie_key_dir):
        print("ERROR: SROIE dataset could not be accessed.")
        print("The PS-provided D1: SROIE datasetv2 is not locally available in the expected directory.")
        print("Please download the SROIE dataset (Task 3 Key Information Extraction) and place it in:")
        print(" - eval/sroie_data/img/*.jpg")
        print(" - eval/sroie_data/key/*.txt")
        sys.exit(1)
        
    img_files = glob.glob(os.path.join(sroie_img_dir, '*.jpg'))
    if not img_files:
        print("ERROR: No images found in SROIE dataset directory.")
        sys.exit(1)
        
    results = {
        'total': len(img_files),
        'merchant': {'exact': 0, 'normalized': 0},
        'date': {'exact': 0, 'normalized': 0},
        'amount': {'exact': 0, 'normalized': 0},
        'failures': [],
        'mismatches': []
    }
    
    print(f"Running OCR Evaluation Pipeline on {len(img_files)} SROIE documents...")
    
    for img_path in img_files:
        base_name = os.path.basename(img_path).replace('.jpg', '')
        key_path = os.path.join(sroie_key_dir, f"{base_name}.txt")
        
        if not os.path.exists(key_path):
            continue
            
        with open(key_path, 'r', encoding='utf-8') as f:
            try:
                gt = json.load(f)
            except json.JSONDecodeError:
                continue
                
        expected_merchant = gt.get('company', 'Unknown')
        expected_date = gt.get('date', 'Unknown')
        expected_amount = gt.get('total', '0.0')
        
        try:
            extracted = ocr.extract_fields(img_path)
            
            # Merchant comparison
            ex_merch = extracted.get('merchant', 'Unknown')
            if str(ex_merch) == str(expected_merchant):
                results['merchant']['exact'] += 1
            if normalize_merchant(ex_merch) == normalize_merchant(expected_merchant):
                results['merchant']['normalized'] += 1
                
            # Date comparison
            ex_date = extracted.get('date', 'Unknown')
            if str(ex_date) == str(expected_date):
                results['date']['exact'] += 1
            if normalize_date(ex_date) == normalize_date(expected_date):
                results['date']['normalized'] += 1
                
            # Amount comparison
            ex_amt = extracted.get('amount', '0.0')
            if str(ex_amt) == str(expected_amount):
                results['amount']['exact'] += 1
            if normalize_amount(ex_amt) == normalize_amount(expected_amount):
                results['amount']['normalized'] += 1
                
        except Exception as e:
            results['failures'].append({
                'case': base_name,
                'reason': f'OCR Error: {str(e)}'
            })

    print(json.dumps(results, indent=2))
    
    with open('eval/sroie_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    main()
