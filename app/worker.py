import os
import json
import time
import pandas as pd
import google.generativeai as genai
from datetime import datetime
from celery import Celery
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Job, JobStatus, Transaction, JobSummary

celery_app = Celery("pipeline_tasks", broker=os.getenv("REDIS_URL", "redis://redis:6379/0"))

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.1-flash-lite")

def call_llm_with_retry(prompt: str, retries: int = 3):
    for attempt in range(retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            return response.text
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt)

@celery_app.task(bind=True)
def process_csv_task(self, job_id: int, file_path: str):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    job.status = JobStatus.PROCESSING
    db.commit()

    try:
        df = pd.read_csv(file_path)
        job.row_count_raw = len(df)

        df = df.drop_duplicates()

        df['amount'] = df['amount'].astype(str).str.replace(r'[\$,]', '', regex=True).astype(float)
        df['date'] = pd.to_datetime(df['date'], dayfirst=True, format='mixed', errors='coerce').dt.strftime('%Y-%m-%dT%H:%M:%S')
        df['status'] = df['status'].astype(str).str.upper()
        df['category'] = df['category'].fillna('Uncategorised')
        df['currency'] = df['currency'].astype(str).str.upper()

        df['is_anomaly'] = False
        df['anomaly_reason'] = None

        medians = df.groupby('account_id')['amount'].median().to_dict()
        for index, row in df.iterrows():
            account_id = row['account_id']
            if pd.notna(account_id) and account_id in medians:
                if row['amount'] > 3 * medians[account_id]:
                    df.at[index, 'is_anomaly'] = True
                    df.at[index, 'anomaly_reason'] = "Amount exceeds 3x account median"

        domestic_merchants = ['SWIGGY', 'OLA', 'IRCTC']
        usd_mask = (df['currency'] == 'USD') & (df['merchant'].astype(str).str.upper().isin(domestic_merchants))
        df.loc[usd_mask, 'is_anomaly'] = True
        df.loc[usd_mask, 'anomaly_reason'] = "USD currency used for domestic merchant"

        uncategorised = df[df['category'] == 'Uncategorised']
        if not uncategorised.empty:
            batch_data = uncategorised[['txn_id', 'merchant', 'amount', 'currency']].to_dict(orient='records')
            prompt = f"""
            Classify the following transactions into exactly one of these categories: Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, Other.
            Return ONLY a JSON object where keys are txn_id and values are the category string.
            Transactions: {json.dumps(batch_data)}
            """
            llm_response = call_llm_with_retry(prompt)
            llm_failed = True
            
            if llm_response:
                try:
                    classifications = json.loads(llm_response)
                    for index, row in uncategorised.iterrows():
                        txn_id = row['txn_id']
                        if txn_id in classifications:
                            df.at[index, 'llm_category'] = classifications[txn_id]
                            df.at[index, 'category'] = classifications[txn_id]
                    llm_failed = False
                except json.JSONDecodeError:
                    pass
            
            if llm_failed:
                df['llm_failed'] = True

        job.row_count_clean = len(df)

        transactions = []
        for _, row in df.iterrows():
            txn = Transaction(
                job_id=job.id,
                txn_id=row.get('txn_id'),
                date=datetime.strptime(row['date'], '%Y-%m-%dT%H:%M:%S') if pd.notna(row.get('date')) else None,
                merchant=row.get('merchant'),
                amount=row.get('amount'),
                currency=row.get('currency'),
                status=row.get('status'),
                category=row.get('category'),
                account_id=row.get('account_id'),
                is_anomaly=row.get('is_anomaly', False),
                anomaly_reason=row.get('anomaly_reason'),
                llm_category=row.get('llm_category'),
                llm_failed=row.get('llm_failed', False)
            )
            transactions.append(txn)
        db.bulk_save_objects(transactions)

        total_inr = float(df[df['currency'] == 'INR']['amount'].sum())
        total_usd = float(df[df['currency'] == 'USD']['amount'].sum())
        anomaly_count = df['is_anomaly'].sum()
        top_merchants = df['merchant'].value_counts().head(3).to_dict()

        summary_prompt = f"""
        Analyze this transaction summary:
        Total Spend INR: {total_inr}
        Total Spend USD: {total_usd}
        Top Merchants: {json.dumps(top_merchants)}
        Anomaly Count: {anomaly_count}

        Return a strictly formatted JSON object with these exact keys:
        - "narrative": A 2-3 sentence spending narrative.
        - "risk_level": "low", "medium", or "high".
        """
        
        summary_response = call_llm_with_retry(summary_prompt)
        narrative = ""
        risk_level = "low"
        
        if summary_response:
            try:
                summary_data = json.loads(summary_response)
                narrative = summary_data.get("narrative", "")
                risk_level = summary_data.get("risk_level", "low")
            except json.JSONDecodeError:
                pass

        job_summary = JobSummary(
            job_id=job.id,
            total_spend_inr=total_inr,
            total_spend_usd=total_usd,
            top_merchants=top_merchants,
            anomaly_count=int(anomaly_count),
            narrative=narrative,
            risk_level=risk_level
        )
        db.add(job_summary)

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()
        if os.path.exists(file_path):
            os.remove(file_path)