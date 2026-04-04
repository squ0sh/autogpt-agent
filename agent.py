import json
import os
import time
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GOAL = ""
memory = []


# -----------------------
# 🔹 Core Chat
# -----------------------
def chat(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()


# -----------------------
# 🧠 Plan
# -----------------------
def generate_plan():
    prompt = f"""
    You are an autonomous execution agent.

    Goal: {GOAL}

    Previous steps:
    {memory}

    What is the NEXT best step?

    Respond with:
    - Short title
    - 3–5 bullet points
    - Clear and actionable
    """
    return chat(prompt)


# -----------------------
# 🎯 Decide Action
# -----------------------
def decide_action(plan):
    prompt = f"""
    Plan:
    {plan}

    Choose ONE action:
    - write
    - analyze
    - search

    IMPORTANT:
    - Keep input SHORT
    - Do NOT repeat the plan

    Return JSON:
    {{
        "action": "...",
        "input": "short instruction"
    }}
    """

    try:
        return json.loads(chat(prompt))
    except:
        return {"action": "write", "input": "Execute next step"}


# -----------------------
# 🛠 Execute Action
# -----------------------
def execute_action(action):
    from tools import run_tool

    result = run_tool(action)

    if isinstance(result, str):
        if result.lower().startswith("generated content"):
            result = result.split(":", 1)[-1].strip()

    return result


# -----------------------
# 🔍 Reflection
# -----------------------
def reflect(result):
    prompt = f"""
    Goal: {GOAL}

    Result:
    {result}

    Did this move us closer to the goal?

    Respond with:
    - Short evaluation
    - What to improve next

    If goal is complete, say: GOAL ACHIEVED
    """
    return chat(prompt)


# -----------------------
# 🏁 FINAL ANSWER
# -----------------------
def generate_final_answer():
    prompt = f"""
    You are completing the goal.

    Goal:
    {GOAL}

    Steps taken:
    {memory}

    Now produce the FINAL RESULT.

    Requirements:
    - Clear and structured
    - No repetition
    - Actionable
    - Feels COMPLETE

    This should feel like the finished answer to the goal.
    """
    return chat(prompt)


# -----------------------
# ⚡ STREAM MODE
# -----------------------
def safe(text):
    return str(text).replace("\n", "\\n")


def run_agent_stream(goal, max_steps=3):
    global GOAL
    GOAL = goal
    memory.clear()

    yield f"event: start\ndata: {safe('Starting: ' + goal)}\n\n"

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
            break

        time.sleep(0.4)

    # 🔥 FINAL OUTPUT
    final = generate_final_answer()
    yield f"event: final\ndata: {safe(final)}\n\n"

    yield f"event: done\ndata: Goal completed\n\n"
