"""Bot y canal de Telegram: solo entrega imágenes aprobadas y textos fijos."""
import json
import re
from html import escape

import pytest

from fondoclaro.config import Blocked
from fondoclaro.content.faq import (ANSWERS, MENU, NOT_UNDERSTOOD, SUMMARY_LABEL,
                                    interpret, keyboard)
from fondoclaro.content.text_checks import reject_language
from fondoclaro.serialization import read_json
from fondoclaro.workflow.telegram import (check, owner_reply, publish_telegram,
                                          reply, serve)

from test_workflow_audit import registry, sealed  # noqa: F401  (fixtures compartidas)

ENV = dict(TELEGRAM_BOT_TOKEN="secreto:123", TELEGRAM_CHANNEL="@fondoclaro_test")


class Fake:
    """Transporte falso: no hay red en las pruebas."""
    def __init__(self, result=None):
        self.calls, self.result = [], result

    def __call__(self, token, method, fields, files=()):
        self.calls.append(dict(method=method, fields=fields, files=[f[0] for f in files]))
        if method == "sendMediaGroup":
            return [dict(message_id=10+i, chat=dict(username="fondoclaro_test")) for i in range(len(files))]
        if method == "getUpdates":
            return self.result or []
        if method == "getMe":
            return dict(id=42, username="fondoclaro_test_bot")
        return dict(message_id=7, chat=dict(username="fondoclaro_test"))


def test_every_answer_is_plain_language():
    for label, _, text, technical in ANSWERS.values():
        reject_language(text, technical=technical)  # sin jerga ni consejos
        reject_language(label)
    reject_language(MENU)
    reject_language(NOT_UNDERSTOOD)


def test_bot_never_gives_investment_advice():
    kind, key = interpret("¿qué fondo me conviene?")
    assert (kind, key) == ("respuesta", "que_fondo_elegir")
    assert "no te la puedo hacer yo" in ANSWERS[key][2]


@pytest.mark.parametrize("probe,expected", [
    ("C", ("fondo", "C")), ("fondo e", ("fondo", "E")), ("resumen", ("resumen", None)),
    ("5", ("resumen", None)), ("hola", ("respuesta", "que_es")),
    ("no sé mi fondo", ("respuesta", "mi_fondo")), ("baja", ("respuesta", "baja")),
    ("blablabla", ("menu", None)), ("", ("menu", None)),
])
def test_routing(probe, expected):
    assert interpret(probe) == expected


@pytest.mark.parametrize("probe,expected", [
    # Nadie escribe la frase exacta: se reconoce por palabras clave.
    ("oye y cual fondo me conviene?", ("respuesta", "que_fondo_elegir")),
    ("no tengo idea que fondo tengo", ("respuesta", "mi_fondo")),
    ("cuanto plata gane yo?", ("respuesta", "es_mi_plata")),
    ("esto es confiable??", ("respuesta", "fuente")),
    ("de donde sacas estos datos", ("respuesta", "fuente")),
    ("QUE SIGNIFICA EL ASTERISCO", ("respuesta", "asterisco")),
    ("ya no quiero recibir mas", ("respuesta", "baja")),
    ("sacame de aqui", ("respuesta", "baja")),
    ("cobras algo?", ("respuesta", "quien_eres")),
    ("gracias!", ("respuesta", "gracias")),
    ("soy del c", ("fondo", "C")),
    ("quiero el grafico del fondo d", ("fondo", "D")),
    ("resumen porfa", ("resumen", None)),
    ("👍", ("menu", None)),
])
def test_routing_free_text(probe, expected):
    assert interpret(probe) == expected


@pytest.mark.parametrize("probe,expected", [
    # Preguntas cargadas: se responden con el dato, nunca con una opinión.
    ("por que las afp ganan y nosotros perdemos", "por_que_ganan"),
    ("nos roban la plata", "por_que_ganan"),
    ("cuanto cobran de comision", "por_que_ganan"),
    ("no+afp", "opinion_sistema"),
    ("NO MAS AFP", "opinion_sistema"),
    ("esto es una estafa", "opinion_sistema"),
    ("estas a favor de las afp", "opinion_sistema"),
    ("por que bajo tanto este mes", "por_que_bajo"),
    ("por que esta en rojo", "por_que_bajo"),
])
def test_charged_questions_get_a_factual_answer(probe, expected):
    kind, key = interpret(probe)
    assert (kind, key) == ("respuesta", expected)


