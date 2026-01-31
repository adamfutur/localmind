from fastapi import APIRouter, BackgroundTasks
from backend.core.file_scanner import FileScanner
from backend.core.text_loader import TextLoader
from backend.core.chunker import Chunker
from backend.core.embeddings import EmbeddingModel
from backend.core.vector_store import VectorStore
from backend.db.database import SessionLocal
from backend.db.models import FileMetadata
from sqlalchemy.orm import Session
from datetime import datetime

router = APIRouter()

def process_indexing():
    scanner = FileScanner()
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
async def trigger_indexing(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_indexing)
    return {"status": "Indexing started in background"}
