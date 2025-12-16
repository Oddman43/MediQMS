from types import FunctionType
import os
import shutil
import sqlite3
import hashlib
from datetime import datetime
from copy import deepcopy
from core_fn import (
    audit_log_docs,
    doc_info,
    version_info,
    user_info,
    update_db,
    create_version,
    max_id,
)
from doc_class import Document_Header, Document_Version


def doc_action(action: str) -> FunctionType:  # type: ignore
    if action == "APPROVE":
        return approve_document
    elif action == "REJECT":
        return reject_doc


def approve_document(
    user: str,
    doc_num: str,
    db_path: str,
    date: str | None = None,
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
        version_new.status = "RELEASED"
        action: str = "RELEASE"
        if not date:
            raise ValueError(f"Date field is obligatory: '{date}'")
        version_new.effective_date = date  # type: ignore
        major_version: int = int(version_old.version.split(".")[0])
        new_version_major: int = major_version + 1
        version_new.version = f"{new_version_major}.0"
        if major_version >= 1:
            supersed_docs(parent_doc.id, user_id, db_path)
        version_new.file_path = (
            version_old.file_path.replace("_DRAFT", "")
            .replace(version_old.version, version_new.version)
            .replace("01_drafts", "03_released")
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
    write_approval(user_id, user_role, version_new, "APPROVE", db_path)


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


def write_approval(
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
        insert_query: str = "INSERT INTO approvals (version_id, approver_id, date_signature, status, role_signing, signature_hash) VALUES (?, ?, ?, ?, ?, ?)"
        if user_type == "owner":
            for info in [["APPROVED", "OWNER"], ["PENDING", "QUALITY_MANAGER"]]:
                status: str
                role: str
                status, role = info
                row_info: str = f"{version_id}{user_id}{timestamp}{status}{role}"
                row_hash: str = hashlib.sha256(row_info.encode("utf-8")).hexdigest()
                cur.execute(
                    insert_query,
                    (version_id, user_id, timestamp, status, role, row_hash),
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
    write_approval(user_id, user_role, version_root, action, db_path, comment)
