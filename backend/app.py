from fastapi import FastAPI
from backend.api import search, index, ask
from backend.config import DATA_DIR
from backend.db.database import Base, engine
from backend.db import models  # Explicit import to register models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LocalMind API", version="0.1.0")

# Include routers
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(index.router, prefix="/api", tags=["index"])
app.include_router(ask.router, prefix="/api", tags=["ask"])

@app.get("/")
async def root():
    return {"message": "LocalMind Backend is running", "data_dir": str(DATA_DIR)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
