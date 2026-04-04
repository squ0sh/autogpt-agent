import json
import os
import time
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GOAL = "Create a simple online business idea and validate it"
memory = []


# -----------------------
# 🔹 Core Chat
# -----------------------
def chat(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# -----------------------
# 🧠 Plan
# -----------------------
def generate_plan():
    prompt = f"""
    Goal: {GOAL}

    Previous memory:
    {memory}

    What is the next best step?
    """
    return chat(prompt)


# -----------------------
# 🎯 Action
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
        "input": "..."
    }}
    """

    try:
        return json.loads(chat(prompt))
    except:
        return {"action": "write", "input": plan}


# -----------------------
# 🛠 Tool Execution
# -----------------------
def execute_action(action):
    from tools import run_tool
    return run_tool(action)


# -----------------------
# 🔍 Reflection
# -----------------------
def reflect(result):
    prompt = f"""
    Goal: {GOAL}

    Result:
    {result}

    Did this help?
    What should improve?
    Say GOAL ACHIEVED if done.
    """
    return chat(prompt)


# -----------------------
# 🔁 NORMAL MODE (UNCHANGED)
# -----------------------
def run_agent(max_steps=3):
    steps_output = []

    for step in range(max_steps):
        plan = generate_plan()
        action = decide_action(plan)
        result = execute_action(action)
        reflection = reflect(result)

        step_data = {
            "step": step + 1,
            "plan": plan,
            "action": action,
            "result": result,
            "reflection": reflection
        }

        memory.append(step_data)
        steps_output.append(step_data)

        if "goal achieved" in reflection.lower():
            break

    return {
        "goal": GOAL,
        "steps": steps_output
    }


def run_once(custom_goal=None):
    global GOAL

    if custom_goal and custom_goal.strip():
        GOAL = custom_goal

    memory.clear()
    return run_agent(max_steps=3)


# -----------------------
# ⚡ STREAM MODE (NEW)
# -----------------------
def safe(text):
    return str(text).replace("\n", "\\n")


def run_agent_stream(goal, max_steps=3):
    global GOAL
    GOAL = goal
    memory.clear()

    yield f"event: start\ndata: {safe('Starting goal: ' + goal)}\n\n"

    for step in range(max_steps):
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

        if "goal achieved" in reflection.lower():
            yield f"event: done\ndata: Goal achieved\n\n"
            return

        time.sleep(0.5)

    yield f"event: done\ndata: Finished all steps\n\n"

