import sqlite3
from datetime import datetime
import json
import hashlib
from classes import Document_Header, Document_Version, Training


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
