# FondoClaro

Una vez al mes, cómo les fue a los cinco fondos de pensiones de Chile: un
gráfico, dos cifras y una explicación en lenguaje simple. El principio rector
es que alguien sin conocimientos financieros lo entienda en 30 segundos.

**Canal:** [t.me/fondoclaro](https://t.me/fondoclaro)

No es una AFP, no vende nada, no tiene avisos y no recomienda cambiarse de
fondo. Las cifras son del promedio del sistema, no de la cuenta de nadie.

## Por qué se pueden creer las cifras

Todo sale de fuentes públicas y oficiales: los valores cuota y el patrimonio
que publica la [Superintendencia de Pensiones](https://www.spensiones.cl), y la
UF para descontar la inflación. Los archivos originales se guardan sin
modificar, con su SHA-256 y la URL de donde vinieron.

El cálculo se contrasta contra las cifras que la propia Superintendencia
publica, en los horizontes donde ella publica: **240 comparaciones, cero
fallos, diferencia máxima 0,005 puntos porcentuales**. Si ese contraste falla,
el informe se bloquea y no se publica.

**Lo que no está validado contra nadie, y conviene saberlo:** la cifra de diez
años acumulada. La Superintendencia no publica acumulados a diez años —para
horizontes largos usa promedios anuales—, así que ese número es el método
oficial aplicado a una ventana que nadie más reporta. Está documentado en
[`docs/BLOQUEOS.md`](docs/BLOQUEOS.md).

## Cómo funciona

```
datos oficiales → cálculo → contraste contra la SP → imagen
      → revisión humana → aprobación → publicación
```

Ningún paso automático publica nada. Las imágenes quedan en
`HUMAN_REVIEW_PENDING` y una persona tiene que aprobarlas, mirando la imagen,
quedando la aprobación atada al hash de ese archivo exacto. Si algo cambia, la
aprobación deja de valer y hay que revisar de nuevo.

El bot de Telegram responde preguntas eligiendo entre respuestas escritas de
antemano y entrega imágenes ya aprobadas: **nunca redacta ni calcula una cifra
en el momento**. Hay pruebas que fallan si una respuesta usa jerga financiera,
da un consejo de inversión o nombra una administradora.

## Para correrlo

Python ≥ 3.11 y Cairo del sistema.

```bash
pip install -e '.[test]'
pytest -q                                        # 314 pruebas, sin red
python -m fondoclaro run --fund all --period 2026-10
```

Las pruebas y la generación usan archivos oficiales archivados, así que
funcionan sin conexión. `run` exige un árbol de git limpio.

## Documentación

| | |
|---|---|
| [Especificación](docs/FONDOCLARO_SPEC_V1.md) | el contrato completo |
| [Metodología](docs/METODOLOGIA.md) | cómo se calcula |
| [Fuentes](docs/FUENTES.md) | cada archivo oficial, con URL y hash |
| [Informe técnico](docs/INFORME_TECNICO.md) | resultados de la última ejecución |
| [Pendientes](docs/BLOQUEOS.md) | lo que falta y lo que no está validado |
| [Decisiones](docs/DECISIONES.md) | por qué se hizo cada cosa así |
| [Despliegue](docs/DESPLIEGUE_RAILWAY.md) | dejar el bot encendido |

La supervisión del cálculo, hecha con scripts independientes del código
principal, está en [`docs/supervision/`](docs/supervision/).
