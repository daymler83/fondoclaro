# Informe técnico — correcciones de supervisión

Actualización: 8 de noviembre de 2026. Se completaron la preparación de Git,
la ampliación de insumos desde 2002 y las correcciones de dibujo/configuración
solicitadas en los puntos 1–3. **La parada de §15 se mantiene.** No se ha elegido
la metodología del punto 4, no se modificó la especificación y no se retomaron las
fases de imágenes reales ni bot.

## 1. Git operativo y commit inicial

Commit inicial del estado previo a las correcciones:
`d1e1b2fdaa0380a2a611b95625a641522eea549e`.

Con el árbol limpio se ejecutó `run --fund C --period latest` **sin --dev**. El
informe `cc8b22ff18034a46a18a216cfbd40124` registró ese SHA, `dirty=false` y
`dev=false`; quedó BLOCKED por las validaciones financieras, sin UNVERSIONED.
Los informes anteriores no se reescribieron. Los siguientes cambios quedan
revisables mediante Git; se conserva también el commit intermedio existente.

## 2. Historia 2002–2026 descargada y congelada

Se utilizó el mismo recolector, ampliado para elegir un inventario separado y
congelar copias offline verificadas. No se sobrescribieron el inventario de 2014
ni sus fixtures: siguen siendo la base reproducible de la prueba dorada fallida.

- `raw_data/history_2002_manifest.json`: 58 entradas y 5 páginas de descubrimiento,
  **63 archivos con SHA-256**, incluidos 5 CSV A–E, 25 tablas UF, 24 publicaciones
  de contraste y 4 documentos de metodología.
- `tests/fixtures/official_history/manifest_2002.json`: copias congeladas con los
  mismos hashes y URL de procedencia.
- `raw_data/history_2002_coverage.json` y su copia en fixtures: cobertura y ausencias.
- **280.293 observaciones fecha/AFP** en los cinco CSV, incluidos provisionales;
  corte confirmado común **31-oct-2026**. Los provisionales se conservan marcados.
- **9.079 valores diarios de UF**, desde 1-ene-2002 hasta los valores publicados
  anticipadamente de 9-nov-2026; todos los años completos 2002–2025 no tienen huecos.

Las URL modernas del SII devolvieron 404 para 2002–2012. Se verificó y usó su ruta
histórica oficial `https://www.sii.cl/pagina/valores/uf/ufYYYY.htm`, con la matriz
`table.tabla`; 2013–2026 usan la ruta moderna y `table#table_export`. No se inventaron
ni interpolaron valores. Las pruebas verifican ambas variantes y cada día del año.

Para A, B y D el CSV comienza el 1-ago-2002 y conserva cuotas de preapertura con
patrimonio cero; el primer patrimonio positivo es del **27-sep-2002**. El período
1-ene–26-sep-2002 queda registrado como FUND_NOT_ACTIVE, sin convertir esas cuotas
de preapertura en historia activa. C y E tienen observaciones desde 1-ene-2002.

**Nivel C: insumos desde 2002 disponibles; NO VALIDADO.** El método espera la
resolución escrita del punto 4. Las columnas desde el origen anteriores a 2002
siguen fuera de este rango: C desde 1981 y E desde mayo de 2000 según los encabezados
SP archivados. No se afirma que una descarga desde 2002 cubra toda su vida.

Reproducción de la descarga y congelación, con internet:

```bash
python scripts/fetch_history.py --start-year 2002 --end-year 2026 \
  --manifest raw_data/history_2002_manifest.json \
  --freeze-to tests/fixtures/official_history/manifest_2002.json
```

## 3. Correcciones independientes de metodología

### Tramo final perceptible en el PNG

Se escribieron y ejecutaron las dos regresiones raster **antes de corregir el
dibujo**. Fallaron ambas: solo **14 píxeles rojos** y **12 verdes** visibles fuera
del disco del extremo; el requisito prefijado es **32 píxeles sólidos**.
La salida real está en [`verification/segment_before.txt`](verification/segment_before.txt).

