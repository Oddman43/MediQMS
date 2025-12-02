from dataclasses import dataclass
import re
from ..main import document_types, status_types


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


@dataclass
class Document_Version:
    id: int
    doc: int
    label: str
    status: str
    file_path: str
    effective_date: str

    def __post_init__(self) -> None:
        basic_check: str | None = self._basic_checks()
        if basic_check is not None:
            raise (ValueError(basic_check))

    def _basic_checks(self) -> str | None:
        if not re.fullmatch(r"^\d+\.\d+$", self.label):
            return f"Invalid label major or minor is not an integer: '{self.label}'"
        if self.status not in status_types:
            return f"Invalid version status: '{self.status}'"
        if not self.file_path:
            return "File path can not be empty"
        if self.status == "RELEASED" and self.effective_date is None:
            return f"Effective date can not be empty in {self.status} documents"
        else:
            return None
