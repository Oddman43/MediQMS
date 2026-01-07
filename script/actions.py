from types import FunctionType
import os
import shutil
import sqlite3
import hashlib
from datetime import datetime, timedelta
from copy import deepcopy
from core_fn import (
    audit_log_docs,
    doc_info,
    version_info,
    user_info,
    update_db,
    create_version,
    max_id,
    get_training_users,
    inital_trining,
    audit_log_training,
)
from doc_class import Document_Header, Document_Version
from training_class import Training


def doc_action(action: str) -> FunctionType:  # type: ignore
    if action == "APPROVE":
        return approve_document
    elif action == "REJECT":
        return reject_doc
    elif action == "OBSOLETE":
        return obsolete_doc


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


def assign_training(
    doc_num: str, efective_date: str, user_assigning: int, db_path: str
):
    action: str = "ASSING"
    parent_doc: Document_Header = doc_info(doc_num, db_path)
    version_training: Document_Version = version_info(
        parent_doc.id, db_path, ["status", "TRAINING"]
    )
    users_to_train: list[int] = get_training_users(db_path)
    for user in users_to_train:
        new_training: Training = Training(
            max_id("training_records", "training_id", db_path),
            user,
            version_training.id,
            "ASSIGNED",
            datetime.now().isoformat(),
            efective_date,
            None,
        )
        inital_trining(new_training, db_path)
        audit_log_training(None, new_training, user_assigning, action, db_path)
