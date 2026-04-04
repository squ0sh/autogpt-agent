import os
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
        messages=[
            {"role": "system", "content": "You are a focused, concise AI agent."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def generate_plan():
    prompt = f"""
    Goal: {GOAL}

    Previous steps:
    {memory}

    Give the NEXT actionable step only.

    Rules:
    - Max 5 bullet points
    - No repetition
    - Be concise
    """
    return chat(prompt)


def reflect(result):
    prompt = f"""
    Goal: {GOAL}

    Latest result:
    {result}

    Give a short reflection:
    - What worked
    - What to do next
    """
    return chat(prompt)


def run_agent_stream(goal):
    global running, GOAL, memory

    running = True
    GOAL = goal
    memory = []

    yield "event: start\ndata: Starting goal...\n\n"

    for step in range(1, 6):
        if not running:
            yield "event: stop\ndata: Agent stopped\n\n"
            return

        # STEP HEADER
        yield f"event: step\ndata: {step}\n\n"

        # PLAN
        yield "event: status\ndata: Thinking...\n\n"
        try:
            plan = generate_plan()
        except Exception as e:
            yield f"event: error\ndata: Plan error: {str(e)}\n\n"
            return

        yield f"event: plan\ndata: {plan}\n\n"

        # RESULT
        result = f"Executed step {step} based on plan"
        yield f"event: result\ndata: {result}\n\n"

        # REFLECTION
        yield "event: status\ndata: Reflecting...\n\n"
        try:
            reflection = reflect(result)
        except Exception as e:
            yield f"event: error\ndata: Reflection error: {str(e)}\n\n"
            return

        yield f"event: reflection\ndata: {reflection}\n\n"

        # MEMORY
        memory.append({
            "step": step,
            "plan": plan,
            "result": result,
            "reflection": reflection
        })

    yield "event: done\ndata: Goal complete\n\n"
