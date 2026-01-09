import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import discord
from discord.ext import commands
import aiohttp # Reemplaza requests para no bloquear el bot
import re
import asyncio
import socket
import json
import os  # Added for path safety
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()
from datetime import datetime, timezone
from discord import ui, ButtonStyle

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("DISCORD_TOKEN") # Leemos el token de la variable de entorno de Render/Sistema
PREFIX = "."
DEFAULT_CFX_CODE = "ka5pqq" # Cambia esto por tu código de servidor por defecto
WEBHOOK_URL = "https://discord.com/api/webhooks/1456993989306749133/2JG3BvXA__irPAOcgx-R-lTPC7n7ScgWSgUl0jMmnR-staCUFK0b0upG2LwDHfck1ean"
JSON_AUTH_FILE = os.path.join(os.path.dirname(__file__), "web_auth", "registered_users.json")
MAPPINGS_FILE = os.path.join(os.path.dirname(__file__), "server_mappings.json")
AUTH_CHANNEL_ID = 1457771004813246748
AUTHORIZED_USERS_CACHE = set()

# --- IP DATABASE CONFIG ---
IP_DATABASE_WEBHOOK_ID = 1458115983507197984
IP_DATABASE_CHANNEL_ID = 1458115931141177576 
IP_DATABASE_WEBHOOK_URL = "https://discord.com/api/webhooks/1458115983507197984/MIlLparbI6tu_L_EXT_e60hZ7DAMnpInWE3LBFpmnNsHjRupD0GeiA9EsS3i4Ry6XTeb"
SERVER_IP_CACHE = {} # Cache: { "code": "ip:port" }
last_activity_time = time.time()

# --- WATCHER / AUTO-RESTART LOGIC ---

class RestartHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        self.last_restart = 0
        self.cooldown = 1  # Segundos de espera entre reinicios

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            current_time = time.time()
            if current_time - self.last_restart > self.cooldown:
                self.last_restart = current_time
                print(f"\n[Auto-Restart] Detectado cambio en {event.src_path}. Reiniciando...")
                self.callback()

def start_bot_process():
    # Ejecuta este mismo script con el argumento --child
    script_path = os.path.abspath(sys.argv[0])
    return subprocess.Popen([sys.executable, script_path, "--child"])

def start_web_server():
    # Ejecuta el servidor Flask
    web_server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_auth", "server.py")
    if os.path.exists(web_server_path):
        print(f"[System] Iniciando Servidor Web en {web_server_path}...")
        return subprocess.Popen([sys.executable, web_server_path])
    else:
        print(f"[Error] No se encontró el servidor web en {web_server_path}")
        return None

