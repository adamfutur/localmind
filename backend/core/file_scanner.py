import os
from pathlib import Path
from typing import List, Generator
from datetime import datetime

from backend.config import MAX_FILE_SIZE_BYTES, SUPPORTED_EXTENSIONS

class FileScanner:
    def __init__(self, root_dirs: List[str] = None, ignore_patterns: List[str] = None):
        # Scan both Documents and Desktop by default so /api/index (no params) is useful
        self.root_dirs = root_dirs or [str(Path.home() / "Documents"), str(Path.home() / "Desktop")]
        self.ignore_patterns = ignore_patterns or [
            ".git", "node_modules", "__pycache__", ".venv", "venv",
            ".ds_store", "dist", "build", "target", ".next", "coverage",
        ]

    def scan(self) -> Generator[dict, None, None]:
        for root_dir in self.root_dirs:
            if not os.path.exists(root_dir):
                continue
                
            for root, dirs, files in os.walk(root_dir):
                # Filter directories
                dirs[:] = [d for d in dirs if d not in self.ignore_patterns]
                
                for file in files:
                    # Basic extension filter for now
                    if file.startswith(".") or any(p in file for p in self.ignore_patterns):
                        continue

                    # Skip files we cannot extract text from before doing any I/O.
                    if Path(file).suffix.lower() not in SUPPORTED_EXTENSIONS:
                        continue
                        
                    file_path = os.path.join(root, file)
                    try:
                        stats = os.stat(file_path)
                        if stats.st_size > MAX_FILE_SIZE_BYTES:
                            continue
                        yield {
                            "path": file_path,
                            "filename": file,
                            "extension": Path(file).suffix.lower(),
                            "size": stats.st_size,
                            "created_at": datetime.fromtimestamp(stats.st_ctime),
                            "modified_at": datetime.fromtimestamp(stats.st_mtime)
                        }
                    except OSError:
                        pass # Skip files we can't read
