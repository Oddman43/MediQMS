import sqlite3
from datetime import datetime
import json
import hashlib
from doc_class import Document_Header, Document_Version


def user_info(user_name: str, db_path: str) -> list:
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(
            "SELECT user_id, active_flag FROM users WHERE user_name = ?", (user_name,)
        )
        result: tuple = cur.fetchone()
        user_id: int
        active_flag: int
        user_id, active_flag = result
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
        return [user_id, active_flag, user_roles]


def audit_log_docs(
    old_object: Document_Header | Document_Version | None,
    new_object: Document_Header | Document_Version,
    user_id: int,
    action: str,
    db_path: str,
) -> dict:
    if isinstance(new_object, Document_Header):
        table_affected: str = "documents"
    else:
        table_affected: str = "versions"
    if not old_object:
        old_dict: dict = {}
    else:
        old_dict = dict(old_object)
    new_dict: dict = dict(new_object)
    changed_keys: list = [k for k, v in new_dict.items() if v != old_dict.get(k)]
    old_val: dict = {k: old_dict.get(k) for k in changed_keys}
    new_val: dict = {k: new_dict.get(k) for k in changed_keys}
    old_val_json: str = json.dumps(old_val)
    new_val_json: str = json.dumps(new_val)
    record_id: int = new_object.id
    timestam: str = datetime.now().isoformat()
    raw_hash: str = f"{table_affected}{record_id}{user_id}{action}{old_val_json}{new_val_json}{timestam}"
    row_hash: str = hashlib.sha256(raw_hash.encode("utf-8")).hexdigest()
    query_insert: str = """
        INSERT INTO audit_log (table_affected, record_id, user, action, old_val, new_val, timestamp, hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
    with sqlite3.connect(db_path) as db:
        try:
            db.execute(
                query_insert,
                (
                    table_affected,
                    record_id,
                    user_id,
                    action,
                    old_val_json,
                    new_val_json,
                    timestam,
                    row_hash,
                ),
            )
            db.commit()
        except sqlite3.Error as e:
            db.rollback()
            raise e
    return new_val


def doc_info(doc_num: str, db_path: str) -> Document_Header:
    doc_id: int
    title: str
    owner_id: int
    doc_type: str
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(
            "SELECT doc_id, title, owner_id, type FROM documents WHERE doc_num = ?",
            (doc_num,),
        )
        result: tuple = cur.fetchone()
    doc_id, title, owner_id, doc_type = result
    return Document_Header(doc_id, doc_num, title, owner_id, doc_type)


def version_info(
    doc_id: int, db_path: str, modifier: list | None = None
) -> Document_Version:
    version_id: int
    version: str
    status: str
    file_path: str
    effective_date: str
    if not modifier:
        query: str = "SELECT version_id, version, status, file_path, effective_date FROM versions WHERE doc = ? ORDER BY version_id DESC LIMIT 1"
    else:
        query: str = f"SELECT version_id, version, status, file_path, effective_date FROM versions WHERE doc = ? AND {modifier[0]} = '{modifier[1]}' ORDER BY version_id DESC LIMIT 1"
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(
            query,
            (doc_id,),
        )
        results: tuple = cur.fetchone()
    version_id, version, status, file_path, effective_date = results
    return Document_Version(
        version_id, doc_id, version, status, file_path, effective_date
    )


def update_db(table: str, new_values: dict, object, db_path: str) -> None:
    update_fields: str = ", ".join([f"{key} = ?" for key in new_values.keys()])
    values: list = list(new_values.values())
    values.append(object.id)
    query_update: str = f"UPDATE {table} SET {update_fields} WHERE version_id = ?"
    with sqlite3.connect(db_path) as db:
        try:
            cur: sqlite3.Cursor = db.cursor()
            cur.execute(query_update, tuple(values))
            db.commit()
        except sqlite3.Error as e:
            db.rollback()
            raise e


def max_id(table: str, field: str, db_path: str):
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(f"SELECT MAX({field}) FROM {table}")
        return cur.fetchone()[0]


def create_version(version_obj: Document_Version, db_path: str) -> None:
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(
            "INSERT INTO versions (version_id, doc, version, status, file_path, effective_date) VALUES (?, ?, ?, ?, ?, ?)",
            version_obj.to_db_tuple(),
        )
        db.commit()


def create_doc(doc_obj: Document_Header, db_path: str) -> None:
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(
            "INSERT INTO documents (doc_id, doc_num, title, owner_id, type) VALUES (?, ?, ?, ?, ?)",
            doc_obj.to_db_tuple(),
        )
        db.commit()
