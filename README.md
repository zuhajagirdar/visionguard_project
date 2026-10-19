# Expense Reimbursement System (Buildathon 2.0)

## 1. What was built
This is a full-stack web application designed for Expense Reimbursement / Expense Claim Verification. It allows Submitters to create requests and upload documents, which are automatically processed using OCR to extract key fields (Merchant, Date, Amount). It includes automated verification checks (completeness, field consistency) and routes requests to Reviewers who can approve, reject, or request corrections. 
It integrates grounded GenAI to answer contextual questions about claims and includes an Intelligent Correction Assistant that drafts correction messages based on verification flags.

## 2. How to run it
### Backend (FastAPI + SQLite)
1. Navigate to `backend/`
2. Activate the virtual environment: `.\venv\Scripts\Activate.ps1`
3. Set your API Key: `$env:GEMINI_API_KEY="your_key"`
4. Run the server: `uvicorn main:app --port 8000 --reload`

### Frontend (React + Vite + TailwindCSS)
1. Navigate to `frontend/`
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`

## 3. Demo credentials
- **Submitter:** username `submitter_demo`, role `Submitter`
- **Reviewer:** username `reviewer_demo`, role `Reviewer`
*(Create these via the `/users/` API endpoint on first run if they don't exist in SQLite)*

## 4. Environment variables required
- `GEMINI_API_KEY`: Google Gemini API key for grounded GenAI and the Intelligent Correction Assistant.

## 5. Test results
Run `pytest` in the `backend/` folder to execute unit tests. End-to-end tests demonstrate validation, missing fields catching, and successful/rejected workflow states.

## 6. ML evaluation results
Available in `docs/evaluation.md`. Based on a held-out synthetic dataset, PyTesseract extracted total amounts with 87% accuracy and dates with 92% accuracy on clear documents.

## 7. Innovation implemented
**Intelligent Correction Assistant:** When verification checks fail (e.g., mismatched amount or missing date), the system automatically uses GenAI to draft a contextual correction message to the Submitter. The reviewer can edit this draft before sending, saving time and standardising communication.

## 8. Known limitations
- The OCR currently falls back to regex and PyTesseract due to `paddlepaddle` availability on this environment.
- The UI is a scaffolded React app; a fully flushed-out multi-screen routing setup needs further expansion for production deployment.

## 9. Main files/modules
- `backend/main.py`: FastAPI server and endpoints.
- `backend/models.py`: SQLAlchemy database models (Request, Document, DocumentVersion, ExtractedField, VerificationCheck).
- `backend/ocr.py`: PyTesseract extraction logic.
- `backend/llm.py`: Grounded GenAI connection and Innovation logic.
- `frontend/src/`: React frontend.

## 10. Final requirements checklist
Available in `docs/requirements-checklist.md`.
