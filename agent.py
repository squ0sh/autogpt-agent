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
# 🛑 STOP (FIXED 🔥)
# -----------------------
def stop():
    global STOP_FLAG
    STOP_FLAG = True


# -----------------------
# 🧠 CORE CHAT (AUTO-CONTINUE)
# -----------------------
def chat(prompt, max_tokens=1200):
    messages = [{"role": "user", "content": prompt}]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.5,
        max_tokens=max_tokens,
    )

    output = response.choices[0].message.content.strip()

    # Auto-continue if cut off
    if response.choices[0].finish_reason == "length":
        messages.append({"role": "assistant", "content": output})
        messages.append({
            "role": "user",
            "content": "Continue exactly where you left off."
        })

        continuation = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.5,
            max_tokens=max_tokens,
        )

        output += "\n" + continuation.choices[0].message.content.strip()

    return output


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

CRITICAL:
- Do NOT claim actions are completed unless tools actually executed them
- Stay grounded in real-world constraints

FORMAT:
Step {step_number}: <short title>

- action 1
- action 2
- action 3
"""

    return chat(prompt, max_tokens=800)


# -----------------------
# 🎯 ACTION SELECTION
# -----------------------
def decide_action(plan):
    prompt = f"""
Plan:
{plan}

Choose ONE action:

- write
- analyze
- search
- scrape
- research
- save_file
- save_structured

Guidelines:

- Use "research" for:
  trends, competitors, niches, platforms, decisions

- "research" = search + scrape combined

- Do NOT rely on general knowledge if real data is needed

- If input contains a URL → ALWAYS use "scrape"

CRITICAL:
If the step involves learning from real-world data:
→ you MUST use "research"

Return JSON:
{{
    "action": "...",
    "input": "short instruction or URL/content"
}}
"""

    try:
        decision = json.loads(chat(prompt, max_tokens=400))
    except:
        decision = {"action": "write", "input": "continue execution"}

    # Force scrape if URL detected
    if isinstance(decision.get("input"), str) and "http" in decision["input"]:
        decision["action"] = "scrape"

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
# 🔍 REFLECTION (REAL DATA)
# -----------------------
def reflect(result):
    prompt = f"""
Goal:
{GOAL}

Result:
{result}

Analyze the REAL data only.

RULES:
- Only describe what ACTUALLY happened
- Do NOT assume tasks were completed
- Extract insights from real data
- Be critical and realistic

FORMAT:

Evaluation:
<what actually happened>

Insights:
- insight 1
- insight 2
- insight 3

Next:
<what should happen next based on real data>
"""
    return chat(prompt, max_tokens=800)


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
    result = chat(prompt, max_tokens=20).lower()
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
- Do NOT remove details
- Keep structured

FORMAT:

# Final Result

## Goal
...

## Steps
...
"""

    return chat(prompt, max_tokens=3000)


# -----------------------
# 🧠 REFINE
# -----------------------
def refine(final):
    prompt = f"""
Improve clarity WITHOUT removing content:

{final}
"""
    return chat(prompt, max_tokens=2500)


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

        # 🔥 STOP HANDLING
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

        # Auto-save useful outputs
        if action["action"] in ["write", "analyze"]:
            try:
                from tools import run_tool
                run_tool({
                    "action": "save_file",
                    "input": str(result)[:200]
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

    # FINAL OUTPUT
    final = generate_final()
    improved = refine(final)

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
