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
def chat(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=700,
    )
    return response.choices[0].message.content.strip()


# -----------------------
# 🧠 STEP GENERATION
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    prompt = f"""
You are an execution agent.

Goal:
{GOAL}

Previous steps:
{json.dumps(memory, indent=2)}

Current step: {step_number}

RULES:
- ONLY generate Step {step_number}
- Must move the goal forward
- Be specific and actionable

FORMAT:
Step {step_number}: <short title>

- action 1
- action 2
- action 3
"""

    return chat(prompt)


# -----------------------
# 🎯 ACTION SELECTION
# -----------------------
def decide_action(plan):
    prompt = f"""
Plan:
{plan}

Choose the BEST action:

- write
- analyze
- search
- json

Return JSON:
{{
    "action": "...",
    "input": "specific instruction"
}}
"""
    try:
        return json.loads(chat(prompt))
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

FORMAT:
Evaluation:
<short evaluation>

Next:
<clear next step>
"""
    return chat(prompt)


# -----------------------
# 🧠 GOAL CHECK
# -----------------------
def is_goal_complete():
    prompt = f"""
Goal:
{GOAL}

Steps taken:
{json.dumps(memory, indent=2)}

Has the goal been FULLY achieved?

Return ONLY: YES or NO
"""
    return "yes" in chat(prompt).lower()


# -----------------------
# 🧠 FINAL OUTPUT
# -----------------------
def generate_final():
    return chat(f"""
Goal:
{GOAL}

Steps completed:
{json.dumps(memory, indent=2)}

Produce FINAL RESULT.
""")


def refine(final):
    return chat(f"Improve this:\n\n{final}")


# -----------------------
# 🛑 STOP CONTROL
# -----------------------
def stop():
    global STOP_FLAG
    STOP_FLAG = True


# -----------------------
# 🚀 MAIN LOOP (FIXED)
# -----------------------
def run_agent_stream(goal, max_steps=6):
    global GOAL, memory, RUN_ID, STOP_FLAG

    from tools import write_file

    GOAL = goal
    memory = []
    STOP_FLAG = False
    RUN_ID = str(uuid.uuid4())

    yield f"event: start\ndata: {goal}\n\n"

    for step in range(max_steps):

        if STOP_FLAG:
            yield "event: stopped\ndata: Stopped\n\n"
            return

        yield f"event: step\ndata: {step+1}\n\n"

        plan = generate_plan()
        yield f"event: plan\ndata: {plan}\n\n"

        action = decide_action(plan)
        yield f"event: action\ndata: {json.dumps(action)}\n\n"

        result = execute_action(action)
        yield f"event: result\ndata: {result}\n\n"

        reflection = reflect(result)
        yield f"event: reflection\ndata: {reflection}\n\n"

        memory.append({
            "step": step + 1,
            "plan": plan,
            "action": action,
            "result": result,
            "reflection": reflection
        })

        save_memory()
        time.sleep(0.2)

    # ✅ FINAL OUTPUT
    final = refine(generate_final())

    filename = f"final_{RUN_ID}.txt"
    write_file(final, filename)

    download_url = f"/download/{filename}"

    yield f"event: final\ndata: {final}\n\n"
    yield f"event: file\ndata: {download_url}\n\n"
    yield "event: done\ndata: complete\n\n"

