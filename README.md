# Veriflow

### Intelligent Document Verification & Expense Reimbursement System

Veriflow is a full-stack, enterprise-grade expense reimbursement and automated document verification platform. It eliminates the manual review bottleneck in financial workflows by extracting structured receipt data, triangulating claimed amounts and dates against uploaded documents, enforcing corporate expense policies, tracking document version history, and assisting reviewers with grounded AI suggestions.

---

## Table of Contents

1. [Overview & Problem Solved](#overview--problem-solved)
2. [Key Capabilities](#key-capabilities)
3. [Technology Stack](#technology-stack)
4. [System Architecture & Components](#system-architecture--components)
5. [End-to-End Workflow](#end-to-end-workflow)
6. [OCR & Document Processing Engine](#ocr--document-processing-engine)
7. [Verification Rules & State Machine](#verification-rules--state-machine)
8. [Authentication, Security & Token Implementation](#authentication-security--token-implementation)
9. [Database Schema & Audit-Log Guarantees](#database-schema--audit-log-guarantees)
10. [AI Assistant & Deterministic Offline Mode](#ai-assistant--deterministic-offline-mode)
11. [Prerequisites & Environment Setup](#prerequisites--environment-setup)
12. [Running the Application](#running-the-application)
13. [Demo Accounts & Development Credentials](#demo-accounts--development-credentials)
14. [Automated Testing & Benchmark Evaluations](#automated-testing--benchmark-evaluations)
15. [Current Limitations & Future Improvements](#current-limitations--future-improvements)

---

## Overview & Problem Solved

Traditional expense reimbursement systems rely heavily on manual human verification. Finance teams manually transcribe receipts, cross-check line items against claim forms, and detect errors or policy violations. This leads to three major problems:
- **Review Fatigue & Fraud Slippage:** Manual reviewers miss subtle discrepancies (e.g., claiming \$1,250 for a \$125 receipt, claiming sales taxes or tips twice, or duplicate submissions).
- **Approval Latency:** Claims sit in review queues for days while reviewers decipher blurry smartphone photos, skewed scans, or foreign currency symbols.
- **The "Blind Automation" Trap:** Naive AI systems that attempt full end-to-end auto-approval without human oversight fail catastrophically when OCR models misread skewed text, read cashier IDs as merchant names, or confuse subtotal lines with grand totals.

**Veriflow solves this dilemma through an evidence-linked, human-in-the-loop verification architecture.** Rather than allowing AI to execute financial payouts autonomously, Veriflow employs local OCR and heuristic extraction to detect mathematical and policy deltas, presenting side-by-side evidence to human reviewers who make the final decision with full audit accountability.

---

## Key Capabilities

1. **Expense Claim Management**
   - Create reimbursement requests with merchant, date, amount, category, and description.
   - Comprehensive state machine tracking: `Draft`, `Submitted`, `Under Review`, `More Information Required`, `Approved`, `Rejected`, `Processing Failed`, and `Withdrawn`.
   - Pre-submission draft synchronization: edits are persisted and verified before status transitions.

2. **Document Upload & Version History**
   - Supports **PDF**, **PNG**, **JPG**, **JPEG**, **TIFF**, **BMP**, and **WEBP** formats (enforced max 10 MB).
   - Document replacement preserves prior versions in a relational history table (`DocumentVersion`), maintaining audit records across resubmissions.
   - Multi-document isolation: allows multiple receipts or invoices per claim, with per-document extraction views and a dedicated document switcher.

3. **Automated OCR & Document Normalization**
   - **Active Engines:** High-speed native digital PDF text extraction via `pdfplumber` (~36 ms) and Tesseract OCR (v5+ with LSTM neural network character recognition) via `pytesseract` for image documents.
   - **Optional Engine:** `PaddleOCR` (PP-OCRv4) lazy-load singleton implemented for Python 3.9–3.13 environments (automatically bypassed on Python 3.14+ where PaddlePaddle binary wheels are unavailable).
   - Image preprocessing pipeline: EXIF rotation correction, Lanczos resolution upscaling for low-DPI receipts, alpha-channel compositing over pure white, and adaptive contrast optimization.
   - Multi-tier regex heuristics handling subtotals, VAT/GST taxes, tips, cash tendered lines, and European comma decimals.

4. **Triangulation Verification Engine**
   - **Amount Consistency:** Verifies claim amount against document total within 1 cent.
   - **Date Consistency & Validity:** Matches receipt date against claim date and flags future dates.
   - **Merchant Consistency:** Normalizes legal entity suffixes (`Inc`, `LLC`, `Sdn Bhd`) and uses string similarity (`difflib`) to detect spelling typos.
   - **High-Value Policy Warning:** Flags claims exceeding the **\$5,000.00 threshold** (`> 5000.0`) for elevated reviewer approval without blocking submission.
   - **Duplicate Claim Detection:** Warns if another request shares the same date, amount, and merchant.
   - **Legibility & Corruption Guard:** Detects corrupted files or unreadable text, routing them to `Processing Failed` for triage.

5. **Human-in-the-Loop Review & Corrections**
   - **Side-by-Side Review:** Embedded live document preview directly adjacent to extracted fields and verification checks.
   - **Field Corrections:** Reviewers can edit misread OCR values while immutably preserving the original machine reading in the database (`original_value` vs. `corrected_value`).
   - **Explicit Decision Controls:** Dedicated action cards for **Approve Claim**, **Reject Claim**, and **Request More Information**.
   - **Mandatory Audit Reasons:** Server-side validation requires written justification for rejections and correction requests, logged permanently in `AuditLog`.
   - **Explicit Form Copy:** Submitters can copy extracted OCR values to the claim form with one click.

6. **Grounded AI Assistant (Google Gemini Integration)**
   - Powered by the modern `google-genai` SDK (`gemini-2.0-flash`) with fallback to `gemini-1.5-flash`.
   - Answers reviewer and submitter questions strictly using ground-truth database evidence.
   - Generates drafted correction messages when claims require more information.
   - **Deterministic Offline Fallback:** When `GEMINI_API_KEY` is not configured, the assistant provides rule-based offline analysis without crashing or hallucinating.

7. **Security & Cryptographic Authentication**
   - PBKDF2-HMAC-SHA256 salted password hashing (100,000 iterations + 16-byte cryptographically secure salts).
   - Server-side Role-Based Access Control (RBAC) preventing Submitters from approving their own claims.
   - Non-destructive database migrations preserving claims and user accounts.

8. **Responsive UI & Viewport Layout**
   - Zero-horizontal-scroll desktop tables using fixed layouts (`table-fixed`) and ellipsis truncation with hover tooltips for long merchant names.
   - Desktop sidebar pinned to viewport height (`sticky top-0 h-screen`) with Logout anchored at the bottom.
   - Full mobile responsive experience with compact card layouts and collapsible drawer navigation on screens under 768px.

---

## Technology Stack

| Layer | Technology | Version | Purpose in Veriflow | Status in Current Environment |
|---|---|---|---|---|
| **Backend Framework** | FastAPI | `^0.110.0` | Asynchronous REST API routing, dependency injection, and OpenAPI documentation. | **Active** |
| **ASGI Server** | Uvicorn | `^0.28.0` | Production ASGI server handling asynchronous HTTP requests. | **Active** |
| **ORM & Database** | SQLAlchemy | `^2.0.28` | Declarative relational database modeling, connection management, and SQLite dialect abstraction. | **Active** |
| **Data Validation** | Pydantic | `^2.7.0` | Request payload validation, response schemas, and date input normalization. | **Active** |
| **Password Hashing** | Python `hashlib` & `secrets` | Standard Library | PBKDF2-HMAC-SHA256 password hashing (100k rounds) with 16-byte random salt, constant-time verification (`compare_digest`). | **Active** |
| **Native PDF Extraction** | pdfplumber | `^0.11.0` | High-speed text and layout extraction from digital vector PDFs (~36 ms). | **Active** |
| **Image OCR (Primary)** | PyTesseract | `^0.3.10` | C++ bindings to Tesseract OCR v5+ LSTM neural network engine. | **Active** |
| **Image OCR (Advanced)** | PaddleOCR | Optional | Lazy-load PP-OCRv4 English recognition and angle classification. | **Optional / Inactive on Python 3.14** *(Supported on Python 3.9–3.13; automatically falls back to Tesseract on Python 3.14+)* |
| **Image Preprocessing** | Pillow (PIL) | `^10.2.0` | EXIF rotation correction, Lanczos upscaling, alpha compositing, and adaptive autocontrast. | **Active** |
| **AI / LLM Integration** | Google GenAI SDK | `^0.1.1` | Gemini 2.0 Flash integration for evidence-grounded review Q&A and correction drafts. | **Active** *(With deterministic offline mode when API key is omitted)* |
| **Frontend Framework** | React | `^19.2.8` | Client-side reactive UI, state management, form drafting, and modal interactions. | **Active** |
| **Frontend Tooling** | Vite | `^8.3.0` | High-speed build tooling and local development HMR server. | **Active** |
| **CSS Architecture** | Tailwind CSS | `^4.3.3` | Utility-first styling, semantic color tokens, responsive breakpoints, and fixed table layouts. | **Active** |
| **Iconography** | Lucide React | `^1.49.0` | Contextual vector icons for status badges, actions, and document formats. | **Active** |
| **Test Automation** | Pytest | `^8.1.0` | Automated regression testing covering RBAC, OCR heuristics, and workflows (73 tests). | **Active** |

---

## System Architecture & Components

```
+-----------------------------------------------------------------------------------+
|                               FRONTEND (React 19 + Vite)                          |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  |     Login Page     |  | Dashboard & Metrics  |  |    Review Queue (RBAC)    |  |
|  | (PBKDF2 Masked UI) |  | (table-fixed / Cards)|  | (Desktop Table & Cards)   |  |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  +-----------------------------------------------------------------------------+  |
|  |             Request Detail Page (Multi-Doc Switcher, Live Preview)          |  |
|  |      [Edit Form] <---> [Verification Badges] <---> [Make Decision Panel]    |  |
|  +-----------------------------------------------------------------------------+  |
+------------------------------------------+----------------------------------------+
                                           | HTTP / REST (Bearer Auth)
+------------------------------------------v----------------------------------------+
|                               FASTAPI BACKEND SERVER                              |
|  +---------------------+  +----------------------+  +--------------------------+  |
|  |   Auth & Security   |  |   Request Lifecycle  |  |   Reviewer Decision API  |  |
|  | (PBKDF2-HMAC-SHA256)|  | (Submit, Resubmit)   |  | (Mandatory Audit Reason) |  |
|  +---------------------+  +----------------------+  +--------------------------+  |
|  +-----------------------------------------------------------------------------+  |
|  |                        Verification Engine State Machine                    |  |
|  |  [Required Rules]  [Amount Delta]  [Date Check]  [Merchant Typo]  [Duplicate] |  |
|  +-----------------------------------------------------------------------------+  |
|  +-----------------------------------------------------------------------------+  |
|  |                    Document Processing & OCR Pipeline                       |  |
|  |  Format Router -> Preprocessing (Lanczos/Contrast) -> OCR Engine -> Heuristics|  |
|  +-----------------------------------------------------------------------------+  |
+------------------------------------+------------------+---------------------------+
                                     |                  |
           +-------------------------v---+          +---v------------------------+
           |       SQLite Database       |          |      Local File System     |
           |  users, requests, documents |          |          uploads/          |
           |  document_versions, fields  |          | (Relational version storage|
           |  verification_checks, audit |          +----------------------------+
           +-----------------------------+
```

### Component Responsibilities

1. **Frontend (`frontend/src/`):** Manages user authentication state, reactive form editing, real-time client validation, live document previewing, multi-document tab switching, and responsive layouts across desktop, tablet, and mobile displays.
2. **FastAPI Gateway (`backend/main.py`):** Enforces authentication via Bearer tokens, validates role permissions server-side, routes CRUD actions, logs audit trail entries, and calculates dashboard analytics.
3. **Security Module (`backend/security.py`):** Handles PBKDF2-HMAC-SHA256 password hashing, salt generation, and constant-time password verification.
4. **Document Processing Pipeline (`backend/ocr.py`):** Identifies file formats, routes native PDFs vs. scanned documents, applies Pillow image preprocessing, executes OCR (Tesseract / PaddleOCR fallback), and parses candidate lines for merchant, date, and amount.
5. **Verification Engine (`backend/main.py:run_verifications`):** Clears previous checks, iterates through active documents and claim details, calculates deltas, evaluates high-value thresholds and duplicate checks, and commits verification check records.
6. **AI Assistant (`backend/llm.py`):** Ingests structured request context (claim values, extractions, verification checks) and queries Gemini 2.0 Flash to answer user questions with strict grounding, or provides deterministic offline analysis.

---

## End-to-End Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Submitter
    participant Client as Frontend (React)
    participant API as Backend (FastAPI)
    participant OCR as OCR & Heuristic Engine
    participant DB as SQLite Database
    actor Reviewer

    Submitter->>Client: Create Claim (Merchant, Date, Amount)
    Client->>API: POST /requests/ (Draft)
    API->>DB: Insert Request (status='Draft')
    
    Submitter->>Client: Upload Receipt (PDF / PNG / JPG)
    Client->>API: POST /requests/{id}/upload
    API->>OCR: Process Document (Preprocessing + OCR)
    OCR->>API: Extracted Merchant, Date, Amount
    API->>DB: Save DocumentVersion & ExtractedField records
    API->>DB: run_verifications() -> Save VerificationCheck records
    API-->>Client: Return updated request & extractions

    Submitter->>Client: Click "Copy Extracted Data to Form" (Optional)
    Submitter->>Client: Click "Submit for Review"
    Client->>API: Save Draft (PUT /requests/{id}) + POST /requests/{id}/submit
    API->>DB: Verify required fields -> Update status to 'Submitted'
    API->>DB: Log AuditLog entry (Draft -> Submitted)

    Note over API,DB: Background transitions status to 'Under Review'
    
    Reviewer->>Client: Open Review Queue & View Request Details
    Client->>API: GET /requests/{id}/details
    API-->>Client: Request details, document versions, extractions, verification checks
    
    opt Field Correction
        Reviewer->>Client: Correct misread OCR field
        Client->>API: POST /requests/{id}/correct_field
        API->>DB: Update corrected_value, keep original_value, rerun verifications
    end

    opt Grounded AI Query
        Reviewer->>Client: Ask AI Assistant about discrepancies
        Client->>API: POST /requests/{id}/ask
        API-->>Client: Grounded answer based strictly on evidence
    end

    Reviewer->>Client: Make Decision (Approve / Reject / More Info) + Comment
    Client->>API: POST /requests/{id}/review {action, reason}
    API->>DB: Validate mandatory reason -> Update status -> Write AuditLog & Comment
    API-->>Client: Return decision confirmation
```

---

## OCR & Document Processing Engine

```
[ Uploaded Document ]
        |
        v
+-------------------+
|  Extension Check  |
+---------+---------+
          |
   +------+------+
   |             |
   v (.pdf)      v (.png, .jpg, .jpeg, .tiff, .bmp, .webp)
+-----------+  +------------------------------------------------+
| pdfplumber|  |           Pillow Image Preprocessing           |
+-----+-----+  | 1. ImageOps.exif_transpose() (Fix Orientation) |
      |        | 2. Composite alpha/transparency over white RGB |
   Text Found? | 3. Lanczos upscaling if width < 1000px         |
     /    \    | 4. ImageOps.autocontrast() + 1.4x Contrast     |
   Yes     No  +-----------------------+------------------------+
   /        \                          |
  v          v                         v
Native     Scanned Page        +---------------+
Text       Rendered (200 DPI)  | Dual OCR Flow |
  |          \                 +-------+-------+
  |           +-------------------> /     \
  |                                v       v
  |                      PaddleOCR (DL)  PyTesseract (LSTM)
  +--------------------------------+-------+
                                   |
                                   v
                      +-------------------------+
                      |   Extracted Text Lines  |
                      +------------+------------+
                                   |
    +------------------------------+-----------------------------+
    |                              |                             |
    v                              v                             v
[ Merchant Selection ]    [ Date Normalization ]      [ Amount Hierarchy ]
Candidate scoring:        20 date pattern formats:    Tier 1: Explicit Grand Total
- Business indicators (+30) Day-first parsing prioritized Tier 2: Total keywords
- Noise exclusions (-50)  Sanity range: 1990 to +1 yr Tier 3: Max candidate fallback
- Staff patterns (-40)    Standardized to YYYY-MM-DD  European comma handling
```

### Technical Implementation References
* **Active Runtime Engine:** On the current Windows Python 3.14 environment, **Tesseract OCR (v5+)** acts as the primary image OCR engine, with `pdfplumber` handling native digital PDFs.
* **PaddleOCR Availability:** The lazy-load singleton `get_paddle_ocr()` is fully implemented and tested with mock fallbacks. However, because upstream PaddlePaddle does not yet distribute binary wheels for Python 3.14+, the system detects this at runtime and defaults to Tesseract without crashing.
* **Path Resolution (`find_tesseract_cmd`):** Discovers Tesseract binaries across custom `TESSERACT_CMD` environment variables, system PATH, and 6 standard Windows directories (Program Files, Local AppData, Scoop).
* **Image Preprocessing (`preprocess_receipt_image`):** Automatically normalizes camera orientation via EXIF metadata, flattens alpha channels, upscales low-DPI receipts under 1,000px, and boosts contrast by 1.4x.
* **Scanned vs. Native Detection (`_read_text`):** Leverages `pdfplumber` to extract digital text in ~36 ms. If zero text is returned (indicating a scanned paper PDF), converts pages to 200 DPI bitmaps and invokes the OCR pipeline.

---

## Verification Rules & State Machine

The verification engine (`backend/main.py:run_verifications`) runs on claim creation, document upload, field correction, and claim editing. It evaluates rules and records discrete entries in the `VerificationCheck` table:

| Rule Name | Checked Conditions | Result Categories | Result Status |
|---|---|---|---|
| **Required Document** | Verifies at least 1 document is attached to the claim. | `valid`, `missing` | `PASS` or `CANNOT DETERMINE` |
| **Required Field** | Verifies `merchant_name`, `expense_date`, and `expense_amount` are provided. | `valid`, `missing` | `PASS` or `CANNOT DETERMINE` |
| **Document Readability** | Checks if any attached document failed OCR extraction. | `valid`, `unreadable` | `PASS` or `CANNOT DETERMINE` |
| **Amount Consistency** | Compares form amount against extracted document total within \$0.01. | `valid`, `inconsistent`, `unreadable` | `PASS`, `INCONSISTENT`, or `CANNOT DETERMINE` |
| **High Value Policy** | Triggers when claim amount **strictly exceeds \$5,000.00** (`> 5000.0`). | `unusual_amount` | `WARNING` |
| **Date Consistency** | Compares form date against extracted document date. | `valid`, `inconsistent`, `unreadable` | `PASS`, `INCONSISTENT`, or `CANNOT DETERMINE` |
| **Date Validity** | Checks if the extracted receipt date is in the future. | `inconsistent` | `WARNING` |
| **Merchant Consistency** | Normalizes business suffixes (`Inc`, `LLC`, `Sdn Bhd`) and compares names. | `valid`, `spelling_mismatch`, `inconsistent` | `PASS`, `WARNING` (if `difflib` similarity >= 65%), or `INCONSISTENT` |
| **Possible Duplicate** | Searches for other requests sharing the same date, amount, and merchant. | `duplicate` | `WARNING` |

---

## Authentication, Security & Token Implementation

### Password Hashing (`backend/security.py`)
* **Algorithm:** Password-Based Key Derivation Function 2 using HMAC with SHA-256 (PBKDF2-HMAC-SHA256).
* **Iterations:** 100,000 rounds.
* **Salt:** Cryptographically secure 16-byte random hex salt per user (`secrets.token_hex(16)`).
* **Storage Format:** Stored in the database as `pbkdf2_sha256$<salt>$<key_hex>`.
* **Timing-Attack Resistance:** Verified via constant-time string comparison (`secrets.compare_digest`).

### Token & Session Architecture
* **Login Endpoint:** `POST /token` receives `username`, `password`, and `role`. It validates the credentials against the database hash.
* **Session Token:** On successful authentication, the server returns an HTTP Bearer token representing the user's primary key ID:
  ```json
  {
    "access_token": "<user_id>",
    "token_type": "bearer",
    "user_id": 1,
    "role": "Submitter",
    "username": "alice_sub"
  }
  ```
* **Server-Side Validation:** The dependency `get_current_user` extracts the user ID from the `Authorization: Bearer <user_id>` header, queries `models.User`, and enforces role permissions server-side on every protected endpoint.
* **Production Recommendation:** For single-node development, this database-backed session token is simple and robust. For multi-server or public production deployments, signed stateless JSON Web Tokens (JWT) with cryptographic expiration (`exp`) and secret key signing are recommended.

### Role Permissions Matrix

| Capability | Submitter | Reviewer | Approver |
|---|:---:|:---:|:---:|
| Create draft claims & upload receipts | Yes | No | No |
| Edit & resubmit returned claims | Yes | No | No |
| Withdraw pending claims | Yes | No | No |
| Copy extracted OCR data to claim form | Yes | Yes | Yes |
| Inspect Review Queue & all claims | No | Yes | Yes |
| Perform OCR field corrections | No | Yes | Yes |
| Trigger OCR re-processing | No | Yes | Yes |
| Request more information with reason | No | Yes | Yes |
| Approve claims | No | Yes | Yes |
| Reject claims with reason | No | Yes | Yes |
| Self-approve own claims | **Blocked** | **Blocked** | **Blocked** |
| Query AI Assistant | Own claims only | All claims | All claims |

---

## Database Schema & Audit-Log Guarantees

Veriflow maintains complete relational traceability across all objects:

```
[ User ]
   | (1:N)
   +-------------------------------------------------------+
   |                                                       |
   v                                                       v
[ Request ] <---+                                     [ AuditLog ]
   | (1:N)      | (1:N)                               (actor, from_status,
   |            +------------------+                   to_status, reason,
   |                               |                   timestamp)
   v                               v
[ Document ]              [ VerificationCheck ]
   | (1:N)                (rule_name, evidence,
   v                       result, category,
[ DocumentVersion ]        timestamp)
   | (1:N)
   v
[ ExtractionRun ] (engine, status, started_at, error_message)
   | (1:N)
   v
[ ExtractedField ] (field_name, original_value, corrected_value,
                    corrected_by_user_id, corrected_at, confidence)
```

### Audit-Log Guarantees & Boundaries
* **What is Guaranteed:** The `AuditLog` table functions as an application-level append-only record in SQLite. Every lifecycle state transition is recorded via `log_audit()`, capturing:
  1. Claim creation (`create`: `None` -> `Draft`)
  2. Submission (`submit`: `Draft` -> `Submitted`)
  3. Document uploads (`upload_document`, recording original filename and version number)
  4. Processing status changes (`start_process`, `process_complete`, `process_fail`)
  5. Review decisions (`approve`, `reject`, `request_correction`, with mandatory reviewer reasons stored in `reason`)
  6. Resubmissions (`resubmit`) and withdrawals (`withdraw`)
  7. Reviewer field corrections (`correct_field`, capturing field name, prior value, and updated value)
* **What is Not Guaranteed:** The audit trail is an internal SQLite database table. It does not provide cryptographic tamper-proofing (such as blockchain hashing or WORM storage). Direct filesystem access to `reimbursement.db` could alter historical rows.

---

## AI Assistant & Deterministic Offline Mode

The AI Assistant (`backend/llm.py`) is designed as a focused document verification aid:
1. **Model Selection:** Uses `gemini-2.0-flash` when the modern `google-genai` SDK is present, and falls back to `gemini-1.5-flash` with the legacy SDK.
2. **Grounded Answering:** When a user asks a question, the backend packages the claim details, attached documents, OCR extractions, and verification checks into a structured evidence prompt.
3. **Safety Constraints:** System instructions strictly forbid the LLM from approving or rejecting claims, fabricating evidence, or honoring prompt injection attempts found in receipts.
4. **Deterministic Offline Fallback:** If `GEMINI_API_KEY` is unset or offline, the assistant invokes `explain_request_findings()`, which parses the actual database records and returns a structured, deterministic analysis covering:
   - Claim form values vs. extracted document values.
   - Exact discrepancies (amount mismatch, date differences, spelling typos).
   - Missing fields and unreadable documents.
   - Recommended next actions based on the current claim status.

---

## Prerequisites & Environment Setup

### Prerequisites
* **Operating System:** Windows 10/11, macOS, or Linux.
* **Python:** Python 3.11, 3.12, 3.13, or 3.14 (Note: Python 3.14 natively uses Tesseract OCR; PaddleOCR runs on Python 3.10–3.13).
* **Node.js:** Node.js 18+ (with npm).
* **Tesseract OCR:** Required for image-based OCR on Windows. Download installer from: [UB-Mannheim Tesseract Releases](https://github.com/UB-Mannheim/tesseract/wiki).

### Environment Variables
Configure environment variables in your terminal or system environment:

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | *(Optional)* Google Gemini API key for online AI assistance. | Unset (uses deterministic offline analysis) |
| `TESSERACT_CMD` | *(Optional)* Absolute path to the Tesseract executable if not in system PATH. | Auto-detected across common paths |
| `DEMO_PASSWORD` | *(Optional)* Development password for seeded demo accounts. | `12345` |
| `ENVIRONMENT` | *(Optional)* Execution environment (`development` or `production`). | `development` |

> [!IMPORTANT]
> **Security Warning:** Never commit `.env` files, API keys, or database credentials to GitHub. Veriflow reads secrets exclusively from system environment variables.

---

## Running the Application

### 1. Backend Startup (FastAPI)

Open a Windows PowerShell terminal from the project root:

```powershell
# Optional: Set your Gemini API key
$env:GEMINI_API_KEY="your_api_key_here"

# Start the FastAPI backend
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

* **Backend Base URL:** `http://127.0.0.1:8000`
* **Interactive OpenAPI (Swagger) Documentation:** `http://127.0.0.1:8000/docs`
* **Alternative ReDoc Documentation:** `http://127.0.0.1:8000/redoc`

### 2. Frontend Startup (React + Vite)

Open a second Windows PowerShell terminal from the project root:

```powershell
cd frontend
npm install
npm run dev
```

* **Frontend Web Application:** `http://localhost:5173` (or `http://localhost:5174` if port 5173 is occupied)
* The backend CORS configuration automatically accepts connections from both port 5173 and port 5174.

### 3. Frontend Production Build Verification
To verify the production bundle:
```powershell
npm run build
```

### 4. Full-Stack Serverless Deployment on Vercel

Veriflow is pre-configured for automated deployment on **Vercel** via GitHub integration:

* **Repository:** `zuhajagirdar/visionguard_project`
* **Vercel Project:** `visionguard-project`
* **Architecture on Vercel:**
  - **Frontend:** Built via root `package.json` and `vercel.json` (`cd frontend && npm install && npm run build`) and served statically from `frontend/dist`.
  - **Serverless API:** Routed via `vercel.json` rewrites (`/api/(.*)` -> `api/index.py`), mounting the FastAPI backend as an ASGI serverless handler.
  - **Database & Auto-Seeding:** Uses SQLite stored in writable `/tmp/data/reimbursement.db` with automatic seeding of demo accounts (`alice_sub`, `charlie_rev`, etc. with password `12345`). For permanent multi-instance persistence, configure an external `DATABASE_URL` (e.g., Supabase, Neon, or Turso) in Vercel Project Settings.
  - **Document Storage:** Uploaded receipts are saved to writable `/tmp/uploads`.
* **Vercel Dashboard Settings:**
  - **Root Directory:** `./` (repository root)
  - **Build Command:** Auto-configured via `vercel.json` (`npm run build`)
  - **Output Directory:** `frontend/dist`
  - **Environment Variables (Optional):**
    - `GEMINI_API_KEY`: Google Gemini API key for online AI assistance.
    - `DATABASE_URL`: Optional PostgreSQL/Supabase database URL for persistent production storage.

### 5. Deploy on Render (Docker)

Veriflow includes a production-ready, multi-stage `Dockerfile` for automated container deployment on **Render**:

1. Log in to [Render](https://dashboard.render.com/) and click **New +** -> **Web Service**.
2. Connect your GitHub repository (`visionguard_project`).
3. Select **Docker** as the Runtime (Render automatically detects the root `Dockerfile`).
4. Choose your branch (e.g., `main`).
5. **Environment Variables (Optional):**
   - `PORT`: Automatically set by Render (defaults to `8000`).
   - `GEMINI_API_KEY`: *(Optional)* Your Google Gemini API key for online AI assistance (falls back to offline suggestions if unset).
   - `DATABASE_URL`: *(Optional)* External PostgreSQL/Supabase connection string (defaults to local SQLite `data/reimbursement.db` if unset).
6. Click **Deploy Web Service**. Every future push to your connected branch will automatically trigger a zero-downtime redeployment.

---

## Demo Accounts & Development Credentials

The local database comes pre-seeded with test accounts across all roles. 

> [!NOTE]
> All demo accounts use the standard local development password: **`12345`**.

| Username | Role | Primary Workflow Scenario |
|---|---|---|
| `alice_sub` | Submitter | Standard employee submitting travel & meal receipts |
| `bob_sub` | Submitter | Submitting hardware receipts & duplicate tests |
| `charlie_rev` | Reviewer | Document inspection, field corrections, requesting more info |
| `david_rev` | Reviewer | Reviewing high-value claims & policy warnings |
| `eve_app` | Approver | Final financial approvals & policy enforcement |
| `frank_app` | Approver | Final claim rejections with required audit notes |

---

## Automated Testing & Benchmark Evaluations

### 1. Backend Regression Suite (73 Tests)
Veriflow includes **73 automated pytest tests** covering authentication, OCR heuristics, workflow state transitions, and reviewer decisions:

```powershell
python -m pytest backend/tests/ -v
```

#### Test Suite Inventory
* `backend/tests/test_auth_password.py`: 8 tests validating password authentication, wrong passwords, role mismatches, hash security, and RBAC actions.
* `backend/tests/test_auto_ocr_and_verification.py`: 8 tests validating native PDF extraction, image OCR, amount mismatches, unreadable detection, corrupt files, and AI grounding.
* `backend/tests/test_claim_submission_workflow.py`: 1 test verifying end-to-end draft save, validation, and submission refresh.
* `backend/tests/test_main.py`: 21 tests verifying CRUD, self-approval prevention, document versioning, filters, and audit logs.
* `backend/tests/test_ocr_heuristics.py`: 7 tests validating extraction heuristics against ground-truth benchmarks, date parsing, and amount extraction.
* `backend/tests/test_request_45_workflow.py`: 1 test verifying multi-document extraction isolation and document switching.
* `backend/tests/test_reviewer_decision_workflow.py`: 6 tests verifying approval comments, mandatory rejection reasons, mandatory more-info notes, and authorization.
* `backend/tests/test_traceability.py`: 2 tests verifying full relational database integrity across requests, documents, runs, fields, and checks.
* `backend/tests/test_verification.py`: 6 tests validating consistency checks, future date warnings, and duplicate detection.

### 2. End-to-End Lifecycle Verification Script
Runs a complete multi-actor simulated lifecycle from Submitter upload through Reviewer correction to Approver authorization:
```powershell
python verify_workflow.py
```

### 3. OCR Benchmark Evaluations: Real-World vs. Synthetic

Veriflow reports two distinct evaluations to ensure complete scientific transparency:

#### A. Real-World SROIE Evaluation (20 Scanned ICDAR 2019 Receipts)
* **Script:** `eval/run_evaluation.py` (reads `eval/manifest.json`, writes `eval/results.json`)
* **Dataset:** 20 held-out real scanned receipts from ICDAR 2019 SROIE test subset (`data/sroie_subset/img/`).
* **Active Engine:** PyTesseract v5+ with heuristic post-processing.
* **Results:**
  * **Merchant Accuracy:** **55%** (9 exact, 2 normalized matching ground truth out of 20).
  * **Date Accuracy:** **70%** (14 normalized to ISO `YYYY-MM-DD` out of 20).
  * **Amount Accuracy:** **55%** (11 exact matches out of 20).
  * **Unreadable / Crashes:** **0** (all 20 receipts processed without unreadable exceptions).
* **Significance:** This ~55–70% real-world accuracy demonstrates why purely autonomous OCR cannot be trusted for financial payouts and validates Veriflow's human-in-the-loop correction design.

#### B. Controlled Synthetic Edge-Case Benchmark (9 Representative Receipts)
* **Script:** `eval/repeatable_evaluation.py` (writes `eval/repeatable_eval_results.json`)
* **Dataset:** 9 generated receipt scenarios (`eval/synthetic_test_assets/`) testing specific edge cases.
* **Scenarios Covered:** Lanczos resolution upscaling, camera rotation, transparent PNG background compositing, European comma decimals, tax/tip exclusion traps, and corrupted files.
* **Results:**
  * **Extraction Accuracy:** **100%** on these 9 controlled edge cases.
  * **Issue Detection Recall:** **100%** (correctly flagged amount mismatch, spelling typo, high-value policy, and corrupt document).
  * **Average Processing Latency:** **393.3 ms** (Native digital PDF: 36.1 ms; Image OCR: ~480 ms).

---

## Current Limitations & Future Improvements

### Current Limitations
1. **Physical Receipt Degradation:** Receipts with extreme physical thermal fading, water damage, or severe paper creases can drop characters in OCR, requiring reviewer manual correction.
2. **Multi-Currency Conversion:** While foreign currency symbols (`€`, `£`, `RM`) are parsed, claims currently assume a unified currency base without automatic live FX exchange conversion.
3. **Local SQLite Concurrency:** SQLite is optimal for single-node local development and testing; heavy concurrent enterprise production would benefit from PostgreSQL.
4. **Session Identifier Tokens:** Bearer tokens currently use database user ID strings rather than stateless cryptographically signed JWTs.

### Future Roadmap
1. **JWT Authentication:** Upgrade bearer tokens to signed JSON Web Tokens (JWT) with cryptographic expiration (`exp`) and refresh token rotation.
2. **Multi-Currency FX Converter:** Integrate live exchange-rate APIs to automatically convert foreign receipts to company base currency.
3. **Line-Item Breakdown Extraction:** Expand heuristic parsing to extract individual line-item tables in addition to the grand total.
4. **PostgreSQL Migration:** Transition database configurations to PostgreSQL with Alembic migration scripts for multi-region deployments.

---


