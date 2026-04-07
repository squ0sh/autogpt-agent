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

MEMORY_FILE = "memory.json"

# -----------------------
# 🧠 AGENT STATE (NEW BRAIN)
# -----------------------
state = {
    "strategy": "explore",
    "failed_steps": 0,
    "useful_steps": 0,
    "last_action": None,
    "confidence": "low",
    "loop_risk": "low",
    "progress_level": "none",
    "last_result_hash": ""
}


# -----------------------
# 🧾 MEMORY STORAGE
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
# 🧠 PLAN (NOW AWARE)
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    recent_context = memory[-3:] if len(memory) > 3 else memory

    prompt = f"""
You are an autonomous execution agent.

Goal:
{GOAL}

Recent steps:
{recent_context}

Agent State:
{state}

CRITICAL:
- ONLY real-world progress counts
- Thinking, planning, or long text DOES NOT count
- You MUST produce something usable or storable

STRATEGY MODE:
{state["strategy"]}

RULES:
- If stuck → try a DIFFERENT action type
- If no real output yet → prioritize STORE
- Avoid repeating same action
- Push toward execution

Step {step_number}:

FORMAT:

Step {step_number}: <outcome>

- Action 1: ...
- Action 2: ...
- Action 3: ...
"""

    return chat(prompt, 700)


# -----------------------
# 🎯 ACTION DECISION
# -----------------------
def decide_action(plan):
    prompt = f"""
Plan:
{plan}

State:
{state}

Choose BEST action:

Options:
- research
- create
- simulate
- store
- transform

IMPORTANT:
- STORE = highest priority if something useful exists
- Avoid repeating last action: {state["last_action"]}

Return JSON:
{{ "action": "...", "input": "..." }}
"""

    try:
        decision = json.loads(chat(prompt, 300))
    except:
        decision = {"action": "research", "input": plan}

    return decision


# -----------------------
# 🛠 TOOL EXECUTION
# -----------------------
def execute_action(action):
    try:
        from tools import run_tool
        return run_tool(action)
    except Exception as e:
        return {"error": str(e)}


# -----------------------
# 🧠 EVALUATION (REALITY ENGINE)
# -----------------------
def evaluate(result, action):
    text = str(result).lower()

    # REALNESS
    is_real = action["action"] == "store"

    # QUALITY
    length_score = min(len(text) / 500, 1.0)
    structure_score = 0.8 if isinstance(result, dict) else 0.3

    quality_score = 0.9 if is_real else (length_score + structure_score) / 2

    result_type = "real" if is_real else "simulated"

    useful = is_real
    novel = text != state["last_result_hash"]

    return {
        "useful": useful,
        "novel": novel,
        "quality_score": round(quality_score, 2),
        "result_type": result_type,
        "is_real": is_real
    }


# -----------------------
# 🧠 STATE UPDATE
# -----------------------
def update_state(evaluation, action, result):
    global state

    if evaluation["useful"]:
        state["useful_steps"] += 1
        state["failed_steps"] = 0
        state["confidence"] = "medium"
    else:
        state["failed_steps"] += 1

    if not evaluation["novel"]:
        state["loop_risk"] = "high"
    else:
        state["loop_risk"] = "low"

    if evaluation["result_type"] == "real":
        state["progress_level"] = "meaningful"

    if state["failed_steps"] >= 2:
        state["strategy"] = "explore"
    elif evaluation["is_real"]:
        state["strategy"] = "build"

    state["last_action"] = action["action"]
    state["last_result_hash"] = str(result)[:200]


# -----------------------
# 🧠 STOP CONDITION
# -----------------------
def should_stop(evaluation):
    if state["useful_steps"] >= 2 and evaluation["is_real"]:
        return True

    if state["failed_steps"] >= 4:
        return True

    return False


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

    return chat(f"Create final report:\n{text}", 1500)


def refine(final):
    return chat(f"Improve clarity:\n{final}", 1200)


# -----------------------
# STREAM SAFE
# -----------------------
def safe(text):
    return str(text).replace("\n", "\\n")


# -----------------------
# 🚀 MAIN LOOP
# -----------------------
def run_agent_stream(goal, max_steps=6):
    global GOAL, memory, RUN_ID, STOP_FLAG, state

    GOAL = goal
    memory = []
    STOP_FLAG = False
    RUN_ID = str(uuid.uuid4())

    state = {
        "strategy": "explore",
        "failed_steps": 0,
        "useful_steps": 0,
        "last_action": None,
        "confidence": "low",
        "loop_risk": "low",
        "progress_level": "none",
        "last_result_hash": ""
    }

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

        result = execute_action(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        evaluation = evaluate(result, action)
        yield f"event: evaluation\ndata: {safe(evaluation)}\n\n"

        update_state(evaluation, action, result)

        memory.append({
            "step": step + 1,
            "plan": plan,
            "action": action,
            "result": result,
            "evaluation": evaluation
        })

        save_memory()

        if should_stop(evaluation):
            break

        time.sleep(0.3)

    final = refine(generate_final())

    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: done\n\n"
