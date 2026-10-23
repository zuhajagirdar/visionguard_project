import os
import sys
import shutil
import datetime
import re
from typing import Optional, List, Dict, Any
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

IS_VERCEL = bool(os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
if IS_VERCEL:
    UPLOAD_DIR = '/tmp/uploads'
else:
    UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))

try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except Exception:
    pass

def resolve_filepath(path: str) -> str:
    if os.path.isfile(path):
        return path
    candidates = [
        os.path.abspath(path),
        os.path.join(UPLOAD_DIR, os.path.basename(path)),
        os.path.join('/tmp/uploads', os.path.basename(path)),
        os.path.join(os.getcwd(), path),
        os.path.join(os.path.dirname(__file__), '..', path),
        os.path.join(os.path.dirname(__file__), path),
        os.path.join('uploads', os.path.basename(path)),
        os.path.join('..', 'uploads', os.path.basename(path)),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return path

from backend import models, schemas, database, ocr, security as auth_security, llm

app = FastAPI(title='Veriflow API')

@app.on_event('startup')
def startup():
    from backend import models, database, security as auth_security
    from sqlalchemy import text
    try:
        models.Base.metadata.create_all(bind=database.engine)
    except Exception as e:
        print('create_all notice:', e)

    try:
        with database.engine.connect() as conn:
            result = conn.execute(text('PRAGMA table_info(users)')).fetchall()
            column_names = [row[1] for row in result]
            if 'password_hash' not in column_names:
                conn.execute(text('ALTER TABLE users ADD COLUMN password_hash VARCHAR'))
                conn.commit()
    except Exception as e:
        print('Table migration notice:', e)

    if not auth_security.IS_PROD:
        db = database.SessionLocal()
        try:
            demo_hash = auth_security.hash_password(auth_security.DEMO_PASSWORD)
            users = db.query(models.User).all()
            if not users:
                demo_specs = [
                    ('alice_sub', 'Submitter'),
                    ('bob_sub', 'Submitter'),
                    ('charlie_rev', 'Reviewer'),
                    ('david_rev', 'Reviewer'),
                    ('eve_app', 'Approver'),
                    ('frank_app', 'Approver'),
                    ('alice', 'Submitter'),
                    ('bob', 'Reviewer'),
                ]
                user_map = {}
                for uname, urole in demo_specs:
                    u = models.User(username=uname, role=urole, password_hash=demo_hash)
                    db.add(u)
                    db.flush()
                    user_map[uname] = u

                sub = user_map.get('alice_sub')
                rev = user_map.get('charlie_rev')
                if sub and rev:
                    sample_claims = [
                        {'type': 'Travel', 'status': 'Under Review', 'amount': 150.00, 'merchant': 'Metro Transit', 'desc': 'Client site visit travel expenses'},
                        {'type': 'Meals', 'status': 'Under Review', 'amount': 85.50, 'merchant': 'Corner Cafe', 'desc': 'Team lunch during quarterly planning'},
                        {'type': 'Supplies', 'status': 'More Information Required', 'amount': 120.00, 'merchant': 'Office Mart', 'desc': 'Project stationery and markers'},
                        {'type': 'Travel', 'status': 'Approved', 'amount': 45.00, 'merchant': 'City Cab', 'desc': 'Airport transfer cab ride'},
                        {'type': 'Meals', 'status': 'Draft', 'amount': 34.00, 'merchant': 'Bistro Express', 'desc': 'Working dinner during release'},
                    ]
                    for s in sample_claims:
                        req = models.Request(
                            submitter_id=sub.id,
                            assigned_reviewer_id=rev.id if s['status'] in ['Under Review', 'More Information Required'] else None,
                            type=s['type'],
                            category='General',
                            status=s['status'],
                            expense_amount=s['amount'],
                            merchant_name=s['merchant'],
                            expense_date=datetime.date.today(),
                            description=s['desc']
                        )
                        db.add(req)
                        db.flush()
                        log_audit(db, req.id, sub.id, 'create', 'None', 'Draft')
                        if s['status'] != 'Draft':
                            log_audit(db, req.id, sub.id, 'submit', 'Draft', 'Submitted')
                            log_audit(db, req.id, rev.id, 'start_process', 'Submitted', s['status'], 'Automated verification initiated')
                        if s['status'] == 'More Information Required':
                            log_audit(db, req.id, rev.id, 'request_correction', 'Under Review', 'More Information Required', 'Receipt image is blurry. Please upload a clear scan.')
                            db.add(models.Comment(request_id=req.id, user_id=rev.id, text='Receipt image is blurry. Please upload a clear scan.'))
                        elif s['status'] == 'Approved':
                            log_audit(db, req.id, rev.id, 'approve', 'Under Review', 'Approved', 'All details verified against receipt.')
                            db.add(models.Comment(request_id=req.id, user_id=rev.id, text='[Approved] All details verified against receipt.'))
            else:
                for u in users:
                    if not u.password_hash or not auth_security.verify_password(auth_security.DEMO_PASSWORD, u.password_hash):
                        u.password_hash = demo_hash
            db.commit()
        except Exception as e:
            print('Demo seed notice:', e)
        finally:
            db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_origin_regex=r'https?://.*',
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

security = HTTPBearer()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        user_id = int(credentials.credentials)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

def log_audit(db: Session, request_id: int, actor_id: int, action: str, old_state: str, new_state: str, reason: str = ""):
    log = models.AuditLog(
        request_id=request_id,
        actor_id=actor_id,
        action=action,
        from_status=old_state,
        to_status=new_state,
        reason=reason,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(log)
    db.commit()

@app.post("/users/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        if user.password:
            db_user.password_hash = auth_security.hash_password(user.password)
            db.commit()
            db.refresh(db_user)
        elif not db_user.password_hash and not auth_security.IS_PROD:
            db_user.password_hash = auth_security.hash_password(auth_security.DEMO_PASSWORD)
            db.commit()
            db.refresh(db_user)
        return db_user
    pwd = user.password or (auth_security.DEMO_PASSWORD if not auth_security.IS_PROD else None)
    pwd_hash = auth_security.hash_password(pwd) if pwd else None
    db_user = models.User(username=user.username, role=user.role, password_hash=pwd_hash)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/requests/", response_model=schemas.RequestOut)
def create_request(req: schemas.RequestCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "Submitter":
        raise HTTPException(status_code=403, detail="Only submitters can create requests")
    db_req = models.Request(
        submitter_id=current_user.id,
        type=req.type,
        expense_amount=req.expense_amount,
        merchant_name=req.merchant_name,
        expense_date=req.expense_date,
        category=req.category,
        description=req.description,
        status="Draft"
    )
    db.add(db_req)
    db.commit()
    db.refresh(db_req)
    log_audit(db, db_req.id, current_user.id, "create", "None", "Draft")
    return db_req



# Removed redundant date parsing block that overwrote filtered date


def normalize_merchant(name: str):
    if not name: return ""
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\b(inc|llc|corp|co|ltd|company)\b', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def normalize_date(date_str: str) -> str:
    """Parse date strings (day‑first preferred) to ISO YYYY‑MM‑DD.
    Returns an empty string for invalid or future dates.
    """
    # Reuse OCR's robust date parsing logic.
    from backend import ocr
    return ocr._parse_date(date_str)




def run_verifications(db: Session, req_id: int):
    db.query(models.VerificationCheck).filter(models.VerificationCheck.request_id == req_id).delete(synchronize_session=False)
    db.commit()
    
    req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not req: return
    
    docs = db.query(models.Document).filter(models.Document.request_id == req.id).all()
    if not docs:
        db.add(models.VerificationCheck(request_id=req.id, rule_name="Required Document", category="missing", evidence="No documents attached", result="CANNOT DETERMINE"))
    else:
        db.add(models.VerificationCheck(request_id=req.id, rule_name="Required Document", category="valid", evidence=f"{len(docs)} document(s) attached", result="PASS"))
        
    if (req.expense_amount is None or req.expense_amount <= 0 or
        req.merchant_name is None or not str(req.merchant_name).strip() or
        req.expense_date is None):
        db.add(models.VerificationCheck(request_id=req.id, rule_name="Required Field", category="missing", evidence="Required fields missing", result="CANNOT DETERMINE"))
    else:
        db.add(models.VerificationCheck(request_id=req.id, rule_name="Required Field", category="valid", evidence="All required fields provided", result="PASS"))

    if docs:
        has_ocr_failure = False
        failure_messages = []
        for doc in docs:
            latest_ver = db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == doc.id).order_by(models.DocumentVersion.version_number.desc()).first()
            if latest_ver and latest_ver.processing_state == "Failed":
                has_ocr_failure = True
                latest_run = db.query(models.ExtractionRun).filter(models.ExtractionRun.document_version_id == latest_ver.id).order_by(models.ExtractionRun.id.desc()).first()
                err = latest_run.error_message if (latest_run and latest_run.error_message) else "OCR extraction failed"
                failure_messages.append(f"{doc.original_filename} (v{latest_ver.version_number}): {err}")
        if has_ocr_failure:
            db.add(models.VerificationCheck(
                request_id=req.id,
                rule_name="Document Readability",
                category="unreadable",
                evidence="; ".join(failure_messages),
                result="CANNOT DETERMINE"
            ))
        else:
            db.add(models.VerificationCheck(
                request_id=req.id,
                rule_name="Document Readability",
                category="valid",
                evidence="Document text extracted successfully",
                result="PASS"
            ))

        
    ext_amounts = []
    ext_dates = []
    ext_merchants = []
    
    for doc in docs:
        latest_ver = db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == doc.id).order_by(models.DocumentVersion.version_number.desc()).first()
        if not latest_ver: continue
        latest_run = db.query(models.ExtractionRun).filter(models.ExtractionRun.document_version_id == latest_ver.id).order_by(models.ExtractionRun.id.desc()).first()
        if not latest_run: continue
        
        for field in latest_run.extractions:
            val = field.corrected_value if field.corrected_value is not None else field.original_value
            if not val or val.lower() == "unknown": continue
            
            evidence_tag = f"Doc {doc.id} v{latest_ver.version_number}"
            
            if field.field_name == "amount":
                try:
                    clean_val = re.sub(r'[^\d\.]', '', val)
                    ext_amounts.append((float(clean_val), evidence_tag, latest_ver.id))
                except ValueError:
                    db.add(models.VerificationCheck(request_id=req.id, rule_name="Amount Parsing", category="unreadable", evidence=f"Could not parse amount from {evidence_tag}: {val}", result="CANNOT DETERMINE"))
            elif field.field_name == "date":
                try:
                    dt = datetime.datetime.strptime(val, "%Y-%m-%d")
                    ext_dates.append((val, evidence_tag, latest_ver.id))
                    if dt > datetime.datetime.utcnow():
                        db.add(models.VerificationCheck(request_id=req.id, rule_name="Date Validity", category="inconsistent", evidence=f"Date from {evidence_tag} is in the future: {val}", result="WARNING"))
                except ValueError:
                    db.add(models.VerificationCheck(request_id=req.id, rule_name="Date Parsing", category="unreadable", evidence=f"Could not parse date from {evidence_tag}: {val}", result="CANNOT DETERMINE"))
            elif field.field_name == "merchant":
                ext_merchants.append((val, evidence_tag))
                
    if req.expense_amount is not None:
        if not ext_amounts:
            db.add(models.VerificationCheck(request_id=req.id, rule_name="Amount Consistency", category="unreadable", evidence="No valid amounts extracted from documents to compare.", result="CANNOT DETERMINE"))
        else:
            match_ev = None
            match_vid = None
            for amt, ev, vid in ext_amounts:
                if abs(float(req.expense_amount) - amt) < 0.01:
                    match_ev = ev
                    match_vid = vid
                    break
            if match_ev:
                db.add(models.VerificationCheck(request_id=req.id, document_version_id=match_vid, rule_name="Amount Consistency", category="valid", evidence=f"Submitted amount matches {match_ev}.", result="PASS"))
            else:
                db.add(models.VerificationCheck(request_id=req.id, rule_name="Amount Consistency", category="inconsistent", evidence=f"Form amount {req.expense_amount} does not match any document amounts.", result="INCONSISTENT"))
                
        # Policy rule: Unusual / High-value amount warning (non-blocking warning requiring manager sign-off)
        try:
            if float(req.expense_amount) > 5000.0:
                db.add(models.VerificationCheck(
                    request_id=req.id,
                    rule_name="High Value Policy",
                    category="unusual_amount",
                    evidence=f"Claim amount ${float(req.expense_amount):.2f} exceeds standard $5,000 threshold. Flagged for elevated reviewer approval.",
                    result="WARNING"
                ))
        except (ValueError, TypeError):
            pass
                
    if req.expense_date is not None:
        if not ext_dates:
            db.add(models.VerificationCheck(request_id=req.id, rule_name="Date Consistency", category="unreadable", evidence="No valid dates extracted from documents to compare.", result="CANNOT DETERMINE"))
        else:
            match_ev = None
            match_vid = None
            for d_val, ev, vid in ext_dates:
                if d_val == str(req.expense_date):
                    match_ev = ev
                    match_vid = vid
                    break
            if match_ev:
                db.add(models.VerificationCheck(request_id=req.id, document_version_id=match_vid, rule_name="Date Consistency", category="valid", evidence=f"Submitted date matches {match_ev}.", result="PASS"))
            else:
                db.add(models.VerificationCheck(request_id=req.id, rule_name="Date Consistency", category="inconsistent", evidence=f"Form date {req.expense_date} does not match any document dates.", result="INCONSISTENT"))
                
    if req.merchant_name is not None:
        if not ext_merchants:
            db.add(models.VerificationCheck(request_id=req.id, rule_name="Merchant Consistency", category="unreadable", evidence="No valid merchants extracted from documents to compare.", result="CANNOT DETERMINE"))
        else:
            import difflib
            norm_req = normalize_merchant(req.merchant_name)
            match_ev = None
            spelling_match = None
            for m_val, ev in ext_merchants:
                norm_doc = normalize_merchant(m_val)
                if norm_doc == norm_req:
                    match_ev = ev
                    break
                else:
                    ratio = difflib.SequenceMatcher(None, norm_req, norm_doc).ratio()
                    if ratio >= 0.65 and not spelling_match:
                        spelling_match = (m_val, ev, ratio)
            if match_ev:
                db.add(models.VerificationCheck(request_id=req.id, rule_name="Merchant Consistency", category="valid", evidence=f"Submitted merchant matches {match_ev}.", result="PASS"))
            elif spelling_match:
                m_val, ev, ratio = spelling_match
                db.add(models.VerificationCheck(request_id=req.id, rule_name="Merchant Consistency", category="spelling_mismatch", evidence=f"Possible spelling mistake or typo in merchant name: Form specifies '{req.merchant_name}', but {ev} shows '{m_val}' (similarity: {ratio:.0%}).", result="WARNING"))
            else:
                db.add(models.VerificationCheck(request_id=req.id, rule_name="Merchant Consistency", category="inconsistent", evidence=f"Form merchant '{req.merchant_name}' does not match any document merchants.", result="INCONSISTENT"))
                

    if ext_amounts and ext_merchants and ext_dates:
        amt = ext_amounts[0][0]
        merch = ext_merchants[0][0]
        dt = ext_dates[0][0]
        
        # very simple duplicate check
        dt_obj = datetime.datetime.strptime(dt, "%Y-%m-%d").date()
        dups = db.query(models.Request).filter(
            models.Request.id != req.id,
            models.Request.expense_amount == amt,
            models.Request.expense_date == dt_obj
        ).all()
        # we check merchant loosely
        is_dup = False
        for d in dups:
            if d.merchant_name and normalize_merchant(d.merchant_name) == normalize_merchant(merch):
                is_dup = True
                break
        
        if is_dup:
            db.add(models.VerificationCheck(request_id=req.id, rule_name="Possible Duplicate", category="duplicate", evidence="Found another request with same amount, date, and merchant", result="WARNING"))

    db.commit()

@app.get("/requests/{req_id}", response_model=schemas.RequestOut)
def get_request(req_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not db_req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if current_user.role == "Submitter" and db_req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this request")
        
    return db_req

@app.put("/requests/{req_id}", response_model=schemas.RequestOut)
def update_request(req_id: int, req_update: schemas.RequestUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not db_req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if db_req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this request")
        
    if db_req.status not in ["Draft", "More Information Required"]:
        raise HTTPException(status_code=400, detail=f"Cannot edit request in status {db_req.status}")
        
    update_data = req_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_req, key, value)
        
    db.commit()
    db.refresh(db_req)
    
    # Rerun verifications since request data changed
    run_verifications(db, db_req.id)
    return db_req


@app.post("/requests/{req_id}/submit")
def submit_request(req_id: int, req_update: Optional[schemas.RequestUpdate] = Body(None), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not db_req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if db_req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to submit this request")
        
    if db_req.status != "Draft":
        raise HTTPException(status_code=400, detail="Only Draft requests can be submitted")
        
    if req_update is not None:
        update_data = req_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_req, key, value)
        db.commit()
        db.refresh(db_req)
        run_verifications(db, db_req.id)

    missing = []
    if db_req.merchant_name is None or not str(db_req.merchant_name).strip():
        missing.append("merchant_name")
    if db_req.expense_date is None:
        missing.append("expense_date")
    if db_req.expense_amount is None or db_req.expense_amount <= 0:
        missing.append("expense_amount")

    if missing:
        raise HTTPException(status_code=400, detail=f"Must provide expense_amount, merchant_name, and expense_date to submit. Missing or invalid: {', '.join(missing)}")
        
    log_audit(db, db_req.id, current_user.id, "submit", db_req.status, "Submitted")
    db_req.status = "Submitted"
    db.commit()
    db.refresh(db_req)
    return {"status": "success", "new_status": "Submitted"}


@app.post("/requests/{req_id}/upload")
def upload_document(req_id: int, file: UploadFile = File(...), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.webp')):
        raise HTTPException(status_code=400, detail="Unsupported file type")
        
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
    
    req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to upload to this request")
        
    # Allow uploads if Draft or More Information Required (correction phase)
    if req.status not in ["Draft", "More Information Required"]:
        raise HTTPException(status_code=400, detail=f"Cannot upload documents in status {req.status}")
        
    doc = db.query(models.Document).filter(models.Document.request_id == req_id, models.Document.original_filename == file.filename).first()
    if not doc:
        doc = models.Document(request_id=req_id, original_filename=file.filename, file_type=file.content_type, current_version=1)
        db.add(doc)
        db.commit()
        db.refresh(doc)
    else:
        doc.current_version += 1
        db.commit()

    file_path = os.path.join(UPLOAD_DIR, f"{req_id}_{doc.id}_v{doc.current_version}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    doc_ver = models.DocumentVersion(document_id=doc.id, version_number=doc.current_version, filepath=file_path, processing_state="Pending", uploader_id=current_user.id)
    db.add(doc_ver)
    db.commit()
    db.refresh(doc_ver)

    # Automatic OCR & Document Text Extraction
    run = models.ExtractionRun(document_version_id=doc_ver.id, engine="pytesseract_pdfplumber", status="Running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        extracted = ocr.extract_fields(file_path)
        if "engine" in extracted:
            run.engine = extracted["engine"]
        for k, v in extracted.items():
            ext_f = models.ExtractedField(extraction_run_id=run.id, field_name=k, original_value=str(v))
            db.add(ext_f)
        run.status = "Completed"
        run.completed_at = datetime.datetime.now(datetime.UTC)
        doc_ver.processing_state = "Completed"
    except Exception as e:
        run.status = "Failed"
        run.error_message = str(e)
        run.completed_at = datetime.datetime.now(datetime.UTC)
        doc_ver.processing_state = "Failed"

    db.commit()

    # Automatically run verification checks
    run_verifications(db, req.id)
    
    log_audit(db, req.id, current_user.id, "upload_document", req.status, req.status, f"Uploaded {file.filename} v{doc.current_version}")
    db.commit()
    return {"message": "File uploaded", "version_id": doc_ver.id, "processing_state": doc_ver.processing_state}

@app.post("/requests/{req_id}/retry-ocr")
def retry_ocr(req_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if current_user.role == "Submitter" and req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    docs = db.query(models.Document).filter(models.Document.request_id == req_id).all()
    if not docs:
        raise HTTPException(status_code=400, detail="No documents attached to retry")
        
    processed_count = 0
    errors = []
    for doc in docs:
        latest_ver = db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == doc.id).order_by(models.DocumentVersion.version_number.desc()).first()
        if not latest_ver:
            continue
        run = models.ExtractionRun(document_version_id=latest_ver.id, engine="pytesseract_pdfplumber", status="Running")
        db.add(run)
        db.commit()
        db.refresh(run)
        try:
            extracted = ocr.extract_fields(latest_ver.filepath)
            if "engine" in extracted:
                run.engine = extracted["engine"]
            for k, v in extracted.items():
                ext_f = models.ExtractedField(extraction_run_id=run.id, field_name=k, original_value=str(v))
                db.add(ext_f)
            run.status = "Completed"
            run.completed_at = datetime.datetime.now(datetime.UTC)
            latest_ver.processing_state = "Completed"
            processed_count += 1
        except Exception as e:
            run.status = "Failed"
            run.error_message = str(e)
            run.completed_at = datetime.datetime.now(datetime.UTC)
            latest_ver.processing_state = "Failed"
            errors.append(str(e))
            
    db.commit()
    run_verifications(db, req.id)
    if errors:
        return {"status": "failed", "error": "; ".join(errors)}
    return {"status": "success", "processed_count": processed_count}

@app.post("/requests/{req_id}/process")
def process_request(req_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req.status not in ["Submitted", "Processing Failed"]:
        raise HTTPException(status_code=400, detail=f"Cannot process request in status {req.status}")
        
    old_status = req.status
    req.status = "Processing"
    log_audit(db, req.id, current_user.id, "start_process", old_status, "Processing")
    db.commit()
    
    docs = db.query(models.Document).filter(models.Document.request_id == req_id).all()
    if not docs:
        req.status = "Processing Failed"
        log_audit(db, req.id, current_user.id, "process_fail", "Processing", "Processing Failed", "No documents attached")
        db.commit()
        raise HTTPException(status_code=400, detail="No documents attached")
        
    has_completed_doc = False
    has_failed_doc = False
    for doc in docs:
        latest_ver = db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == doc.id).order_by(models.DocumentVersion.version_number.desc()).first()
        if latest_ver and latest_ver.processing_state == "Pending":
            run = models.ExtractionRun(document_version_id=latest_ver.id, engine="pytesseract_pdfplumber", status="Running")
            db.add(run)
            db.commit()
            db.refresh(run)
            try:
                extracted = ocr.extract_fields(latest_ver.filepath)
                if "engine" in extracted:
                    run.engine = extracted["engine"]
                for k, v in extracted.items():
                    ext_f = models.ExtractedField(extraction_run_id=run.id, field_name=k, original_value=str(v))
                    db.add(ext_f)
                run.status = "Completed"
                run.completed_at = datetime.datetime.now(datetime.UTC)
                latest_ver.processing_state = "Completed"
                has_completed_doc = True
            except Exception as e:
                run.status = "Failed"
                run.error_message = str(e)
                run.completed_at = datetime.datetime.now(datetime.UTC)
                latest_ver.processing_state = "Failed"
                has_failed_doc = True
        elif latest_ver and latest_ver.processing_state == "Completed":
            has_completed_doc = True
        elif latest_ver and latest_ver.processing_state == "Failed":
            has_failed_doc = True
    db.commit()

    if has_failed_doc and not has_completed_doc:
        req.status = "Processing Failed"
        log_audit(db, req.id, current_user.id, "process_fail", "Processing", "Processing Failed", "No valid documents could be processed")
        db.commit()
        return {"status": "Processing Failed"}
    
    run_verifications(db, req.id)
            
    req.status = "Under Review"
    log_audit(db, req.id, current_user.id, "process_complete", "Processing", "Under Review")
    db.commit()
    return {"status": "Under Review"}

@app.post("/requests/{req_id}/review")
def review_request(req_id: int, action: schemas.ReviewAction, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if current_user.role not in ["Reviewer", "Approver"]:
        raise HTTPException(status_code=403, detail="Not authorized as reviewer or approver")
        
    if req.submitter_id == current_user.id:
        raise HTTPException(status_code=403, detail="Submitter cannot approve their own request")
        
    if req.status not in ["Under Review", "Processing Failed"]:
        raise HTTPException(status_code=400, detail=f"Cannot review request in status {req.status}")

    if action.action not in ["approve", "reject", "request_correction"]:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action.action}. Allowed actions: approve, reject, request_correction")
        
    clean_reason = action.reason.strip() if action.reason else ""
    if action.action in ["reject", "request_correction"] and not clean_reason:
        raise HTTPException(
            status_code=400,
            detail=f"A reason or explanation is required when {action.action.replace('_', ' ')}ing a claim."
        )
        
    old_status = req.status
    if action.action == "approve":
        if old_status == "Processing Failed":
            raise HTTPException(status_code=400, detail="Cannot approve a request that failed processing")
        req.status = "Approved"
        if clean_reason:
            comment = models.Comment(request_id=req.id, user_id=current_user.id, text=f"[Approved] {clean_reason}")
            db.add(comment)
    elif action.action == "reject":
        req.status = "Rejected"
        comment = models.Comment(request_id=req.id, user_id=current_user.id, text=f"[Rejected] {clean_reason}")
        db.add(comment)
    elif action.action == "request_correction":
        req.status = "More Information Required"
        draft = llm.generate_correction_draft({}, clean_reason)
        comment = models.Comment(request_id=req.id, user_id=current_user.id, text=draft)
        db.add(comment)
            
    log_audit(db, req.id, current_user.id, action.action, old_status, req.status, clean_reason if clean_reason else None)
    db.commit()
    return {"status": req.status}

@app.post("/requests/{req_id}/resubmit")
def resubmit_request(req_id: int, req_update: Optional[schemas.RequestUpdate] = Body(None), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to resubmit this request")
        
    if req.status != "More Information Required":
        raise HTTPException(status_code=400, detail=f"Cannot resubmit request in status {req.status}")
        
    if req_update is not None:
        update_data = req_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(req, key, value)
        db.commit()
        db.refresh(req)
        run_verifications(db, req.id)

    missing = []
    if req.merchant_name is None or not str(req.merchant_name).strip():
        missing.append("merchant_name")
    if req.expense_date is None:
        missing.append("expense_date")
    if req.expense_amount is None or req.expense_amount <= 0:
        missing.append("expense_amount")

    if missing:
        raise HTTPException(status_code=400, detail=f"Must provide expense_amount, merchant_name, and expense_date to resubmit. Missing or invalid: {', '.join(missing)}")
        
    old_status = req.status
    req.status = "Submitted"
    log_audit(db, req.id, current_user.id, "resubmit", old_status, req.status)
    db.commit()
    db.refresh(req)
    return {"status": "Submitted", "new_status": "Submitted"}

@app.post("/requests/{req_id}/withdraw")
def withdraw_request(req_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role != "Submitter":
        raise HTTPException(status_code=403, detail="Only submitters can withdraw requests")
    if req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to withdraw this request")
    if req.status in ["Approved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Cannot withdraw a request that is already Approved or Rejected")
    if req.status == "Withdrawn":
        raise HTTPException(status_code=400, detail="Request is already withdrawn")
    old_status = req.status
    req.status = "Withdrawn"
    log_audit(db, req.id, current_user.id, "withdraw", old_status, "Withdrawn")
    db.commit()
    return {"status": "Withdrawn"}

@app.post("/requests/{req_id}/correct_field")
def correct_field(req_id: int, field_id: int, new_value: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["Reviewer", "Approver"]:
        raise HTTPException(status_code=403, detail="Only reviewers can correct fields")
        
    req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req.status != "Under Review":
        raise HTTPException(status_code=400, detail="Request must be Under Review to correct fields")
        
    field = db.query(models.ExtractedField).filter(models.ExtractedField.id == field_id).first()
    if field:
        old_val = field.corrected_value or field.original_value
        field.corrected_value = new_value
        field.corrected_by_user_id = current_user.id
        field.corrected_at = datetime.datetime.utcnow()
        log_audit(db, req.id, current_user.id, "correct_field", req.status, req.status, f"Changed {field.field_name} from {old_val} to {new_value}")
        db.commit()
        run_verifications(db, req.id)
    return {"status": "corrected"}

from typing import List, Optional
from sqlalchemy import func
from collections import defaultdict

@app.get("/requests/", response_model=List[schemas.RequestOut])
def get_requests(
    req_id: Optional[int] = None,
    merchant: Optional[str] = None,
    type: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[str] = None,
    assignee_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role == "Submitter":
        query = db.query(models.Request).filter(models.Request.submitter_id == current_user.id)
    else:
        query = db.query(models.Request)
        
    if req_id is not None:
        query = query.filter(models.Request.id == req_id)
    if merchant:
        query = query.filter(models.Request.merchant_name.ilike(f"%{merchant}%"))
    if type:
        query = query.filter(models.Request.type == type)
    if date:
        query = query.filter(models.Request.expense_date == date)
    if status:
        query = query.filter(models.Request.status == status)
    if assignee_id is not None:
        query = query.filter(models.Request.assigned_reviewer_id == assignee_id)
        
    return query.all()

@app.get("/dashboard", response_model=schemas.DashboardOut)
def get_dashboard(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "Submitter":
        base_query = db.query(models.Request).filter(models.Request.submitter_id == current_user.id)
        # Use explicit SELECT for subquery to avoid SAWarning
        req_ids_subquery = select(models.Request.id).where(models.Request.submitter_id == current_user.id)
        
        missing_records = db.query(models.VerificationCheck).filter(
            models.VerificationCheck.category.in_(["unreadable", "missing"]),
            models.VerificationCheck.request_id.in_(req_ids_subquery)
        ).all()
        
        logs_query = db.query(models.AuditLog).filter(
            models.AuditLog.to_status.in_(["Approved", "Rejected"]),
            models.AuditLog.request_id.in_(req_ids_subquery)
        )
    else:
        base_query = db.query(models.Request)
        
        missing_records = db.query(models.VerificationCheck).filter(
            models.VerificationCheck.category.in_(["unreadable", "missing"])
        ).all()
        
        logs_query = db.query(models.AuditLog).filter(
            models.AuditLog.to_status.in_(["Approved", "Rejected"])
        )
        
    pending = base_query.filter(models.Request.status.in_(["Draft", "Submitted", "Processing", "Under Review"])).count()
    approved = base_query.filter(models.Request.status == "Approved").count()
    rejected = base_query.filter(models.Request.status == "Rejected").count()
    correction = base_query.filter(models.Request.status == "More Information Required").count()
    
    missing_dict = defaultdict(list)
    for r in missing_records:
        missing_dict[r.rule_name].append(r.request_id)
        
    missing_fields = []
    for k, v in sorted(missing_dict.items(), key=lambda item: len(item[1]), reverse=True)[:5]:
        missing_fields.append({"field_name": k, "count": len(v), "request_ids": list(set(v))})
        
    turnaround_times = []
    terminal_logs = logs_query.all()
    for t_log in terminal_logs:
        s_log = db.query(models.AuditLog).filter(
            models.AuditLog.request_id == t_log.request_id,
            models.AuditLog.to_status == "Submitted"
        ).order_by(models.AuditLog.timestamp.desc()).first()
        if s_log and t_log.timestamp > s_log.timestamp:
            diff_hours = (t_log.timestamp - s_log.timestamp).total_seconds() / 3600.0
            turnaround_times.append(diff_hours)
            
    avg_turnaround = sum(turnaround_times) / len(turnaround_times) if turnaround_times else None
    
    return {
        "pending_count": pending, 
        "approved_count": approved, 
        "rejected_count": rejected, 
        "correction_required_count": correction,
        "frequent_missing_fields": missing_fields,
        "average_review_turnaround_hours": avg_turnaround
    }


@app.post("/requests/{req_id}/ask")
def ask_genai(req_id: int, q: schemas.AskQuestion, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404)
        
    if current_user.role not in ["Reviewer", "Approver"] and req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="No permission to view this request")
        
    docs = db.query(models.Document).filter(models.Document.request_id == req.id).all()
    verifications = db.query(models.VerificationCheck).filter(models.VerificationCheck.request_id == req.id).all()
    mir_log = db.query(models.AuditLog).filter(models.AuditLog.request_id == req_id, models.AuditLog.action == "request_correction").order_by(models.AuditLog.timestamp.desc()).first()
    mir_reason = mir_log.reason if mir_log else None

    if not docs and not verifications and not mir_reason:
        return {"answer": "Insufficient evidence in the current request."}

    doc_details = []
    extractions = []
    for d in docs:
        versions = db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == d.id).order_by(models.DocumentVersion.version_number.desc()).all()
        doc_details.append({
            "id": d.id,
            "original_filename": d.original_filename,
            "versions": [{"version_number": v.version_number, "processing_state": v.processing_state} for v in versions]
        })
        if versions:
            run = db.query(models.ExtractionRun).filter(models.ExtractionRun.document_version_id == versions[0].id).order_by(models.ExtractionRun.id.desc()).first()
            if run:
                for f in run.extractions:
                    extractions.append({
                        "field_name": f.field_name,
                        "original_value": f.original_value,
                        "corrected_value": f.corrected_value
                    })

    verifs_data = [{
        "rule_name": v.rule_name,
        "category": v.category,
        "result": v.result,
        "evidence": v.evidence
    } for v in verifications]

    req_data = {
        "id": req.id,
        "type": req.type,
        "status": req.status,
        "merchant_name": req.merchant_name,
        "expense_date": str(req.expense_date) if req.expense_date else None,
        "expense_amount": req.expense_amount,
        "category": req.category,
        "description": req.description,
        "reviewer_reason": mir_reason
    }

    answer = llm.explain_request_findings(
        req_data=req_data,
        documents_data=doc_details,
        extractions_data=extractions,
        verifications_data=verifs_data,
        user_question=q.question
    )

    return {"answer": answer}











from fastapi import Form
@app.post("/token")
def login_for_access_token(
    username: str = Form(...),
    password: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    clean_username = username.strip() if username else ""
    if not clean_username:
        raise HTTPException(status_code=400, detail="Username is required")

    user = db.query(models.User).filter(models.User.username == clean_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if role and user.role != role:
        raise HTTPException(status_code=400, detail=f"Role mismatch: account '{user.username}' is a {user.role}, but {role} was selected")

    if not password or not password.strip():
        raise HTTPException(status_code=400, detail="Password is required")

    if not user.password_hash and not auth_security.IS_PROD:
        user.password_hash = auth_security.hash_password(auth_security.DEMO_PASSWORD)
        db.commit()
        db.refresh(user)

    if not user.password_hash or not auth_security.verify_password(password.strip(), user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    return {
        "access_token": str(user.id),
        "token_type": "bearer",
        "role": user.role,
        "username": user.username
    }
@app.get("/requests/{req_id}/details")
def get_request_details(req_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not db_req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if current_user.role == "Submitter" and db_req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this request")
        
    docs = db.query(models.Document).filter(models.Document.request_id == req_id).all()
    
    doc_details = []
    for d in docs:
        versions = db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == d.id).order_by(models.DocumentVersion.version_number.desc()).all()
        v_list = []
        for v in versions:
            run = db.query(models.ExtractionRun).filter(models.ExtractionRun.document_version_id == v.id).order_by(models.ExtractionRun.id.desc()).first()
            v_list.append({
                "id": v.id,
                "version_number": v.version_number,
                "processing_state": v.processing_state,
                "uploaded_at": v.timestamp.isoformat() if v.timestamp else None,
                "error_message": run.error_message if run and run.error_message else None
            })
        doc_details.append({
            "id": d.id,
            "original_filename": d.original_filename,
            "versions": v_list
        })
        
    verifications = db.query(models.VerificationCheck).filter(models.VerificationCheck.request_id == req_id).all()
    
    extractions = []
    document_extractions = []
    # get extractions for latest run of each doc, preserving per-document association
    for d in doc_details:
        if d["versions"]:
            latest_v = d["versions"][0]
            latest_v_id = latest_v["id"]
            run = db.query(models.ExtractionRun).filter(models.ExtractionRun.document_version_id == latest_v_id).order_by(models.ExtractionRun.id.desc()).first()
            doc_fields = []
            if run:
                fields = db.query(models.ExtractedField).filter(models.ExtractedField.extraction_run_id == run.id).all()
                for f in fields:
                    conf_val = None
                    try:
                        if f.confidence is not None and float(f.confidence) > 0.0:
                            conf_val = float(f.confidence)
                    except (ValueError, TypeError):
                        pass

                    field_dict = {
                        "id": f.id,
                        "field_name": f.field_name,
                        "original_value": f.original_value,
                        "corrected_value": f.corrected_value,
                        "confidence": conf_val,
                        "document_id": d["id"],
                        "document_filename": d["original_filename"],
                        "version_number": latest_v["version_number"],
                        "version_id": latest_v_id,
                        "engine": run.engine
                    }
                    extractions.append(field_dict)
                    doc_fields.append(field_dict)

            document_extractions.append({
                "document_id": d["id"],
                "document_filename": d["original_filename"],
                "version_number": latest_v["version_number"],
                "version_id": latest_v_id,
                "engine": run.engine if run else None,
                "processing_state": latest_v["processing_state"],
                "error_message": latest_v.get("error_message"),
                "fields": doc_fields
            })

    # Fetch comments for the request, most recent first
    comments = db.query(models.Comment).filter(models.Comment.request_id == req_id).order_by(models.Comment.timestamp.desc()).all()

    # Fetch audit history
    history = db.query(models.AuditLog).filter(models.AuditLog.request_id == req_id).order_by(models.AuditLog.timestamp.asc()).all()

    # Determine information required reason from the most recent request_correction audit log entry
    information_required_reason = None
    if db_req.status == "More Information Required":
        mir_log = db.query(models.AuditLog).filter(
            models.AuditLog.request_id == req_id,
            models.AuditLog.action == "request_correction"
        ).order_by(models.AuditLog.timestamp.desc()).first()
        if mir_log and mir_log.reason:
            information_required_reason = mir_log.reason
        elif comments:
            information_required_reason = comments[0].text

    return {
        "request": {
            "id": db_req.id,
            "status": db_req.status,
            "type": db_req.type,
            "expense_amount": db_req.expense_amount,
            "merchant_name": db_req.merchant_name,
            "expense_date": str(db_req.expense_date) if db_req.expense_date else None,
            "category": db_req.category,
            "description": db_req.description,
            "submitter_id": db_req.submitter_id
        },
        "documents": doc_details,
        "verifications": [{"id": v.id, "rule_name": v.rule_name, "category": v.category, "evidence": v.evidence, "result": v.result} for v in verifications],
        "extractions": extractions,
        "document_extractions": document_extractions,
        "history": [{"action": h.action, "from_status": h.from_status, "to_status": h.to_status, "timestamp": str(h.timestamp), "user_id": h.actor_id, "reason": h.reason} for h in history],
        "comments": [{"id": c.id, "user_id": c.user_id, "text": c.text, "timestamp": str(c.timestamp)} for c in comments],
        "information_required_reason": information_required_reason,
        "missing_fields": (
            ([{"field": "merchant_name", "location": "claim", "label": "Claim Merchant", "message": "Not filled in claim form"}] if (db_req.merchant_name is None or not str(db_req.merchant_name).strip()) else []) +
            ([{"field": "expense_date", "location": "claim", "label": "Claim Date", "message": "Not filled in claim form"}] if db_req.expense_date is None else []) +
            ([{"field": "expense_amount", "location": "claim", "label": "Claim Amount", "message": "Not filled in claim form"}] if (db_req.expense_amount is None or db_req.expense_amount <= 0) else []) +
            [
                {"field": "document_unreadable", "location": "document", "label": f"{d['original_filename']} (v{d['versions'][0]['version_number']})", "message": f"Document unreadable: {d['versions'][0].get('error_message') or 'OCR failed'}"}
                for d in doc_details
                if d.get("versions") and d["versions"][0].get("processing_state") == "Failed"
            ]
        )
    }
from fastapi.responses import FileResponse

@app.get("/documents/{version_id}/content")
def get_document_content(version_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc_ver = db.query(models.DocumentVersion).filter(models.DocumentVersion.id == version_id).first()
    if not doc_ver:
        raise HTTPException(status_code=404, detail="Version not found")
        
    doc = db.query(models.Document).filter(models.Document.id == doc_ver.document_id).first()
    req = db.query(models.Request).filter(models.Request.id == doc.request_id).first()
    
    if current_user.role == "Submitter" and req.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    import mimetypes
    mime_type, _ = mimetypes.guess_type(doc.original_filename)
    if not mime_type:
        mime_type = "application/octet-stream"
        
    actual_path = resolve_filepath(doc_ver.filepath)
    return FileResponse(actual_path, media_type=mime_type, filename=doc.original_filename)


import json
import os

@app.get("/eval-results")
def get_eval_results(current_user: models.User = Depends(get_current_user)):
    try:
        with open("eval/results.json", "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Evaluation results not found. Run eval script first.")

@app.post("/requests/{req_id}/generate-correction-message")
def generate_correction_message(req_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not req or current_user.role not in ["Reviewer", "Approver"]:
        raise HTTPException(status_code=403)
        
    verifications = db.query(models.VerificationCheck).filter(models.VerificationCheck.request_id == req.id).all()
    failed = [v for v in verifications if v.result != "PASS"]
    
    if not failed:
        return {"message": "All verification checks have passed. No corrections needed."}
        
    msg = "Please review your request. The following issues were found:\n"
    for v in failed:
        msg += f"- {v.rule_name}: {v.evidence}\n"
    
    return {"message": msg}

@app.get("/requests/{req_id}/corrections", response_model=schemas.CorrectionAssistanceOut)
def get_corrections(req_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Only reviewers or approvers may request correction assistance
    if current_user.role not in ["Reviewer", "Approver"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions for correction assistance")
    req = db.query(models.Request).filter(models.Request.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    # Gather latest extraction values per field
    docs = db.query(models.Document).filter(models.Document.request_id == req_id).all()
    extracted_vals = {}
    corrected_vals = {}
    for doc in docs:
        latest_ver = db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == doc.id).order_by(models.DocumentVersion.version_number.desc()).first()
        if not latest_ver:
            continue
        run = db.query(models.ExtractionRun).filter(models.ExtractionRun.document_version_id == latest_ver.id).order_by(models.ExtractionRun.id.desc()).first()
        if not run:
            continue
        fields = db.query(models.ExtractedField).filter(models.ExtractedField.extraction_run_id == run.id).all()
        for f in fields:
            extracted_vals[f.field_name] = f.original_value
            if f.corrected_value is not None:
                corrected_vals[f.field_name] = f.corrected_value
    # Gather verification failures for context
    verifs = db.query(models.VerificationCheck).filter(models.VerificationCheck.request_id == req_id).all()
    failed_rules = [v.rule_name for v in verifs if v.result != "PASS"]
    # Build suggestion objects
    suggestions = []
    for field_name, ex_val in extracted_vals.items():
        suggestion = schemas.CorrectionSuggestion(
            field_name=field_name,
            extracted_value=ex_val,
            corrected_value=corrected_vals.get(field_name),
            evidence="Latest extraction from document"
        )
        suggestions.append(suggestion)
    # Generate a friendly message via LLM (fallback if unavailable)
    draft_msg = llm.generate_correction_draft(extracted_vals, failed_rules)
    return schemas.CorrectionAssistanceOut(
        request_id=req_id,
        suggestions=suggestions,
        message=draft_msg
    )
