# Metodología autorizada — 8-nov-2026

Daymler adopta por escrito la opción (a) de la supervisión. El SISTEMA es un
promedio de retornos por AFP en el mismo horizonte, ponderado por patrimonio del
mes anterior al corte. Se modificaron únicamente §5.1–§5.3, §6.1, §6.2 y la
aclaración expresamente solicitada de §6.3-6. La tolerancia dorada sigue 0,01 pp y
la relativa del recálculo independiente sigue 1e-9 (piso absoluto 1e-30 para cero).

Para cada AFP: r_a(i,j) = (VC_a,j / VC_a,i) × (UF_i / UF_j) − 1.
Para el SISTEMA: suma de r_a multiplicado por patrimonio_a,j−1 dividido por
el total de patrimonios de las AFP con historia completa en ese horizonte.
Las AFP sin historia desde el inicio se registran explícitamente como excluidas;
no reciben un retorno inventado. Si una AFP sí tenía historia pero aparece un
hueco intermedio o falta en el cierre, el cálculo se bloquea/omite según §5.5.
SP omite las cifras de AFP sin historia completa en sus tablas (nota 7 del informe
febrero 2026) y pondera por patrimonio previo (nota 8). Se preservan componentes,
ponderaciones, fechas y exclusiones, incluida UNO en la ventana de diez años.

La anualizada por AFP usa 365/días exactos, según la imagen normativa SP
articles-7457_recurso_2.jpg. Se ponderan esas anualizadas con los mismos pesos;
no se anualiza el promedio agregado como sustituto. Los promedios desde 2002 se
intentan aparte: las fusiones/continuidades de AFP que no pueden demostrarse con
los archivos se declaran y no se inventan series. Las columnas desde origen
anteriores a 2002 quedan fuera de cobertura. Son controles consultivos en este ciclo.

Para el gráfico se fija b = j−120 y V_t = 10.000.000 × (1+r_sistema(b,t)).
Cada punto usa el patrimonio del mes anterior a su propio corte t. No se encadenan
retornos agregados. El punto final exacto coincide con base × (1+r_120m).
El signo del último cambio de V se verifica frente a r_1m; si difiere se bloquea,
incluso con retornos casi nulos. Nunca se mueve el punto para forzar el signo.

El recálculo independiente lee por sí mismo CSV SP y matrices UF SII. Por cada
AFP multiplica factores reales mensuales y solo después aplica los pesos j−1;
el principal calcula cocientes de extremos por AFP. Se comparan también las AFP
incluidas/excluidas, horizontes y todos los puntos de la curva. No importa el
motor ni los lectores principales. Ambos caminos usan Decimal con precisión 40.

La presentación conserva la política de redondeo autorizada previamente: monto
visible derivado del porcentaje visible; el monto exacto y la serie permanecen
archivados. Esta excepción de §5.4 no modifica el cálculo financiero ni los datos.
No se editó §5.4 en este ciclo porque no se autorizó ampliar el cambio a esa sección.

Los datos se cargan offline desde inventarios oficiales con hashes, estado de
confirmación, parámetros y URL. El SII es la alternativa pública autorizada a UF
BCCh. Las rentabilidades publicadas SP se usan solo para contraste posterior.

El SVG y PNG salen de las cadenas del manifiesto y contornos de Inter incluido.
Se verifican texto, layout, puntos/escala y último segmento. Hay regresiones raster
y snapshot sintético versionado. La medición raster de espacios de §8.4 y el bot
quedaron expresamente para después. Los paquetes externos permiten trazabilidad;
no prueban una auditoría ni aprueban publicación por sí mismos.
