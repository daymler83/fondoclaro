# FONDOCLARO — ESPECIFICACIÓN V1 PARA IMPLEMENTACIÓN

> "Tus ahorros, explicados en 30 segundos."

Este documento reemplaza la propuesta anterior. Es la fuente de verdad para la versión 1.
Si algo de este documento contradice otra instrucción, manda este documento.
Si algo no está especificado aquí, elige la opción más conservadora, documéntala en
`docs/DECISIONES.md` y sigue; no inventes alcance nuevo.

---

## 0. REGLAS DE TRABAJO

Rol: ingeniero de software y datos financieros trabajando en este repositorio.

Puedes: crear y modificar archivos del proyecto, instalar dependencias del proyecto,
ejecutar pruebas, generar documentos e imágenes locales.

No puedes, sin aprobación humana explícita: enviar mensajes, publicar, desplegar,
usar credenciales que no se te hayan entregado, ni modificar configuración global
de herramientas (Codex, Claude, git global, etc.).

Excepción acotada: el bot de WhatsApp de §9.5 **responde** a quien le escribe, y solo con
imágenes ya aprobadas. Nunca inicia conversaciones ni envía a listas.

Reglas de honestidad:

- No declares completado un componente que no esté implementado **y** cubierto por pruebas que pasan.
- No afirmes que una auditoría externa ocurrió si no existe su archivo de resultado validado (§10).
- Nunca ajustes una fórmula, tolerancia o dato para que una prueba pase. Si la prueba dorada (§6.1)
  falla, detente y repórtalo (§15).
- Registra todo bloqueo en `docs/BLOQUEOS.md` con: qué falta, por qué, qué necesitas del humano.

---

## 1. QUÉ SE CONSTRUYE

Un pipeline determinístico que, con un solo comando:

```
python -m fondoclaro run --fund C --period latest
```

produce, para un tipo de fondo y un mes cerrado:

1. **Una imagen PNG para WhatsApp** (1080×1350 px) según §7: **dos cifras, un gráfico y una
   explicación simple.** Principio rector: una persona sin conocimientos financieros la entiende
   en menos de 30 segundos. Todo el rigor está detrás; en la imagen solo está lo necesario.
2. **Un texto de acompañamiento** para WhatsApp (≤ 40 palabras), según §7.6.
   Además, con `--fund all`: **una imagen resumen "Los 5 fondos"** (§7.8), que es la del primer
   envío a contactos cuyo fondo no se conoce y la que se reenvía en grupos.
3. **Un manifiesto** con todas las cifras y textos visibles, y su trazabilidad.
4. **Un paquete de auditoría** exportable (§10).
5. **Un registro de ejecución** reproducible (§11).

Y lo deja en estado `HUMAN_REVIEW_PENDING`. Nunca publica.

Referencias visuales (cifras ficticias en ambas):

- `docs/reference/maqueta_objetivo.png` y `docs/reference/render_maqueta.py`: **el diseño a
  implementar.** El script genera la maqueta desde datos, en SVG, y la rasteriza; úsalo como
  punto de partida del renderizador, no como código de producción.
- `docs/reference/mockup_original.png`: primera idea de diseño, **con errores documentados en
  §6.4** que el sistema debe ser capaz de detectar. No implementes ese diseño.

---

## 2. DECISIONES FIJADAS PARA V1

| Tema | Decisión |
|---|---|
| Universo | Multifondos A, B, C, D, E. **Promedio del sistema** (no AFP individuales). |
| Vigencia | Los multifondos se reemplazan por Fondos Generacionales el 1-abr-2027. El modelo de datos trata el fondo como entidad genérica con fecha de inicio y término. Si se pide un período donde el fondo no existe o no tiene historia suficiente, la métrica se omite o el informe se bloquea (§5.5). No implementes Fondos Generacionales en v1. |
| Rentabilidad real | Deflactada por **UF del último día del mes**, igual que la metodología de la Superintendencia de Pensiones (SP). No usar IPC directo. |
| Horizontes | Se calculan y validan mes, 12, 60 y 120 meses. **En la imagen solo se muestran dos cifras: el mes y los 10 años (acumulado).** 12 y 60 meses quedan en el manifiesto y el paquete de auditoría, no en la imagen. La anualizada se calcula y guarda para validar contra SP. |
| Convención monetaria | Todo monto está en **pesos de la fecha de corte** ("pesos de hoy"). Se declara en la imagen. |
| Montos hipotéticos | **Una sola base**: $10.000.000 en pesos de hoy, hace 120 meses (§5.3). El mes se expresa solo en %, nunca en pesos. |
| `latest` | Último mes calendario cerrado con valor cuota y UF de fin de mes disponibles. |
| Uso de LLM en el pipeline | **Ninguno en v1.** Todo texto sale de plantillas determinísticas (§7). |
| Investigación económica | Fuera de alcance v1. La imagen no atribuye causas. |
| Redes | Solo WhatsApp en v1. |
| Auditoría externa (Claude) | Opcional y consultiva. No reemplaza ni bloquea las validaciones determinísticas; su ausencia se muestra en la aprobación (§9). |
| Publicación | Manual, fuera del sistema. El sistema solo registra que se publicó (§9). |

---

## 3. ARQUITECTURA

El pipeline es una secuencia determinística de etapas. No hay "agentes" autónomos en v1;
cada etapa es un módulo con entrada y salida tipadas (dataclasses o pydantic) y
serializables a JSON. Ninguna etapa puede producir una cifra que no venga del motor financiero.

