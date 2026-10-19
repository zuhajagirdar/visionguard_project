from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean, Date
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    role = Column(String)

class Request(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True, index=True)
    submitter_id = Column(Integer, ForeignKey("users.id"))
    assigned_reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type = Column(String)
    status = Column(String, default="Draft")
    expense_amount = Column(Float, nullable=True)
    merchant_name = Column(String, nullable=True)
    expense_date = Column(Date, nullable=True)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    documents = relationship("Document", back_populates="request")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"))
    original_filename = Column(String)
    file_type = Column(String)
    current_version = Column(Integer, default=1)
    
    request = relationship("Request", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document")

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    version_number = Column(Integer)
    filepath = Column(String)
    processing_state = Column(String, default="Pending")
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    document = relationship("Document", back_populates="versions")
    extraction_runs = relationship("ExtractionRun", back_populates="version")

class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    id = Column(Integer, primary_key=True, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"))
    engine = Column(String)
    engine_version = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String)
    error_message = Column(Text, nullable=True)
    
    version = relationship("DocumentVersion", back_populates="extraction_runs")
    extractions = relationship("ExtractedField", back_populates="run")

class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    id = Column(Integer, primary_key=True, index=True)
    extraction_run_id = Column(Integer, ForeignKey("extraction_runs.id"))
    field_name = Column(String)
    original_value = Column(String)
    corrected_value = Column(String, nullable=True)
    corrected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    corrected_at = Column(DateTime, nullable=True)
    confidence = Column(Float, nullable=True)
    
    run = relationship("ExtractionRun", back_populates="extractions")

class VerificationCheck(Base):
    __tablename__ = "verification_checks"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"))
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=True)
    rule_name = Column(String)
    evidence = Column(Text)
    result = Column(String)
    category = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    text = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"))
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String)
    from_status = Column(String)
    to_status = Column(String)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
