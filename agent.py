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
        temperature=0.5,
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
        strategy_note = "⚠️ Previous steps failed. CHANGE STRATEGY completely. Use a different ACTION type."

    prompt = f"""
You are an autonomous execution agent.

Goal:
{GOAL}

Previous steps:
{memory}

{strategy_note}

RULES:
- Each step MUST produce REAL output (data, artifacts, structured results)
- Avoid repeating research
- If enough knowledge exists → CREATE or SIMULATE
- Prefer ACTION over thinking
- Do NOT just describe steps

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

Choose the BEST next action:

Options:
- research
- scrape
- create
- store
- simulate
- transform

RULES:
- If enough info → create or simulate
- If missing data → research
- Avoid repeating same action type
- Prefer REAL output actions

Return JSON:
{{ "action": "...", "input": "..." }}
"""

    try:
        decision = json.loads(chat(prompt, 300))
    except:
        decision = {"action": "research", "input": plan}

    if "http" in str(decision.get("input")):
        decision["action"] = "scrape"

    return decision


# -----------------------
# 🧠 REALITY VALIDATION
# -----------------------
def is_real_output(result, action_type):
    # If already structured → good
    if isinstance(result, dict):
        return True

    text = str(result).lower()

    fake_patterns = [
        "here are",
        "you should",
        "consider",
        "steps to",
        "guide",
        "strategy",
        "this approach",
        "you can",
    ]

    if any(p in text for p in fake_patterns):
        return False

    # Enforce strictness for real actions
    if action_type in ["create", "simulate", "store"]:
        return isinstance(result, dict)

    return True


# -----------------------
# 🛠 TOOL EXECUTION (WITH RETRY)
# -----------------------
def execute_with_validation(action):
    attempts = 0
    max_attempts = 3

    while attempts < max_attempts:
        try:
            from tools import run_tool
            result = run_tool(action)
        except Exception as e:
            result = f"Tool error: {str(e)}"

        if is_real_output(result, action.get("action")):
            return result

        attempts += 1

        # Force retry with stronger instruction
        action["input"] = str(action["input"]) + "\n\nRETRY: Produce REAL structured output. No explanations."

    return "FAILED: Could not produce real output"


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
- ONLY evaluate real output
- If result == FAILED → must change strategy
- If no meaningful progress → say EXACTLY: "No real progress made"
- DO NOT invent success

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

Has the goal been TRULY achieved with REAL outputs?

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
Plan: {s['plan']}
Action: {s['action']}
Result: {s['result']}
Reflection: {s['reflection']}
---
"""

    return chat(f"Create a structured final report with REAL outputs:\n{text}", 2000)


def refine(final):
    return chat(f"Improve clarity and readability:\n{final}", 1500)


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

        # 1. PLAN
        plan = generate_plan()
        yield f"event: plan\ndata: {safe(plan)}\n\n"

        # 2. DECIDE
        action = decide_action(plan)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        # 3. EXECUTE (WITH REALITY ENFORCEMENT)
        result = execute_with_validation(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        # 4. REFLECT
        reflection = reflect(result)
        yield f"event: reflection\ndata: {safe(reflection)}\n\n"

        # 5. FAILURE TRACKING
        if "No real progress made" in reflection or "FAILED" in result:
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

    # FINAL OUTPUT
    final = refine(generate_final())

    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: done\n\n"
