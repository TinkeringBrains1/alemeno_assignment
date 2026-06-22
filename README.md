# **AI-Powered Transaction Pipeline**

A resilient, highly-scalable asynchronous ETL pipeline that ingests financial transaction data, performs mathematical anomaly detection, and utilizes the Gemini 3.1 Flash Lite LLM for dynamic categorization and financial narrative generation.

## **Tech Stack**

* **Web Framework:** FastAPI (Asynchronous, non-blocking HTTP API)  
* **Background Processing:** Celery (Distributed task queue)  
* **Message Broker:** Redis (In-memory buffer)  
* **Database:** PostgreSQL (Relational integrity \+ JSONB support)  
* **Data Processing:** Pandas (Vectorized anomaly detection)  
* **AI Inference:** Google Gemini API 
* **Infrastructure:** Docker & Docker Compose

## 

## **Local Setup & Installation**

**Prerequisites:** You must have Docker and Docker Compose installed on your machine.  
**1\. Clone the repository**  
```
git clone \<your-repo-url\>  
cd \<your-repo-folder\>
```
**2\. Configure Environment Variables**  
Create a .env file in the root directory using the provided example:  
```
cp .env.example .env
```
Open .env and insert your actual GEMINI\_API\_KEY.  
**3\. Build and Run the Containers**  
```
docker compose up \--build
```
The FastAPI application will be available at http://localhost:8000. You can view the interactive Swagger UI documentation at http://localhost:8000/docs.

## **Testing**

You can test the endpoints using the Swagger UI (/docs), or via the terminal using the following curl commands:

### **1\. Upload a CSV File (Async Trigger)**

This endpoint accepts a CSV file, creates a pending job, and returns a job\_id.  
```
curl \-X POST "http://localhost:8000/jobs/upload" \\  
  \-H "accept: application/json" \\  
  \-H "Content-Type: multipart/form-data" \\  
  \-F "file=@data/transactions.csv"
```
*Expected Response:* {"job\_id": 1, "message": "File uploaded successfully. Processing in background."}

### **2\. Poll Job Status**


Use the job\_id from the previous step to check if the worker has finished processing.  
```
curl \-X GET "http://localhost:8000/jobs/1/status" \\  
  \-H "accept: application/json"
```

### **3\. Fetch Final Enriched Results**

Once the status is "completed", retrieve the fully cleaned dataset, calculated anomalies, and the AI-generated financial narrative.  
```
curl \-X GET "http://localhost:8000/jobs/1/results" \\  
  \-H "accept: application/json"
```
### **4\. List All Jobs**

Filter your processed jobs by status (e.g., completed, pending, processing, failed).  
```
curl \-X GET "http://localhost:8000/jobs?status=completed" \\  
  \-H "accept: application/json"
```
## **Folder Structure**

```
├── app/  
│   ├── main.py          \# FastAPI application and routing  
│   ├── worker.py        \# Celery background tasks & Gemini logic  
│   ├── models.py        \# SQLAlchemy database schemas  
│   ├── schemas.py       \# Pydantic data validation schemas  
│   └── core/  
│       └── database.py  \# PostgreSQL connection engine  
├── data/  
│   ├── .gitkeep         \# Preserves required folder structure  
│   └── uploads/         \# Temporary CSV storage before processing  
├── .env.example         \# Template for environment variables  
├── .gitignore           \# Secures API keys and local environment  
├── docker-compose.yml   \# Multi-container orchestration  
├── Dockerfile           \# Python environment setup  
└── requirements.txt     \# Python dependencies  
```
