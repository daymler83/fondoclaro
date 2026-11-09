# FondoClaro

Informes determinísticos del promedio del sistema, con revisión humana. Método SP
por horizonte autorizado por Daymler el 8-nov-2026. La dorada bloqueante pasa:
240 comparaciones, cero fallos, tolerancia intacta 0,01 pp. Los promedios anuales
se intentan como control consultivo y permanecen parcialmente no validados.

```bash
source .venv/bin/activate
pytest -q --tb=short
python -m fondoclaro run --fund all --period 2026-10
```

En un clon nuevo: Python >=3.11, Cairo del sistema, `pip install -e '.[test]'`.
Las pruebas y `run` usan archivos oficiales archivados y funcionan offline.
`run` exige un commit Git limpio salvo --dev; un informe dev no se puede aprobar.
Produce cinco imágenes individuales y un resumen, textos WhatsApp, manifiestos,
registros, paquetes de auditoría y una vista HTML conjunta en reports/.
Todos terminan HUMAN_REVIEW_PENDING. No genera ni envía publicaciones.

La aprobación es una acción humana separada. No se debe ejecutar approve,
mark-published o send-package como parte de generación. El bot y monthly, y el
control raster de espacios, quedaron expresamente para otro ciclo.

- [Informe técnico](docs/INFORME_TECNICO.md)
- [Pruebas completas](docs/PYTEST.txt)
- [Dorada](docs/GOLDEN_RESULT.json)
- [Anualizadas consultivas](docs/ANNUAL_VALIDATION.json)
- [Fuentes](docs/FUENTES.md)
- [Pendientes](docs/BLOQUEOS.md)

Los datos originales y las evidencias de supervisión no se alteran. La ampliación
2002–2026 usa raw_data/history_2002_manifest.json y sus copias con SHA-256. La
presentación conserva la política monetaria autorizada: monto visible desde el
porcentaje visible y monto exacto archivado, sin modificar retornos.
