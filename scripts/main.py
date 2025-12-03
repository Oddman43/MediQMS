# from document_control.doc_class import Document_Header, Document_Version
# import sqlite3

storage_root_path: str = "/storage"

document_types: dict = {
    "Quality Manual": "QM",  # Manual de Calidad
    "Policy": "POL",  # Políticas (Quality Policy, RA Policy)
    "Quality Objective": "OBJ",  # Objetivos de Calidad
    "Standard Operating Procedure": "SOP",  # Procedimientos
    "Work Instruction": "WI",  # Instrucciones de Trabajo (Paso a paso técnico)
    "Form / Template": "FORM",  # Plantillas vacías (Checklists, Forms)
    "Specification": "SPEC",  # Especificaciones (Producto, Material, Software)
    "Drawing": "DWG",  # Planos mecánicos, esquemas eléctricos
    "Bill of Materials": "BOM",  # Lista de Materiales (si se controla como doc)
    "Software Documentation": "SW",  # Documentación específica de ciclo de vida de SW
    "Risk Management": "RISK",  # Archivos de Gestión de Riesgos (o usar PLAN/REP)
    "Instructions for Use": "IFU",  # Manual de Usuario
    "Labeling": "LBL",  # Artes gráficas de etiquetas y cajas
    "Plan": "PLAN",  # PMS Plan, Clinical Eval Plan, Validation Plan
    "Protocol": "PROT",  # Protocolos de Validación (antes de ejecutar)
    "Report": "REP",  # Reportes Técnicos que se versionan (CER, PMCF)
    "External Standard": "EXT",  # Normas ISO, Regulaciones FDA, MDR
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

template_map: dict = {
    "SOP": "templates/SOP_Master.txt",
    "WI": "templates/WI_Master.txt",
    "POL": "templates/POL_Master.txt",
    "QM": "templates/QM_Master.txt",
    "FORM": "templates/FORM_Master.txt",
    "BOM": "tempaltes/BOM_Master.txt",
    "TMP": "templates/SEED_Blank.txt",
}
