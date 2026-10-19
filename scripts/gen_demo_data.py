import os
import sys
import shutil
sys.path.append(os.path.abspath('backend'))
from database import SessionLocal, engine
import models
from datetime import datetime

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

def create_synthetic_demo_data():
    print("Generating synthetic demo scenarios...")
    # Clear existing demo data
    db.query(models.Request).filter(models.Request.category == "Synthetic Demo").delete()
    
    # Ensure users exist
    submitter = db.query(models.User).filter_by(username="alice").first()
    if not submitter:
        submitter = models.User(username="alice", role="Submitter")
        db.add(submitter)
        
    reviewer = db.query(models.User).filter_by(username="bob").first()
    if not reviewer:
        reviewer = models.User(username="bob", role="Reviewer")
        db.add(reviewer)
        
    db.commit()
    
    scenarios = [
        {"type": "Travel", "status": "Under Review", "amount": 150.00, "merchant": "Uber", "desc": "VALID_APPROVAL"},
        {"type": "Meals", "status": "Under Review", "amount": 450.00, "merchant": "Steakhouse", "desc": "AMOUNT_MISMATCH"},
        {"type": "Travel", "status": "Under Review", "amount": 200.00, "merchant": "Delta", "desc": "DATE_MISMATCH"},
        {"type": "Supplies", "status": "Under Review", "amount": 50.00, "merchant": "Staples", "desc": "MISSING_REQUIRED_FIELD"},
        {"type": "Other", "status": "Under Review", "amount": 10.00, "merchant": "Unknown", "desc": "MISSING_DOCUMENT"},
        {"type": "Meals", "status": "Under Review", "amount": 150.00, "merchant": "Uber", "desc": "POSSIBLE_DUPLICATE"},
        {"type": "Travel", "status": "Under Review", "amount": 300.00, "merchant": "Hilton", "desc": "OCR_CORRECTION"},
        {"type": "Travel", "status": "Under Review", "amount": 300.00, "merchant": "Hilton", "desc": "DOCUMENT_REPLACEMENT"},
        {"type": "Meals", "status": "More Information Required", "amount": 120.00, "merchant": "Cafe", "desc": "MORE_INFORMATION_REQUIRED"},
        {"type": "Supplies", "status": "Submitted", "amount": 25.00, "merchant": "Amazon", "desc": "RESUBMITTED_AFTER_CORRECTION"},
        {"type": "Other", "status": "Processing Failed", "amount": 0.0, "merchant": "", "desc": "PROCESSING_FAILED"},
        {"type": "Travel", "status": "Approved", "amount": 90.00, "merchant": "Lyft", "desc": "APPROVED"},
        {"type": "Meals", "status": "Rejected", "amount": 800.00, "merchant": "Luxury Dining", "desc": "REJECTED"}
    ]
    
    for s in scenarios:
        req = models.Request(
            submitter_id=submitter.id,
            assigned_reviewer_id=reviewer.id if s['status'] not in ['Draft', 'Approved', 'Rejected'] else None,
            type=s['type'],
            category="Synthetic Demo",
            status=s['status'],
            expense_amount=s['amount'],
            merchant_name=f"{s['merchant']} - {s['desc']}"
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        
        # Add basic audit logs to make it look realistic
        log = models.AuditLog(
            request_id=req.id,
            action="Status Changed",
            from_status="Draft",
            to_status=s['status'],
            timestamp=datetime.utcnow()
        )
        db.add(log)
        
        if s['status'] == "More Information Required":
            mir_log = models.AuditLog(
                request_id=req.id,
                actor_id=reviewer.id,
                action="request_correction",
                from_status="Under Review",
                to_status="More Information Required",
                reason="The receipt is illegible. Please re-upload a clearer image.",
                timestamp=datetime.utcnow()
            )
            db.add(mir_log)
            
    db.commit()
    print("Created 13 synthetic demo scenarios successfully.")

if __name__ == "__main__":
    create_synthetic_demo_data()
