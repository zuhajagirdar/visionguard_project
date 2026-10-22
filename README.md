# Veriflow

### Intelligent Expense Reimbursement & Document Verification System

Veriflow is a full-stack document verification and expense approval platform designed to streamline reimbursement workflows. It automates receipt extraction, validates expense details against uploaded documents, tracks version history, and assists reviewers with grounded AI-powered suggestions.

---

## Key Features

1. **Expense Claim Management**
   - Create reimbursement requests with merchant, date, amount, category, and description.
   - Real-time status tracking (`Draft`, `Submitted`, `Under Review`, `More Information Required`, `Approved`, `Rejected`, `Processing Failed`, `Withdrawn`).

2. **Document Upload & Version History**
   - Supports **PDF**, **PNG**, **JPG**, and **JPEG** formats (enforced max 10 MB).
   - Document replacement preserves prior versions in an immutable history with timestamps and uploader audit trails.

3. **Automated OCR & Verification Checks**
   - Extracts merchant names, transaction dates, and total amounts using `pdfplumber`, `pytesseract`, and pattern heuristics.
   - Runs verification checks:
     - **Amount Consistency**: Checks form amount against document extracted amount.
     - **Date Consistency**: Verifies receipt date matches claim date and flags future dates.
     - **Required Fields**: Detects missing or unreadable essential information.
     - **Format & Legibility**: Flags corrupt or unreadable files into `Processing Failed` status for manual reviewer triage.

4. **Human-in-the-Loop Review & Corrections**
   - **Reviewer Field Corrections**: Reviewers can edit extracted values while preserving original OCR values.
   - **Request Correction**: Reviewers can return claims with required action notes.
   - **Submitter Resubmission**: Submitters can update fields or upload replacement documents and resubmit.
   - **Role Separation**: Distinct roles for `Submitter`, `Reviewer`, and `Approver`. Strict enforcement prevents submitters from approving their own claims.

5. **AI Assistant & Correction Drafts (Gemini Integration)**
   - Built with the modern `google-genai` SDK (`gemini-2.0-flash`).
   - Generates grounded correction messages based on extraction values and verification failures.
   - Answers reviewer questions strictly using ground-truth evidence available in the request.
   - **Graceful Fallback**: When `GEMINI_API_KEY` is not configured, the system returns clear offline notices without crashing or fabricating responses.

6. **Dashboard & Traceability**
   - Metrics for pending, approved, rejected, and correction-required claims.
   - Aggregated analytics on frequent missing or unreadable fields.
   - Complete audit trail logging every actor, state change, timestamp, and review reason.

---

## Tech Stack

| Component | Technology |
|---|---|
| **Frontend** | React 19, Vite, Tailwind CSS, Lucide React, React Router |
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, SQLite, Pydantic v2 |
| **Document Processing** | PyTesseract, pdfplumber, Pillow, ReportLab |
| **AI Integration** | Google GenAI SDK (`google-genai`) |
| **Testing** | Pytest, FastAPI TestClient, Requests |

---

## Getting Started

### Prerequisites

- **Python**: Version 3.11 or higher
- **Node.js**: Version 18 or higher (with npm)
- **Tesseract OCR** *(Optional)*: Required for image-based OCR; PDF text extraction operates directly via `pdfplumber`.

---

### 1. Backend Setup & Startup

From the project root directory:

```powershell
# Set optional Gemini API key (keep your key private)
$env:GEMINI_API_KEY="your_api_key_here"

# Start the FastAPI backend
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The backend API will be available at `http://127.0.0.1:8000`. Interactive OpenAPI documentation is accessible at `http://127.0.0.1:8000/docs`.

---

### 2. Frontend Setup & Startup

Open a second terminal window:

```powershell
cd frontend
npm install
npm run dev
```

The frontend development server will launch at `http://localhost:5173`.

To verify the production build:
```powershell
cd frontend
npm run build
```

---

## Demo Accounts

The database comes pre-seeded with test accounts across all roles (password is `password` for all accounts):

| Username | Role | Description |
|---|---|---|
| `alice` | Submitter | Standard employee account for submitting claims |
| `alice_sub` | Submitter | Secondary submitter account |
| `bob` | Reviewer | Verification and document review officer |
| `charlie_rev` | Reviewer | Secondary review officer |
| `eve_app` | Approver | Financial authority for final approvals |
| `frank_app` | Approver | Secondary approval officer |

---

## Verification & Testing

Veriflow includes multiple layers of automated testing and validation:

### 1. Backend Pytest Suite (49 tests)
Runs all unit and integration tests for auth, status transitions, OCR heuristics, verifications, versioning, and security:
```powershell
python -m pytest backend/tests/ -v
```

### 2. End-to-End Workflow Verification
Validates multi-step lifecycle transitions, role barriers, resubmissions, and document corruptions:
```powershell
python verify_workflow.py
```

### 3. Live Smoke Test
Executes a 14-step live integration test against the running backend server:
```powershell
python scripts/smoke_test.py
```

### 4. OCR Evaluation
Runs automated field extraction benchmark against the evaluated document subset:
```powershell
python eval/run_evaluation.py
```
Evaluation metrics and error distributions are saved to `eval/results.json`.

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key for GenAI correction assistance and grounded claim Q&A. | Unset (falls back gracefully) |

> **Security Note:** Never commit `.env` files or API keys to the repository. The backend reads secrets exclusively from environment variables.

---

## Repository Structure

```text
.
├── backend/
│   ├── main.py              # FastAPI application endpoints and orchestration
│   ├── models.py            # SQLAlchemy database models
│   ├── schemas.py           # Pydantic v2 schemas and request models
│   ├── database.py          # Database session and SQLite configuration
│   ├── ocr.py               # OCR text extraction and field heuristics
│   ├── llm.py               # Google GenAI SDK integration with fallback
│   ├── gen_test_files.py    # Synthetic test PDF/image generators
│   └── tests/               # 49 unit and integration tests
├── data/
│   └── reimbursement.db     # SQLite database
├── eval/
│   ├── run_evaluation.py    # OCR evaluation runner
│   ├── results.json         # Benchmark output and error cases
│   └── manifest.json        # Evaluation dataset manifest
├── frontend/
│   ├── src/                 # React components, pages, and API client
│   └── package.json         # Frontend dependencies and Vite configuration
├── scripts/
│   └── smoke_test.py        # Live HTTP smoke test script
├── verify_workflow.py       # End-to-end lifecycle verification script
└── README.md
```
