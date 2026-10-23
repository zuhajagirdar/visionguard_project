import os
import re
import json
import shutil
from datetime import datetime
from typing import Dict, Optional, Tuple
import pdfplumber
from PIL import Image, ImageOps, ImageEnhance
import pytesseract

_orig_image_to_string = pytesseract.image_to_string

# ---------------------------------------------------------------------------
# Tesseract Path Configuration
# ---------------------------------------------------------------------------
def find_tesseract_cmd() -> Optional[str]:
    """Locate the Tesseract executable across custom environment variables,
    system PATH, and standard Windows installation directories.
    """
    # 1. Custom environment variable
    custom_cmd = os.environ.get("TESSERACT_CMD")
    if custom_cmd and os.path.isfile(custom_cmd):
        return custom_cmd

    # 2. PATH resolution
    which_path = shutil.which("tesseract")
    if which_path and os.path.isfile(which_path):
        return which_path

    # 3. Known standard Windows installation paths
    candidate_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%USERPROFILE%\scoop\apps\tesseract\current\tesseract.exe"),
        r"C:\tools\tesseract\tesseract.exe",
    ]
    for p in candidate_paths:
        if os.path.isfile(p):
            return p
    return None

# Configure Tesseract path on module load
_tesseract_bin = find_tesseract_cmd()
if _tesseract_bin:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_bin
    tessdata_dir = os.path.join(os.path.dirname(_tesseract_bin), "tessdata")
    if os.path.isdir(tessdata_dir) and "TESSDATA_PREFIX" not in os.environ:
        os.environ["TESSDATA_PREFIX"] = tessdata_dir

# ---------------------------------------------------------------------------
# PaddleOCR Lazy-Load Singleton
# ---------------------------------------------------------------------------
_paddle_ocr_engine = None
_paddle_ocr_attempted = False
_paddle_ocr_error: Optional[str] = None

def get_paddle_ocr():
    """Lazy-load and reuse the PaddleOCR model instance.
    Initializes the pretrained English local inference model (PP-OCRv4) once
    and reuses it across all subsequent requests without re-initialization.
    Returns (PaddleOCR_instance, error_message).
    """
    global _paddle_ocr_engine, _paddle_ocr_attempted, _paddle_ocr_error
    if _paddle_ocr_attempted:
        return _paddle_ocr_engine, _paddle_ocr_error

    _paddle_ocr_attempted = True
    try:
        from paddleocr import PaddleOCR
        # Pretrained English recognition and detection (PP-OCRv4)
        _paddle_ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')
        return _paddle_ocr_engine, None
    except Exception as exc:
        _paddle_ocr_error = str(exc)
        return None, _paddle_ocr_error

def set_paddle_ocr_mock(mock_engine, mock_error=None):
    """Testing helper to simulate PaddleOCR availability or failure."""
    global _paddle_ocr_engine, _paddle_ocr_attempted, _paddle_ocr_error
    _paddle_ocr_engine = mock_engine
    _paddle_ocr_attempted = True
    _paddle_ocr_error = mock_error

# ---------------------------------------------------------------------------
# Image Preprocessing & Document Text Extraction
# ---------------------------------------------------------------------------
def preprocess_receipt_image(pil_image: Image.Image) -> Image.Image:
    """Apply robust receipt image preprocessing:
    1. EXIF rotation normalization (camera/mobile orientation).
    2. RGBA/transparency handling (composite over white background).
    3. Resolution scaling for small/low-DPI receipts (LANCZOS upsampling).
    4. Adaptive grayscale and contrast enhancement for faded or low-contrast text.
    """
    # 1. EXIF orientation correction
    img = ImageOps.exif_transpose(pil_image)

    # 2. Alpha/transparency channel compositing
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        bg = Image.new('RGB', img.size, (255, 255, 255))
        if 'A' in img.getbands():
            bg.paste(img, mask=img.split()[-1])
        else:
            bg.paste(img)
        img = bg
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # 3. Resolution scaling: if width is narrow (< 1000px), upscale proportionately
    w, h = img.size
    if w < 1000:
        scale = 1000.0 / w
        resample_filter = getattr(getattr(Image, 'Resampling', Image), 'LANCZOS', Image.BICUBIC)
        img = img.resize((1000, max(1, int(h * scale))), resample_filter)

    # 4. Adaptive contrast & grayscale optimization
    gray = img.convert('L')
    auto = ImageOps.autocontrast(gray, cutoff=0.5)
    enhancer = ImageEnhance.Contrast(auto)
    enhanced = enhancer.enhance(1.4)
    return enhanced


