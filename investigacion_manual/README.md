# 🕵️ Guía Avanzada de Investigación y Extracción de Datos (FiveM)

Esta guía contiene métodos avanzados de nivel profesional para extraer identificadores (Discord, Steam, License) e IPs reales de servidores FiveM, incluso si usan proxies y protecciones de privacidad.

---

## 🟢 MÉTODO 1: Intercepción de NUI (Nivel: Fácil/Medio)

Este es el método más limpio y no requiere herramientas externas.

**Requisitos:** Tener el juego instalado y acceso al servidor.
**Pasos Detallados:**

1.  **Entra al servidor** y espera a que carguen todos los scripts.
2.  Pulsa `F8` y escribe `nui_devtools`. Se abrirá una ventana de inspección.
3.  **Filtrado de Datos:**
    - En la ventana de inspección, ve a la pestaña **Network (Red)**.
    - Busca el icono de "Filtro" (embudo) y escribe `json`.
    - Dentro del juego, realiza acciones que muestren información de otros: abre el marcador (`TAB`), el chat (`T`), o menús de administración si los tienes.
4.  **Identificación del paquete:**
    - Busca peticiones llamadas `names`, `players`, `GetScoreboardData`, o similares.
    - Haz clic derecho sobre la petición -> **Open in new tab**.
    - Verás un archivo de texto con todos los IDs. Puedes usar `Ctrl + F` para buscar "discord:".

---

## 🟡 MÉTODO 2: Sniffing de Red con Wireshark (Nivel: Medio/Avanzado)

Útil para servidores que ocultan su IP real tras un Proxy de FiveM.

**Herramientas:** [Wireshark](https://www.wireshark.org/)
**Pasos Detallados:**

1.  Instala Wireshark y ábrelo seleccionando tu tarjeta de red activa (WiFi o Ethernet).
2.  En el filtro de arriba escribe: `udp.port == 30120` (o el puerto del servidor).
3.  Inicia la captura (icono de aleta de tiburón azul).
4.  **Lanza FiveM y conéctate al servidor.**
5.  Observa los paquetes. Aunque FiveM use un proxy, durante la negociación inicial de la conexión (Handshake), a veces se envían paquetes `STUN` o de sincronización directamente a la IP del host.
6.  Busca paquetes entrantes/salientes con una IP que **no sea** de Cloudflare o de la lista oficial de FiveM. Esa será la IP real.

---

## 🟠 MÉTODO 3: Fiddler Everywhere - Intercepción HTTP/S (Nivel: Medio)

Perfecto para ver qué datos envía el juego a las APIs del servidor.

**Herramientas:** [Fiddler Everywhere](https://www.telerik.com/fiddler/fiddler-everywhere)
**Pasos Detallados:**

1.  Abre Fiddler y activa **"Capture HTTPS Traffic"** en la configuración.
2.  Abre FiveM. Fiddler empezará a listar todas las peticiones web que hace el juego.
3.  Busca peticiones hacia dominios como `.cfx.re` o IPs directas.
4.  Inspecciona los **Headers** y el **Body** (Cuerpo) de las respuestas. Muchos servidores envían la configuración completa (incluyendo scripts y variables ocultas) por HTTP antes de entrar al túnel UDP.

---

## 🔴 MÉTODO 4: OSINT y Bases de Datos Externas (Nivel: Experto)

Cuando no puedes entrar al servidor pero tienes un nombre de usuario o un Steam Hex.

**Herramientas/Sitios:**

- **SteamID.io:** Para convertir Steam Hex -> Steam ID de 64 bits.
- **VacList / Steam2Discord:** Servicios que almacenan la vinculación histórica de usuarios.
- **GitHub/SourceGraph:** Busca el nombre del servidor o de los desarrolladores. Muchas veces dejan las IPs o los bots de Discord con permisos abiertos en repositorios públicos.

---

## 🔥 MÉTODO 5: Explotación de txAdmin mal configurado

Muchos dueños creen que txAdmin es seguro por tener contraseña, pero dejan rutas de lectura abiertas.

**Rutas Críticas para investigar (Pégalas en tu navegador):**

- `http://IP:40120/diagnostics` -> A veces muestra la ruta local de los archivos (ej: `C:/Users/Admin/Desktop/...`), revelando el nombre de usuario de la máquina.
- `http://IP:40120/logs/setup.log` -> Muestra el historial de instalación y a veces tokens.
- `http://IP:40120/cfg/server.cfg` -> Aunque suele estar bloqueado, algunos paneles mal configurados permiten leer el archivo de configuración si no tienen bien los permisos de archivos de Windows.

---

## ⚠️ ADVERTENCIA DE SEGURIDAD

1.  **Anti-Cheats:** Herramientas como Wireshark o Fiddler son seguras. Herramientas que lean la memoria RAM (como Cheat Engine o Scanners de memoria) **te banearán** por Global Ban de FiveM. No las uses mientras el proceso `FiveM.exe` esté abierto.
2.  **Uso de Datos:** Esta guía es para investigación y fortalecimiento de tu propio bot. No nos hacemos responsables de ataques realizados a terceros.

---

_Este documento es dinámico. Si encuentras un método nuevo, agrégalo aquí siguiendo el formato._
