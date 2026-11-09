# Informe técnico — fase de datos y primera prueba dorada

8 de noviembre de 2026. **Detenido en fase 2 por §15: la prueba dorada falla.**
No se inició fase 3 ni fase 4; no se declara terminada la V1.

## Especificación y referencias

Se leyó la especificación recibida en `fondoclaro_spec_v1(1).zip` (773 líneas,
43.092 bytes) y se actualizaron `docs/FONDOCLARO_SPEC_V1.md` y la copia extraída.
Contiene §9.5 con bot, comandos del dueño y monthly. Se revisaron los scripts e
imágenes de `docs/reference/`; las cinco referencias son idénticas a las del nuevo zip.

## Fase 1 realizada

52 archivos oficiales archivados, con URL/petición, fecha y SHA-256: 5 páginas SP,
5 CSV A–E desde 2014, 13 tablas anuales SII UF, 24 publicaciones de rentabilidades
SP y 5 recursos metodológicos. Inventario: `raw_data/history_manifest.json`.
Se conservaron copias con los mismos hashes bajo `tests/fixtures/official_history/`.

Los cinco CSV contienen 153.720 observaciones fecha/AFP en total, incluidas las
provisionales. Hay 154 cierres mensuales por fondo, enero 2014–octubre 2026. El
corte confirmado común es **31-oct-2026**. La UF aporta 4.696 días, incluidos
valores anticipados del mes abierto; solo se usan cierres hasta octubre. El SII
sustituye al acceso BCCh autenticado por autorización expresa del usuario.

Se extendió el lector a bloques repetidos, cambios de AFP y estado provisional.
Se añadieron lector de matriz anual SII, lector de todos los valores publicados
por AFP y SISTEMA, recolector reproducible de historia e integridad de sus archivos.
Las pruebas de esos lectores son offline con los archivos oficiales completos.
Véase `docs/FUENTES.md` para formato, columnas, frecuencia y ejemplos.

## Fase 2: método fijado y resultado real

Se documentó antes de contrastar el promedio de retornos por patrimonio anterior
(SP Circular 2268 / informe junio 2025, nota 8). Para alimentar el motor existente
se construyó un índice nominal encadenando factores mensuales, deflactado una sola
vez por el motor. El índice es calculado, no una cuota oficial publicada.
Las fórmulas del motor, datos y tolerancia permanecen sin cambios.

Períodos comparados: **noviembre 2024 a octubre 2026**, A, B, C, D, E. Total:
**240 comparaciones** = 24 meses × 5 fondos × (mes y 12 meses).

| Métrica | Comparaciones | Fallos | Diferencia máxima (pp) |
| --- | ---: | ---: | ---: |
| Mes | 120 | 0 | 0,0049573561502499068 |
| 12 meses | 120 | 5 | 0,0131710012791798464 |

| Fondo / mes | Horizonte | Calculado (%) | SP (%) | Diferencia (pp) |
| --- | --- | ---: | ---: | ---: |
| A / mayo 2025 | 12 meses | 7,060071709532255 | 7,05 | 0,010071709532255 |
| A / octubre 2026 | 12 meses | 8,419687990294226 | 8,43 | 0,010312009705774 |
| B / diciembre 2024 | 12 meses | 7,426828998720820 | 7,44 | 0,013171001279180 |
| B / enero 2025 | 12 meses | 8,379450749080966 | 8,39 | 0,010549250919034 |
| C / julio 2025 | 12 meses | 7,829209598738904 | 7,84 | 0,010790401261096 |

Tolerancia: **0,01 pp**, sin cambios. La evidencia exacta sin redondear está en
[`GOLDEN_RESULT.json`](GOLDEN_RESULT.json), copia del primer resultado de
`reports/golden_validation/result.json`. No se normalizaron los datos para aprobar.

El diagnóstico calculado desde el comienzo con promedio directo por horizonte
permanece dentro de tolerancia en las 240 comparaciones (máximo 0,00495735615025 pp).
Esto señala una diferencia entre promedio de retornos por horizonte e índice
mensual encadenado. **No se reemplazó la fórmula del motor después del fallo.**

Se descargaron también promedios anuales desde 2002/origen en los 24 HTML y PDFs
con 36/60 meses. No se declara validación completa de esas anualizadas. La historia
2014–2026 no cubre desde 2002 y, además, se activó la parada por el fallo de 12 meses.
La normativa SP muestra anualización 365/días y el motor conserva 12/n según §5.1.

## Redondeo: explicación exacta y cumplimiento

Antes se añadió `example_amount`: porcentaje visible = ROUND_HALF_UP(r × 100,
1 decimal); monto visible = 10.000.000 × (1 + porcentaje visible / 100). No se cambió
r, el monto exacto ni la serie del gráfico. Globo, explicación y WhatsApp utilizan
el mismo monto visible; el manifiesto conserva `raw_final_amount`,
`displayed_final_amount` y `amount_rounding_policy`.

El usuario autorizó ese cambio en la conversación anterior para que las cifras
visibles cuadren. **No puedo confirmar cumplimiento literal de §5.4 tal como quedó
en el nuevo archivo**: esa sección pide redondear independientemente el monto
exacto con HALF_UP y afirma una igualdad que falla en empates negativos.

Contraejemplo: r exacto −0,05%; porcentaje visible −0,1%; monto exacto 9.995.000.
HALF_UP del monto al múltiplo de 10.000 da 10.000.000; el monto coherente con −0,1%
es 9.990.000. La política autorizada cumple la coherencia visible, pero requiere
ser incorporada expresamente en el texto de §5.4 para declarar conformidad literal.
Este formato no interviene en el fallo dorado, que compara retornos sin redondear.

## Salida completa de pruebas

Comando: `.venv/bin/pytest -q --tb=short`.

```text
1 failed, 139 passed in 3.78s
```

Salida completa real: [`PYTEST.txt`](PYTEST.txt), incluyendo el fallo y sus valores.
La prueba dorada antes omitida fue reemplazada por una prueba real que recalcula
los archivos oficiales: no está marcada SKIP ni XFAIL. Las 139 pruebas restantes
pasan. No se ocultó el fallo para obtener una suite verde.

## Pendiente y acciones del humano

1. Revisar con el responsable de metodología el vínculo entre el promedio SP por
   horizonte y el índice de §5; resolver documentalmente antes de retomar. No
   hace falta entregar de nuevo los CSV ni UF ya descargados.
2. Incorporar en §5.4 la política de presentación previamente autorizada, si se
   mantiene la exigencia de cifras visibles que cuadren exactamente.
3. Para una ejecución real de producción, disponer de un checkout Git válido y
   limpio: el `.git` de este workspace no es operativo. No se lo modificó.
4. **Todavía no hay seis imágenes para aprobar ni pasos en Meta que ejecutar.**
   La fase 3 (pipeline/PNG/resumen completos) y la fase 4 (bot, monthly, cliente
   falso, BOT_PRUEBA.md y DESPLIEGUE.md) no se iniciaron por la parada obligatoria.
   Su implementación no se declara hecha ni probada.

No se generó ningún PNG con datos reales: no hay rutas de seis imágenes que se
puedan entregar honestamente. Los PNG antiguos de pruebas unitarias sintéticas
no son informes de este mes. No hubo aprobación, auditoría externa, publicación,
conexión a Meta ni mensajes reales. Bloqueos detallados: [`BLOQUEOS.md`](BLOQUEOS.md).
