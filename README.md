# Veriflow
### Expense Reimbursement & Document Verification System


Veriflow is a web application that helps organizations manage expense reimbursement requests, verify supporting documents, and handle approval workflows.

Users can submit expense claims with receipts or other supporting documents. The system extracts key information from uploaded documents, checks for missing or mismatched details, and helps reviewers make informed decisions. It also includes an AI-assisted correction feature that drafts messages when a claim needs additional information or changes.

## Features

- **Expense Claim Submission:** Create reimbursement requests and upload supporting documents.
- **OCR-Based Data Extraction:** Extract merchant names, dates, and amounts from receipts.
- **Automated Verification:** Identify missing fields and inconsistencies between claims and documents.
- **Review and Approval Workflow:** Allow reviewers to inspect claims, request corrections, approve requests, or reject them.
- **Intelligent Correction Assistant:** Draft correction messages based on failed verification checks, with the option for reviewers to edit them.
- **Claim Q&A:** Answer questions about claims using information available in the application.
- **OCR Evaluation Dashboard:** View extraction results and error cases from the SROIE dataset subset.

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| Database | SQLite, SQLAlchemy |
| OCR | PyTesseract, regex-based extraction |
| AI Integration | Google Gemini API |

## Getting Started

### Prerequisites

Install the following:

- Python
- Node.js and npm
- Tesseract OCR
- A Google Gemini API key for AI-assisted features

### 1. Start the Backend

Open a terminal in the project directory:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
$env:GEMINI_API_KEY="your_key"
uvicorn main:app --port 8000 --reload
```

Replace `your_key` with your own Gemini API key. Keep the key private and do not commit it to GitHub.

If the virtual environment does not exist, create it and install the dependencies using the project's dependency files.

### 2. Start the Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL displayed by Vite in the terminal.

## Demo Accounts

The application supports two roles:

- **Submitter:** `submitter_demo`
- **Reviewer:** `reviewer_demo`

If these accounts are not present in the local database, they may need to be created through the `/users/` API endpoint according to the application's authentication requirements.

## Environment Variables

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Enables Gemini-powered claim Q&A and correction assistance. |

Store credentials in environment variables rather than hardcoding them in source files.

## Testing

Run the backend tests from the `backend` directory:

```powershell
python -m pytest tests/ -v
```

Run the end-to-end workflow verification script from the project root:

```powershell
python verify_workflow.py
```

Build the frontend from the `frontend` directory:

```powershell
npm run build
```

These commands help verify backend behavior, reimbursement workflows, and frontend build compatibility.

## OCR Evaluation

The project includes an OCR evaluation using a held-out synthetic dataset. The reported results are:

- **Amount extraction accuracy:** 87% on clear documents.
- **Date extraction accuracy:** 92% on clear documents.

Results may vary with image quality, receipt layout, and formatting. These figures apply to the evaluated dataset and do not guarantee the same accuracy on all real-world documents.

See [`docs/evaluation.md`](docs/evaluation.md) for further details.

## Current Limitations

- The OCR pipeline currently relies on PyTesseract and regex-based extraction because PaddlePaddle was unavailable in the development environment.
- Poor image quality and unusual receipt layouts may affect extraction accuracy.
- The frontend needs further development before production deployment.
- Additional testing with real-world documents and a production-ready deployment setup are still required.

## Project Structure

```text
.
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── ocr.py
│   └── llm.py
├── frontend/
│   └── src/
├── docs/
│   ├── evaluation.md
│   └── requirements-checklist.md
├── scripts/
└── verify_workflow.py
```

## Documentation

- [OCR Evaluation](docs/evaluation.md)
- [Requirements Checklist](docs/requirements-checklist.md)

## About the Project

Veriflow explores how document extraction, automated verification, and AI-assisted communication can make expense reimbursement reviews more consistent and easier to manage.

Developed as part of **Buildathon 2.0**.
