import sqlite3
import json
import hashlib
from datetime import datetime
from doc_class import Document_Header, Document_Version


def prepare_audit_data(
    document: Document_Header,
    version: Document_Version,
    db_path: str = "/data/database/mediqms.db",
) -> tuple[dict | None, dict]:  # type: ignore
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute("SELECT count(*) FROM versions WHERE doc = ?", (document.id,))
        count_result: tuple | None = cur.fetchone()
        version_count: int = count_result[0] if count_result else 0
        if version_count <= 1:
            old_val = None
            new_val: dict = {
                "id": document.id,
                "doc_num": document.number,
                "title": document.title,
                "owner": document.owner,
                "version": version.label,
                "status": version.status,
                "path": version.file_path,
                "effective_date": version.effective_date,
            }
            return old_val, new_val
        else:
            raise (NotImplementedError)


def audit_log_documents(
    document: Document_Header,
    version: Document_Version,
    db_path: str = "/data/database/mediqms.db",
) -> None:
    old_val, new_val = prepare_audit_data(document, version, db_path=db_path)
    old_val_json: str | None = json.dumps(old_val) if old_val is not None else None
    new_val_json: str = json.dumps(new_val)
    timestamp: str = datetime.now().isoformat()
    action: str = "CREATE" if not old_val else "UPDATE"
    table_affected: str = "documents"

    str_old: str = old_val_json if old_val_json else ""
    raw_str_hash: str = f"{table_affected}{document.id}{document.owner}{action}{str_old}{new_val_json}{timestamp}"
    row_hash: str = hashlib.sha256(raw_str_hash.encode("utf-8")).hexdigest()

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
                    document.id,
                    document.owner,
                    action,
                    old_val_json,
                    new_val_json,
                    timestamp,
                    row_hash,
                ),
            )
            db.commit()
        except sqlite3.Error as e:
            db.rollback()
            raise e
