from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from backend.core.file_scanner import FileScanner
from backend.core.text_loader import TextLoader
from backend.core.chunker import Chunker
from backend.core.embeddings import EmbeddingModel
from backend.core.vector_store import VectorStore
from backend.db.database import SessionLocal
from backend.db.models import FileMetadata
from sqlalchemy.orm import Session
from datetime import datetime
import os
from typing import List, Optional

router = APIRouter()


def process_indexing(root_dirs: Optional[List[str]] = None):
    """
    Perform indexing over the provided root directories. If none provided,
    FileScanner will use its default roots.
    """
    scanner = FileScanner(root_dirs=root_dirs)
    loader = TextLoader()
    chunker = Chunker()
    embedder = EmbeddingModel()
    vector_store = VectorStore()

    db: Session = SessionLocal()

    for file_info in scanner.scan():
        # Check if already indexed or modified
        existing = db.query(FileMetadata).filter(FileMetadata.path == file_info['path']).first()
        if existing and existing.modified_at == file_info['modified_at']:
            continue

        print(f"Indexing: {file_info['path']}")

        # Load Content
        text = loader.load(file_info['path'])

        # Update DB
        if not existing:
            meta = FileMetadata(**file_info)
            db.add(meta)
        else:
            for k, v in file_info.items():
                setattr(existing, k, v)

        db.commit()

        # Vectorize
        if text:
            chunks = chunker.chunk(text)
            embeddings = embedder.embed(chunks)

            # Store metadata for each chunk
            metas = []
            for chunk in chunks:
                metas.append({
                    "path": file_info['path'],
                    "text": chunk
                })

            vector_store.add(embeddings, metas)

    db.close()
    print("Indexing Complete")


@router.post("/index")
async def trigger_indexing(background_tasks: BackgroundTasks, path: Optional[str] = None):
    """
    Trigger background indexing.
    If 'path' is provided, it must be an existing directory. You can pass multiple paths
    separated by ';' or ','. Example:
      /api/index?path=C:\\Users\\me\\Desktop;D:\\Docs
    If not provided, defaults from FileScanner are used (e.g., Documents).
    """
    root_dirs: Optional[List[str]] = None
    if path:
        # Split by ';' or ',' and normalize/validate
        raw_parts = [p.strip() for p in path.replace(',', ';').split(';') if p.strip()]
        if not raw_parts:
            raise HTTPException(status_code=400, detail="Provided 'path' is empty after parsing.")
        invalid = [p for p in raw_parts if not os.path.isdir(p)]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid directory path(s): {invalid}")
        root_dirs = raw_parts

    background_tasks.add_task(process_indexing, root_dirs)
    msg = (
        f"Indexing started in background for: {root_dirs}" if root_dirs else
        "Indexing started in background using default roots"
    )
    return {"status": msg}


@router.get("/indexed-files")
async def indexed_files(limit: int = Query(50, ge=1, le=1000)):
    """
    List the first N indexed files (filename + path) for diagnostics.
    """
    s = SessionLocal()
    try:
        rows = s.query(FileMetadata).limit(limit).all()
        return [{"filename": r.filename, "path": r.path} for r in rows]
    finally:
        s.close()


@router.post("/index-path")
async def index_path(path: str = Query(..., min_length=1)):
    """
    Index a specific directory or a single file synchronously for immediate feedback.
    Useful to ensure a target path is indexed without changing /api/index.
    """
    # Validate path
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")

    # Prepare components
    loader = TextLoader()
    chunker = Chunker()
    embedder = EmbeddingModel()
    vector_store = VectorStore()
    db: Session = SessionLocal()

    def upsert_file(file_path: str):
        try:
            stats = os.stat(file_path)
            info = {
                "path": file_path,
                "filename": os.path.basename(file_path),
                "extension": os.path.splitext(file_path)[1].lower(),
                "size": stats.st_size,
                "created_at": datetime.fromtimestamp(stats.st_ctime),
                "modified_at": datetime.fromtimestamp(stats.st_mtime),
            }
            # Upsert metadata
            existing = db.query(FileMetadata).filter(FileMetadata.path == info['path']).first()
            if not existing:
                db.add(FileMetadata(**info))
            else:
                for k, v in info.items():
                    setattr(existing, k, v)
            db.commit()

            # Load and embed
            text = loader.load(file_path)
            if text:
                chunks = chunker.chunk(text)
                embeddings = embedder.embed(chunks)
                metas = [{"path": file_path, "text": c} for c in chunks]
                vector_store.add(embeddings, metas)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Indexing failed for {file_path}: {e}")

    try:
        if os.path.isdir(path):
            # Walk directory
            for root, _, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    # basic skip hidden
                    if os.path.basename(fp).startswith('.'):
                        continue
                    upsert_file(fp)
        else:
            upsert_file(path)
        return {"status": f"Indexed: {path}"}
    finally:
        db.close()
