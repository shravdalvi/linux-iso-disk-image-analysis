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
            "manifest_match": False,
            "found_in_manifest": False,
            "success": False
        }

        if not os.path.exists(self.filepath):
            return result

        # Calculate SHA256
        sha256_hash = hashlib.sha256()
        try:
            with open(self.filepath, "rb") as f:
                # Read and update hash string value in blocks of 4K
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            result["calculated_sha256"] = sha256_hash.hexdigest()
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
            return result

        # Check against manifest
        filename = os.path.basename(self.filepath)
        try:
            with open(self.manifest_path, 'r') as mf:
                manifest = json.load(mf)
                
            if filename in manifest:
                result["found_in_manifest"] = True
                expected_sha = manifest[filename]["sha256"]
                if result["calculated_sha256"] == expected_sha:
                    result["manifest_match"] = True
        except Exception as e:
            result["manifest_error"] = str(e)

        return result
