# from document_control.doc_class import Document_Header, Document_Version
# import sqlite3

storage_root_path: str = "/storage"

db_path = "/data/database/mediqms.db"

document_types: dict[str, str] = {
    "Quality Manual": "QM",
    "Policy": "POL",
    "Quality Objective": "OBJ",
    "Standard Operating Procedure": "SOP",
    "Work Instruction": "WI",
    "Form / Template": "FORM",
    "Specification": "SPEC",
    "Drawing": "DWG",
    "Bill of Materials": "BOM",
    "Software Documentation": "SW",
    "Risk Management": "RISK",
    "Instructions for Use": "IFU",
    "Labeling": "LBL",
    "Plan": "PLAN",
    "Protocol": "PROT",
    "Report": "REP",
    "External Standard": "EXT",
    "Controlled Template": "TMP",
}

status_types: list = [
    "DRAFT",
    "IN_REVIEW",
    "APPROVED_PENDING",
    "RELEASED",
    "SUPERSEDED",
    "OBSOLETE",
]

template_map: dict[str, str] = {
    "QM": "storage/templates/Template_QM.txt",  # Quality Manual
    "POL": "storage/templates/Template_POL.txt",  # Policy
    "OBJ": "storage/templates/Template_OBJ.txt",  # Objectives
    "SOP": "storage/templates/Template_SOP.txt",  # Standard Operating Procedure
    "WI": "storage/templates/Template_WI.txt",  # Work Instruction
    "FORM": "storage/templates/Template_FORM.txt",  # Forms
    "SPEC": "storage/templates/Template_SPEC.txt",  # Specifications
    "BOM": "storage/templates/Template_BOM.txt",  # Bill of Materials
    "SW": "storage/templates/Template_SW.txt",  # Software Docs
    "RISK": "storage/templates/Template_RISK.txt",  # Risk Management
    "IFU": "storage/templates/Template_IFU.txt",  # Instructions for Use
    "PLAN": "storage/templates/Template_PLAN.txt",  # Plans
    "PROT": "storage/templates/Template_PROT.txt",  # Protocols
    "REP": "storage/templates/Template_REP.txt",  # Reports
    "TMP": "storage/templates/Template_Meta.txt",  # Template para crear nuevas plantillas
    "DWG": "storage/mock_external/Mock_Drawing.pdf",  # Planos
    "LBL": "storage/mock_external/Mock_Label.jpg",  # Etiquetas
    "EXT": "storage/mock_external/Mock_Standard.pdf",  # Normas Externas
}
