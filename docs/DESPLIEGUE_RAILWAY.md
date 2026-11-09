# Dejar el bot encendido siempre — Railway

El bot corre hoy en el computador de Daymler, así que se apaga con él. Esto lo
deja corriendo en un servidor.

## Qué se despliega y qué no

| Corre en Railway | Sigue en tu computador |
|---|---|
| Responder preguntas, en el grupo y en privado | Generar las imágenes del mes (`run`) |
| `revisar`, `aprobar`, `publicar` desde el teléfono | |

La generación necesita Cairo y los datos oficiales, así que por ahora se hace
local. Lo demás vive en el servidor.

## Pasos

1. Entra a railway.app y crea una cuenta con tu GitHub.
2. **New Project → Deploy from GitHub repo** y elige este repositorio.
3. En **Variables**, agrega:

   ```
   TELEGRAM_BOT_TOKEN   el token de @BotFather
   TELEGRAM_CHANNEL     @fondoclaro
   OWNER_TELEGRAM_ID    tu id (está en tu .env local)
   FONDOCLARO_ROOT      /data
   ```

4. En **Settings → Volumes**, crea un volumen montado en `/data`.
   Sin esto, las aprobaciones se pierden en cada despliegue.
5. Railway despliega solo. En **Deploy Logs** debe aparecer
   `FondoClaro: bot escuchando`.

## Antes de encenderlo: apaga el bot local

Telegram **no permite dos bots leyendo el mismo token a la vez**. Si dejas el
local corriendo, los dos se roban los mensajes y ninguno responde bien.

```bash
pkill -f "m fondoclaro bot"
```

## Cada mes

1. En tu computador: `python -m fondoclaro run --fund all --period YYYY-MM`
2. Copia los informes nuevos a `seed/reports/` y haz `git push`
3. Railway redespliega solo
4. Desde el teléfono: `revisar`, `aprobar`, `publicar`

## Costo

$5 de crédito de prueba por 30 días; después alrededor de $5 al mes. Es costo
fijo: no sube con la cantidad de suscriptores.
