# LocalMind

Local-first AI system for your file system.

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. Install Node dependencies:
   ```bash
   cd desktop
   npm install
   ```

3. Run the application:
   ```bash
   scripts\start_localmind.bat
   ```

## Architecture
- **Backend**: FastAPI
- **Frontend**: Tauri + React
- **Vector Store**: FAISS
