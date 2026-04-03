import time
import json
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GOAL = "Create a simple online business idea and validate it"

memory = []


def chat(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content


def generate_plan():
    prompt = f"""
    Goal: {GOAL}

    Memory:
    {memory}

    What is the next best step?
    """
    return chat(prompt)


def decide_action(plan):
    prompt = f"""
    Plan:
    {plan}

    Choose ONE action:
    - write
    - analyze
    - search

    Respond ONLY in JSON:
    {{
        "action": "...",
        "input": "..."
    }}
    """

    response = chat(prompt)

    try:
        return json.loads(response)
    except:
        return {"action": "write", "input": response}


def execute_action(action):
    from tools import run_tool
    return run_tool(action)


def reflect(result):
    prompt = f"""
    Goal: {GOAL}

    Result:
    {result}

    Did this help? What should be improved next?
    """
    return chat(prompt)


def run_agent():
    for step in range(5):
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
            "plan": plan,
            "action": action,
            "result": result,
            "reflection": reflection
        })

        if "goal achieved" in reflection.lower():
            break


def run_forever():
    while True:
        run_agent()
        time.sleep(60)


if __name__ == "__main__":
    run_forever()
