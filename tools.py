import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DATA_DIR = "data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# -----------------------
# 🔍 SCRAPE TOOL (REAL)
# -----------------------
def scrape_tool(input_data):
    try:
        url = input_data.strip()

        res = requests.get(url, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")

        text = soup.get_text(separator=" ", strip=True)

        return {
            "source": url,
            "content": text[:3000]  # limit size
        }

    except Exception as e:
        return {"error": f"scrape failed: {str(e)}"}


# -----------------------
# 🔬 RESEARCH TOOL
# -----------------------
def research_tool(input_data):
    return {
        "simulation": True,
        "query": input_data,
        "insight": "Research simulated. Connect search API for real data."
    }


# -----------------------
# ⚙️ CREATE TOOL
# -----------------------
def create_tool(input_data):
    return {
        "simulation": True,
        "created_object": {
            "description": input_data,
            "timestamp": str(datetime.utcnow())
        }
    }


# -----------------------
# 🧪 SIMULATE TOOL
# -----------------------
def simulate_tool(input_data):
    return {
        "simulation": True,
        "scenario": input_data,
        "predicted_outcome": {
            "success_probability": 0.65,
            "risk_level": "medium"
        }
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
        return {"error": f"store failed: {str(e)}"}


# -----------------------
# 🔄 TRANSFORM TOOL
# -----------------------
def transform_tool(input_data):
    return {
        "simulation": True,
        "transformed": input_data,
        "note": "Basic transform placeholder"
    }


# -----------------------
# 🎯 TOOL ROUTER
# -----------------------
def run_tool(action):
    action_type = action.get("action")
    input_data = action.get("input", "")

    if action_type == "scrape":
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

    else:
        return {"error": f"Unknown action: {action_type}"}
