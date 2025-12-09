import pytest
import sqlite3
import os
from unittest.mock import patch, MagicMock

from doc_control_functions import create_new_document, write_new_doc
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
        conn.execute("""
                    CREATE TABLE audit_log (
                        log_id INTEGER PRIMARY KEY,
                        table_affected TEXT,
                        record_id INTEGER,
                        user INTEGER,
                        action TEXT,
                        old_val TEXT,
                        new_val TEXT,
                        timestamp TEXT,
                        hash TEXT,
                        FOREIGN KEY(user) REFERENCES users(user_id)
                    )
                """)

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


def test_write_new_doc_success(mock_db):
    mock_header = MagicMock()
    mock_header.to_db_tuple.return_value = (100, "DOC-100", "Nuevo Documento", 1, "pdf")
    mock_header.id = 100
    mock_header.number = "DOC-100"
    mock_header.title = "Nuevo Documento"
    mock_header.owner = 1

    mock_version = MagicMock()
    mock_version.to_db_tuple.return_value = (
        500,
        100,
        "0.1",
        "DRAFT",
        "/ruta/falsa.pdf",
        "2023-10-01",
    )
    mock_version.label = "0.1"
    mock_version.status = "DRAFT"
    mock_version.file_path = "/ruta/falsa.pdf"
    mock_version.effective_date = "2023-10-01"

    write_new_doc(mock_header, mock_version, db_path=mock_db)
    with sqlite3.connect(mock_db) as conn:
        doc = conn.execute(
            "SELECT title, type FROM documents WHERE doc_id=100"
        ).fetchone()
        assert doc is not None
        assert doc[0] == "Nuevo Documento"

        ver = conn.execute(
            "SELECT status, file_path FROM versions WHERE version_id=500"
        ).fetchone()
        assert ver is not None
        assert ver[0] == "DRAFT"


def test_write_new_doc_rollback_on_error(mock_db):
    with sqlite3.connect(mock_db) as conn:
        conn.execute("INSERT INTO versions (version_id) VALUES (500)")
        conn.commit()
    mock_header = MagicMock()
    mock_header.to_db_tuple.return_value = (200, "DOC-200", "Doc Fallido", 1, "pdf")
    mock_version = MagicMock()
    mock_version.to_db_tuple.return_value = (500, 200, "1.0", "DRAFT", "path", "date")
    with pytest.raises(sqlite3.IntegrityError):
        write_new_doc(mock_header, mock_version, db_path=mock_db)
    with sqlite3.connect(mock_db) as conn:
        cursor = conn.execute("SELECT * FROM documents WHERE doc_id=200")
        assert cursor.fetchone() is None, (
            "El rollback falló: el documento se guardó a pesar del error en la versión."
        )
