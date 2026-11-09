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

## Ejecución final completada

Se ejecutó exactamente la generación solicitada, sin --dev, desde el commit
`7b8e9371758441ec57f9f0177ac9a42833ee4aab`, con `dirty=false`:

```bash
python -m fondoclaro run --fund all --period 2026-10
```

Los seis registros están en **HUMAN_REVIEW_PENDING**; sus auditorías están en
PACKAGE_EXPORTED. Se revalidaron SVG/PNG y hashes de cada informe, los cinco
vínculos del resumen y la integridad de los paquetes exportados.
No existe approved_index.json ni ningún archivo de aprobación de esta ejecución.
No se ejecutaron approve, mark-published ni send-package.

| Informe | Mes visible | 10 años visible | PNG |
| --- | --- | --- | --- |
| A | -0,3% | +68,8% | [PNG](../reports/0bbbd7ab8df1407f88f983644f3d400a/infographic.png) |
| B | 0,0% | +55,5% | [PNG](../reports/3de514372db948568a116f378a3c8462/infographic.png) |
| C | +1,0% | +33,5% | [PNG](../reports/eb760c3754d5414bb3caca1e390c2435/infographic.png) |
| D | +1,8% | +16,3% | [PNG](../reports/5119a4d2542b48f2ba82627d73ca01ee/infographic.png) |
| E | +3,2% | +9,6% | [PNG](../reports/8cbab2ed02e247c4a12eb8b3cd47f505/infographic.png) |
| all | — | — | [PNG](../reports/a2d21c00863e4ec79eb239aba8610bbd/infographic.png) |

[Vista conjunta de revisión](../reports/review_68e14ba4475141809d25c9afcc9a5c28.html).

El inventario íntegro con report_id, código, estado, hash y rutas de mensajes
y paquetes está en `docs/REPORTS_2026-10.json`. Los archivos anteriores no se
modificaron ni heredaron aprobación. Los PNG son 1080×1350 y corresponden al
corte 31-oct-2026. Las únicas tareas diferidas por el usuario son el control
raster de espacios y el bot/monthly; las anualizadas conservan sus límites
consultivos documentados, sin afectar la dorada mensual/12 meses.
