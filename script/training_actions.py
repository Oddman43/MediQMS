from types import FunctionType
from copy import deepcopy
from datetime import datetime
from training_class import Training
from core_fn import (
    get_training,
    audit_log_training,
    update_training,
    get_active_training,
    get_user_id,
)


def training_actions(action: str) -> FunctionType: ...


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
            if training_event.due_date > datetime.now():
                new_training: Training = deepcopy(training_event)
                new_training.status = "OVERDUE"
                update_training(new_training, db_path)
                audit_log_training(
                    training_event, new_training, 0, "AUTO_OVERDUE", db_path
                )
