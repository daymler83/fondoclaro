"""Canal de difusión por Telegram (§9.4): publica solo imágenes aprobadas.

Gratuito y sin aprobación previa de la plataforma. Un canal de Telegram tiene
difusión real: un post lo leen todos los suscriptores, sin costo por persona.

Lee únicamente `approved_index.json`, verifica el hash del PNG antes de subirlo
y no calcula ni redacta cifras: el pie es el texto aprobado de §7.6.

Configuración, en `.env` y nunca en git:
    TELEGRAM_BOT_TOKEN   token que entrega @BotFather
    TELEGRAM_CHANNEL     destino, por ejemplo @fondoclaro
"""
import json
import mimetypes
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request

from ..config import Blocked
from ..serialization import read_json, write_json
from .states import State
from .approved import approved_entries, latest_approved, pending_reports, stem

API = "https://api.telegram.org"
TIMEOUT = 60


def load_env(root):
    """Variables del proceso, completadas con `.env` del proyecto si existe."""
    values = dict(os.environ)
    path = root/".env"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            values.setdefault(name.strip(), value.strip().strip("'\""))
    return values


def _credentials(env=None):
    env = env if env is not None else os.environ
    token, channel = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_CHANNEL")
    if not token or not channel:
        raise Blocked("TELEGRAM_NOT_CONFIGURED: falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHANNEL en .env")
    return token, channel


def _multipart(fields, files):
    """Codifica multipart/form-data. `files` es [(campo, nombre, bytes)]."""
    boundary = "----FondoClaro" + secrets.token_hex(16)
    marker = ("--" + boundary).encode()
    body = bytearray()
    for name, value in fields.items():
        body += marker + b"\r\n"
        body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        body += str(value).encode() + b"\r\n"
    for name, filename, payload in files:
        kind = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        body += marker + b"\r\n"
        body += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        body += f"Content-Type: {kind}\r\n\r\n".encode()
        body += payload + b"\r\n"
    body += marker + b"--\r\n"
    return bytes(body), "multipart/form-data; boundary=" + boundary


def call(token, method, fields, files=()):
    """Llama a la API de Telegram. Nunca incluye el token en el mensaje de error.

    Sin archivos va como formulario simple: un multipart vacío lo rechaza la API.
    """
    if files:
        body, content_type = _multipart(fields, files)
    else:
        body = urllib.parse.urlencode({k: str(v) for k, v in fields.items()}).encode()
        content_type = "application/x-www-form-urlencoded"
    request = urllib.request.Request(f"{API}/bot{token}/{method}", data=body,
                                     headers={"Content-Type": content_type})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            answer = json.loads(response.read(2_000_000))
    except urllib.error.HTTPError as exc:
        detail = exc.read(4000).decode("utf-8", "replace")
        raise Blocked(f"TELEGRAM_HTTP_{exc.code} en {method}: {detail[:400]}") from None
    except (OSError, ValueError) as exc:
        raise Blocked(f"TELEGRAM_UNREACHABLE en {method}: {type(exc).__name__}") from None
    if not answer.get("ok"):
        raise Blocked(f"TELEGRAM_REJECTED en {method}: {str(answer.get('description'))[:400]}")
    return answer["result"]


def _link(channel, message):
    chat = message.get("chat", {}) if isinstance(message, dict) else {}
    name = chat.get("username") or channel.lstrip("@")
    return f"https://t.me/{name}/{message.get('message_id')}" if message.get("message_id") else "telegram:"+channel