```
fondoclaro/
  pyproject.toml
  src/fondoclaro/
    __main__.py            # python -m fondoclaro
    cli.py
    config.py
    data/
      sources.py           # definición de fuentes y formatos
      collectors.py        # descarga opcional (red) -> raw_data/
      loaders.py           # lectura de archivos raw -> series normalizadas
      checks.py            # duplicados, huecos, fechas, rangos
    finance/
      engine.py            # cálculo principal (§5)
      independent.py       # recálculo por camino distinto (§6.2)
      formatting.py        # formato es-CL y redondeo (§7.1)
    content/
      manifest.py          # construye el manifiesto (fuente única de lo visible)
      templates.py         # textos por casos (§7.5, §7.6)
      text_checks.py       # números en texto ⊆ manifiesto, bases no mezcladas, frases prohibidas
    render/
      svg_template.svg.j2  # plantilla de la infografía
      chart.py             # gráfico como paths SVG generados desde datos
      render.py            # SVG -> PNG
      visual_checks.py     # nodos de texto, desbordes, gráfico vs datos (§8)
    audit/
      package.py           # exporta paquete (§10)
      schemas.py           # JSON Schema de audit_results.json
      importer.py          # valida e importa resultado externo
    workflow/
      states.py            # máquina de estados (§9)
      pipeline.py
      registry.py          # registro de informes y ejecuciones (§11)
  tests/
    fixtures/              # archivos oficiales reales, con hash (§4.3)
    golden/                # cifras publicadas por SP para prueba dorada (§6.1)
  docs/
    reference/            # maqueta_objetivo.png, render_maqueta.py, mockup_original.png
    FUENTES.md  METODOLOGIA.md  DECISIONES.md  BLOQUEOS.md
  raw_data/  reports/  audit_packages/
```

Python ≥ 3.11. Cálculos con `decimal.Decimal` (precisión ≥ 28). Dependencias mínimas y fijadas.
Fuente tipográfica de licencia abierta incluida en el repo (no depender de fuentes del sistema).
La maqueta usa Inter (licencia SIL OFL); incluir los .otf usados en `src/fondoclaro/render/fonts/`.

---

## 4. DATOS

### 4.1 Fuentes

- **Valor cuota** por tipo de fondo, último día hábil de cada mes: Superintendencia de Pensiones
  (spensiones.cl). Si SP publica directamente la serie o rentabilidad del "Sistema" (promedio
  ponderado), usar esa. Si solo publica por AFP, **no inventes la ponderación**: investiga y
  documenta el método oficial de SP en `docs/METODOLOGIA.md`, impleméntalo y valídalo con §6.1.
  Si no puedes reproducir las cifras oficiales del sistema, detente (§15).
- **UF** diaria (se usa el valor del último día de cada mes): Banco Central de Chile.
  Si la API requiere credenciales, no las busques ni las inventes: pide los archivos o la
  credencial vía variable de entorno y registra el bloqueo.
- **Rentabilidades oficiales publicadas por SP** (mensual, 12 meses, promedios anuales):
  solo para validación (§6.1), nunca como insumo del cálculo.

Primera tarea obligatoria: documentar en `docs/FUENTES.md` la URL exacta, formato, columnas,
frecuencia, zona horaria/fecha de corte y ejemplo de cada fuente, a partir de archivos reales.

### 4.2 Reglas

- Nunca datos inventados, ni interpolación o relleno silencioso. Un hueco en la ventana de un
  horizonte omite esa métrica (§5.5); un hueco en el mes actual bloquea el informe.
- No usar prensa como fuente de cifras.
- Cada archivo descargado se guarda tal cual en `raw_data/<fuente>/<fecha_descarga>/` con SHA-256.
- Si un archivo nuevo cambia un valor histórico ya usado en un informe, es una **revisión**:
  se registra, no se sobreescribe nada, y los informes previos quedan intactos (§11).

### 4.3 Red y pruebas

El entorno puede no tener red. **Todas las pruebas corren offline** contra `tests/fixtures/`,
que contiene recortes de archivos oficiales reales con su hash y su URL de origen.
La descarga en vivo es un paso separado (`python -m fondoclaro fetch`) y opcional.
Si no hay red ni archivos, crea los lectores, deja el bloqueo documentado y continúa con el
resto usando fixtures marcados como `SYNTHETIC` **solo en pruebas unitarias**; un informe real
nunca puede generarse con datos sintéticos (validación bloqueante).

---

## 5. MOTOR FINANCIERO

### 5.1 Definiciones

Método autorizado por Daymler el 8-nov-2026: el SISTEMA es el promedio ponderado
de los retornos de las AFP en el mismo horizonte, no un índice encadenado único.
Para cada AFP a, mes inicial i y corte j:

- `r_a(i,j) = (VC_a,j / VC_a,i) × (UF_i / UF_j) − 1`.
- `w_a(j−1) = patrimonio_a,j−1 / Σ patrimonio_a,j−1` entre AFP con historia
  completa para el horizonte. Las AFP sin historia se registran como excluidas;
  nunca se inventa ni rellena una cuota. Si no queda historia suficiente, s/d.
- `r_sistema(i,j) = Σ_a w_a(j−1) × r_a(i,j)`.
- Nominal: el mismo promedio de `VC_a,j / VC_a,i − 1`.
- Anualizada: promedio con los mismos pesos de la anualizada de cada AFP,
  `(1 + r_a)^(365/nd) − 1`, con nd días exactos, según la fórmula publicada por SP.
- Horizontes `n ∈ {1,12,60,120}`, `i = j − n`; cuotas y UF de fin de mes.

Cada resultado conserva AFP incluidas/excluidas, patrimonios y ponderaciones.
Prohibido sumar retornos, deflactar dos veces, mezclar IPC/UF o usar retornos de
contraste SP como insumo. No hay un I_t único válido para todos los horizontes.

### 5.2 Métricas que produce

Por fondo y corte: `r_1m, r_12m, r_60m, r_120m`, reales acumuladas por el método
SP de §5.1, sus nominales y las anualizadas de 60/120 meses. Se conservan los
componentes, pesos y exclusiones de cada horizonte para auditoría.

La serie visible es V_t de §5.3, 121 puntos si hay diez años. No se exporta un
índice real único que se presente como equivalente al SISTEMA por horizonte.
`meses_negativos_120` cuenta los retornos mensuales SP negativos de esa ventana;
no se infiere de cambios de la curva, pues sus ponderaciones pueden variar.

### 5.3 Monto hipotético — una sola base

Base única `base_id="LARGO_120"`: $10.000.000 en pesos de hoy, hace 120 meses.
Para el corte j, inicio fijo b = j−120 y cada t de b a j:

`V_t = 10.000.000 × (1 + r_sistema(b,t))`.

