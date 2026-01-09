from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

storage_root_path: str = str(BASE_DIR / "storage")
db_path: str = str(BASE_DIR / "data" / "database" / "mediqms.db")
os.makedirs(os.path.dirname(db_path), exist_ok=True)
os.makedirs(storage_root_path, exist_ok=True)

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
    "TRAINING",
    "RELEASED",
    "SUPERSEDED",
    "OBSOLETE",
]

training_types: list = ["ASIGNED", "FAILED", "COMPLETED", "OVERDUE"]

template_map: dict[str, str] = {
    "QM": str(BASE_DIR / "storage/templates/Template_QM.txt"),
    "POL": str(BASE_DIR / "storage/templates/Template_POL.txt"),
    "OBJ": str(BASE_DIR / "storage/templates/Template_OBJ.txt"),
    "SOP": str(BASE_DIR / "storage/templates/Template_SOP.txt"),
    "WI": str(BASE_DIR / "storage/templates/Template_WI.txt"),
    "FORM": str(BASE_DIR / "storage/templates/Template_FORM.txt"),
    "SPEC": str(BASE_DIR / "storage/templates/Template_SPEC.txt"),
    "BOM": str(BASE_DIR / "storage/templates/Template_BOM.txt"),
    "SW": str(BASE_DIR / "storage/templates/Template_SW.txt"),
    "RISK": str(BASE_DIR / "storage/templates/Template_RISK.txt"),
    "IFU": str(BASE_DIR / "storage/templates/Template_IFU.txt"),
    "PLAN": str(BASE_DIR / "storage/templates/Template_PLAN.txt"),
    "PROT": str(BASE_DIR / "storage/templates/Template_PROT.txt"),
    "REP": str(BASE_DIR / "storage/templates/Template_REP.txt"),
    "TMP": str(BASE_DIR / "storage/templates/Template_Meta.txt"),
    "DWG": str(BASE_DIR / "storage/mock_external/Mock_Drawing.pdf"),
    "LBL": str(BASE_DIR / "storage/mock_external/Mock_Label.jpg"),
    "EXT": str(BASE_DIR / "storage/mock_external/Mock_Standard.pdf"),
}