Se redujo el marcador a radio 2 y borde 2, se dibuja debajo del último segmento y
se redondearon los extremos del trazo. No se extendió el color a otros meses ni
se cambiaron puntos de la serie, cifras o escalas. Las dos regresiones ahora pasan.
`validate_svg` mantiene sus comprobaciones de datos y geometría.

### WhatsApp: mes, año y fecha es-CL

Pie y mensaje comparten `cutoff_label`. El caso normal incluye ahora `octubre 2026`
y termina con la misma fecha del pie, `31-oct-2026`, en lugar de ISO. Hay 48 casos
que cubren los doce meses y cuatro disponibilidades/horizontes, con igualdad de
fecha carácter a carácter, nombre del mes/año y límite de 40 palabras.

### Snapshot y pie

Referencia almacenada: `tests/snapshots/individual_C_SYNTHETIC.png`, con parámetros
y hash en su JSON. **Es una prueba sintética, no un informe real publicable.**
La comparación permite delta por canal de 2 y cero píxeles fuera de ese umbral.
Una prueba desplaza el texto de marca 1 px en el SVG y confirma que el comparador
rechaza el PNG. No se confunde el snapshot con la prueba previa de determinismo.

El alto de la tarjeta del pie se calcula desde la última línea, con margen
interior inferior de 26 px, en vez del bloque fijo que dejaba unos 130 px vacíos.
El control raster de espacios de §8.4 sigue pendiente y se declara expresamente
junto a la decisión #8 y en el docstring de `validate_png`.

### Configuración y dependencia

`.gitignore` incluye `.env`, variantes `.env.*` y excepción para `.env.example`.
El ejemplo contiene únicamente las cinco claves vacías de §9.5. Se declaró
`defusedxml==0.7.1` como dependencia directa; instalación editable local y
`pip check` pasan. No existe código de bot ni se emplearon credenciales.

## 4. Pruebas y evidencia independiente conservada

Comando ejecutado: `.venv/bin/pytest -q --tb=short`.

```text
1 failed, 214 passed in 9.98s
```

La salida íntegra está en [`PYTEST.txt`](PYTEST.txt). La única fallida sigue siendo
la prueba dorada original: **5 de 240 celdas**, diferencia máxima
**0,0131710012791798464 pp**, fondo B, diciembre 2024, 12 meses; tolerancia **0,01 pp**.
Los nuevos tests de correcciones pasan; no se omitió, debilitó ni marcó XFAIL la dorada.
`docs/GOLDEN_RESULT.json` conserva el resultado previo y sus insumos originales de 2014.

Se ejecutaron con `python3 -I` los tres scripts aportados por la supervisión,
sin modificarlos. Sus salidas están en `docs/verification/supervision_*.txt`.
Verifican la muestra original (52 raw y 47 fixtures), no el inventario extendido;
los 63 archivos extendidos y su igualdad raw/fixture los verifican los tests nuevos.
El recálculo reproduce los cinco fallos y las variantes mantienen como compatible
el promedio por horizonte con patrimonio del mes anterior al corte.

No se cambiaron `finance/engine.py`, `golden.py`, `independent.py`, `system.py`,
sus tolerancias ni `docs/FONDOCLARO_SPEC_V1.md`. Git permite contrastarlo con el
commit inicial. Ejecutar esos scripts no equivale a importar una auditoría externa
según §10 ni a aprobar un informe.

## 5. Decisión pendiente de Daymler y límites

El punto 4 sigue pendiente: Daymler debe elegir la metodología y actualizar por
escrito §5.1–§5.3, §6.1 y §6.2. La supervisión recomienda el método SP por horizonte
y definir la curva mediante esos retornos. No se adoptó esa opción automáticamente,
no se relajó la tolerancia ni se mezclaron métodos. Los insumos anuales están
preparados para cuando se autorice la definición.

Se mantiene también la desviación de redondeo previamente autorizada: el monto
visible sale del porcentaje visible y el cálculo exacto permanece archivado.
No se afirma cumplimiento literal del §5.4 actual en empates negativos; requiere
incorporar esa política en el documento.

No hay seis PNG reales, aprobación, envío, despliegue ni bot. Los PNG nuevos son
solo fixtures de pruebas unitarias. [`BLOQUEOS.md`](BLOQUEOS.md) detalla los pendientes.