En b se fija V_b = 10.000.000. Cada retorno usa el mismo método SP de §5.1 y
los patrimonios del mes anterior a su propio corte t; nunca un índice encadenado.
Por construcción, el último punto exacto es
`V_j = 10.000.000 × (1 + r_120m)`.

El signo de V_j−V_(j−1) ya no es una identidad con r_1m, porque los pesos difieren.
Se valida §6.3-6 y se bloquea si hay discrepancia; no se modifica la curva para
forzar el signo. Para historia reducida, mismo procedimiento con el inicio del
horizonte disponible. El mes se comunica solo en porcentaje, nunca en pesos.
Toda cifra monetaria conserva base_id; no se mezclan bases hipotéticas.

### 5.4 Redondeo

Cálculo sin redondear. Redondeo **solo** al formatear, `ROUND_HALF_UP`:
porcentajes a 1 decimal; montos sobre base $10.000.000 al múltiplo de $10.000.
Con esa elección, el monto redondeado es exactamente el porcentaje redondeado aplicado a la base,
así que el lector siempre puede verificar "+48,0% sobre $10.000.000 = $14.800.000". Agrega una
prueba de propiedad (hypothesis) que lo garantice.

### 5.5 Disponibilidad

Si una ventana `[j−n, j]` tiene huecos o el fondo no existía, la métrica se marca
`NO_DISPONIBLE` con motivo. La plantilla la muestra como "s/d" con nota al pie; el gráfico se
acorta al período disponible y cambia su título. Si falta `r_1m`, el informe se bloquea.

---

## 6. VALIDACIÓN (TODA BLOQUEANTE)

Cualquier fallo de esta sección deja el informe en `BLOCKED` con el motivo exacto.

### 6.1 Prueba dorada contra SP

Bloqueante para este ciclo: al menos 24 cortes históricos × 5 fondos × (mes y
12 meses), 240 comparaciones, con el método SP de §5.1. Tolerancia intacta:
`|calculado − publicado| ≤ 0,01 puntos porcentuales`, por el redondeo SP a dos
decimales. Si falla, detenerse: no ajustar fórmulas, datos ni tolerancia.

Los promedios anuales publicados se intentan con historia desde 2002 y desde
origen donde alcance. Son consultivos y no bloqueantes en este ciclo autorizado;
se reportan comparaciones, fallos, diferencia máxima y límites de cobertura,
sin llamar validado a un promedio cuyo historial o sucesiones de AFP falten.
No se compara un acumulado de diez años con una anualizada de otro horizonte.

En cada ejecución real se contrasta además el corte si SP lo publicó; si todavía
no, se registra `SP_NO_PUBLICADO_AUN` visible en la revisión humana.

### 6.2 Recálculo por camino independiente

`independent.py` tiene lectores propios de CSV cuota/patrimonio y UF, sin importar
engine.py ni loaders.py. Para cada AFP encadena factores reales mensuales
`Π[(VC_a,t / VC_a,t−1) × (UF_t−1 / UF_t)] − 1`, y luego pondera los retornos
individuales con patrimonio de j−1. Se contrasta con el cálculo principal por
cociente de extremos por AFP y suma ponderada. Se verifican las mismas AFP
incluidas/excluidas, sin encadenar retornos agregados del sistema.

La tolerancia relativa sigue siendo `1e-9`; solo cubre residuos aritméticos.
El recálculo incluye horizontes críticos y los puntos de la curva, que usan el
mismo inicio fijo y el peso del mes anterior a cada corte. La justificación y
cobertura se guardan en el paquete de auditoría.

### 6.3 Invariantes del contenido

Deben verificarse sobre el manifiesto **y** sobre lo efectivamente renderizado (§8):

1. Cada cifra visible existe en el manifiesto y coincide carácter a carácter.
2. Signo, flecha y color de cada métrica coinciden con el signo del valor redondeado.
3. La imagen contiene exactamente estas cifras y ninguna otra: `r_1m`, `r_120m`, `$10.000.000`,
   `V_j`, el año del mes de corte, la fecha de corte y los rótulos de ejes. Ningún monto en pesos
   asociado al mes.
4. El último punto del gráfico = etiqueta final = `V_j` = `10.000.000 × (1 + r_120m)`.
5. Globo final y "¿Qué significa?" muestran el mismo `V_j`; globo final y tarjeta de 10 años
   muestran el mismo `r_120m`.
6. **El último tramo del gráfico (mes j−1 → j) sube, baja o queda plano según el signo de `r_1m`.** Es una validación bloqueante, no una identidad del método SP: si las ponderaciones por corte producen un signo distinto, se bloquea; no se altera la serie.
7. El eje X cubre exactamente la ventana del gráfico; primer y último mes rotulados con su año real.
8. Todo número que aparece en un texto pertenece al manifiesto (extracción por regex de
   porcentajes, montos, años y conteos).
9. Ninguna frase combina cifras de bases distintas.
10. Ninguna frase prohibida (§7.7).
11. Pie de fuente presente con fecha de corte exacta.
12. No hay datos personales (nombres, RUT, correos, teléfonos) en ningún archivo exportado.
13. Toda cifra descontada por inflación en tarjetas y título del gráfico lleva asterisco, y la
    nota "* Descontada la inflación…" está presente y es la primera línea del pie.

### 6.4 Pruebas de regresión construidas con los errores del mockup original

`mockup_original.png` tiene errores reales. Cada uno debe tener una prueba que construya un
manifiesto o SVG con ese error y verifique que el sistema **lo rechaza**:

