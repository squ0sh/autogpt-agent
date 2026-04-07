from ddgs import DDGS


def run_tool(action):
    act = action.get("action")
    inp = action.get("input", "")

    # -----------------------
    # ✍️ WRITE (STRUCTURED OUTPUT)
    # -----------------------
    if act == "write":
        return f"""Generated content:

{inp}
"""

    # -----------------------
    # 🧠 ANALYZE (THINKING TOOL)
    # -----------------------
    elif act == "analyze":
        return f"""Analysis:

{inp}
"""

    # -----------------------
    # 🌐 SEARCH (HIGH-SIGNAL VERSION 🔥)
    # -----------------------
    elif act == "search":
        try:
            results_clean = []

            with DDGS() as ddgs:
                results = ddgs.text(inp, max_results=10)

                for r in results:
                    title = r.get("title", "")
                    link = r.get("href", "")
                    snippet = r.get("body", "")

                    if not link:
                        continue

                    link_lower = link.lower()

                    # ❌ FILTER LOW-SIGNAL / NOISE
                    if any(bad in link_lower for bad in [
                        "facebook",
                        "reddit",
                        "pinterest",
                        "forum",
                        "thread",
                        "login",
                        "signup",
                        "scribd",
                        "tiktok",
                        "instagram"
                    ]):
                        continue

                    # ❌ FILTER VERY SHORT / USELESS SNIPPETS
                    if len(snippet.strip()) < 50:
                        continue

                    results_clean.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet[:300]
                    })

            if not results_clean:
                return "No high-quality search results found."

            # 🔥 STRUCTURED OUTPUT (VERY IMPORTANT)
            formatted = "Search Results:\n\n"

            for i, r in enumerate(results_clean[:6], 1):
                formatted += f"""[{i}] {r['title']}
URL: {r['link']}
Summary: {r['snippet']}

---
"""

            return formatted

        except Exception as e:
            return f"Search error: {str(e)}"

    # -----------------------
    # ❓ UNKNOWN ACTION
    # -----------------------
    return "Unknown action"