def publish_telegram(registry, period, *, con_fondos=False, dry_run=False, env=None, transport=call):
    """Publica en el canal el resumen aprobado del período.

    Por omisión publica solo la imagen resumen: es la que se entiende sola.
    Con `con_fondos`, agrega las cinco individuales como un álbum aparte.
    Registra la publicación de cada informe con el enlace como evidencia (§11).
    """
    token, channel = _credentials(env if env is not None else load_env(registry.root))
    selected, missing = approved_entries(registry, period)
    chosen = dict((fund, (entry, source)) for fund, entry, source in selected)
    if "all" not in chosen:
        raise Blocked("SUMMARY_NOT_APPROVED: la imagen resumen de "+period+" no está aprobada")
    entry, source = chosen["all"]
    if dry_run:
        return dict(dry_run=True, channel=channel, period=period,
                    publicaria=["all"]+([f for f in "ABCDE" if f in chosen] if con_fondos else []),
                    missing=missing)
    posted = {}
    titulo, etiqueta = _mes(period)
    # Separador de mes: sin él, noviembre se confunde con octubre al hacer scroll.
    transport(token, "sendMessage", dict(chat_id=channel, text=f"<b>— {titulo} —</b>",
                                         parse_mode="HTML", disable_notification=True))
    caption = (entry["whatsapp_text"] + (PIE_CANAL if con_fondos else "")
               + "\n\n" + etiqueta)
    message = transport(token, "sendPhoto", dict(chat_id=channel, caption=caption),
                        [("photo", stem("all")+".png", source.read_bytes())])
    posted["all"] = _link(channel, message)
    # No se fija el resumen: cada fijado publica un aviso de servicio
    # («fijó una foto») que ensucia el canal todos los meses. Basta con
    # el índice de preguntas fijado una sola vez.
    # Las cinco en un álbum: un bloque ordenado en vez de cinco pantallas
    # seguidas. Se tocan para verlas completas y se desliza entre ellas.
    funds = [f for f in "ABCDE" if f in chosen] if con_fondos else []
    if funds:
        media, files = [], []
        for posicion, fund in enumerate(funds):
            campo = "f"+fund
            item = dict(type="photo", media="attach://"+campo)
            if posicion == 0:
                item["caption"] = (f"Los cinco fondos uno por uno. Toca para verlos.\n\n"
                                   + etiqueta)
            media.append(item)
            files.append((campo, stem(fund)+".png", chosen[fund][1].read_bytes()))
        album = transport(token, "sendMediaGroup",
                          dict(chat_id=channel, disable_notification=True,
                               media=json.dumps(media, ensure_ascii=False)), files)
        for fund, item in zip(funds, album if isinstance(album, list) else []):
            posted[fund] = _link(channel, item)
    teclado = botones({f: posted.get(f) for f in "ABCDE"}, enlace_faq(registry))
    if teclado:
        transport(token, "editMessageReplyMarkup",
                  dict(chat_id=channel, message_id=message["message_id"],
                       reply_markup=json.dumps(teclado, ensure_ascii=False)))
    for fund, url in posted.items():
        report_id = chosen[fund][0]["report_id"]
        # Republicar algo ya marcado (p. ej. si se borró el post) no es un error:
        # la evidencia anterior se conserva y no se vuelve a transicionar.
        if registry.get(report_id)[1]["state"] != State.MARKED_PUBLISHED:
            registry.mark_published(report_id, url)
    return dict(channel=channel, period=period, posted=posted, missing=missing)


NO_IMAGE = "Todavía no tengo el gráfico de este mes. En unos días lo publico."


def _mask(chat_id):
    text = str(chat_id)
    return text[:3] + "*" * max(0, len(text) - 5) + text[-2:] if len(text) > 5 else "*****"


def reply(registry, token, chat_id, text, *, transport=call):
    """Responde un mensaje. Si piden un fondo, manda la imagen aprobada."""
    from ..content.faq import NOT_UNDERSTOOD, answer, interpret, keyboard
    kind, value = interpret(text)
    if kind in ("fondo", "resumen"):
        found = latest_approved(registry, value if kind == "fondo" else "all")
        if not found:
            transport(token, "sendMessage", dict(chat_id=chat_id, text=NO_IMAGE))
            return kind, "sin_imagen"
        _, entry, source = found
        transport(token, "sendPhoto", dict(chat_id=chat_id, caption=entry["whatsapp_text"]),
                  [("photo", stem(value if kind == "fondo" else "all")+".png", source.read_bytes())])
        return kind, value or "all"
    body = answer(value) if kind == "respuesta" else NOT_UNDERSTOOD
    transport(token, "sendMessage", dict(chat_id=chat_id, text=body,
              reply_markup=json.dumps(keyboard(), ensure_ascii=False)))
    return kind, value or "menu"