| # | Error en el mockup | Regla que lo detecta |
|---|---|---|
| E1 | "Perdiste $200.000 este mes, pero tu ahorro sigue $4.800.000 por sobre el valor de hace 10 años": mezcla dos bases hipotéticas distintas (con $9.800.000 no puedes estar $4.800.000 sobre $10.000.000). | 6.3-9 |
| E2 | El gráfico termina subiendo mientras el mes muestra −2,0%. | 6.3-6 |
| E3 | "Cifras aproximadas" en el pie (resta credibilidad a cifras que son exactas y verificadas). | 6.3-10 |
| E4 | "Tu pensión en 30 segundos": no es la pensión, es la rentabilidad del fondo. | 6.3-10 |
| E5 | "Perdiste" en segunda persona sobre un monto hipotético. | 6.3-10 |
| E6 | Pie sin fecha de corte ni indicación de promedio del sistema. | 6.3-11 |
| E7 | El relleno del área se extiende más allá del último punto de la línea. | §8.3 |
| E8 | El eje X termina en 2025 aunque la ventana llega al mes de corte. | 6.3-7 |
| E9 | "Las inversiones de largo plazo pueden tener meses difíciles y aun así generar crecimiento": afirmación genérica tranquilizadora, no derivada de los datos. | 6.3-10 |
| E10 | Exceso de cifras: tarjetas de 12 meses y 5 años, y montos en pesos del mes ("−$200.000", "de $10.000.000 a $9.800.000") que usan otra base. | 6.3-3 |
| E11 | (Resumen) Un fondo destacado como "el mejor", o filas ordenadas por rentabilidad. | §7.8 |

---

## 7. CONTRATO DE LA IMAGEN (WhatsApp, 1080×1350 px)

Diseño de referencia: `docs/reference/maqueta_objetivo.png`, generado por
`docs/reference/render_maqueta.py`. Estilo de tarjetas, compacto, legible en un teléfono.
Contenido mínimo: **dos cifras, un gráfico y una explicación de una o dos líneas.**

```
┌────────────────────────────────────────────────┐
│ ▐▌ FondoClaro                     ( Fondo C )  │  encabezado verde
│    Tus ahorros, explicados en 30 segundos      │
├───────────────────────┬────────────────────────┤
│ Este mes              │ Últimos 10 años        │  dos tarjetas
│ ↓ −2,0%*              │ ↑ +48,0%*              │  (rojo / verde según signo)
│ octubre 2026          │ acumulado              │
├───────────────────────┴────────────────────────┤
│ Así pudo evolucionar $10.000.000 en 10 años*   │  tarjeta del gráfico
│                              [$14.800.000    ] │  globo final
│                              [hoy (+48,0%)   ] │
│               ╱╲      ╱╲╱╲      ╱╲╱──●         │  último tramo en rojo/verde
│  [$10.000.000]   ╲╱╲╱╱    ╲╱╲╱╱                │  globo inicial
│  ●──╱╲╱                                        │
│  2017  2018  …                       2026      │
├────────────────────────────────────────────────┤
│ 📅 ¿Qué significa? Octubre fue un mes negativo.│  explicación, ≤ 3 líneas
│    Aun así, en 10 años $10.000.000 pasaron a   │
│    ser $14.800.000.                            │
├────────────────────────────────────────────────┤
│ ⓘ * Descontada la inflación (variación de la   │  pie: nota técnica
│   UF). Montos en pesos de hoy.                 │
│   Fuente: SP y Banco Central, al 31-oct-2026.  │
│   Promedio del sistema. Monto de ejemplo.      │
│   No es una recomendación.                     │
└────────────────────────────────────────────────┘
```

(Cifras ilustrativas.)

### 7.1 Formato es-CL

- Decimal con coma, miles con punto: `14.800.000`, `48,0%`.
- Signo explícito: `+48,0%`, `−2,0%` (U+2212 en la imagen; `-` ASCII en JSON). Cero: `0,0%` sin signo.
- Montos con `$`: `$10.000.000`, `$14.800.000`. Eje Y sin `$`: `12.000.000`.
- Meses en español, minúscula: `octubre 2026`.

### 7.2 Estilo

Fondo de página verde muy claro; tarjetas con esquinas redondeadas. Encabezado verde con texto
blanco. Verde principal, azul para la curva y el globo inicial. Rojo solo para un mes negativo
(tarjeta rosada, flecha y cifra rojas, último tramo rojo); verde para valores positivos. El signo y
la flecha siempre presentes: el color nunca es el único portador del significado. Contraste WCAG
AA ≥ 4.5:1 en todo texto.
Tamaños (a 1080 px de ancho): cifras de las tarjetas ≥ 60 px; títulos de tarjeta ≥ 28 px;
explicación ≥ 26 px; ejes y pie ≥ 21 px. Si algo no cabe, se acorta el texto, no la letra.

### 7.3 Elementos (los únicos permitidos)

| # | Elemento | Contenido | Claves del manifiesto |
|---|---|---|---|
| 1 | Encabezado | "FondoClaro", eslogan, pastilla "Fondo C" | `brand`, `slogan`, `fund_label` |
| 2 | Tarjeta mes | "Este mes", flecha, `r_1m` con asterisco, "{mes} {año}" | `r_1m`, `month_label` |
| 3 | Tarjeta 10 años | "Últimos 10 años", flecha, `r_120m` con asterisco, "acumulado" | `r_120m` |
| 4 | Gráfico | Título "Así pudo evolucionar $10.000.000 en 10 años*" (sin subtítulo), curva, globos, ejes (§7.4) | `chart_series`, `chart_start_label`, `chart_end_label` |
| 5 | ¿Qué significa? | Plantilla §7.5, máximo 3 líneas | `meaning_text` |
| 6 | Pie | Nota técnica primero: "* Descontada la inflación (variación de la UF). Montos en pesos de hoy." Luego: "Fuente: Superintendencia de Pensiones y Banco Central, al {fecha_corte}. Promedio del sistema. Monto de ejemplo. No es una recomendación." | `footer_text`, `cutoff_date` |

Prohibido agregar tarjetas de 12 meses o 5 años, montos en pesos asociados al mes, u otras
cifras. Regla verificada por 6.3-3. (Si en el futuro se quieren 12 meses y 5 años, es un cambio
de especificación, no una decisión de implementación.)

### 7.4 Gráfico

- Una sola curva: `V_t`, 121 puntos de fin de mes, generada por código como path SVG, con área
  degradada bajo la curva que termina exactamente en el último punto.
- Grilla suave: líneas horizontales cada $1.000.000 con rótulo a la izquierda; líneas verticales
  en enero de cada año con el año debajo.
