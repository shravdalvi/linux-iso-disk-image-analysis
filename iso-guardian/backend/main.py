import os
import shutil
from fastapi import FastAPI, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app, Counter, Gauge
from sqlalchemy.orm import Session

from database import engine, get_db, Base, ISOAnalysisResult
from agents.ingestion import IngestionAgent
from agents.metadata import MetadataAgent
from agents.checksum import ChecksumAgent
from agents.filesystem import FilesystemAgent
from agents.alerting import AlertingAgent

app = FastAPI(title="ISO Guardian API")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics setup
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

ISO_ANALYZED_TOTAL = Counter('iso_analyzed_total', 'Total number of ISOs analyzed')
ISO_STATUS_COUNTER = Counter('iso_status_total', 'Count of ISOs by status', ['status'])
ISO_RISK_SCORE = Gauge('iso_risk_score', 'Risk score of the last analyzed ISO')

UPLOAD_DIR = "../data/uploads"
MANIFEST_PATH = "manifest.json"

os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/analyze")
async def analyze_iso(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ISO_ANALYZED_TOTAL.inc()
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Ingestion
    ingestion = IngestionAgent(file_path).analyze()
    
    # 2. Metadata
    metadata = MetadataAgent(file_path).analyze()
    
    # 3. Checksum
    checksum = ChecksumAgent(file_path, MANIFEST_PATH).analyze()
    
    # 4. Filesystem
    filesystem = FilesystemAgent(file_path).analyze()
    
    # 5. Alerting
    alerting = AlertingAgent(ingestion, metadata, checksum, filesystem).analyze()

    status = alerting["status"]
    risk_score = alerting["risk_score"]

    # Update metrics
    ISO_STATUS_COUNTER.labels(status=status).inc()
    ISO_RISK_SCORE.set(risk_score)

    # Save to database
    db_result = ISOAnalysisResult(
        filename=file.filename,
        checksum=checksum.get("calculated_sha256", "UNKNOWN"),
        status=status,
        risk_score=risk_score,
        details={
            "ingestion": ingestion,
            "metadata": metadata,
            "checksum": checksum,
            "filesystem": filesystem,
            "alerting": alerting
        }
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)

    # Clean up upload
    os.remove(file_path)

    return {
        "id": db_result.id,
        "filename": db_result.filename,
        "status": status,
        "risk_score": risk_score,
        "details": db_result.details
    }

@app.get("/api/results")
def get_results(db: Session = Depends(get_db)):
    results = db.query(ISOAnalysisResult).order_by(ISOAnalysisResult.id.desc()).all()
    return results