def test_bot_states_no_opinion_on_the_system():
    """Debe decir que no opina: tomar partido destruye la neutralidad de la fuente."""
    assert "no opino" in ANSWERS["opinion_sistema"][2].casefold()
    assert "no opino" in ANSWERS["por_que_ganan"][2].casefold()


def test_charged_answers_name_no_administrator_and_give_no_advice():
    for key in ("por_que_ganan", "opinion_sistema", "por_que_bajo"):
        reject_language(ANSWERS[key][2])


@pytest.mark.parametrize("probe", [
    "tengo 45.000.000 con cuanto me jubilo?",
    "con cuanto me jubilo",
    "$38.500.000",
    "tengo ahorrado 60 millones",
    "cuanto me va a quedar de pension",
    "45000000",
    "me puedo jubilar ya?",
    "calcula mi pension",
])
def test_pension_questions_never_get_a_number(probe):
    """Estimar una jubilación es asesoría previsional: actividad regulada.

    Un monto equivocado sobre la jubilación de alguien es el peor fracaso
    posible del proyecto, así que el bot explica la regla y deriva al
    simulador oficial, sin calcular nunca.
    """
    kind, key = interpret(probe)
    assert (kind, key) == ("respuesta", "con_cuanto_me_jubilo")


def test_pension_answer_gives_no_figure_and_names_the_official_tool():
    text = ANSWERS["con_cuanto_me_jubilo"][2]
    assert "spensiones.cl/apps/simuladorPensiones/" in text
    assert "ClaveÚnica" in text
    assert len(text.split()) <= 40, "la respuesta debe ser corta"
    # Ninguna cifra de plata en la respuesta: no se insinúa un monto.
    assert not re.search(r"\$\s*\d|\d{1,3}(?:\.\d{3}){2,}", text)


def test_amount_alone_does_not_leak_into_the_fund_images(registry):  # noqa: F811
    """Mandar un saldo no debe gatillar la entrega de una imagen ni un cálculo."""
    fake = Fake()
    kind, value = reply(registry, "t", 123456789, "tengo $52.300.000", transport=fake)
    assert (kind, value) == ("respuesta", "con_cuanto_me_jubilo")
    assert fake.calls[0]["method"] == "sendMessage"
    assert fake.calls[0]["files"] == []


def test_every_button_matches_its_own_answer():
    """Apretar un botón envía su pregunta tal cual: debe calzar siempre."""
    labels = {label: key for key, (label, _, _, _) in ANSWERS.items()}
    for row in keyboard()["keyboard"]:
        for button in row:
            text = button["text"]
            kind, value = interpret(text)
            if text in labels:
                assert (kind, value) == ("respuesta", labels[text]), text
            elif text == SUMMARY_LABEL:
                assert kind == "resumen", text
            else:
                assert (kind, value) == ("fondo", text), text


def test_text_reply_carries_the_keyboard(registry):  # noqa: F811
    fake = Fake()
    reply(registry, "t", 123456789, "cualquier cosa rara", transport=fake)
    assert "keyboard" in fake.calls[0]["fields"]["reply_markup"]


def test_no_credentials_blocks(registry):  # noqa: F811
    with pytest.raises(Blocked, match="TELEGRAM_NOT_CONFIGURED"):
        publish_telegram(registry, "2026-10", env={})


def test_summary_must_be_approved(registry, sealed):  # noqa: F811
    registry.approve(sealed, sealed, without_external=True)  # solo el fondo C
    with pytest.raises(Blocked, match="SUMMARY_NOT_APPROVED"):
        publish_telegram(registry, "2026-10", env=ENV, transport=Fake())


def test_nothing_sent_without_any_approval(registry, sealed):  # noqa: F811
    fake = Fake()
    with pytest.raises(Blocked):
        publish_telegram(registry, "2026-10", env=ENV, transport=fake)
    assert fake.calls == []


def test_dry_run_sends_nothing(registry, sealed):  # noqa: F811
    registry.approve(sealed, sealed, without_external=True)
    fake = Fake()
    try:
        publish_telegram(registry, "2026-10", env=ENV, dry_run=True, transport=fake)
    except Blocked:
        pass
    assert fake.calls == []


def test_bot_answers_question_with_fixed_text(registry):  # noqa: F811
    fake = Fake()
    kind, value = reply(registry, "t", 123456789, "¿de dónde salen los números?", transport=fake)
    assert (kind, value) == ("respuesta", "fuente")
    assert fake.calls[0]["method"] == "sendMessage"
    assert fake.calls[0]["fields"]["text"] == ANSWERS["fuente"][2]