- **Globo inicial** (azul oscuro): "$10.000.000", sobre el punto inicial, con línea punteada al punto.
- **Globo final** (verde): "{V_j}" / "hoy ({r_120m})", sobre el punto final, con línea punteada.
- Los globos se ubican por encima del punto más alto de la curva en su ancho: **nunca tapan la
  curva** (verificado por intersección caja–polilínea). La banda vertical de la curva deja
  espacio arriba para el globo final.
- **Último tramo** (j−1 → j) en rojo si `r_1m < 0`, verde si `> 0`, gris si es 0; el punto final
  con borde del mismo color.
- Prohibido usar modelos generativos para dibujar o completar el gráfico.

### 7.5 Plantillas de "¿Qué significa?"

Principio de dos niveles: **el lector no técnico solo ve cifras y frases simples; el lector técnico
encuentra la metodología en la nota del asterisco.** Por eso el texto no habla de inflación.
Selección determinística por casos (signo de `r_1m` × signo de `r_120m`):

| Mes | 10 años | `meaning_text` |
|---|---|---|
| − | + | "{Mes} fue un mes negativo. Aun así, en 10 años $10.000.000 pasaron a ser {V_j}." |
| + | + | "{Mes} fue un mes positivo. En 10 años, $10.000.000 pasaron a ser {V_j}." |
| − | − | "{Mes} fue un mes negativo. En 10 años, $10.000.000 pasaron a ser {V_j}." |
| + | − | "{Mes} fue un mes positivo. Aun así, en 10 años $10.000.000 pasaron a ser {V_j}." |
| 0 | ± | "En {mes} el fondo no cambió. En 10 años, $10.000.000 pasaron a ser {V_j}." |

Si `r_120m` no está disponible (fondo con menos de 10 años de historia), se usa el horizonte más
largo disponible entre 60 y 12 meses; la tarjeta, el título del gráfico, el globo y la plantilla
se ajustan ("Últimos 5 años", "en 5 años"). Si no hay ni 12 meses, se muestra solo la tarjeta del
mes y el gráfico con los meses disponibles.

Cada caso tiene prueba. Ninguna plantilla predice, recomienda, promete recuperación, minimiza
ni dramatiza. Solo hechos del manifiesto.

### 7.6 Texto de acompañamiento para WhatsApp

≤ 40 palabras. Repite las dos cifras y la explicación en texto (para quien no abre la imagen) y
agrega la fuente con fecha. Mismas reglas y controles (6.3-8 a 6.3-10) que la imagen. Ejemplo:

> "FondoClaro · Fondo C · octubre 2026: −2,0%* en el mes y +48,0%* en 10 años. En 10 años,
> $10.000.000 pasaron a ser $14.800.000. *Descontada la inflación. Fuente: Superintendencia de
> Pensiones y Banco Central."

### 7.8 Imagen resumen "Los 5 fondos"

Referencia: `docs/reference/maqueta_resumen_5_fondos.png`, generada por
`docs/reference/render_resumen.py`. Mismo estilo que la imagen individual.

Contenido, de arriba a abajo:

1. Encabezado FondoClaro con pastilla "{Mes} {año}".
2. Tabla "¿Cómo le fue a cada fondo?" con columnas Fondo · Este mes* · 10 años* · Evolución.
   Una fila por fondo, **siempre en orden A → E**, con la letra en un círculo, "Fondo X" y su
   etiqueta de riesgo (Más riesgoso, Riesgoso, Intermedio, Conservador, Más conservador),
   `r_1m` y `r_120m` con flecha y color por signo, y un minigráfico de 10 años con el último tramo
   coloreado por el signo del mes.
3. Nota de riesgo, fija: "Cada fondo tiene un nivel de riesgo distinto: más riesgo suele
   significar subidas y bajadas más grandes. Esto no es una recomendación para cambiarse."
4. Invitación, fija: "¿Quieres el gráfico de tu fondo cada mes? Respóndeme con tu letra:
   A, B, C, D o E."
5. Pie: nota del asterisco, fuente y fecha, "Promedio del sistema por tipo de fondo. No es una
   recomendación."

Reglas específicas:

- El resumen es un informe propio (`report_id`, hash, aprobación) que **referencia los 5 informes
  individuales del mismo mes**. Solo puede generarse si los 5 están al menos en
  `VISUALLY_VERIFIED`, y cada cifra de la tabla debe ser idéntica a la de su informe individual.
- **Prohibido destacar un fondo**: nada de "mejor fondo", rankings, coronas, negritas o colores
  distintos para el mayor o menor valor, ni ordenar por rentabilidad. El orden es siempre A → E.
- Si un fondo no tiene una métrica, su celda dice "s/d" y la nota al pie lo explica; el resumen
  no se bloquea por eso, pero sí si falta `r_1m` de algún fondo.
- Pruebas: cifras = informes individuales; orden A → E; ningún destaque; nota de riesgo e
  invitación presentes; minigráficos coherentes con el signo del mes.

### 7.9 Envío (manual en v1)

El envío lo hace una persona desde la app WhatsApp Business con **listas de difusión**. El sistema
nunca envía mensajes. Lo que hace es preparar un **paquete de envío** mensual con las imágenes
aprobadas:

```
outputs/envio_YYYY-MM/
  00_resumen_5_fondos.png   + 00_resumen.txt
  fondo_A.png ... fondo_E.png + fondo_X.txt
  LEEME.txt                 # checklist de envío (abajo)
```

`python -m fondoclaro send-package --period YYYY-MM` arma la carpeta solo con informes en
`APPROVED_FOR_PUBLICATION`; si falta alguno, lo dice y no lo incluye.

Checklist de `LEEME.txt`:

1. Primer mes: enviar `00_resumen_5_fondos.png` a todas las listas. A quienes respondan con
   una letra, agregarlos a la lista de ese fondo ("FondoClaro A", …, "FondoClaro E").
2. Meses siguientes: a cada lista, la imagen de su fondo; el resumen se puede seguir enviando a
   quienes no han elegido fondo.
3. Las listas de difusión solo llegan a quien tiene guardado el número y admiten hasta 256
   contactos por lista; si una lista se llena, crear "FondoClaro C 2".
4. Si alguien pide no recibir más, sacarlo de la lista ese mismo día.
5. No usar extensiones ni programas no oficiales de envío masivo: violan las condiciones de
   WhatsApp y pueden hacer que bloqueen el número.
