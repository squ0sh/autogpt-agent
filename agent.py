import json
import os
import time
import uuid
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GOAL = ""
memory = []
RUN_ID = None
STOP_FLAG = False
failed_steps = 0

MEMORY_FILE = "memory.json"


# -----------------------
# 🧾 MEMORY
# -----------------------
def save_memory():
    data = {}
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
        except:
            data = {}

    data[RUN_ID] = {
        "goal": GOAL,
        "steps": memory
    }

    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


# -----------------------
# 🧠 CHAT
# -----------------------
def chat(prompt, max_tokens=1200):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=max_tokens,
    )
    return res.choices[0].message.content.strip()


# -----------------------
# 🧠 VALIDATION
# -----------------------
def is_valid_result(result):
    if not result:
        return False

    text = str(result).lower()

    bad = [
        "results': []",
        "no results",
        "error",
        "failed"
    ]

    return not any(b in text for b in bad)


# -----------------------
# 🔁 SEARCH RETRY
# -----------------------
def retry_search(query):
    from tools import run_tool

    variations = [
        query,
        query + " research",
        query + " latest studies",
        query + " clinical trials"
    ]

    for q in variations:
        result = run_tool({"action": "search", "input": q})
        if result.get("results"):
            return result

    return {"error": "search failed"}


# -----------------------
# ⚙️ EXECUTION ENGINE
# -----------------------
def execute(action):
    from tools import run_tool, is_useful_content, transform_tool

    # 🔍 SEARCH FLOW
    if action["action"] == "search":
        search_result = retry_search(action["input"])

        if not is_valid_result(search_result):
            return {"error": "No search results"}

        for r in search_result["results"][:3]:
            scrape = run_tool({
                "action": "scrape",
                "input": r["url"]
            })

            if "content" in scrape and is_useful_content(scrape["content"]):
                return transform_tool(scrape["content"])

        return {"error": "No useful pages"}

    # 🌐 SCRAPE FLOW
    if action["action"] == "scrape":
        scrape = run_tool(action)

        if "content" in scrape and is_useful_content(scrape["content"]):
            return transform_tool(scrape["content"])

        return {"error": "Bad scrape"}

    return run_tool(action)


# -----------------------
# 🧠 PLAN
# -----------------------
def generate_plan():
    step = len(memory) + 1

    return chat(f"""
Goal: {GOAL}

Previous: {memory}

Step {step} plan:
- real-world actions
- prefer search → scrape → transform
""", 600)


# -----------------------
# 🎯 DECISION
# -----------------------
def decide_action(plan):
    try:
        decision = json.loads(chat(f"""
Plan:
{plan}

Return JSON:
{{ "action": "...", "input": "..." }}
""", 300))
    except:
        decision = {"action": "search", "input": plan}

    if decision["action"] == "scrape" and not str(decision["input"]).startswith("http"):
        decision["action"] = "search"

    return decision


# -----------------------
# 🔍 REFLECT
# -----------------------
def reflect(result):
    return chat(f"""
Goal: {GOAL}

Result: {result}

If useless → say: No real progress made

Insights:
- ...
- ...
""", 500)


# -----------------------
# 🚀 MAIN LOOP
# -----------------------
def run_agent_stream(goal, max_steps=6):
    global GOAL, memory, RUN_ID, failed_steps

    GOAL = goal
    memory = []
    failed_steps = 0
    RUN_ID = str(uuid.uuid4())

    yield f"event: start\ndata: {goal}\n\n"

    for step in range(max_steps):

        yield f"event: step\ndata: {step+1}\n\n"

        plan = generate_plan()
        yield f"event: plan\ndata: {plan}\n\n"

        action = decide_action(plan)
        yield f"event: action\ndata: {json.dumps(action)}\n\n"

        result = execute(action)
        yield f"event: result\ndata: {result}\n\n"

        reflection = reflect(result)
        yield f"event: reflection\ndata: {reflection}\n\n"

        if "error" in str(result).lower() or "No real progress made" in reflection:
            failed_steps += 1
        else:
            failed_steps = 0

        memory.append({
            "step": step + 1,
            "action": action,
            "result": result,
            "reflection": reflection
        })

        save_memory()

        time.sleep(0.3)

    yield f"event: done\ndata: complete\n\n"