def test_bot_says_so_when_no_approved_image(registry):  # noqa: F811
    fake = Fake()
    kind, value = reply(registry, "t", 123456789, "C", transport=fake)
    assert value == "sin_imagen"
    assert fake.calls[0]["method"] == "sendMessage"


def test_bot_sends_approved_image(registry, sealed):  # noqa: F811
    registry.approve(sealed, sealed, without_external=True)
    fake = Fake()
    reply(registry, "t", 123456789, "fondo C", transport=fake)
    assert fake.calls[0]["method"] == "sendPhoto"
    assert fake.calls[0]["files"] == ["photo"]


def test_serve_masks_identifiers(registry):  # noqa: F811
    seen = []
    fake = Fake(result=[dict(update_id=1, message=dict(chat=dict(id=987654321), text="hola"))])
    serve(registry, limit=1, env=ENV, transport=fake, log=seen.append)
    joined = " ".join(seen)
    assert "987654321" not in joined and "987" in joined and "*" in joined


class FakeCheck(Fake):
    def __init__(self, status="administrator", can_post=True):
        super().__init__()
        self.status, self.can_post = status, can_post

    def __call__(self, token, method, fields, files=()):
        self.calls.append(dict(method=method, fields=fields, files=[f[0] for f in files]))
        if method == "getMe":
            return dict(id=42, username="fondoclaro_bot")
        if method == "getChat":
            return dict(title="FondoClaro", username="fondoclaro", member_count=3)
        return dict(status=self.status, can_post_messages=self.can_post)


def test_check_reports_ready(registry):  # noqa: F811
    result = check(registry, env=ENV, transport=FakeCheck())
    assert result["listo"] and result["problemas"] == []
    assert result["bot"] == "@fondoclaro_bot" and result["enlace"] == "t.me/fondoclaro"
    assert all(c["method"] != "sendPhoto" for c in FakeCheck().calls)


def test_check_detects_bot_not_admin(registry):  # noqa: F811
    result = check(registry, env=ENV, transport=FakeCheck(status="member"))
    assert not result["listo"] and "no es administrador" in result["problemas"][0]


def test_check_detects_missing_post_permission(registry):  # noqa: F811
    result = check(registry, env=ENV, transport=FakeCheck(can_post=False))
    assert not result["listo"] and "sin permiso para publicar" in result["problemas"][0]


def test_call_without_files_uses_form_encoding():
    """Un multipart vacío lo rechaza la API con 400: sin archivos va como formulario."""
    from fondoclaro.workflow import telegram as mod
    sent = {}

    class FakeResponse:
        def read(self, *a): return b'{"ok":true,"result":{}}'
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(request, timeout=None):
        sent["type"] = request.headers.get("Content-type")
        sent["body"] = request.data
        return FakeResponse()

    original = mod.urllib.request.urlopen
    mod.urllib.request.urlopen = fake_urlopen
    try:
        mod.call("t", "getMe", {})
        assert sent["type"] == "application/x-www-form-urlencoded"
        mod.call("t", "sendPhoto", dict(chat_id="@x"), [("photo", "a.png", b"bytes")])
        assert sent["type"].startswith("multipart/form-data")
    finally:
        mod.urllib.request.urlopen = original


OWNER = dict(ENV, OWNER_TELEGRAM_ID="555")


def test_owner_commands_ignored_for_strangers(registry, sealed):  # noqa: F811
    """Un desconocido que escriba «aprobar» recibe el menú, no aprueba nada."""
    fake = Fake()
    kind, _ = reply(registry, "t", 999, "aprobar", transport=fake)
    assert kind == "menu"
    assert not (registry.directory(sealed)/"approval.json").exists()


def test_owner_must_review_before_approving(registry, sealed):  # noqa: F811
    fake, shown = Fake(), {}
    owner_reply(registry, "t", 555, "aprobar", shown, transport=fake)
    assert "Primero escribe" in fake.calls[-1]["fields"]["text"]
    assert not (registry.directory(sealed)/"approval.json").exists()


def test_owner_review_then_approve(registry, sealed):  # noqa: F811
    fake, shown = Fake(), {}
    owner_reply(registry, "t", 555, "revisar", shown, transport=fake)
    assert fake.calls[0]["method"] == "sendPhoto"
    assert shown and sealed in shown
    owner_reply(registry, "t", 555, "aprobar", shown, transport=fake)
    assert (registry.directory(sealed)/"approval.json").exists()
    assert "Aprobadas 1" in fake.calls[-1]["fields"]["text"]
    assert shown == {}


