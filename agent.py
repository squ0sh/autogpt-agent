import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

running = False

GOAL = ""
memory = []


def stop_agent():
    global running
    running = False


def chat(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def generate_plan():
    prompt = f"""
    Goal: {GOAL}

    Previous memory:
    {memory}

    Give the NEXT step only.

    Rules:
    - Max 5 bullet points
    - No repetition
    - Be concise
    """
    return chat(prompt)


def reflect(result):
    prompt = f"""
    Goal: {GOAL}

    Result:
    {result}

    Give short reflection:
    - What worked
    - What next
    """
    return chat(prompt)


def run_agent_stream(goal):
    global running, GOAL, memory

    running = True
    GOAL = goal
    memory = []

    yield "🎯 Starting goal...\n\n"

    for step in range(1, 6):
        if not running:
            yield "🛑 Agent stopped.\n"
            return

        yield f"🔹 Step {step}\n"

        # PLAN
        plan = generate_plan()
        yield f"\n📋 Plan:\n{plan}\n"

        # ACTION (simulated for now)
        result = f"Executed step {step} based on plan"
        yield f"\n⚙️ Result:\n{result}\n"

        # REFLECTION
        reflection = reflect(result)
        yield f"\n🧠 Reflection:\n{reflection}\n\n"

        memory.append({
            "step": step,
            "plan": plan,
            "result": result,
            "reflection": reflection
        })

    yield "✅ Goal complete.\n"