def run_watcher():
    print("[Auto-Restart] Iniciando bot con sistema de reinicio automático...")
    
    # Iniciar Servidor Web una sola vez
    web_process = start_web_server()
    
    process = start_bot_process()
    
    def restart_process():
        nonlocal process
        if process:
            try:
                process.terminate()
                process.wait(timeout=2)
            except:
                process.kill()
        process = start_bot_process()

    event_handler = RestartHandler(restart_process)
    observer = Observer()
    # Observar el directorio actual de forma recursiva
    observer.schedule(event_handler, path=".", recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
            # Verificar si el proceso del bot murió por error (no por reinicio)
            if process.poll() is not None:
                print("[Auto-Restart] El bot se detuvo inesperadamente. Reiniciando en 3s...")
                time.sleep(3)
                restart_process()
                
    except KeyboardInterrupt:
        observer.stop()
        if process:
            try: process.terminate()
            except: pass
        if web_process:
            try: web_process.terminate()
            except: pass
        print("\n[Auto-Restart] Deteniendo todo...")
    
    observer.join()

# --- BOT CODE ---
# Solo inicializamos el bot si somos el proceso hijo (o si no hay logic)
# Pero para que los decoradores funcionen, definimos las cosas globalmente.
# El run() final es lo que controlamos.

# Configuración de intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Necesario para info de usuarios y roles

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# --- DATOS (Puertos) ---
PORT_DESCRIPTIONS = {
    # Game Servers
    30120: "FiveM Server (Default)",
    30110: "FiveM Server (Alt)",
    30121: "FiveM Server (Alt 2)",
    40120: "txAdmin / FiveM Server",
    7777: "Unreal Engine Game Server",
    7778: "Unreal Engine Query",
    27015: "Source Engine (CS:GO, TF2)",
    27016: "Source RCON",
    25565: "Minecraft Server",
    25575: "Minecraft RCON",
    19132: "Minecraft Bedrock",
    3074: "Xbox Live",
    3478: "Steam In-Home Streaming",
    27036: "Steam Client",
    6112: "Battle.net",
    28960: "Call of Duty",
       
    # Web Servers & Panels
    80: "HTTP (Web)",
    443: "HTTPS (Web Seguro)",
    8080: "HTTP Proxy / Web Panel",
    8443: "HTTPS Alt / Web Panel",
    8000: "HTTP Dev Server",
    8888: "HTTP Alt",
    3000: "Node.js / React (Common Dev)",
    3001: "Node.js Alt",
    4000: "Ruby/Rails Dev",
    5000: "Flask/Python Web",
    5001: "Flask Alt",
    8081: "HTTP Proxy Alt",
    9000: "PHP-FPM / Portainer",
    9090: "Web Panel Alt (Cockpit)",
    10000: "Webmin (Panel Admin Linux)",
    2082: "cPanel",
    2083: "cPanel SSL",
    2086: "WHM",
    2087: "WHM SSL",
    2095: "Webmail",
    2096: "Webmail SSL",

    # Databases
    3306: "MySQL/MariaDB (FiveM Standard)",
    3307: "MySQL Alt",
    33060: "MySQL X Protocol",
    5432: "PostgreSQL",
    5433: "PostgreSQL Alt",
    6379: "Redis (Cache / FiveM)",
    6380: "Redis Alt",
    11211: "Memcached",
    1433: "SQL Server (Microsoft)",
    1434: "SQL Server Browser",
    27017: "MongoDB (NoSQL)",
    27018: "MongoDB Alt",
    27019: "MongoDB Shard",
    3050: "Firebird Database",
    5984: "CouchDB (NoSQL)",
    9042: "Cassandra (NoSQL)",
    7000: "Cassandra Cluster",
    7001: "Cassandra SSL",
    9200: "Elasticsearch",
    9300: "Elasticsearch Cluster",
    8529: "ArangoDB",
    28015: "RethinkDB",
    7474: "Neo4j",

     

    # Access/Remote Control
    21: "FTP (File Transfer)",
    22: "SSH (Secure Shell)",
    23: "Telnet (Insecure)",
    3389: "RDP (Windows Remote Desktop)",
    5900: "VNC (Remote Desktop)",
    5901: "VNC Display 1",
    5902: "VNC Display 2",
    5800: "VNC Web",
    4899: "Radmin",
    5938: "TeamViewer",
    102: "AnyDesk", 
    7070: "AnyDesk Alt",

    # Email
    25: "SMTP (Send Email)",
    465: "SMTPS (Secure SMTP)",
    587: "SMTP Submission",
    110: "POP3 (Receive Email)",
    995: "POP3S (Secure POP3)",
    143: "IMAP (Receive Email)",
    993: "IMAPS (Secure IMAP)",
    
    # File Sharing
    20: "FTP Data",
    69: "TFTP",
    115: "SFTP",
    137: "NetBIOS Name",
    138: "NetBIOS Datagram",
    139: "NetBIOS Session",
    445: "SMB/CIFS (Windows Share)",
    2049: "NFS",
    
    # VoIP & Others
    5060: "SIP (VoIP)",
    5061: "SIP TLS",
    9987: "TeamSpeak 3 Voice",
    10011: "TeamSpeak 3 Query",
    30033: "TeamSpeak 3 FileTransfer",
    
    # Proxy/VPN
    1080: "SOCKS Proxy",
    3128: "Squid Proxy",
    8123: "Polipo Proxy",
    1194: "OpenVPN",
    1723: "PPTP VPN",
    500: "IPSec IKE",
    4500: "IPSec NAT-T",
    
    # DevOps / Infrastructure
    5672: "RabbitMQ",
    15672: "RabbitMQ Management",
    2375: "Docker",
    2376: "Docker Secure",
    6443: "Kubernetes API",
    9418: "Git",
}

COMMON_PORTS = [
    30120, 30110, 30121, 40120, 7777, 25565, # Juegos
    80, 443, 8080, 8443, 8000, 8081, 3000, 5000, 9000, 10000, 2082, 2083, # Web/Paneles
    3306, 33060, 5432, 6379, 1433, 27017, 11211, # DB
    21, 22, 23, 3389, 5900 # Acceso
]

def get_port_description(port):
    return PORT_DESCRIPTIONS.get(port, "Desconocido")

# --- AUTH LOGIC ---
def is_user_authorized(user_id):
    """Verifica si el ID de usuario está en la caché cargada desde el canal"""
    return str(user_id) in AUTHORIZED_USERS_CACHE

async def log_bot_activity(user, command, ctx):
    """Loguea SOLO el comando help a un canal específico"""
    if command.name != "help":
        return

    target_channel_id = 1457002966732247103
    channel = bot.get_channel(target_channel_id)
    
    if not channel:
        try:
            channel = await bot.fetch_channel(target_channel_id)
        except:
            return

    embed = discord.Embed(
        title="📚 HELP COMMAND LOG",
        description=f"El usuario {user.mention} ha solicitado ayuda.",
        color=0x9b59b6,
        timestamp=datetime.now()
    )
    embed.add_field(name="👤 Usuario", value=f"{user.name} (`{user.id}`)", inline=True)
    embed.add_field(name="🏠 Servidor", value=f"{ctx.guild.name if ctx.guild else 'DMs'}", inline=True)
    embed.set_thumbnail(url=str(user.display_avatar.url))
    embed.set_footer(text="Help Logger Service")

    try:
        await channel.send(embed=embed)
    except:
        pass

# --- MAPPINGS LOGIC ---
def get_manual_mapping(code):
    """Obtiene una IP mapeada manualmente para un código CFX"""
    try:
        if not os.path.exists(MAPPINGS_FILE):
            return None
        with open(MAPPINGS_FILE, "r") as f:
            data = json.load(f)
            return data.get(code.lower())
    except:
        return None

def save_manual_mapping(code, ip_port):
    """Guarda una IP mapeada manualmente"""
    try:
        data = {}
        if os.path.exists(MAPPINGS_FILE):
            with open(MAPPINGS_FILE, "r") as f:
                data = json.load(f)
        
        data[code.lower()] = ip_port
        with open(MAPPINGS_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return True
    except:
        return False

# --- LOAD IPs FROM DISCORD CHANNEL ---
async def load_server_db():
    """Carga la base de datos de IPs leyendo el historial del canal"""
    print(f"[DB] Iniciando sincronización desde el canal {IP_DATABASE_CHANNEL_ID}...")
    try:
        channel = bot.get_channel(IP_DATABASE_CHANNEL_ID)
        if not channel:
            channel = await bot.fetch_channel(IP_DATABASE_CHANNEL_ID)
            
        if not channel:
            print(f"[DB Error] No se pudo acceder al canal {IP_DATABASE_CHANNEL_ID}")
            return

        print(f"[DB] Leyendo historial del canal: {channel.name}...")
        
        count = 0
        async for message in channel.history(limit=1000): # Aumentamos el límite
            if not message.embeds:
                continue
                
            for embed in message.embeds:
                cfx_code = None
                ip_addr = None
                
                # Buscar en los campos (fields)
                for field in embed.fields:
                    f_name = field.name.lower()
                    if "cfx code" in f_name or "código" in f_name:
                        cfx_code = field.value.replace("`", "").strip().lower()
                    elif "ip address" in f_name or "dirección" in f_name or "ip" in f_name:
                        ip_addr = field.value.replace("`", "").strip()
                
                # Si no lo encontró en fields, buscar en descripción o título (por si acaso)
                if not cfx_code and embed.title and "CFX" in embed.title:
                    # Lógica extra de fallback si fuera necesario
                    pass

                if cfx_code and ip_addr and "Protegida" not in ip_addr:
                    SERVER_IP_CACHE[cfx_code] = ip_addr
                    count += 1
                    
        print(f"[DB] Sincronización completada. {count} servidores cargados en memoria.")
        
    except Exception as e:
        print(f"[DB Error] Falló la carga de IPs: {e}")

# --- FUNCIONES DE UTILIDAD (Adaptadas de cfx.py) ---

def limpiar_query(q):
    q = link = q.strip()
    q = re.sub(r"(https?://)?(www\.)?cfx\.re/join/", "", q, flags=re.I)
    if "/" in q:
        q = q.split("/")[-1]
    return q

async def fetch_server_data(code):
    url = f"https://servers-frontend.fivem.net/api/servers/single/{code}"
    # Cabeceras que imitan a un navegador real para evitar bloqueos
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://cfx.re/",
        "Accept": "application/json"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as r:
                if r.status == 200:
                    return await r.json()
                else:
                    print(f"[Debug] Error API FiveM: Status {r.status} para código {code}")
    except Exception as e:
        print(f"[Debug] Error de conexión API FiveM: {e}")
    return None

async def check_port_async(ip, port):
    """Verifica puerto de forma asíncrona"""
    try:
        fut = asyncio.open_connection(ip, port)
        # Esperar 0.5s máximo
        await asyncio.wait_for(fut, timeout=0.5)
        # Si conecta, cerramos y retornamos True
        return port
    except:
        return None

# --- VISTAS INTERACTIVAS (BOTONES) ---

class PlayersPaginator(discord.ui.View):
    def __init__(self, players):
        super().__init__(timeout=120)
        self.players = players
        self.page = 0
        self.per_page = 15
        self.max_page = max(0, (len(players) - 1) // self.per_page)
        self.update_buttons()

    def update_buttons(self):
        # [0] is prev, [1] is next
        self.children[0].disabled = (self.page <= 0)
        self.children[1].disabled = (self.page >= self.max_page)

    def get_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        current_players = self.players[start:end]
        
        embed = discord.Embed(title=f"Jugadores ({len(self.players)}) - Pág {self.page + 1}/{self.max_page + 1}", color=discord.Color.blue())
        
        desc = ""
        for p in current_players:
            name = p.get('name', 'Desconocido')
            # Limpiar códigos de color (ej: ^1, ^9) del nombre
            name = re.sub(r"\^[0-9]", "", name).strip()
            pid = p.get('id', '?')
            ping = p.get('ping', '?')
            identifiers = p.get('identifiers', [])
            discord_id = ""
            license_id = ""
            
            for i in identifiers:
                if i.startswith("discord:"):
                    discord_id = i.replace("discord:", "")
                elif i.startswith("license:"):
                    license_id = i
            
            desc += f"**[{pid}]** {name} (Ping: {ping})\n"
            if discord_id:
                desc += f"Discord: <@{discord_id}> (`{discord_id}`)\n"
            if license_id:
                desc += f"Licencia: `{license_id.replace('license:', '')}`\n"
                
        embed.description = desc
        return embed

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_page:
            self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

class ServerView(discord.ui.View):
    def __init__(self, data, server_ip, code=None, players_url=None):
        super().__init__(timeout=120)
        self.data = data
        self.server_ip = server_ip
        self.code = code
        self.players_url = players_url
        
        # Añadir botón de conexión si tenemos el código
        if self.code:
            self.add_item(discord.ui.Button(
                label="Conectarse", 
                url=f"https://cfx.re/join/{self.code}", 
                style=discord.ButtonStyle.link,
                emoji="🎮",
                row=0 # Asegurar que aparezca primero o en la fila superior
            ))

    @discord.ui.button(label="Ver Jugadores", style=discord.ButtonStyle.primary, emoji="👥")
    async def show_players(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        players = []
        source = "Master List"

        # 1. Intentar players.json directo y puertos alternativos en esa IP
        if self.players_url or self.server_ip:
            target_ips = []
            if self.server_ip: target_ips.append(self.server_ip.split(":")[0])
            if self.players_url and "http" in self.players_url:
                # Extraer IP de la URL actual
                match = re.search(r"//([^:/]+)", self.players_url)
                if match: target_ips.append(match.group(1))
            
            # Limpiar duplicados
            target_ips = list(set([ip for ip in target_ips if ip]))
            
            # Puertos a probar para la lista de jugadores
            ports_to_try = ["30120", "30121", "30110"]
            
            async with aiohttp.ClientSession() as session:
                for ip in target_ips:
                    if players and any('identifiers' in p for p in players if isinstance(p, dict)): break
                    for port in ports_to_try:
                        url = f"http://{ip}:{port}/players.json"
                        try:
                            async with session.get(url, headers=headers, timeout=3) as r:
                                if r.status == 200:
                                    players = await r.json()
                                    source = f"Direct IP ({ip}:{port})"
                                    print(f"[Debug] ¡ÉXITO! IDs extraídos desde {url}")
                                    break
                        except: continue
        
        # 2. MÉTODO ALTERNATIVO: txAdmin (40120/40121)
        if (not players or not any('identifiers' in p for p in players if isinstance(p, dict))) and self.server_ip:
            clean_ip = self.server_ip.split(":")[0] if ":" in self.server_ip else self.server_ip
            tx_urls = [f"http://{clean_ip}:40120/players.json", f"http://{clean_ip}:40121/players.json"]
            
            for tx_url in tx_urls:
                if players and any('identifiers' in p for p in players if isinstance(p, dict)): break
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(tx_url, headers=headers, timeout=3) as r:
                            if r.status == 200:
                                tx_data = await r.json()
                                players = tx_data if isinstance(tx_data, list) else tx_data.get('players', [])
                                source = "txAdmin (40120)"
                except: continue

        # 3. Fallback a la Master List
        if not players:
            players = self.data.get('Data', {}).get('players') or self.data.get('players') or []
        
        if not players:
            await interaction.followup.send("❌ No se pudo obtener la lista de jugadores. El servidor tiene el puerto cerrado o es privado.", ephemeral=True)
            return

        # Comprobar si tenemos IDs de Discord
        has_ids = any('identifiers' in p and any('discord' in i for i in p['identifiers']) for p in players if isinstance(p, dict))
        
        # Si no hay IDs, intentar buscar un leak del dueño en info.json
        leak_msg = ""
        if not has_ids and self.server_ip:
            try:
                clean_ip = self.server_ip.split(":")[0] if ":" in self.server_ip else self.server_ip
                info_url = f"http://{clean_ip}:30120/info.json"
                async with aiohttp.ClientSession() as session:
                    async with session.get(info_url, headers=headers, timeout=3) as r:
                        if r.status == 200:
                            info_data = await r.json()
                            # Buscar menciones a discord en los vars
                            vars_str = str(info_data.get('vars', {}))
                            found_discord = re.search(r"discord:(\d{17,19})", vars_str)
                            if found_discord:
                                leak_msg = f"\n\n⚠️ **Nota:** No hay IDs de jugadores, pero encontré este Discord en la configuración: <@{found_discord.group(1)}>"
            except: pass

        # Ordenar
        try: players.sort(key=lambda x: int(x.get('id', 0)))
        except: pass

        paginator = PlayersPaginator(players)
        embed = paginator.get_embed()
        
        footer_text = f"Petición vía: {source}"
        if not has_ids:
            footer_text += " | 🔒 Identificadores Protegidos"
        
        embed.set_footer(text=footer_text)
        
        if leak_msg:
            await interaction.followup.send(content=f"🔎 **Información Extra:** {leak_msg}", embed=embed, view=paginator, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, view=paginator, ephemeral=True)

    @discord.ui.button(label="Ver Recursos", style=discord.ButtonStyle.secondary, emoji="📦")
    async def show_resources(self, interaction: discord.Interaction, button: discord.ui.Button):
        resources = self.data.get('Data', {}).get('resources') or self.data.get('resources') or []
        
        if not resources:
            await interaction.response.send_message("No hay información de recursos.", ephemeral=True)
            return
            
        # Unir recursos en un string, cuidado con el limite de 4096 chars
        res_str = ", ".join(resources)
        if len(res_str) > 4000:
            res_str = res_str[:4000] + "..."
            
        embed = discord.Embed(title=f"Recursos ({len(resources)})", description=res_str, color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Escanear Puertos", style=discord.ButtonStyle.danger, emoji="🔍")
    async def scan_ports(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.server_ip or "http" in self.server_ip:
            await interaction.response.send_message("❌ No hay una IP directa disponible para escanear (el servidor usa proxy o URL).", ephemeral=True)
            return

        await interaction.response.send_message(f"🔎 Escaneando puertos comunes en `{self.server_ip}`... esto puede tardar unos segundos...", ephemeral=True)
        
        # Usar lista global
        open_ports = []
        tasks = [check_port_async(self.server_ip, p) for p in COMMON_PORTS]
        results = await asyncio.gather(*tasks)
        
        for res in results:
            if res:
                open_ports.append(res)
                
        if open_ports:
            desc = ""
            for p in sorted(open_ports):
                desc += f" - **{p}**: {get_port_description(p)}\n"
            msg = f"**Puertos Abiertos en {self.server_ip}:**\n{desc}"
        else:
            msg = f"❌ No se encontraron puertos comunes abiertos en {self.server_ip} (o firewall activo)."
            
        await interaction.followup.send(msg, ephemeral=True)

# --- COMANDOS ---
ALLOWED_GUILD_ID = 1446491205604081686
ALLOWED_USER_ID = 770058215961657374

@bot.check
async def global_access_check(ctx):
    """Check de acceso robusto con botón de registro"""
    # Siempre permitir al dueño (ALLOWED_USER_ID)
    if ctx.author.id == ALLOWED_USER_ID:
        return True
        
    if is_user_authorized(ctx.author.id):
        return True
        
    # User no autorizado - Crear Vista con Botón
    try:
        class RegisterView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                # Reemplaza localhost con tu IP si es necesario
                self.add_item(discord.ui.Button(
                    label="Registrarse / Autorizar",
                    url="https://bot-autorizaci-n.vercel.app/",
                    style=discord.ButtonStyle.link,
                    emoji="🛡️"
                ))

        embed = discord.Embed(
            title="🔒 ACCESO RESTRINGIDO",
            description=f"Hola {ctx.author.mention}, tu cuenta no está autorizada en nuestro sistema.\n\n"
                        f"Para usar los comandos del bot, por favor haz clic en el botón de abajo y regístrate.",
            color=0xff3366
        )
        embed.set_footer(text="Seguridad Ozyat v2.0")
        
        await ctx.send(embed=embed, view=RegisterView())
    except Exception as e:
        print(f"Error in access check message: {e}")
        
    return False

# Evento para loguear comandos exitosos
@bot.event
async def on_command_completion(ctx):
    await log_bot_activity(ctx.author, ctx.command, ctx)

# Manejador de errores global
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        # Si falla el check, ignoramos silenciosamente
        return
    # Dejar pasar otros errores
    raise error


@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    
    # Cargar usuarios autorizados desde el canal
    print("[Auth] Cargando base de datos desde el canal de discord...")
    channel = bot.get_channel(AUTH_CHANNEL_ID)
    if not channel:
        try: channel = await bot.fetch_channel(AUTH_CHANNEL_ID)
        except: print(f"[Auth Error] No pude acceder al canal {AUTH_CHANNEL_ID}")
    
    if channel:
        count = 0
        async for message in channel.history(limit=100): # Limitamos a los últimos 100 para velocidad
            content = message.content.strip()
            if content.isdigit(): 
                AUTHORIZED_USERS_CACHE.add(content)
                count += 1
        print(f"[Auth] {count} usuarios recientes cargados en memoria.")

    # Cargar base de datos de IPs
    bot.loop.create_task(load_server_db())

@bot.event
async def on_message(message):
    # Escuchar nuevos registros en tiempo real
    if message.channel.id == AUTH_CHANNEL_ID:
        content = message.content.strip()
        if content.isdigit():
            AUTHORIZED_USERS_CACHE.add(content)
            print(f"[Auth] Nuevo usuario autorizado detectado al instante: {content}")
    
    await bot.process_commands(message)

@bot.command(name="help")
async def help(ctx):
    embed = discord.Embed(
        title="OZYAT BOT | Sistema de Control", 
        description="Lista de comandos disponibles para el sistema.", 
        color=0x00f2ff
    )
    
    # Comandos Principales
    embed.add_field(
        name="Análisis & Red",
        value=(
            "`.cfx <código/url>` - Análisis de servidor FiveM.\n"
            "`.ip <ip>` - Información detallada de una IP.\n"
            "`.ports <ip>` - Escaneo de puertos comunes."
        ),
        inline=False
    )
    
    # Comandos de Base de Datos
    embed.add_field(
        name="Gestión de Datos",
        value=(
            "`.add <ip:puerto> <code>` - Mapeo manual local.\n"
            "`.addip <código>` - Registrar IP en base de datos global."
        ),
        inline=False
    )
    
    # Comandos de Utilidad
    embed.add_field(
        name="Utilidad",
        value=(
            "`.status <on|off|mant>` - Estado del servidor.\n"
            "`.clear <cantidad>` - Borra mensajes (Admin).\n"
            "`.ping` - Latencia del bot."
        ),
        inline=False
    )
    
    # Comandos de Usuario
    embed.add_field(
        name="Usuario",
        value=(
            "`.avatar <user>` - Muestra avatar.\n"
            "`.userinfo <user>` - Info de cuenta.\n"
            "`.serverinfo` - Info del Discord."
        ),
        inline=False
    )
    
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(text=f"Solicitado por {ctx.author.name} • v2.5", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    """Muestra la latencia del bot."""
    latencia = round(bot.latency * 1000)
    await ctx.send(f"🏓 **Pong!** Latencia: `{latencia}ms`")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    """Muestra el avatar de un usuario."""
    member = member or ctx.author
    embed = discord.Embed(title=f"Avatar de {member.display_name}", color=discord.Color.random())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    """Muestra información sobre un usuario."""
    member = member or ctx.author
    embed = discord.Embed(title=f"Información de {member.display_name}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🆔 ID", value=member.id, inline=True)
    embed.add_field(name="📅 Creación", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="📥 Entrada", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="🤖 Bot?", value="Sí" if member.bot else "No", inline=True)
    roles = [r.mention for r in member.roles if r.name != "@everyone"]
    embed.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles) if roles else "Ninguno", inline=False)
    embed.set_footer(text="By: al3xg0nzalezzz")
    
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    """Muestra información del servidor de Discord."""
    guild = ctx.guild
    embed = discord.Embed(title=f"Info de {guild.name}", color=discord.Color.gold())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Dueño", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 Miembros", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Creado", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="💬 Canales", value=len(guild.channels), inline=True)
    embed.set_footer(text=f"By: al3xg0nzalezzz")
    
    await ctx.send(embed=embed)

@bot.command(hidden=True)
async def shutdown(ctx):
    """Apaga el bot. Útil para matar instancias fantasmas."""
    await ctx.send("🔌 Apagando esta instancia del bot... (Si soy un fantasma, no volveré).")
    await bot.close()
    sys.exit(0)

@bot.command(name="status")
@commands.has_permissions(administrator=True)
async def status(ctx, estado: str = None):
    """Establece el estado del servidor: on, off, mantenimiento."""
    if not estado:
        await ctx.send("❌ Uso: `.status on` | `.status off` | `.status mantenimiento`")
        return

    target_channel_id = 1450050187421548644
    channel = bot.get_channel(target_channel_id)
    
    if not channel:
        # Intentar buscarlo si no está en caché
        try:
            channel = await bot.fetch_channel(target_channel_id)
        except:
            await ctx.send(f"❌ No se pudo encontrar el canal con ID {target_channel_id}.")
            return

    estado = estado.lower()
    
    embed = None
    mencion = ""

    if estado == "on":
        mencion = "@everyone"
        embed = discord.Embed(
            title="🟢 ESTADO DEL SERVIDOR",
            description=f">>> **El servidor se encuentra actualmente:** `ONLINE`",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

    elif estado == "off":
        mencion = "@here" # Menos intrusivo para avisos de apagado
        embed = discord.Embed(
            title="🔴 ESTADO DEL SERVIDOR",
            description=">>> **El servidor se encuentra actualmente:** `OFFLINE`\n\nEstamos realizando tareas internas o apagado programado.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

    elif estado == "mantenimiento":
        mencion = "@here"
        embed = discord.Embed(
            title="🟠 MANTENIMIENTO",
            description=">>> **El servidor entra en:** `MANTENIMIENTO`\n\nEstamos aplicando mejoras y correcciones. Volveremos pronto.",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

    else:
        await ctx.send("❌ Estado desconocido. Opciones: `on`, `off`, `mantenimiento`.")
        return
    
    # Footer común
    embed.set_footer(text=f"Actualizado por {ctx.author.display_name}")

    try:
        if estado == "on":
            # view = discord.ui.View()
            # view.add_item(discord.ui.Button(label="Conectarse", url=f"https://cfx.re/join/{DEFAULT_CFX_CODE}", emoji="🎮"))
            await channel.send(content=mencion, embed=embed) #, view=view)
        else:
            await channel.send(content=mencion, embed=embed)
            
        await ctx.send(f"✅ Estado publicado en {channel.mention}.")
    except Exception as e:
        await ctx.send(f"❌ Error al enviar mensaje: {e}")

@status.error
async def status_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ No tienes permisos de Administrador para usar este comando.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Se han eliminado {amount} mensajes.", delete_after=3)

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ No tienes permisos para borrar mensajes.", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Uso: `.clear <cantidad>`", delete_after=5)

@bot.command()
async def cfx(ctx, query: str = None):
    if not query:
        await ctx.send("Uso: `.cfx <código o url>`")
        return

    msg = await ctx.send("🔍 Analizando servidor...")
    
    code = limpiar_query(query)
    data = await fetch_server_data(code)
    
    manual_ip = get_manual_mapping(code)

    if not data and not manual_ip:
        await msg.edit(content="❌ No se encontró información del servidor. Verifica el código.")
        return
        
    # Si no hay data de FiveM pero hay mapping manual, creamos un objeto 'Data' mínimo
    if not data and manual_ip:
        data = {
            "Data": {
                "hostname": f"Server Manual ({code})",
                "connectEndPoints": [manual_ip],
                "clients": 0,
                "svMaxclients": 0,
                "ownerName": "Manual Registry",
                "vars": {}
            }
        }

    # Revisar Cache de Discord (Database Channel)
    cached_ip = SERVER_IP_CACHE.get(code.lower())
    
    # --- PROCESAMIENTO ---
    info = data.get('Data', {}) or data
    hostname = info.get('hostname', 'Desconocido')
    hostname_clean = re.sub(r"\^[0-9]", "", hostname).strip()
    
    endpoints = info.get('connectEndPoints') or data.get('connectEndPoints') or []
    primary_endpoint = endpoints[0] if endpoints else None
    
    resolved_ip = None
    players_url = None
    is_proxy_protected = False
    
    # 1. Resolver IP y Link
    async def get_ip_from_endpoint(ep):
        try:
            target = ep.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
            # Check si es IP
            try:
                socket.inet_aton(target)
                return target, False # Es IP directa
            except:
                pass
            # Resolver DNS
            return await bot.loop.run_in_executor(None, socket.gethostbyname, target), True # Es Dominio (Posible Proxy)
        except:
            return None, False

    if primary_endpoint:
        resolved_ip, is_domain = await get_ip_from_endpoint(primary_endpoint)
        is_proxy_protected = is_domain
        
        # Link Players
        if "http" in primary_endpoint:
            base = primary_endpoint.rstrip("/")
            players_url = f"{base}/players.json"
        else:
            players_url = f"http://{primary_endpoint}/players.json"

    # 2. Buscar LEAKS
    server_vars = info.get('vars', {})
    ip_regex = r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
    leaked_ips = []
    
    real_ip_found = None

    for key, value in server_vars.items():
        matches = re.findall(ip_regex, str(value))
        for match in matches:
            if not match.startswith("127.0.") and not match.startswith("192.168."):
                if resolved_ip and match != resolved_ip:
                     leaked_ips.append(f"`{match}` ({key})")
                     # Si encontramos un leak y parece válido, esa es nuestra "Real IP" para escanear
                     if not real_ip_found:
                         real_ip_found = match

    # Si encontramos una IP real por leak, ya no está "protegido" para el escáner
    if real_ip_found:
        resolved_ip = real_ip_found
        is_proxy_protected = False
    elif cached_ip:
        # Si tenemos IP en caché (leída del canal), la usamos como prioritaria
        resolved_ip = cached_ip
        is_proxy_protected = False
        # Nota: Podríamos verificar si la IP cached sigue viva, pero confiamos en la DB por ahora.

    # --- DATOS GENERALES ---
    clients = info.get('clients', 0)
    max_clients = info.get('svMaxclients') or info.get('sv_maxclients', 0)
    owner = info.get('ownerName', 'Desconocido')

    # --- EMBED ---
    embed = discord.Embed(title=hostname_clean[:250], url=f"https://cfx.re/join/{code}", color=0xFFA500)
    
    connect_value = f"`{primary_endpoint}`" if primary_endpoint else "`Oculto`"
    connect_value += f"\n🔗 [Click para entrar](https://cfx.re/join/{code})"
    
    embed.add_field(name="Connect", value=connect_value, inline=False)
    
    if manual_ip:
        embed.add_field(name="📍 IP Capturada (Manual)", value=f"`{manual_ip}`", inline=False)
    elif real_ip_found:
        embed.add_field(name="🔓 IP Real (Detectada)", value="\n".join(leaked_ips[:5]), inline=False)
    elif cached_ip:
        embed.add_field(name="📂 IP Database", value=f"`{cached_ip}`", inline=False)
    elif is_proxy_protected:
        embed.add_field(name="🔒 IP Real", value="`Imposible resolver (Protegida)`", inline=False)
    
    p_txt = f"[{clients}/{max_clients}]({players_url})" if players_url else f"{clients}/{max_clients}"
    embed.add_field(name="Jugadores", value=p_txt, inline=True)
    
    embed.add_field(name="Dueño", value=owner, inline=True)
    embed.add_field(name="CFX Code", value=f"`{code}`", inline=True)
    
    if 'vars' in info and 'banner_detail' in info['vars']:
        embed.set_image(url=info['vars']['banner_detail'])
    
    embed.set_footer(text=f"Solicitado por {ctx.author.display_name} • Ozyat Bot • By: al3xg0nzalezzz")

    # --- MEJORA: Re-construir players_url si tenemos IP real ---
    # Si tenemos una IP resuelta/real que no es el endpoint original, intentamos ir directo
    if resolved_ip and not is_proxy_protected:
        # Si el resolved_ip no tiene puerto, le ponemos el estándar o el que tuviera el endpoint
        final_port = "30120"
        if primary_endpoint and ":" in primary_endpoint:
            final_port = primary_endpoint.split(":")[-1]
        
        # Esta es la URL "agresiva" que el bot usará para bypass
        players_url = f"http://{resolved_ip}:{final_port}/players.json"

    # Pasar flag is_proxy para deshabilitar botón si es necesario
    view = ServerView(data, resolved_ip if not is_proxy_protected else None, code=code, players_url=players_url)
    await msg.edit(content=None, embed=embed, view=view)

@bot.command(name="ports")
async def ports(ctx, *args):
    """
    Escanea puertos comunes en una o varias IPs.
    Uso: .ports <ip> <ip2> ...
    Soporta formato ip:puerto (se ignora el puerto y se escanean los comunes).
    """
    if not args:
        await ctx.send("❌ Uso: `.ports <ip>` (puedes poner varias separadas por espacio)")
        return

    # Procesar argumentos para soportar comas y espacios
    targets_raw = []
    for arg in args:
        targets_raw.extend(arg.split(','))
    
    # Limpiar vacíos
    targets_raw = [t.strip() for t in targets_raw if t.strip()]

    if not targets_raw:
        await ctx.send("No se detectaron IPs válidas.")
        return

    # Reaccionar para indicar que se recibió el comando
    try:
        await ctx.message.add_reaction("📩")
    except:
        pass

    scan_output = []

    for raw_target in targets_raw:
        # Limpiar protocolo si lo pegan
        target_clean = raw_target.replace("http://", "").replace("https://", "")
        # Quitar path si tiene
        target_clean = target_clean.split("/")[0]
        # Separar IP de puerto si viene ip:port
        ip_candidate = target_clean.split(":")[0]

        # Resolver IP si es dominio
        final_ip = None
        is_hostname = False
        try:
            socket.inet_aton(ip_candidate)
            final_ip = ip_candidate
        except:
            # Intentar resolver
            try:
                final_ip = await bot.loop.run_in_executor(None, socket.gethostbyname, ip_candidate)
                is_hostname = True
            except:
                scan_output.append(f"[!] **{raw_target}**: Protegida o dominio no resuelto.")
                continue
        
        # Escanear
        tasks = [check_port_async(final_ip, p) for p in COMMON_PORTS]
        results = await asyncio.gather(*tasks)
        
        open_ports = [p for p in results if p]
        
        header = f"Resultados para **{raw_target}**"
        if final_ip != ip_candidate or is_hostname:
            header += f" (`{final_ip}`)"
            
        if open_ports:
            lines = [f"[+] **{header}**"]
            for p in sorted(open_ports):
                lines.append(f" - `{p}`: {get_port_description(p)}")
            scan_output.append("\n".join(lines))
        else:
            scan_output.append(f"[-] **{header}**: Ningún puerto común abierto (o Firewall).")

    # Enviar respuesta al privado del usuario
    full_response = "\n\n".join(scan_output)
    
    try:
        target_dest = ctx.author
        if len(full_response) > 1900:
            chunks = [full_response[i:i+1900] for i in range(0, len(full_response), 1900)]
            await target_dest.send("**Reporte de Escaneo de Puertos** (Resultados extendidos):")
            for chunk in chunks:
                await target_dest.send(chunk)
        else:
            await target_dest.send(f"**Reporte de Escaneo de Puertos**:\n\n{full_response}")
    except discord.Forbidden:
        await ctx.send(f"{ctx.author.mention} No puedo enviarte el MD. Tienes los mensajes privados bloqueados.")

@bot.command(name="ip")
@commands.guild_only()
async def ip(ctx, ip: str = None):
    global last_activity_time
    last_activity_time = time.time()

    if not ip:
        await ctx.reply("👻 Proporciona una IP. Ejemplo: `.ip 8.8.8.8`")
        return

    msg = await ctx.reply(f"⏳ Consultando `{ip}`...")

    # Sistema Multi-API con fallback
    apis = [
        {
            "name": "ip-api.com",
            "url": f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,offset,currency,isp,org,as,asname,reverse,mobile,proxy,hosting,query&lang=es",
            "timeout": 8,
            "parser": lambda d: d if d.get("status") == "success" else None
        },
        {
            "name": "ipapi.co",
            "url": f"https://ipapi.co/{ip}/json/",
            "timeout": 8,
            "parser": lambda d: {
                "query": d.get("ip"),
                "country": d.get("country_name"),
                "countryCode": d.get("country_code"),
                "region": d.get("region_code"),
                "regionName": d.get("region"),
                "city": d.get("city"),
                "zip": d.get("postal"),
                "lat": d.get("latitude"),
                "lon": d.get("longitude"),
                "timezone": d.get("timezone"),
                "offset": d.get("utc_offset"),
                "currency": d.get("currency"),
                "isp": d.get("org"),
                "org": d.get("org"),
                "as": d.get("asn"),
                "asname": d.get("org"),
                "reverse": "N/D",
                "mobile": False,
                "proxy": False,
                "hosting": False
            } if not d.get("error") else None
        },
        {
            "name": "ipinfo.io",
            "url": f"https://ipinfo.io/{ip}/json",
            "timeout": 8,
            "parser": lambda d: {
                "query": d.get("ip"),
                "country": d.get("country"),
                "countryCode": d.get("country"),
                "region": d.get("region"),
                "regionName": d.get("region"),
                "city": d.get("city"),
                "zip": d.get("postal"),
                "lat": d.get("loc", ",").split(",")[0] if d.get("loc") else "N/D",
                "lon": d.get("loc", ",").split(",")[1] if d.get("loc") and "," in d.get("loc") else "N/D",
                "timezone": d.get("timezone"),
                "offset": "",
                "currency": "N/D",
                "isp": d.get("org"),
                "org": d.get("org"),
                "as": d.get("org"),
                "asname": d.get("org"),
                "reverse": d.get("hostname", "N/D"),
                "mobile": False,
                "proxy": False,
                "hosting": False
            } if not d.get("error") and not d.get("bogon") else None
        }
    ]

    d = None
    used_api = None

    # Intentar cada API en orden
    for api_config in apis:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(api_config["url"], timeout=api_config["timeout"]) as r:
                    if r.status == 200:
                        raw_data = await r.json()
                        parsed_data = api_config["parser"](raw_data)
                        if parsed_data:
                            d = parsed_data
                            used_api = api_config["name"]
                            print(f"[IP Command] Usada API: {used_api}")
                            break
        except Exception as e:
            print(f"[IP Command] Falló {api_config['name']}: {e}")
            continue

    if not d:
        await msg.edit(content=f"❌ No se pudo obtener información de **{ip}**. Todas las APIs fallaron o la IP es inválida.")
        return

    try:
        e = discord.Embed(
            title=f"🌍 IP — {d.get('query', ip)}",
            description=f"📌 Información detallada sobre la IP consultada\n🔍 *Fuente: {used_api}*",
            color=0x6AB88E,
            timestamp=datetime.now(timezone.utc)
        )
        e.add_field(name="📍 Ubicación", value=f"{d.get('city','N/D')}, {d.get('regionName','N/D')}, {d.get('country','N/D')} ({d.get('countryCode','N/D')})", inline=False)
        e.add_field(name="🕰 Zona Horaria", value=f"{d.get('timezone','N/D')} {('(UTC' + str(d.get('offset')) + ')') if d.get('offset') else ''}", inline=True)
        e.add_field(name="🌐 Coordenadas", value=f"Lat: {d.get('lat','N/D')}, Lon: {d.get('lon','N/D')}", inline=False)
        e.add_field(name="📮 Código Postal", value=d.get('zip','N/D'), inline=True)
        if d.get('currency') and d.get('currency') != 'N/D':
            e.add_field(name="💱 Moneda", value=d.get('currency'), inline=True)
        e.add_field(name="🖥 ISP", value=d.get('isp','N/D'), inline=True)
        e.add_field(name="🏛 Organización", value=f"{d.get('org','N/D')} / {d.get('as','N/D')} ({d.get('asname','N/D')})", inline=False)
        if d.get('reverse') and d.get('reverse') != 'N/D':
            e.add_field(name="🔄 Reverse DNS", value=d.get('reverse'), inline=False)
        
        # Solo mostrar flags si están disponibles
        flags_value = f"{'Sí' if d.get('mobile') else 'No'} / {'Sí' if d.get('proxy') else 'No'} / {'Sí' if d.get('hosting') else 'No'}"
        if any([d.get('mobile'), d.get('proxy'), d.get('hosting')]):
            e.add_field(name="📱 Móvil / 🛡 Proxy / 🏠 Hosting", value=flags_value, inline=False)

        class CopyButton(ui.View):
            @ui.button(label="📋 Copiar", style=ButtonStyle.primary)
            async def copy(self, interaction: discord.Interaction, button: ui.Button):
                markdown_text = (
                    "```\n"
                    f"🌍 IP: {d.get('query','N/D')}\n"
                    f"📍 Ubicación: {d.get('city','N/D')}, {d.get('regionName','N/D')}, {d.get('country','N/D')} ({d.get('countryCode','N/D')})\n"
                    f"🕰 Zona Horaria: {d.get('timezone','N/D')} {('(UTC' + str(d.get('offset')) + ')') if d.get('offset') else ''}\n"
                    f"🌐 Coordenadas: Lat {d.get('lat','N/D')}, Lon {d.get('lon','N/D')}\n"
                    f"📮 Código Postal: {d.get('zip','N/D')}\n"
                    f"💱 Moneda: {d.get('currency','N/D')}\n"
                    f"🖥 ISP: {d.get('isp','N/D')}\n"
                    f"🏛 Organización: {d.get('org','N/D')} / {d.get('as','N/D')} ({d.get('asname','N/D')})\n"
                    f"Fuente: {used_api}\n"
                    "```"
                )
                try:
                    await interaction.user.send(f"📋 Información copiada:\n{markdown_text}")
                    await interaction.response.send_message("✅ Te envié la información en privado 📩", ephemeral=True)
                except:
                    await interaction.response.send_message("❌ No pude enviarte el mensaje privado.", ephemeral=True)

        await msg.edit(content=None, embed=e, view=CopyButton())

    except asyncio.TimeoutError:
        await msg.edit(content="⏱ Tiempo de espera agotado.")
    except Exception as e:
        print(f"[IP Command Error] {e}")
        await msg.edit(content=f"💀 Error al procesar la información: {e}")

@bot.command()
async def add(ctx, ip_port: str = None, code_url: str = None):
    """Vincula manualmente una IP a un código CFX"""
    if not ip_port or not code_url:
        await ctx.send("❌ Uso: `.add <ip:puerto> <codigo_o_url>`\nEjemplo: `.add 162.19.126.112:30120 bjyrxb`")
        return

    code = limpiar_query(code_url).lower()
    if save_manual_mapping(code, ip_port):
        # 1. Update Cache
        SERVER_IP_CACHE[code] = ip_port
        
        # 2. Local feedback
        embed = discord.Embed(
            title="✅ Mapeo Guardado (Local)",
            description=f"Se ha vinculado correctamente:\n**Código:** `{code}`\n**IP:** `{ip_port}`",
            color=0x00ff88,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Base de Datos Ozyat")
        await ctx.send(embed=embed)
        
        # 3. Mandar a la Webhook de la base de datos (Persistencia)
        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(IP_DATABASE_WEBHOOK_URL, session=session)
                wh_embed = discord.Embed(
                    title="📍 Entrada Manual Registrada",
                    description=f"Servidor mapeado manualmente por {ctx.author.name}",
                    color=0x3498db,
                    timestamp=datetime.now()
                )
                wh_embed.add_field(name="🏷️ CFX Code", value=f"`{code}`", inline=True)
                wh_embed.add_field(name="📍 IP Address", value=f"`{ip_port}`", inline=True)
                wh_embed.set_footer(text="Manual Entry Registry")
                await webhook.send(embed=wh_embed, username="CFX IP Database")
        except Exception as e:
            print(f"[Error] No se pudo enviar el mapeo manual a la webhook: {e}")
    else:
        await ctx.send("❌ Error al guardar el mapeo en el archivo.")



@bot.command()
async def addip(ctx, query: str = None):
    """
    Resuelve la IP de un servidor CFX y la envía a un canal de logs (Webhook).
    Uso: .addip <cfx_code>
    """
    if not query:
        await ctx.send("❌ Uso: `.addip <código cfx>`")
        return

    TARGET_WEBHOOK_URL = "https://discord.com/api/webhooks/1458115983507197984/MIlLparbI6tu_L_EXT_e60hZ7DAMnpInWE3LBFpmnNsHjRupD0GeiA9EsS3i4Ry6XTeb"

    # Feedback inicial
    msg = await ctx.send(f"🔍 Procesando servidor `{query}`...")

    code = limpiar_query(query)
    data = await fetch_server_data(code)
    manual_ip = get_manual_mapping(code)

    if not data and not manual_ip:
        await msg.edit(content="❌ No se encontró información del servidor. Verifica el código.")
        return

    # Si hay manual IP pero no data, fake data
    if not data and manual_ip:
        data = {
            "Data": {
                "hostname": f"Server Manual ({code})",
                "connectEndPoints": [manual_ip],
                "clients": 0,
                "svMaxclients": 0,
                "ownerName": "Manual Registry",
                "vars": {}
            }
        }

    # Procesar Datos
    info = data.get('Data', {}) or data
    hostname = info.get('hostname', 'Desconocido')
    hostname_clean = re.sub(r"\^[0-9]", "", hostname).strip()
    
    endpoints = info.get('connectEndPoints') or data.get('connectEndPoints') or []
    primary_endpoint = endpoints[0] if endpoints else None
    
    server_vars = info.get('vars', {})
    clients = info.get('clients', 0)
    max_clients = info.get('svMaxclients') or info.get('sv_maxclients', 0)
    
    # Lógica de Resolución de IP (Simplificada del comando .cfx)
    resolved_ip = manual_ip # Prioridad manual
    is_proxy = False
    
    if not resolved_ip and primary_endpoint:
        # Intentar resolver endpoint
        target = primary_endpoint.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        try:
            socket.inet_aton(target)
            resolved_ip = target # Es IP Directa
        except:
             # Es dominio
             is_proxy = True
             try:
                resolved_ip = await bot.loop.run_in_executor(None, socket.gethostbyname, target)
             except:
                pass
    
    # Buscar Leaks si no tenemos IP o es proxy
    if not resolved_ip or is_proxy:
        ip_regex = r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
        for key, value in server_vars.items():
            matches = re.findall(ip_regex, str(value))
            for match in matches:
                 if not match.startswith("127.0.") and not match.startswith("192.168."):
                      if resolved_ip and match != resolved_ip:
                           # Encontramos leak diferente a la IP resuelta (que podria ser proxy float)
                           resolved_ip = match
                           is_proxy = False # Ya no es protegida, tenemos leak

    # Construir Embed para Webhook
    embed = discord.Embed(
        title="📥 Nuevo Servidor Añadido",
        description=f"**{hostname_clean}**",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="🏷️ CFX Code", value=f"`{code}`", inline=True)
    embed.add_field(name="👥 Jugadores", value=f"{clients}/{max_clients}", inline=True)
    
    if resolved_ip:
        embed.add_field(name="📍 IP Address", value=f"`{resolved_ip}`", inline=False)
        embed.add_field(name="🔌 Connect Endpoint", value=f"`{primary_endpoint}`", inline=False)
    else:
        embed.add_field(name="🔒 IP Address", value="`Protegida / No Encontrada`", inline=False)

    embed.set_thumbnail(url="https://r2.fivemanage.com/pub/logo.png") # Logo genérico o del server
    
    # Intentar poner banner del server si existe
    if 'banner_detail' in server_vars:
        embed.set_image(url=server_vars['banner_detail'])
    
    embed.set_footer(text=f"Añadido por {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

    # Enviar a Webhook
    try:
        print(f"[Log] Intentando enviar a webhook: {code}")
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(IP_DATABASE_WEBHOOK_URL, session=session)
            await webhook.send(embed=embed, username="CFX IP Database")
        
        await msg.edit(content=f"✅ Servidor `{hostname_clean}` guardado correctamente en la base de datos (Webhook).")
        
        # Actualizar caché local instantáneamente
        if code and resolved_ip:
            SERVER_IP_CACHE[code.lower()] = resolved_ip
            
    except Exception as e:
        await msg.edit(content=f"❌ Error al enviar a la webhook: {str(e)}")


# --- EJECUCIÓN ---
if __name__ == "__main__":
    if "--child" in sys.argv:
        # Modo BOT: Ejecutar el bot de Discord
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"Error al iniciar el bot: {e}")
            print("Asegúrate de poner un TOKEN válido en la línea 12.")
    else:
        # Modo WATCHER: Ejecutar el monitor de cambios
        run_watcher()