def test_approval_rejected_if_content_changed_after_review(registry, sealed):  # noqa: F811
    """§9.5: si algo cambió desde «revisar», rechaza."""
    fake, shown = Fake(), {}
    owner_reply(registry, "t", 555, "revisar", shown, transport=fake)
    shown[sealed] = "hash-distinto-al-vigente"
    owner_reply(registry, "t", 555, "aprobar", shown, transport=fake)
    assert "Algo cambió" in fake.calls[-1]["fields"]["text"]
    assert not (registry.directory(sealed)/"approval.json").exists()


def test_owner_status_reports_counts(registry, sealed):  # noqa: F811
    fake = Fake()
    owner_reply(registry, "t", 555, "estado", {}, transport=fake)
    text = fake.calls[-1]["fields"]["text"]
    assert "2026-10" in text and "Esperando revisión: 1" in text


def test_unknown_order_is_not_an_owner_command(registry):  # noqa: F811
    assert owner_reply(registry, "t", 555, "hola", {}, transport=Fake()) is None


def _summary_report(registry):
    """Informe resumen sintético, en HUMAN_REVIEW_PENDING."""
    from fondoclaro.audit.package import ARTIFACTS
    from fondoclaro.serialization import write_json
    from fondoclaro.workflow.states import FLOW, State
    report_id = registry.create("all", "2026-10")
    path = registry.directory(report_id)
    for name in ARTIFACTS:
        if name.endswith(".json"):
            write_json(path/name, {"kind": "SYNTHETIC_UNIT_TEST"})
        else:
            (path/name).write_bytes(b"SYNTHETIC_UNIT_TEST")
    registry.seal(report_id)
    for state in FLOW[1:FLOW.index(State.HUMAN_REVIEW_PENDING)+1]:
        registry.transition(report_id, state)
    return report_id


def _fund_report(registry, fund):
    from fondoclaro.audit.package import ARTIFACTS
    from fondoclaro.serialization import write_json
    from fondoclaro.workflow.states import FLOW, State
    report_id = registry.create(fund, "2026-10")
    path = registry.directory(report_id)
    for name in ARTIFACTS:
        if name.endswith(".json"):
            write_json(path/name, {"kind": "SYNTHETIC_UNIT_TEST"})
        else:
            (path/name).write_bytes(b"SYNTHETIC_UNIT_TEST")
    registry.seal(report_id)
    for state in FLOW[1:FLOW.index(State.HUMAN_REVIEW_PENDING)+1]:
        registry.transition(report_id, state)
    return report_id




def test_republishing_a_deleted_post_is_not_an_error(registry):  # noqa: F811
    """Si el post se borra del canal, volver a publicar debe funcionar."""
    from fondoclaro.workflow.states import State
    summary = _summary_report(registry)
    registry.approve(summary, summary, without_external=True)
    publish_telegram(registry, "2026-10", env=ENV, transport=Fake())
    assert registry.get(summary)[1]["state"] == State.MARKED_PUBLISHED
    primera = read_json(registry.directory(summary)/"publication.json")["evidence"]
    fake = Fake()
    resultado = publish_telegram(registry, "2026-10", env=ENV, transport=fake)
    assert resultado["posted"]["all"]
    assert any(c["method"] == "sendPhoto" for c in fake.calls)
    # La evidencia original se conserva.
    assert read_json(registry.directory(summary)/"publication.json")["evidence"] == primera


def test_fund_images_go_in_one_album(registry):  # noqa: F811
    """Cinco posts seguidos ocupan pantallas enteras; en álbum es un bloque."""
    summary = _summary_report(registry)
    registry.approve(summary, summary, without_external=True)
    for fund in "AB":
        rid = _fund_report(registry, fund)
        registry.approve(rid, rid, without_external=True)
    fake = Fake()
    publish_telegram(registry, "2026-10", con_fondos=True, env=ENV, transport=fake)
    fotos = [c for c in fake.calls if c["method"] == "sendPhoto"]
    assert len(fotos) == 1, "solo el resumen va como foto suelta"
    album = next(c for c in fake.calls if c["method"] == "sendMediaGroup")
    assert album["fields"]["disable_notification"]
    assert album["files"] == ["fA", "fB"]
    media = json.loads(album["fields"]["media"])
    assert "caption" in media[0] and "caption" not in media[1], "una sola leyenda"
    assert "#Octubre2026" in media[0]["caption"]


