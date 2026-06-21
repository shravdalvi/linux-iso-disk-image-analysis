import subprocess
import os

class MetadataAgent:
    def __init__(self, filepath):
        self.filepath = filepath

    def analyze(self):
        metadata = {
            "agent": "Metadata",
            "is_bootable": False,
            "volume_id": "Unknown",
            "suspicious_metadata": False,
            "success": False,
            "warnings": []
        }

        if not os.path.exists(self.filepath):
            return metadata

        try:
            # Check using 'xorriso' command
            xorriso_result = subprocess.run(["xorriso", "-indev", self.filepath, "-pvd_info"], capture_output=True, text=True, timeout=10)
            output = xorriso_result.stdout

            for line in output.split('\n'):
                if "Volume Id" in line:
                    metadata["volume_id"] = line.split(':', 1)[1].strip()
                if "El Torito" in line or "boot" in line.lower():
                    metadata["is_bootable"] = True
            
            # Using 7z l to check metadata basics
            try:
                z_result = subprocess.run(["7z", "l", self.filepath], capture_output=True, text=True, timeout=10)
                if "Type = Iso" in z_result.stdout:
                    metadata["success"] = True
            except:
                pass

            if not metadata["is_bootable"]:
                metadata["warnings"].append("ISO does not appear to be bootable.")
                metadata["suspicious_metadata"] = True

        except Exception as e:
            metadata["error"] = str(e)
            metadata["warnings"].append("Failed to extract metadata")

        if metadata["suspicious_metadata"]:
            metadata["explanation"] = "The ISO structure or boot details look unusual."
        elif not metadata["success"]:
            metadata["explanation"] = "The system could not properly inspect the ISO contents."
        else:
            metadata["explanation"] = f"The ISO is built like a proper Linux installation image. Volume ID: {metadata['volume_id']}."

        return metadata
