from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False) 
    status = Column(Enum(JobStatus), default=JobStatus.PENDING) 
    row_count_raw = Column(Integer, default=0) 
    row_count_clean = Column(Integer, default=0) 
    created_at = Column(DateTime, default=datetime.utcnow) 
    completed_at = Column(DateTime, nullable=True) 
    error_message = Column(String, nullable=True) 

    transactions = relationship("Transaction", back_populates="job", cascade="all, delete")
    summary = relationship("JobSummary", back_populates="job", uselist=False, cascade="all, delete")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True) 
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False) 
    
    # Raw Data
    txn_id = Column(String, nullable=True)
    date = Column(DateTime, nullable=True)
    merchant = Column(String, nullable=True) 
    amount = Column(Float, nullable=True) 
    currency = Column(String, nullable=True)
    status = Column(String, nullable=True) 
    category = Column(String, nullable=True) 
    account_id = Column(String, nullable=True) 
    
    # Anomaly Detection Flags
    is_anomaly = Column(Boolean, default=False) 
    anomaly_reason = Column(String, nullable=True) 
    
    # LLM Enrichments
    llm_category = Column(String, nullable=True) 
    llm_raw_response = Column(String, nullable=True)
    llm_failed = Column(Boolean, default=False) 

    job = relationship("Job", back_populates="transactions")

class JobSummary(Base):
    __tablename__ = "job_summaries"
    
    id = Column(Integer, primary_key=True, index=True) 
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, unique=True) 
    
    total_spend_inr = Column(Float, default=0.0) 
    total_spend_usd = Column(Float, default=0.0) 
    top_merchants = Column(JSON, nullable=True)  
    anomaly_count = Column(Integer, default=0)  
    narrative = Column(String, nullable=True)  
    risk_level = Column(String, nullable=True) 

    job = relationship("Job", back_populates="summary")