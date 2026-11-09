# Metodología implementada y límites

## Contraste oficial iniciado el 8-nov-2026

Se descargaron cuotas/patrimonios A–E desde 2014, UF diaria SII y publicaciones
de validación desde noviembre 2024 hasta octubre 2026. Se fijan las siguientes
fórmulas **antes** del primer contraste; no se cambiarán a partir de su resultado.

Para cada AFP k y mes j, patrimonio P(k,j−1), peso
`w(k,j−1)=P(k,j−1)/ΣP(k,j−1)` y factor nominal de cuota
`f(k,j)=VC(k,j)/VC(k,j−1)`. El promedio mensual nominal del sistema es
`Σ w(k,j−1) × f(k,j) − 1`. Su factor real divide por `UF(j)/UF(j−1)`.
La Circular SP 2268, nota 4, y el informe SP de junio 2025, nota 8, documentan
patrimonio del último día hábil del mes anterior. El CSV publica también el fin
de mes calendario con la misma fotografía cuando ese día es inhábil; por ejemplo
30/31-may-2025 y 30/31-oct-2025 son idénticos. No se sustituye una fecha faltante.

Para dar al motor de §5 una serie, se encadenan los factores nominales mensuales
en un índice normalizado inicialmente a 100. La normalización se cancela en los
cocientes y el motor deflacta una sola vez. **No se llama cuota oficial del sistema
a este índice calculado**. Nunca se alimenta con rentabilidades de contraste.
Una AFP que recién aparece y no tenía patrimonio en el mes anterior no recibe
un peso inventado; una AFP con patrimonio anterior que falte al cierre bloquea.

Se conserva también una operación de diagnóstico documental para el horizonte n:
`Σ w(k,j−1) × [VC(k,j)/VC(k,j−n) × UF(j−n)/UF(j) − 1]`.
El informe de junio 2025 usa el mismo patrimonio de mayo en las columnas de su
tabla. Esta operación no sustituye al motor ni cambia qué fórmula se somete a la
prueba dorada. En general, un promedio ponderado del retorno de 12 meses no es
igual al producto de doce promedios mensuales con pesos variables.

La imagen oficial `articles-7457_recurso_2.jpg`, archivada con hash, fija para
anualizar `365/nd`, donde nd son días del período. El motor conserva `12/n` porque
así lo exige §5.1: no se altera el exponente para forzar una coincidencia. Los
promedios publicados desde 2002/origen no pueden validarse con historia desde
2014. Los PDFs de junio 2025 y febrero 2026, con 36/60 meses, también se preservan;
su validación integral no se declara satisfecha por una comparación mensual.

La primera prueba compara los 24 cortes × A–E × (mes,12 meses) con tolerancia
**0,01 puntos porcentuales** y Decimal de precisión 40. Un fallo basta para
detenerse por §15; no se continúa a los PNG ni al bot. El resultado completo
se guarda en `reports/golden_validation/result.json`.

## Módulos previos

Motor puro con Decimal, contexto local de precisión 40: I = VC/UF;
r = I_final/I_inicial − 1; nominal = VC_final/VC_inicial − 1; anualizada para
60/120 meses = (1+r)^(12/n) − 1. El contexto global de Decimal no se modifica.
Horizontes 1/12/60/120 exigen todas las fechas mensuales en su ventana. Un hueco
omite esa métrica; si afecta el mes, bloquea. Ningún dato se interpola.

El recálculo independiente tiene lector JSON propio y encadena los factores
mensuales `(VC_j/VC_i)*(UF_i/UF_j)`. No importa el motor ni el lector principal.
Se compara con tolerancia relativa 1e-9 y piso absoluto 1e-30 para cero; 40 dígitos
permiten distinguir holgadamente un error financiero de un residuo aritmético.
El contrato JSON normalizado es interno y solo tiene fixtures SYNTHETIC en pruebas.
No es un formato de archivo oficial ni una serie del sistema certificada.

Se añadió `finance/system.py` para promediar retornos por patrimonio y construir
un índice mensual, conservando los componentes y pesos. No se promedian valores
cuota de unidades distintas. La prueba dorada real ya se ejecutó y FALLA en cinco
retornos de 12 meses; los resultados figuran en `docs/GOLDEN_RESULT.json`. El índice
no se habilita para imágenes reales ni se declara equivalente a la publicación.

Base monetaria 10.000.000; serie hipotética V = base × I/I_inicio. El JSON almacena
los cálculos sin redondear como cadenas decimales. Los textos JSON de métricas usan
`-` ASCII; la imagen y el mensaje usan `−` U+2212. Las cadenas específicas para SVG
se conservan tal cual en `visible_texts` para compararlas carácter por carácter.

Formato autorizado por el usuario el 2026-11-08: porcentaje visible HALF_UP a un
decimal; monto visible = 10.000.000 × (1 + porcentaje visible / 100). Este monto
ya es múltiplo de 10.000. Resuelve la incompatibilidad original de §5.4: para
r=-0,0005, el porcentaje visible es -0,1% y el monto visible 9.990.000. El resultado
exacto 9.995.000 permanece en `raw_final_amount` y en el último punto del gráfico;
`displayed_final_amount` contiene el monto que ve el lector. Los globos, la
explicación y WhatsApp comparten ese mismo monto visible. La curva no se redondea.

Renderer: SVG desde datos, texto convertido a contornos de Inter 3.19 OFL incluido
antes de CairoSVG 2.7.1. Las métricas y los contornos proceden del mismo OTF, sin
fontconfig ni fuentes del sistema. Se comparan textos, atributos, puntos de línea,
dominio del área, último segmento, cajas y cruces de polilínea. Las verificaciones
geométricas no sustituyen una revisión visual. La verificación de huecos de espacios
en el raster y el contraste exhaustivo no están implementados todavía.

Los paquetes externos son solo trazabilidad: un resultado PASS no demuestra que
una revisión ocurrió ni otorga aprobación. No hay llamadas a modelos ni mensajería.
