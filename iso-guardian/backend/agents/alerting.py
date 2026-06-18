class AlertingAgent:
    def __init__(self, ingestion_res, metadata_res, checksum_res, fs_res):
        self.ingestion = ingestion_res
        self.metadata = metadata_res
        self.checksum = checksum_res
        self.fs = fs_res

    def analyze(self):
        score = 0
        status = "UNKNOWN"
        reasons = []

        # Start with 100 and deduct for issues
        if self.ingestion.get("success"):
            score += 20
        else:
            reasons.append("Failed ingestion (Not a valid readable ISO)")

        if self.metadata.get("success"):
            score += 20
            if not self.metadata.get("is_bootable"):
                score -= 10
                reasons.append("ISO is not bootable")
        else:
            reasons.append("Failed metadata analysis")

        if self.checksum.get("success"):
            if self.checksum.get("manifest_match"):
                score += 40
            else:
                if self.checksum.get("found_in_manifest"):
                    score -= 50
                    reasons.append("Checksum MISMATCH with manifest (Tampered)")
                else:
                    score += 10
                    reasons.append("Checksum not found in trusted manifest")
        else:
            reasons.append("Failed checksum analysis")

        if self.fs.get("success"):
            score += 20
            if len(self.fs.get("suspicious_files", [])) > 0:
                score -= 60
                reasons.append(f"Suspicious files found: {self.fs.get('suspicious_files')}")
            
            # Missing critical directories
            if not self.fs.get("has_efi") and not self.fs.get("has_isolinux"):
                score -= 10
                reasons.append("Missing boot directories (EFI/isolinux)")
        else:
            reasons.append("Failed filesystem analysis")

        # Clamp score between 0 and 100
        score = max(0, min(100, score))

        # Classify
        if score == 100 and self.checksum.get("manifest_match"):
            status = "TRUSTED"
        elif score >= 80 and not self.checksum.get("found_in_manifest") and len(self.fs.get("suspicious_files", [])) == 0:
            status = "LIKELY_SAFE_BUT_UNVERIFIED"
        elif score < 40 or len(self.fs.get("suspicious_files", [])) > 0:
            status = "SUSPICIOUS"
            if self.checksum.get("found_in_manifest") and not self.checksum.get("manifest_match"):
                status = "MODIFIED_OR_FABRICATED"
        elif score == 0:
            status = "FABRICATED_OR_INVALID"
        elif not self.ingestion.get("success") or not self.metadata.get("success"):
            status = "CORRUPTED"
        else:
            status = "UNKNOWN"

        return {
            "agent": "Alerting",
            "risk_score": score,
            "status": status,
            "reasons": reasons
        }
