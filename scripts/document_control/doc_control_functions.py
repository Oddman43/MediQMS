from doc_class import Document_Header, Document_Version
from ..main import document_types, status_types
import sqlite3

db_path = "/data/database/mediqms.db"

# def create_new_document(
#     title: str, type: str, owner_id: int
# ) -> tuple[Document_Header, Document_Version]:


def create_new_document(title: str, type: str, owner_id: int):
    if type not in document_types.values():
        raise (ValueError(f"Invalid type, not in valid types: '{type}'"))
    with sqlite3.connect(db_path) as db:
        cursor: sqlite3.Cursor = db.cursor()
        cursor.execute("SELECT count(*) FROM documents WHERE title = ?", (title,))
        if cursor.fetchone()[0] > 0:
            raise ValueError(f"Document title already exists: '{title}'")
        cursor.execute(
            "SELECT count(*) FROM users WHERE user_id = ? AND active_flag = 1",
            (owner_id,),
        )
        if cursor.fetchone()[0] == 0:
            raise ValueError(f"Owner ID {owner_id} does not exist or is inactive")
        cursor.execute("SELECT MAX(doc_id) FROM documents")
        last_doc_id: int | None = cursor.fetchone()[0]
        next_doc_id: int = 1 if last_doc_id is None else last_doc_id + 1

        cursor.execute("SELECT MAX(version_id) FROM versions")
        last_ver_id: int | None = cursor.fetchone()[0]
        next_ver_id: int = 1 if last_ver_id is None else last_ver_id + 1

        cursor.execute(
            "SELECT doc_num FROM documents WHERE type = ? ORDER BY doc_id DESC LIMIT 1",
            (type,),
        )
        result_num: tuple | None = cursor.fetchone()

        if result_num is None:
            next_doc_num: str = f"{type}-001"
        else:
            last_num_str: str = result_num[0]
            parts: list[str] = last_num_str.split("-")
            if len(parts) < 2:
                next_doc_num: str = f"{type}-001"
            else:
                current_seq: int = int(parts[1])
                next_seq: int = current_seq + 1
                next_doc_num: str = f"{type}-{next_seq:03d}"


# validacion inicial
# title no esta repetido en la db
# type es valido
# owner_id valido y active

# numeracion
# check el type y ver ultimo numero
# tener en cuenta coldstart

# consultar id
# ver max id de documento y version y sumarle 1

# instanciar los objetos
# Document_Header
# Document_Version

# insert a la db

# return los objetos
