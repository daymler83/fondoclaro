import argparse
import json
import sys
import webbrowser
from pathlib import Path

from .audit.importer import import_result
from .audit.package import export_package
from .config import Blocked
from .content.text_checks import validate_manifest
from .data.collectors import fetch
from .render.render import rasterize
from .render.visual_checks import validate_png, validate_svg
from .serialization import canonical, read_json
from .workflow.distribution import send_package
from .workflow.pipeline import run
from .workflow.registry import Registry


def validate_report(registry, report_id):
    inventory = registry.integrity(report_id)
    path = registry.directory(report_id)
    m = read_json(path/"render_manifest.json")
    svg = (path/"infographic.svg").read_text()
    result = {**validate_manifest(m), **validate_svg(svg, m), **validate_png((path/"infographic.png").read_bytes())}
    if rasterize(svg) != (path/"infographic.png").read_bytes():
        raise Blocked("PNG_DOES_NOT_MATCH_VALIDATED_SVG")
    return dict(content_hash=inventory["content_hash"], validations=result)


def parser():
    p = argparse.ArgumentParser(prog="fondoclaro", description="Informes determinísticos; nunca publica. Ver docs/BLOQUEOS.md.")
    p.add_argument("--root", type=Path, default=Path.cwd())
    subs = p.add_subparsers(dest="command", required=True)
    command = subs.add_parser("fetch")
    command.add_argument("--source", choices=("sp", "bcch", "all"), default="all")
    command.add_argument("--year", type=int)
    command = subs.add_parser("run")
    command.add_argument("--fund", choices=(*"ABCDE", "all"), required=True)
    command.add_argument("--period", default="latest")
    command.add_argument("--dev", action="store_true")
    for name in ("status", "validate", "export", "import-audit", "approve", "mark-published"):
        command = subs.add_parser(name)
        command.add_argument("--report-id", required=True)
        if name == "import-audit":
            command.add_argument("--path", type=Path, required=True)
        if name == "approve":
            command.add_argument("--sin-auditoria-externa", action="store_true")
        if name == "mark-published":
            command.add_argument("--url", required=True)
    command = subs.add_parser("send-package")
    command.add_argument("--period", required=True)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    root = args.root.resolve()
    try:
        registry = Registry(root)
        if args.command == "run":
            reports = run(root, args.fund, args.period, dev=args.dev)
            print(canonical(reports).decode())
            return 2 if any(r["state"] == "BLOCKED" for r in reports) else 0
        if args.command == "fetch":
            result = dict(paths=[str(p) for p in fetch(root, args.source, args.year)], warning="Capturas crudas; no habilitan informes sin prueba dorada.")
        elif args.command == "status":
            record, workflow = registry.get(args.report_id)
            result = dict(run=record, workflow=workflow)
        elif args.command == "validate":
            result = validate_report(registry, args.report_id)
        elif args.command == "export":
            result = dict(path=str(export_package(registry, args.report_id)))
        elif args.command == "import-audit":
            result = import_result(registry, args.report_id, args.path)
        elif args.command == "approve":
            result = validate_report(registry, args.report_id)
            record, workflow = registry.get(args.report_id)
            print(json.dumps(dict(validations=result, workflow=workflow, manifest=read_json(registry.directory(args.report_id)/"render_manifest.json")), ensure_ascii=False, indent=2))
            if not webbrowser.open((registry.directory(args.report_id)/"infographic.png").as_uri()):
                raise Blocked("VISUAL_REVIEW_UNAVAILABLE: configure un visor para mostrar el PNG antes de aprobar")
            print("Identidad del SO/git no autenticada. Revise el PNG abierto y escriba el report_id.")
            confirmation = input("report_id: ").strip()
            extra = None
            if workflow.get("high_findings"):
                print("\033[31mHallazgos altos: "+json.dumps(workflow["high_findings"], ensure_ascii=False)+"\033[0m")
                extra = input('Escriba ACEPTO HALLAZGOS ALTOS: ').strip()
            registry.approve(args.report_id, confirmation, without_external=args.sin_auditoria_externa, findings_confirmation=extra)
            result = dict(state="APPROVED_FOR_PUBLICATION")
        elif args.command == "mark-published":
            registry.mark_published(args.report_id, args.url)
            result = dict(state="MARKED_PUBLISHED", note="Solo se registró la evidencia; no se envió nada.")
        elif args.command == "send-package":
            directory, missing = send_package(registry, args.period)
            result = dict(path=str(directory), missing=missing)
        print(canonical(result).decode())
        return 0
    except (Blocked, OSError, KeyError, EOFError) as exc:
        print(json.dumps(dict(state="BLOCKED", reason=str(exc)), ensure_ascii=False), file=sys.stderr)
        return 2
