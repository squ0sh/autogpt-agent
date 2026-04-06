import json
import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime

try:
    from ddgs import DDGS
except:
    DDGS = None


# -----------------------
# QUALITY FILTER
# -----------------------
def is_good_content(text):
    bad = ["enable javascript", "sign up", "cookie", "captcha"]

    if len(text) < 200:
        return False

    for b in bad:
        if b in text.lower():
            return False

    return True


# -----------------------
# CLEAN HTML
# -----------------------
def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.extract()

    text = soup.get_text()
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    return "\n".join(lines)


# -----------------------
# EXTRACT INSIGHTS
# -----------------------
def extract_insights(text):
    lines = text.split("\n")
    insights = []

    for l in lines:
        if 60 < len(l) < 300:
            insights.append(l)

        if len(insights) >= 5:
            break

    return insights


# -----------------------
# 🔍 RESEARCH
# -----------------------
def research(query):
    if DDGS is None:
        return "Install ddgs"

    urls = []

    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
        for r in results:
            urls.append(r.get("href"))

    data = []

    for url in urls:
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            text = clean_text(res.text)

            if not is_good_content(text):
                continue

            insights = extract_insights(text)

            if insights:
                data.append({
                    "url": url,
                    "insights": insights
                })

        except:
            continue

        if len(data) >= 3:
            break

    return json.dumps({
        "query": query,
        "sources": data
    }, indent=2)


# -----------------------
# 🌐 SCRAPE
# -----------------------
def scrape(url):
    try:
        res = requests.get(url, timeout=10)
        text = clean_text(res.text)

        if not is_good_content(text):
            return "Low-quality content"

        return text[:2000]

    except Exception as e:
        return str(e)


# -----------------------
# 🧠 CREATE (REAL OUTPUT)
# -----------------------
def create(data):
    filename = f"output_{int(datetime.now().timestamp())}.txt"

    with open(filename, "w") as f:
        f.write(str(data))

    return f"Created file: {filename}"


# -----------------------
# 💾 STORE (STRUCTURED MEMORY)
# -----------------------
def store(data):
    filename = "agent_store.json"

    existing = []

    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                existing = json.load(f)
            except:
                existing = []

    existing.append({
        "timestamp": str(datetime.now()),
        "data": data
    })

    with open(filename, "w") as f:
        json.dump(existing, f, indent=2)

    return "Stored successfully"


# -----------------------
# 🔮 SIMULATE (FIRST VERSION)
# -----------------------
def simulate(data):
    """
    Simple scenario modeling:
    - best case
    - worst case
    - likely outcome
    """

    return json.dumps({
        "simulation": {
            "best_case": f"If executed well → strong positive outcome based on: {data[:200]}",
            "worst_case": f"If assumptions fail → minimal or no impact",
            "likely_outcome": f"Moderate progress with key dependency on execution quality"
        }
    }, indent=2)


# -----------------------
# 🔄 TRANSFORM
# -----------------------
def transform(data):
    return f"Transformed version:\n{data}"


# -----------------------
# 🎯 ROUTER
# -----------------------
def run_tool(action):
    act = action.get("action")
    inp = action.get("input")

    if act == "research":
        return research(inp)

    elif act == "scrape":
        return scrape(inp)

    elif act == "create":
        return create(inp)

    elif act == "store":
        return store(inp)

    elif act == "simulate":
        return simulate(inp)

    elif act == "transform":
        return transform(inp)

    return "Unknown action"
