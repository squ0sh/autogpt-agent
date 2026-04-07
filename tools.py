from ddgs import DDGS


def run_tool(action):
    act = action.get("action")
    inp = action.get("input", "")

    # -----------------------
    # ✍️ WRITE
    # -----------------------
    if act == "write":
        return f"Generated content:\n{inp}"

    # -----------------------
    # 🧠 ANALYZE
    # -----------------------
    elif act == "analyze":
        return f"Analysis:\n{inp}"

    # -----------------------
    # 🌐 SEARCH (DDGS 🔥)
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

                    if not link:
                        continue

                    # 🔥 filter junk
                    if any(bad in link.lower() for bad in [
                        "forum",
                        "thread",
                        "reddit",
                        "pinterest",
                        "login"
                    ]):
                        continue

                    results_clean.append(
                        f"{title}\n{link}\n{snippet[:200]}"
                    )

            if not results_clean:
                return "No high-quality results found."

            return "Search results:\n\n" + "\n\n---\n\n".join(results_clean)

        except Exception as e:
            return f"Search error: {str(e)}"

    # -----------------------
    # ❓ UNKNOWN
    # -----------------------
    return "Unknown action"