def serve(registry, *, limit=None, env=None, transport=call, log=print):
    """Atiende mensajes con getUpdates: sin servidor, sin dominio, sin HTTPS.

    No guarda números, nombres ni el contenido de los mensajes: el registro
    muestra el identificador enmascarado y solo el tipo de pedido.
    """
    values = env if env is not None else load_env(registry.root)
    token, _ = _credentials(values)
    dueno, shown = owner_id(values), {}
    offset, served = None, 0
    log("FondoClaro: bot escuchando. Ctrl+C para detener.")
    while limit is None or served < limit:
        fields = dict(timeout=25)
        if offset is not None:
            fields["offset"] = offset
        updates = transport(token, "getUpdates", fields)
        if not updates:
            if limit is not None:
                break
            continue
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message") or update.get("edited_message") or {}
            chat_id = (message.get("chat") or {}).get("id")
            if not chat_id or not message.get("text"):
                continue
            try:
                done = (owner_reply(registry, token, chat_id, message["text"], shown,
                                    transport=transport) if chat_id == dueno else None)
                if done:
                    log(f"dueño -> {done}")
                else:
                    kind, value = reply(registry, token, chat_id, message["text"], transport=transport)
                    log(f"{_mask(chat_id)} -> {kind}:{value}")
            except Blocked as exc:
                log(f"{_mask(chat_id)} -> error: {exc}")
            served += 1
            if limit is not None and served >= limit:
                break
    return served


def check(registry, *, env=None, transport=call):
    """Comprueba que el token sirve y que el bot puede publicar en el canal.

    No publica nada. Sirve para descubrir un error de configuración antes del
    envío y no durante.
    """
    token, channel = _credentials(env if env is not None else load_env(registry.root))
    me = transport(token, "getMe", {})
    chat = transport(token, "getChat", dict(chat_id=channel))
    member = transport(token, "getChatMember", dict(chat_id=channel, user_id=me["id"]))
    status = member.get("status")
    can_post = bool(member.get("can_post_messages")) or status == "creator"
    problems = []
    if status != "administrator" and status != "creator":
        problems.append(f"el bot no es administrador del canal (está como «{status}»)")
    elif not can_post:
        problems.append("el bot es administrador pero sin permiso para publicar mensajes")
    return dict(bot="@"+me.get("username", "?"), canal=chat.get("title"),
                enlace="t.me/"+(chat.get("username") or channel.lstrip("@")),
                suscriptores=chat.get("member_count"),
                listo=not problems, problemas=problems)


# Línea de navegación del canal. No lleva cifras: §9.4 prohíbe que un canal
# genere datos, no que diga dónde escribir.
PIE_CANAL = "\n\nLas cinco láminas, una por fondo, están acá abajo."

MESES = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def _mes(period):
    """('OCTUBRE 2026', '#Octubre2026') — separador y etiqueta del mes."""
    anio, mes = period.split("-")
    nombre = MESES[int(mes)]
    return f"{nombre.upper()} {anio}", f"#{nombre.capitalize()}{anio}"

SIN_PENDIENTES = "No hay imágenes esperando revisión."
NO_MOSTRADAS = "Primero escribe «revisar» para ver qué vas a aprobar."
CAMBIO = "Algo cambió desde que las revisaste. Escribe «revisar» de nuevo."


def _estado_path(registry):
    return registry.reports/"telegram_state.json"


def recordar_faq(registry, enlace):
    estado = read_json(_estado_path(registry)) if _estado_path(registry).exists() else {}
    estado["faq"] = enlace
    write_json(_estado_path(registry), estado)


def enlace_faq(registry):
    path = _estado_path(registry)
    return (read_json(path).get("faq") if path.exists() else None)


