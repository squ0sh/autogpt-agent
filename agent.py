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
            data = json.load(f)

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
        temperature=0.6,
        max_tokens=700,
    )
    return response.choices[0].message.content.strip()


# -----------------------
# 🧠 PLAN
# -----------------------
def generate_plan():
    prompt = f"""
    Goal: {GOAL}

    Previous steps:
    {memory}

    What is the NEXT best step?

    Format:
    - Title
    - 3–5 bullets
    """
    return chat(prompt)


# -----------------------
# 🎯 ACTION
# -----------------------
def decide_action(plan):
    prompt = f"""
    Plan:
    {plan}

    Choose ONE action:
    - write
    - analyze
    - search

    Return JSON:
    {{
        "action": "...",
        "input": "short instruction"
    }}
    """

    try:
        return json.loads(chat(prompt))
    except:
        return {"action": "write", "input": "execute step"}


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
# 🔍 REFLECT
# -----------------------
def reflect(result):
    prompt = f"""
    Goal: {GOAL}

    Result:
    {result}

    Did this help?

    Respond:
    - short evaluation
    - improvement

    If done, say: GOAL ACHIEVED
    """
    return chat(prompt)


# -----------------------
# 🧠 FINAL ANSWER
# -----------------------
def generate_final():
    prompt = f"""
    Goal:
    {GOAL}

    Steps:
    {memory}

    Produce FINAL COMPLETE RESULT.
    Clean. Structured. Actionable.
    """
    return chat(prompt)


# -----------------------
# 🧠 SELF IMPROVE
# -----------------------
def refine(final):
    prompt = f"""
    Improve this result to be clearer, more actionable, and higher quality:

    {final}

    Return improved version only.
    """
    return chat(prompt)


# -----------------------
# 🛑 STOP CONTROL
# -----------------------
def stop():
    global STOP_FLAG
    STOP_FLAG = True


# -----------------------
# ⚡ STREAM
# -----------------------
def safe(text):
    return str(text).replace("\n", "\\n")


def run_agent_stream(goal, max_steps=5):
    global GOAL, memory, RUN_ID, STOP_FLAG

    GOAL = goal
    memory = []
    STOP_FLAG = False
    RUN_ID = str(uuid.uuid4())

    yield f"event: start\ndata: {safe(goal)}\n\n"

    for step in range(max_steps):

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

        if "goal achieved" in reflection.lower():
            break

        time.sleep(0.3)

    # FINAL
    final = generate_final()
    improved = refine(final)

    yield f"event: final\ndata: {safe(improved)}\n\n"
    yield f"event: done\ndata: complete\n\n"

