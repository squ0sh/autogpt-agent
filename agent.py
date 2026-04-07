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
# 🧠 PLAN GENERATION (UPGRADED)
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    global failed_steps

    strategy_note = ""
    if failed_steps >= 2:
        strategy_note = """
⚠️ CRITICAL: Previous steps failed.

MANDATORY:
- You MUST use a DIFFERENT action type
- You MUST produce REAL output (scrape, create, or store)
- DO NOT use research unless paired with scraping
"""

    prompt = f"""
You are an autonomous execution agent.

Goal:
{GOAL}

Previous steps:
{memory}

{strategy_note}

RULES:
- Each step MUST produce REAL output
- Prefer ACTION over thinking
- If stuck → FORCE scrape or create
- Avoid repeating past failures
- Move toward tangible outcomes

Step {step_number}:

Format:
Step {step_number}: <title>

- action 1
- action 2
- action 3
"""

    return chat(prompt, 700)


# -----------------------
# 🎯 ACTION DECISION (ENFORCED)
# -----------------------
def decide_action(plan):
    prompt = f"""
Plan:
{plan}

Choose ONE action:

Options:
- research
- scrape
- create
- store
- simulate
- transform

RULES:
- If URL exists → scrape
- If previous step failed → DO NOT use research
- If data exists → transform or store
- Prefer real-world execution

Return JSON:
{{ "action": "...", "input": "..." }}
"""

    try:
        decision = json.loads(chat(prompt, 300))
    except:
        decision = {"action": "research", "input": plan}

    # 🔥 FORCE SCRAPE IF URL
    if "http" in str(decision.get("input")):
        decision["action"] = "scrape"

    # 🔥 BREAK RESEARCH LOOP
    if decision["action"] == "research" and failed_steps >= 1:
        decision["action"] = "scrape"

    # 🔥 ESCALATION LOGIC
    if failed_steps >= 2:
        decision["action"] = "scrape"

    return decision


# -----------------------
# 🧠 REALITY CHECK
# -----------------------
def is_simulation(result):
    return isinstance(result, dict) and result.get("simulation") is True


def is_error(result):
    return "error" in str(result).lower()


# -----------------------
# 🛠 EXECUTION WITH ESCALATION
# -----------------------
def execute_with_validation(action):
    from tools import run_tool

    result = run_tool(action)

    # 🔥 IF SIMULATION → FORCE REAL ACTION
    if is_simulation(result):
        if action["action"] != "scrape":
            forced = {
                "action": "scrape",
                "input": action.get("input", "")
            }
            result = run_tool(forced)

    return result


# -----------------------
# 🔍 REFLECTION (STRICT)
# -----------------------
def reflect(result):
    prompt = f"""
Goal:
{GOAL}

Result:
{result}

CRITICAL:
- If result is simulation → say "No real progress made"
- If error → must change strategy
- ONLY count real-world outputs

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
# 🧠 GOAL CHECK
# -----------------------
def is_goal_complete():
    result = chat(
        f"""
Goal:
{GOAL}

Steps:
{memory}

Has REAL progress been achieved?

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

    return chat(f"Create a FINAL report using REAL outputs only:\n{text}", 2000)


def refine(final):
    return chat(f"Improve clarity:\n{final}", 1500)


# -----------------------
# STREAM SAFE
# -----------------------
def safe(text):
    return str(text).replace("\n", "\\n")


# -----------------------
# 🚀 MAIN LOOP (UPGRADED)
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

        # 1. PLAN
        plan = generate_plan()
        yield f"event: plan\ndata: {safe(plan)}\n\n"

        # 2. DECIDE
        action = decide_action(plan)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        # 3. EXECUTE
        result = execute_with_validation(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        # 4. REFLECT
        reflection = reflect(result)
        yield f"event: reflection\ndata: {safe(reflection)}\n\n"

        # 5. FAILURE TRACKING (UPGRADED)
        if is_simulation(result) or is_error(result) or "No real progress made" in reflection:
            failed_steps += 1
        else:
            failed_steps = 0

        # 6. MEMORY
        memory.append({
            "step": step + 1,
            "plan": plan,
            "action": action,
            "result": result,
            "reflection": reflection
        })

        save_memory()

        # 7. GOAL CHECK
        if step >= 2 and is_goal_complete():
            break

        time.sleep(0.3)

    final = refine(generate_final())

    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: done\n\n"
