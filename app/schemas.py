from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class JobStatusResponse(BaseModel):
    id: int
    status: str
    filename: str
    row_count_raw: int
    row_count_clean: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class JobSummaryData(BaseModel):
    total_spend_inr: float
    total_spend_usd: float
    top_merchants: Optional[Dict[str, Any]] = None
    anomaly_count: int
    narrative: Optional[str] = None
    risk_level: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class TransactionData(BaseModel):
    txn_id: Optional[str]
    date: Optional[datetime]
    merchant: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    status: Optional[str]
    category: Optional[str]
    is_anomaly: bool
    anomaly_reason: Optional[str]
    llm_category: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class JobResultsResponse(BaseModel):
    job: JobStatusResponse
    summary: Optional[JobSummaryData] = None
    transactions: List[TransactionData] = []