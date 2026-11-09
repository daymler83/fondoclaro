# Prueba dorada real — FAIL

Se sustituyó la prueba omitida por `tests/test_golden_real.py`. Recalcula offline
las cuotas/patrimonios SP y UF SII de `tests/fixtures/official_history/`, con hashes
y URL de procedencia. No hay insumos SYNTHETIC en esta prueba.

Noviembre 2024–octubre 2026, A–E, mensual y 12 meses: 240 comparaciones.
120/120 mensuales pasan; 115/120 de 12 meses pasan y cinco fallan.
Máxima diferencia: 0,0131710012791798464 pp frente a tolerancia fija 0,01 pp.

Resultado exacto en `docs/GOLDEN_RESULT.json` y salida completa en `docs/PYTEST.txt`.
La prueba debe seguir roja hasta resolver documentalmente la metodología. No
modificar datos, tolerancia o fórmulas solo para conseguir que pase.