6. Después de enviar: `python -m fondoclaro mark-published --report-id ID --url "difusión
   manual YYYY-MM-DD"` para cada imagen enviada.

El sistema **no guarda teléfonos, nombres ni qué fondo tiene cada persona**: esas listas viven
solo en la app de WhatsApp. Así el repositorio no contiene datos personales.

### 7.7 Lenguaje prohibido (lista inicial, configurable)

"perdiste", "ganaste", "tu pensión", "aproximad", "recuperará", "se recuperará", "no te preocupes",
"tranquilo", "desplome", "catástrofe", "te conviene", "cámbiate", "deberías", "mejor AFP",
"peor AFP", "garantiza" (salvo en "no garantizan"), cualquier nombre de AFP.

Jerga técnica ("real", "nominal", "deflactad", "inflación", "UF", "IPC", "rentabilidad",
"poder adquisitivo", "anualizad", "volatilidad") **solo puede aparecer en la nota del asterisco**
del pie. En tarjetas, título del gráfico, globos y "¿Qué significa?" está prohibida.

---

## 8. VERIFICACIÓN DE LO RENDERIZADO

No basta con el JSON: se verifica lo que el lector verá.

1. **Textos**: la plantilla SVG solo recibe strings del manifiesto. Antes de rasterizar, se
   parsea el SVG final y se extraen todos los nodos `<text>`/`<tspan>`; el conjunto de cifras
   extraídas debe ser igual al del manifiesto (ni sobran ni faltan).
2. **Gráfico**: se parsean los paths del gráfico, se invierte la escala y se comparan los 121
   puntos con `chart_series` (tolerancia: medio píxel en unidades de datos). Se verifican las
   invariantes 6.3-4, 6.3-6 y 6.3-7.
3. **Desbordes y superposición**: medir cada texto con las métricas de la fuente incluida y
   verificar que cabe en su caja; verificar que ninguna caja de texto se superpone con otra
   **ni con la línea del gráfico** (intersección de la caja con la polilínea).
   Verificar que el área rellena no excede el dominio X de la línea (E7).
4. **Espacios**: en SVG, los espacios al final de un `<tspan>` se pierden si no se usa
   `xml:space="preserve"` ("negativo:−2,0%", "a$14.800.000"; ocurrió en la maqueta). El texto
   extraído del SVG final debe coincidir con el manifiesto **incluyendo espacios**, y además se
   verifica sobre el PNG que entre cada tramo haya un hueco horizontal ≥ 0,2 em.
5. **Raster**: PNG con renderizador determinístico (resvg o cairosvg con versión fijada).
   Prueba de snapshot con tolerancia de píxeles para detectar cambios no intencionales.
6. **Revisión visual**: la maqueta pasó todos los chequeos numéricos y aun así tenía 3 problemas
   visibles (espacios perdidos, etiquetas sobre la curva). Por eso `approve` siempre muestra el PNG final al humano, y el paquete de auditoría
   lo incluye.
7. **OCR**: opcional y solo como control complementario; nunca como único control.

---

## 9. ESTADOS, APROBACIÓN Y CLI

### 9.1 Estados

```
PENDING → DATA_COLLECTED → DATA_VALIDATED → CALCULATED → NUMERICALLY_VERIFIED
→ CONTENT_GENERATED → VISUAL_GENERATED → VISUALLY_VERIFIED → HUMAN_REVIEW_PENDING
→ APPROVED_FOR_PUBLICATION → MARKED_PUBLISHED
```

Estados laterales: `BLOCKED` (con motivo y etapa, terminal para ese informe),
`SUPERSEDED` (reemplazado por un informe nuevo).
Estado de auditoría externa, independiente del flujo: `NOT_REQUESTED | PACKAGE_EXPORTED |
RESULT_IMPORTED_PASS | RESULT_IMPORTED_FINDINGS | RESULT_INVALID`.

Toda transición se registra (timestamp, etapa, versión de código, hash de entradas y salidas).
Transiciones inválidas lanzan error y tienen prueba.

### 9.2 Aprobación

- La aprobación se liga a `content_hash = SHA-256(manifiesto + texto WhatsApp + PNG + hashes de datos + git SHA)`.
- Si cualquier componente cambia, el hash cambia y la aprobación no aplica: se crea un informe nuevo.
- `approve` muestra: imagen, resumen de cifras, fuentes y fecha de corte, resultado de todas las
  validaciones, estado de auditoría externa, advertencias (p. ej. `SP_NO_PUBLICADO_AUN`).
- Exige escribir el `report_id` para confirmar. Si no hay auditoría externa con resultado válido,
  exige además el flag `--sin-auditoria-externa`.
- Registra el usuario del sistema operativo y `git config user.name` declarando que **no son identidad autenticada**.
- `mark-published --report-id ID --url URL` solo acepta informes aprobados y guarda la evidencia entregada.

### 9.3 Comandos

```
python -m fondoclaro fetch      [--source sp|bcch|all]
python -m fondoclaro run        --fund {A..E|all} --period {latest|YYYY-MM}
python -m fondoclaro validate   --report-id ID
python -m fondoclaro status     --report-id ID
python -m fondoclaro export     --report-id ID          # paquete de auditoría
python -m fondoclaro import-audit --report-id ID --path DIR
python -m fondoclaro approve    --report-id ID [--sin-auditoria-externa]
python -m fondoclaro mark-published --report-id ID --url URL
python -m fondoclaro send-package --period YYYY-MM
python -m fondoclaro bot             # servidor del webhook (§9.5)
python -m fondoclaro monthly         # ciclo mensual automático (§9.5)
```

`run` nunca aprueba ni publica. Ejecutar el pipeline no equivale a autorizar nada.

`--fund all` genera los 5 informes del mes (uno por fondo, cada uno con su propio `report_id`,
hash y validaciones), el informe resumen "Los 5 fondos" (§7.8) y una vista de revisión conjunta. Cada imagen se aprueba por separado;
si un fondo queda `BLOCKED`, los otros no se ven afectados.

### 9.4 Catálogo de imágenes aprobadas

