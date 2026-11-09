# Fuentes oficiales reales — 8 de noviembre de 2026

La fase 1 terminó con 52 archivos: cinco páginas SP que fijan la fecha de
confirmación, cinco CSV históricos A–E, trece tablas anuales UF SII, 24 publicaciones
mensuales SP y cinco documentos/recursos de metodología. Todos se conservaron sin
modificar sus bytes y con SHA-256 en `raw_data/<fuente>/<fecha>/<identificador>/`.

Inventario íntegro, con URL exacta, método HTTP, parámetros POST cuando corresponde,
fecha de descarga, ruta y SHA-256: [`raw_data/history_manifest.json`](../raw_data/history_manifest.json).
Las copias offline tienen el mismo hash en
`tests/fixtures/official_history/manifest.json`. Los resultados no usan datos sintéticos.

## Cuotas y patrimonio, fondos A–E

Páginas de descubrimiento: `https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFP.php?tf=A`
y las variantes B, C, D, E. En sus scripts se observó `fecconf=20261031`.

CSV descargados, uno por fondo:

- https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFPxls.php?aaaaini=2014&aaaafin=2026&tf=A&fecconf=20261031
- https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFPxls.php?aaaaini=2014&aaaafin=2026&tf=B&fecconf=20261031
- https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFPxls.php?aaaaini=2014&aaaafin=2026&tf=C&fecconf=20261031
- https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFPxls.php?aaaaini=2014&aaaafin=2026&tf=D&fecconf=20261031
- https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFPxls.php?aaaaini=2014&aaaafin=2026&tf=E&fecconf=20261031

Formato real: CSV ISO-8859-1, separador `;`, bloques repetidos por año y por cambio
 de AFP. Cada bloque incluye estado, fila `Fecha;CAPITAL;;CUPRUM;;...`, y otra con
pares `Valor Cuota;Valor Patrimonio`. La última AFP no tiene columna vacía adicional
en la primera fila. Cuota es-CL; patrimonio entero en pesos; fechas ISO diarias.
Se observan seis AFP al inicio de 2014 y siete después de la incorporación de UNO.

Cada archivo contiene 30.744 observaciones fecha/AFP, desde 1-ene-2014. Las
confirmadas llegan hasta 31-oct-2026; también se descargaron provisionales hasta
5-nov-2026. El lector preserva `confirmed=False` y el cálculo las excluye. Una celda
vacía no se transforma en cero. No se confunden cuotas individuales con una cuota
del sistema ni se promedian cuotas de distintas unidades.

Ejemplo real previo, fondo C / 1-ene-2025 / CAPITAL: cuota 60.512,60 y patrimonio
11006399466865. Frecuencia diaria, fecha civil `America/Santiago`, sin hora en el
archivo. Se exige la fecha de fin de mes publicada; no se reemplaza un mes ausente.
Se obtuvieron 154 puntos mensuales por fondo, enero 2014–octubre 2026.

## UF diaria — sustitución pública SII autorizada

La documentación oficial BCCh indica autenticación mediante API Key Token o
credenciales BDE:
https://si3.bcentral.cl/estadisticas/Principal1/Web_Services/ayuda_soporte_en.html

No se usaron credenciales. Se aplicó la alternativa expresamente autorizada por el
usuario: fuente oficial pública del Servicio de Impuestos Internos.

URLs: https://www.sii.cl/valores_y_fechas/uf/uf2014.htm y las variantes anuales
2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026. Las trece URL
exactas y hashes constan en el inventario.

HTML UTF-8 o ISO-8859-1 según archivo. Se lee únicamente la matriz anual
`table#table_export`: columnas Día, Ene, Feb, Mar, Abr, May, Jun, Jul, Ago, Sep,
Oct, Nov, Dic. Cada fila es un día del mes; celdas vacías son ausencias y las fechas
imposibles (por ejemplo 31-feb) no se inventan. Valores en pesos es-CL.

Se extrajeron 4.696 observaciones diarias: todos los días de 2014–2025 y hasta
9-nov-2026 en la tabla 2026, que publica valores de UF anticipadamente. Solo se usa
UF de fines de mes hasta 31-oct-2026. Ejemplo real: 31-oct-2026 = 41.247,63.
Frecuencia diaria y fecha civil de Chile. Los años completos no tienen huecos;
las pruebas exigen el último día de todos los meses cerrados.

