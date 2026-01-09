import aiohttp
import asyncio
import json

async def fetch_server_data(code):
    url = f"https://servers-frontend.fivem.net/api/servers/single/{code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as r:
                print(f"Status: {r.status}")
                if r.status == 200:
                    return await r.json()
                else:
                    print(await r.text())
    except Exception as e:
        print(f"Error: {e}")
    return None

async def main():
    code = "78y6ma"
    print(f"Fetching data for {code}...")
    data = await fetch_server_data(code)
    if data:
        # Save to file for inspection
        with open("server_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        info = data.get('Data', {})
        endpoints = info.get('connectEndPoints')
        if endpoints:
            ep = endpoints[0]
            if not ep.endswith("/"):
                ep += "/"
            players_url = f"{ep}players.json"
            print(f"Trying to fetch players from: {players_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(players_url, headers=headers) as r:
                    print(f"Players.json Status: {r.status}")
                    if r.status == 200:
                        p_data = await r.json()
                        print(f"Found {len(p_data)} players in players.json")
                        # Check for IPs in players.json (unlikely but worth a look)
                        for p in p_data[:5]:
                            print(f"Player: {p.get('name')} - Endpoint: {p.get('endpoint')}")
                    else:
                        print(f"Players.json Error: {await r.text()}")
        
        print("VARS:", info.get('vars', {}).keys())
    else:
        print("No data found")

if __name__ == "__main__":
    asyncio.run(main())
