# Bloqueos — actualización del 8-nov-2026

## B1 — Desviación autorizada de redondeo, no cumplimiento literal de §5.4

El usuario autorizó que el monto visible se derive del porcentaje visible. Esto
mantiene coherencia de las dos cifras, pero NO equivale en todos los casos a
redondear independientemente el monto exacto con HALF_UP como escribe §5.4.

Ejemplo: retorno exacto −0,05%; porcentaje visible −0,1%; monto exacto 9.995.000.
HALF_UP independiente al múltiplo de 10.000 produce 10.000.000; la política
autorizada produce 9.990.000. No se alteran el motor ni la serie exacta.

Qué falta del humano: incorporar explícitamente la política autorizada en la
especificación si se pretende afirmar cumplimiento literal. No se debe declarar
que el texto actual y la implementación son equivalentes en ese empate.

## B2 — ACTIVO: falló la prueba dorada real, parada obligatoria §15

Hay datos reales y prueba ejecutada; este bloqueo ya NO se debe a falta de archivos.
Períodos: noviembre 2024–octubre 2026; A–E; mes y 12 meses: 240 comparaciones.

- Mes: 120/120 pasan; máxima diferencia 0,0049573561502499068 pp.
- 12 meses: 115/120 pasan, 5 fallan.
- Máxima diferencia: 0,0131710012791798464 pp, fondo B, diciembre 2024, 12 meses.
- Tolerancia conservada sin cambios: 0,01 pp.

Casos que fallan: A/mayo-2025, A/octubre-2026, B/diciembre-2024,
B/enero-2025 y C/julio-2025, todos en 12 meses.

Motivo observado: el promedio ponderado del retorno de un horizonte no es, en
general, igual al producto de promedios mensuales con ponderaciones variables.
El índice encadenado que se entrega al motor reproduce los meses, pero no todos
los 12 meses dentro de la tolerancia. Como diagnóstico prefijado, el promedio por
horizonte con pesos del mes anterior queda dentro de 0,01 pp en las 240 celdas;
no se utilizó para reemplazar el motor tras observar el fallo.

Qué se necesita del humano: resolver/revisar documentalmente con el responsable
financiero el contrato entre la métrica del sistema por horizonte y la curva
encadenada de §5. No se propone aflojar tolerancias ni cambiar datos. Solo después
de resolver la metodología puede retomarse desarrollo y validación.

Evidencia: `docs/GOLDEN_RESULT.json`, `reports/golden_validation/result.json` y
`docs/PYTEST.txt`. Los promedios anuales publicados están descargados, pero su
validación integral no se alcanzó: la parada ocurrió con el fallo de 12 meses.

## B3 — RESUELTO: datos oficiales y UF histórica

Se descargaron CSV completos A–E de 2014 a 2026, UF SII anual de 2014 a 2026,
24 publicaciones SP y recursos metodológicos. Hay SHA-256 y copias oficiales
congeladas para pruebas offline. El uso del SII fue autorizado por el usuario.
No se necesitan credenciales BCCh ni archivos del humano para esos períodos.

## B4 — Fases 3 y 4 no iniciadas por parada de §15

No se generaron los seis PNG reales ni informes HUMAN_REVIEW_PENDING. No se
implementaron el bot, monthly, su cliente falso ni BOT_PRUEBA.md en esta fase:
el usuario ordenó las fases secuencialmente y detenerse si falla la prueba dorada.
Los módulos y CLI anteriores permanecen parciales y no constituyen la V1 completa.
No hay imágenes para revisar/aprobar ni una prueba Meta que deba ejecutar el humano.

## B5 — RESUELTO: Git operativo

Daymler habilitó el repositorio. Commit inicial:
`d1e1b2fdaa0380a2a611b95625a641522eea549e`. Una ejecución sin --dev registró ese SHA,
`dirty=false`, `dev=false` y estado BLOCKED por metodología, sin UNVERSIONED.
Los informes anteriores permanecen intactos. No se modificó configuración global.

## B6 — Datos desde 2002 preparados; nivel C espera definición escrita

Hay inventario extendido raw y fixture, 63 archivos con hashes iguales, cinco
CSV A–E, UF anual 2002–2026 y registro de ausencias. A/B/D no están activos antes
del 27-sep-2002: se preservan las filas de preapertura sin usarlas como historia
activa. No se rellenaron enero–julio ni se interpolaron valores.

Qué falta: la decisión de Daymler del punto 4 y la actualización escrita de
§5.1–§5.3, §6.1 y §6.2. No se declara nivel C validado por tener los archivos.
Las columnas desde origen anteriores a 2002 siguen sin insumos en este rango:
C desde 1981 y E desde mayo-2000 según los encabezados SP. La referencia de la
supervisión a 1981 para ambos fondos no se tomó como dato ni se editó su evidencia.

## B7 — Control raster de espacios de §8.4 pendiente

Se evita el fallo original rechazando tspan y usando nodos completos con espacios
preservados y contornos de la misma fuente incluida. Aún no se comprueba el hueco
mínimo 0,2 em sobre el PNG. El snapshot ya existe y detecta un desplazamiento de
1 px, pero no sustituye esa medición de espacios. Véase DECISIONES.md #8.

## Observación sobre un script de supervisión — no modificado

`docs/supervision/scripts/verify_hashes.py` termina con `sys.exit(0)` incluso si
su contador de problemas fuera mayor que cero. Su salida de esta ejecución sí
muestra todos los hashes coincidentes; el código de salida por sí solo no debe
usarse como prueba de integridad. Las pruebas del proyecto hacen asserts sobre
los hashes originales y extendidos. Se registra la observación en lugar de
modificar el script independiente, como exige el encargo.