## Rentabilidades reales publicadas — únicamente contraste

Endpoint original:
https://www.spensiones.cl/apps/rentabilidad/getRentabilidad.php?tiprent=FP&template=0

Se realizaron 24 peticiones POST, desde noviembre 2024 hasta octubre 2026, con
`aaaa=YYYY`, `mm=MM`, `btn=Buscar`. Se validó que el título de cada respuesta
coincidiera con el período pedido; no se supuso que los parámetros fueran aceptados.

HTML ISO-8859-1. Cinco tablas A–E y filas de cada AFP más `SISTEMA`. Columnas: mes,
acumulado anual, últimos 12 meses, promedio anual desde septiembre 2002; C y E
incluyen además promedio anual desde su origen. Valores porcentuales con dos
decimales es-CL. La frecuencia es mensual, cierre civil de Chile.

Se conservan todas esas columnas. El contraste ejecutado abarca 24 × 5 × (mes,
12 meses) = 240 comparaciones. Los promedios desde 2002/origen no pueden calcularse
con insumos que comienzan en 2014; su validación no está declarada completa.
Estos archivos no alimentan el cálculo de la serie: solo la comparación posterior.

## Metodología y promedios anuales adicionales

Documentos originales descargados y con hash:

- https://www.spensiones.cl/apps/GetFile.php?id=001&namefile=CAFP2268.pdf
- https://www.spensiones.cl/portal/institucional/594/w3-article-7457.html
- https://www.spensiones.cl/portal/institucional/594/articles-7457_recurso_2.jpg
- https://www.spensiones.cl/portal/institucional/594/articles-16643_recurso_1.pdf
- https://www.spensiones.cl/portal/institucional/594/articles-16971_recurso_1.pdf

La Circular 2268 documenta promedio mensual ponderado por patrimonio previo. El
informe junio 2025, nota 8, explicita el patrimonio de mayo como ponderador para
las columnas de la tabla; incluye promedio anual 36 meses. El informe febrero
2026 incluye promedios 36 y 60 meses. La imagen normativa del Capítulo II muestra
exponente 365/nd. No se cambió el exponente 12/n del motor para pasar una prueba.

La prueba ejecutada falló en cinco comparaciones de 12 meses. Se detuvo el proceso
por §15; no se presenta el contraste de los promedios anuales como terminado.


## Ampliación de supervisión: datos desde 2002

El inventario separado `raw_data/history_2002_manifest.json` cubre 2002–2026;
su copia offline es `tests/fixtures/official_history/manifest_2002.json`.
Son 58 entradas y 5 páginas de descubrimiento (63 archivos verificados). Se
preservan sin cambios el inventario anterior y sus originales.

Los cinco CSV usan el mismo endpoint SP con `aaaaini=2002`, `aaaafin=2026`,
`tf=A|B|C|D|E`, `fecconf=20261031`. Hay 280.293 observaciones fecha/AFP, incluidas
provisionales: las confirmadas llegan a 31-oct-2026. Los encabezados históricos
incluyen entidades ya desaparecidas; el lector conserva cada AFP sin unificar
cuotas o inventar series a través de fusiones.

Para A/B/D aparecen filas desde 1-ago-2002 con cuota 10.000 y patrimonio cero;
el primer patrimonio positivo es 27-sep-2002. Enero–septiembre anterior al inicio
queda registrado como ausencia de fondo activo en `history_2002_coverage.json`.
Para C/E el archivo empieza 1-ene-2002. Los originales no se rellenan ni alteran.

La ruta moderna SII devuelve 404 para 2002–2012. Las URL públicas verificadas son
`https://www.sii.cl/pagina/valores/uf/uf2002.htm` y variantes hasta `uf2012.htm`.
Formato UTF-8, una matriz `table.tabla` con Día y Ene…Dic; tiene la misma convención
es-CL y celdas vacías para fechas imposibles. En 2013 comienza la ruta moderna
`https://www.sii.cl/valores_y_fechas/uf/uf2013.htm`, con `table#table_export`.

Se disponen de 9.079 valores diarios de UF desde 1-ene-2002. Los doce años
adicionales 2002–2013 están completos, incluidos años bisiestos, con hash y pruebas
offline. Esto prepara insumos: NO declara validadas las anualizadas ni resuelve
la definición metodológica que espera autorización escrita.
