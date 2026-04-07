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
# 🧠 PLAN GENERATION
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
- Each step MUST produce REAL, GROUNDED output
- Output must include either:
  (1) a real source
  (2) or be explicitly marked as simulation
- Prefer CREATE, SIMULATE, TRANSFORM over thinking
- Do NOT describe steps

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
- If real-world info needed → research/scrape
- If enough info → create or simulate
- Avoid repeating actions
- Prefer actions that produce structured, grounded output

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
# 🧠 GROUNDING VALIDATION (NEW)
# -----------------------
def is_grounded_output(result):
    if not isinstance(result, dict):
        return False

    # Must include grounding
    if "source" in result:
        return True

    if result.get("simulation") is True:
        return True

    return False


# -----------------------
# 🧠 REALITY VALIDATION
# -----------------------
def is_real_output(result, action_type):
    if not isinstance(result, dict):
        return False

    # Strict for powerful actions
    if action_type in ["create", "simulate", "store", "transform"]:
        return is_grounded_output(result)

    return True


# -----------------------
# 🛠 TOOL EXECUTION WITH ENFORCEMENT
# -----------------------
def execute_with_validation(action):
    attempts = 0
    max_attempts = 3

    while attempts < max_attempts:
        try:
            from tools import run_tool
            result = run_tool(action)
        except Exception as e:
            result = {"error": str(e)}

        if is_real_output(result, action.get("action")):
            return result

        attempts += 1

        # Force correction
        action["input"] = str(action["input"]) + """
        
RETRY REQUIREMENTS:
- Return ONLY structured JSON
- MUST include either:
  "source": "real URL or reference"
  OR
  "simulation": true
- No explanations
"""

    return {"error": "FAILED: Could not produce grounded output"}


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
- Evaluate ONLY real, grounded outputs
- If result contains error → must change strategy
- If no progress → say EXACTLY: "No real progress made"
- DO NOT assume success

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

Has the goal been achieved with REAL, GROUNDED outputs?

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

    return chat(f"Create a FINAL report using ONLY grounded outputs:\n{text}", 2000)


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

        # 3. EXECUTE (WITH REALITY + GROUNDING)
        result = execute_with_validation(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        # 4. REFLECT
        reflection = reflect(result)
        yield f"event: reflection\ndata: {safe(reflection)}\n\n"

        # 5. FAILURE TRACKING
        if "No real progress made" in reflection or "error" in str(result).lower():
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
