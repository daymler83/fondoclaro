# Decisiones conservadoras

1. Proyecto local Python; no sitio, despliegue ni publicación. El zip exige operación
   local y aprobación humana; no se usan herramientas de hosting.
2. `python3` es el ejecutable disponible; `.venv/bin/python` proporciona `python`
   tras activar el entorno. No se modifica ninguna configuración global.
3. Sin repositorio Git operativo: `run` registra UNVERSIONED y bloquea sin `--dev`.
   Un informe dev tampoco se puede aprobar. Actualización: Daymler habilitó Git;
   se creó el commit inicial solicitado, sin cambiar configuración global.
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
   hasta que exista control raster de separación ≥0,2 em. La medición sigue
   diferida: los nodos completos evitan perder espacios entre tramos, pero un
   detector general de huecos debe distinguir blancos de letras y fondos de la
   imagen antes de declarar §8.4 verificado. El snapshot nuevo detecta regresiones
   y no se presenta como sustituto de esa medición; validate_png lo declara.
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

16. Para preparar el nivel C se amplía la descarga a 2002 conservando los inventarios
    originales de 2014 y el fallo dorado. Se usa un manifiesto separado y congelación
    que rechaza sobrescribir fixtures de otros bytes. No se adopta metodología nueva.
17. Los años SII 2002–2012 usan su ruta histórica pública y tabla class="tabla";
    la ruta moderna devuelve 404. Se documentan ambas, sin sustituir cifras.
18. La corrección del tramo final solo cambia orden de dibujo y tamaño del marcador.
    El umbral raster de 32 píxeles sólidos fuera del disco se fijó antes del cambio;
    falló con 14/12 píxeles y ahora pasa en ambos signos. No se colorean meses extra.
19. Snapshot sintético versionado: delta máximo 2 por canal y cero píxeles fuera
    de ese umbral. Desplazar la marca 1 px produce rechazo. No se actualiza la
    referencia automáticamente al ejecutar pytest.
20. Las fases 3 y 4 permanecen detenidas hasta decisión escrita de Daymler del punto 4.
    No se edita la especificación ni ningún script de supervisión.
