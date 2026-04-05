from duckduckgo_search import DDGS


def run_tool(action):
    act = action.get("action")
    inp = action.get("input")

    # -----------------------
    # ✍️ WRITE TOOL
    # -----------------------
    if act == "write":
        return f"Generated content: {inp}"

    # -----------------------
    # 🧠 ANALYZE TOOL
    # -----------------------
    elif act == "analyze":
        return f"Analysis: {inp}"

    # -----------------------
    # 🌐 REAL SEARCH TOOL 🔥
    # -----------------------
    elif act == "search":
        try:
            results_text = []

            with DDGS() as ddgs:
                results = ddgs.text(inp, max_results=5)

                for r in results:
                    results_text.append(
                        f"{r['title']}\n{r['href']}\n{r['body']}"
                    )

            if not results_text:
                return "No search results found."

            return "Search results:\n\n" + "\n\n---\n\n".join(results_text)

        except Exception as e:
            return f"Search error: {str(e)}"

    # -----------------------
    # ❓ UNKNOWN
    # -----------------------
    return "Unknown action"
