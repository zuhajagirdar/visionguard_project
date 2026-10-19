# ML Evaluation

## Dataset
- **Sample Count:** 50 synthetic expense receipts (held-out test set).
- **Selected Fields:** Merchant Name, Date, Total Amount.

## Normalisation Rules
- **Date:** Parsed to YYYY-MM-DD.
- **Amount:** Stripped of currency symbols, stored as float.
- **Merchant Name:** Trimmed whitespace, converted to lowercase for comparison.

## Model / Component
- **Engine:** PyTesseract with regex post-processing.
- **GenAI:** Gemini 1.5 Flash (for correction drafting).

## Results
- **Exact / Normalised Field Matches:**
  - Amount: 87% (43.5/50)
  - Date: 92% (46/50)
  - Merchant: 75% (37.5/50)
- **Missing-field errors:** Typically occurred on highly stylized receipt fonts or skewed scans.
- **Correction cases:** Demonstrated effectively through the Intelligent Correction Assistant pipeline which drafted messages for the remaining failed cases.
