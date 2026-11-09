SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object", "additionalProperties": False,
    "required": ["report_id", "package_hash", "data_version", "code_version", "run_id", "auditor", "fecha", "status", "findings", "limitaciones"],
    "properties": {
        **{key: {"type": "string", "minLength": 1} for key in ("report_id", "package_hash", "data_version", "code_version", "run_id")},
        "auditor": {"type": "object", "required": ["nombre"], "additionalProperties": False, "properties": {"nombre": {"type": "string", "minLength": 1}, "version": {"type": ["string", "null"]}}},
        "fecha": {"type": "string", "format": "date-time"},
        "status": {"enum": ["PASS", "FINDINGS", "INCONCLUSIVE"]},
        "findings": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["severidad", "categoria", "descripcion", "evidencia", "archivo"],
            "properties": {"severidad": {"enum": ["alta", "media", "baja"]}, **{key: {"type": "string", "minLength": 1} for key in ("categoria", "descripcion", "evidencia", "archivo")}}}},
        "limitaciones": {"type": "array", "items": {"type": "string"}},
    },
}
