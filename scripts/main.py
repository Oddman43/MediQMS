from doc_control_functions import create_new_document, write_new_doc
from approvals import approve_document
from revise_doc import revise_doc
from config import db_path
from datetime import datetime


if __name__ == "__main__":
    doc, ver = create_new_document("test1", "SOP", 4, db_path)
    write_new_doc(doc, ver, db_path)
    approve_document("charlie_eng", 1, db_path)
    approve_document("alice_qa", 1, db_path, datetime.now().isoformat())
