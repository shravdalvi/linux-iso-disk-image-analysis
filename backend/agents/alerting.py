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

        # Math calculation for percentage rating
        MAX_POSSIBLE_SCORE = 200
        raw_score = score
        risk_percentage = min(100.0, round((raw_score / MAX_POSSIBLE_SCORE) * 100.0, 2))

        # Determine Final Status
        status = "UNKNOWN"
        severity = "INFO"

        if score == 0 and c_status == "pass":
            status = "TRUSTED"
            severity = "LOW"
            explanation = "The ISO matches the trusted version and no suspicious activity was detected."
        elif score <= 10 and c_status == "unknown" and not self.fs.get("suspicious_files"):
            status = "LIKELY_SAFE_BUT_UNVERIFIED"
            severity = "LOW"
            explanation = "The ISO does not show dangerous signs, but it is not present in the trusted manifest, so the system cannot fully confirm its authenticity."
        elif score >= 50 and c_status == "fail":
            status = "MODIFIED_OR_FABRICATED"
            severity = "CRITICAL"
            explanation = "The ISO does not match the trusted version and may have been altered, replaced, or maliciously modified."
        elif self.ingestion.get("fake_iso_detected"):
            status = "MODIFIED_OR_FABRICATED"
            severity = "CRITICAL"
            explanation = "The file claims to be an ISO but does not behave like one internally."
        elif score >= 40:
            status = "SUSPICIOUS"
            severity = "HIGH"
            explanation = "The ISO may not be malicious, but it has enough unusual indicators that it should be reviewed before use."
        elif not self.ingestion.get("success") or not self.metadata.get("success"):
            status = "CORRUPTED"
            severity = "HIGH"
            explanation = "The file may be damaged, incomplete, or intentionally malformed."
        else:
            status = "UNKNOWN"
            severity = "MEDIUM"
            explanation = "The ISO may not be malicious, but it has enough unusual indicators that it should be reviewed before use."

        formula = "Risk Percentage = Total Penalty Points ÷ 200 × 100"

        return {
            "agent": "Alerting",
            "risk_score": score,
            "risk_percentage": risk_percentage,
            "status": status,
            "severity": severity,
            "reasons": reasons,
            "explanation": explanation,
            "formula_used": formula
        }
