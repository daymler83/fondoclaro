import shutil

from ..config import Blocked, FUNDS, period_end
from ..serialization import file_hash, read_json, write_json
from .states import State

CHECKLIST = """FondoClaro — envío manual por WhatsApp Business

1. Primer mes: enviar 00_resumen_5_fondos.png a todas las listas. A quienes respondan con una letra, agregarlos a FondoClaro A, B, C, D o E.
2. Meses siguientes: a cada lista, la imagen de su fondo. El resumen puede enviarse a quienes no han elegido fondo.
3. Las listas solo llegan a quien tiene guardado el número y admiten hasta 256 contactos por lista. Si se llena, crear, por ejemplo, FondoClaro C 2.
4. Si alguien pide no recibir más, sacarlo de la lista ese mismo día.
5. No usar extensiones ni programas no oficiales de envío masivo: violan las condiciones de WhatsApp y pueden bloquear el número.
6. Después de enviar cada imagen: python -m fondoclaro mark-published --report-id ID --url "difusión manual YYYY-MM-DD"

No guardar teléfonos, nombres ni la elección de fondo en este repositorio.
"""


def send_package(registry, period):
    period_end(period)
    path = registry.reports/"approved_index.json"
    index = read_json(path) if path.exists() else {}
    destination = registry.root/"outputs"/("envio_"+period)
    if destination.exists():
        raise Blocked("SEND_PACKAGE_EXISTS: preservar paquete anterior")
    selected, missing = [], []
    for fund in ("all", *FUNDS):
        entry = index.get(period+"/"+fund)
        if not entry:
            missing.append(fund)
            continue
        record, state = registry.get(entry["report_id"])
        if state["state"] not in (State.APPROVED_FOR_PUBLICATION, State.MARKED_PUBLISHED):
            missing.append(fund)
            continue
        inventory = registry.integrity(entry["report_id"])
        source = registry.directory(entry["report_id"])/"infographic.png"
        approval = read_json(source.parent/"approval.json")
        if (record["period"] != period or record["fund"] != fund or record["dev"] or
                inventory["content_hash"] != entry["content_hash"] or approval["content_hash"] != entry["content_hash"] or file_hash(source) != entry["png_hash"]):
            raise Blocked("APPROVED_INDEX_INTEGRITY_MISMATCH")
        selected.append((fund, entry, source))
    destination.mkdir(parents=True)
    for fund, entry, source in selected:
        stem = "00_resumen_5_fondos" if fund == "all" else "fondo_"+fund
        shutil.copyfile(source, destination/(stem+".png"))
        (destination/(("00_resumen" if fund == "all" else stem)+".txt")).write_text(entry["whatsapp_text"])
    (destination/"LEEME.txt").write_text(CHECKLIST+"\nNo incluidos por falta de aprobación vigente: "+", ".join(missing)+"\n")
    write_json(destination/"delivery_manifest.json", dict(period=period, missing=missing, reports=[entry for _,entry,_ in selected]))
    return destination, missing
