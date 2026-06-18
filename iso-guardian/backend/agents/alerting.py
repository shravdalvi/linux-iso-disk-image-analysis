class AlertingAgent:
    def __init__(self, ingestion_res, metadata_res, checksum_res, fs_res, ocr_res):
        self.ingestion = ingestion_res
        self.metadata = metadata_res
        self.checksum = checksum_res
        self.fs = fs_res
        self.ocr = ocr_res

    def analyze(self):
        # Risk score starts at 0, goes up to 100
        score = 0
        reasons = []

        # Ingestion Check
        if not self.ingestion.get("success") or self.ingestion.get("fake_iso_detected"):
            score += 40
            reasons.append("Invalid ISO or fake extension detected")

        # Metadata Check
        if self.metadata.get("suspicious_metadata"):
            score += 10
            reasons.append("Metadata warning (e.g., not bootable)")

        # Checksum Check
        c_status = self.checksum.get("status")
        if c_status == "fail":
            score += 50
            reasons.append("Checksum mismatch (Tampered)")
        elif c_status == "unknown":
            score += 10
            reasons.append("No trusted checksum found in manifest")

        # Filesystem Check
        if not self.fs.get("success"):
            score += 35
            reasons.append("Filesystem inspection failure")
        else:
            if len(self.fs.get("suspicious_files", [])) > 0:
                score += 20
                reasons.append(f"Suspicious file found: {self.fs.get('suspicious_files')}")
            if self.fs.get("rpm_signature_failure"):
                score += 30
                reasons.append("RPM signature failure")

        # OCR Check
        if self.ocr.get("suspicious_text_found"):
            score += 15
            reasons.append(f"OCR suspicious text found: {self.ocr.get('found_words')}")

        # Clamp score between 0 and 100
        score = max(0, min(100, score))

        # Determine Final Status
        status = "UNKNOWN"
        severity = "INFO"

        if score == 0 and c_status == "pass":
            status = "TRUSTED"
            severity = "LOW"
        elif score <= 10 and c_status == "unknown" and not self.fs.get("suspicious_files"):
            status = "LIKELY_SAFE_BUT_UNVERIFIED"
            severity = "LOW"
        elif score >= 50 and c_status == "fail":
            status = "MODIFIED_OR_FABRICATED"
            severity = "CRITICAL"
        elif self.ingestion.get("fake_iso_detected"):
            status = "FABRICATED_OR_INVALID"
            severity = "CRITICAL"
        elif score >= 40:
            status = "SUSPICIOUS"
            severity = "HIGH"
        elif not self.ingestion.get("success") or not self.metadata.get("success"):
            status = "CORRUPTED"
            severity = "HIGH"
        else:
            status = "UNKNOWN"
            severity = "MEDIUM"

        return {
            "agent": "Alerting",
            "risk_score": score,
            "status": status,
            "severity": severity,
            "reasons": reasons
        }
