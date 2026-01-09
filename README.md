# CFX Discord Bot

Este bot permite obtener información de servidores FiveM usando el código o enlace CFX.

## Instalación

1.  Asegúrate de tener Python instalado.
2.  Instala las dependencias necesarias:
    ```bash
    pip install discord.py requests
    ```

## Configuración

1.  Abre el archivo `discord_bot.py`.
2.  Busca la línea 12:
    ```python
    TOKEN = "TU_TOKEN_AQUI"
    ```
3.  Reemplaza `"TU_TOKEN_AQUI"` con el token de tu bot de Discord.

## Ejecución

Ejecuta el bot desde la terminal:

```bash
python discord_bot.py
```

## Uso

En Discord, usa el comando:
`.cfx <código o enlace>`

Ejemplo:
`.cfx jggpdk`
`.cfx cfx.re/join/jggpdk`

Aparecerán botones para ver:
-   Jugadores
-   Recursos
-   Escanear puertos
