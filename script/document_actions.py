from types import FunctionType
import os
import shutil
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from copy import deepcopy
from config import document_types, template_map, storage_root_path
from core_actions import (
    doc_info,
    version_info,
    user_info,
    update_db,
    create_version,
    max_id,
    create_doc,
)
from audit_actions import audit_log_docs
from training_actions import assign_training
from classes import Document_Header, Document_Version


def doc_action(action: str) -> FunctionType:  # type: ignore
    if action == "APPROVE":
        return approve_document
    elif action == "REJECT":
        return reject_doc
    elif action == "OBSOLETE":
        return obsolete_doc
    else:
        raise ValueError("Action does not exist")


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
    efective_date: str | None = (datetime.now() + timedelta(days=15)).isoformat(),
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
        if datetime.fromisoformat(efective_date) < (
            datetime.now() + timedelta(days=14)
        ):
            raise ValueError("Efective date must be at least 15 days from today")
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


def approve_checks(user: str, doc_num: str, db_path: str) -> tuple:
    parent_doc: Document_Header = doc_info(doc_num, db_path)
    version_newest: Document_Version = version_info(parent_doc.id, db_path)
    user_id: int
    active_flag: int
    user_roles: list
    user_id, active_flag, user_roles = user_info(user, db_path)
    if active_flag == 0:
        raise ValueError(f"User '{user}' is inactive")
    if user_id == parent_doc.owner and version_newest.status == "DRAFT":
        user_type: str = "owner"
    elif "Quality Manager" in user_roles and version_newest.status == "IN_REVIEW":
        user_type: str = "QM"
    else:
        raise PermissionError(f"Action not permited for user: '{user}'")
    return parent_doc, version_newest, user_type, user_id


def write_approvals_table(
    user_id: int,
    user_type: str,
    version_obj: Document_Version,
    action: str,
    db_path: str,
    comment: str | None = None,
) -> None:
    timestamp: str = datetime.now().isoformat()
    version_id: int = version_obj.id
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        insert_query: str = """INSERT INTO approvals 
                            (version_id, approver_id, date_signature, status, role_signing, signature_hash) 
                            VALUES (?, ?, ?, ?, ?, ?)"""
        if user_type == "owner":
            for info in [["APPROVED", "OWNER"], ["PENDING", "QUALITY_MANAGER"]]:
                status: str
                role: str
                status, role = info
                row_info: str = f"{version_id}{user_id if role == 'OWNER' else 2}{timestamp}{status}{role}"
                row_hash: str = hashlib.sha256(row_info.encode("utf-8")).hexdigest()
                cur.execute(
                    insert_query,
                    (
                        version_id,
                        user_id if role == "OWNER" else 2,
                        timestamp,
                        status,
                        role,
                        row_hash,
                    ),
                )
        else:
            role: str = "QUALITY_MANAGER"
            if action == "APPROVE":
                status: str = "APPROVED"
                update_query: str = """UPDATE approvals
                    SET
                        approver_id = ?,
                        date_signature = ?,
                        status = ?,
                        signature_hash = ?
                    WHERE
                        version_id = ?
                        AND STATUS = 'PENDING'
                    """
                row_info: str = f"{version_id}{user_id}{timestamp}{status}{role}"
                row_hash: str = hashlib.sha256(row_info.encode("utf-8")).hexdigest()
                cur.execute(
                    update_query,
                    (user_id, timestamp, status, row_hash, version_id),
                )
            elif action == "REJECT":
                status: str = "REJECTED"
                update_query: str = """UPDATE approvals
                    SET
                        approver_id = ?,
                        date_signature = ?,
                        status = ?,
                        signature_hash = ?,
                        comments = ?
                    WHERE
                        version_id = ?
                        AND STATUS = 'PENDING'
                    """
                row_info: str = f"{version_id}{user_id}{timestamp}{status}{role}"
                row_hash: str = hashlib.sha256(row_info.encode("utf-8")).hexdigest()
                cur.execute(
                    update_query,
                    (user_id, timestamp, status, row_hash, comment, version_id),
                )
            else:
                raise ValueError(f"Action not permited: '{action}'")
        db.commit()


