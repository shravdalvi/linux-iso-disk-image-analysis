import os
import shutil
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app, Counter, Gauge
from sqlalchemy.orm import Session

from database import engine, get_db, Base, ScanResult, AgentResult
from agents.ingestion import IngestionAgent
from agents.metadata import MetadataAgent
from agents.checksum import ChecksumAgent
from agents.filesystem import FilesystemAgent
from agents.ocr_module import OCRAgent
from agents.alerting import AlertingAgent

app = FastAPI(title="ISO Guardian API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Prometheus Metrics
ISO_SCAN_TOTAL = Counter('iso_scan_total', 'Total number of ISOs scanned')
ISO_RISK_SCORE = Gauge('iso_risk_score', 'Risk score of the last analyzed ISO')
ISO_CHECKSUM_MATCH = Gauge('iso_checksum_match', '1 if checksum matches, 0 otherwise')
ISO_SIGNATURE_VALID = Gauge('iso_signature_valid', '1 if RPM signature valid, 0 otherwise')
ISO_SUSPICIOUS_FILES = Gauge('iso_suspicious_files', 'Count of suspicious files found in last scan')
ISO_OCR_SUSPICIOUS_WORDS = Gauge('iso_ocr_suspicious_words', 'Count of suspicious words found by OCR')

UPLOAD_DIR = "/app/data/uploads" if os.getenv("DATABASE_URL") else "../data/uploads"
EXTRACT_DIR = "/app/data/extracted" if os.getenv("DATABASE_URL") else "../data/extracted"
MANIFEST_PATH = "trusted_manifest.json"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXTRACT_DIR, exist_ok=True)

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/scan")
async def scan_iso(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ISO_SCAN_TOTAL.inc()
    
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
    fs_extract_dir = os.path.join(EXTRACT_DIR, file.filename + "_ext")
    filesystem = FilesystemAgent(file_path, fs_extract_dir).analyze()
    
    # 5. Optional OCR
    ocr = OCRAgent(filesystem.get("extracted_images", [])).analyze()
    
    # 6. Alerting / Risk Score
    alerting = AlertingAgent(ingestion, metadata, checksum, filesystem, ocr).analyze()

    status = alerting["status"]
    risk_score = alerting["risk_score"]
    severity = alerting["severity"]

    # Update metrics
    ISO_RISK_SCORE.set(risk_score)
    ISO_CHECKSUM_MATCH.set(1 if checksum.get("status") == "pass" else 0)
    ISO_SIGNATURE_VALID.set(0 if filesystem.get("rpm_signature_failure") else 1)
    ISO_SUSPICIOUS_FILES.set(len(filesystem.get("suspicious_files", [])))
    ISO_OCR_SUSPICIOUS_WORDS.set(len(ocr.get("found_words", [])))

    # Save to database
    db_scan = ScanResult(
        file_name=file.filename,
        file_hash=checksum.get("calculated_sha256", "UNKNOWN"),
        final_status=status,
        severity=severity,
        risk_score=risk_score
    )
    db.add(db_scan)
    db.commit()
    db.refresh(db_scan)

    agents_data = {
        "Ingestion": ingestion,
        "Metadata": metadata,
        "Checksum": checksum,
        "Filesystem": filesystem,
        "OCR": ocr,
        "Alerting": alerting
    }

    for agent_name, result in agents_data.items():
        db_agent = AgentResult(
            scan_id=db_scan.scan_id,
            agent_name=agent_name,
            status="done",
            result_json=result
        )
        db.add(db_agent)
    
    db.commit()

    # Clean up
    try:
        os.remove(file_path)
        shutil.rmtree(fs_extract_dir, ignore_errors=True)
    except:
        pass

    return {
        "scan_id": db_scan.scan_id,
        "file_name": db_scan.file_name,
        "final_status": status,
        "severity": severity,
        "risk_score": risk_score,
        "agents": agents_data
    }

@app.get("/scans")
def get_scans(db: Session = Depends(get_db)):
    scans = db.query(ScanResult).order_by(ScanResult.scan_id.desc()).all()
    return scans

@app.get("/scan/{scan_id}")
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(ScanResult).filter(ScanResult.scan_id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    agents = db.query(AgentResult).filter(AgentResult.scan_id == scan_id).all()
    
    return {
        "scan": scan,
        "agents": {a.agent_name: a.result_json for a in agents}
    }
