from datetime import datetime
from config import training_types


class Training:
    def __init__(
        self,
        training_id: int,
        user_id: int,
        version_id: int,
        status: str,
        assigned_date: str,
        due_date: str,
        completion_date: str | None = None,
        score: int | None = None,
    ) -> None:
        self.id: int = training_id
        self.user_id: int = user_id
        self.version_id: int = version_id
        self.status: str = status
        self.assigned_date: datetime = datetime.fromisoformat(assigned_date)
        self.due_date: datetime = datetime.fromisoformat(due_date)
        if completion_date:
            self.completion_date: datetime | None = datetime.fromisoformat(
                completion_date
            )
        else:
            self.completion_date = None
        self.score: int | None = score

    def _checks(self) -> None | str:
        if self.status not in training_types:
            return "Status not valid or empty"

    def __iter__(self):
        yield "training_id", self.id
        yield "user_id", self.user_id
        yield "version_id", self.version_id
        yield "status", self.status
        yield "assigned_date", self.assigned_date.isoformat()
        yield "due_date", self.due_date.isoformat()
        if self.completion_date:
            yield "completion_date", self.completion_date.isoformat()
        else:
            yield "completion_date", None
        yield "score", self.score

    def to_db_tuple(self) -> tuple:
        completion_str: str | None = (
            self.completion_date.isoformat() if self.completion_date else None
        )
        return (
            self.id,
            self.user_id,
            self.version_id,
            self.status,
            self.assigned_date.isoformat(),
            self.due_date.isoformat(),
            completion_str,
            self.score,
        )
