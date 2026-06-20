import subprocess
import os
import shutil

class FilesystemAgent:
    def __init__(self, filepath, extraction_dir):
        self.filepath = filepath
        self.extraction_dir = extraction_dir

    def analyze(self):
        result = {
            "agent": "Filesystem",
            "missing_folders": [],
            "suspicious_files": [],
            "rpm_signature_failure": False,
            "success": False,
            "extracted_images": []
        }

        if not os.path.exists(self.filepath):
            return result

        try:
            # Create extraction dir
            os.makedirs(self.extraction_dir, exist_ok=True)
            
            # Use 7z to list contents
            out = subprocess.run(["7z", "l", self.filepath], capture_output=True, text=True, timeout=15)
            output = out.stdout

            expected_folders = ["EFI", "isolinux", "images", "Packages", "repodata", "LiveOS", "boot"]
            found_folders = []
            
            # Very basic check: just see if folder name appears in the listing
            for f in expected_folders:
                if f in output:
                    found_folders.append(f)
                else:
                    result["missing_folders"].append(f)

            suspicious_exts = [".exe", ".bat", ".ps1"]
            suspicious_keywords = ["autorun.inf", "malware", "payload", "backdoor", "crack", "trojan"]
            
            has_rpms = False
            
            for line in output.split('\n'):
                lower_line = line.lower()
                for ext in suspicious_exts:
                    if ext in lower_line:
                        result["suspicious_files"].append(line.split()[-1])
                for kw in suspicious_keywords:
                    if kw in lower_line:
                        result["suspicious_files"].append(line.split()[-1])
                if ".rpm" in lower_line:
                    has_rpms = True

            # Extract images/pdfs for OCR and RPMs for sig check
            try:
                subprocess.run(["7z", "e", self.filepath, "-o" + self.extraction_dir, "*.png", "*.jpg", "*.jpeg", "*.pdf", "*.rpm", "-r"], capture_output=True, timeout=30)
                
                # Check what was extracted
                for root, dirs, files in os.walk(self.extraction_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        if file.endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                            result["extracted_images"].append(full_path)
                        elif file.endswith('.rpm'):
                            # Check RPM signature
                            rpm_check = subprocess.run(["rpm", "-K", full_path], capture_output=True, text=True, timeout=10)
                            if "NOT OK" in rpm_check.stdout or "NOKEY" in rpm_check.stdout or "failed" in rpm_check.stdout.lower():
                                result["rpm_signature_failure"] = True
            except Exception as e:
                pass

            result["success"] = True

        except Exception as e:
            result["error"] = str(e)

        if not result["success"]:
            result["explanation"] = "Filesystem extraction failed or encountered an error."
        elif result["rpm_signature_failure"]:
            result["explanation"] = "Filesystem check found RPM packages with invalid or failing signatures. This is a strong indicator of tampering."
        elif result["suspicious_files"]:
            result["explanation"] = f"Filesystem check found suspicious files ({', '.join(result['suspicious_files'])})."
        else:
            result["explanation"] = "Filesystem check passed. No suspicious files or invalid RPM signatures detected."

        return result
