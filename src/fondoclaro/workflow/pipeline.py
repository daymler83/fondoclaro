"""Pipeline oficial determinístico. Genera, verifica y deja revisión humana pendiente."""
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from html import escape

from ..audit.package import export_package
from ..config import Blocked,FUNDS,ZONE,period_end,shift_month
from ..content.manifest import build_manifest
from ..content.summary import build_summary_manifest,validate_summary_manifest
from ..content.text_checks import validate_manifest
from ..data.dataset import load_official_history
from ..finance.engine import calculate_system
from ..finance.golden import evaluate_history,optional_annualized_check,TOLERANCE_PP
from ..finance.independent import IndependentSystem,compare
from ..finance.system import month_snapshots
from ..render.render import render_svg,render_summary_svg,rasterize
from ..render.visual_checks import validate_svg,validate_summary_svg,validate_png
from ..serialization import digest,canonical,write_json,read_json
from .registry import Registry
from .states import State

READINESS_BLOCKERS=("OFFICIAL_HISTORY_MISSING: falta un manifiesto oficial con hashes verificables",)


def summary_inputs(registry,references):
    items=[]
    for ref in references:
        record,state=registry.get(ref["report_id"])
        inventory=registry.integrity(ref["report_id"])
        if inventory["content_hash"]!=ref["content_hash"]:raise Blocked("SUMMARY_REFERENCE_HASH_MISMATCH")
        items.append(dict(report_id=ref["report_id"],content_hash=ref["content_hash"],state=state["state"],
                          manifest=read_json(registry.directory(ref["report_id"])/"render_manifest.json")))
    return items


