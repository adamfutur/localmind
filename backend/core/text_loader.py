from pathlib import Path

from backend.config import SUPPORTED_EXTENSIONS


class TextLoader:
    @staticmethod
    def load(file_path: str) -> str:
        path = Path(file_path)
        ext = path.suffix.lower()
        
        try:
            if ext in SUPPORTED_EXTENSIONS:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            # Add support for PDF, DOCX here later using pypdf or similar
            else:
                return ""
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""
