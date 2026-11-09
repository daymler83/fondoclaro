# Prompt para Codex — lo único que falta para tener las seis imágenes

Estado verificado por la supervisión tras el commit `978a52a`: git operativo y árbol
limpio, 214 pruebas pasan y falla solo la dorada, fórmulas y tolerancias intactas, historia
oficial desde 2002 con hashes correctos, y los arreglos de imagen y texto confirmados.

Ya no hace falta nada previo. Pega el bloque completo.

---

```
DECISIÓN DE DAYMLER (2026-11-08) — SE LEVANTA LA PARADA DE §15

Verifiqué tu trabajo del commit 978a52a y está correcto: la prueba nueva del tramo final
falla con el dibujo viejo (14 píxeles) y pasa con el nuevo, el tramo rojo ahora se ve y
baja, la fecha de WhatsApp quedó en formato es-CL e incluye el mes, los 58 archivos de la
historia 2002 tienen hashes correctos y las ausencias de los fondos A, B y D antes del
27-sep-2002 están registradas sin inventar historia. No tocaste fórmulas, tolerancias,
la especificación ni los scripts de supervisión.

Falta una sola cosa, y es la que desbloquea todo. El objetivo de este ciclo es tener las
seis imágenes de octubre 2026 (fondos A a E más el resumen) en HUMAN_REVIEW_PENDING.

Se adopta la opción (a) de la supervisión. Daymler te AUTORIZA EXPRESAMENTE a modificar
§5.1, §5.2, §5.3, §6.1 y §6.2 de FONDOCLARO_SPEC_V1.md para dejarlo escrito, y a
registrarlo en docs/DECISIONES.md. Es la única autorización para tocar la especificación:
no cambies nada más de ella, y sigues sin poder aflojar tolerancias ni ajustar datos.

1. MÉTODO DEL SISTEMA

La rentabilidad real del SISTEMA en un horizonte es el promedio de las rentabilidades
reales de cada AFP en ESE MISMO horizonte, ponderado por el PATRIMONIO DEL MES ANTERIOR AL
MES DE CORTE (j−1):

    r_a(i,j) = (VC_a,j / VC_a,i) × (UF_i / UF_j) − 1        para cada AFP a
    r_sistema(i,j) = Σ_a w_a × r_a(i,j),  con w_a ∝ patrimonio_a del mes j−1
    i = mes anterior al primero del período, j = mes de corte

No lo re-derives: la supervisión lo demostró contra las 240 celdas publicadas por la SP.
Residuo máximo 0,004957 pp, bajo el límite de 0,005 pp que explica el redondeo a 2
decimales de la SP, y es la única de seis hipótesis compatible. El índice encadenado actual
falla 5 celdas con máximo 0,013171 pp. Compruébalo en un minuto antes de implementar:

    python3 -I docs/supervision/scripts/weighting_variants.py

2. LA CURVA DEL GRÁFICO

Como la cifra por horizonte ya no sale de un índice único, define la serie explícitamente,
por el mismo método:

    V_t = 10.000.000 × (1 + r_sistema(j−120, t))        para t = j−120 … j

Así el último punto es exactamente V_j = 10.000.000 × (1 + r_120m) y §6.3-4 se conserva por
construcción. El signo del último tramo deja de ser idénticamente el signo de r_1m, porque
las ponderaciones difieren: §6.3-6 pasa de identidad a validación que puede fallar en un
mes de signo casi nulo. Si falla, el informe se bloquea como corresponde; no la relajes.
Deja esto escrito en §5.3 y §6.3-6.

3. PRUEBA DORADA

Bloqueante: mes y 12 meses, 240 comparaciones, con la tolerancia de §6.1 SIN modificar.

Ahora que tienes historia desde 2002, intenta además validar los promedios anuales que
publica la SP (desde el 27-sep-2002, y desde jul-1981 para C y E, donde alcance). Esto NO
es bloqueante en este ciclo, pero reporta el resultado con sus números, porque es la única
evidencia posible de que el método también funciona en horizontes largos: hoy r_120m, que
es la cifra grande de la imagen, no se contrasta contra ninguna cifra publicada, ya que la
SP no publica acumulados a 10 años. Si no alcanza para jul-1981, dilo y sigue.

Actualiza el texto de annualized_status: hoy dice que no hay insumos desde 2014, y eso ya
no es cierto.

4. GENERAR LAS IMÁGENES

    python -m fondoclaro run --fund all --period 2026-10

Los seis informes deben quedar en HUMAN_REVIEW_PENDING. NO ejecutes approve,
mark-published ni send-package: eso lo hace Daymler.

Al terminar, dile en tu respuesta, en una lista corta:
  - la ruta de cada uno de los seis PNG;
  - para cada fondo, r_1m y r_120m tal como se ven en la imagen;
  - el resultado de la prueba dorada: comparaciones, fallos y diferencia máxima;
  - la salida de pytest.

5. QUEDA PARA DESPUÉS — no lo hagas ahora

El control raster de espacios de §8.4 y el bot de §9.5 con su ciclo mensual. Anótalos en
docs/BLOQUEOS.md para que no se pierdan.

6. SI ALGO NO CALZA

Si la prueba dorada no pasa en mes y 12 meses con el método del punto 1, DETENTE y
repórtalo con los números en la mano. No ajustes fórmulas, tolerancias ni datos, y no sigas
a los puntos 3 y 4.
```
