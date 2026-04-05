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
- Do NOT generate multiple steps
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

- write → create content
- analyze → evaluate something
- search → research info
- json → structured data

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

RULES:
- Be realistic
- Do NOT say goal complete unless fully done

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

Be strict.

Return ONLY:
YES or NO
"""

    result = chat(prompt).strip().lower()
    return "yes" in result


# -----------------------
# 🧠 FINAL OUTPUT
# -----------------------
def generate_final():
    prompt = f"""
Goal:
{GOAL}

Steps completed:
{json.dumps(memory, indent=2)}

Produce FINAL RESULT.

Requirements:
- Structured
- Clear
- Actionable
- Clean (no fluff)
"""

    return chat(prompt)


# -----------------------
# 🧠 REFINEMENT
# -----------------------
def refine(final):
    prompt = f"""
Improve this result:

{final}

Make it clearer, tighter, and more actionable.
"""

    return chat(prompt)


# -----------------------
# 🛑 STOP CONTROL
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

    from tools import write_file  # only used for FINAL output

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

    # -----------------------
    # 🏁 FINAL OUTPUT + FILE
    # -----------------------
    final = generate_final()
    improved = refine(final)

    final_filename = f"final_{RUN_ID}.txt"
    file_result = write_file(improved, final_filename)

    yield f"event: final\ndata: {safe(improved)}\n\n"
    yield f"event: file\ndata: {safe(file_result)}\n\n"
    yield f"event: done\ndata: Goal completed\n\n"
