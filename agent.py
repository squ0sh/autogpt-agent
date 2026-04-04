import os
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Global control flag
running = False

# Agent state
GOAL = ""
memory = []


def stop_agent():
    global running
    running = False


def chat(prompt):
    """Call OpenAI API"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a focused, concise AI agent."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def generate_plan():
    """Generate next step plan"""
    prompt = f"""
    Goal: {GOAL}

    Previous steps:
    {memory}

    Give the NEXT actionable step only.

    Rules:
    - Max 5 bullet points
    - Be concise
    - No repetition
    - Focus on execution
    """
    return chat(prompt)


def reflect(result):
    """Reflect on result"""
    prompt = f"""
    Goal: {GOAL}

    Latest result:
    {result}

    Give a short reflection:
    - What worked
    - What should happen next

    Keep it concise.
    """
    return chat(prompt)


def run_agent_stream(goal):
    """Main streaming agent loop"""
    global running, GOAL, memory

    running = True
    GOAL = goal
    memory = []

    yield "🎯 Starting goal...\n\n"

    for step in range(1, 6):
        if not running:
            yield "🛑 Agent stopped by user.\n"
            return

        yield f"\n🔹 Step {step}\n"

        # --- PLAN ---
        yield "⏳ Thinking...\n"
        try:
            plan = generate_plan()
        except Exception as e:
            yield f"❌ Error generating plan: {str(e)}\n"
            return

        yield f"\n📋 Plan:\n{plan}\n"

        # --- ACTION (simulated for now) ---
        result = f"Executed step {step} based on plan."
        yield f"\n⚙️ Result:\n{result}\n"

        # --- REFLECTION ---
        yield "🧠 Reflecting...\n"
        try:
            reflection = reflect(result)
        except Exception as e:
            yield f"❌ Error generating reflection: {str(e)}\n"
            return

        yield f"\n🧠 Reflection:\n{reflection}\n\n"

        # --- MEMORY ---
        memory.append({
            "step": step,
            "plan": plan,
            "result": result,
            "reflection": reflection
        })

    yield "✅ Goal complete.\n"
