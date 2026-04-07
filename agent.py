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
        temperature=0.7,  # 🔥 slightly higher for creativity
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


# -----------------------
# 🧠 STEP GENERATION
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    prompt = f"""
You are a research + synthesis agent.

Goal:
{GOAL}

Previous steps:
{memory}

Current step: {step_number}

RULES:
- ONLY generate Step {step_number}
- Push toward deeper understanding, not repetition
- Prioritize insight over surface research

FORMAT:
Step {step_number}: <title>

- action 1
- action 2
- action 3
"""

    return chat(prompt, 600)


# -----------------------
# 🎯 ACTION SELECTION
# -----------------------
def decide_action(plan):
    prompt = f"""
Plan:
{plan}

Choose ONE action:

- search (for new external info)
- analyze (for thinking / synthesis)
- write (for generating structured insight)

Prefer:
- search if missing info
- analyze if enough info exists

Return JSON:
{{
    "action": "...",
    "input": "specific instruction"
}}
"""
    try:
        return json.loads(chat(prompt, 300))
    except:
        return {"action": "analyze", "input": "extract deeper insight"}


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
# 🔥 SYNTHESIS REFLECTION (UPGRADED)
# -----------------------
def reflect(result):
    prompt = f"""
Goal:
{GOAL}

New Information:
{result}

You are NOT summarizing.

You are THINKING.

Do ALL of the following:

1. Extract key patterns
2. Identify contradictions or gaps
3. Generate at least ONE NEW IDEA (not directly stated)
4. Combine domains into a unified model

Be bold. Avoid generic answers.

FORMAT:

Evaluation:
- Information Quality: low/medium/high
- Pattern Strength: weak/medium/strong

Patterns:
- ...

Contradictions / Gaps:
- ...

New Insight (IMPORTANT):
- ...

Next Direction:
- ...
"""
    return chat(prompt, 900)


# -----------------------
# 🧠 GOAL CHECK
# -----------------------
def is_goal_complete():
    prompt = f"""
Goal:
{GOAL}

Steps taken:
{memory}

Has the goal been FULLY achieved with strong synthesis?

Return ONLY:
YES or NO
"""
    result = chat(prompt, 10).lower()
    return "yes" in result


# -----------------------
# 🧠 FINAL OUTPUT (SYNTHESIS MODE)
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
You are producing a FINAL SYNTHESIS REPORT.

Goal:
{GOAL}

Execution Steps:
{steps_text}

INSTRUCTIONS:
- DO NOT summarize step-by-step only
- Extract deeper meaning across all steps
- Combine ideas into a unified framework
- Highlight NEW insights discovered

FORMAT:

# Final Result

## Goal

## Core Patterns

## Key Contradictions

## Breakthrough Insights

## Unified Model

## Practical Applications
"""

    return chat(prompt, 1800)


# -----------------------
# 🧠 REFINE (NO LOSS)
# -----------------------
def refine(final):
    prompt = f"""
Improve clarity WITHOUT removing anything:

{final}

Rules:
- Keep ALL insights
- Keep structure
- Only enhance readability
"""
    return chat(prompt, 1800)


# -----------------------
# 🛑 STOP
# -----------------------
def stop():
    global STOP_FLAG
    STOP_FLAG = True


# -----------------------
# ⚡ SAFE STREAM
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

    os.makedirs("outputs", exist_ok=True)

    MIN_STEPS = 3

    yield f"event: start\ndata: {safe(goal)}\n\n"

    step = 0

    while step < max_steps:

        if STOP_FLAG:
            yield f"event: stopped\ndata: Stopped\n\n"
            return

        yield f"event: step\ndata: {step+1}\n\n"

        plan = generate_plan()
        yield f"event: plan\ndata: {safe(plan)}\n\n"

        action = decide_action(plan)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        result = execute_action(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

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

    final = generate_final()
    improved = refine(final)

    filename = f"final_{RUN_ID}.txt"
    filepath = os.path.join("outputs", filename)

    with open(filepath, "w") as f:
        f.write(improved)

    download_url = f"/download/{filename}"

    yield f"event: final\ndata: {safe(improved)}\n\n"
    yield f"event: file\ndata: {safe(download_url)}\n\n"
    yield f"event: done\ndata: Goal completed\n\n"
