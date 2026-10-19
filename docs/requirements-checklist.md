# Requirements Checklist

## Problem context
- [ ] Build Expense Reimbursement / Expense Claim Verification tool for one organization

## Target users
- [ ] Submitter (create, edit, upload, submit, track, correct)
- [ ] Reviewer/Approver (inspect, correct, comment, verify, request info, approve, reject)

## Request CRUD
- [ ] Create, view, edit draft, submit, withdraw/archive
- [ ] Store: request ID, type, submitter, date, status, assigned reviewer, expense amount, category, description, created timestamp, updated timestamp
- [ ] Draft editing
- [ ] Traceable submitted changes

## Files and versions
- [ ] Support images and PDFs
- [ ] Multiple docs per request
- [ ] Store original file, type, version, uploader, processing state, timestamp
- [ ] Validate file type, MIME type, size, corruption
- [ ] Versioning rule: Do not delete old version, keep history, current version is for review

## Automatic extraction
- [ ] Use pretrained learned OCR/document component (PaddleOCR or similar)
- [ ] Extract: merchant/vendor name, receipt/reference number, date, total amount, category
- [ ] Link extracted value to request, document, version, run, page
- [ ] Preserve original extracted value separately from corrected value

## Verification checks
- [ ] Check 1: Required fields / attachments (missing, unreadable, inconsistent)
- [ ] Check 2: Form vs Document consistency (amount, date, merchant)
- [ ] Statuses: PASS, WARNING, ERROR
- [ ] Duplicate detection (optional flag, not fraud)

## Human decisions (Review)
- [ ] Reviewer interface: Document/evidence next to extracted values, verifications, corrections, comments
- [ ] Actions: inspect, edit/correct, comment, request correction, approve, reject
- [ ] Retain original vs corrected value history

## Dashboard and search
- [ ] Dashboard showing: pending, approved, rejected, correction-required, turnaround, missing fields
- [ ] Search/filter by: request ID, fields, type, date, assignee, status

## API and security
- [ ] Enforce roles server-side (Submitter cannot approve their own request)
- [ ] REST API for all operations
- [ ] Secure file uploads
- [ ] No frontend-only security

## AI/ML requirement & Evaluation
- [ ] Use OCR/document model
- [ ] Report ML evaluation (held-out set, exact/normalised match, missing fields) in `docs/evaluation.md`

## Generative AI requirement & Security
- [ ] Integrated workflow for GenAI (Not a standalone generic chatbot)
- [ ] Grounded in evidence (request, doc, extracted values, verifications, history)
- [ ] Citations to evidence
- [ ] Explain, summarise, draft messages
- [ ] Security: ignore prompt injections in documents
- [ ] Do NOT let GenAI approve/reject/modify

## Innovation
- [ ] Intelligent Correction Assistant: Generate correction checklist/draft when verification fails. Reviewer can edit/approve.

## Recovery and failure states
- [ ] Loading, processing, empty, failure, corrupt file, OCR failure, verification issue, GenAI failure handling

## Synthetic Data & Testing
- [ ] Create demo data and users
- [ ] Write end-to-end tests
- [ ] Document demo credentials in README

## Out of scope
- [ ] Not fraud detection, not real payments, not legal interpretation.
