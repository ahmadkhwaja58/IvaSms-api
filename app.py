from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import os
import re

app = Flask(__name__)
CORS(app)

# =============================================
# CREDENTIALS
# =============================================
IVAS_EMAIL    = "funnybaddshah@gmail.com"
IVAS_PASSWORD = "Allah123"

# Session store
session_data = {"cookies": None, "time": 0}

import time

# =============================================
# HEADERS
# =============================================
def get_headers(cookies=""):
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.ivasms.com/portal/dashboard",
        "Cookie": cookies
    }

def get_ajax_headers(cookies=""):
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.5",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.ivasms.com/portal/numbers",
        "Cookie": cookies
    }

# =============================================
# AUTO LOGIN
# =============================================
def do_login():
    try:
        # Step 1 - Login page
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        login_page = s.get("https://www.ivasms.com/login", timeout=15)
        soup = BeautifulSoup(login_page.text, "html.parser")

        # CSRF token
        csrf = ""
        token_input = soup.find("input", {"name": "_token"})
        if token_input:
            csrf = token_input.get("value", "")
        if not csrf:
            meta = soup.find("meta", {"name": "csrf-token"})
            if meta:
                csrf = meta.get("content", "")

        # Step 2 - POST login
        resp = s.post("https://www.ivasms.com/login", data={
            "_token": csrf,
            "email": IVAS_EMAIL,
            "password": IVAS_PASSWORD,
            "remember": "on"
        }, headers={
            "Referer": "https://www.ivasms.com/login",
            "Origin": "https://www.ivasms.com"
        }, timeout=15)

        # Cookies string banao
        cookies_str = "; ".join([f"{k}={v}" for k, v in s.cookies.items()])

        session_data["cookies"] = cookies_str
        session_data["time"] = time.time()

        return cookies_str

    except Exception as e:
        print(f"Login error: {e}")
        return ""

def get_cookies():
    # 5 ghante se zyada purani hain toh refresh
    if not session_data["cookies"] or (time.time() - session_data["time"]) > 18000:
        return do_login()
    return session_data["cookies"]

# =============================================
# ROUTES
# =============================================
@app.route("/")
def home():
    return jsonify({
        "status": "✅ ivasms Tool Running!",
        "endpoints": {
            "/numbers": "Numbers list",
            "/sms": "Live SMS",
            "/debug": "Debug info"
        }
    })

@app.route("/debug")
def debug():
    try:
        cookies = get_cookies()
        url = "https://www.ivasms.com/portal/numbers?draw=1&columns%5B1%5D%5Bdata%5D=Number&columns%5B2%5D%5Bdata%5D=range&start=0&length=5&_=1"
        resp = requests.get(url, headers=get_ajax_headers(cookies), timeout=15)
        return jsonify({
            "status": "debug",
            "http_code": resp.status_code,
            "is_json": resp.text.strip().startswith("{"),
            "preview": resp.text[:500],
            "has_data": '"data"' in resp.text,
            "cloudflare": "Just a moment" in resp.text
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/numbers")
def get_numbers():
    try:
        country_filter = request.args.get("country", "")
        cookies = get_cookies()

        url = ("https://www.ivasms.com/portal/numbers?draw=1"
               "&columns%5B1%5D%5Bdata%5D=Number"
               "&columns%5B2%5D%5Bdata%5D=range"
               "&order%5B0%5D%5Bcolumn%5D=1&order%5B0%5D%5Bdir%5D=desc"
               f"&start=0&length=1000&search%5Bvalue%5D=&_={int(time.time())}")

        resp = requests.get(url, headers=get_ajax_headers(cookies), timeout=15)

        # Session expire — retry
        if resp.status_code in [401, 403] or '"data"' not in resp.text:
            session_data["cookies"] = None
            cookies = get_cookies()
            resp = requests.get(url, headers=get_ajax_headers(cookies), timeout=15)

        data = resp.json()
        rows = data.get("data", [])
        numbers = []

        for row in rows:
            num     = row.get("Number") or row.get("number", "")
            country = row.get("range", "Unknown")
            country = re.sub(r'\s*[\d.]+\s*$', '', country).strip()

            if num:
                if not country_filter or country_filter.lower() in country.lower():
                    numbers.append({
                        "number": num,
                        "country": country,
                        "status": "Active"
                    })

        return jsonify({"status": "success", "count": len(numbers), "numbers": numbers})

    except Exception as e:
        return jsonify({"error": str(e), "numbers": []})

@app.route("/sms")
def get_sms():
    try:
        target = request.args.get("number", "")
        cookies = get_cookies()

        resp = requests.get(
            "https://www.ivasms.com/portal/live/my_sms",
            headers=get_headers(cookies),
            timeout=15
        )

        # Session expire — retry
        if "login" in resp.url or resp.status_code == 401:
            session_data["cookies"] = None
            cookies = get_cookies()
            resp = requests.get(
                "https://www.ivasms.com/portal/live/my_sms",
                headers=get_headers(cookies),
                timeout=15
            )

        soup = BeautifulSoup(resp.text, "html.parser")
        messages = []

        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                num     = cols[0].get_text(strip=True)
                sender  = cols[1].get_text(strip=True)
                message = cols[2].get_text(strip=True)
                t       = cols[3].get_text(strip=True) if len(cols) > 3 else ""

                if message and len(message) > 1:
                    nc = re.sub(r'\D', '', num)
                    tc = re.sub(r'\D', '', target)

                    if not tc or tc in nc or nc in tc:
                        messages.append({
                            "number": num,
                            "sender": sender,
                            "message": message,
                            "time": t
                        })

        return jsonify({"status": "success", "count": len(messages), "messages": messages})

    except Exception as e:
        return jsonify({"error": str(e), "messages": []})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
