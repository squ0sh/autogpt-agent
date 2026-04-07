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
# 🧠 STEP GENERATION (SYNTHESIS)
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    prompt = f"""
You are a RESEARCH + SYNTHESIS agent.

Goal:
{GOAL}

Previous steps:
{memory}

Current step: {step_number}

CORE OBJECTIVE:
Each step must:
1. Extract useful information
2. Identify patterns or principles
3. Connect ideas to previous steps
4. Generate at least ONE new insight

RULES:
- ONLY generate Step {step_number}
- DO NOT repeat previous work
- Avoid shallow research
- Focus on deeper understanding

FORMAT:
Step {step_number}: <insight-focused title>

- Action 1: <what to research or analyze>
- Action 2: <what pattern to extract>
- Action 3: <what new insight to generate>
"""

    return chat(prompt, max_tokens=700)


# -----------------------
# 🎯 ACTION SELECTION (SMARTER)
# -----------------------
def decide_action(plan):
    prompt = f"""
Plan:
{plan}

Choose ONE action:

- search → gather new information
- analyze → extract patterns or insights
- write → synthesize or generate ideas

RULES:
- Prefer search early
- Prefer analyze when enough data exists
- Prefer write when generating insights
- Avoid repeating same action too often

Return JSON:
{{
    "action": "...",
    "input": "clear and specific instruction"
}}
"""

    try:
        return json.loads(chat(prompt, max_tokens=300))
    except:
        return {"action": "search", "input": f"{GOAL} patterns insights explanation"}


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
# 🔍 REFLECTION (SYNTHESIS AWARE)
# -----------------------
def reflect(result):
    prompt = f"""
Goal:
{GOAL}

Result:
{result}

Evaluate this step based on SYNTHESIS quality.

CRITERIA:
1. Did this produce useful information?
2. Did it identify any patterns?
3. Did it generate NEW insight?
4. Did it connect to previous steps?

Be critical.

FORMAT:

Evaluation:
- Information Quality: (low/medium/high)
- Pattern Detection: (yes/no)
- Insight Quality: (weak/strong)
- Overall Value: (low/medium/high)

Key Insight:
<most important new idea>

Next Direction:
<what should be explored or connected next>
"""

    return chat(prompt, max_tokens=700)


# -----------------------
# 🧠 GOAL CHECK
# -----------------------
def is_goal_complete():
    prompt = f"""
Goal:
{GOAL}

Steps:
{memory}

Has enough meaningful insight and synthesis been achieved?

Return ONLY:
YES or NO
"""
    result = chat(prompt, max_tokens=20).strip().lower()
    return "yes" in result


# -----------------------
# 🧠 FINAL OUTPUT (SYNTHESIS)
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

YOUR TASK:
- Extract key insights
- Identify recurring patterns
- Connect ideas across steps
- Generate NEW conclusions

DO NOT summarize — synthesize.

FORMAT:

# Final Result

## Goal

## Key Insights
- ...

## Patterns Discovered
- ...

## New Connections
- ...

## Final Synthesis
<your best original insight>

## Practical Takeaways
- ...
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
- Keep all insights
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
