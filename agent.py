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
# 🧠 STEP GENERATION (UPGRADED)
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    global failed_steps

    # 🧠 Use only recent memory (prevents overload)
    recent_context = memory[-3:] if len(memory) > 3 else memory

    # ⚠️ Failure adaptation
    strategy_note = ""
    if failed_steps >= 2:
        strategy_note = "⚠️ Previous steps failed. ABANDON current approach. Try a completely different strategy or ACTION TYPE."

    # 🔥 Force action after early steps
    force_action_note = ""
    if step_number >= 2:
        force_action_note = """
MANDATORY:
- You MUST produce a step that leads to a REAL ACTION (create, simulate, store)
- DO NOT propose more research unless absolutely necessary
- The system must start producing tangible outputs
"""

    prompt = f"""
You are an autonomous execution agent.

Goal:
{GOAL}

Recent context (last steps only):
{recent_context}

{strategy_note}

{force_action_note}

CAPABILITIES AVAILABLE:
- research → gather information
- simulate → predict outcomes
- create → generate real outputs (ideas, assets, structured data)
- store → save useful results
- transform → improve/refine outputs

CORE RULES:
- Every step MUST move closer to a REAL outcome
- Avoid repeating previous work
- Prefer ACTION over thinking
- If enough information exists → STOP researching and START creating/simulating
- Outputs should be usable, not theoretical

THINK:
What is the MOST LEVERAGE next step that produces a tangible result?

Step {step_number}:

Format STRICTLY:

Step {step_number}: <clear outcome-focused title>

- Action 1: <specific actionable task>
- Action 2: <specific actionable task>
- Action 3: <specific actionable task>
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
- If enough info exists → simulate or create
- If data is missing → research
- Avoid repeating same action type
- Prefer ACTION over thinking

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
- If no meaningful progress → say EXACTLY: "No real progress made"
- If action created something useful → recognize it
- DO NOT invent outcomes

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

Has the goal been TRULY achieved with real outcomes (not just research)?

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

    return chat(f"Create a clear, structured final report:\n{text}", 2000)


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

        # 3. EXECUTE
        result = execute_action(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        # 4. REFLECT
        reflection = reflect(result)
        yield f"event: reflection\ndata: {safe(reflection)}\n\n"

        # 5. FAILURE TRACKING
        if "No real progress made" in reflection:
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

