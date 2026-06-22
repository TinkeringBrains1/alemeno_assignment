from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
import os

from app.core.database import get_db, engine
from app.models import Base, Job, JobStatus, Transaction, JobSummary
from app.schemas import JobStatusResponse, JobResultsResponse
from app.worker import process_csv_task

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-Powered Transaction Pipeline")

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/jobs/upload", response_model=dict)
def upload_transactions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    job = Job(filename=file.filename, status=JobStatus.PENDING)
    db.add(job)
    db.commit()
    db.refresh(job)

    file_path = os.path.join(UPLOAD_DIR, f"{job.id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    process_csv_task.delay(job.id, file_path)

    return {"job_id": job.id, "message": "File uploaded and processing started."}

@app.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job

@app.get("/jobs/{job_id}/results", response_model=JobResultsResponse)
def get_job_results(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job is not completed yet.")

    transactions = db.query(Transaction).filter(Transaction.job_id == job_id).all()
    summary = db.query(JobSummary).filter(JobSummary.job_id == job_id).first()

    return {
        "job": job,
        "summary": summary,
        "transactions": transactions
    }

@app.get("/jobs", response_model=List[JobStatusResponse])
def list_jobs(status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    return query.all()