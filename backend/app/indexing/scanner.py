import os
from datetime import datetime
from backend.app.search.engine import add_document_to_index, remove_document_from_index_by_file_path
from backend.app.storage.metadata import save_file_metadata, get_file_metadata, update_file_metadata, delete_file_metadata
from backend.app.search.engine import remove_document_from_index_by_file_path

TEXT_FILE_EXTENSIONS = (".txt", ".md", ".py", ".json", ".csv", ".xml", ".html", ".css", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".toml", ".yaml", ".yml")
MIN_TEXT_LENGTH_FOR_INDEXING = 50
CHUNK_SIZE = 500  # characters per chunk
CHUNK_OVERLAP = 50 # overlap for context between chunks

def get_file_content(file_path):
    """Attempts to read file content, handling common encodings."""
    try:
        # Try UTF-8 first, then fall back to latin-1
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            print(f"[Scanner] Warning: Could not read {file_path} with utf-8 or latin-1: {e}")
            return None
    except Exception as e:
        print(f"[Scanner] Error reading file {file_path}: {e}")
        return None

def chunk_text(text, file_path):
    """Splits text into chunks with overlap for better context, yielding (chunk_content, unique_chunk_id)."""
    if len(text) <= CHUNK_SIZE:
        unique_chunk_id = f"{file_path}::chunk::0"
        yield text, unique_chunk_id
        return

    start = 0
    chunk_idx = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end]
        unique_chunk_id = f"{file_path}::chunk::{chunk_idx}"
        yield chunk, unique_chunk_id

        if end == len(text): # Reached end of text
            break
            
        start += (CHUNK_SIZE - CHUNK_OVERLAP)
        if start >= len(text): # Ensure not to overshoot
            start = len(text) - CHUNK_SIZE # Adjust last chunk start to ensure full chunk size if possible at end
            if start < 0: start = 0 # Avoid negative start for very short texts

        chunk_idx += 1


def index_single_file(file_path):
    """
    Indexes a single file: reads content, chunks it, adds to vector store, and updates metadata.
    Handles re-indexing if file is modified.
    Returns True if file was indexed/re-indexed, False otherwise.
    """
    if not os.path.exists(file_path):
        print(f"[Scanner] File deleted: {file_path}. Removing from index.")
        remove_document_from_index_by_file_path(file_path)
        delete_file_metadata(file_path)
        return False
        
    if os.path.isdir(file_path):
        # print(f"[Scanner] Skipping directory: {file_path}")
        return False

    if not file_path.lower().endswith(TEXT_FILE_EXTENSIONS):
        # print(f"[Scanner] Skipping non-text file type: {file_path}")
        return False

    try:
        current_last_modified_os = datetime.fromtimestamp(os.path.getmtime(file_path))
        file_metadata = get_file_metadata(file_path)

        if file_metadata and file_metadata['last_modified_timestamp'] >= current_last_modified_os:
            # print(f"[Scanner] File {file_path} is already indexed and up-to-date.")
            return False
            
        # If file exists in metadata but is outdated, or if it's new
        # For re-indexing, first remove old chunks if any
        if file_metadata:
            print(f"[Scanner] Re-indexing modified file: {file_path}")
            remove_document_from_index_by_file_path(file_path) # Remove old chunks from FAISS
        else:
            print(f"[Scanner] Indexing new file: {file_path}")

        content = get_file_content(file_path)
        if not content or len(content.strip()) < MIN_TEXT_LENGTH_FOR_INDEXING:
            print(f"[Scanner] Skipping file {file_path} due to insufficient content (length: {len(content.strip()) if content else 0}).")
            # If it had metadata, delete it because it's no longer considered indexable
            if file_metadata:
                remove_document_from_index_by_file_path(file_path)
                delete_file_metadata(file_path)
            return False

        indexed_chunks = 0
        current_indexed_at = datetime.now()

        for chunk_content, unique_chunk_id in chunk_text(content, file_path):
            add_document_to_index(chunk_content, unique_chunk_id)
            indexed_chunks += 1
        
        # Save/update metadata for the file after processing all chunks
        save_file_metadata(file_path, current_last_modified_os, current_indexed_at, indexed_chunks)
        
        print(f"[Scanner] Successfully indexed {indexed_chunks} chunks for: {file_path}")
        return True

    except Exception as e:
        print(f"[Scanner] Error indexing {file_path}: {e}")
        return False


def scan_folder(root_path):
    """
    Scans a folder recursively and indexes relevant text files.
    This function is designed to be run in a background task.
    """
    print(f"[Scanner] Starting scan of folder: {root_path}")
    indexed_files_count = 0
    
    # Track files found during this scan
    files_found_in_scan = set()

    for dirpath, _, filenames in os.walk(root_path):
        for name in filenames:
            file_path = os.path.join(dirpath, name)
            files_found_in_scan.add(file_path)
            if index_single_file(file_path):
                indexed_files_count += 1
    
    # Optional: Clean up metadata/index for files that are no longer in the scanned directory
    # This part can be resource-intensive for large indexes and might be better as a separate, less frequent cleanup task.
    # For now, we'll keep it simple and only index what's found or modified.

    print(f"[Scanner] Finished scanning '{root_path}'. Total new/updated files indexed: {indexed_files_count}")
    return {"scanned_path": root_path, "new_or_updated_files_indexed": indexed_files_count}