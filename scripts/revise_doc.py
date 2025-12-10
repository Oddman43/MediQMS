import sqlite3
import json
import hashlib
import os
import shutil
from datetime import datetime
from doc_class import Document_Version


def revise_doc(user: str, doc_num: str, db_path: str) -> None:
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(
            "SELECT doc_id, owner_id FROM documents WHERE doc_num = ?", (doc_num,)
        )
        doc_info: tuple | None = cur.fetchone()
        if not doc_info:
            raise ValueError(f"Document does not exist: '{doc_num}'")
        doc_id: int
        owner_id: int
        doc_id, owner_id = doc_info
        cur.execute(
            "SELECT file_path, version FROM versions WHERE doc = ? AND status = 'RELEASED' ORDER BY version_id DESC LIMIT 1",
            (doc_id,),
        )
        version_info: tuple | None = cur.fetchone()
        if not version_info:
            raise ValueError(f"No RELEASED version of document: '{doc_num}'")
        file_path: str
        version: str
        file_path, version = version_info
        cur.execute("SELECT MAX(version_id) FROM versions")
        max_version_id: int = cur.fetchone()[0]
        cur.execute(
            "SELECT user_id FROM users WHERE user_name = ? AND active_flag = 1", (user,)
        )
        user_info: tuple = cur.fetchone()
        if not user_info:
            raise ValueError(f"User does not exist or is inactive: '{user}'")
        user_id: int = user_info[0]
        cur.execute(
            "SELECT r.role_name FROM roles r JOIN users_roles ur ON r.role_id = ur.role WHERE ur.user = ?",
            (user_id,),
        )
        user_roles: list = [i[0] for i in cur.fetchall()]
        cur.execute(
            "SELECT version_id FROM versions WHERE doc = ? AND status IN ('DRAFT', 'IN_REVIEW')",
            (doc_id,),
        )
        if cur.fetchone():
            raise ValueError(
                f"Draft or In review already in process for document: '{doc_num}'"
            )
    if not (user_id == owner_id or "Quality Manager" in user_roles):
        raise PermissionError(f"User not allwed to revise document: '{doc_num}'")
    v_major: int = int(version.split(".")[0])
    v_minor: int = int(version.split(".")[1]) + 1
    new_version: str = f"{v_major}.{v_minor}"

    tmp_path: str = file_path.replace(version, new_version).replace(
        "03_released", "01_drafts"
    )

    root, ext = os.path.splitext(tmp_path)
    new_file_path: str = f"{root}_DRAFT{ext}"

    new_id: int = max_version_id + 1

    shutil.copy(file_path, new_file_path)
    revised_doc: Document_Version = Document_Version(
        new_id, doc_id, new_version, "DRAFT", new_file_path, None
    )
    old_val_str: str = ""
    new_val: dict = {
        "doc_id": doc_id,
        "version": new_version,
        "status": "DRAFT",
        "file_path": new_file_path,
        "derived_from": version,
    }
    new_val_str: str = json.dumps(new_val)
    action: str = "REVISE"
    table_affected: str = "versions"
    audit_ts: str = datetime.now().isoformat()
    raw_str_hash: str = (
        f"{table_affected}{new_id}{user_id}{action}{old_val_str}{new_val_str}{audit_ts}"
    )
    row_hash: str = hashlib.sha256(raw_str_hash.encode("utf-8")).hexdigest()
    query_audit_log: str = """
    INSERT INTO audit_log (table_affected, record_id, user, action, old_val, new_val, timestamp, hash)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    with sqlite3.connect(db_path) as db:
        try:
            cur: sqlite3.Cursor = db.cursor()
            cur.execute(
                "INSERT INTO versions (version_id, doc, version, status, file_path, effective_date) VALUES (?, ?, ?, ?, ?, ?)",
                revised_doc.to_db_tuple(),
            )
            cur.execute(
                query_audit_log,
                (
                    table_affected,
                    new_id,
                    user_id,
                    action,
                    None,
                    new_val_str,
                    audit_ts,
                    row_hash,
                ),
            )
            db.commit()
        except sqlite3.Error as e:
            db.rollback()
            raise e
