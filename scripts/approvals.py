import os
import shutil
from copy import deepcopy
from base_fns import audit_log_docs, doc_info, version_info, user_info, update_db
from doc_class import Document_Header, Document_Version


def approve_document(
    user: str, doc_num: str, db_path: str, date: str | None = None
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
    version_released: Document_Version = version_info(
        doc_id, db_path, ["status", "RELEASED"]
    )
    new_version: Document_Version = deepcopy(version_released)
    tmp_file_path: str = new_version.file_path.replace("03_released", "04_archive")
    root, ext = os.path.splitext(tmp_file_path)
    new_version.file_path = f"{root}_SUPERSEDED{ext}"
    shutil.move(version_released.file_path, new_version.file_path)
    new_val: dict = audit_log_docs(
        version_released, new_version, user_id, action, db_path
    )
    update_db("versions", new_val, new_version, db_path)
