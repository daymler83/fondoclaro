# Informe técnico — método SP autorizado y seis imágenes

Ciclo: octubre de 2026. Daymler autorizó levantar la parada y adoptar el promedio
SP por horizonte. Se verificó primero el script independiente de variantes. Se
modificaron únicamente §5.1–§5.3, §6.1, §6.2 y la aclaración solicitada de §6.3-6,
en ambas copias de la especificación. El resto, incluido §5.4, quedó intacto.

## Método y trazabilidad

Cada retorno por AFP usa cocientes de cuota y UF del mismo horizonte. La media
usa patrimonio del mes anterior al corte y registra AFP/pesos/exclusiones. La
curva tiene inicio fijo j−120 y cada punto se calcula por ese método; el punto
final coincide con el retorno de diez años. El signo del último tramo se valida
sin ajustar los datos. El recálculo tiene lectores propios y encadena por AFP
antes de ponderar: mismo resultado con tolerancia relativa intacta 1e-9.

La producción no consume el índice agregado antiguo ni rentabilidades publicadas
como insumo. Estas se usan solo para contraste. Se verifican hashes de todos los
originales. Los informes se sellan y exportan individualmente; el resumen referencia
los cinco content_hash. Nada se aprueba ni publica dentro de run.

## Validación

Dorada obligatoria: noviembre 2024–octubre 2026, A–E, mensual y 12 meses:
**240 comparaciones, 0 fallos, máximo 0,0049573561502499068 pp**. La tolerancia
sigue **0,01 pp**. Resultado íntegro: `docs/GOLDEN_RESULT.json`; el resultado del
método previo permanece en `docs/archive/GOLDEN_CHAINED_978a52a.json`.

Anualizadas consultivas: **480 comparaciones AFP, 94 diferencias fuera de
0,01 pp, máximo 2,8921965763706168 pp**. Hay 120 medias parciales del sistema,
pero cero comparaciones completas por falta de continuidad de algunas AFP;
el máximo diagnóstico parcial es 0,2373670239881845 pp. Los 48 casos desde origen
C/E no tienen insumos anteriores a 2002. No se declaran validados esos promedios.
Detalle: `docs/ANNUAL_VALIDATION.json`. Este control no bloquea por autorización.

Se verifican contenido, texto/espacios SVG, signos/colores, fuente y corte, puntos
inversamente escalados, dominios, cajas e intersecciones, contraste AA y dimensiones
PNG. El fondo A necesitó una banda vertical mayor para que no chocaran los rótulos;
se conservó la fuente y cada millón. El resumen mantiene A→E y no destaca ganador.
La medición raster de espacios y el bot/monthly siguen diferidos por el usuario.

## Pruebas

```text
223 passed in 22.61s
```

Salida completa: `docs/PYTEST.txt`. Incluye E2E offline de los seis informes con
datos oficiales, paquetes verificables y ausencia de aprobación; validación
independiente de cuatro horizontes por fondo; rechazo de signo final contrario;
y todas las regresiones previas. La dorada no está omitida ni marcada XFAIL.
Los scripts de supervisión permanecen sin cambios.

## Ejecución final

La prueba E2E completa ya deja seis informes en HUMAN_REVIEW_PENDING. Tras guardar
el código se ejecutará sin --dev el comando solicitado, desde Git limpio:

```bash
python -m fondoclaro run --fund all --period 2026-10
```

Se registrarán las rutas e identificadores de esa ejecución en un añadido de
este informe. No se ejecutarán approve, mark-published ni send-package.
