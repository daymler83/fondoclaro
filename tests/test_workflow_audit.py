from copy import deepcopy
from pathlib import Path

import pytest

from fondoclaro.audit.importer import import_result
from fondoclaro.audit.package import ARTIFACTS, export_package, verify_package
from fondoclaro.cli import main
from fondoclaro.config import Blocked
from fondoclaro.serialization import read_json, write_json
from fondoclaro.workflow.distribution import send_package
from fondoclaro.workflow.pipeline import READINESS_BLOCKERS, run
from fondoclaro.workflow.registry import Registry
from fondoclaro.workflow.states import FLOW, State, check_transition


@pytest.fixture
def registry(tmp_path):
    return Registry(tmp_path)


@pytest.fixture
def sealed(registry):
    """Unit test of hash/state behavior; not a real report or pipeline bypass."""
    report_id=registry.create("C","2026-10")
    path=registry.directory(report_id)
    for name in ARTIFACTS:
        if name.endswith(".json"):
            write_json(path/name,{"kind":"SYNTHETIC_UNIT_TEST"})
        else:
            (path/name).write_bytes(b"SYNTHETIC_UNIT_TEST")
    (registry.root/"docs").mkdir()
    (registry.root/"docs"/"METODOLOGIA.md").write_text("Metodologia de prueba unitaria; no publicable.")
    registry.seal(report_id)
    for state in FLOW[1:FLOW.index(State.HUMAN_REVIEW_PENDING)+1]:
        registry.transition(report_id,state)
    return report_id


def external_result(registry,report_id,tmp_path,status="PASS",findings=None):
    package=verify_package(export_package(registry,report_id))
    result={k:package[k] for k in ("report_id","package_hash","data_version","code_version","run_id")}
    result.update(auditor={"nombre":"UNIT_TEST"},fecha="2026-11-08T18:00:00-03:00",status=status,findings=findings or [],limitaciones=["Prueba unitaria, no revisión real"])
    folder=tmp_path/"external_result"
    folder.mkdir(exist_ok=True)
    write_json(folder/"audit_results.json",result)
    (folder/"AUDIT_REPORT.md").write_text("SYNTHETIC_UNIT_TEST — no auditoría externa real")
    return folder,result


@pytest.mark.parametrize("old,new",list(zip(FLOW,FLOW[1:])))
def test_valid_state_transitions(old,new):
    check_transition(old,new)


@pytest.mark.parametrize("old,new",[(State.PENDING,State.APPROVED_FOR_PUBLICATION),(State.BLOCKED,State.PENDING),(State.MARKED_PUBLISHED,State.APPROVED_FOR_PUBLICATION),(State.SUPERSEDED,State.PENDING)])
def test_invalid_transitions(old,new):
    with pytest.raises(Blocked):
        check_transition(old,new)


def test_real_run_is_blocked_and_recorded(registry):
    outputs=run(registry.root,"C","2026-10",dev=True)
    assert len(outputs)==1
    assert outputs[0]["state"]==State.BLOCKED
    _,workflow=registry.get(outputs[0]["report_id"])
    assert workflow["events"][-1]["details"]["reasons"]==list(READINESS_BLOCKERS)
    assert not (registry.directory(outputs[0]["report_id"])/"infographic.png").exists()


def test_all_reports_have_independent_ids(registry):
    output=run(registry.root,"all","2026-10",dev=True)
    assert len(output)==6
    assert len({r["report_id"] for r in output})==6
    assert all(r["state"]==State.BLOCKED for r in output)


def test_run_without_git_blocks_even_without_dev(registry):
    output=run(registry.root,"C","latest")
    assert "DIRTY_OR_UNVERSIONED_CODE" in output[0]["reasons"][0]


def test_seal_immutable(registry,sealed):
    with pytest.raises(Blocked,match="IMMUTABLE"):
        registry.seal(sealed)


def test_approval_requires_flag_and_confirmation(registry,sealed):
    with pytest.raises(Blocked,match="EXTERNAL_AUDIT_MISSING"):
        registry.approve(sealed,sealed)
    with pytest.raises(Blocked,match="CONFIRMATION"):
        registry.approve(sealed,"wrong",without_external=True)
    registry.approve(sealed,sealed,without_external=True)
    assert registry.get(sealed)[1]["state"]==State.APPROVED_FOR_PUBLICATION
    approval=read_json(registry.directory(sealed)/"approval.json")
    assert approval["identity_authenticated"] is False


def test_dev_report_cannot_be_approved(registry,sealed):
    # Recreate a separate dev record; dev status is immutable in its sealed run.json.
    report_id=registry.create("A","2026-10",dev=True)
    source=registry.directory(sealed)
    dest=registry.directory(report_id)
    for name in ARTIFACTS:
        (dest/name).write_bytes((source/name).read_bytes())
    registry.seal(report_id)
    for state in FLOW[1:FLOW.index(State.HUMAN_REVIEW_PENDING)+1]:
        registry.transition(report_id,state)
    with pytest.raises(Blocked,match="DEV_REPORT"):
        registry.approve(report_id,report_id,without_external=True)


