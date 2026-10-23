import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from backend.config import SUPPORTED_EXTENSIONS

# These formats contain binary containers, so never fall through to the
# plain-text reader even when an extractor is unavailable.
BINARY_DOCUMENT_EXTENSIONS = frozenset({
    ".pdf", ".docx", ".doc", ".odt", ".rtf",
})


def _log(message: str) -> None:
    """Print without crashing on Windows console encodings (cp1252)."""
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", "backslashreplace").decode("ascii"))


class TextLoader:
    @staticmethod
    def load(file_path: str) -> str:
        path = Path(file_path)
        ext = path.suffix.lower()

        try:
            if ext == ".pdf":
                return TextLoader._load_pdf(path)
            if ext == ".docx":
                return TextLoader._load_docx(path)
            if ext == ".odt":
                return TextLoader._load_odt(path)
            if ext in SUPPORTED_EXTENSIONS and ext not in BINARY_DOCUMENT_EXTENSIONS:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            # .doc and .rtf are indexed for filename/path search. Their
            # content needs a separate converter, so they are metadata-only.
            return ""
        except Exception as e:
            _log(f"Error reading {file_path}: {e}")
            return ""

    @staticmethod
    def _load_pdf(path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError:
            _log("[TextLoader] pypdf is not installed; PDF content is not indexed.")
            return ""

        reader = PdfReader(str(path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return ""

        pages = []
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                _log(f"[TextLoader] Could not extract a PDF page from {path}: {exc}")
                continue
            if text.strip():
                pages.append(text.strip())

        return "\n\n".join(pages)

    @staticmethod
    def _load_docx(path: Path) -> str:
        try:
            from docx import Document
        except ImportError:
            _log("[TextLoader] python-docx is not installed; DOCX content is not indexed.")
            return ""

        document = Document(str(path))
        parts = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    parts.append(" | ".join(cells))

        return "\n".join(parts)

    @staticmethod
    def _load_odt(path: Path) -> str:
        with zipfile.ZipFile(path) as archive:
            content = archive.read("content.xml")

        root = ET.fromstring(content)
        parts = [text.strip() for text in root.itertext() if text.strip()]
        return "\n".join(parts)
