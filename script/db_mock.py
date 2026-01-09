import sqlite3
from pathlib import Path
import os
from datetime import datetime, timedelta
from mock_scripts import create_new_document, approve_document, do_training
from core_fn import lazy_check
from training_actions import check_overdue
from revise_doc import revise_doc

base_dir: Path = Path(__file__).resolve().parent.parent
db_path: str = str(base_dir / "data" / "database" / "mediqms.db")
schema_path: str = str(base_dir / "data" / "database" / "schema.sql")
mock_path: str = str(base_dir / "data" / "database" / "mock_data.sql")

os.remove(db_path)

with sqlite3.connect(db_path) as db:
    with open(schema_path, encoding="utf-8") as f:
        schema = f.read()
    db.executescript(schema)
    with open(mock_path) as md:
        mock_data = md.read()
    db.executescript(mock_data)

folders_to_clean = [
    "storage/01_drafts",
    "storage/02_pending_approval",
    "storage/03_released",
    "storage/04_archive",
]

for relative_path in folders_to_clean:
    folder_path = base_dir / relative_path
    if not folder_path.exists():
        continue
    count = 0
    for item in folder_path.iterdir():
        if item.is_file() and not item.name.startswith("."):
            item.unlink()
            count += 1


create_new_document("test1", "SOP", "albert.sevilleja", db_path)
approve_document("albert.sevilleja", "SOP-001", db_path, None)
approve_document(
    "gus.fring", "SOP-001", db_path, (datetime.now() - timedelta(days=1)).isoformat()
)
training_users: list = [
    "walter.white",
    "jesse.pinkman",
    "hank.schrader",
    "mike.ehrmantraut",
]
for user in training_users:
    do_training(user, "SOP-001", 100, db_path)
lazy_check(db_path)

create_new_document("test2", "WI", "albert.sevilleja", db_path)
approve_document("albert.sevilleja", "WI-001", db_path, None)
approve_document(
    "gus.fring", "WI-001", db_path, (datetime.now() - timedelta(days=4)).isoformat()
)

for user in training_users:
    score: int = 90
    if user == "mike.ehrmantraut":
        continue
    if user == "jesse.pinkman":
        score = 60
    do_training(user, "WI-001", score, db_path)

check_overdue(db_path)
lazy_check(db_path)

revise_doc("albert.sevilleja", "SOP-001", db_path)
approve_document("albert.sevilleja", "SOP-001", db_path, None)
approve_document(
    "gus.fring", "SOP-001", db_path, (datetime.now() - timedelta(days=1)).isoformat()
)
for user in training_users:
    do_training(user, "SOP-001", 100, db_path)
lazy_check(db_path)

create_new_document("test3", "SOP", "albert.sevilleja", db_path)
approve_document("albert.sevilleja", "SOP-002", db_path, None)
approve_document(
    "gus.fring", "SOP-002", db_path, (datetime.now() - timedelta(days=4)).isoformat()
)
for user in training_users:
    do_training(user, "SOP-002", 100, db_path)
lazy_check(db_path)
