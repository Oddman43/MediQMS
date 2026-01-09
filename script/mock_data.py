import sqlite3
from pathlib import Path
from config import storage_root_path
import os
import shutil
from datetime import datetime, timedelta
from copy import deepcopy
from training_actions import lazy_check
from training_actions import check_overdue
from document_actions import revise_doc


from classes import Document_Header, Document_Version, Training
from config import document_types, template_map
from core_actions import (
    audit_log_docs,
    user_info,
    create_doc,
    create_version,
    update_db,
    get_user_id,
    get_training,
    update_training,
)
from audit_actions import audit_log_training
from document_actions import approve_checks, write_approvals_table, assign_training


def create_new_document(title: str, type: str, user_name: str, db_path: str) -> None:
    if type not in document_types.values():
        raise (ValueError(f"Invalid type, not in valid types: '{type}'"))
    tmp_path: str = template_map.get(type.upper())  # type: ignore
    if not tmp_path:
        raise ValueError(
            f"Configuration Error: No template or mock found for type '{type}'"
        )
    user_id: int
    active_flag: int
    user_id, active_flag, _ = user_info(user_name, db_path)
    if active_flag == 0:
        raise ValueError(f"Owner ID {user_id} does not exist or is inactive")
    with sqlite3.connect(db_path) as db:
        cursor: sqlite3.Cursor = db.cursor()
        cursor.execute("SELECT count(*) FROM documents WHERE title = ?", (title,))
        if cursor.fetchone()[0] > 0:
            raise ValueError(f"Document title already exists: '{title}'")
        cursor.execute("SELECT MAX(doc_id) FROM documents")
        last_doc_id: int | None = cursor.fetchone()[0]
        next_doc_id: int = 1 if last_doc_id is None else last_doc_id + 1
        cursor.execute("SELECT MAX(version_id) FROM versions")
        last_ver_id: int | None = cursor.fetchone()[0]
        next_ver_id: int = 1 if last_ver_id is None else last_ver_id + 1
        cursor.execute(
            "SELECT doc_num FROM documents WHERE type = ? ORDER BY doc_id DESC LIMIT 1",
            (type,),
        )
        result_num: tuple | None = cursor.fetchone()

        if result_num is None:
            next_doc_num: str = f"{type}-001"
        else:
            last_num_str: str = result_num[0]
            parts: list[str] = last_num_str.split("-")
            if len(parts) < 2:
                next_doc_num: str = f"{type}-001"
            else:
                current_seq: int = int(parts[1])
                next_seq: int = current_seq + 1
                next_doc_num: str = f"{type}-{next_seq:03d}"
    copy_path: Path = Path(tmp_path)
    extension_file: str = os.path.splitext(tmp_path)[1]
    destination_folder: Path = Path(storage_root_path) / "01_drafts"
    file_name: str = f"{next_doc_num}_V0.1_DRAFT{extension_file}"
    destination_path_root = destination_folder / file_name
    shutil.copy(copy_path, destination_path_root)
    new_document: Document_Header = Document_Header(
        next_doc_id, next_doc_num, title, user_id, type
    )
    new_version: Document_Version = Document_Version(
        next_ver_id, next_doc_id, "0.1", "DRAFT", str(destination_path_root), None
    )
    create_doc(new_document, db_path)
    create_version(new_version, db_path)
    audit_log_docs(None, new_document, new_document.owner, "CREATE", db_path)
    audit_log_docs(None, new_version, new_document.owner, "CREATE", db_path)


def approve_document(
    user: str,
    doc_num: str,
    db_path: str,
    efective_date: str | None,
    comment: str | None = None,
) -> None:
    parent_doc: Document_Header
    version_old: Document_Version
    user_role: str
    user_id: int
    parent_doc, version_old, user_role, user_id = approve_checks(user, doc_num, db_path)
    version_new = deepcopy(version_old)
    if user_id == parent_doc.owner and version_old.status == "DRAFT":
        version_new.status = "IN_REVIEW"
        action: str = "UPDATE"
    elif user_role == "QM" and version_old.status == "IN_REVIEW":
        version_new.status = "TRAINING"
        action: str = "APPROVE"
        if not efective_date:
            raise ValueError(f"Efective_date field is obligatory: '{efective_date}'")
        version_new.effective_date = efective_date  # type: ignore
        major_version: int = int(version_old.version.split(".")[0])
        new_version_major: int = major_version + 1
        version_new.version = f"{new_version_major}.0"
        version_new.file_path = (
            version_old.file_path.replace("_DRAFT", "_TRAINING")
            .replace(version_old.version, version_new.version)
            .replace("01_drafts", "02_pending_approval")
        )
        if os.path.exists(version_old.file_path):
            shutil.move(version_old.file_path, version_new.file_path)
        else:
            raise FileNotFoundError(
                f"Incorrect path in the databse: '{version_old.file_path}'"
            )
    else:
        raise PermissionError(f"Action not permited for user: '{user}'")
    new_values = audit_log_docs(version_old, version_new, user_id, action, db_path)
    update_db("versions", new_values, version_new, db_path)
    write_approvals_table(user_id, user_role, version_new, "APPROVE", db_path)
    if version_new.status == "TRAINING":
        assign_training(doc_num, efective_date, user_id, db_path)  # type: ignore


def do_training(user: str, doc_num: str, score: int, db_path: str) -> None:
    user_id: int = get_user_id(user, db_path)
    old_training_obj: Training = get_training(user_id, doc_num, db_path)
    new_training_obj: Training = deepcopy(old_training_obj)
    new_training_obj.score = score
    if score > 70:
        new_training_obj.status = "COMPLETED"
        new_training_obj.completion_date = datetime.now() - timedelta(days=2)

    else:
        new_training_obj.status = "FAILED"
    audit_log_training(
        old_training_obj,
        new_training_obj,
        user_id,
        new_training_obj.status,
        db_path,
    )
    update_training(new_training_obj, db_path)


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
