"""Resumen en orden A–E, siempre ligado a los informes individuales verificados."""
from datetime import date
from decimal import Decimal

from ..config import Blocked, FUNDS, MONTHS, RISK
from ..finance.formatting import direction,percent
from ..render.font import wrap
from .manifest import text_node
from .templates import INVITATION, RISK_NOTE,SLOGAN,TECH_NOTE,footer


def build_summary(individuals):
    if len(individuals) != 5 or [x["manifest"]["fund"] for x in individuals] != list(FUNDS):
        raise Blocked("SUMMARY_ORDER_A_TO_E_REQUIRED")
    periods = {x["manifest"]["cutoff_date"] for x in individuals}
    if len(periods) != 1:
        raise Blocked("SUMMARY_PERIOD_MISMATCH")
    rows = []
    valid_states = {"VISUALLY_VERIFIED", "HUMAN_REVIEW_PENDING", "APPROVED_FOR_PUBLICATION", "MARKED_PUBLISHED"}
    for item in individuals:
        m = item["manifest"]
        if item["state"] not in valid_states or m["r_1m"] == "s/d":
            raise Blocked("INDIVIDUAL_REPORT_NOT_VERIFIED")
        rows.append(dict(fund=m["fund"], risk=RISK[m["fund"]], r_1m=m["r_1m"], r_120m=m["r_120m"],
                         chart_series=m["chart_series"], report_id=item["report_id"], content_hash=item["content_hash"]))
    return dict(cutoff_date=periods.pop(), rows=rows, risk_note=RISK_NOTE, invitation=INVITATION)


def validate_summary(summary, individuals):
    if summary != build_summary(individuals):
        raise Blocked("SUMMARY_EXTRA_CONTENT_OR_MISMATCH: prohibido ranking/destaque")
    return {"summary": "PASS"}


def build_summary_manifest(individuals):
    m=build_summary(individuals)
    cutoff=date.fromisoformat(m["cutoff_date"])
    m.update(kind="SUMMARY",fund="all",schema_version=1,brand="FondoClaro",slogan=SLOGAN,
             month_label=f"{MONTHS[cutoff.month].capitalize()} {cutoff.year}",footer_text=footer(cutoff,summary=True),
             references=[dict(report_id=i["report_id"],content_hash=i["content_hash"]) for i in individuals])
    nodes=[text_node("brand","FondoClaro",140,88,40,700,"#ffffff"),
           text_node("slogan",SLOGAN,140,126,23,400,"#ffffff"),
           text_node("month_label",m["month_label"],797,103,27,700,"#0f5a2c",225),
           text_node("table_title","¿Cómo le fue a cada fondo?",66,224,32,700),
           text_node("header_fund","Fondo",66,275,23,600),
           text_node("header_month","Este mes*",380,275,23,600),
           text_node("header_long","10 años*",596,275,23,600),
           text_node("header_curve","Evolución",824,275,23,600)]
    scales={}
    for k,(row,item) in enumerate(zip(m["rows"],individuals)):
        f=row["fund"];cy=355+k*126
        nodes.extend([text_node(f"letter_{f}",f,82,cy+14,40,700,"#ffffff",60),
                      text_node(f"fund_{f}",f"Fondo {f}",146,cy-8,28,700,max_width=218),
                      text_node(f"risk_{f}",row["risk"],146,cy+23,22,max_width=220)])
        fr=item["manifest"]["financial_results"]["metrics"]
        for key,column,x in (("r_1m",1,380),("r_120m",120,596)):
            metric=fr.get(column,fr.get(str(column)))
            raw=Decimal(str(metric["real"])) if metric["real"] is not None else None
            arrow,color=direction(raw) if raw is not None else ("","#55635c")
            value=arrow+" "+percent(raw,svg=True) if raw is not None else "s/d"
            row["raw_"+key]=str(raw) if raw is not None else None
            nodes.append(text_node(f"{key}_{f}",value,x,cy+14,40,700,color,208))
        vals=[Decimal(p["value"]) for p in row["chart_series"]]
        lo,hi=min(vals),max(vals)
        if hi==lo:hi=lo+1
        scales[f]=dict(left=824,right=1008,top=cy-36,bottom=cy+36,lo=str(lo),hi=str(hi))
    for i,line in enumerate(wrap(RISK_NOTE,22,940)):
        nodes.append(text_node(f"risk_note_{i}",line,66,956+i*28,22))
    for i,line in enumerate(wrap(INVITATION,28,940,600)):
        nodes.append(text_node(f"invitation_{i}",line,66,1077+i*37,28,600))
    foot=wrap(TECH_NOTE,21,940)+wrap(m["footer_text"][len(TECH_NOTE)+1:],21,940)
    if any(row["r_120m"]=="s/d" for row in m["rows"]):
        foot+=wrap("s/d: historia insuficiente en el horizonte indicado.",21,940)
    for i,line in enumerate(foot):nodes.append(text_node(f"footer_{i}",line,66,1189+i*26,21,color="#46574c"))
    m["visible_texts"]=nodes;m["spark_scales"]=scales
    m["whatsapp_text"]=f"FondoClaro · {MONTHS[cutoff.month]} {cutoff.year}. Los cinco fondos, en orden A–E. Responde con tu letra para recibir el gráfico de tu fondo. Fuente: Superintendencia de Pensiones y Banco Central, al {cutoff.day:02d}-{MONTHS[cutoff.month][:3]}-{cutoff.year}."
    return m


def validate_summary_manifest(m,individuals):
    from ..serialization import canonical
    from .text_checks import reject_language
    if canonical(m)!=canonical(build_summary_manifest(individuals)):
        raise Blocked("SUMMARY_EXTRA_CONTENT_OR_MISMATCH")
    for n in m["visible_texts"]:reject_language(n["text"],technical=n["key"].startswith("footer_"))
    if len(m["whatsapp_text"].split())>40:raise Blocked("WHATSAPP_TOO_LONG")
    return {"summary":"PASS","content":"PASS"}
