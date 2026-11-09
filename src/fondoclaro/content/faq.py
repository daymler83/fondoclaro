"""Preguntas frecuentes del bot, con respuestas escritas de antemano.

§9.4 prohíbe que un canal genere cifras bajo demanda. El bot nunca redacta ni
calcula: elige una de estas respuestas fijas, revisadas por una persona, o
entrega una imagen ya aprobada.

Reconoce la pregunta de dos formas, porque nadie escribe la frase exacta:
botones con la pregunta ya redactada, y palabras clave para el texto libre.
Gana la palabra clave más específica; si ninguna alcanza, ofrece el menú.

Cada respuesta pasa por `reject_language` en las pruebas: sin jerga, sin
consejos de inversión y sin nombres de administradoras.
"""
import re
import unicodedata

MENU = ("Escribe la letra de tu fondo y te mando su gráfico:\n"
        "A · B · C · D · E\n\n"
        "O usa los botones de abajo. También puedes preguntarme con tus "
        "palabras: te entiendo igual.")

# clave: (pregunta para el botón, palabras clave, respuesta, admite palabra técnica)
ANSWERS = {
    "que_es": (
        "¿Qué es esto?",
        ("que es esto", "que es fondoclaro", "para que sirve", "de que se trata",
         "ayuda", "hola", "buenas", "info", "start", "menu"),
        "FondoClaro te muestra, una vez al mes, cómo les fue a los cinco fondos "
        "de las AFP en Chile.\n\nUn gráfico, dos cifras y nada más. Es gratis y no "
        "vendo nada.\n\n" + MENU,
        False),
    "mi_fondo": (
        "¿Cómo sé qué fondo tengo?",
        ("mi fondo", "que fondo tengo", "cual fondo tengo", "no se mi fondo",
         "como se mi fondo", "saber mi fondo", "cual es el mio", "donde veo mi fondo",
         "cual es mi fondo", "no se cual"),
        "Tu fondo es una letra, de la A a la E.\n\nLa encuentras en la aplicación "
        "de tu AFP o en la cartola que te llega. Dice algo así como «Fondo C».\n\n"
        "Cuando la tengas, busca su gráfico más arriba en el canal.",
        False),
    "es_mi_plata": (
        "¿Esto es mi plata?",
        ("mi plata", "mi cuenta", "mi saldo", "mi dinero", "mi ahorro", "cuanto gane",
         "cuanto tengo", "cuanto perdi", "es lo mio", "esto es mio", "me gane",
         "gane", "perdi", "gano yo", "plata gane"),
        "No. Las cifras son del promedio de todo el sistema, no de tu cuenta.\n\n"
        "Lo tuyo depende de cuánto llevas ahorrado y de cuándo entró cada peso. "
        "Para ver tu saldo tienes que entrar a tu AFP.",
        False),
    "diez_millones": (
        "¿Por qué 10 millones?",
        ("10 millones", "diez millones", "10.000.000", "los millones", "por que 10",
         "de donde salen los 10", "esos millones"),
        "Son un ejemplo, no tu plata.\n\nEl gráfico muestra en qué se habrían "
        "convertido 10 millones puestos hace diez años y dejados quietos. Sirve "
        "para hacerse una idea del tamaño del cambio.",
        False),
    "asterisco": (
        "¿Qué significa el asterisco?",
        ("asterisco", "descontada", "inflacion", "que significa el", "el *",
         "por que el asterisco"),
        "El asterisco avisa que la cifra ya tiene descontada la inflación.\n\n"
        "O sea: es lo que de verdad alcanza a comprar, no el número antes de que "
        "los precios suban.",
        True),
    "fuente": (
        "¿De dónde salen los números?",
        ("de donde salen", "de donde sacas", "fuente", "quien calcula", "confiable",
         "es verdad", "oficial", "los datos", "inventado", "quien los saca"),
        "De la Superintendencia de Pensiones y del Banco Central, que son "
        "públicas y oficiales.\n\nYo solo las ordeno y las dibujo. No invento "
        "ninguna cifra.",
        False),
    "que_fondo_elegir": (
        "¿Qué fondo me conviene?",
        ("me conviene", "mejor fondo", "cual es mejor", "cual es el mejor", "me cambio",
         "cambiarme", "me paso", "que fondo elijo", "que fondo escojo", "recomienda",
         "recomiendas", "que hago", "me sirve mas", "conviene"),
        "Esa decisión no te la puedo hacer yo, y desconfía de quien te la haga "
        "por mensaje.\n\nLos fondos se ordenan de la A, que se mueve más, a la E, "
        "que se mueve menos. Lo que calza contigo depende de cuántos años te "
        "faltan y de cuánto te incomoda ver bajar el saldo.\n\nSi quieres "
        "orientarte, pregunta en tu AFP o en la Superintendencia de Pensiones, "
        "que atiende consultas del público.",
        False),
    "cada_cuanto": (
        "¿Cada cuánto publicas?",
        ("cada cuanto", "cuando publicas", "cuando sale", "frecuencia", "proximo",
         "todos los meses", "cuando viene", "cuando subes"),
        "Una vez al mes, cuando la Superintendencia publica el mes cerrado. "
        "Suele ser en los primeros días del mes siguiente.",
        False),
    "quien_eres": (
        "¿Quién está detrás?",
        ("quien eres", "quien hizo", "quien esta detras", "eres una afp", "trabajas para",
         "cobras", "es gratis", "vendes", "me vas a vender", "que ganas tu"),
        "No soy una AFP ni trabajo para ninguna. No cobro, no vendo y no tengo "
        "avisos.\n\nEsto lo hace una persona que quería que esta información se "
        "entendiera sin ser experto.",
        False),
    "baja": (
        "No quiero recibir más",
        ("baja", "no quiero mas", "no quiero recibir", "dejar de recibir", "salir",
         "stop", "chao", "desuscribir", "eliminame", "sacame"),
        "Para dejar de recibir estos mensajes, sal del canal desde el menú de "
        "Telegram: toca el nombre arriba y elige salir.\n\nSi algún día quieres "
        "volver, acá va a estar.",
        False),
    "por_que_ganan": (
        "¿Por qué la AFP gana igual?",
        ("por que ganan", "ganan igual", "ellos ganan", "se llevan", "comision",
         "cuanto cobran", "nos roban", "roban", "cobran igual", "negocio",
         "ganan ellos", "lucran", "se enriquecen", "afp ganan", "ganan y nosotros",
         "nosotros perdemos", "perdemos", "ganan ellas", "se la llevan"),
        "La AFP cobra una comisión por administrar. Se calcula sobre tu sueldo y "
        "no sobre cómo le va al fondo.\n\nLas subidas y las bajas del fondo van a "
        "tu cuenta, no a la AFP. Y la comisión se paga igual en los meses en que "
        "el fondo baja: eso es efectivamente así, está escrito en el sistema.\n\n"
        "Yo no opino del sistema. Te muestro las cifras oficiales para que saques "
        "tus propias conclusiones.",
        False),
    "opinion_sistema": (
        "¿Qué opinas del sistema?",
        ("que opinas", "no mas afp", "no afp", "estas a favor", "estas en contra", "eres de",
         "que piensas del sistema", "hay que cambiar", "sirve el sistema",
         "es un robo", "estafa", "politica"),
        "No opino, y es a propósito.\n\nSi te digo qué pensar, ya no te sirvo para "
        "saber qué pasó. Lo que hago es sacar las cifras oficiales y dibujarlas "
        "simple, para que discutas el tema con los datos en la mano, sea lo que "
        "sea que pienses.\n\nPuedes estar muy a favor o muy en contra: las cifras "
        "son las mismas y acá las vas a encontrar.",
        False),
    "con_cuanto_me_jubilo": (
        "¿Con cuánto me jubilo?",
        ("con cuanto me jubilo", "cuanto me jubilo", "me jubilo", "jubilar", "jubilacion",
         "cuanto voy a recibir", "cuanto me va a quedar", "con cuanto quedo", "me alcanza",
         "cuanto me daran", "cuanto me van a dar", "me puedo jubilar", "mi pension",
         "que pension", "cuanta pension", "tengo ahorrado", "llevo ahorrado",
         "si tengo", "calcula", "calcular"),
        "Hazlo gratis acá, con tu ClaveÚnica:\n"
        "spensiones.cl/apps/simuladorPensiones/",
        False),
    "por_que_bajo": (
        "¿Por qué bajó este mes?",
        ("por que bajo", "por que baja", "bajo mucho", "esta en rojo", "numero negativo",
         "por que negativo", "que paso este mes", "por que subio", "por que sube"),
        "Los fondos están invertidos en acciones y bonos, y esos precios suben y "
        "bajan todos los meses. Cuando bajan, el fondo baja.\n\nNo es un cobro ni "
        "un error: es lo que vale ese día lo que el fondo tiene guardado.",
        False),
    "gracias": (
        "Gracias",
        ("gracias", "muchas gracias", "te agradezco", "buena", "genial", "excelente",
         "bakan", "la raja", "que bueno"),
        "De nada. Si quieres ver otro fondo, escríbeme su letra.",
        False),
}