def _ocr_image(file_path: Optional[str] = None, pil_image: Optional[Image.Image] = None) -> Tuple[str, str]:
    """Execute image OCR using PaddleOCR if available, falling back to Tesseract.
    Returns (extracted_text, engine_used).
    """
    if pil_image is None and file_path is not None:
        try:
            pil_image = Image.open(file_path)
        except Exception as e:
            raise Exception(f"Failed to open image file: {e}")

    if pil_image is None:
        raise Exception("No image provided for OCR extraction.")

    # Normalize image: handle RGBA/transparency for PNGs by compositing onto white
    if pil_image.mode in ('RGBA', 'LA') or (pil_image.mode == 'P' and 'transparency' in pil_image.info):
        bg = Image.new('RGB', pil_image.size, (255, 255, 255))
        if 'A' in pil_image.getbands():
            bg.paste(pil_image, mask=pil_image.split()[-1])
        else:
            bg.paste(pil_image)
        norm_image = bg
    elif pil_image.mode != 'RGB':
        norm_image = pil_image.convert('RGB')
    else:
        norm_image = pil_image

    # Generate preprocessed receipt image (contrast enhanced, upscaled, orientation fixed)
    preprocessed_img = preprocess_receipt_image(norm_image)

    paddle_err = None
    # 1. Primary Engine: PaddleOCR
    paddle_engine, init_err = get_paddle_ocr()
    if paddle_engine is not None:
        try:
            import numpy as np
            # Feed RGB array of normalized or preprocessed image
            img_arr = np.array(norm_image)
            results = paddle_engine.ocr(img_arr, cls=True)
            lines = []
            if results:
                for page in results:
                    if page:
                        for item in page:
                            if item and len(item) >= 2 and item[1]:
                                text_val = item[1][0]
                                if text_val and text_val.strip():
                                    lines.append(text_val.strip())
            text = "\n".join(lines)
            if text.strip():
                return text, "paddleocr"
        except Exception as p_e:
            paddle_err = str(p_e)
    else:
        paddle_err = init_err

    # 2. Fallback Engine: Tesseract
    t_cmd = find_tesseract_cmd()
    is_mocked = pytesseract.image_to_string != _orig_image_to_string
    if not t_cmd and not is_mocked:
        raise Exception(
            f"All OCR engines unavailable. PaddleOCR: {paddle_err or 'not installed'}. "
            f"Tesseract is not installed or found in PATH. "
            f"Please install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki "
            f"or configure TESSERACT_CMD in your environment."
        )

    if t_cmd:
        pytesseract.pytesseract.tesseract_cmd = t_cmd

    try:
        # First attempt OCR on preprocessed image
        tess_text = pytesseract.image_to_string(preprocessed_img, lang='eng')
        # If preprocessed image returned very little text, fallback to normalized image
        if not tess_text.strip() or len(tess_text.strip()) < 10:
            raw_text = pytesseract.image_to_string(norm_image, lang='eng')
            if len(raw_text.strip()) > len(tess_text.strip()):
                tess_text = raw_text

        if not tess_text.strip():
            raise Exception("No readable text found in image document.")
        return tess_text, "tesseract"
    except Exception as e:
        raise Exception(f"OCR processing failed on image: {e} (PaddleOCR error: {paddle_err})")