def run(root,fund,period,*,dev=False):
    root=Path(root).resolve();registry=Registry(root);run_id=uuid4().hex
    if fund not in (*FUNDS,"all"):raise Blocked("FUND_INVALID")
    if period!="latest" and period_end(period)>=datetime.now(ZONE).date().replace(day=1):raise Blocked("PERIOD_NOT_CLOSED")
    manifest_path=root/"raw_data/history_2002_manifest.json"
    if not manifest_path.exists():manifest_path=root/"raw_data/history_manifest.json"
    dataset=None;golden=None;annual=None;preflight=[]
    if not manifest_path.exists():preflight=list(READINESS_BLOCKERS)
    else:
        try:
            dataset=load_official_history(root,manifest_path)
            golden=evaluate_history(root,manifest_path)
            if golden["status"]!="PASS":preflight=[f"GOLDEN_FAILED: {golden['failed']} fallos, máximo {golden['max_difference_pp']} pp"]
            else:
                annual=optional_annualized_check(dataset)
                golden["annualized_status"]=f"{annual['status']}: {annual['afp_comparisons']} comparaciones AFP; {annual['system_comparisons']} promedios completos sistema; {annual['partial_system_diagnostics']} diagnósticos parciales; historia desde 2002"
                golden["annualized_results"]=annual
        except (Blocked,OSError,ValueError) as exc:preflight=[str(exc)]
    cutoff=period_end(period) if period!="latest" else dataset.cutoff if dataset else None
    if cutoff and dataset and cutoff>dataset.cutoff:preflight.append("CUTOFF_NOT_CONFIRMED")
    resolved_period=cutoff.strftime("%Y-%m") if cutoff else period
    reports=[];individuals=[]

    def create(selected):
        rid=registry.create(selected,resolved_period,run_id=run_id,dev=dev)
        path=registry.directory(rid)
        record,state=registry.get(rid)
        reasons=list(preflight)
        if record["code_version"]["dirty"] and not dev:reasons.insert(0,"DIRTY_OR_UNVERSIONED_CODE: requiere commit limpio o --dev")
        record["parameters"]=dict(fund=selected,period=period,resolved_period=resolved_period,dev=dev)
        record["cutoff_date"]=str(cutoff) if cutoff else None
        if dataset:
            record["data_version"]=dataset.data_version
            record["source_manifest_path"]=str(manifest_path.relative_to(root))
        write_json(path/"run.json",record)
        return rid,path,reasons

    def block(rid,reasons,stage):
        registry.transition(rid,State.BLOCKED,stage=stage,reasons=reasons)
        return dict(report_id=rid,fund=registry.get(rid)[0]["fund"],state=State.BLOCKED,reasons=reasons)

    def finish(rid,path,m,svg,validations,financial,calculations,sources):
        write_json(path/"render_manifest.json",m)
        (path/"whatsapp_text.txt").write_text(m["whatsapp_text"])
        registry.transition(rid,State.CONTENT_GENERATED)
        (path/"infographic.svg").write_text(svg)
        png=rasterize(svg)
        (path/"infographic.png").write_bytes(png)
        registry.transition(rid,State.VISUAL_GENERATED)
        validations.update(validate_summary_svg(svg,m) if m.get("kind")=="SUMMARY" else validate_svg(svg,m))
        validations.update(validate_png(png))
        validations["raster_spaces"]="DEFERRED_BY_USER_2026-11-08"
        validations["annualized_consultative"]=annual["status"]
        write_json(path/"validation_results.json",validations)
        write_json(path/"financial_results.json",financial)
        write_json(path/"calculations.json",calculations)
        write_json(path/"source_manifest.json",sources)
        write_json(path/"golden_validation.json",golden)
        registry.transition(rid,State.VISUALLY_VERIFIED)
        inventory=registry.seal(rid)
        export_package(registry,rid)
        registry.transition(rid,State.HUMAN_REVIEW_PENDING)
        return dict(report_id=rid,fund=m["fund"],period=resolved_period,state=State.HUMAN_REVIEW_PENDING,
                    png=str((path/"infographic.png").relative_to(root)),content_hash=inventory["content_hash"])

    for selected in FUNDS if fund=="all" else (fund,):
        rid,path,reasons=create(selected)
        if reasons:
            reports.append(block(rid,reasons,"PREFLIGHT"));continue
        try:
            sources=dict(data_version=dataset.data_version,cutoff_date=str(cutoff),kind="OFFICIAL_RAW",
                         manifest_path=str(manifest_path.relative_to(root)),files=dataset.manifest["entries"]+dataset.manifest["landing_pages"])
            registry.transition(rid,State.DATA_COLLECTED)
            snapshots=month_snapshots(dataset.quotas[selected],cutoff)
            registry.transition(rid,State.DATA_VALIDATED)
            result=calculate_system(snapshots,dataset.uf,selected,cutoff)
            registry.transition(rid,State.CALCULATED)
            independent=IndependentSystem(dataset.csv_paths[selected],dataset.uf_files)
            checks=[]
            for n,metric in result.metrics.items():
                if metric.real is None:continue
                other=independent.return_for(shift_month(cutoff,-n),cutoff)
                compare(metric.real,other["real"])
                details=result.calculation_details[str(n)]
                if details["included_afps"]!=other["included_afps"] or details["excluded_afps"]!=other["excluded_afps"]:
                    raise Blocked("INDEPENDENT_AFP_SET_MISMATCH")
                checks.append(dict(horizon=n,calculated=metric.real,independent=other["real"]))
            begin=result.chart_values[0][0]
            for end,value in result.chart_values[1:]:
                other=independent.return_for(begin,end)
                from ..config import BASE
                compare(value/BASE-1,other["real"])
            current=dataset.published.get(resolved_period)
            warnings=[]
            if current:
                for n in (1,12):
                    metric=result.metrics[n]
                    if metric.real is not None and abs(metric.real-current[selected]["rows"]["SISTEMA"][f"r_{n}m"])*100>TOLERANCE_PP:
                        raise Blocked("SP_CUTOFF_MISMATCH")
            else:warnings.append("SP_NO_PUBLICADO_AUN")
            record,state=registry.get(rid);state["warnings"]=warnings+[annual["status"]]
            write_json(path/"workflow.json",state)
            registry.transition(rid,State.NUMERICALLY_VERIFIED)
            m=build_manifest(result)
            validations={**validate_manifest(m),"golden":"PASS","independent":"PASS","cutoff_sp":"PASS" if current else "SP_NO_PUBLICADO_AUN"}
            calculations=dict(method=result.method,details=result.calculation_details,independent_checks=checks,
                              independent_curve_points=len(result.chart_values),independent_relative_tolerance="1e-9")
            report=finish(rid,path,m,render_svg(m),validations,asdict(result),calculations,sources)
            reports.append(report)
            individuals.append(dict(report_id=rid,state=report["state"],content_hash=report["content_hash"],manifest=m))
        except (Blocked,OSError,ValueError,ArithmeticError) as exc:
            reports.append(block(rid,[str(exc)],registry.get(rid)[1]["state"]))
    if fund=="all":
        rid,path,reasons=create("all")
        if reasons or len(individuals)!=5:
            reports.append(block(rid,reasons or ["INDIVIDUAL_REPORTS_NOT_VISUALLY_VERIFIED"],"SUMMARY"))
        else:
            try:
                for state in (State.DATA_COLLECTED,State.DATA_VALIDATED,State.CALCULATED,State.NUMERICALLY_VERIFIED):registry.transition(rid,state)
                m=build_summary_manifest(individuals)
                validations=validate_summary_manifest(m,individuals)
                validations.update(golden="PASS",independent="PASS",individual_references="PASS")
                sources=dict(data_version=dataset.data_version,cutoff_date=str(cutoff),files=dataset.manifest["entries"],references=m["references"])
                reports.append(finish(rid,path,m,render_summary_svg(m),validations,dict(rows=m["rows"]),dict(references=m["references"]),sources))
            except (Blocked,OSError,ValueError,ArithmeticError) as exc:reports.append(block(rid,[str(exc)],"SUMMARY"))
        review=root/"reports"/("review_"+run_id+".html")
        content=['<!doctype html><html lang="es"><meta charset="utf-8"><title>FondoClaro · revisión '+escape(resolved_period)+'</title><h1>Revisión humana pendiente · '+escape(resolved_period)+'</h1>']
        for report in reports:
            content.append('<article><h2>'+escape(report['fund'])+' · '+escape(report['state'])+'</h2><p>'+escape(report['report_id'])+'</p>')
            if report.get("png"):content.append('<a href="'+escape(report['report_id'])+'/infographic.png"><img width="432" src="'+escape(report['report_id'])+'/infographic.png"></a>')
            else:content.append('<p>'+escape(str(report.get('reasons')))+'</p>')
            content.append('</article>')
        review.write_text(''.join(content))
        write_json(root/"reports"/("review_"+run_id+".json"),reports)
    return reports