def test_faq_survives_missing_pin_permission(registry):  # noqa: F811
    """Sin permiso para fijar, el mensaje igual queda publicado."""
    from fondoclaro.workflow.telegram import publish_faq

    class SinPermiso(Fake):
        def __call__(self, token, method, fields, files=()):
            if method == "pinChatMessage":
                raise Blocked("TELEGRAM_HTTP_400: not enough rights")
            return super().__call__(token, method, fields, files)

    resultado = publish_faq(registry, env=ENV, transport=SinPermiso())
    assert resultado["fijado"] is False
    assert "a mano" in resultado["aviso"]



def test_month_separator_and_hashtag(registry):  # noqa: F811
    """Sin separador ni etiqueta, noviembre se confunde con octubre."""
    summary = _summary_report(registry)
    registry.approve(summary, summary, without_external=True)
    rid = _fund_report(registry, "A")
    registry.approve(rid, rid, without_external=True)
    fake = Fake()
    publish_telegram(registry, "2026-10", con_fondos=True, env=ENV, transport=fake)
    cabecera = next(c for c in fake.calls if c["method"] == "sendMessage")
    assert "OCTUBRE 2026" in cabecera["fields"]["text"]
    assert cabecera["fields"]["disable_notification"]
    for foto in [c for c in fake.calls if c["method"] == "sendPhoto"]:
        assert "#Octubre2026" in foto["fields"]["caption"]
    assert not any(c["method"] == "pinChatMessage" for c in fake.calls), \
        "fijar cada mes publica un aviso de servicio que ensucia el canal"


def test_month_label_for_every_month():
    from fondoclaro.workflow.telegram import _mes
    assert _mes("2026-01") == ("ENERO 2026", "#Enero2026")
    assert _mes("2026-12") == ("DICIEMBRE 2026", "#Diciembre2026")







def test_faq_is_one_message_short_when_collapsed():
    """Un mensaje: preguntas a la vista y respuestas en un solo bloque plegado."""
    from fondoclaro.content.faq import ANSWERS
    from fondoclaro.workflow.telegram import faq_post
    texto = faq_post()
    assert texto.count("<blockquote expandable>") == 1, "un solo rectángulo, no trece"
    visible = re.sub(r"<blockquote expandable>.*?</blockquote>", "", texto, flags=re.S)
    assert len(visible) < 650, f"lo visible son {len(visible)} caracteres"
    for label, _, respuesta, _ in ANSWERS.values():
        if label in ("Gracias", "¿Qué es esto?"):
            continue
        assert label in visible, "la pregunta va a la vista"
        assert escape(respuesta) in texto, "la respuesta va dentro del bloque"

def test_publish_faq_sends_exactly_one_message(registry):  # noqa: F811
    from fondoclaro.workflow.telegram import publish_faq
    fake = Fake()
    publish_faq(registry, env=ENV, transport=fake)
    envios = [c for c in fake.calls if c["method"] == "sendMessage"]
    assert len(envios) == 1, "dos mensajes es justo lo que no se quiere"
    assert envios[0]["fields"]["disable_notification"]


def test_nothing_promises_the_bot_in_the_channel():
    """El bot puede estar apagado: el canal no puede mandar a escribirle."""
    from fondoclaro.workflow.telegram import PIE_CANAL, faq_post
    assert "bot" not in faq_post().casefold()
    assert "bot" not in PIE_CANAL.casefold()
    assert "acá abajo" in PIE_CANAL


def test_summary_mentions_the_album_only_when_published(registry):  # noqa: F811
    summary = _summary_report(registry)
    registry.approve(summary, summary, without_external=True)
    solo = Fake()
    publish_telegram(registry, "2026-10", env=ENV, transport=solo)
    pie = next(c for c in solo.calls if c["method"] == "sendPhoto")["fields"]["caption"]
    assert "acá abajo" not in pie, "sin álbum no se promete el álbum"
    rid = _fund_report(registry, "A")
    registry.approve(rid, rid, without_external=True)
    con = Fake()
    publish_telegram(registry, "2026-10", con_fondos=True, env=ENV, transport=con)
    pie = next(c for c in con.calls if c["method"] == "sendPhoto")["fields"]["caption"]
    assert "acá abajo" in pie


