from create_doc import create_new_document
from actions import doc_action
from revise_doc import revise_doc
from config import db_path
from datetime import datetime


if __name__ == "__main__":
    create_new_document("test1", "SOP", "albert.sevilleja", db_path)
    doc_action("APPROVE")("albert.sevilleja", "SOP-001", db_path)
    doc_action("APPROVE")(
        "quality.manager", "SOP-001", db_path, datetime.now().isoformat()
    )
    revise_doc("quality.manager", "SOP-001", db_path)
    create_new_document("test2", "SOP", "albert.sevilleja", db_path)
    doc_action("APPROVE")("albert.sevilleja", "SOP-002", db_path)
    doc_action("APPROVE")(
        "quality.manager", "SOP-002", db_path, datetime.now().isoformat()
    )
    doc_action("APPROVE")("albert.sevilleja", "SOP-001", db_path)
    doc_action("APPROVE")(
        "quality.manager", "SOP-001", db_path, datetime.now().isoformat()
    )
    revise_doc("quality.manager", "SOP-001", db_path)
    doc_action("APPROVE")("albert.sevilleja", "SOP-001", db_path)
    doc_action("REJECT")(
        "quality.manager", "SOP-001", db_path, datetime.now().isoformat(), "misc"
    )
    doc_action("APPROVE")("albert.sevilleja", "SOP-001", db_path)
    doc_action("APPROVE")(
        "quality.manager", "SOP-001", db_path, datetime.now().isoformat()
    )
    revise_doc("quality.manager", "SOP-002", db_path)
    doc_action("APPROVE")("albert.sevilleja", "SOP-002", db_path)
    doc_action("APPROVE")(
        "quality.manager", "SOP-002", db_path, datetime.now().isoformat()
    )
    create_new_document("test3", "WI", "albert.sevilleja", db_path)
    doc_action("APPROVE")("albert.sevilleja", "WI-001", db_path)
    doc_action("APPROVE")(
        "quality.manager", "WI-001", db_path, datetime.now().isoformat()
    )
    revise_doc("quality.manager", "WI-001", db_path)
    doc_action("APPROVE")("albert.sevilleja", "WI-001", db_path)
    doc_action("OBSOLETE")("quality.manager", "SOP-002", db_path)