`reports/approved_index.json` lista, por (mes, fondo), el `report_id`, la ruta del PNG, el texto
de WhatsApp y el `content_hash` de lo aprobado. Es la **única** fuente que puede leer cualquier
canal de distribución futuro (p. ej. un bot de WhatsApp). Ningún canal genera imágenes ni cifras
bajo demanda: solo entrega imágenes ya aprobadas. Antes de entregar, el canal verifica que el
hash del PNG coincide con el del índice.

### 9.5 Bot de WhatsApp (API oficial de WhatsApp Cloud, solo respuestas)

Objetivo: que cualquier persona le escriba al número de FondoClaro su letra y reciba, al
instante y sin costo, la imagen aprobada más reciente de su fondo.

**Cómo funciona**

1. Meta envía cada mensaje recibido a un webhook HTTPS del sistema (`POST /webhook`).
2. El bot interpreta el texto:
   - `A`…`E` (también "fondo c", "c ", minúsculas): responde con la imagen aprobada más
     reciente de ese fondo desde `approved_index.json` (§9.4) y su texto de §7.6 como pie.
   - `5`, `todos` o `resumen`: responde con la imagen resumen de los 5 fondos.
   - Cualquier otra cosa: mensaje de bienvenida con botones de respuesta A–E y la frase
     "¿No sabes tu fondo? Aparece en la cartola o en la app de tu AFP."
   - `baja`: responde "Listo, no te escribiremos." (el bot nunca escribe primero, pero se
     respeta la palabra).
3. Antes de enviar, verifica que el hash del PNG coincide con el del índice. Si no hay imagen
   aprobada, responde "Estamos preparando las cifras de este mes" y no envía nada más.

**Comandos del dueño** (solo desde el número en `OWNER_PHONE`; cualquier otro número que los
escriba recibe la bienvenida normal):

- `revisar`: el bot envía las imágenes del mes en `HUMAN_REVIEW_PENDING` con su `report_id`.
- `aprobar`: aprueba todas las imágenes pendientes del mes mostradas por `revisar` (cada una
  queda ligada a su `content_hash`, como en §9.2). Si algo cambió desde `revisar`, rechaza.
- `estado`: qué mes está entregando el bot y qué hay pendiente.

**Ciclo mensual automático**

- Tarea programada (`python -m fondoclaro monthly`) que corre a diario desde el día 5 de cada
  mes: si la Superintendencia ya publicó el mes cerrado, ejecuta `run --fund all`, y si todo
  queda en `HUMAN_REVIEW_PENDING`, avisa al dueño. Si algo queda `BLOCKED`, avisa el motivo.
- El aviso al dueño se hace por correo o, si el dueño escribió al bot en las últimas 24 horas,
  por WhatsApp. **No usar plantillas pagadas.**
- Hasta que el dueño apruebe, el bot sigue entregando el mes anterior.

**Configuración** (`.env`, nunca en git; agregar `.env` a `.gitignore` y un `.env.example`):

```
WHATSAPP_TOKEN=            # token de acceso de Meta
WHATSAPP_PHONE_NUMBER_ID=  # ID del número (no el número)
WHATSAPP_VERIFY_TOKEN=     # texto secreto elegido por el dueño para verificar el webhook
WHATSAPP_APP_SECRET=       # para validar la firma X-Hub-Signature-256 de cada llamada
OWNER_PHONE=               # número del dueño, formato 569XXXXXXXX
```

**Reglas**

- Validar la firma de cada llamada de Meta con `WHATSAPP_APP_SECRET`; rechazar las que no
  coincidan.
- Responder solo mensajes recibidos en las últimas 24 horas (ventana de servicio gratuita).
  Prohibido usar mensajes de plantilla o iniciar conversaciones.
- **No guardar números de teléfono ni contenido de mensajes.** Los registros muestran el número
  enmascarado (`569****5678`) y solo el tipo de pedido ("fondo C", "bienvenida").
- Responder al webhook con 200 en menos de 5 segundos y procesar el envío después, para que
  Meta no reintente y duplique respuestas; ignorar IDs de mensaje ya procesados.
- Implementación: FastAPI + `httpx` (o la biblioteca `pywa`), subir la imagen con el endpoint
  de medios y responder con un mensaje de tipo imagen.

**Pruebas**

- Unitarias con payloads de webhook de ejemplo: cada letra, variantes de escritura, mensaje
  desconocido, comandos del dueño desde otro número (deben ignorarse), firma inválida,
  mensaje duplicado, sin imagen aprobada, hash que no coincide.
- Ninguna prueba llama a Meta: el cliente de WhatsApp se reemplaza por uno falso.
- Prueba manual documentada en `docs/BOT_PRUEBA.md` (abajo).

**`docs/BOT_PRUEBA.md`** debe explicar, para alguien no técnico:

1. Crear la app en developers.facebook.com con el producto WhatsApp y copiar el token y el
   Phone Number ID del número de prueba.
2. Agregar su propio número como destinatario de prueba.
3. Llenar `.env`.
4. Levantar el bot en el PC (`python -m fondoclaro bot`) y exponerlo con un túnel gratuito
   (`cloudflared tunnel --url http://localhost:8000`).
5. Pegar la URL del túnel + `/webhook` y el `WHATSAPP_VERIFY_TOKEN` en Meta → WhatsApp →
   Configuración, y suscribirse al campo `messages`.
6. Escribir "C" al número de prueba desde el celular y recibir la imagen.

**Despliegue** (después de que la prueba funcione): documentar en `docs/DESPLIEGUE.md` cómo
dejar el bot y la tarea mensual en un servidor que esté prendido siempre, con la opción gratuita
o más barata disponible al momento, y cómo pasar del número de prueba a un número real con
nombre visible "FondoClaro".

---

## 10. AUDITORÍA EXTERNA (CLAUDE U OTRO REVISOR)

El sistema no invoca a ningún modelo. Exporta un paquete que un humano entrega al auditor.

```
audit_packages/<report_id>/
  package_manifest.json     # lista de archivos con SHA-256 y package_hash
  source_manifest.json      # fuentes, URLs, fechas, hashes raw
  financial_results.json    # métricas sin redondear y formateadas
  calculations.json         # pasos intermedios (I_t, ventanas, bases)
  validation_results.json   # resultado de §6 y §8
  render_manifest.json      # textos y cifras visibles
  infographic.png
  whatsapp_text.txt
  methodology.md
  audit_instructions.md     # qué revisar y esquema exacto de salida
  audit_results.schema.json
```

