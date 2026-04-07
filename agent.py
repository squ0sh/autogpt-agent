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
# 🧾 MEMORY STORAGE
# -----------------------
def save_memory():
    data = {}
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            try:
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
# 🛑 STOP
# -----------------------
def stop():
    global STOP_FLAG
    STOP_FLAG = True


# -----------------------
# 🧠 CORE CHAT
# -----------------------
def chat(prompt, max_tokens=1200):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


# -----------------------
# 🧠 PLAN GENERATION
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    strategy_note = ""
    if failed_steps >= 2:
        strategy_note = """
⚠️ MUST CHANGE STRATEGY:
- Use search → scrape pipeline
- Produce real outputs only
"""

    prompt = f"""
You are an autonomous execution agent.

Goal:
{GOAL}

Previous steps:
{memory}

{strategy_note}

RULES:
- Prefer real-world actions
- Use search if no URL exists
- Then scrape
- Then transform/store

Step {step_number}:

Format:
Step {step_number}: <title>

- action 1
- action 2
- action 3
"""

    return chat(prompt, 700)


# -----------------------
# 🎯 ACTION DECISION
# -----------------------
def decide_action(plan):
    prompt = f"""
Plan:
{plan}

Choose ONE action:

Options:
- search
- scrape
- create
- store
- simulate
- transform

RULES:
- If no URL → search
- If URL → scrape
- Prefer real actions

Return JSON:
{{ "action": "...", "input": "..." }}
"""

    try:
        decision = json.loads(chat(prompt, 300))
    except:
        decision = {"action": "search", "input": plan}

    input_text = str(decision.get("input", ""))

    # 🔥 AUTO FIX
    if decision["action"] == "scrape" and not input_text.startswith("http"):
        decision["action"] = "search"

    return decision


# -----------------------
# 🧠 EXECUTION (CHAINING)
# -----------------------
def execute_with_validation(action):
    from tools import run_tool

    result = run_tool(action)

    # 🔗 AUTO CHAIN: search → scrape
    if action["action"] == "search" and "source" in result:
        scrape_action = {
            "action": "scrape",
            "input": result["source"]
        }
        result = run_tool(scrape_action)

    return result


# -----------------------
# 🔍 REFLECTION
# -----------------------
def reflect(result):
    prompt = f"""
Goal:
{GOAL}

Result:
{result}

CRITICAL:
- If no real data → "No real progress made"
- If error → change strategy

FORMAT:

Evaluation:
...

Insights:
- ...
- ...
- ...

Next:
...
"""
    return chat(prompt, 700)


# -----------------------
# 🧠 GOAL CHECK (STRICT)
# -----------------------
def is_goal_complete():
    result = chat(
        f"""
Goal:
{GOAL}

Steps:
{memory}

Has REAL, VERIFIABLE progress been made?

Answer ONLY:
YES or NO
""",
        30
    ).lower()

    return "yes" in result


# -----------------------
# 🧠 FINAL OUTPUT
# -----------------------
def generate_final():
    text = ""

    for s in memory:
        text += f"""
Step {s['step']}
Action: {s['action']}
Result: {s['result']}
---
"""

    return chat(f"Create FINAL report using REAL data only:\n{text}", 2000)


def refine(final):
    return chat(f"Improve clarity:\n{final}", 1500)


# -----------------------
# STREAM SAFE
# -----------------------
def safe(text):
    return str(text).replace("\n", "\\n")


# -----------------------
# 🚀 MAIN LOOP
# -----------------------
def run_agent_stream(goal, max_steps=6):
    global GOAL, memory, RUN_ID, STOP_FLAG, failed_steps

    GOAL = goal
    memory = []
    STOP_FLAG = False
    failed_steps = 0
    RUN_ID = str(uuid.uuid4())

    yield f"event: start\ndata: {safe(goal)}\n\n"

    for step in range(max_steps):

        if STOP_FLAG:
            yield f"event: stopped\ndata: stopped\n\n"
            return

        yield f"event: step\ndata: {step+1}\n\n"

        plan = generate_plan()
        yield f"event: plan\ndata: {safe(plan)}\n\n"

        action = decide_action(plan)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        result = execute_with_validation(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        reflection = reflect(result)
        yield f"event: reflection\ndata: {safe(reflection)}\n\n"

        # failure tracking
        if "error" in str(result).lower() or "No real progress made" in reflection:
            failed_steps += 1
        else:
            failed_steps = 0

        memory.append({
            "step": step + 1,
            "plan": plan,
            "action": action,
            "result": result,
            "reflection": reflection
        })

        save_memory()

        if step >= 2 and is_goal_complete():
            break

        time.sleep(0.3)

    final = refine(generate_final())

    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: done\n\n"

