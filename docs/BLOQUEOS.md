# Pendientes y controles — ciclo de imágenes de octubre 2026

## Resuelto: método SP y dorada bloqueante

Daymler autorizó por escrito la opción (a), y la actualización acotada de la
especificación. La dorada pasa con **240 comparaciones, 0 fallos**, máximo
**0,0049573561502499068 pp**, con la tolerancia original **0,01 pp**.
El fallo del índice encadenado previo queda preservado en
`docs/archive/GOLDEN_CHAINED_978a52a.json`. Los scripts del supervisor no se modifican.

## Pendiente no bloqueante: anualizadas desde 2002/origen

Se intentaron 480 comparaciones individuales de AFP desde 26-sep-2002; 94 exceden
0,01 pp, máximo 2,8921965763706168 pp. No se alteraron sus datos ni continuidad.
Hay 120 diagnósticos parciales del sistema, máximo 0,2373670239881845 pp, pero
**cero promedios completos del sistema validados**, porque faltan historias de
administradoras/sucesiones que sí intervienen en la publicación. No se interpreta
una media parcial como el promedio oficial completo. Los 48 casos desde origen
C/E quedan sin historia anterior a 2002. Véase `docs/ANNUAL_VALIDATION.json`.

Esto es consultivo y no bloquea este ciclo por decisión expresa de Daymler. Para
cerrarlo se necesitan series oficiales con continuidades/fusiones documentadas y
la historia anterior a 2002; no se inventan empalmes ni se afloja tolerancia.

## Diferido por el usuario: control raster de espacios §8.4

Se preservan espacios SVG y se rechazan tspan; hay snapshot, control geométrico y
contraste de texto. Aún no se mide el hueco raster >=0,2 em. El registro de
validación lo señala DEFERRED_BY_USER_2026-11-08. No se declara implementado.

## Resuelto en parte: difusión por Telegram; WhatsApp en espera de presupuesto

El canal es Telegram (`telegram-post` y `bot`), gratuito y sin aprobación previa
de plataforma. Lee solo `approved_index.json` y verifica el hash del PNG (§9.4).
No publica nada sin aprobación humana.

La WhatsApp Cloud API queda pendiente por falta de presupuesto, no por falta de
implementación: Meta exige plantillas pagadas para iniciar conversación. El bot
§9.5 de WhatsApp y el webhook no se construyen hasta que exista financiamiento.
`.env.example` conserva sus claves vacías.

## Pendiente: ciclo monthly

No implementado. Hoy el ciclo lo inicia una persona ejecutando `run`. Falta la
tarea que detecte la publicación de la SP y avise.

## Presentación monetaria: excepción ya autorizada

Se mantiene monto visible derivado del porcentaje visible y monto exacto archivado.
El texto literal de §5.4 conserva el conflicto de empates negativos; no se modificó
esa sección porque la autorización de edición de este ciclo fue acotada. La
excepción documentada y autorizada no cambia los retornos ni la dorada.

## Estado de Git y aprobaciones

Git es operativo. La ejecución final sin --dev se completó desde el commit
7b8e9371758441ec57f9f0177ac9a42833ee4aab con dirty=false; los seis informes están
en HUMAN_REVIEW_PENDING y los anteriores quedan intactos. No se ejecutan approve, mark-published
ni send-package. Los informes nuevos requieren revisión y acción posterior de Daymler.

## Observación preservada sobre evidencia de supervisión

`verify_hashes.py` termina con exit 0 incluso si su contador detectara problemas.
Su salida anterior muestra coincidencia íntegra. Los tests propios hacen asserts
sobre los hashes; no se modifica el script independiente.