El auditor devuelve `audit_results.json` y `AUDIT_REPORT.md`. `import-audit` valida:

- Esquema JSON (campos: report_id, package_hash, data_version, code_version, run_id,
  auditor {nombre, versión si se conoce}, fecha, status `PASS|FINDINGS|INCONCLUSIVE`,
  findings[] {severidad, categoría, descripción, evidencia, archivo}, limitaciones).
- Que `package_hash` y `report_id` coincidan exactamente con el paquete exportado.
- Si no coinciden o el esquema falla: `RESULT_INVALID`.

Documenta que esto da **trazabilidad, no prueba** de que la revisión ocurrió.
Un archivo que diga PASS no aprueba nada: solo informa al humano en `approve`.
Hallazgos de severidad alta deben mostrarse en rojo en `approve` y requerir confirmación adicional.

---

## 11. VERSIONADO Y REPRODUCIBILIDAD

Cada informe guarda: `report_id`, `run_id`, fecha/hora de generación, mes de corte, fondo,
fuentes y hashes raw, git SHA (y si el árbol estaba sucio, bloquear `run` salvo `--dev`),
parámetros, versiones de dependencias, resultados, imagen, estados.

Los informes son inmutables. Corregir algo = nuevo informe con `supersedes: <report_id>`;
la aprobación nunca se hereda. Una revisión de datos oficiales genera un registro de revisión
y no altera informes existentes. Prueba: regenerar un informe desde su registro produce un
manifiesto idéntico y un PNG idéntico byte a byte (o con diferencia nula de píxeles).

El ciclo "corregir y reauditar" es **trabajo de desarrollo** (commit nuevo → informe nuevo),
nunca algo que el pipeline haga solo en tiempo de ejecución.

---

## 12. PRUEBAS

Unitarias y de integración, todas offline:

- Fórmulas: positivo, negativo, cero, deflación (UF que baja), 1 mes, 120 meses.
- Prueba dorada vs SP (§6.1). Recálculo independiente (§6.2).
- Propiedad de redondeo de §5.4.
- Datos: duplicados, huecos, meses faltantes, archivo con columnas cambiadas, revisión de un valor histórico.
- Disponibilidad: fondo con menos de 120 meses → métrica s/d, gráfico acortado.
- Contenido: los 5 casos de plantilla, horizonte reducido (60/12 meses), frases prohibidas, números ⊆ manifiesto, cifras extra rechazadas, globos que no tapan la curva.
- Regresión E1–E11 (§6.4).
- Render: textos SVG = manifiesto, gráfico = datos, desbordes, snapshot.
- Estados: transiciones válidas e inválidas, aprobación invalidada por cambio,
  intento de `mark-published` sin aprobación, `approve` sin flag cuando no hay auditoría.
- Auditoría: import válido, hash distinto, esquema roto, PASS sin paquete.
- E2E: `run` con fixtures → `HUMAN_REVIEW_PENDING` con PNG y paquete; `run` con fuente caída → `BLOCKED`.

---

## 13. FUERA DE ALCANCE V1 (NO IMPLEMENTAR)

Agente investigador económico · redacción con LLM · Instagram/Facebook/LinkedIn/TikTok ·
AFP individuales y comparaciones entre AFP · Fondos Generacionales · publicación automática ·
cualquier recomendación o proyección.

Fases siguientes previstas (solo para que la arquitectura no las impida):
- v2: envío mensual automático a suscriptores (mensajes de plantilla pagados, con
  consentimiento explícito y baja en un mensaje; requiere guardar teléfono y fondo, por lo que
  aplica la Ley 21.719 de datos personales). Otros formatos de redes y redacción asistida por
  LLM con los mismos controles de §6.3.
- v3: Fondos Generacionales (desde abril 2027): el bot pregunta el año de nacimiento en vez de
  la letra del fondo; investigador con fuentes curadas.

---

## 14. CRITERIOS DE ACEPTACIÓN (DEFINICIÓN DE TERMINADO)

1. `pip install -e .` y `pytest` pasan offline en un clon limpio.
2. Prueba dorada vs SP pasa para ≥ 24 meses × 5 fondos.
3. `python -m fondoclaro run --fund C --period <mes con fixtures>` produce PNG 1080×1350,
   texto WhatsApp, manifiesto y paquete de auditoría, y queda en `HUMAN_REVIEW_PENDING`.
   `--fund all` produce además el resumen de 5 fondos; `send-package` arma la carpeta de envío
   solo con lo aprobado.
9. El bot de §9.5 pasa sus pruebas sin conectarse a Meta, y `docs/BOT_PRUEBA.md` permite a una
   persona no técnica hacer la prueba real con el número de prueba de Meta.
4. El PNG respeta el contrato de §7 (dos cifras, un gráfico, una explicación, un pie) y pasa §8.
5. Las 11 pruebas de regresión E1–E11 fallan como se espera.
6. `approve` y `mark-published` respetan §9.2.
7. `docs/FUENTES.md`, `docs/METODOLOGIA.md`, `docs/DECISIONES.md` y `docs/BLOQUEOS.md` existen y están al día.
8. README con instalación, uso y limitaciones.

---

## 15. CUÁNDO DETENERSE Y QUÉ REPORTAR

Detente y reporta en vez de improvisar si:

- No puedes acceder a las fuentes oficiales ni hay fixtures reales.
- La prueba dorada no pasa.
- SP no publica lo que esta especificación asume (p. ej. la serie del sistema) y no hay método oficial documentado.
- Una decisión de §2 resulta inviable.

Informe final (en `docs/INFORME_TECNICO.md` y en tu respuesta):

1. Qué quedó implementado y probado (con salida real de `pytest`).
2. Qué quedó parcial o no implementado, y por qué.
3. Bloqueos y qué necesitas del humano.
4. Desviaciones de esta especificación y su justificación.
5. Ruta del PNG generado con datos reales, si se pudo generar.
