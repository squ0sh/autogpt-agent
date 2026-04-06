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
# 🧠 STEP GENERATION (SMART)
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    global failed_steps

    strategy_note = ""
    if failed_steps >= 2:
        strategy_note = "⚠️ Previous steps failed. CHANGE STRATEGY completely. Try a different angle or data source."

    prompt = f"""
You are an autonomous execution agent.

Goal:
{GOAL}

Previous steps:
{memory}

{strategy_note}

RULES:
- Each step MUST produce new real-world insights
- DO NOT repeat previous research
- If stuck → change strategy completely
- Prioritize high-quality sources (guides, case studies, real data)

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

- research
- search
- scrape
- analyze
- write

RULES:
- If learning needed → research
- If URL present → scrape
- Avoid "write" unless summarizing real data

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
# 🛠 TOOL EXECUTION
# -----------------------
def execute_action(action):
    try:
        from tools import run_tool
        return run_tool(action)
    except Exception as e:
        return f"Tool error: {str(e)}"


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
- ONLY evaluate real output
- If no meaningful progress → say "No real progress made"
- DO NOT invent outcomes (sales, traffic, etc.)

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
        f"Goal: {GOAL}\nSteps: {memory}\nHas the goal been achieved? Answer YES or NO only.",
        20
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
Result: {s['result']}
Reflection: {s['reflection']}
---
"""

    return chat(f"Create a clean, structured final report:\n{text}", 2000)


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

        # 2. ACTION
        action = decide_action(plan)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        # 3. EXECUTE
        result = execute_action(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        # 4. REFLECT
        reflection = reflect(result)
        yield f"event: reflection\ndata: {safe(reflection)}\n\n"

        # 5. FAILURE TRACKING
        if "No real progress" in reflection:
            failed_steps += 1
        else:
            failed_steps = 0

        # 6. STORE MEMORY
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

