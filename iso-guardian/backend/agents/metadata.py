import subprocess
import os

class MetadataAgent:
    def __init__(self, filepath):
        self.filepath = filepath

    def analyze(self):
        metadata = {
            "agent": "Metadata",
            "file_output": "",
            "is_bootable": False,
            "volume_id": "Unknown",
            "success": False
        }

        if not os.path.exists(self.filepath):
            return metadata

        try:
            # Check using 'file' command
            result = subprocess.run(["file", self.filepath], capture_output=True, text=True, timeout=10)
            file_output = result.stdout.strip()
            metadata["file_output"] = file_output

            if "bootable" in file_output.lower():
                metadata["is_bootable"] = True

            # If xorriso is installed, we can get volume ID
            try:
                xorriso_result = subprocess.run(["xorriso", "-indev", self.filepath, "-pvd_info"], capture_output=True, text=True, timeout=10)
                for line in xorriso_result.stdout.split('\n'):
                    if "Volume Id" in line:
                        metadata["volume_id"] = line.split(':', 1)[1].strip()
            except FileNotFoundError:
                metadata["volume_id"] = "xorriso not installed"

            if "ISO 9660" in file_output:
                metadata["success"] = True

        except Exception as e:
            metadata["error"] = str(e)

        return metadata
