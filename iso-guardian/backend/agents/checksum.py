import hashlib
import json
import os

class ChecksumAgent:
    def __init__(self, filepath, manifest_path):
        self.filepath = filepath
        self.manifest_path = manifest_path

    def analyze(self):
        result = {
            "agent": "Checksum",
            "calculated_sha256": None,
            "status": "unknown" # pass, fail, or unknown
        }

        if not os.path.exists(self.filepath):
            return result

        # Calculate SHA256
        sha256_hash = hashlib.sha256()
        try:
            with open(self.filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            result["calculated_sha256"] = sha256_hash.hexdigest()
        except Exception as e:
            result["error"] = str(e)
            return result

        # Check against manifest
        filename = os.path.basename(self.filepath)
        try:
            with open(self.manifest_path, 'r') as mf:
                manifest = json.load(mf)
                
            if filename in manifest:
                expected_sha = manifest[filename]["sha256"]
                if result["calculated_sha256"] == expected_sha:
                    result["status"] = "pass"
                else:
                    result["status"] = "fail"
            else:
                result["status"] = "unknown"
        except Exception as e:
            result["error"] = str(e)

        return result
