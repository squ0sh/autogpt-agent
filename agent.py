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
# 🧠 THINKER (PLAN)
# -----------------------
def thinker():
    step_number = len(memory) + 1

    return chat(f"""
You are the THINKER agent.

Goal:
{GOAL}

Memory:
{memory}

Generate the BEST next step.

Rules:
- Be strategic
- Avoid repetition
- Move toward useful outcome

Format:

Step {step_number}: <title>

- action 1
- action 2
- action 3
""", 600)


# -----------------------
# 🧩 ORCHESTRATOR (ACTION DECISION)
# -----------------------
def orchestrator(plan):
    try:
        decision = json.loads(chat(f"""
You are the ORCHESTRATOR.

Plan:
{plan}

Choose the BEST action.

Options:
- search
- analyze
- write

Rules:
- Prefer SEARCH if information is missing
- Avoid useless actions

Return JSON:
{{ "action": "...", "input": "..." }}
""", 300))
    except:
        decision = {"action": "search", "input": plan}

    return decision


# -----------------------
# ⚙️ ACTOR (TOOLS)
# -----------------------
def actor(action):
    try:
        from tools import run_tool
        return run_tool(action)
    except Exception as e:
        return f"Tool error: {str(e)}"


# -----------------------
# ❤️ FEELER (EVALUATION)
# -----------------------
def feeler(result):
    return chat(f"""
You are the FEELER agent.

Goal:
{GOAL}

Result:
{result}

Evaluate STRICTLY.

Return:

Score (0-10):
<score>

On Track:
yes/no

Insights:
- ...
- ...

Next Decision:
- continue
- change_strategy
""", 500)


# -----------------------
# 🧠 GOAL CHECK
# -----------------------
def is_goal_complete():
    if len(memory) < 3:
        return False

    result = chat(f"""
Goal:
{GOAL}

Steps:
{memory}

Has the goal been sufficiently explored and answered?

YES or NO
""", 20).lower()

    return "yes" in result


# -----------------------
# 🧠 FINAL OUTPUT
# -----------------------
def generate_final():
    text = ""

    for s in memory:
        text += f"""
Step {s['step']}

Plan:
{s['plan']}

Action:
{s['action']}

Result:
{s['result']}

Evaluation:
{s['evaluation']}

---
"""

    return chat(f"""
Create a FINAL REPORT.

Goal:
{GOAL}

Steps:
{text}

Include:
- key findings
- best insights
- useful links (if any)
""", 1800)


def refine(final):
    return chat(f"Improve clarity:\n{final}", 1500)


# -----------------------
# 🛑 STOP
# -----------------------
def stop():
    global STOP_FLAG
    STOP_FLAG = True


# -----------------------
# ⚡ STREAM SAFE
# -----------------------
def safe(text):
    return str(text).replace("\n", "\\n")


# -----------------------
# 🚀 MAIN LOOP (MULTI-AGENT)
# -----------------------
def run_agent_stream(goal, max_steps=6):
    global GOAL, memory, RUN_ID, STOP_FLAG

    GOAL = goal
    memory = []
    STOP_FLAG = False
    RUN_ID = str(uuid.uuid4())

    yield f"event: start\ndata: {safe(goal)}\n\n"

    step = 0

    while step < max_steps:

        if STOP_FLAG:
            yield f"event: stopped\ndata: stopped\n\n"
            return

        yield f"event: step\ndata: {step+1}\n\n"

        # 🧠 THINK
        plan = thinker()
        yield f"event: plan\ndata: {safe(plan)}\n\n"

        # 🧩 DECIDE
        action = orchestrator(plan)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        # ⚙️ ACT
        result = actor(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        # ❤️ FEEL
        evaluation = feeler(result)
        yield f"event: evaluation\ndata: {safe(evaluation)}\n\n"

        memory.append({
            "step": step + 1,
            "plan": plan,
            "action": action,
            "result": result,
            "evaluation": evaluation
        })

        save_memory()

        # 🧠 ORCHESTRATION LOGIC
        if "change_strategy" in evaluation.lower():
            step += 1
            continue

        if len(memory) >= 3 and is_goal_complete():
            break

        step += 1
        time.sleep(0.3)

    final = refine(generate_final())

    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: complete\n\n"
