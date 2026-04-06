import json
import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except:
    DDGS = None


# -----------------------
# 🔍 QUALITY FILTER
# -----------------------
def is_good_content(text):
    bad_signals = [
        "enable javascript",
        "sign up",
        "log in",
        "cookie",
        "accept cookies",
        "captcha",
        "403 forbidden"
    ]

    if len(text) < 200:
        return False

    for bad in bad_signals:
        if bad in text.lower():
            return False

    return True


# -----------------------
# ✂️ CLEAN TEXT
# -----------------------
def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.extract()

    text = soup.get_text()
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    return "\n".join(lines)


# -----------------------
# 🧠 EXTRACT INSIGHTS
# -----------------------
def extract_insights(text):
    lines = text.split("\n")

    insights = []

    for line in lines:
        if len(line) > 60 and len(line) < 300:
            insights.append(line)

        if len(insights) >= 5:
            break

    return insights


# -----------------------
# 🔥 RESEARCH (UPGRADED)
# -----------------------
def research(query):
    if DDGS is None:
        return "Install ddgs"

    urls = []

    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
        for r in results:
            urls.append(r.get("href"))

    collected = []

    for url in urls:
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            text = clean_text(res.text)

            if not is_good_content(text):
                continue

            insights = extract_insights(text)

            if insights:
                collected.append({
                    "url": url,
                    "insights": insights
                })

        except:
            continue

        if len(collected) >= 3:
            break

    if not collected:
        return json.dumps({
            "query": query,
            "error": "No high-quality sources found"
        }, indent=2)

    return json.dumps({
        "query": query,
        "sources": collected
    }, indent=2)


# -----------------------
# 🌐 SEARCH
# -----------------------
def search(query):
    if DDGS is None:
        return "Install ddgs"

    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)

    return json.dumps(results, indent=2)


# -----------------------
# 🧪 SCRAPE
# -----------------------
def scrape(url):
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        text = clean_text(res.text)

        if not is_good_content(text):
            return "Low-quality or blocked content"

        return text[:2000]

    except Exception as e:
        return str(e)


# -----------------------
# 🧠 ANALYZE
# -----------------------
def analyze(data):
    return f"Structured analysis:\n{data}"


# -----------------------
# ✍️ WRITE
# -----------------------
def write(data):
    return f"Generated output:\n{data}"


# -----------------------
# 🎯 MAIN ROUTER
# -----------------------
def run_tool(action):
    act = action.get("action")
    inp = action.get("input")

    if act == "research":
        return research(inp)

    elif act == "search":
        return search(inp)

    elif act == "scrape":
        return scrape(inp)

    elif act == "analyze":
        return analyze(inp)

    elif act == "write":
        return write(inp)

    return "Unknown action"
