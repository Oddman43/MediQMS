import sqlite3
import os
from pathlib import Path

db_path: str = "mediqms.db"
db_schema: str = "schema.sql"
mock_data_path: str = "mock_data.sql"

os.remove(db_path)

with sqlite3.connect(db_path) as db:
    with open(db_schema, encoding="utf-8") as f:
        schema = f.read()
    db.executescript(schema)
    with open(mock_data_path) as md:
        mock_data = md.read()
    db.executescript(mock_data)

script_location = Path(__file__).resolve()
project_root = script_location.parents[2]
folders_to_clean = ["storage/01_drafts", "storage/03_released", "storage/04_archive"]

for relative_path in folders_to_clean:
    folder_path = project_root / relative_path
    if not folder_path.exists():
        continue
    count = 0
    for item in folder_path.iterdir():
        if item.is_file() and not item.name.startswith("."):
            item.unlink()
            count += 1
