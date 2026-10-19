# External Document Dataset: SROIE datasetv2

## Dataset Name and Source
**D1: SROIE datasetv2 (Scanned Receipt OCR and Information Extraction)**
Source: ICDAR 2019 Robust Reading Challenge on SROIE.

## What the Dataset Contains
SROIE contains scanned images of receipts (Task 1 & 2 for text localization/OCR) and ground truth JSON annotations mapping specific values (Task 3 for Key Information Extraction).

## Subset Used
We use **Task 3 (Key Information Extraction)**. We specifically designate 15-20 documents from this subset as the held-out evaluation subset.

## Fields / Labels Used
- company (Mapped to Application merchant)
- date (Mapped to Application expense_date)
- 	otal (Mapped to Application mount)

*Original source IDs (e.g. X51005230616) are preserved in the file names and manifest.*

## Licence / Terms
SROIE is typically licensed for academic/research purposes. You must verify and comply with the original author's licensing terms before usage. 

## Relevance to Project
SROIE perfectly mirrors our Expense Reimbursement use case by providing structurally similar receipt scans with exact extraction targets for merchants, dates, and amounts.

## What this Dataset Does NOT Prove
This external dataset is for MODEL INPUT / EXTRACTION EVALUATION ONLY. It does NOT provide or prove:
- Fictional users, submitters, or reviewers
- Approvals, rejections, or business policies
- Fraud labels or authenticity labels
- Complete reimbursement histories
These application-level records are entirely separate and exist as synthetic demonstration records within our database.

## How to Place the Authorised Dataset
Due to network and licensing restrictions, the dataset is not packaged here.
To run the evaluation, place the authorised files into:
- \data/sroie_subset/img/\ (for \.jpg\ images)
- \data/sroie_subset/key/\ (for \.txt\ ground truth annotations)
