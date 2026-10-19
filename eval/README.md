# Dataset Integration Evaluation (SROIE Dataset)

## Dataset Name and Source
**D1: SROIE datasetv2 (Scanned Receipt OCR and Information Extraction)**
This dataset originates from the ICDAR 2019 Robust Reading Challenge on SROIE.

## Exact Subset Used
Task 3 (Key Information Extraction). We use a held-out subset of 20 labelled receipt documents for this evaluation. 
These 20 documents must NOT be used for tuning the extraction logic.

## Licence / Usage Note
SROIE is typically used for academic and non-commercial research purposes in OCR. 
*Note on Access:* Due to external authentication/licensing walls on platforms like Kaggle, the dataset archive must be downloaded manually by the user.

## Labels / Ground Truth Available
The dataset provides bounding boxes and a JSON-like text file for each receipt image containing:
- company (mapped to our merchant)
- date (mapped to our expense_date)
- 	otal (mapped to our mount)
- ddress (ignored for our use case)

## Separation from Synthetic Data
- **Real Labelled PS Dataset (Here):** Used strictly to measure the accuracy of the ackend/ocr.py extraction engine. 
- **Synthetic Application Demo Data:** The 25 mock SQL records inside eimbursement.db used for UI/workflow demonstrations. 
*Synthetic demo data does NOT prove OCR accuracy and is kept completely isolated from this evaluation.*

## How to Run the Evaluation

1. **Download the SROIE dataset** (Task 3).
2. **Place the data locally:**
   Extract the images into eval/sroie_data/img/ (e.g. .jpg)
   Extract the ground-truth text files into eval/sroie_data/key/ (e.g. .txt)
3. **Build the Manifest:**
   Run python eval/setup_manifest.py to securely select 20 held-out documents and create eval/manifest.json.
4. **Run the Evaluation:**
   Run python eval/run_eval.py
   This will execute the existing pipeline, generate eval/results.json, and output eval/EVALUATION_REPORT.md.
