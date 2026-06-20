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
ISO_ANALYSIS_TOTAL = Counter('iso_analysis_total', 'Total number of ISO files analyzed by result', ['result'])
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

from pydantic import BaseModel

@app.get("/")
def health_check():
    return {"status": "ok"}

TEST_FILES_DIR = "/app/iso-test-files" if os.getenv("DATABASE_URL") else "../iso-test-files"

class TestScanReq(BaseModel):
    file_name: str

@app.get("/test-files")
def get_test_files():
    if not os.path.exists(TEST_FILES_DIR):
        return []
    return sorted([f for f in os.listdir(TEST_FILES_DIR) if f.endswith(".iso")])

def update_analysis_metrics(ingestion, metadata, checksum, filesystem, ocr, alerting):
    result_label = "unknown"
    if ingestion.get("fake_iso_detected"):
        result_label = "fake"
    elif not ingestion.get("is_large_enough"):
        result_label = "truncated"
    elif not ingestion.get("is_readable") or not filesystem.get("success") or not metadata.get("success"):
        result_label = "defective"
    elif checksum.get("status") == "fail" or filesystem.get("suspicious_files") or filesystem.get("rpm_signature_failure") or ocr.get("suspicious_text_found"):
        result_label = "edited"
    elif alerting.get("status") in ["TRUSTED", "LIKELY_SAFE_BUT_UNVERIFIED"] or alerting.get("risk_score") == 0:
        result_label = "valid"
        
    ISO_ANALYSIS_TOTAL.labels(result=result_label).inc()

