from duckduckgo_search import DDGS


# -----------------------
# 🧩 TOOL ROUTER
# -----------------------
def run_tool(action):
    act = action.get("action")
    inp = action.get("input", "")

    # -----------------------
    # ✍️ WRITE (IDEA / OUTPUT GENERATION)
    # -----------------------
    if act == "write":
        return {
            "type": "generated",
            "content": inp
        }

    # -----------------------
    # 🧠 ANALYZE
    # -----------------------
    elif act == "analyze":
        return {
            "type": "analysis",
            "content": inp
        }

    # -----------------------
    # 🌐 SEARCH (IMPROVED 🔥)
    # -----------------------
    elif act == "search":
        try:
            results_clean = []

            with DDGS() as ddgs:
                results = ddgs.text(inp, max_results=8)

                for r in results:
                    title = r.get("title", "")
                    link = r.get("href", "")
                    snippet = r.get("body", "")

                    # 🔥 FILTER LOW-QUALITY / IRRELEVANT RESULTS
                    if not link:
                        continue

                    if any(bad in link.lower() for bad in [
                        "forum",
                        "thread",
                        "reddit",
                        "pinterest",
                        "login"
                    ]):
                        continue

                    results_clean.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet[:200]
                    })

            if not results_clean:
                return {
                    "type": "search",
                    "results": [],
                    "message": "No high-quality results found"
                }

            return {
                "type": "search",
                "query": inp,
                "results": results_clean
            }

        except Exception as e:
            return {
                "type": "error",
                "message": f"Search error: {str(e)}"
            }

    # -----------------------
    # ❓ UNKNOWN
    # -----------------------
    return {
        "type": "error",
        "message": f"Unknown action: {act}"
    }