def botones(enlaces_fondos, faq=None):
    """Teclado bajo el resumen: lleva a cada lámina y a las preguntas.

    Son enlaces internos del canal, así que funcionan siempre: no dependen
    de que el bot esté encendido.
    """
    filas, fila = [], []
    for letra in "ABCDE":
        if enlaces_fondos.get(letra):
            fila.append({"text": "Fondo "+letra, "url": enlaces_fondos[letra]})
        if len(fila) == 3:
            filas.append(fila); fila = []
    if fila:
        filas.append(fila)
    if faq:
        filas.append([{"text": "Preguntas frecuentes", "url": faq}])
    return {"inline_keyboard": filas} if filas else None


def owner_id(env):
    raw = (env or {}).get("OWNER_TELEGRAM_ID", "").strip()
    return int(raw) if raw.isdigit() else None


def owner_reply(registry, token, chat_id, text, shown, *, transport=call):
    """Comandos del dueño (§9.5): revisar, aprobar, publicar, estado.

    `shown` es lo que mostró el último «revisar»; «aprobar» solo acepta eso
    y rechaza si algún hash cambió desde entonces.
    """
    order = (text or "").strip().casefold()
    if order not in ("revisar", "aprobar", "publicar", "estado"):
        return None
    period, rows = pending_reports(registry)
    if order == "estado":
        aprobados, _ = approved_entries(registry, period) if period else ([], [])
        transport(token, "sendMessage", dict(chat_id=chat_id, text=(
            f"Período: {period or 'ninguno'}\n"
            f"Esperando revisión: {len(rows)}\n"
            f"Ya aprobadas: {len(aprobados)}")))
        return "estado"
    if order == "revisar":
        if not rows:
            transport(token, "sendMessage", dict(chat_id=chat_id, text=SIN_PENDIENTES))
            return "revisar"
        shown.clear()
        for fund, report_id, content_hash, png, caption in rows:
            etiqueta = "Resumen" if fund == "all" else "Fondo "+fund
            transport(token, "sendPhoto", dict(chat_id=chat_id, caption=etiqueta+"\n"+caption),
                      [("photo", stem(fund)+".png", png.read_bytes())])
            shown[report_id] = content_hash
        transport(token, "sendMessage", dict(chat_id=chat_id, text=(
            f"Son {len(rows)} de {period}. Si están bien, escribe «aprobar». "
            "Si algo está mal, no escribas nada y me avisas.")))
        return "revisar"
    if order == "aprobar":
        if not shown:
            transport(token, "sendMessage", dict(chat_id=chat_id, text=NO_MOSTRADAS))
            return "aprobar"
        vigentes = {report_id: content_hash for _, report_id, content_hash, _, _ in rows}
        if vigentes != shown:
            shown.clear()
            transport(token, "sendMessage", dict(chat_id=chat_id, text=CAMBIO))
            return "aprobar"
        hechas, fallidas = [], []
        for report_id in list(shown):
            try:
                registry.approve(report_id, report_id, without_external=True)
                hechas.append(report_id)
            except Blocked as exc:
                fallidas.append(f"{report_id[:8]}…: {exc}")
        shown.clear()
        mensaje = f"Aprobadas {len(hechas)} de {period}."
        if fallidas:
            mensaje += "\nNo pude con:\n" + "\n".join(fallidas)
        mensaje += "\n\nEscribe «publicar» para sacarlas al canal."
        transport(token, "sendMessage", dict(chat_id=chat_id, text=mensaje))
        return "aprobar"
    # publicar
    try:
        _, aprobadas = pending_reports(registry)
        objetivo = period or max((k.split("/")[0] for k in
                                  read_json(registry.reports/"approved_index.json")), default=None)
        resultado = publish_telegram(registry, objetivo, transport=transport)
        transport(token, "sendMessage", dict(chat_id=chat_id, text=(
            "Publicado en el canal.\n" + "\n".join(resultado["posted"].values()))))
    except Blocked as exc:
        transport(token, "sendMessage", dict(chat_id=chat_id, text="No pude publicar: "+str(exc)))
    return "publicar"


