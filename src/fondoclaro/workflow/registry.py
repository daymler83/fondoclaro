import getpass
import re
import subprocess
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import fcntl

from ..config import Blocked, now
from ..serialization import canonical, digest, file_hash, read_json, write_json
from .states import State, check_transition


def code_version(root: Path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL, text=True).strip()
    try:
        return dict(git_sha=git("rev-parse", "HEAD"), dirty=bool(git("status", "--porcelain")))
    except (OSError, subprocess.CalledProcessError):
        return dict(git_sha="UNVERSIONED", dirty=True)


class Registry:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.reports = self.root / "reports"
        self.reports.mkdir(parents=True, exist_ok=True)

    def directory(self, report_id):
        if not re.fullmatch(r"[0-9a-f]{32}", report_id):
            raise Blocked("REPORT_ID_INVALID")
        return self.reports / report_id

    @contextmanager
    def lock(self):
        with (self.reports / ".registry.lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def create(self, fund, period, *, run_id=None, dev=False, supersedes=None):
        report_id = uuid4().hex
        path = self.directory(report_id)
        path.mkdir()
        from importlib.metadata import version
        data = dict(report_id=report_id, run_id=run_id or uuid4().hex, fund=fund, period=period,
                    created_at=now(), code_version=code_version(self.root), dev=dev,
                    supersedes=supersedes, dependencies={name: version(name) for name in ("CairoSVG", "Pillow", "fonttools", "Jinja2", "jsonschema")})
        write_json(path / "run.json", data)
        write_json(path / "workflow.json", dict(state=State.PENDING, external_audit="NOT_REQUESTED", events=[], warnings=[]))
        return report_id

    def get(self, report_id):
        path = self.directory(report_id)
        try:
            return read_json(path/"run.json"), read_json(path/"workflow.json")
        except FileNotFoundError as exc:
            raise Blocked("REPORT_NOT_FOUND") from exc

    def transition(self, report_id, state, **details):
        with self.lock():
            run, workflow = self.get(report_id)
            check_transition(workflow["state"], state)
            hashes = {p.name: file_hash(p) for p in self.directory(report_id).iterdir() if p.is_file() and p.name != "workflow.json"}
            event = dict(timestamp=now(), previous_state=workflow["state"], state=state, code_version=run["code_version"],
                         input_hash=digest(canonical(hashes)), output_hash=digest(canonical(details)), details=details)
            workflow["events"].append(event)
            workflow["state"] = state
            write_json(self.directory(report_id)/"workflow.json", workflow)

    def integrity(self, report_id):
        directory = self.directory(report_id)
        inventory = read_json(directory/"integrity.json")
        for name, expected in inventory["files"].items():
            if Path(name).name != name or file_hash(directory/name) != expected:
                raise Blocked(f"CONTENT_CHANGED: {name}; crear un informe nuevo")
        actual = digest(canonical(inventory["files"]))
        if actual != inventory["content_hash"]:
            raise Blocked("CONTENT_HASH_MISMATCH")
        return inventory

    def seal(self, report_id):
        directory = self.directory(report_id)
        if (directory/"integrity.json").exists():
            raise Blocked("REPORT_IMMUTABLE")
        files = {p.name: file_hash(p) for p in directory.iterdir() if p.is_file() and p.name not in ("workflow.json", "integrity.json", "approval.json", "publication.json")}
        for required in ("run.json", "render_manifest.json", "whatsapp_text.txt", "infographic.png", "source_manifest.json"):
            if required not in files:
                raise Blocked(f"MISSING_ARTIFACT: {required}")
        write_json(directory/"integrity.json", dict(files=files, content_hash=digest(canonical(files))))
        return self.integrity(report_id)

    def approve(self, report_id, confirmation, *, without_external=False, findings_confirmation=None):
        with self.lock():
            run, state = self.get(report_id)
            inventory = self.integrity(report_id)
            if run["dev"]:
                raise Blocked("DEV_REPORT_NOT_APPROVABLE")
            if state["state"] != State.HUMAN_REVIEW_PENDING or confirmation != report_id:
                raise Blocked("APPROVAL_CONFIRMATION_OR_STATE_INVALID")
            if (state["external_audit"] not in ("RESULT_IMPORTED_PASS", "RESULT_IMPORTED_FINDINGS") or state.get("audit_status") == "INCONCLUSIVE") and not without_external:
                raise Blocked("EXTERNAL_AUDIT_MISSING: requiere --sin-auditoria-externa")
            if state.get("high_findings") and findings_confirmation != "ACEPTO HALLAZGOS ALTOS":
                raise Blocked("HIGH_FINDINGS_CONFIRMATION_REQUIRED")
            if (self.directory(report_id)/"approval.json").exists():
                raise Blocked("ALREADY_APPROVED")
            try:
                git_name = subprocess.check_output(["git", "-C", str(self.root), "config", "user.name"], text=True, stderr=subprocess.DEVNULL).strip()
            except (OSError, subprocess.CalledProcessError):
                git_name = None
            write_json(self.directory(report_id)/"approval.json", dict(content_hash=inventory["content_hash"], timestamp=now(),
                       os_user=getpass.getuser(), git_user_name=git_name, identity_authenticated=False, without_external=without_external))
        self.transition(report_id, State.APPROVED_FOR_PUBLICATION)
        with self.lock():
            path = self.reports/"approved_index.json"
            index = read_json(path) if path.exists() else {}
            key = run["period"]+"/"+run["fund"]
            index[key] = dict(report_id=report_id, png_path=str((self.directory(report_id)/"infographic.png").relative_to(self.root)),
                             png_hash=file_hash(self.directory(report_id)/"infographic.png"), content_hash=inventory["content_hash"],
                             whatsapp_text=(self.directory(report_id)/"whatsapp_text.txt").read_text())
            write_json(path, index)

    def mark_published(self, report_id, evidence):
        run, state = self.get(report_id)
        inventory = self.integrity(report_id)
        if state["state"] != State.APPROVED_FOR_PUBLICATION:
            raise Blocked("PUBLICATION_REQUIRES_APPROVAL")
        if not evidence.strip():
            raise Blocked("PUBLICATION_EVIDENCE_REQUIRED")
        if read_json(self.directory(report_id)/"approval.json")["content_hash"] != inventory["content_hash"]:
            raise Blocked("APPROVAL_HASH_MISMATCH")
        write_json(self.directory(report_id)/"publication.json", dict(timestamp=now(), evidence=evidence))
        self.transition(report_id, State.MARKED_PUBLISHED)
