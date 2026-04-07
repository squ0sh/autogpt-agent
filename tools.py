import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DATA_DIR = "data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# -----------------------
# 🔍 SEARCH TOOL (BRAVE API)
# -----------------------
def search_tool(input_data):
    try:
        api_key = os.getenv("LANGSEARCH_API_KEY")

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key
        }

        url = "https://api.search.brave.com/res/v1/web/search"

        params = {
            "q": input_data,
            "count": 5
        }

        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()

        results = []
        for r in data.get("web", {}).get("results", []):
            results.append({
                "title": r.get("title"),
                "url": r.get("url")
            })

        return {
            "results": results
        }

    except Exception as e:
        return {"error": f"search failed: {str(e)}"}


# -----------------------
# 🌐 SCRAPE TOOL
# -----------------------
def scrape_tool(input_data):
    try:
        if not input_data.startswith("http"):
            return {"error": "Invalid URL"}

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        res = requests.get(input_data, headers=headers, timeout=10)

        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        return {
            "source": input_data,
            "content": text[:4000]
        }

    except Exception as e:
        return {"error": f"scrape failed: {str(e)}"}


# -----------------------
# 🧠 TRUTH FILTER
# -----------------------
def is_useful_content(text):
    if not text:
        return False

    bad_signals = [
        "captcha",
        "verify you are human",
        "access denied",
        "enable javascript",
        "bot detection"
    ]

    lowered = text.lower()

    for b in bad_signals:
        if b in lowered:
            return False

    return len(text) > 200


# -----------------------
# 🔄 TRANSFORM TOOL (STRUCTURE FIX)
# -----------------------
def transform_tool(input_data):
    text = str(input_data)

    sentences = text.split(". ")

    bullets = []
    for s in sentences:
        s = s.strip()
        if len(s) > 40:
            bullets.append(s)
        if len(bullets) >= 8:
            break

    return {
        "summary": bullets
    }


# -----------------------
# 🔬 RESEARCH TOOL
# -----------------------
def research_tool(input_data):
    return {
        "simulation": True,
        "query": input_data
    }


# -----------------------
# ⚙️ CREATE TOOL
# -----------------------
def create_tool(input_data):
    return {
        "simulation": True,
        "created": input_data,
        "time": str(datetime.utcnow())
    }


# -----------------------
# 🧪 SIMULATE TOOL
# -----------------------
def simulate_tool(input_data):
    return {
        "simulation": True,
        "scenario": input_data
    }


# -----------------------
# 💾 STORE TOOL
# -----------------------
def store_tool(input_data):
    try:
        filename = f"{DATA_DIR}/data_{datetime.utcnow().timestamp()}.json"

        with open(filename, "w") as f:
            json.dump({"data": input_data}, f, indent=2)

        return {
            "stored": True,
            "file": filename
        }

    except Exception as e:
        return {"error": str(e)}


# -----------------------
# 🎯 ROUTER
# -----------------------
def run_tool(action):
    action_type = action.get("action")
    input_data = action.get("input", "")

    if action_type == "search":
        return search_tool(input_data)

    elif action_type == "scrape":
        return scrape_tool(input_data)

    elif action_type == "research":
        return research_tool(input_data)

    elif action_type == "create":
        return create_tool(input_data)

    elif action_type == "simulate":
        return simulate_tool(input_data)

    elif action_type == "store":
        return store_tool(input_data)

    elif action_type == "transform":
        return transform_tool(input_data)

    return {"error": f"Unknown action: {action_type}"}
