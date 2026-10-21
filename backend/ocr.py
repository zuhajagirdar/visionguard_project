import re
import json
from datetime import datetime
from typing import Dict
import pdfplumber
from PIL import Image
import pytesseract

# Optional: keep Tesseract configuration portable; rely on system PATH or environment variable.
# Users can set pytesseract.pytesseract.tesseract_cmd externally if needed.

def _read_text(file_path: str) -> str:
    """Extract raw text from a PDF, TXT, or image file.
    Raises an exception if no text could be extracted.
    """
    if file_path.lower().endswith('.pdf'):
        with pdfplumber.open(file_path) as pdf:
            texts = [page.extract_text() or "" for page in pdf.pages]
            text = "\n".join(texts)
    elif file_path.lower().endswith('.txt'):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        # Image file – rely on Tesseract via pytesseract.
        text = pytesseract.image_to_string(Image.open(file_path))
        if not text.strip():
            raise Exception("No text could be extracted from image.")
    return text

def _select_merchant(lines) -> str:
    """Heuristic to choose the merchant line.
    - Prefer early lines (first 5) that are not dates, totals, tax, or obvious address lines.
    - Reject lines containing digits mixed with typical street keywords.
    - Reject lines that look like cashier or staff identifiers.
    - Return the first suitable line, falling back to the first non‑empty line.
    """
    address_keywords = [
        "street", "st.", "road", "rd.", "ave", "avenue", "blvd", "boulevard",
        "lane", "ln", "park", "floor", "unit", "suite", "#",
    ]
    staff_keywords = ["cashier", "clerk", "server", "waiter", "attendant"]
    for line in lines[:5]:
        low = line.lower()
        # Skip obvious date lines
        if re.search(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", low):
            continue
        # Skip total/tax lines
        if re.search(r"\btotal\b|\bgrand total\b|\btax\b|\bgst\b", low):
            continue
        # Skip address‑like lines (contains digits and address keyword)
        if any(kw in low for kw in address_keywords) and re.search(r"\d", low):
            continue
        # Skip staff lines like cashier
        if any(kw in low for kw in staff_keywords):
            continue
        # Accept lines with alphabetic characters.
        if re.search(r"[a-zA-Z]", line):
            return line.strip()
    # Fallback – first non‑empty line
    return next((l.strip() for l in lines if l.strip()), "Unknown")

def _parse_date(date_str: str) -> str:
    """Parse a date string with day‑first preference.
    Returns ISO YYYY‑MM‑DD or empty string on failure.
    Reject impossible dates and future years.
    """
    # Accept common separators.
    date_str = date_str.strip()
    formats_dayfirst = ["%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y", "%d.%m.%y"]
    formats_yearfirst = ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]
    for fmt in formats_dayfirst + formats_yearfirst:
        try:
            dt = datetime.strptime(date_str, fmt)
        except ValueError:
            continue
        # Reject dates beyond current year.
        if dt.year > datetime.now().year:
            continue
        # Reject impossible calendar dates (datetime.strptime already does).
        return dt.strftime("%Y-%m-%d")
    return ""

def _extract_dates(lines) -> str:
    """Find the first valid date in the receipt lines.
    Uses _parse_date on each candidate.
    """
    # Regex captures both day-first (DD/MM/YYYY) and year-first (YYYY-MM-DD) patterns.
    date_regex = r"\b(\d{1,4}[./-]\d{1,2}[./-]\d{1,4})\b"
    for line in lines:
        for match in re.findall(date_regex, line):
            norm = _parse_date(match)
            if norm:
                return norm
    return "Unknown"

def _extract_amount(lines) -> str:
    """Extract the total amount.
    Preference order:
    1. Lines containing keywords (total, grand total, amount due) – take the last number.
    2. Fallback to the largest numeric value that looks like a monetary amount, ignoring phone‑like patterns.
    Returns a string with two decimal places or "0.0".
    """
    amount_regex = r"([0-9]+(?:[.,][0-9]{2}))"
    # First pass – look for explicit total amount lines, then generic total keywords.
    # Prioritize lines containing "total amount" exactly to avoid matching "subtotal".
    for line in lines:
        if re.search(r"\btotal amount\b", line, re.IGNORECASE):
            nums = re.findall(amount_regex, line.replace(",", "."))
            if nums:
                return f"{float(nums[-1]):.2f}"
    # Fallback to generic total keywords (total, grand total, amount due) as whole words.
    for line in lines:
        if re.search(r"\btotal\b|\bgrand total\b|\bamount due\b", line, re.IGNORECASE):
            nums = re.findall(amount_regex, line.replace(",", "."))
            if nums:
                return f"{float(nums[-1]):.2f}"
    # Second pass – gather numeric candidates.
    candidates = []
    for line in lines:
        # Skip lines that look like phone numbers or dates.
        if re.search(r"\d{2,4}[./-]\d{2,4}[./-]\d{2,4}", line):
            continue
        for num in re.findall(amount_regex, line.replace(",", ".")):
            # Exclude isolated 4‑digit numbers likely to be phone parts.
            if len(num.split(".")[0]) > 4:
                continue
            candidates.append(float(num))
    if candidates:
        return f"{max(candidates):.2f}"
    return "0.0"

def extract_fields(file_path: str) -> Dict[str, str]:
    """Extract merchant, date, amount, category, and confidence from a receipt.
    Returns a dict with string values; category defaults to "Unknown" and confidence to "0.0" (placeholder).
    """
    text = _read_text(file_path)
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    if not lines:
        return {"merchant": "Unknown", "date": "Unknown", "amount": "0.0", "category": "Unknown", "confidence": "0.0"}
    merchant = _select_merchant(lines)
    date = _extract_dates(lines)
    amount = _extract_amount(lines)
    # Category detection is out of scope – keep placeholder.
    return {
        "merchant": merchant,
        "date": date,
        "amount": amount,
        "category": "Unknown",
        "confidence": "0.0"  # Placeholder – not a measured confidence score.
    }