def test_buttons_link_to_each_fund_and_the_faq():
    from fondoclaro.workflow.telegram import botones
    teclado = botones({"A": "u/9", "B": "u/10", "C": "u/11", "D": "u/12", "E": "u/13"},
                      "u/45")
    filas = teclado["inline_keyboard"]
    assert [len(f) for f in filas] == [3, 2, 1]
    assert filas[0][0] == {"text": "Fondo A", "url": "u/9"}
    assert filas[2][0]["text"] == "Preguntas frecuentes"
    # Son enlaces, no comandos: funcionan con el bot apagado.
    assert all("url" in b for fila in filas for b in fila)


def test_buttons_skip_funds_that_are_not_published():
    from fondoclaro.workflow.telegram import botones
    teclado = botones({"A": "u/9", "C": "u/11"}, None)
    textos = [b["text"] for fila in teclado["inline_keyboard"] for b in fila]
    assert textos == ["Fondo A", "Fondo C"]


def test_no_buttons_when_nothing_to_link():
    from fondoclaro.workflow.telegram import botones
    assert botones({}, None) is None


def test_summary_gets_the_buttons_after_the_album(registry):  # noqa: F811
    """Los botones se cuelgan al final, cuando ya se sabe dónde quedó cada lámina."""
    from fondoclaro.workflow.telegram import recordar_faq
    recordar_faq(registry, "https://t.me/fondoclaro/45")
    summary = _summary_report(registry)
    registry.approve(summary, summary, without_external=True)
    for fund in "AB":
        rid = _fund_report(registry, fund)
        registry.approve(rid, rid, without_external=True)
    fake = Fake()
    publish_telegram(registry, "2026-10", con_fondos=True, env=ENV, transport=fake)
    edicion = next(c for c in fake.calls if c["method"] == "editMessageReplyMarkup")
    teclado = json.loads(edicion["fields"]["reply_markup"])
    textos = [b["text"] for fila in teclado["inline_keyboard"] for b in fila]
    assert textos == ["Fondo A", "Fondo B", "Preguntas frecuentes"]


def test_faq_link_is_remembered_for_the_button(registry):  # noqa: F811
    from fondoclaro.workflow.telegram import enlace_faq, publish_faq
    assert enlace_faq(registry) is None
    publish_faq(registry, env=ENV, transport=Fake())
    assert enlace_faq(registry).startswith("https://t.me/")


def test_in_group_the_bot_stays_quiet_when_it_does_not_understand(registry):  # noqa: F811
    """En un grupo no se interrumpe la conversación de la gente."""
    fake = Fake()
    kind, value = reply(registry, "t", -100, "jajaja que buena", en_grupo=True, transport=fake)
    assert (kind, value) == ("menu", "callado")
    assert fake.calls == []


def test_in_private_it_offers_the_menu(registry):  # noqa: F811
    fake = Fake()
    reply(registry, "t", 123, "jajaja que buena", transport=fake)
    assert fake.calls[0]["method"] == "sendMessage"
    assert "keyboard" in fake.calls[0]["fields"]["reply_markup"]


def test_in_group_the_answer_hangs_from_the_question(registry):  # noqa: F811
    fake = Fake()
    reply(registry, "t", -100, "¿de dónde salen los números?",
          en_grupo=True, responde_a=77, transport=fake)
    campos = fake.calls[0]["fields"]
    assert campos["reply_to_message_id"] == 77
    assert "reply_markup" not in campos, "el teclado en grupo lo vería todo el mundo"


def test_in_group_images_also_hang_from_the_question(registry, sealed):  # noqa: F811
    registry.approve(sealed, sealed, without_external=True)
    fake = Fake()
    reply(registry, "t", -100, "fondo C", en_grupo=True, responde_a=88, transport=fake)
    assert fake.calls[0]["method"] == "sendPhoto"
    assert fake.calls[0]["fields"]["reply_to_message_id"] == 88


def test_serve_survives_a_network_drop(registry, monkeypatch):  # noqa: F811
    """Un corte de red no puede matar el bot: reintenta en vez de caerse."""
    from fondoclaro.workflow import telegram as mod
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    intentos = []

    def inestable(token, method, fields, files=()):
        intentos.append(method)
        if len(intentos) <= 3:
            raise Blocked("TELEGRAM_UNREACHABLE en getUpdates: URLError")
        return [dict(update_id=1, message=dict(chat=dict(id=1, type="private"), text="hola"))]

    serve(registry, limit=1, env=ENV, transport=inestable, log=lambda *a: None)
    assert intentos.count("getUpdates") >= 4, "debe reintentar, no rendirse"