@app.post("/scan")
async def scan_iso(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ISO_SCAN_TOTAL.inc()
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    async def generate():
        import json
        import asyncio

        yield json.dumps({"step": "init", "message": "File uploaded. Starting scan..."}) + "\n"
        await asyncio.sleep(0.5)

        # 1. Ingestion
        yield json.dumps({"step": "Ingestion", "status": "running"}) + "\n"
        ingestion = await asyncio.to_thread(IngestionAgent(file_path).analyze)
        yield json.dumps({"step": "Ingestion", "status": "done", "result": ingestion}) + "\n"
        await asyncio.sleep(0.5)
        
        # 2. Metadata
        yield json.dumps({"step": "Metadata", "status": "running"}) + "\n"
        metadata = await asyncio.to_thread(MetadataAgent(file_path).analyze)
        yield json.dumps({"step": "Metadata", "status": "done", "result": metadata}) + "\n"
        await asyncio.sleep(0.5)
        
        # 3. Checksum
        yield json.dumps({"step": "Checksum", "status": "running"}) + "\n"
        checksum = await asyncio.to_thread(ChecksumAgent(file_path, MANIFEST_PATH).analyze)
        yield json.dumps({"step": "Checksum", "status": "done", "result": checksum}) + "\n"
        await asyncio.sleep(0.5)
        
        # 4. Filesystem
        yield json.dumps({"step": "Filesystem", "status": "running"}) + "\n"
        fs_extract_dir = os.path.join(EXTRACT_DIR, file.filename + "_ext")
        filesystem = await asyncio.to_thread(FilesystemAgent(file_path, fs_extract_dir).analyze)
        yield json.dumps({"step": "Filesystem", "status": "done", "result": filesystem}) + "\n"
        await asyncio.sleep(0.5)
        
        # 5. Optional OCR
        yield json.dumps({"step": "OCR", "status": "running"}) + "\n"
        ocr = await asyncio.to_thread(OCRAgent(filesystem.get("extracted_images", [])).analyze)
        yield json.dumps({"step": "OCR", "status": "done", "result": ocr}) + "\n"
        await asyncio.sleep(0.5)
        
        # 6. Alerting / Risk Score
        yield json.dumps({"step": "Alerting", "status": "running"}) + "\n"
        alerting = await asyncio.to_thread(AlertingAgent(ingestion, metadata, checksum, filesystem, ocr).analyze)
        yield json.dumps({"step": "Alerting", "status": "done", "result": alerting}) + "\n"

        status = alerting["status"]
        risk_score = alerting["risk_score"]
        severity = alerting["severity"]

        # Update metrics
        ISO_RISK_SCORE.set(risk_score)
        ISO_CHECKSUM_MATCH.set(1 if checksum.get("status") == "pass" else 0)
        ISO_SIGNATURE_VALID.set(0 if filesystem.get("rpm_signature_failure") else 1)
        ISO_SUSPICIOUS_FILES.set(len(filesystem.get("suspicious_files", [])))
        ISO_OCR_SUSPICIOUS_WORDS.set(len(ocr.get("found_words", [])))
        update_analysis_metrics(ingestion, metadata, checksum, filesystem, ocr, alerting)

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

        yield json.dumps({
            "step": "complete",
            "scan_id": db_scan.scan_id,
            "file_name": db_scan.file_name,
            "final_status": status,
            "severity": severity,
            "risk_score": risk_score,
            "risk_percentage": alerting.get("risk_percentage", 0)
        }) + "\n"

    from fastapi.responses import StreamingResponse
    return StreamingResponse(generate(), media_type="application/x-ndjson")

@app.post("/scan-test")
async def scan_test_iso(req: TestScanReq, db: Session = Depends(get_db)):
    ISO_SCAN_TOTAL.inc()
    
    file_path = os.path.join(TEST_FILES_DIR, req.file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Test file not found")
        
    target_path = os.path.join(UPLOAD_DIR, req.file_name)
    shutil.copy2(file_path, target_path)

    async def generate():
        import json
        import asyncio

        yield json.dumps({"step": "init", "message": f"Test file {req.file_name} selected. Starting scan..."}) + "\n"
        await asyncio.sleep(0.5)

        # 1. Ingestion
        yield json.dumps({"step": "Ingestion", "status": "running"}) + "\n"
        ingestion = await asyncio.to_thread(IngestionAgent(target_path).analyze)
        yield json.dumps({"step": "Ingestion", "status": "done", "result": ingestion}) + "\n"
        await asyncio.sleep(0.5)
        
        # 2. Metadata
        yield json.dumps({"step": "Metadata", "status": "running"}) + "\n"
        metadata = await asyncio.to_thread(MetadataAgent(target_path).analyze)
        yield json.dumps({"step": "Metadata", "status": "done", "result": metadata}) + "\n"
        await asyncio.sleep(0.5)
        
        # 3. Checksum
        yield json.dumps({"step": "Checksum", "status": "running"}) + "\n"
        checksum = await asyncio.to_thread(ChecksumAgent(target_path, MANIFEST_PATH).analyze)
        yield json.dumps({"step": "Checksum", "status": "done", "result": checksum}) + "\n"
        await asyncio.sleep(0.5)
        
        # 4. Filesystem
        yield json.dumps({"step": "Filesystem", "status": "running"}) + "\n"
        fs_extract_dir = os.path.join(EXTRACT_DIR, req.file_name + "_ext")
        filesystem = await asyncio.to_thread(FilesystemAgent(target_path, fs_extract_dir).analyze)
        yield json.dumps({"step": "Filesystem", "status": "done", "result": filesystem}) + "\n"
        await asyncio.sleep(0.5)
        
        # 5. Optional OCR
        yield json.dumps({"step": "OCR", "status": "running"}) + "\n"
        ocr = await asyncio.to_thread(OCRAgent(filesystem.get("extracted_images", [])).analyze)
        yield json.dumps({"step": "OCR", "status": "done", "result": ocr}) + "\n"
        await asyncio.sleep(0.5)
        
        # 6. Alerting / Risk Score
        yield json.dumps({"step": "Alerting", "status": "running"}) + "\n"
        alerting = await asyncio.to_thread(AlertingAgent(ingestion, metadata, checksum, filesystem, ocr).analyze)
        yield json.dumps({"step": "Alerting", "status": "done", "result": alerting}) + "\n"

        status = alerting["status"]
        risk_score = alerting["risk_score"]
        severity = alerting["severity"]
        risk_percentage = alerting.get("risk_percentage", 0)

        # Update metrics
        ISO_RISK_SCORE.set(risk_score)
        ISO_CHECKSUM_MATCH.set(1 if checksum.get("status") == "pass" else 0)
        ISO_SIGNATURE_VALID.set(0 if filesystem.get("rpm_signature_failure") else 1)
        ISO_SUSPICIOUS_FILES.set(len(filesystem.get("suspicious_files", [])))
        ISO_OCR_SUSPICIOUS_WORDS.set(len(ocr.get("found_words", [])))
        update_analysis_metrics(ingestion, metadata, checksum, filesystem, ocr, alerting)

        # Save to database
        db_scan = ScanResult(
            file_name=req.file_name,
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
            os.remove(target_path)
            shutil.rmtree(fs_extract_dir, ignore_errors=True)
        except:
            pass

        yield json.dumps({
            "step": "complete",
            "scan_id": db_scan.scan_id,
            "file_name": db_scan.file_name,
            "final_status": status,
            "severity": severity,
            "risk_score": risk_score,
            "risk_percentage": risk_percentage
        }) + "\n"

    from fastapi.responses import StreamingResponse
    return StreamingResponse(generate(), media_type="application/x-ndjson")

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