SUMMARY_LABEL = "Ver los cinco fondos"
NOT_UNDERSTOOD = "No estoy seguro de qué me preguntas.\n\n" + MENU


def normalize(text):
    """Minúsculas, sin acentos y sin puntuación: así escribe la gente de verdad."""
    plain = unicodedata.normalize("NFD", (text or "").casefold())
    plain = "".join(ch for ch in plain if unicodedata.category(ch) != "Mn")
    kept = [ch if (ch.isalnum() or ch in " .") else " " for ch in plain]
    return " ".join("".join(kept).split())


FUND_WORDS = {}
for _letter in "ABCDE":
    for _form in (_letter, "fondo "+_letter, "el "+_letter, "soy "+_letter,
                  "fondo tipo "+_letter, "la "+_letter, "mi fondo es "+_letter):
        FUND_WORDS[normalize(_form)] = _letter

SUMMARY_WORDS = tuple(normalize(w) for w in
                      ("resumen", "todos", "los cinco", "5", "cinco", "todo", "los 5",
                       "todos los fondos", SUMMARY_LABEL))

# Etiqueta de botón y palabras clave, todo normalizado para comparar.
_INDEX = {key: ([normalize(label)] + [normalize(k) for k in keywords])
          for key, (label, keywords, _, _) in ANSWERS.items()}


