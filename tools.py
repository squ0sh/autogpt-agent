import json
import os
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_FILE = "agent_data.json"


# -----------------------
# 🧾 STORAGE SYSTEM
# -----------------------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# -----------------------
# 🧠 CORE LLM TOOL
# -----------------------
def llm(prompt, max_tokens=1000):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


# -----------------------
# 🔍 RESEARCH
# -----------------------
def research(input_text):
    prompt = f"""
Research the following:

{input_text}

Return:
- Key findings
- Actionable insights
- Relevant structured data (if possible)
"""
    return llm(prompt)


# -----------------------
# 🧠 SIMULATION ENGINE
# -----------------------
def simulate(input_text):
    prompt = f"""
Simulate realistic outcomes for:

{input_text}

Return JSON:
{{
  "scenario": "...",
  "best_case": "...",
  "worst_case": "...",
  "most_likely": "...",
  "success_probability": 0-1,
  "key_factors": ["...", "..."]
}}
"""
    try:
        return json.loads(llm(prompt))
    except:
        return {"error": "simulation_failed", "raw": llm(prompt)}


# -----------------------
# 🏗 CREATE (REAL ARTIFACTS)
# -----------------------
def create(input_text):
    prompt = f"""
Create a REAL, usable output for:

{input_text}

Return structured JSON if possible.
Examples:
- business ideas
- product concepts
- plans
- datasets
- assets

DO NOT explain — PRODUCE.
"""
    try:
        return json.loads(llm(prompt))
    except:
        return {"output": llm(prompt)}


# -----------------------
# 💾 STORE
# -----------------------
def store(input_text):
    data = load_data()

    entry = {
        "timestamp": str(datetime.utcnow()),
        "data": input_text
    }

    if "entries" not in data:
        data["entries"] = []

    data["entries"].append(entry)
    save_data(data)

    return {"status": "stored", "entry": entry}


# -----------------------
# 🔄 TRANSFORM
# -----------------------
def transform(input_text):
    prompt = f"""
Refine / improve / restructure:

{input_text}

Make it:
- clearer
- more actionable
- more optimized
"""
    return llm(prompt)


# -----------------------
# 🧩 TOOL ROUTER
# -----------------------
def run_tool(action):
    action_type = action.get("action", "research")
    input_text = action.get("input", "")

    if action_type == "research":
        return research(input_text)

    elif action_type == "simulate":
        return simulate(input_text)

    elif action_type == "create":
        return create(input_text)

    elif action_type == "store":
        return store(input_text)

    elif action_type == "transform":
        return transform(input_text)

    else:
        return {"error": f"Unknown action: {action_type}"}
