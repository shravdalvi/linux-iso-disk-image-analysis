# ISO Guardian 🛡️
**Dockerized Agent-Based ISO Integrity Verification System with OCR, Prometheus, Grafana, and Web Dashboard**

## Project Overview
ISO Guardian is an agent-based forensic tool that analyzes Linux ISO images (like Fedora/RHEL) to determine if they are trusted, modified, corrupted, or fabricated. It uses an extensible 5-agent pipeline + an optional OCR module to score the risk level of uploaded ISOs.

## Architecture
- **Frontend**: React (Vite)
- **Backend**: Python FastAPI
- **Database**: SQLite
- **Monitoring**: Prometheus
- **Dashboard**: Grafana
- **Deployment**: Docker Compose

## Setup & Running
1. Make sure Docker and Docker Compose are installed.
2. In the `iso-guardian` directory, run:
   ```bash
   docker compose up --build
   ```
3. Access the services:
   - **Frontend UI**: http://localhost:3000
   - **Backend API Docs**: http://localhost:8000/docs
   - **Prometheus**: http://localhost:9090
   - **Grafana**: http://localhost:3001

## How to Test

### 1. Original Fedora ISO
- Download a real Fedora ISO.
- Add its SHA256 checksum to `backend/trusted_manifest.json` in this format:
  ```json
  {
      "fedora-real.iso": { "sha256": "the_actual_sha256_here" }
  }
  ```
- Upload via the UI.
- **Expected Status**: `TRUSTED` (Risk Score: 0)

### 2. Tampered ISO
- Copy the original ISO: `cp fedora-real.iso tampered.iso`
- Modify it slightly: `echo "malicious-change" >> tampered.iso`
- Upload `tampered.iso` via the UI.
- **Expected Status**: `MODIFIED_OR_FABRICATED` (Because checksum fails).

### 3. Fake ISO
- Create a text file: `echo "This is a fake file" > fake.iso`
- Upload `fake.iso` via the UI.
- **Expected Status**: `FABRICATED_OR_INVALID` (The `file` command inside the Ingestion agent detects it's ASCII text, not an ISO9660 filesystem).

## Grafana Dashboard Setup
1. Open Grafana at `http://localhost:3001` (login: admin / admin).
2. Go to **Connections > Data Sources > Add data source**.
3. Select **Prometheus**. Set the URL to `http://prometheus:9090`. Click **Save & Test**.
4. Go to **Dashboards > New Dashboard**. Add the following panels by using these PromQL queries:
   - **Total ISO Scans**: `iso_scan_total` (Stat panel)
   - **Latest Risk Score**: `iso_risk_score` (Stat panel)
   - **Checksum Failed Count**: `sum(iso_checksum_match == 0)` (Stat panel)
   - **Suspicious Files Found**: `iso_suspicious_files` (Time series)
   - **OCR Suspicious Words**: `iso_ocr_suspicious_words` (Stat panel)

## Grafana Alert Rules
In Grafana, go to **Alerting > Alert rules** to create rules for:
1. `iso_risk_score > 70` (High-severity tamper alert)
2. `iso_checksum_match == 0` (Immediate mismatch alert)
3. `iso_suspicious_files > 0` (Malware payload detected)
4. `iso_ocr_suspicious_words > 0` (OCR found suspicious watermarks/text)
