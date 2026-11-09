# Decisiones conservadoras

1. Proyecto local Python; no sitio, despliegue ni publicación. El zip exige operación
   local y aprobación humana; no se usan herramientas de hosting.
2. `python3` es el ejecutable disponible; `.venv/bin/python` proporciona `python`
   tras activar el entorno. No se modifica ninguna configuración global.
3. Sin repositorio Git operativo: `run` registra UNVERSIONED y bloquea sin `--dev`.
   Un informe dev tampoco se puede aprobar. No se inicializa ni modifica `.git`.
4. Se conserva la especificación recibida en `docs/FONDOCLARO_SPEC_V1.md` y los
   archivos de referencia originales. Sus datos ficticios no se usan como datos.
5. No se usa prensa. Las capturas oficiales completas y hashes quedan conservados.
   `fetch` conserva su implementación previa. El recolector explícito
   `scripts/fetch_history.py` descargó la historia 2014–2026 y los contrastes.
6. Cada invocación de `run` crea registros nuevos y termina BLOCKED con motivos
   explícitos. Tras fallar la prueba dorada, no se continuó integrando el
   pipeline por §15; los motivos estáticos previos no son el informe actualizado.
   La evidencia vigente es `docs/GOLDEN_RESULT.json` y `docs/BLOQUEOS.md`.
7. Para historia reducida se conserva `base_id=LARGO_120` por el contrato estricto
   de §5.3 y se declara `horizon` explícito. La base monetaria sigue siendo única;
   no se presenta un monto del mes. Esa interpretación necesita revisión antes de
   habilitar producción porque el nombre del identificador presupone 120 meses.
8. Los espacios se preservan usando nodos completos, sin tspan. El raster se
   genera desde contornos del OTF incluido. Se rechazan tspan en el verificador
   hasta que exista control raster de separación ≥0,2 em.
9. Estado operacional separado de artefactos sellados; aprobación e identidad
   permanecen locales, no se exportan. Hash canónico de inventario SHA-256 incluye
   manifiesto, PNG, mensaje, fuentes y registro de ejecución con Git/dependencias.
10. `send-package` preserva una carpeta existente y lista ausencias. No acepta
    imágenes dev ni hashes alterados; no incluye borradores.
11. Los tests sintéticos se crean bajo directorios temporales de pytest. No existe
    modo demo del CLI ni un PNG sintético que parezca un informe real aprobado.
12. El usuario autorizó el 2026-11-08: «Sí, que las cifras visibles siempre cuadren».
    Se cambia §5.4: porcentaje visible HALF_UP a un decimal; monto visible = base ×
    (1 + porcentaje visible / 100). El monto de la curva y las métricas conservan
    precisión completa. La política y ambos montos constan en el manifiesto.
    La prueba de propiedad de esa política pasa, incluidos empates negativos.
    La política es una desviación explícita de redondear ambos valores por
    separado según el texto literal de §5.4; no se declara conformidad literal.
13. Se recibió `fondoclaro_spec_v1(1).zip`, con §9.5. Se actualizaron las dos copias
    del Markdown. Las referencias gráficas son idénticas a las anteriores.
14. Por autorización expresa del usuario, se usa UF pública del SII porque la API
    BCCh requiere autenticación. No se utilizaron credenciales ni datos privados.
15. La prueba dorada omitida fue reemplazada por una prueba real offline. El primer
    contraste falló: 5/240 celdas, máximo 0,01317100127918 pp; se conserva la prueba
    fallida y se detiene por §15. No se cambian fórmulas ni tolerancia. No se inicia
    el bot ni se generan imágenes reales después de esa parada.
