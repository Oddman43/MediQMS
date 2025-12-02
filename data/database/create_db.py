import sqlite3
import os

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