def test_no_publication_without_approval(registry,sealed):
    with pytest.raises(Blocked,match="REQUIRES_APPROVAL"):
        registry.mark_published(sealed,"difusión manual 2026-11-08")


def test_approved_report_changes_invalidate(registry,sealed):
    registry.approve(sealed,sealed,without_external=True)
    (registry.directory(sealed)/"infographic.png").write_bytes(b"modified")
    with pytest.raises(Blocked,match="CONTENT_CHANGED"):
        registry.mark_published(sealed,"difusión manual 2026-11-08")
    with pytest.raises(Blocked,match="CONTENT_CHANGED"):
        send_package(registry,"2026-10")


def test_publication_evidence_and_delivery_package(registry,sealed):
    registry.approve(sealed,sealed,without_external=True)
    directory,missing=send_package(registry,"2026-10")
    assert missing==["all","A","B","D","E"]
    assert (directory/"fondo_C.png").exists()
    assert not (directory/"fondo_A.png").exists()
    assert "256" in (directory/"LEEME.txt").read_text()
    registry.mark_published(sealed,"difusión manual 2026-11-08")
    assert registry.get(sealed)[1]["state"]==State.MARKED_PUBLISHED
    assert read_json(registry.directory(sealed)/"publication.json")["evidence"]=="difusión manual 2026-11-08"


def test_missing_approvals_not_in_delivery(registry,sealed):
    directory,missing=send_package(registry,"2026-10")
    assert len(missing)==6
    assert not list(directory.glob("*.png"))


def test_path_traversal_report_id(registry):
    with pytest.raises(Blocked,match="ID_INVALID"):
        registry.directory("../../secret")


def test_package_hashes_and_idempotence(registry,sealed):
    package=export_package(registry,sealed)
    manifest=verify_package(package)
    assert manifest["report_id"]==sealed
    assert set(ARTIFACTS).issubset(manifest["files"])
    assert "approval.json" not in manifest["files"]
    assert export_package(registry,sealed)==package
    (package/"financial_results.json").write_text("{}")
    with pytest.raises(Blocked,match="FILE_CHANGED"):
        verify_package(package)


def test_valid_audit_does_not_approve(registry,sealed,tmp_path):
    folder,_=external_result(registry,sealed,tmp_path)
    import_result(registry,sealed,folder)
    workflow=registry.get(sealed)[1]
    assert workflow["external_audit"]=="RESULT_IMPORTED_PASS"
    assert workflow["state"]==State.HUMAN_REVIEW_PENDING


@pytest.mark.parametrize("field",["report_id","package_hash","data_version","code_version","run_id"])
def test_audit_mismatched_binding(registry,sealed,tmp_path,field):
    folder,result=external_result(registry,sealed,tmp_path)
    result[field]="different"
    write_json(folder/"audit_results.json",result)
    with pytest.raises(Blocked,match="RESULT_INVALID"):
        import_result(registry,sealed,folder)
    assert registry.get(sealed)[1]["external_audit"]=="RESULT_INVALID"


def test_broken_schema_and_pass_without_package(registry,sealed,tmp_path):
    folder=tmp_path/"unbound"
    folder.mkdir()
    write_json(folder/"audit_results.json",{"status":"PASS"})
    (folder/"AUDIT_REPORT.md").write_text("Unbound")
    with pytest.raises(Blocked,match="RESULT_INVALID"):
        import_result(registry,sealed,folder)
    export_package(registry,sealed)
    with pytest.raises(Blocked,match="RESULT_INVALID"):
        import_result(registry,sealed,folder)


def test_high_findings_require_additional_confirmation(registry,sealed,tmp_path):
    findings=[dict(severidad="alta",categoria="datos",descripcion="Prueba",evidencia="Prueba unitaria",archivo="financial_results.json")]
    folder,_=external_result(registry,sealed,tmp_path,"FINDINGS",findings)
    import_result(registry,sealed,folder)
    with pytest.raises(Blocked,match="HIGH_FINDINGS"):
        registry.approve(sealed,sealed)
    registry.approve(sealed,sealed,findings_confirmation="ACEPTO HALLAZGOS ALTOS")


def test_inconclusive_is_visible_and_requires_optout(registry,sealed,tmp_path):
    folder,_=external_result(registry,sealed,tmp_path,"INCONCLUSIVE")
    import_result(registry,sealed,folder)
    with pytest.raises(Blocked,match="EXTERNAL_AUDIT_MISSING"):
        registry.approve(sealed,sealed)


def test_cli_blocked_run_and_status(registry,capsys):
    assert main(["--root",str(registry.root),"run","--fund","C","--period","2026-10","--dev"])==2
    import json
    data=json.loads(capsys.readouterr().out)
    assert main(["--root",str(registry.root),"status","--report-id",data[0]["report_id"]])==0
    assert "BLOCKED" in capsys.readouterr().out


def test_fetch_failure_is_offline_blocking(monkeypatch,registry):
    from fondoclaro.data import collectors
    def fail(*a,**kw):
        raise OSError("unit test network unavailable")
    monkeypatch.setattr(collectors,"urlopen",fail)
    with pytest.raises(Blocked,match="FETCH_FAILED"):
        collectors.fetch(registry.root,"bcch")
