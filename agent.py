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
You are a general-purpose autonomous agent.

Goal:
{GOAL}

Previous steps:
{memory}

Current step: {step_number}

RULES:
- ONLY generate Step {step_number}
- Each step must move toward real understanding or useful output
- Avoid vague steps
- Prefer actions that produce real-world information

FORMAT:
Step {step_number}: <short title>

- action 1 (specific)
- action 2 (specific)
- action 3 (specific)
"""

    return chat(prompt, max_tokens=600)


# -----------------------
# 🎯 ACTION SELECTION (SEARCH-FIRST)
# -----------------------
def decide_action(plan, step):
    prompt = f"""
Plan:
{plan}

Step: {step}

RULES:
- You MUST produce useful output
- NO placeholders like "execute next step"
- Prefer SEARCH for real-world grounding
- Use ANALYZE to synthesize findings
- WRITE only for summarizing insights

Actions:
- search (find real information + links)
- analyze (break down info)
- write (summarize findings clearly)

Return JSON:
{{
    "action": "...",
    "input": "specific query or instruction"
}}
"""

    try:
        decision = json.loads(chat(prompt, max_tokens=300))
    except:
        decision = {"action": "search", "input": plan}

    # 🔥 FORCE SEARCH EARLY
    if step <= 2:
        decision["action"] = "search"

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
# 🔍 REFLECTION (UPGRADED)
# -----------------------
def reflect(result):
    prompt = f"""
Goal:
{GOAL}

Result:
{result}

Evaluate progress.

RULES:
- Must reference REAL findings
- Identify what was learned
- Suggest next concrete step
- DO NOT be generic

FORMAT:
Evaluation:
<what was actually learned>

Next:
<next specific step>
"""
    return chat(prompt, max_tokens=500)


# -----------------------
# 🧠 GOAL CHECK (SMART)
# -----------------------
def is_goal_complete():
    if len(memory) < 3:
        return False

    prompt = f"""
Goal:
{GOAL}

Steps:
{memory}

Has the goal been meaningfully addressed with:
- real research
- useful insights
- actionable understanding

Return ONLY:
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

Action:
{step['action']}

Result:
{step['result']}

Reflection:
{step['reflection']}

---
"""

    prompt = f"""
You are compiling a FINAL REPORT.

Goal:
{GOAL}

Execution Steps:
{steps_text}

INSTRUCTIONS:
- Include ALL steps
- Keep useful links and findings
- Synthesize insights clearly
- Maintain structure

FORMAT:

# Final Result

## Goal

## Key Findings

## Step-by-Step Breakdown

## Final Insight
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
- Do NOT shorten
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

        action = decide_action(plan, step + 1)
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

        if len(memory) >= MIN_STEPS and is_goal_complete():
            break

        step += 1
        time.sleep(0.3)

    final = generate_final()
    improved = refine(final)

    yield f"event: final\ndata: {safe(improved)}\n\n"
    yield f"event: done\ndata: Goal completed\n\n"
