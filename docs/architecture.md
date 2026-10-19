# Architecture

## System Architecture
- **Frontend:** React + Vite, using TailwindCSS for styling. Communicates with the backend via RESTful APIs.
- **Backend:** FastAPI (Python) for handling business logic, user roles, document upload, and integration with ML models.
- **Database:** SQLite with SQLAlchemy ORM.
- **OCR Engine:** PyTesseract (Fallback Regex) for extracting structured data from documents.
- **GenAI/LLM:** Google Gemini API for grounded answering and Intelligent Correction Assistant.

## Database Relationships
- `User` 1:N `Request`
- `Request` 1:N `Document`
- `Document` 1:N `DocumentVersion` (preserves historical edits/uploads)
- `DocumentVersion` 1:N `ExtractedField` (maintains original vs corrected)
- `Request` 1:N `VerificationCheck`

## Security Boundaries
- Submitter can only view and edit their own requests.
- Reviewer handles approvals and verification checks.
- API endpoints strictly enforce these roles. Server-side validation prevents Submitters from self-approving.