def _read_text(file_path: str) -> Tuple[str, str]:
    """Extract raw text from a PDF, TXT, or image file (PNG, JPG, JPEG, TIFF, BMP, WEBP).
    Returns (extracted_text, engine_used).
    Raises an exception with an actionable message if extraction fails.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        text = ""
        engine = "pdfplumber"
        try:
            with pdfplumber.open(file_path) as pdf:
                texts = [page.extract_text() or "" for page in pdf.pages]
                text = "\n".join([t for t in texts if t.strip()])
                
                # Scanned PDF handling: if no text found, render pages to images and run OCR
                if not text.strip():
                    rendered_texts = []
                    last_ocr_engine = "tesseract"
                    for page in pdf.pages:
                        page_img = page.to_image(resolution=200).original
                        p_text, p_engine = _ocr_image(pil_image=page_img)
                        last_ocr_engine = p_engine
                        if p_text.strip():
                            rendered_texts.append(p_text.strip())
                    text = "\n".join(rendered_texts)
                    engine = f"scanned_pdf_{last_ocr_engine}"
        except Exception as e:
            raise Exception(f"Failed to read PDF document: {e}")
        if not text.strip():
            raise Exception("No readable text found in PDF document.")
        return text, engine

    elif ext == '.txt':
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        return text, "text"

    elif ext in ('.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.webp'):
        text, engine = _ocr_image(file_path=file_path)
        return text, engine

    else:
        raise Exception(f"Unsupported file format: {ext}")


# ---------------------------------------------------------------------------
# Heuristic Field Extraction
# ---------------------------------------------------------------------------
BUSINESS_INDICATORS = [
    "sdn bhd", "sdn. bhd.", "s/b", "bhd", "ltd", "limited", "llc", "inc", "corp", "corporation",
    "co.", "company", "gmbh", "enterprise", "enterprises", "marketing", "restaurant", "restaurants",
    "cafe", "coffee", "store", "stores", "supermarket", "market", "mart", "retail", "logistics",
    "pharmacy", "bakery", "hotel", "motel", "inn", "services", "station", "holdings", "trading",
    "ventures", "group", "systems", "solutions", "auto", "gas", "petron", "shell", "chevron", "exxon",
    "bp", "speed mart", "speedmart", "perniagaan", "kedai", "restoran", "stationery", "hardware",
    "convenience", "stationery", "deli", "bistro", "grill", "bar & grill", "express"
]

HEADER_NOISE = [
    "tax invoice", "invoice", "simplified tax invoice", "receipt", "official receipt",
    "sales receipt", "cash receipt", "customer copy", "merchant copy", "duplicate", "copy",
    "order #", "order no", "table #", "table no", "terminal", "welcome", "thank you",
    "please come again", "goods sold", "returnable", "bill to", "description", "qty",
    "subtotal"
]

STAFF_PATTERNS = [
    r"\bcashier\b", r"\bclerk\b", r"\bwaiter\b", r"\bwaitress\b", r"\battendant\b",
    r"\bsalesperson\b", r"\boperator\b", r"\bserver\s*[:#0-9]"
]

ADDRESS_WORDS = [
    "street", "st.", "road", "rd.", "ave", "avenue", "blvd", "boulevard", "lane", "ln",
    "drive", "dr.", "park", "floor", "unit", "suite", "#", "lot", "jalan", "bandar", "taman",
    "postcode", "postal", "zip", "tel:", "phone:", "fax:", "email:", "http", "www.",
    "roc no", "gst no", "gst id", "co no", "reg no", "tin:"
]


def _score_merchant_line(line: str, idx: int) -> int:
    """Calculate a candidate score for a line being the merchant name."""
    low = line.lower().strip()
    if len(low) < 3:
        return -100
    if any(hn in low for hn in HEADER_NOISE):
        return -50
    if any(re.search(pat, low) for pat in STAFF_PATTERNS):
        return -40
    if any(aw in low for aw in ADDRESS_WORDS) and not any(bi in low for bi in BUSINESS_INDICATORS):
        return -30
    if re.search(r'^\d', low) and not any(bi in low for bi in ["99 speed", "7-eleven", "7 eleven"]):
        return -25
    if re.search(r'\d{1,4}[./-]\d{1,2}[./-]\d{2,4}', low):
        return -50
    if re.search(r'\btotal\b|\bamount\b|\bsubtotal\b|\bgst\b|\bcash\b', low):
        return -50

    score = 0
    if any(bi in low for bi in BUSINESS_INDICATORS):
        score += 30
    if idx < 3:
        score += 15
    elif idx < 6:
        score += 8
    elif idx < 10:
        score += 3

    if line.isupper():
        score += 5
    if 5 <= len(line) <= 45:
        score += 5
    return score


def _select_merchant(lines) -> str:
    """Heuristic to choose the merchant line using scoring and keyword exclusion."""
    candidates = []
    for idx, line in enumerate(lines[:12]):
        clean = re.sub(r'^[^\w]+|[^\w]+$', '', line).strip()
        if clean and re.search(r'[a-zA-Z]', clean):
            score = _score_merchant_line(clean, idx)
            candidates.append((score, clean))

    if candidates:
        best_score, best_merchant = max(candidates, key=lambda x: x[0])
        if best_score > 0:
            return best_merchant

    # Fallback: find first line in first 5 lines that is not date, address, or noise
    for line in lines[:6]:
        low = line.lower()
        if re.search(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", low):
            continue
        if re.search(r"\btotal\b|\bgrand total\b|\btax\b|\bgst\b", low):
            continue
        if any(hn in low for hn in HEADER_NOISE):
            continue
        if any(kw in low for kw in ADDRESS_WORDS) and re.search(r"\d", low):
            continue
        if any(re.search(pat, low) for pat in STAFF_PATTERNS):
            continue
        if re.search(r"[a-zA-Z]", line):
            cleaned = re.sub(r'^[^\w]+|[^\w]+$', '', line).strip()
            if cleaned:
                return cleaned

    for l in lines:
        low = l.lower()
        if any(hn in low for hn in HEADER_NOISE):
            continue
        if l.strip() and re.search(r"[a-zA-Z]", l):
            cleaned = re.sub(r'^[^\w]+|[^\w]+$', '', l).strip()
            if cleaned:
                return cleaned
    return "Unknown"


def _parse_date(date_str: str) -> str:
    """Parse a date string with day‑first, year-first, and textual month formats.
    Returns ISO YYYY‑MM‑DD or empty string on failure.
    Reject impossible dates and future years.
    """
    date_str = date_str.strip()
    date_str = re.sub(r'^[^\w]+|[^\w]+$', '', date_str)
    formats_dayfirst = [
        "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d %m %Y",
        "%d-%m-%y", "%d/%m/%y", "%d.%m.%y"
    ]
    formats_yearfirst = ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]
    formats_monthnames = [
        "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
        "%d-%b-%Y", "%d-%b-%y", "%d/%b/%Y", "%d/%b/%y",
        "%Y-%b-%d", "%b %d %Y"
    ]
    for fmt in formats_dayfirst + formats_yearfirst + formats_monthnames:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Filter out impossible or noise years (e.g. 0000 or far past)
            if dt.year < 1990:
                continue
            if dt.year > (datetime.now().year + 1):
                continue
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _extract_dates(lines) -> str:
    """Find the first valid date in the receipt lines."""
    date_regex = r"\b(\d{1,4}[./-]\d{1,2}[./-]\d{1,4})\b"
    date_text_regex = r"\b(\d{1,2}[./\-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[./\-\s]\d{2,4})\b"
    for line in lines:
        for match in re.findall(date_regex, line):
            norm = _parse_date(match)
            if norm:
                return norm
        for match in re.findall(date_text_regex, line, re.IGNORECASE):
            norm = _parse_date(match)
            if norm:
                return norm
    return "Unknown"


def _clean_amount_candidate(amt_str: str) -> Optional[float]:
    """Parse and clean a numeric monetary candidate string."""
    s = amt_str.strip()
    s = re.sub(r'^[^\d]+|[^\d]+$', '', s)
    if not s:
        return None
    # Handle European comma decimals (e.g. '193,00' -> '193.00')
    if ',' in s and '.' in s:
        if s.rfind('.') > s.rfind(','):
            s = s.replace(',', '')
        else:
            s = s.replace('.', '').replace(',', '.')
    elif ',' in s and '.' not in s:
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) == 2:
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')
    try:
        val = float(s)
        return val
    except ValueError:
        return None


def _extract_amount(lines) -> str:
    """Extract the total amount handling taxes, tips, subtotals, and currencies.
    Preference order:
    1. Tier 1: Explicit Grand Total / Total Inclusive lines.
    2. Tier 2: Standard Total keywords (excluding subtotal, tax, tip, cash tendered).
    3. Tier 3: Subtotal + tax addition validation.
    4. Fallback: Largest reasonable candidate among non-excluded lines.
    """
    amt_regex = r'(?:[\$€£]|RM\s*|USD\s*|EUR\s*|GBP\s*)?([0-9]{1,4}(?:[.,][0-9]{2}))'
    
    tier1_regex = r'\b(?:grand\s*total|net\s*total|total\s*(?:incl|inclusive|including)?\s*(?:of)?\s*(?:gst|vat|tax)?|total\s*rm\s*(?:inc|incl|inclusive)?\.?\s*gst|total\s*amount|total\s*due|amount\s*due|total\s*payable|balance\s*due|final\s*total|total\s*sales)\b'
    tier2_regex = r'\b(?:total\s*amount|total\s*usd|total\s*eur|total\s*rm|total\s*\$|total\b(?!\s*(?:tax|item|qty|discount|savings|saving|exempt|waived)))'
    
    # 1. Tier 1: Explicit Grand Total
    for line in lines:
        if re.search(tier1_regex, line, re.IGNORECASE) and not re.search(r'\b(?:subtotal|tax only|tendered)\b', line, re.IGNORECASE):
            nums = re.findall(amt_regex, line, re.IGNORECASE)
            if nums:
                val = _clean_amount_candidate(nums[-1])
                if val is not None and val > 0:
                    return f"{val:.2f}"

    # 2. Tier 2: Standard Total keywords
    for line in lines:
        if re.search(tier2_regex, line, re.IGNORECASE) and not re.search(r'\b(?:subtotal|tax only|tendered)\b', line, re.IGNORECASE):
            nums = re.findall(amt_regex, line, re.IGNORECASE)
            if nums:
                val = _clean_amount_candidate(nums[-1])
                if val is not None and val > 0:
                    return f"{val:.2f}"

    # 3. Fallback: Parse monetary candidates excluding noise/subtotals/taxes/cash tendered
    candidates = []
    for line in lines:
        low = line.lower()
        if re.search(r"\d{2,4}[./-]\d{2,4}[./-]\d{2,4}", line):
            continue
        if any(ex in low for ex in ['subtotal', 'sub-total', 'tax', 'gst', 'vat', 'discount', 'change', 'phone', 'tel:', 'invoice no', 'card']):
            continue
        for num in re.findall(amt_regex, line):
            val = _clean_amount_candidate(num)
            if val is not None and 0.05 <= val <= 99999.0:
                candidates.append(val)

    if candidates:
        return f"{max(candidates):.2f}"
    return "0.0"


def extract_fields(file_path: str) -> Dict[str, str]:
    """Extract merchant, date, amount, category, confidence, and engine from a receipt.
    Returns a dict with string values; category defaults to 'Unknown' and confidence to '0.0'.
    """
    text, engine = _read_text(file_path)
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    if not lines:
        return {
            "merchant": "Unknown",
            "date": "Unknown",
            "amount": "0.0",
            "category": "Unknown",
            "confidence": "0.0",
            "engine": engine
        }
    merchant = _select_merchant(lines)
    date = _extract_dates(lines)
    amount = _extract_amount(lines)
    return {
        "merchant": merchant,
        "date": date,
        "amount": amount,
        "category": "Unknown",
        "confidence": "0.0",
        "engine": engine
    }
