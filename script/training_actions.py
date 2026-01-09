import sqlite3
import os
import shutil
from types import FunctionType
from copy import deepcopy
from datetime import datetime
from classes import Training, Document_Header, Document_Version
from audit_actions import audit_log_training, audit_log_docs
from core_actions import (
    update_db,
    get_training,
    version_info,
    doc_info,
    get_training_users,
    max_id,
    inital_trining,
    update_training,
    get_active_training,
    get_user_id,
    supersed_docs,
)


def doc_action(action: str) -> FunctionType:  # type: ignore
    if action == "TRAINING":
        return do_training
    else:
        raise ValueError("Action does not exist")


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
            max_id("training_records", "training_id", db_path) + 1,
            user,
            version_training.id,
            "ASSIGNED",
            datetime.now().isoformat(),
            efective_date,
        )
        inital_trining(new_training, db_path)
        audit_log_training(None, new_training, user_assigning, action, db_path)


def do_training(user: str, doc_num: str, score: int, db_path: str) -> None:
    user_id: int = get_user_id(user, db_path)
    old_training_obj: Training = get_training(user_id, doc_num, db_path)
    new_training_obj: Training = deepcopy(old_training_obj)
    new_training_obj.score = score
    if score > 70:
        new_training_obj.status = "COMPLETED"
        new_training_obj.completion_date = datetime.now()

    else:
        new_training_obj.status = "FAILED"
    audit_log_training(
        old_training_obj,
        new_training_obj,
        user_id,
        new_training_obj.status,
        db_path,
    )
    update_training(new_training_obj, db_path)


def check_overdue(db_path: str) -> None:
    active_training: list[tuple] = get_active_training(db_path)
    if len(active_training) >= 1:
        for active in active_training:
            training_event: Training = Training(*active)
            if training_event.due_date < datetime.now():
                new_training: Training = deepcopy(training_event)
                new_training.status = "OVERDUE"
                update_training(new_training, db_path)
                audit_log_training(
                    training_event, new_training, 0, "AUTO_OVERDUE", db_path
                )


def lazy_check(db_path: str):
    query: str = "SELECT * FROM versions WHERE status = 'TRAINING'"
    with sqlite3.connect(db_path) as db:
        cur: sqlite3.Cursor = db.cursor()
        cur.execute(query)
        res: list[tuple] = cur.fetchall()
        if len(res) >= 1:
            for i in res:
                old_version: Document_Version = Document_Version(*i)
                new_version: Document_Version = deepcopy(old_version)
                major_v: int = int(old_version.version.split(".")[0])
                if datetime.fromisoformat(old_version.effective_date) < datetime.now():  # type: ignore
                    if major_v > 1:
                        supersed_docs(old_version.doc, 0, db_path)
                    new_version.status = "RELEASED"
                    new_version.file_path = new_version.file_path.replace(
                        "_TRAINING", ""
                    ).replace("02_pending_approval", "03_released")
                    if os.path.exists(old_version.file_path):
                        shutil.move(old_version.file_path, new_version.file_path)
                    new_vals: dict = audit_log_docs(
                        old_version, new_version, 0, "AUTO_RELEASE", db_path
                    )
                    update_db("versions", new_vals, new_version, db_path)
