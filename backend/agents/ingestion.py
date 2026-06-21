import os
import mimetypes
import subprocess

class IngestionAgent:
    def __init__(self, filepath):
        self.filepath = filepath

    def analyze(self):
        if not os.path.exists(self.filepath):
            return {"status": "error", "message": "File does not exist"}
        
        filename = os.path.basename(self.filepath)
        size_bytes = os.path.getsize(self.filepath)
        is_readable = os.access(self.filepath, os.R_OK)
        
        _, ext = os.path.splitext(filename)
        
        valid_iso_ext = ext.lower() == '.iso'
        
        # Simple size check: an ISO should be at least 1MB
        is_large_enough = size_bytes > 1024 * 1024
        
        # Check using 'file' command to detect fake files renamed as .iso
        file_cmd_output = ""
        try:
            result = subprocess.run(["file", "-b", self.filepath], capture_output=True, text=True, timeout=5)
            file_cmd_output = result.stdout.strip().lower()
        except Exception:
            pass

        looks_like_iso = "iso 9660" in file_cmd_output or "boot sector" in file_cmd_output

        fake_iso_detected = valid_iso_ext and not looks_like_iso

        explanation = ""
        if fake_iso_detected:
            explanation = "The file has a .iso extension but its content format does not match ISO 9660 or boot sector standards."
        elif not valid_iso_ext:
            explanation = f"The file has an invalid extension: '{ext}'."
        elif not is_large_enough:
            explanation = "The file is too small to be a valid ISO image."
        elif not is_readable:
            explanation = "The file cannot be read from the disk."
        else:
            explanation = "The file is successfully ingested, has valid ISO 9660 structure, proper size, and extension."

        return {
            "agent": "Ingestion",
            "filename": filename,
            "size_bytes": size_bytes,
            "is_readable": is_readable,
            "extension": ext,
            "valid_iso_extension": valid_iso_ext,
            "is_large_enough": is_large_enough,
            "fake_iso_detected": fake_iso_detected,
            "file_command_output": file_cmd_output,
            "success": is_readable and is_large_enough and looks_like_iso,
            "explanation": explanation
        }
