import os
import json
import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except:
    DDGS = None


def run_tool(action):
    act = action.get("action")
    inp = action.get("input")

    # -----------------------
    # 🔥 RESEARCH (REAL CHAIN)
    # -----------------------
    if act == "research":
        if DDGS is None:
            return "Install ddgs"

        query = str(inp)
        urls = []

        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            for r in results:
                urls.append(r.get("href"))

        data = []

        for url in urls[:3]:
            try:
                res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(res.text, "html.parser")

                for tag in soup(["script", "style"]):
                    tag.extract()

                text = soup.get_text()
                clean = "\n".join([l.strip() for l in text.splitlines() if l.strip()])

                data.append({
                    "url": url,
                    "content": clean[:1500]
                })

            except:
                continue

        return json.dumps({
            "query": query,
            "sources": data
        }, indent=2)

    # -----------------------
    # SEARCH
    # -----------------------
    elif act == "search":
        if DDGS is None:
            return "Install ddgs"

        with DDGS() as ddgs:
            results = ddgs.text(inp, max_results=5)

        return json.dumps(results, indent=2)

    # -----------------------
    # SCRAPE
    # -----------------------
    elif act == "scrape":
        try:
            res = requests.get(inp, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.text, "html.parser")

            for tag in soup(["script", "style"]):
                tag.extract()

            text = soup.get_text()
            clean = "\n".join([l.strip() for l in text.splitlines() if l.strip()])

            return clean[:3000]

        except Exception as e:
            return str(e)

    # -----------------------
    # ANALYZE
    # -----------------------
    elif act == "analyze":
        return f"Analysis of data:\n{inp}"

    # -----------------------
    # WRITE
    # -----------------------
    elif act == "write":
        return f"Written output:\n{inp}"

    return "Unknown action"
