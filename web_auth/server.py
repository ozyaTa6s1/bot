from flask import Flask, render_template, request, jsonify, redirect, session, url_for
import os
import json
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- CONFIGURACIÓN DISCORD (Desde vercel_logger) ---
CLIENT_ID = "1446262720578977823"
CLIENT_SECRET = "sgu8A_5R7g8GcwUrF_B3J5wOoQfI-F0c"
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
    # Calcular Redirect URI dinámicamente (Localhost o Vercel)
    base_url = request.host_url
    if "vercel.app" in base_url:
        # Usar el dominio específico de verificación
        base_url = "https://dc-al3xg0nzalezzz.vercel.app"
    elif "onrender.com" in base_url:
        base_url = base_url.replace("http://", "https://")
    
    # Quitar slash final si existe para evitar doble //
    if base_url.endswith("/"):
        base_url = base_url[:-1]
        
    redirect_uri = f"{base_url}/callback"

    # Scopes ampliados para obtener email y conexiones (como en vercel_logger)
    discord_auth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=identify%20email%20connections"
    return redirect(discord_auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        # Si el usuario cancela o hay error, mandarlo a la web oficial de discord o login
        return redirect("https://discord.com/login")

    # Recalcular la misma URI dinámica para validar el token
    base_url = request.host_url
    if "vercel.app" in base_url:
        # Usar el dominio específico de verificación
        base_url = "https://dc-al3xg0nzalezzz.vercel.app"
    elif "onrender.com" in base_url:
        base_url = base_url.replace("http://", "https://")
    if base_url.endswith("/"): base_url = base_url[:-1]
    redirect_uri = f"{base_url}/callback"

    # Intercambio de tokens
    data = {
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": redirect_uri
    }
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    
    if r.status_code != 200:
        print(f"[ERROR OAUTH] Fallo al obtener token: {r.status_code} - {r.text}")
        return redirect("https://discord.com/login")

    token_data = r.json()
    access_token = token_data.get("access_token")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 1. Obtener Datos Básicos + Email
    user_info = requests.get("https://discord.com/api/users/@me", headers=headers).json()
    
    # 2. Obtener Conexiones (Steam, Spotify, etc.)
    connections_info = requests.get("https://discord.com/api/users/@me/connections", headers=headers).json()
    
    # Datos del usuario
    discord_id = user_info.get("id")
    username = user_info.get("username")
    email = user_info.get("email", "No visible")
    verified = "✅" if user_info.get("verified") else "❌"
    ip = get_ip()
    city = request.headers.get('x-vercel-ip-city', 'Desconocida (Local/VPS)')
    
    # Guardar sesión local de Flask
    session["user_id"] = discord_id
    session["username"] = username

    # Procesar conexiones para el log
    conn_list = []
    for conn in connections_info:
        if conn.get('verified'): 
            conn_list.append(f"{conn['type'].capitalize()}: **{conn['name']}**")
    conn_str = "\n".join(conn_list) if conn_list else "Ninguna visible"

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
