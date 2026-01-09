from flask import Flask, render_template, request, jsonify, redirect, session, url_for
import os
import json
import requests
from datetime import datetime
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- CONFIGURACIÓN DISCORD ---
# Datos de la app que me pasaste:
# Client ID: 1446262720578977823
# Client Secret: O_erWPGYfb4Mm9u6A7gVJR5-noGfulbt
CLIENT_ID = "1446262720578977823"
CLIENT_SECRET = "O_erWPGYfb4Mm9u6A7gVJR5-noGfulbt"
# NOTA: Asegúrate de que http://localhost:5000/callback esté en los Redirects de la aplicación en Discord Developer Portal
# O ajusta esto si usas un dominio/túnel
REDIRECT_URI = "http://localhost:5000/callback" 
WEBHOOK_URL = "https://discord.com/api/webhooks/1458969826671198376/RXcxTIPwKXKR-LRQOV3mbxcx47Vvxs3XfJSqZ894LAZfp-_IP_N542pxhSnyx7cn8lgO"
JSON_FILE = os.path.join(os.path.dirname(__file__), "registered_users.json")
LOGO = "https://i.pinimg.com/736x/10/e3/f5/10e3f51d11ef13d5c88cb329211146ba.jpg"

def load_data():
    if not os.path.exists(JSON_FILE): return {"authorized_users": {}}
    with open(JSON_FILE, "r") as f:
        try: return json.load(f)
        except: return {"authorized_users": {}}

def save_data(data):
    with open(JSON_FILE, "w") as f: json.dump(data, f, indent=4)

def get_ip():
    # Intenta obtener la IP real detrás de proxies (lógica de vercel_logger)
    ip = request.headers.get('x-real-ip') or request.headers.get('x-forwarded-for', request.remote_addr).split(',')[0].strip()
    return ip

@app.route("/")
def index():
    # Si ya hay una sesión activa, mostramos la página de "Ya estás dentro"
    if "user_id" in session:
        return render_template("success.html", username=session.get("username"), discord_id=session.get("user_id"))
    # Si no, mostramos tu portal de HTML
    return render_template("index.html")

@app.route("/login")
def login():
    # Usar el dominio específico de Vercel si estamos en producción
    host = request.headers.get('X-Forwarded-Host') or request.headers.get('Host') or request.host
    
    # Si estamos en Vercel, usar el dominio específico
    if 'vercel.app' in host or 'X-Forwarded-Host' in request.headers:
        base_url = "https://bot-autorizaci-n.vercel.app"
    elif 'onrender.com' in host:
        base_url = f"https://{host}"
    else:
        # Localhost o desarrollo
        scheme = request.headers.get('X-Forwarded-Proto', 'http')
        base_url = f"{scheme}://{host}"
    
    # Asegurar que no tenga slash final
    base_url = base_url.rstrip('/')
    redirect_uri = f"{base_url}/callback"
    
    # Debug: imprimir el redirect_uri que se está usando
    print(f"[DEBUG] Redirect URI: {redirect_uri}")
    
    # URL encode el redirect_uri para la URL de Discord
    encoded_redirect_uri = quote(redirect_uri, safe='')

    # Scopes para obtener información básica del usuario
    discord_auth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={encoded_redirect_uri}&response_type=code&scope=identify%20email"
    print(f"[DEBUG] Discord Auth URL: {discord_auth_url}")
    return redirect(discord_auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        # Si el usuario cancela o hay error, mandarlo a la web oficial de discord o login
        return redirect("https://discord.com/login")

    # Recalcular la misma URI dinámica para validar el token (debe coincidir exactamente con la del login)
    host = request.headers.get('X-Forwarded-Host') or request.headers.get('Host') or request.host
    
    # Usar el mismo dominio que en login
    if 'vercel.app' in host or 'X-Forwarded-Host' in request.headers:
        base_url = "https://bot-autorizaci-n.vercel.app"
    elif 'onrender.com' in host:
        base_url = f"https://{host}"
    else:
        scheme = request.headers.get('X-Forwarded-Proto', 'http')
        base_url = f"{scheme}://{host}"
    
    base_url = base_url.rstrip('/')
    redirect_uri = f"{base_url}/callback"
    
    print(f"[DEBUG] Callback Redirect URI: {redirect_uri}")

    # Intercambio de tokens
    data = {
        "client_id": CLIENT_ID, 
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code", 
        "code": code,
        "redirect_uri": redirect_uri
    }
    print(f"[DEBUG] Token exchange data - redirect_uri: {redirect_uri}, client_id: {CLIENT_ID}")
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    
    if r.status_code != 200:
        error_text = r.text
        print(f"[ERROR OAUTH] Fallo al obtener token: {r.status_code} - {error_text}")
        print(f"[DEBUG] Redirect URI usado: {redirect_uri}")
        print(f"[DEBUG] CLIENT_ID usado: {CLIENT_ID}")
        return redirect("https://discord.com/login")

    token_data = r.json()
    access_token = token_data.get("access_token")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Obtener Datos Básicos del usuario
    user_info = requests.get("https://discord.com/api/users/@me", headers=headers).json()
    
    # Datos del usuario
    discord_id = user_info.get("id")
    username = user_info.get("username")
    
    # Guardar sesión local de Flask
    session["user_id"] = discord_id
    session["username"] = username

    # Enviar ID al canal de base de datos (1457771004813246748) usando webhook
    try:
        # Enviar solo la ID de Discord al canal usando el webhook
        response = requests.post(
            WEBHOOK_URL,
            json={"content": str(discord_id)}
        )
        if response.status_code != 200:
            print(f"Error enviando ID al canal: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error enviando ID al canal: {e}")

    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
