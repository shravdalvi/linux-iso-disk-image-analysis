import subprocess
import os

class FilesystemAgent:
    def __init__(self, filepath):
        self.filepath = filepath

    def analyze(self):
        result = {
            "agent": "Filesystem",
            "has_efi": False,
            "has_isolinux": False,
            "has_packages": False,
            "has_liveos": False,
            "suspicious_files": [],
            "success": False
        }

        if not os.path.exists(self.filepath):
            return result

        try:
            # Using 7z to list contents
            # Assuming 7z is installed
            out = subprocess.run(["7z", "l", self.filepath], capture_output=True, text=True, timeout=15)
            output = out.stdout

            if "EFI" in output or "efi" in output:
                result["has_efi"] = True
            if "isolinux" in output.lower():
                result["has_isolinux"] = True
            if "Packages" in output or "repodata" in output:
                result["has_packages"] = True
            if "LiveOS" in output or "images" in output:
                result["has_liveos"] = True

            # Basic heuristic for suspicious files
            suspicious_keywords = ["ransom", "hack", "miner", "backdoor", "trojan"]
            for line in output.split('\n'):
                for keyword in suspicious_keywords:
                    if keyword in line.lower():
                        result["suspicious_files"].append(line.strip())

            result["success"] = True
            
            # If 7z fails or isn't installed
            if out.returncode != 0:
                result["error"] = "7z command failed. Make sure p7zip-full is installed."
                result["success"] = False

        except FileNotFoundError:
            result["error"] = "7z command not found"
        except Exception as e:
            result["error"] = str(e)

        return result
