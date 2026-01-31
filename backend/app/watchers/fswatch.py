import time
import os
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from backend.app.indexing.scanner import index_single_file

class LocalMindEventHandler(FileSystemEventHandler):
    """
    Custom event handler for filesystem events.
    Triggers indexing for newly created or modified files.
    """
    def __init__(self, watch_path):
        super().__init__()
        self.watch_path = os.path.abspath(watch_path)
        print(f"[Watcher] Initialized event handler for: {self.watch_path}")

    def on_created(self, event):
        if not event.is_directory:
            print(f"[Watcher] Detected new file: {event.src_path}")
            # Use a background task for indexing to not block the watcher thread
            threading.Thread(target=index_single_file, args=(event.src_path,), daemon=True).start()

    def on_modified(self, event):
        if not event.is_directory:
            print(f"[Watcher] Detected modified file: {event.src_path}")
            threading.Thread(target=index_single_file, args=(event.src_path,), daemon=True).start()

    def on_deleted(self, event):
        if not event.is_directory:
            print(f"[Watcher] Detected deleted file: {event.src_path}")
            # The index_single_file function now also handles deletes (by checking os.path.exists)
            # or you can have a dedicated delete function
            from backend.app.search.engine import remove_document_from_index_by_file_path
            from backend.app.storage.metadata import delete_file_metadata
            threading.Thread(target=remove_document_from_index_by_file_path, args=(event.src_path,), daemon=True).start()
            threading.Thread(target=delete_file_metadata, args=(event.src_path,), daemon=True).start()


def start_watcher_daemon(path_to_watch: str):
    """
    Starts the filesystem watcher in a daemon thread.
    The watcher will monitor 'path_to_watch' for changes.
    """
    if not os.path.exists(path_to_watch):
        print(f"[Watcher] Warning: Path to watch '{path_to_watch}' does not exist. Creating it.")
        os.makedirs(path_to_watch, exist_ok=True)
        
    event_handler = LocalMindEventHandler(path_to_watch)
    observer = Observer()
    observer.schedule(event_handler, path_to_watch, recursive=True)
    
    # Start the observer in a daemon thread so it doesn't prevent app shutdown
    watcher_thread = threading.Thread(target=observer.start, daemon=True)
    watcher_thread.start()
    
    print(f"[Watcher] Filesystem observer started for '{path_to_watch}' in a daemon thread.")
    # The observer.join() would block the main thread, so we don't call it here.
    # The daemon thread will exit when the main program exits.