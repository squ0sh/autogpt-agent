import os
import uuid
from duckduckgo_search import DDGS

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_tool(action):
    act = action.get("action")
    inp = action.get("input")

    # -----------------------
    # ✍️ WRITE TOOL (REAL 🔥)
    # -----------------------
    if act == "write":
        filename = f"{uuid.uuid4()}.txt"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "w") as f:
            f.write(inp)

        return {
            "message": "File created",
            "file": filename,
            "path": filepath
        }

    # -----------------------
    # 🧠 ANALYZE
    # -----------------------
    elif act == "analyze":
        return f"Analysis: {inp}"

    # -----------------------
    # 🌐 SEARCH
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

            return "\n\n---\n\n".join(results_text)

        except Exception as e:
            return f"Search error: {str(e)}"

    return "Unknown action"
