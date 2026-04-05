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
- Each step must move the goal forward

FORMAT:
Step {step_number}: <short title>

- action 1
- action 2
- action 3
"""

    return chat(prompt, max_tokens=600)


# -----------------------
# 🎯 ACTION SELECTION (UPDATED 🔥)
# -----------------------
def decide_action(plan):
    prompt = f"""
Plan:
{plan}

Choose ONE action:
- write
- analyze
- search
- save_file
- save_structured

Guidelines:
- Use "search" for real-world info
- Use "save_file" for simple notes
- Use "save_structured" for important outputs
- Prefer saving useful outputs

Return JSON:
{{
    "action": "...",
    "input": "short instruction or content"
}}
"""

    try:
        return json.loads(chat(prompt, max_tokens=300))
    except:
        return {"action": "write", "input": "execute next step"}


# -----------------------
# 🛠 TOOL EXECUTION
# -----------------------
def execute_action(action):
    try:
        from tools import run_tool
        result = run_tool(action)
    except Exception as e:
        result = f"Tool error: {str(e)}"

    if isinstance(result, str) and "Generated content:" in result:
        result = result.split(":", 1)[-1].strip()

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

Be realistic.

FORMAT:
Evaluation:
<short evaluation>

Next:
<next step>
"""
    return chat(prompt, max_tokens=600)


# -----------------------
# 🧠 GOAL CHECK
# -----------------------
def is_goal_complete():
    prompt = f"""
Goal:
{GOAL}

Steps:
{memory}

Is the goal fully achieved?

Answer ONLY:
YES or NO
"""
    result = chat(prompt, max_tokens=10).lower()
    return "yes" in result


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

Result:
{step['result']}

Reflection:
{step['reflection']}

---
"""

    prompt = f"""
Create a COMPLETE FINAL REPORT.

Goal:
{GOAL}

Execution:
{steps_text}

RULES:
- Include ALL steps
- Do NOT summarize away details
- Keep structured

FORMAT:

# Final Result

## Goal
...

## Steps
...
"""

    return chat(prompt, max_tokens=1800)


# -----------------------
# 🧠 REFINE
# -----------------------
def refine(final):
    prompt = f"""
Improve clarity WITHOUT removing content:

{final}
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
# 🚀 MAIN LOOP (UPDATED 🔥)
# -----------------------
def run_agent_stream(goal, max_steps=6):
    global GOAL, memory, RUN_ID, STOP_FLAG

    GOAL = goal
    memory = []
    STOP_FLAG = False
    RUN_ID = str(uuid.uuid4())

    os.makedirs("outputs", exist_ok=True)

    MIN_STEPS = 3

    yield f"event: start\ndata: {safe(goal)}\n\n"

    step = 0

    while step < max_steps:

        if STOP_FLAG:
            yield f"event: stopped\ndata: Stopped by user\n\n"
            return

        yield f"event: step\ndata: {step+1}\n\n"

        plan = generate_plan()
        yield f"event: plan\ndata: {safe(plan)}\n\n"

        action = decide_action(plan)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        result = execute_action(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        # 🔥 AUTO-SAVE IMPORTANT RESULTS
        if action["action"] in ["write", "analyze"]:
            try:
                from tools import run_tool
                run_tool({
                    "action": "save_file",
                    "input": result[:200]  # avoid huge filenames
                })
            except:
                pass

        reflection = reflect(result)
        yield f"event: reflection\ndata: {safe(reflection)}\n\n"

        memory.append({
            "step": step + 1,
            "plan": plan,
            "action": action,
            "result": result,
            "reflection": reflection
        })

        save_memory()

        if len(memory) >= MIN_STEPS:
            if is_goal_complete():
                break

        step += 1
        time.sleep(0.3)

    # 🧠 FINAL OUTPUT
    final = generate_final()
    improved = refine(final)

    # 🔥 SAVE FINAL (STRUCTURED)
    from tools import run_tool
    run_tool({
        "action": "save_structured",
        "input": improved
    })

    filename = f"final_{RUN_ID}.txt"
    filepath = os.path.join("outputs", filename)

    with open(filepath, "w") as f:
        f.write(improved)

    download_url = f"/download/{filename}"

    yield f"event: final\ndata: {safe(improved)}\n\n"
    yield f"event: file\ndata: {safe(download_url)}\n\n"
    yield f"event: done\ndata: Goal completed\n\n"