MONEY = re.compile(r"\$\s*\d|\b\d{1,3}(?:[.\s]\d{3}){2,}\b|\b\d{7,}\b|\bmillones?\b")


def interpret(text):
    """Clasifica un mensaje. Devuelve ('fondo', 'A'..'E'), ('resumen', None),
    ('respuesta', clave) o ('menu', None). Nunca redacta nada nuevo.

    Para texto libre gana la palabra clave más larga que aparezca: así
    «que fondo tengo» no se confunde con «que fondo me conviene».
    """
    clean = normalize(text)
    if not clean:
        return "menu", None
    if clean in FUND_WORDS:
        return "fondo", FUND_WORDS[clean]
    if clean in SUMMARY_WORDS:
        return "resumen", None
    best, best_len = None, 0
    for key, needles in _INDEX.items():
        for needle in needles:
            if needle and needle in clean and len(needle) > best_len:
                best, best_len = key, len(needle)
    if best and best_len >= 4:
        return "respuesta", best
    # Alguien que manda su saldo y nada más está preguntando por su jubilación.
    if MONEY.search(normalize(text)) and "10 millones" not in clean:
        return "respuesta", "con_cuanto_me_jubilo"
    for word in clean.split():
        if word in FUND_WORDS:
            return "fondo", FUND_WORDS[word]
        if word in SUMMARY_WORDS:
            return "resumen", None
    return "menu", None


def answer(key):
    return ANSWERS[key][2]


def keyboard():
    """Teclado de Telegram: al apretar un botón se envía su pregunta tal cual,
    así que siempre calza con la respuesta correcta."""
    rows = [[{"text": letter} for letter in "ABCDE"],
            [{"text": SUMMARY_LABEL}]]
    hidden = ("¿Qué es esto?", "Gracias")
    labels = [label for label, _, _, _ in ANSWERS.values() if label not in hidden]
    rows += [[{"text": label}] for label in labels]
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}
