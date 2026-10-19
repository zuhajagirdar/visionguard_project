# Synthetic Application Demo Data

## Overview
This document describes the synthetic demo data seeded into the application for demonstration and presentation purposes. 

**IMPORTANT NOTE:** All users, requests, reviews, decisions, and timestamps inside this dataset are entirely **FICTIONAL AND SYNTHETIC**. They do not represent real individuals, real expenses, or real corporate actions.

## Separation from Problem Statement (PS) Dataset
This synthetic data is structurally independent from the external PS document dataset (e.g., SROIE, CORD).
- **PS Dataset:** Reserved strictly for evaluating the mathematical accuracy of the standalone OCR extraction pipeline. It provides raw images and bounding box truths, but *no* application-level concepts.
- **Synthetic Application Data:** Populates the SQL database (eimbursement.db) to demonstrate the complete lifecycle of our software application. It uses mock extraction strings to simulate the OCR outputs, ensuring the demo environment remains self-contained without needing the heavy 2GB external benchmark files.

## Dataset Profile
- **Total Synthetic Cases:** 25 expense requests.
- **Fictional Users:**
  - Submitters: \lice_sub\, \ob_sub\
  - Reviewers: \charlie_rev\, \david_rev\
  - Approvers: \eve_app\, \rank_app\

## Scenarios Covered
The 25 requests intentionally span the full lifecycle of the state machine to populate the Review Queue, Dashboard metrics, and audit logs:
1. **Draft:** (2) Newly created requests yet to be submitted.
2. **Submitted:** (3) Pending asynchronous processing.
3. **Processing Failed:** (2) Simulating corrupt documents or unreadable image uploads.
4. **Under Review:** (6) Evaluated for verification issues (e.g. inconsistent amount, missing date).
5. **More Information Required:** (4) Sent back to submitters with synthetic Reviewer comments.
6. **Approved:** (5) Fully authorized requests.
7. **Rejected:** (3) Denied requests (e.g., "Out of policy", "Duplicate submission").

## How to Apply
The data is seeded via:
\\\ash
cd backend
python seed_demo_data.py
\\\
*(This drops existing SQL tables and cleanly recreates them with the 25 cases).*
