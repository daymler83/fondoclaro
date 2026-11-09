import shutil

from ..config import Blocked
from ..serialization import write_json
from .approved import approved_entries, stem

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
    destination = registry.root/"outputs"/("envio_"+period)
    if destination.exists():
        raise Blocked("SEND_PACKAGE_EXISTS: preservar paquete anterior")
    selected, missing = approved_entries(registry, period)
    destination.mkdir(parents=True)
    for fund, entry, source in selected:
        shutil.copyfile(source, destination/(stem(fund)+".png"))
        (destination/(("00_resumen" if fund == "all" else stem(fund))+".txt")).write_text(entry["whatsapp_text"])
    (destination/"LEEME.txt").write_text(CHECKLIST+"\nNo incluidos por falta de aprobación vigente: "+", ".join(missing)+"\n")
    write_json(destination/"delivery_manifest.json", dict(period=period, missing=missing, reports=[entry for _,entry,_ in selected]))
    return destination, missing