def find_owner(registry, *, env=None, transport=call):
    """Toma el último mensaje privado recibido y guarda ese id como dueño."""
    values = env if env is not None else load_env(registry.root)
    token, _ = _credentials(values)
    updates = transport(token, "getUpdates", dict(timeout=0))
    privados = [u for u in updates
                if (u.get("message") or {}).get("chat", {}).get("type") == "private"]
    if not privados:
        raise Blocked("SIN_MENSAJES: escríbele algo a tu bot por privado y vuelve a correr esto")
    chat = privados[-1]["message"]["chat"]
    path = registry.root/".env"
    lineas = [l for l in path.read_text().splitlines() if not l.startswith("OWNER_TELEGRAM_ID=")]
    lineas.append(f"OWNER_TELEGRAM_ID={chat['id']}")
    path.write_text("\n".join(lineas) + "\n")
    path.chmod(0o600)
    return dict(dueno=chat.get("username") or chat.get("first_name"), guardado_en=".env")


def _faq_visible():
    from ..content.faq import ANSWERS
    return [(label, text) for label, _, text, _ in ANSWERS.values()
            if label not in ("Gracias", "¿Qué es esto?")]


def faq_post(bot_username=None):
    """Un solo mensaje: la lista de preguntas y las respuestas en un bloque plegado.

    El bloque va colapsado, así que ocupa tres líneas. Las respuestas quedan en
    el canal y no dependen de que el bot esté encendido.
    """
    from html import escape
    visibles = _faq_visible()
    partes = ["<b>PREGUNTAS FRECUENTES</b>",
              "\n".join(f"· {escape(label)}" for label, _ in visibles)]
    # La primera línea del bloque es un rótulo, no una respuesta: plegado se ve
    # eso y no un trozo de respuesta mezclado con la lista de preguntas.
    cuerpo = "\n\n".join(f"▸ <b>{escape(label.upper())}</b>\n{escape(text)}"
                          for label, text in visibles)
    partes.append("<blockquote expandable><b>▾ TOCA ACÁ PARA VER LAS RESPUESTAS</b>\n\n"
                  + cuerpo + "</blockquote>")
    return "\n\n".join(partes)


def publish_faq(registry, *, reemplazar=None, env=None, transport=call):
    """Publica las preguntas frecuentes en el canal y las fija.

    Con `reemplazar`, reescribe ese mensaje en vez de publicar uno nuevo: evita
    duplicados y conserva el fijado.
    """
    token, channel = _credentials(env if env is not None else load_env(registry.root))
    bot = transport(token, "getMe", {}).get("username")
    texto = faq_post("@"+bot if bot else None)
    if len(texto) > 4096:
        raise Blocked(f"FAQ_DEMASIADO_LARGA: {len(texto)} caracteres, el máximo es 4096")
    if reemplazar:
        message = transport(token, "editMessageText",
                            dict(chat_id=channel, message_id=int(reemplazar),
                                 text=texto, parse_mode="HTML"))
    else:
        message = transport(token, "sendMessage", dict(chat_id=channel, text=texto,
                                                       parse_mode="HTML",
                                                       disable_notification=True))
    # Fijar en un canal exige «Editar mensajes». Si falta, el mensaje igual queda
    # publicado y se puede fijar a mano: no se pierde el trabajo por un permiso.
    fijado, aviso = True, None
    try:
        transport(token, "pinChatMessage", dict(chat_id=channel, message_id=message["message_id"],
                                                disable_notification=True))
    except Blocked as exc:
        fijado, aviso = False, ("publicado pero no fijado; dale al bot el permiso "
                                "«Editar mensajes», o fíjalo a mano: " + str(exc)[:120])
    enlace = _link(channel, message)
    recordar_faq(registry, enlace)
    return dict(canal=channel, enlace=enlace, caracteres=len(texto),
                fijado=fijado, aviso=aviso)
