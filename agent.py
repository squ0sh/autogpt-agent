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
OUTPUT_DIR = "outputs"


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
# 🧠 STEP GENERATION
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    prompt = f"""
You are an execution agent working step-by-step.

Goal:
{GOAL}

Previous steps:
{memory}

Current step: {step_number}

RULES:
- ONLY generate Step {step_number}
- DO NOT generate multiple steps
- Each step must move the goal forward
- Avoid vague steps

FORMAT:
Step {step_number}: <short title>

- action 1 (specific)
- action 2 (specific)
- action 3 (specific)
"""

    return chat(prompt, max_tokens=600)


# -----------------------
# 🎯 ACTION SELECTION (UPGRADED)
# -----------------------
def decide_action(plan, step):
    prompt = f"""
Plan:
{plan}

Step: {step}

RULES:
- You MUST produce something tangible
- Avoid vague actions like "execute next step"
- If step >= 3 → MUST use "write"
- Input must contain REAL usable content

Actions:
- write (create real output file)
- analyze
- search

Return JSON:
{{
    "action": "...",
    "input": "specific useful content"
}}
"""

    try:
        decision = json.loads(chat(prompt, max_tokens=300))
    except:
        decision = {"action": "write", "input": plan}

    # 🔥 HARD ENFORCEMENT
    if step >= 3:
        decision["action"] = "write"

    return decision


# -----------------------
# 🛠 TOOL EXECUTION
# -----------------------
def execute_action(action):
    try:
        from tools import run_tool
        result = run_tool(action)
    except Exception as e:
        result = f"Tool error: {str(e)}"

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

Evaluate progress.

RULES:
- Be honest
- DO NOT claim goal complete unless files/products exist
- Focus on real-world progress

FORMAT:
Evaluation:
<short evaluation>

Next:
<next step>
"""
    return chat(prompt, max_tokens=500)


# -----------------------
# 🧠 GOAL CHECK (REAL)
# -----------------------
def is_goal_complete():
    if not os.path.exists(OUTPUT_DIR):
        return False

    files = os.listdir(OUTPUT_DIR)

    # ✅ Require at least 2 real outputs
    return len(files) >= 2


# -----------------------
# 🧠 FINAL OUTPUT
# -----------------------
def generate_final():
    steps_text = ""

    for step in memory:
        steps_text += f"""
Step {step['step']}

Plan:
{step['plan']}

Action:
{step['action']}

Result:
{step['result']}

Reflection:
{step['reflection']}

---
"""

    prompt = f"""
You are compiling a COMPLETE EXECUTION REPORT.

Goal:
{GOAL}

Execution Steps:
{steps_text}

INSTRUCTIONS:
- Include ALL steps
- Do NOT skip anything
- Expand clarity where useful
- Keep full structure

FORMAT:

# Final Result

## Goal
...

## Step 1
...

## Step 2
...

(continue through all steps)
"""

    return chat(prompt, max_tokens=1800)


# -----------------------
# 🧠 REFINE
# -----------------------
def refine(final):
    prompt = f"""
Improve clarity WITHOUT removing content:

{final}

Rules:
- DO NOT shorten
- DO NOT remove steps
- Only improve readability
"""
    return chat(prompt, max_tokens=1800)


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
# 🚀 MAIN LOOP
# -----------------------
def run_agent_stream(goal, max_steps=6):
    global GOAL, memory, RUN_ID, STOP_FLAG

    GOAL = goal
    memory = []
    STOP_FLAG = False
    RUN_ID = str(uuid.uuid4())

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    MIN_STEPS = 3

    yield f"event: start\ndata: {safe(goal)}\n\n"

    step = 0

    while step < max_steps:

        if STOP_FLAG:
            yield f"event: stopped\ndata: Stopped by user\n\n"
            return

        yield f"event: step\ndata: {step+1}\n\n"

        # PLAN
        plan = generate_plan()
        yield f"event: plan\ndata: {safe(plan)}\n\n"

        # ACTION
        action = decide_action(plan, step + 1)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        # EXECUTE
        result = execute_action(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        # REFLECT
        reflection = reflect(result)
        yield f"event: reflection\ndata: {safe(reflection)}\n\n"

        # MEMORY
        memory.append({
            "step": step + 1,
            "plan": plan,
            "action": action,
            "result": result,
            "reflection": reflection
        })

        save_memory()

        # STOP CONDITION
        if len(memory) >= MIN_STEPS and is_goal_complete():
            break

        step += 1
        time.sleep(0.3)

    # FINAL OUTPUT
    final = generate_final()
    improved = refine(final)

    filename = f"final_{RUN_ID}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w") as f:
        f.write(improved)

    download_url = f"/download/{filename}"

    yield f"event: final\ndata: {safe(improved)}\n\n"
    yield f"event: file\ndata: {safe(download_url)}\n\n"
    yield f"event: done\ndata: Goal completed\n\n"
