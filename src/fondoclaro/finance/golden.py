"""Contraste financiero real. Un FAIL no autoriza cambiar datos o metodología."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

from ..config import Blocked, FUNDS, period_end
from ..data.loaders import load_sii_uf, load_sp_csv, load_sp_published
from ..serialization import file_hash, read_json, write_json
from .engine import calculate
from .system import build_system_index, month_snapshots, weighted_period_return

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
            series, steps = build_system_index(quotas[fund],uf,cutoff)
            snapshots = month_snapshots(quotas[fund],cutoff)
            data_counts[fund] = dict(raw_observations=len(quotas[fund]),monthly_points=len(series))
            for period, reference in sorted(published.items()):
                end = period_end(period)
                actual = calculate(series,fund,end)
                row = reference[fund]["rows"]["SISTEMA"]
                for horizon in (1,12):
                    metric = f"r_{horizon}m"
                    expected = row[metric]
                    value = actual.metrics[horizon].real
                    if expected is None or value is None:
                        raise Blocked("GOLDEN_COMPARISON_DATA_MISSING")
                    delta = abs(value-expected)*100
                    direct = weighted_period_return(snapshots,uf,end,horizon)
                    comparisons.append(dict(fund=fund,period=period,metric=metric,calculated=value,published=expected,
                        difference_pp=delta,passed=delta<=TOLERANCE_PP,
                        official_period_weighting=direct,official_period_difference_pp=abs(direct-expected)*100))
            own = [r for r in comparisons if r["fund"]==fund]
            per_fund[fund] = dict(compared=len(own),failed=sum(not r["passed"] for r in own),max_difference_pp=max(r["difference_pp"] for r in own))
    worst = max(comparisons,key=lambda r:r["difference_pp"])
    by_metric = {metric: dict(compared=sum(r["metric"]==metric for r in comparisons),
                             failed=sum(r["metric"]==metric and not r["passed"] for r in comparisons),
                             max_difference_pp=max(r["difference_pp"] for r in comparisons if r["metric"]==metric)) for metric in ("r_1m","r_12m")}
    report = dict(status="FAIL" if any(not r["passed"] for r in comparisons) else "INCOMPLETE",
                  tolerance_pp=TOLERANCE_PP,months=sorted(published),funds=list(FUNDS),compared=len(comparisons),
                  failed=sum(not r["passed"] for r in comparisons),max_difference_pp=worst["difference_pp"],worst_case=worst,
                  by_fund=per_fund,by_metric=by_metric,data_counts=data_counts,uf_daily_points=len(uf),
                  annualized_status="NOT_VALIDATED: HTML publica desde 2002/origen; esos horizontes no tienen insumos desde 2014. PDFs 36/60 preservados, no se declara validación integral.",
                  manifest_sha256=file_hash(manifest_path),comparisons=comparisons)
    return report


def save_evaluation(root: Path):
    report = evaluate_history(root)
    target = root/"reports"/"golden_validation"
    target.mkdir(parents=True,exist_ok=True)
    write_json(target/"result.json",report)
    return report