def reject_doc(
    user: str,
    doc_num: str,
    db_path: str,
    date: str | None = None,
    comment: str | None = None,
) -> None:
    action: str = "REJECT"
    parent_doc: Document_Header
    version_root: Document_Version
    user_role: str
    user_id: int
    parent_doc, version_root, user_role, user_id = approve_checks(
        user, doc_num, db_path
    )
    version_old = deepcopy(version_root)
    version_new = deepcopy(version_root)
    if user_role != "QM":
        raise ValueError(
            f"Only quality manager can reject drafts, '{user}' is not Quality Manager"
        )
    if version_old.status != "IN_REVIEW":
        raise ValueError(f"Document does not have in review version: '{doc_num}'")
    if not comment:
        raise ValueError("Rejection needs a comment")
    max_v_id: int = max_id("versions", "version_id", db_path)
    version_new.id = max_v_id + 1
    major_minor_old = version_old.version
    major_old: int = int(major_minor_old.split(".")[0])
    minor_old: int = int(major_minor_old.split(".")[1])
    minor_new: int = minor_old + 1
    major_minor_new: str = f"{major_old}.{minor_new}"
    version_new.version = major_minor_new
    version_new.file_path = version_old.file_path.replace(
        major_minor_old, major_minor_new
    )
    shutil.copy(version_old.file_path, version_new.file_path)
    version_old.file_path = version_old.file_path.replace(
        "01_drafts", "04_archive"
    ).replace("_DRAFT", "_REJECTED")
    version_old.status = "REJECTED"
    version_new.status = "DRAFT"
    shutil.move(version_root.file_path, version_old.file_path)
    rejected_new_vals: dict = audit_log_docs(
        version_root, version_old, user_id, action, db_path
    )
    audit_log_docs(version_root, version_new, user_id, "CREATE", db_path)
    update_db("versions", rejected_new_vals, version_old, db_path)
    create_version(version_new, db_path)
    write_approvals_table(user_id, user_role, version_root, action, db_path, comment)


def obsolete_doc(user: str, doc_num: str, db_path: str):
    action: str = "OBSOLETE"
    user_id: int
    active_flag: int
    user_roles: list
    user_id, active_flag, user_roles = user_info(user, db_path)
    if active_flag == 0:
        raise ValueError(f"User is not active: '{user}'")
    if "Quality Manager" not in user_roles:
        raise ValueError(f"Only quality manager can obsolete docs: '{user}'")
    parent_doc: Document_Header = doc_info(doc_num, db_path)
    version_old: Document_Version = version_info(
        parent_doc.id, db_path, ["status", "RELEASED"]
    )
    version_new: Document_Version = deepcopy(version_old)
    new_file_path: str = version_old.file_path.replace("03_released", "04_archive")
    root: str
    ext: str
    root, ext = os.path.splitext(new_file_path)
    version_new.file_path = f"{root}_{action}{ext}"
    version_new.status = action
    shutil.move(version_old.file_path, version_new.file_path)
    new_vals: dict = audit_log_docs(version_old, version_new, user_id, action, db_path)
    update_db("versions", new_vals, version_new, db_path)


def revise_doc(user: str, doc_num: str, db_path: str) -> None:
    action: str = "REVISE"
    parent_doc: Document_Header = doc_info(doc_num, db_path)
    version_old: Document_Version = version_info(
        parent_doc.id, db_path, ["status", "RELEASED"]
    )
    version_new: Document_Version = deepcopy(version_old)
    version_new.effective_date = None
    user_id: int
    user_roles: list
    active_flag: int
    user_id, active_flag, user_roles = user_info(user, db_path)
    if active_flag == 0:
        raise ValueError(f"User '{user}' is not active")
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(
            "SELECT version_id FROM versions WHERE doc = ? AND status IN ('DRAFT', 'IN_REVIEW')",
            (parent_doc.id,),
        )
        if cur.fetchone():
            raise ValueError(
                f"Draft or In review already in process for document: '{doc_num}'"
            )

    if not (user_id == parent_doc.owner or "Quality Manager" in user_roles):
        raise PermissionError(f"User not allwed to revise document: '{doc_num}'")
    v_major: int = int(version_old.version.split(".")[0])
    v_minor: int = int(version_old.version.split(".")[1]) + 1
    new_version: str = f"{v_major}.{v_minor}"
    version_new.version = new_version
    version_new.status = "DRAFT"
    tmp_path: str = version_old.file_path.replace(
        version_old.version, new_version
    ).replace("03_released", "01_drafts")
    root, ext = os.path.splitext(tmp_path)
    new_file_path: str = f"{root}_DRAFT{ext}"
    version_new.file_path = new_file_path
    new_id: int = max_id("versions", "version_id", db_path) + 1
    version_new.id = new_id
    shutil.copy(version_old.file_path, version_new.file_path)
    audit_log_docs(None, version_new, user_id, action, db_path)
    create_version(version_new, db_path)
