# Prompt para Codex — objetivo: seis imágenes de octubre 2026 listas para enviar

Reemplaza la versión anterior de este archivo, que estaba ordenada como auditoría y dejaba
el proyecto detenido. Daymler decidió priorizar que el sistema funcione.

Antes de pegarlo: haz tú estos dos comandos en `/home/daymler/fondoclaro` (Codex tiene
prohibido tocar `.git`, y sin repositorio `approve` falla con `DEV_REPORT_NOT_APPROVABLE`):

```
git init && git add -A && git commit -m "Estado previo a la corrección de metodología"
```

---

```
DECISIÓN TOMADA POR DAYMLER (2026-11-08)

Se levanta la parada de §15. El objetivo de este ciclo es tener las seis imágenes de
octubre 2026 (fondos A a E más el resumen) en HUMAN_REVIEW_PENDING, para que Daymler las
revise y las envíe. Todo lo que no sirva a eso queda para después.

Se adopta la opción (a) de la supervisión: el método de cálculo del SISTEMA pasa a ser el
de la Superintendencia. Daymler te AUTORIZA EXPRESAMENTE a modificar §5.1, §5.2, §5.3,
§6.1 y §6.2 de FONDOCLARO_SPEC_V1.md para dejarlo escrito, y a registrarlo en
docs/DECISIONES.md. Esta es la única autorización para tocar la especificación: no cambies
nada más de ella, y sigue sin poder aflojar tolerancias ni ajustar datos.

1. MÉTODO DEL SISTEMA

La rentabilidad real del SISTEMA en un horizonte es el promedio de las rentabilidades
reales de cada AFP en ESE MISMO horizonte, ponderado por el PATRIMONIO DEL MES ANTERIOR AL
MES DE CORTE (j-1):

    r_a(i,j) = (VC_a,j / VC_a,i) × (UF_i / UF_j) − 1        para cada AFP a
    r_sistema(i,j) = Σ_a w_a × r_a(i,j),  con w_a ∝ patrimonio_a del mes j−1
    i = mes anterior al primero del período, j = mes de corte

Esto no lo inventes ni lo re-derives: la supervisión lo demostró contra las 240 celdas
publicadas por la SP (24 meses × 5 fondos × 2 horizontes). Residuo máximo 0,004957 pp, por
debajo del límite de 0,005 pp que explica el redondeo a 2 decimales de la SP. Es la única
de seis hipótesis compatible. El índice encadenado actual de §5.1 falla 5 celdas con
máximo 0,013171 pp. La evidencia y los scripts están en docs/supervision/.

Puedes comprobarlo en un minuto antes de implementar:
    python3 -I docs/supervision/scripts/weighting_variants.py

2. LA CURVA DEL GRÁFICO

Como la cifra del sistema por horizonte ya no sale de un índice único, define la serie del
gráfico de forma explícita, por el mismo método:

    V_t = 10.000.000 × (1 + r_sistema(j−120, t))        para t = j−120 … j

Así el último punto es exactamente V_j = 10.000.000 × (1 + r_120m) y §6.3-4 se conserva
por construcción. Ojo: el signo del último tramo deja de ser idénticamente el signo de
r_1m, porque las ponderaciones difieren. §6.3-6 pasa de ser una identidad a ser una
validación que puede fallar en un mes de signo casi nulo; si falla, el informe se bloquea
como corresponde, no lo relajes. Deja esto escrito en §5.3 y en §6.3-6.

3. PRUEBA DORADA

Debe pasar en los niveles de mes y 12 meses, 240 comparaciones, con la tolerancia de §6.1
SIN modificar (0,01 pp).

El nivel de promedios anuales queda FUERA DE ALCANCE en este ciclo, por decisión de
Daymler: la SP los publica desde el 27-sep-2002 (y jul-1981 para C y E) y la historia
descargada parte en 2014. Déjalo escrito así en §6.1 y en docs/BLOQUEOS.md, con la nota de
que es subsanable descargando desde 2002 (la URL que ya usas acepta aaaaini=2002) y que se
hará más adelante. No lo declares validado.

Consecuencia que debes dejar dicha con todas sus letras en docs/INFORME_TECNICO.md: la
cifra grande de la imagen, r_120m, se calcula con el mismo método validado en los
horizontes de 1 y 12 meses, pero NO se contrasta contra ninguna cifra publicada por la SP,
porque la SP no publica acumulados a 10 años.

4. DOS ARREGLOS QUE SE VEN EN LA IMAGEN

4.1 El último tramo del gráfico es invisible. Con 121 puntos mide 6,67 px de ancho, y el
    círculo del punto final (r=7 más borde 4, radio efectivo ~9 px) lo tapa entero:
      <path id="chart-last" d="M998.333333,647.734690 L1005.000000,658.779997"
            stroke="#b52323" stroke-width="6"/>
      <circle cx="1005.000000" cy="658.779997" r="7" fill="white"
              stroke="#b52323" stroke-width="4"/>
    El lector ve la curva azul subiendo junto a una tarjeta que dice −2,0 %: es el error E2
    que §6.4 obliga a detectar. Colorea los últimos 3 a 6 meses en vez de uno solo, y/o
    achica el círculo y dibújalo bajo la línea. Es un cambio de dibujo: no toques la serie.
    Aceptación: una prueba que rasterice un caso con r_1m < 0 y verifique sobre el PNG que
    quedan píxeles del color del tramo visibles FUERA del disco del punto final. Comprueba
    que falla con el dibujo actual antes de corregir.

4.2 El texto de WhatsApp usa fecha ISO y no nombra el mes. templates.py:36 produce
    "al 2026-10-31" mientras el pie de la imagen dice "al 31-oct-2026"; y templates.py:35
    queda como "FondoClaro · Fondo C: −2,0%* mensual; …", sin decir de qué mes habla, que
    es justo lo que necesita quien no abre la imagen. Usa el formato es-CL del pie e
    incluye "{mes} {año}", respetando el límite de 40 palabras de §7.6.

5. GENERAR LAS IMÁGENES

    python -m fondoclaro run --fund all --period 2026-10

Los seis informes deben quedar en HUMAN_REVIEW_PENDING. No ejecutes approve,
mark-published ni send-package: eso lo hace Daymler.

Al terminar, dile en tu respuesta, en una lista corta:
  - la ruta de cada uno de los seis PNG;
  - para cada fondo, r_1m y r_120m tal como se ven en la imagen;
  - el resultado de la prueba dorada (comparaciones, fallos, diferencia máxima);
  - la salida de pytest.

6. QUEDA PARA DESPUÉS — no lo hagas ahora

Historia desde 2002 para los promedios anuales; prueba de snapshot de §8.5; control raster
de espacios de §8.4; .env en .gitignore y .env.example (antes del bot, no ahora);
defusedxml en las dependencies de pyproject.toml; el espacio vacío del pie de la imagen.
Anótalos en docs/BLOQUEOS.md como pendientes conocidos para que no se pierdan.

7. SI ALGO NO CALZA

Si la prueba dorada no pasa con el método del punto 1, DETENTE y repórtalo con los números
en la mano. No ajustes fórmulas, tolerancias ni datos, y no sigas a los puntos 4 y 5.
```
