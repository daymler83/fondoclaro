# FondoClaro

Pipeline local de informes financieros para WhatsApp, con revisión humana.
La especificación actual incluye el bot (§9.5), pero el trabajo se **detuvo en la
fase 2 por una prueba dorada real fallida**, conforme a §15. El bot y la generación
completa de seis PNG reales todavía no están implementados.

Resultado vigente: **139 pruebas pasan y 1 falla**. La fallida es la prueba dorada:
5 de 240 comparaciones exceden 0,01 pp. No está omitida ni marcada como fallo esperado.

- [Informe técnico y acciones pendientes](docs/INFORME_TECNICO.md)
- [Salida completa de pytest](docs/PYTEST.txt)
- [Resultado financiero exacto](docs/GOLDEN_RESULT.json)
- [Fuentes reales y formatos](docs/FUENTES.md)
- [Bloqueos](docs/BLOQUEOS.md)

## Instalar y verificar

Python ≥3.11 y biblioteca Cairo (`libcairo2` en Debian/Ubuntu).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q --tb=short
```

Las pruebas corren offline con los archivos oficiales de `tests/fixtures/`.
La instalación inicial requiere paquetes disponibles en caché o acceso al índice.
`requirements.lock` fija el entorno previo y las dependencias transitivas.

## Descargar historia y reproducir la validación

```bash
python scripts/fetch_history.py --start-year 2014 --end-year 2026
python scripts/validate_history.py
```

El primer comando requiere internet y solo descarga archivos públicos. Conserva
CSV de cuota/patrimonio A–E, UF SII y publicaciones SP, con petición y SHA-256, en
`raw_data/`. No usa credenciales. El segundo es offline y retorna código 2 al fallar;
guarda el resultado en `reports/golden_validation/result.json`.

Mes cerrado confirmado encontrado: **octubre 2026**. El índice encadenado reproduce
los meses, pero cinco retornos de 12 meses superan la tolerancia. No se debe cambiar
la fórmula o los datos para conseguir una prueba verde.

## CLI parcial conservado

```bash
python -m fondoclaro --help
python -m fondoclaro run --fund C --period latest --dev
python -m fondoclaro status --report-id ID
python -m fondoclaro validate --report-id ID
python -m fondoclaro export --report-id ID
python -m fondoclaro import-audit --report-id ID --path DIRECTORIO
python -m fondoclaro approve --report-id ID --sin-auditoria-externa
python -m fondoclaro mark-published --report-id ID --url 'difusión manual YYYY-MM-DD'
python -m fondoclaro send-package --period 2026-10
```

`run` sigue bloqueado por el preflight previo: no se continuó integrándolo después
del fallo de §15. Su mensaje estático no sustituye el resultado financiero vigente.
`--dev` no omite controles financieros ni autoriza aprobación. El `.git` de este
workspace no es un repositorio operativo. Los comandos de auditoría/aprobación
requieren artefactos completos y sellados; no hay informes reales para aprobar.

El formateo monetario conserva la política autorizada por el usuario: monto visible
derivado del porcentaje visible y monto exacto archivado. Es una desviación de
redondear ambos independientemente con HALF_UP en empates negativos; véase el
informe técnico. No influye en la prueba dorada, que usa cifras sin redondear.

No hubo envío, publicación ni conexión a Meta. No ejecutar una prueba con Meta
hasta resolver la metodología, generar/aprobar los informes e implementar §9.5.
