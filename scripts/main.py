# from doc_class import Document_Header, Document_Version
from doc_control_functions import create_new_document, write_new_doc
from config import db_path


if __name__ == "__main__":
    doc, ver = create_new_document("test", "SOP", 2, db_path)
    write_new_doc(doc, ver, db_path)
