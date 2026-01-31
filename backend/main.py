import uvicorn
import os
from fastapi import FastAPI, BackgroundTasks
from backend.app.api.routes import router
from backend.app.storage.metadata import init_db
from backend.app.watchers.fswatch import start_watcher_daemon
from backend.app.search.engine import load_index_and_documents

app = FastAPI(title="LocalMind Backend")

# @app.on_event("startup") will run once when the application starts
@app.on_event("startup")
async def startup_event():
    print("Application startup event triggered.")
    
    # Initialize SQLite database for metadata
    init_db()
    print("Metadata database initialized.")
    
    # Load FAISS index and document map from disk
    load_index_and_documents()
    print("FAISS index and document map loaded (if available).")

    # Start the filesystem watcher in a daemon thread.
    # Specify the directory to watch. For demonstration, we'll watch a 'test_data' folder
    # or you might want to configure this via environment variables or user input.
    # Make sure this folder exists for the watcher to work.
    
    # Example: watch a 'data/watched_folder' relative to project root
    # watched_dir = os.path.join(os.getcwd(), "data", "watched_folder")
    # os.makedirs(watched_dir, exist_ok=True) # Ensure the directory exists
    # print(f"Starting filesystem watcher for: {watched_dir}")
    # start_watcher_daemon(watched_dir)
    # print("Filesystem watcher started.")
    
    print("Startup complete.")

# @app.on_event("shutdown") will run once when the application is shutting down
@app.on_event("shutdown")
async def shutdown_event():
    # Placeholder for any cleanup needed before shutdown
    print("Application shutdown event triggered.")
    # The FAISS index is saved periodically or on explicit trigger
    # In a real app, you might want to explicitly save here too if not saved recently.
    # from backend.app.search.engine import save_index_and_documents
    # save_index_and_documents()
    print("Shutdown complete.")


app.include_router(router)

@app.get("/", summary="Health Check")
def health():
    """
    Returns a simple status to indicate the API is running.
    """
    return {"status": "running", "message": "LocalMind Backend is operational."}

if __name__ == "__main__":
    # Ensure data directory for metadata.db and FAISS index exists
    os.makedirs("data", exist_ok=True)
    
    # Ensure a directory for watcher (if enabled) exists
    # os.makedirs(os.path.join(os.getcwd(), "data", "watched_folder"), exist_ok=True)

    print("Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)