# AI/ML & Dataset Evaluation Report

## AI/ML Component Justification
**Pretrained Learned Component:** This project utilizes **Tesseract OCR (v5+)**, which natively employs a pretrained Long Short-Term Memory (LSTM) neural network for character recognition. This strictly satisfies the PS requirement for a pretrained learned component performing automatic extraction.

## Dataset Information
- **Dataset Name/Source:** D1: SROIE datasetv2 (Scanned Receipt OCR and Information Extraction) from ICDAR 2019 Robust Reading Challenge.
- **Licence/Access Note:** Licensed for academic and non-commercial research purposes.
- **Train/Development vs Held-Out Separation:** The \SROIE2019/train\ subset was entirely ignored. We exclusively used the \SROIE2019/test\ subset, randomly selecting 20 documents strictly as a held-out evaluation set. These were NEVER used to tune the regex normalizers.
- **Exact Number of Evaluation Documents:** 20 documents.
- **Original Source IDs:** Maintained identically (e.g., \X00016469670\, \X51005230621\).
- **Fields Evaluated:** Merchant (company), Date (date), Amount (total).
- **Labels/Ground Truth Used:** Original unmodified JSON labels from \SROIE2019/test/entities/\.
- **Normalization Rules:**
  - Merchant: Lowercased, stripped of punctuation and excess whitespace.
  - Date: Standardized to \YYYY-MM-DD\ via python \datetime.strptime\.
  - Amount: Stripped of currency symbols, letters, and commas, cast to \loat\.

## Real Evaluation Results
*(Executed natively via \pytesseract\ using the LSTM engine)*
- **Merchant Exact Accuracy:** 0/20 (0%)
- **Merchant Normalized Accuracy:** 0/20 (0%)
- **Date Exact Accuracy:** 0/20 (0%)
- **Date Normalized Accuracy:** 3/20 (15%)
- **Amount Exact/Normalized Accuracy:** 3/20 (15%)
- **Extraction Failures:** 0 complete unreadable failures (Tesseract processed all images).
- **Representative Errors (Missing/Wrong Fields):** 
  - \wrong merchant\: expected "OJC MARKETING SDN BHD", extracted "Unknown".
  - \wrong amount\: expected "193.00", extracted "0.0".
- **Missing-Field Errors:** Naive regex parsing over the raw OCR block frequently results in missing/unpaired fields (defaulting to "Unknown" or "0.0"), triggering our fallback Human-in-the-Loop workflows.

## Workflow Integration & Synthetic Data Disclosure
- **Correction Cases:** When OCR yields "0.0" (as seen in 85% of SROIE cases), the verification engine flags the claim as \INCONSISTENT\. Reviewers are forced to manually correct the extracted field, preserving both the original OCR output and the human correction.
- **Synthetic Anomaly Disclosure:** The 25 fictional application cases inside \eimbursement.db\ (used for UI demonstrations) are entirely synthetic anomaly cases. **These 25 synthetic cases DO NOT represent OCR accuracy and are NOT part of the AI evaluation.**
