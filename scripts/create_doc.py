import sqlite3
from pathlib import Path
from config import storage_root_path
import os
import shutil

from doc_class import Document_Header, Document_Version
from config import document_types, template_map
from core_fn import audit_log_docs, user_info


def create_new_document(
    title: str, type: str, user_name: str, db_path: str
) -> tuple[Document_Header, Document_Version]:
    if type not in document_types.values():
        raise (ValueError(f"Invalid type, not in valid types: '{type}'"))
    tmp_path: str = template_map.get(type.upper())  # type: ignore
    if not tmp_path:
        raise ValueError(
            f"Configuration Error: No template or mock found for type '{type}'"
        )
    user_id: int
    active_flag: int
    user_roles: list[str]
    user_id, active_flag, user_roles = user_info(user_name, db_path)
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
    return (new_document, new_version)


def write_new_doc(
    header: Document_Header,
    version: Document_Version,
    db_path: str,
) -> None:
    with sqlite3.connect(db_path) as db:
        try:
            db.execute(
                "INSERT INTO documents (doc_id, doc_num, title, owner_id, type) VALUES (?, ?, ?, ?, ?)",
                header.to_db_tuple(),
            )
            db.execute(
                "INSERT INTO versions (version_id, doc, version, status, file_path, effective_date) VALUES (?, ?, ?, ?, ?, ?)",
                version.to_db_tuple(),
            )
            db.commit()

        except sqlite3.Error as e:
            db.rollback()
            raise e
    audit_log_docs(None, header, header.owner, "CREATE", db_path)
    audit_log_docs(None, version, header.owner, "CREATE", db_path)
