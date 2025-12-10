import sqlite3
from datetime import datetime
import json
import hashlib
import os
import shutil


def approve_document(
    user: str, version_id: int, db_path: str, date: str | None = None
) -> None:
    table_affected: str = "versions"
    timestamp: str = datetime.now().isoformat()
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        query_doc = """
            SELECT 
                v.doc, 
                v.status, 
                v.file_path, 
                v.version,
                v.effective_date,
                d.owner_id
            FROM versions v
            JOIN documents d ON v.doc = d.doc_id
            WHERE v.version_id = ?
        """
        cur.execute(query_doc, (version_id,))
        doc_id: int
        status: str
        file_path: str
        version: str
        effective_date: str
        owner_id: int
        doc_id, status, file_path, version, effective_date, owner_id = cur.fetchone()
        cur.execute("SELECT user_id FROM users WHERE user_name = ?", (user,))
        user_id: int = cur.fetchone()[0]
        cur.execute(
            """
            SELECT r.role_name 
            FROM roles r 
            JOIN users_roles ur ON r.role_id = ur.role 
            WHERE ur.user = ?
        """,
            (user_id,),
        )
        user_roles: list[str] = [i[0] for i in cur.fetchall()]
    if user_id == owner_id and status == "DRAFT":
        new_status: str = "IN_REVIEW"
        action: str = "UPDATE"
        old_values: dict = {"status": status}
        new_values: dict = {"status": new_status}
    elif "Quality Manager" in user_roles and status == "IN_REVIEW":
        new_status: str = "RELEASED"
        action: str = "RELEASE"
        if not date:
            raise ValueError(f"Date field is obligatory: '{date}'")
        new_effective_date: str = date  # type: ignore
        new_version_major: int = int(version.split(".")[0]) + 1
        new_version: str = f"{new_version_major}.0"
        new_file_path: str = (
            file_path.replace("_DRAFT", "")
            .replace(version, new_version)
            .replace("01_drafts", "03_released")
        )
        old_values: dict = {
            "status": status,
            "version": version,
            "file_path": file_path,
            "effective_date": effective_date,
        }
        new_values: dict = {
            "status": new_status,
            "version": new_version,
            "file_path": new_file_path,
            "effective_date": new_effective_date,
        }
        if os.path.exists(file_path):
            shutil.move(file_path, new_file_path)

        else:
            raise FileNotFoundError(f"Incorrect path in the databse: '{file_path}'")
    else:
        raise PermissionError(f"Action not permited for user: '{user}'")
    update_fields: str = ", ".join([f"{key} = ?" for key in new_values.keys()])
    values: list = list(new_values.values())
    values.append(version_id)
    query_update: str = f"UPDATE versions SET {update_fields} WHERE version_id = ?"
    old_values_str: str = json.dumps(old_values)
    new_values_str: str = json.dumps(new_values)
    raw_str_hash: str = f"{table_affected}{version_id}{user_id}{action}{old_values_str}{new_values_str}{timestamp}"
    row_hash: str = hashlib.sha256(raw_str_hash.encode("utf-8")).hexdigest()
    query_audit_log: str = """
    INSERT INTO audit_log (table_affected, record_id, user, action, old_val, new_val, timestamp, hash)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    with sqlite3.connect(db_path) as db:
        try:
            cur: sqlite3.Cursor = db.cursor()
            cur.execute(query_update, tuple(values))
            cur.execute(
                query_audit_log,
                (
                    table_affected,
                    version_id,
                    user_id,
                    action,
                    old_values_str,
                    new_values_str,
                    timestamp,
                    row_hash,
                ),
            )
            db.commit()
        except sqlite3.Error as e:
            db.rollback()
            raise e
