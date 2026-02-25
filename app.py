from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import os

app = Flask(__name__)
CORS(app)  # Blogger se connect ho sake isliye

# =============================================
# COOKIES LOAD KARO
# =============================================
def get_cookies():
    try:
        with open("cookies.json", "r") as f:
            cookies_list = json.load(f)
        # List ko dict mein convert karo
        cookies = {}
        for cookie in cookies_list:
            cookies[cookie["name"]] = cookie["value"]
        return cookies
    except Exception as e:
        print(f"Cookie error: {e}")
        return {}

# =============================================
# HEADERS — Browser jesa lagao taake block na ho
# =============================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.ivasms.com/portal/dashboard",
}

# =============================================
# ROUTE 1 — Home
# =============================================
@app.route("/")
def home():
    return jsonify({
        "status": "✅ API Running",
        "endpoints": {
            "/numbers": "Aapke ivasms numbers",
            "/sms": "Live SMS messages",
            "/stats": "SMS Statistics"
        }
    })

# =============================================
# ROUTE 2 — Numbers Fetch
# =============================================
@app.route("/numbers")
def get_numbers():
    try:
        cookies = get_cookies()
        
        response = requests.get(
            "https://www.ivasms.com/portal/numbers",
            cookies=cookies,
            headers=HEADERS,
            timeout=15
        )
        
        # Check login hai ya nahi
        if "login" in response.url or response.status_code == 401:
            return jsonify({"error": "Session expire ho gayi — cookies update karo"}), 401
        
        soup = BeautifulSoup(response.text, "html.parser")
        numbers = []
        
        # Table rows dhundo
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 2:
                num_data = {}
                # Pehla column — number
                num_data["number"] = cols[0].get_text(strip=True)
                # Doosra column — country/type
                if len(cols) > 1:
                    num_data["type"] = cols[1].get_text(strip=True)
                # Teesra column — status
                if len(cols) > 2:
                    num_data["status"] = cols[2].get_text(strip=True)
                # Khaali rows skip karo
                if num_data["number"] and num_data["number"] != "":
                    numbers.append(num_data)
        
        # Agar table nahi mili toh div/span try karo
        if not numbers:
            cards = soup.find_all("div", class_=lambda x: x and "number" in x.lower())
            for card in cards:
                text = card.get_text(strip=True)
                if text:
                    numbers.append({"number": text, "type": "", "status": "active"})
        
        return jsonify({
            "status": "success",
            "count": len(numbers),
            "numbers": numbers
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
# ROUTE 3 — Live SMS Fetch
# =============================================
@app.route("/sms")
def get_sms():
    try:
        cookies = get_cookies()
        
        response = requests.get(
            "https://www.ivasms.com/portal/live/my_sms",
            cookies=cookies,
            headers=HEADERS,
            timeout=15
        )
        
        if "login" in response.url or response.status_code == 401:
            return jsonify({"error": "Session expire ho gayi — cookies update karo"}), 401
        
        soup = BeautifulSoup(response.text, "html.parser")
        messages = []
        
        # Table rows se SMS nikalo
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                msg_data = {}
                msg_data["number"] = cols[0].get_text(strip=True)
                msg_data["sender"] = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                msg_data["message"] = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                msg_data["time"] = cols[3].get_text(strip=True) if len(cols) > 3 else ""
                
                if msg_data["message"] and msg_data["message"] != "":
                    messages.append(msg_data)
        
        return jsonify({
            "status": "success",
            "count": len(messages),
            "messages": messages
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
# ROUTE 4 — Statistics
# =============================================
@app.route("/stats")
def get_stats():
    try:
        cookies = get_cookies()
        
        response = requests.get(
            "https://www.ivasms.com/portal/sms_statistics",
            cookies=cookies,
            headers=HEADERS,
            timeout=15
        )
        
        soup = BeautifulSoup(response.text, "html.parser")
        stats = {}
        
        # Stats cards dhundo
        cards = soup.find_all("div", class_=lambda x: x and ("card" in str(x) or "stat" in str(x)))
        for card in cards:
            text = card.get_text(strip=True)
            if text:
                stats[f"item_{len(stats)}"] = text
        
        return jsonify({
            "status": "success",
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
