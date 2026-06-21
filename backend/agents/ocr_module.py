import os
from PIL import Image
import pytesseract
import subprocess

class OCRAgent:
    def __init__(self, image_paths):
        self.image_paths = image_paths

    def analyze(self):
        result = {
            "agent": "OCR",
            "ocr_scanned": False,
            "suspicious_text_found": False,
            "found_words": []
        }

        if not self.image_paths:
            return result
        
        result["ocr_scanned"] = True
        suspicious_words = ["hacked", "malware", "trojan", "payload", "backdoor", "crack", "unofficial", "modified", "infected"]

        for img_path in self.image_paths:
            ext = os.path.splitext(img_path)[1].lower()
            text = ""
            try:
                if ext in ['.png', '.jpg', '.jpeg']:
                    img = Image.open(img_path)
                    text = pytesseract.image_to_string(img).lower()
                elif ext == '.pdf':
                    # Extract text from pdf using pdftotext (poppler-utils)
                    out = subprocess.run(["pdftotext", img_path, "-"], capture_output=True, text=True, timeout=10)
                    text = out.stdout.lower()
                
                for word in suspicious_words:
                    if word in text and word not in result["found_words"]:
                        result["found_words"].append(word)
                        result["suspicious_text_found"] = True

            except Exception as e:
                # ignore OCR errors on specific files
                pass

        if not result["ocr_scanned"]:
            result["explanation"] = "No images or PDFs were extracted for OCR scanning."
        elif result["suspicious_text_found"]:
            result["explanation"] = f"Images or PDFs contain suspicious words or messages: {', '.join(result['found_words'])}."
        else:
            result["explanation"] = "No suspicious text was found in any extracted images or PDFs."

        return result
