import json
import os
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Default goal (can be overridden from UI)
GOAL = "Create a simple online business idea and validate it"

# In-memory storage
memory = []


# -----------------------
# 🔹 Core Chat Function
# -----------------------
def chat(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# -----------------------
# 🧠 Planning Step
# -----------------------
def generate_plan():
    prompt = f"""
    Goal: {GOAL}

    Previous memory:
    {memory}

    What is the next best step to achieve the goal?
    Be specific and actionable.
    """
    return chat(prompt)


# -----------------------
# 🎯 Decide Action
# -----------------------
def decide_action(plan):
    prompt = f"""
    Based on this plan:

    {plan}

    Choose ONE action:
    - write
    - analyze
    - search

    Respond ONLY in valid JSON:
    {{
        "action": "...",
        "input": "..."
    }}
    """

    response = chat(prompt)

    try:
        return json.loads(response)
    except:
        return {
            "action": "write",
            "input": response
        }


# -----------------------
# 🛠 Execute Action
# -----------------------
def execute_action(action):
    from tools import run_tool
    return run_tool(action)


# -----------------------
# 🔍 Reflection Step
# -----------------------
def reflect(result):
    prompt = f"""
    Goal: {GOAL}

    Result of last action:
    {result}

    Did this help achieve the goal?
    What should be done next differently or better?
    If the goal is complete, say "GOAL ACHIEVED".
    """
    return chat(prompt)


# -----------------------
# 🔁 Main Agent Loop
# -----------------------
def run_agent(max_steps=3):
    steps_output = []

    for step in range(max_steps):
        print(f"\n--- Step {step+1} ---")

        plan = generate_plan()
        print("PLAN:", plan)

        action = decide_action(plan)
        print("ACTION:", action)

        result = execute_action(action)
        print("RESULT:", result)

        reflection = reflect(result)
        print("REFLECTION:", reflection)

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


# -----------------------
# 🌐 Run Once (for UI)
# -----------------------
def run_once(custom_goal=None):
    global GOAL

    if custom_goal and custom_goal.strip():
        GOAL = custom_goal

    memory.clear()

    result = run_agent(max_steps=3)

    return result


# -----------------------
# 🧪 Local Test
# -----------------------
if __name__ == "__main__":
    output = run_once()
    print("\nFINAL OUTPUT:\n", json.dumps(output, indent=2))
