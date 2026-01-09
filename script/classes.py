from dataclasses import dataclass
from datetime import datetime
import re
from config import document_types, status_types, training_types


@dataclass
class Document_Header:
    id: int
    number: str
    title: str
    owner: int
    type: str

    def __post_init__(self) -> None:
        check_1: str | None = self._checks()
        if check_1 is not None:
            raise (ValueError(check_1))

    def _checks(self) -> None | str:
        if not self.title or self.title == "":
            return "Title cannot be empty"
        elif self.type not in document_types.values():
            return f"Invalid document type: '{self.type}'"
        elif not re.fullmatch(r"^[a-zA-Z]{2,4}-\d{3}$", self.number):
            return f"Invalid document number format: '{self.number}'"
        elif self.type != self.number.split("-")[0]:
            return f"Mismatch: Type is '{self.type}' but Number starts with '{self.number.split('-')[0]}'"
        else:
            return None

    def __iter__(self):
        yield "doc_id", self.id
        yield "doc_num", self.number
        yield "title", self.title
        yield "owner_id", self.owner
        yield "type", self.type

    def to_db_tuple(self) -> tuple:
        return (self.id, self.number, self.title, self.owner, self.type)


@dataclass
class Document_Version:
    id: int
    doc: int
    version: str
    status: str
    file_path: str
    effective_date: str | None

    def __post_init__(self) -> None:
        basic_check: str | None = self._basic_checks()
        if basic_check is not None:
            raise (ValueError(basic_check))

    def _basic_checks(self) -> str | None:
        if not re.fullmatch(r"^\d+\.\d+$", self.version):
            return f"Invalid version major or minor is not an integer: '{self.version}'"
        if self.status not in status_types:
            return f"Invalid version status: '{self.status}'"
        if not self.file_path:
            return "File path can not be empty"
        if self.status == "RELEASED" and self.effective_date is None:
            return f"Effective date can not be empty in {self.status} documents"
        else:
            return None

    def __iter__(self):
        yield "version_id", self.id
        yield "doc", self.doc
        yield "version", self.version
        yield "status", self.status
        yield "file_path", self.file_path
        yield "effective_date", self.effective_date

    def to_db_tuple(self) -> tuple:
        return (
            self.id,
            self.doc,
            self.version,
            self.status,
            self.file_path,
            self.effective_date,
        )


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
