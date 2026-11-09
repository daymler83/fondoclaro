import shutil
from pathlib import Path

from ..config import Blocked
from ..content.text_checks import PERSONAL
from ..serialization import canonical, digest, file_hash, read_json, write_json
from .schemas import SCHEMA

ARTIFACTS = ("source_manifest.json", "financial_results.json", "calculations.json", "validation_results.json", "render_manifest.json", "infographic.png", "whatsapp_text.txt")


def export_package(registry, report_id):
    run, state = registry.get(report_id)
    integrity = registry.integrity(report_id)
    directory = registry.root/"audit_packages"/report_id
    if directory.exists():
        verify_package(directory)
        return directory
    source = registry.directory(report_id)
    for name in ARTIFACTS:
        if not (source/name).is_file():
            raise Blocked("AUDIT_MISSING_ARTIFACT: "+name)
    methodology = registry.root/"docs"/"METODOLOGIA.md"
    if not methodology.is_file():
        raise Blocked("AUDIT_METHODOLOGY_MISSING")
    directory.mkdir(parents=True)
    try:
        for name in ARTIFACTS:
            data = (source/name).read_bytes()
            if name.endswith((".json", ".txt")) and PERSONAL.search(data.decode()):
                raise Blocked("PERSONAL_DATA_IN_EXPORT")
            (directory/name).write_bytes(data)
        shutil.copyfile(methodology, directory/"methodology.md")
        write_json(directory/"audit_results.schema.json", SCHEMA)
        (directory/"audit_instructions.md").write_text("Revisar fuentes, fórmulas, cifras, texto y PNG. Devolver audit_results.json según audit_results.schema.json y AUDIT_REPORT.md. Copiar exactamente report_id, package_hash, data_version, code_version y run_id de package_manifest.json. PASS no aprueba publicación. Esto da trazabilidad, no prueba de revisión.\n")
        files = {p.name: file_hash(p) for p in directory.iterdir() if p.is_file()}
        manifest = dict(report_id=report_id, run_id=run["run_id"], code_version=run["code_version"]["git_sha"],
                        data_version=file_hash(source/"source_manifest.json"), content_hash=integrity["content_hash"], files=files)
        manifest["package_hash"] = digest(canonical(manifest))
        write_json(directory/"package_manifest.json", manifest)
    except Exception:
        shutil.rmtree(directory)
        raise
    with registry.lock():
        run, state = registry.get(report_id)
        state["external_audit"] = "PACKAGE_EXPORTED"
        write_json(source/"workflow.json", state)
    return directory


def verify_package(directory):
    manifest = read_json(directory/"package_manifest.json")
    expected = manifest.pop("package_hash")
    if digest(canonical(manifest)) != expected:
        raise Blocked("PACKAGE_HASH_MISMATCH")
    for name, hashed in manifest["files"].items():
        if name != Path(name).name or file_hash(directory/name) != hashed:
            raise Blocked("PACKAGE_FILE_CHANGED")
    manifest["package_hash"] = expected
    return manifest
