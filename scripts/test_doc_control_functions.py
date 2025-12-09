import pytest
import sqlite3
import os
from unittest.mock import patch

from doc_control_functions import create_new_document
from main import document_types, template_map


db_file: str = "tests/test_eqms.db"


@pytest.fixture(autouse=True)
def mock_filesystem():
    with (
        patch("shutil.copy") as mock_copy,
        patch("os.path.exists", return_value=True) as mock_exists,
    ):
        yield mock_copy, mock_exists


@pytest.fixture
def mock_db():
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "CREATE TABLE documents (doc_id INTEGER PRIMARY KEY, doc_num TEXT, title TEXT, owner_id INTEGER, type TEXT)"
        )
        conn.execute(
            "CREATE TABLE users (user_id INTEGER PRIMARY KEY, active_flag INTEGER)"
        )
        conn.execute(
            "CREATE TABLE versions (version_id INTEGER PRIMARY KEY, doc INTEGER, version TEXT, status TEXT, file_path TEXT, effective_date TEXT)"
        )

        conn.execute("INSERT INTO users (user_id, active_flag) VALUES (1, 1)")
        conn.execute("INSERT INTO users (user_id, active_flag) VALUES (99, 0)")
        conn.commit()
    yield db_file
    if os.path.exists(db_file):
        os.remove(db_file)


def test_create_document_cold_start(mock_db, mock_filesystem):
    mock_copy, _ = mock_filesystem
    header, version = create_new_document("Primer Documento", "SOP", 1, db_path=mock_db)

    assert header.id == 1
    assert header.number == "SOP-001"
    assert header.type == "SOP"

    assert version.doc == 1
    assert version.label == "0.1"
    assert version.status == "DRAFT"

    mock_copy.assert_called_once()
    args, _ = mock_copy.call_args
    destination = args[1]

    assert "storage/01_drafts" in str(destination)
    assert "SOP-001_V0.1_DRAFT.txt" in str(destination)


def test_create_document_incremental(mock_db, mock_filesystem):
    mock_copy, _ = mock_filesystem
    with sqlite3.connect(mock_db) as conn:
        conn.execute(
            "INSERT INTO documents (doc_id, doc_num, title, type, owner_id) VALUES (10, 'SOP-001', 'Old Doc', 'SOP', 1)"
        )
        conn.execute(
            "INSERT INTO versions (version_id, doc, version, status, file_path) VALUES (50, 10, '0.1', 'DRAFT', 'path')"
        )
        conn.commit()

    header, version = create_new_document(
        title="Segundo Documento", type="SOP", owner_id=1, db_path=mock_db
    )

    assert header.id == 11
    assert header.number == "SOP-002"
    assert version.id == 51


def test_create_document_external_pdf(mock_db, mock_filesystem):
    mock_copy, _ = mock_filesystem

    header, version = create_new_document(
        title="Plano Mecánico", type="DWG", owner_id=1, db_path=mock_db
    )

    assert header.type == "DWG"
    assert header.number == "DWG-001"

    args, _ = mock_copy.call_args
    destination = str(args[1])

    assert ".pdf" in destination
    assert ".txt" not in destination


def test_fail_duplicate_title(mock_db, mock_filesystem):
    with sqlite3.connect(mock_db) as conn:
        conn.execute("INSERT INTO documents (title) VALUES ('Titulo Unico')")
        conn.commit()

    with pytest.raises(ValueError, match="already exists"):
        create_new_document(
            title="Titulo Unico", type="SOP", owner_id=1, db_path=mock_db
        )


def test_fail_inactive_owner(mock_db, mock_filesystem):
    with pytest.raises(ValueError, match="inactive"):
        create_new_document(
            title="Doc Hacker", type="SOP", owner_id=99, db_path=mock_db
        )


def test_fail_invalid_type(mock_db, mock_filesystem):
    with pytest.raises(ValueError, match="Invalid type"):
        create_new_document(
            title="Doc", type="TIPO_INVENTADO", owner_id=1, db_path=mock_db
        )


def test_fail_configuration_error(mock_db, mock_filesystem):
    with (
        patch.dict(document_types, {"Zombie Doc": "ZOM"}),
        patch.dict(template_map, {}, clear=False),
    ):
        with pytest.raises(ValueError, match="Configuration Error"):
            create_new_document("Doc", "ZOM", 1, db_path=mock_db)


def test_incremental_corrupt_format(mock_db, mock_filesystem):
    mock_copy, _ = mock_filesystem
    with sqlite3.connect(mock_db) as conn:
        conn.execute(
            "INSERT INTO documents (doc_id, doc_num, title, type) VALUES (10, 'SOP001', 'Bad Fmt', 'SOP')"
        )
        conn.execute("INSERT INTO versions (version_id, doc) VALUES (50, 10)")
        conn.commit()
    header, _ = create_new_document("New Doc", "SOP", 1, db_path=mock_db)
    assert header.number == "SOP-001"
