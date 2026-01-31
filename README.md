# LocalMind

LocalMind is a **local-first AI system** that runs entirely on your machine. It indexes your documents and code, allowing you to search and interact with your files using semantic understanding without any data leaving your device.

## ✨ Features

- **100% Offline**: No specialized cloud infrastructure required. Your data stays with you.
- **Semantic Search**: Find files based on meaning, not just exact keywords.
- **File System Integration**: Designed to work intimately with your local files.
- **Cross-Platform**: Built for Windows, macOS, and Linux.

## 🏗️ Architecture

LocalMind is built with a modern, performant stack:

- **Frontend / Desktop App**: [Tauri](https://tauri.app/) (Rust) + [React](https://react.dev/) (TypeScript/Vite). This provides a lightweight, native-feeling desktop application.
- **Backend API**: [FastAPI](https://fastapi.tiangolo.com/) (Python). Handles the business logic and AI processing.
- **Database**:
  - **Metadata**: SQLite (via SQLAlchemy).
  - **Vector Store**: FAISS (via LangChain/Sentence Transformers) for fast semantic retrieval.
- **AI Engine**: Uses local embeddings (Sentence Transformers) and LLMs (via LangChain).

## 🚀 Getting Started

### Prerequisites

Ensure you have the following installed:
- [Python 3.8+](https://www.python.org/)
- [Node.js & npm](https://nodejs.org/)
- [Rust](https://www.rust-lang.org/tools/install) (Required for building the Tauri desktop app)
- [Microsoft Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) (For Windows users, needed for Rust)

### 1. Backend Setup

Initialize the Python environment and dependencies.

```bash
# Create a virtual environment (optional but recommended)
python -m venv venv
# Windows
.\venv\Scripts\activate
# Unix
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Frontend Setup

Install the desktop application dependencies.

```bash
cd desktop
npm install
```

### 3. Running the Application

You can run the full application using the provided script (Windows):

```bash
scripts\start_localmind.bat
```

Or run the components individually for development:

**Backend:**
```bash
# From the project root
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend:**
```bash
cd desktop
npm run tauri dev
```

## 🛠️ Development

- **Backend Code**: located in `backend/`
- **Desktop UI**: located in `desktop/src` and `desktop/src-tauri`

## 📄 License

MIT
