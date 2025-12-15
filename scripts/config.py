from pathlib import Path
import sqlite3
import os
from datetime import datetime
import json
import hashlib
from doc_class import Document_Header, Document_Version

BASE_DIR = Path(__file__).resolve().parent.parent

storage_root_path: str = str(BASE_DIR / "storage")
db_path: str = str(BASE_DIR / "data" / "database" / "mediqms.db")
os.makedirs(os.path.dirname(db_path), exist_ok=True)
os.makedirs(storage_root_path, exist_ok=True)

document_types: dict[str, str] = {
    "Quality Manual": "QM",
    "Policy": "POL",
    "Quality Objective": "OBJ",
    "Standard Operating Procedure": "SOP",
    "Work Instruction": "WI",
    "Form / Template": "FORM",
    "Specification": "SPEC",
    "Drawing": "DWG",
    "Bill of Materials": "BOM",
    "Software Documentation": "SW",
    "Risk Management": "RISK",
    "Instructions for Use": "IFU",
    "Labeling": "LBL",
    "Plan": "PLAN",
    "Protocol": "PROT",
    "Report": "REP",
    "External Standard": "EXT",
    "Controlled Template": "TMP",
}

status_types: list = [
    "DRAFT",
    "IN_REVIEW",
    "APPROVED_PENDING",
    "RELEASED",
    "SUPERSEDED",
    "OBSOLETE",
]

template_map: dict[str, str] = {
    "QM": str(BASE_DIR / "storage/templates/Template_QM.txt"),
    "POL": str(BASE_DIR / "storage/templates/Template_POL.txt"),
    "OBJ": str(BASE_DIR / "storage/templates/Template_OBJ.txt"),
    "SOP": str(BASE_DIR / "storage/templates/Template_SOP.txt"),
    "WI": str(BASE_DIR / "storage/templates/Template_WI.txt"),
    "FORM": str(BASE_DIR / "storage/templates/Template_FORM.txt"),
    "SPEC": str(BASE_DIR / "storage/templates/Template_SPEC.txt"),
    "BOM": str(BASE_DIR / "storage/templates/Template_BOM.txt"),
    "SW": str(BASE_DIR / "storage/templates/Template_SW.txt"),
    "RISK": str(BASE_DIR / "storage/templates/Template_RISK.txt"),
    "IFU": str(BASE_DIR / "storage/templates/Template_IFU.txt"),
    "PLAN": str(BASE_DIR / "storage/templates/Template_PLAN.txt"),
    "PROT": str(BASE_DIR / "storage/templates/Template_PROT.txt"),
    "REP": str(BASE_DIR / "storage/templates/Template_REP.txt"),
    "TMP": str(BASE_DIR / "storage/templates/Template_Meta.txt"),
    "DWG": str(BASE_DIR / "storage/mock_external/Mock_Drawing.pdf"),
    "LBL": str(BASE_DIR / "storage/mock_external/Mock_Label.jpg"),
    "EXT": str(BASE_DIR / "storage/mock_external/Mock_Standard.pdf"),
}


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
) -> None:
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
        insert into audit_log (table_affected, record_id, user, action, old_val, new_val, timestamp, hash)
        values (?, ?, ?, ?, ?, ?, ?, ?)
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


def doc_info(doc_name: str, db_path: str) -> Document_Version: ...


def version_info(doc_id: int, db_path: str) -> Document_Header: ...
