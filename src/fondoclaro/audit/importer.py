import shutil
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from ..config import Blocked
from ..serialization import read_json, write_json
from .package import verify_package
from .schemas import SCHEMA


def import_result(registry, report_id, path: Path):
    run, state = registry.get(report_id)
    try:
        registry.integrity(report_id)
        package = verify_package(registry.root/"audit_packages"/report_id)
        result = read_json(path/"audit_results.json")
        Draft202012Validator(SCHEMA, format_checker=FormatChecker()).validate(result)
        for key in ("report_id", "package_hash", "data_version", "code_version", "run_id"):
            if result[key] != package[key]:
                raise Blocked("AUDIT_BINDING_MISMATCH: "+key)
        if not (path/"AUDIT_REPORT.md").read_text().strip():
            raise Blocked("AUDIT_REPORT_EMPTY")
        if result["status"] == "PASS" and result["findings"]:
            raise Blocked("AUDIT_PASS_WITH_FINDINGS")
    except (ValueError, OSError, ValidationError) as exc:
        state["external_audit"] = "RESULT_INVALID"
        state["audit_error"] = str(exc)
        write_json(registry.directory(report_id)/"workflow.json", state)
        raise Blocked("RESULT_INVALID: "+str(exc)) from exc
    from uuid import uuid4
    imported = registry.root/"audit_results"/report_id/uuid4().hex
    imported.mkdir(parents=True)
    for name in ("audit_results.json", "AUDIT_REPORT.md"):
        shutil.copyfile(path/name, imported/name)
    state["external_audit"] = "RESULT_IMPORTED_PASS" if result["status"] == "PASS" else "RESULT_IMPORTED_FINDINGS"
    state["audit_status"] = result["status"]
    state["high_findings"] = [f for f in result["findings"] if f["severidad"] == "alta"]
    state["audit_import_path"] = str(imported.relative_to(registry.root))
    write_json(registry.directory(report_id)/"workflow.json", state)
    return result
