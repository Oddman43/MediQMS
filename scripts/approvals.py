import sqlite3
from datetime import datetime
import json
import hashlib
import os
import shutil


def approve_document(
    user: str, version_id: int, db_path: str, date: str | None = None
) -> None:
    user_role: str
    doc_data: tuple
    user_role, doc_data = approve_checks(user, version_id, db_path)
    doc_id: int
    status: str
    file_path: str
    version: str
    effective_date: str
    owner_id: int
    user_id: int
    doc_id, status, file_path, version, effective_date, owner_id, user_id = doc_data
    table_affected: str = "versions"
    timestamp: str = datetime.now().isoformat()
    if user_id == owner_id and status == "DRAFT":
        new_status: str = "IN_REVIEW"
        action: str = "UPDATE"
        old_values: dict = {"status": status}
        new_values: dict = {"status": new_status}
    elif user_role == "QM" and status == "IN_REVIEW":
        new_status: str = "RELEASED"
        action: str = "RELEASE"
        if not date:
            raise ValueError(f"Date field is obligatory: '{date}'")
        new_effective_date: str = date  # type: ignore
        major_version: int = int(version.split(".")[0])
        new_version_major: int = major_version + 1
        new_version: str = f"{new_version_major}.0"
        if major_version >= 1:
            supersed_docs(doc_id, user_id, db_path)
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


def approve_checks(user: str, version_id: int, db_path: str) -> tuple[str, tuple]:
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
        user_type: str = "owner"
    elif "Quality Manager" in user_roles and status == "IN_REVIEW":
        user_type: str = "QM"
    else:
        raise PermissionError(f"Action not permited for user: '{user}'")
    approval_data: tuple = (
        doc_id,
        status,
        file_path,
        version,
        effective_date,
        owner_id,
        user_id,
    )
    return user_type, approval_data


def supersed_docs(doc_id: int, user_id: int, db_path: str) -> None:
    action: str = "SUPERSEDED"
    affected_table: str = "versions"
    timestamp: str = datetime.now().isoformat()
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(
            "SELECT version_id, file_path FROM versions WHERE doc = ? AND status = 'RELEASED' ORDER BY version_id DESC LIMIT 1",
            (doc_id,),
        )
        version_id: int
        file_path_release: str
        version_id, file_path_release = cur.fetchone()

    tmp_file_path: str = file_path_release.replace("03_released", "04_archive")
    root, ext = os.path.splitext(tmp_file_path)
    new_file_path: str = f"{root}_SUPERSEDED{ext}"
    shutil.move(file_path_release, new_file_path)

    old_val: dict = {
        "status": "RELEASED",
        "file_path": file_path_release,
    }
    new_val: dict = {
        "status": "SUPERSEDED",
        "file_path": new_file_path,
    }
    old_val_str: str = json.dumps(old_val)
    new_val_str: str = json.dumps(new_val)
    raw_str_hash: str = f"{affected_table}{version_id}{user_id}{action}{old_val_str}{new_val_str}{timestamp}"
    row_hash: str = hashlib.sha256(raw_str_hash.encode("utf-8")).hexdigest()
    update_fields: str = ", ".join([f"{key} = ?" for key in new_val.keys()])
    values: list = list(new_val.values())
    values.append(version_id)
    query_update: str = f"UPDATE versions SET {update_fields} WHERE version_id = ?"
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
                    affected_table,
                    version_id,
                    user_id,
                    action,
                    old_val_str,
                    new_val_str,
                    timestamp,
                    row_hash,
                ),
            )
            db.commit()
        except sqlite3.Error as e:
            db.rollback()
            raise e
