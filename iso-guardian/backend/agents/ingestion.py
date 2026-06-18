import os
import mimetypes

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
        mime_type, _ = mimetypes.guess_type(self.filepath)
        
        valid_iso = ext.lower() == '.iso'
        
        # Simple size check: an ISO should be at least 1MB
        is_large_enough = size_bytes > 1024 * 1024
        
        return {
            "agent": "Ingestion",
            "filename": filename,
            "size_bytes": size_bytes,
            "is_readable": is_readable,
            "extension": ext,
            "mime_type": mime_type,
            "valid_iso_extension": valid_iso,
            "is_large_enough": is_large_enough,
            "success": is_readable and valid_iso and is_large_enough
        }
