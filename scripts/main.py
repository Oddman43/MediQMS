from create_doc import create_new_document
from approvals import approve_document
from revise_doc import revise_doc
from config import db_path
from datetime import datetime


if __name__ == "__main__":
    create_new_document("test1", "SOP", "charlie_eng", db_path)
    approve_document("charlie_eng", "SOP-001", db_path)
    approve_document("alice_qa", "SOP-001", db_path, datetime.now().isoformat())
    # revise_doc("alice_qa", "SOP-001", db_path)
    # doc, ver = create_new_document("test2", "SOP", 4, db_path)
    # write_new_doc(doc, ver, db_path)
    # approve_document("charlie_eng", 2, db_path)
    # approve_document("alice_qa", 2, db_path, datetime.now().isoformat())
