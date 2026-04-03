import json
import os
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Your agent goal (you can change this anytime)
GOAL = "Create a simple online business idea and validate it"

# In-memory storage (resets on restart)
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
        # fallback if model breaks JSON
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
def run_agent(max_steps=5):
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

        memory.append({
            "step": step + 1,
            "plan": plan,
            "action": action,
            "result": result,
            "reflection": reflection
        })

        # stop early if goal achieved
        if "goal achieved" in reflection.lower():
            break

    return memory


# -----------------------
# 🌐 Run Once (for Flask)
# -----------------------
def run_once():
    memory.clear()  # reset each run (optional)
    result = run_agent(max_steps=3)
    return result[-1] if result else {}


# -----------------------
# 🧪 Local Testing Only
# -----------------------
if __name__ == "__main__":
    output = run_once()
    print("\nFINAL OUTPUT:\n", output)

if __name__ == "__main__":
    run_forever()
