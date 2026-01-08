import sqlite3
from datetime import datetime
import json
import hashlib
import shutil
import os
from copy import deepcopy
from doc_class import Document_Header, Document_Version
from training_class import Training


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


def audit_log_training(
    old_training_obj: Training | None,
    new_training_obj: Training,
    user_id: int,
    action: str,
    db_path: str,
):
    table_affected: str = "training_records"
    if not old_training_obj:
        old_dict: dict = {}
    else:
        old_dict = dict(old_training_obj)
    new_dict: dict = dict(new_training_obj)
    changed_keys: list = [k for k, v in new_dict.items() if v != old_dict.get(k)]
    old_val: dict = {k: old_dict.get(k) for k in changed_keys}
    new_val: dict = {k: new_dict.get(k) for k in changed_keys}
    old_val_json: str = json.dumps(old_val)
    new_val_json: str = json.dumps(new_val)
    record_id: int = new_training_obj.id
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
        result = cur.fetchone()[0]
        if result:
            return int(result)
        else:
            return 1


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


def supersed_docs(doc_id: int, user_id: int, db_path: str) -> None:
    action: str = "SUPERSEDED"
    version_old: Document_Version = version_info(
        doc_id, db_path, ["status", "RELEASED"]
    )
    version_superseded: Document_Version = deepcopy(version_old)
    tmp_file_path: str = version_superseded.file_path.replace(
        "03_released", "04_archive"
    )
    root, ext = os.path.splitext(tmp_file_path)
    version_superseded.file_path = f"{root}_SUPERSEDED{ext}"
    version_superseded.status = "SUPERSEDED"
    shutil.move(version_old.file_path, version_superseded.file_path)
    new_val: dict = audit_log_docs(
        version_old, version_superseded, user_id, action, db_path
    )
    update_db("versions", new_val, version_superseded, db_path)


def get_training_users(db_path: str) -> list[int]:
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(
            """
            SELECT user 
            FROM users_roles 
            WHERE role = (SELECT role_id FROM roles WHERE role_name = 'General Employee') 
            AND user IN (SELECT user_id FROM users WHERE active_flag = 1);
            """
        )
        return [i[0] for i in cur.fetchall()]


def inital_trining(training_obj: Training, db_path: str) -> None:
    query_training = """
    INSERT INTO training_records(training_id, user_id, version_id, status, assigned_date, due_date, completion_date, score) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
    """
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(query_training, training_obj.to_db_tuple())
        db.commit()


def get_training(user_id: int, doc_num: str, db_path: str) -> Training:
    doc_obj: Document_Header = doc_info(doc_num, db_path)
    version_obj: Document_Version = version_info(
        doc_obj.id, db_path, ["status", "TRAINING"]
    )
    query: str = """
                SELECT * FROM training_records WHERE user_id = ? AND version_id = ? AND status IN ('ASSIGNED','FAILED')
                """
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(query, (user_id, version_obj.id))
        res: tuple = cur.fetchone()
        if not res:
            raise ValueError("No training for user and document")
        return Training(*res[:-1])


def lazy_check(): ...


# Pasar de training a released cuando toque
