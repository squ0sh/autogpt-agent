import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DATA_DIR = "data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# -----------------------
# 🔍 SEARCH TOOL
# -----------------------
def search_tool(input_data):
    query = input_data.replace(" ", "+")
    url = f"https://duckduckgo.com/html/?q={query}"

    return {
        "source": url,
        "query": input_data
    }


# -----------------------
# 🌐 SCRAPE TOOL
# -----------------------
def scrape_tool(input_data):
    try:
        if not input_data.startswith("http"):
            return {"error": "Invalid URL"}

        res = requests.get(input_data, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")

        text = soup.get_text(separator=" ", strip=True)

        return {
            "source": input_data,
            "content": text[:3000]
        }

    except Exception as e:
        return {"error": f"scrape failed: {str(e)}"}


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
# 🔄 TRANSFORM TOOL
# -----------------------
def transform_tool(input_data):
    return {
        "transformed": input_data[:500]
    }


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
