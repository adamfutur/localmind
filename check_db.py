from backend.db.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Tables: {tables}")

if "files" in tables:
    columns = [c["name"] for c in inspector.get_columns("files")]
    print(f"Columns in 'files': {columns}")
    if "path" in columns:
        print("VERIFICATION SUCCESS: 'path' column exists.")
    else:
        print("VERIFICATION FAILURE: 'path' column MISSING.")
else:
    print("VERIFICATION FAILURE: 'files' table MISSING.")
