from fastapi import FastAPI
from backend.api import search, index, ask
from backend.config import DATA_DIR
from backend.db.database import Base, engine
from backend.db import models  # Explicit import to register models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LocalMind API", version="0.1.0")

# Enable CORS for frontend
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Wildcard for debugging
    allow_credentials=False, # Must be False if origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request, call_next):
    print(f"DEBUG: Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response

# Include routers
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(index.router, prefix="/api", tags=["index"])
app.include_router(ask.router, prefix="/api", tags=["ask"])

@app.get("/")
async def root():
    return {"message": "LocalMind Backend is running", "data_dir": str(DATA_DIR)}

if __name__ == "__main__":
    import uvicorn
    # Important: point to the new filename
    uvicorn.run("backend.server:app", host="127.0.0.1", port=8001, reload=True)
