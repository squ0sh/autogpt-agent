import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DATA_DIR = "data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# -----------------------
# 🔍 SEARCH TOOL (GENERIC / LANG / API)
# -----------------------
def search_tool(input_data):
    try:
        # 🔁 Replace this with LangSearch / Brave / etc.
        url = f"https://api.duckduckgo.com/?q={input_data}&format=json"

        res = requests.get(url, timeout=10)
        data = res.json()

        results = []

        # fallback parsing
        for topic in data.get("RelatedTopics", []):
            if "FirstURL" in topic:
                results.append({
                    "title": topic.get("Text"),
                    "url": topic.get("FirstURL")
                })

        return {"results": results}

    except Exception as e:
        return {"error": f"search failed: {str(e)}"}


# -----------------------
# 🌐 SCRAPE TOOL
# -----------------------
def scrape_tool(input_data):
    try:
        if not input_data.startswith("http"):
            return {"error": "Invalid URL"}

        headers = {"User-Agent": "Mozilla/5.0"}

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
# 🧠 CONTENT VALIDATION
# -----------------------
def is_useful_content(text):
    if not text:
        return False

    bad = [
        "captcha",
        "verify",
        "access denied",
        "enable javascript",
        "bot detection"
    ]

    t = text.lower()

    if any(b in t for b in bad):
        return False

    return len(text) > 200


# -----------------------
# 🔄 TRANSFORM TOOL
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
# 🔬 OTHER TOOLS
# -----------------------
def research_tool(input_data):
    return {"simulation": True, "query": input_data}


def create_tool(input_data):
    return {
        "simulation": True,
        "created": input_data,
        "time": str(datetime.utcnow())
    }


def simulate_tool(input_data):
    return {"simulation": True, "scenario": input_data}


def store_tool(input_data):
    try:
        filename = f"{DATA_DIR}/data_{datetime.utcnow().timestamp()}.json"

        with open(filename, "w") as f:
            json.dump({"data": input_data}, f, indent=2)

        return {"stored": True, "file": filename}

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
    elif action_type == "transform":
        return transform_tool(input_data)
    elif action_type == "research":
        return research_tool(input_data)
    elif action_type == "create":
        return create_tool(input_data)
    elif action_type == "simulate":
        return simulate_tool(input_data)
    elif action_type == "store":
        return store_tool(input_data)

    return {"error": f"Unknown action: {action_type}"}

