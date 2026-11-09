"""Contraste financiero real. Un FAIL no autoriza cambiar datos o metodología."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

from ..config import Blocked, FUNDS, period_end
from ..data.loaders import load_sii_uf, load_sp_csv, load_sp_published
from ..serialization import file_hash, read_json, write_json
from .engine import calculate_system
from .system import month_snapshots, period_components

TOLERANCE_PP = Decimal("0.01")


def evaluate_history(root: Path, manifest_path: Path | None = None):
    root = root.resolve()
    manifest_path = manifest_path or root/"raw_data"/"history_manifest.json"
    manifest = read_json(manifest_path)
    if manifest["errors"]:
        raise Blocked("HISTORY_INCOMPLETE")
    entries = manifest["entries"]
    for e in entries + manifest.get("landing_pages",[]):
        p = (root/e["path"]).resolve()
        if not p.is_relative_to(root) or file_hash(p) != e["sha256"]:
            raise Blocked("HISTORY_RAW_HASH_MISMATCH")
    uf, published, quotas = {}, {}, {}
    for e in entries:
        p = root/e["path"]
        if e["source"] == "sii_uf":
            for d,value in load_sii_uf(p,e["year"]).items():
                if d in uf:
                    raise Blocked("HISTORY_DUPLICATE_UF")
                uf[d] = value
        elif e["source"] == "sp_quota_history":
            if e["fund"] in quotas:
                raise Blocked("HISTORY_DUPLICATE_FUND")
            quotas[e["fund"]] = load_sp_csv(p)
        elif e["source"] == "sp_published_returns":
            if e["period"] in published:
                raise Blocked("HISTORY_DUPLICATE_PERIOD")
            published[e["period"]] = load_sp_published(p,e["period"])
    if set(quotas) != set(FUNDS) or len(published) < 24:
        raise Blocked("GOLDEN_COVERAGE_INSUFFICIENT")
    cutoff = date.fromisoformat(manifest["cutoff"])
    comparisons, per_fund, data_counts = [], {}, {}
    # Fórmulas y tolerancia fijadas antes de ejecutar el primer contraste.
    with localcontext() as ctx:
        ctx.prec = 40
        for fund in FUNDS:
            snapshots = month_snapshots(quotas[fund],cutoff)
            data_counts[fund] = dict(raw_observations=len(quotas[fund]),monthly_points=len(snapshots))
            for period, reference in sorted(published.items()):
                end = period_end(period)
                actual = calculate_system(snapshots,uf,fund,end,include_chart=False)
                row = reference[fund]["rows"]["SISTEMA"]
                for horizon in (1,12):
                    metric = f"r_{horizon}m"
                    expected = row[metric]
                    value = actual.metrics[horizon].real
                    if expected is None or value is None:
                        raise Blocked("GOLDEN_COMPARISON_DATA_MISSING")
                    delta = abs(value-expected)*100
                    direct = value
                    comparisons.append(dict(fund=fund,period=period,metric=metric,calculated=value,published=expected,
                        difference_pp=delta,passed=delta<=TOLERANCE_PP,
                        official_period_weighting=direct,official_period_difference_pp=abs(direct-expected)*100))
            own = [r for r in comparisons if r["fund"]==fund]
            per_fund[fund] = dict(compared=len(own),failed=sum(not r["passed"] for r in own),max_difference_pp=max(r["difference_pp"] for r in own))
    worst = max(comparisons,key=lambda r:r["difference_pp"])
    by_metric = {metric: dict(compared=sum(r["metric"]==metric for r in comparisons),
                             failed=sum(r["metric"]==metric and not r["passed"] for r in comparisons),
                             max_difference_pp=max(r["difference_pp"] for r in comparisons if r["metric"]==metric)) for metric in ("r_1m","r_12m")}
    report = dict(status="FAIL" if any(not r["passed"] for r in comparisons) else "PASS",method="SP_HORIZON_WEIGHTED_V1",
                  tolerance_pp=TOLERANCE_PP,months=sorted(published),funds=list(FUNDS),compared=len(comparisons),
                  failed=sum(not r["passed"] for r in comparisons),max_difference_pp=worst["difference_pp"],worst_case=worst,
                  by_fund=per_fund,by_metric=by_metric,data_counts=data_counts,uf_daily_points=len(uf),
                  annualized_status="PENDING_OPTIONAL_CHECK: insumos 2002 disponibles; no bloqueante en el ciclo autorizado",
                  manifest_sha256=file_hash(manifest_path),comparisons=comparisons)
    return report


def save_evaluation(root: Path):
    from ..data.dataset import load_official_history
    path=root/"raw_data/history_2002_manifest.json"
    if not path.exists():path=root/"raw_data/history_manifest.json"
    report = evaluate_history(root,path)
    if report["status"]=="PASS":
        annual=optional_annualized_check(load_official_history(root,path))
        report["annualized_results"]=annual
        report["annualized_status"]=f"{annual['status']}: {annual['afp_comparisons']} comparaciones AFP; {annual['system_comparisons']} promedios completos sistema; historia desde 2002"
    target = root/"reports"/"golden_validation"
    target.mkdir(parents=True,exist_ok=True)
    write_json(target/"result.json",report)
    return report


def optional_annualized_check(history):
    """Contraste consultivo: nunca oculta falta de historia o sucesiones AFP."""
    systems=[];afps=[];unavailable=[]
    start=date(2002,9,26)
    for fund in FUNDS:
        daily={}
        for r in history.quotas[fund]:
            if r.confirmed:daily.setdefault(r.date,{})[r.afp]=r
        snapshots=month_snapshots(history.quotas[fund],history.cutoff)
        if start in daily:snapshots[start]=daily[start]
        for period,published in sorted(history.published.items()):
            expected=published[fund]["rows"]
            try:
                part=period_components(snapshots,history.uf,start,period_end(period),include_annualized=True)
            except Blocked as exc:
                unavailable.append(dict(fund=fund,period=period,horizon="SINCE_2002",reason=str(exc)))
                continue
            missing=[a for a,r in expected.items() if a!="SISTEMA" and r.get("annualized_since_2002") is not None and a not in part["included_afps"]]
            delta=abs(part["annualized"]-expected["SISTEMA"]["annualized_since_2002"])*100
            systems.append(dict(fund=fund,period=period,calculated=part["annualized"],published=expected["SISTEMA"]["annualized_since_2002"],difference_pp=delta,
                                fully_comparable=not missing,missing_official_afps=missing,included_afps=part["included_afps"],passed=delta<=TOLERANCE_PP))
            for component in part["components"]:
                published_value=expected.get(component["afp"],{}).get("annualized_since_2002")
                if published_value is None:continue
                delta=abs(component["annualized"]-published_value)*100
                afps.append(dict(fund=fund,period=period,afp=component["afp"],calculated=component["annualized"],published=published_value,difference_pp=delta,passed=delta<=TOLERANCE_PP))
            if fund in "CE":
                unavailable.append(dict(fund=fund,period=period,horizon="SINCE_ORIGIN",reason="Historia anterior a 2002 no disponible en estos archivos"))
    complete=[x for x in systems if x["fully_comparable"]]
    return dict(status="PARTIAL_NON_BLOCKING",system_comparisons=len(complete),system_failures=sum(not x["passed"] for x in complete),
                partial_system_diagnostics=len(systems)-len(complete),partial_system_max_difference_pp=max((x["difference_pp"] for x in systems),default=None),
                afp_comparisons=len(afps),afp_failures=sum(not x["passed"] for x in afps),afp_max_difference_pp=max((x["difference_pp"] for x in afps),default=None),
                unavailable=len(unavailable),system_details=systems,afp_details=afps,unavailable_details=unavailable,
                limitation="No se inventan sucesiones/fusiones de AFP ni datos anteriores a 2002; los diagnósticos parciales no validan el promedio completo del sistema.")
