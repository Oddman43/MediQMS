import os
import shutil
from copy import deepcopy
from doc_class import Document_Version, Document_Header
from core_fn import (
    doc_info,
    version_info,
    user_info,
    update_db,
    audit_log_docs,
    max_id,
    create_version,
)


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
    user_id, _, user_roles = user_info(user, db_path)
    # cur.execute(
    #     "SELECT version_id FROM versions WHERE doc = ? AND status IN ('DRAFT', 'IN_REVIEW')",
    #     (doc_id,),
    # )
    # if cur.fetchone():
    #     raise ValueError(
    #         f"Draft or In review already in process for document: '{doc_num}'"
    #     )

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
    new_vals: dict = audit_log_docs(version_old, version_new, user_id, action, db_path)
    # update_db("versions", new_vals, new_version, db_path)
    create_version(new_version, db_path)
