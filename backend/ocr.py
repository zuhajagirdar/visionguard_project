import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:/Users/zuhaj/.gemini/antigravity/scratch/expense-reimbursement-system/scripts/installers/tess_portable/tesseract.exe"
from PIL import Image
import re
import pdfplumber
import dateutil.parser

def extract_fields(file_path: str):
    text = ""
    is_pdf = file_path.lower().endswith(".pdf")
    
    if is_pdf:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        if not text.strip():
            raise Exception("No text could be extracted from PDF.")
    else:
        text = pytesseract.image_to_string(Image.open(file_path))
        if not text.strip():
            raise Exception("No text could be extracted from the image.")
            
    extracted = {
        "merchant": "Unknown",
        "date": "Unknown",
        "amount": "0.0",
        "category": "Unknown",
        "confidence": 0.8  # deterministic placeholder when real confidence isn't available
    }
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return extracted
        
    # MERCHANT: Usually top 1-3 lines. Avoid obvious dates, totals, standard fluff.
    merchant_candidate = None
    for line in lines[:5]:
        if re.search(r'\d{2}/\d{2}/\d{2,4}', line) or 'TOTAL' in line.upper() or 'GST' in line.upper() or 'TAX' in line.upper():
            continue
        # Check if it has letters
        if re.search(r'[a-zA-Z]', line):
            merchant_candidate = line.strip()
            break
            
    if merchant_candidate:
        # Strip some common suffix like SDN BHD if we wanted, but SROIE expects it.
        extracted["merchant"] = merchant_candidate

    # DATE:
    date_regex = r'\b(\d{1,2}[\./-]\d{1,2}[\./-]\d{2,4}|\d{2,4}[\./-]\d{1,2}[\./-]\d{1,2})\b'
    date_matches = []
    for line in lines:
        for match in re.findall(date_regex, line):
            date_matches.append(match)
            
    if date_matches:
        # Just pick the first date looking thing
        extracted["date"] = date_matches[0]
        
    # AMOUNT:
    # Look for 'total', 'grand total', 'amount due'
    # Or just the largest float number that is at the end of a line.
    amount_candidates = []
    for i, line in enumerate(lines):
        # find numbers with decimals
        nums = re.findall(r'\b\d{1,5}\.\d{2}\b', line)
        for n in nums:
            val = float(n)
            # Boost score if 'total' is in the line or previous line
            score = val
            if 'total' in line.lower() or 'amount' in line.lower() or 'net' in line.lower():
                score += 10000.0 
            amount_candidates.append((val, score))
            
    if amount_candidates:
        # Sort by score descending
        amount_candidates.sort(key=lambda x: x[1], reverse=True)
        extracted["amount"] = f"{amount_candidates[0][0]:.2f}"
    else:
        # try without decimals
        nums = re.findall(r'\b\d+\b', text)
        if nums:
            amount_candidates = []
            for n in nums:
                val = float(n)
                amount_candidates.append(val)
            amount_candidates.sort(reverse=True)
            if amount_candidates:
                # Assuming the biggest number might be the total if it's not a phone number or date
                # Cap it at something reasonable
                filtered = [x for x in amount_candidates if x < 100000 and x > 0]
                if filtered:
                    extracted["amount"] = f"{filtered[0]:.2f}"
                    
    return extracted
