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


def chat(prompt, max_tokens=1200):
    messages = [{"role": "user", "content": prompt}]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.5,
        max_tokens=max_tokens,
    )

    output = response.choices[0].message.content.strip()

    if response.choices[0].finish_reason == "length":
        messages.append({"role": "assistant", "content": output})
        messages.append({
            "role": "user",
            "content": "Continue exactly where you left off."
        })

        continuation = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.5,
            max_tokens=max_tokens,
        )

        output += "\n" + continuation.choices[0].message.content.strip()

    return output


# -----------------------
# 🧠 PLAN
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    prompt = f"""
You are an execution agent.

Goal:
{GOAL}

Previous:
{memory}

Step: {step_number}

CRITICAL:
- Do NOT claim actions are completed unless tools executed them
- Stay grounded in reality

FORMAT:
Step {step_number}: <title>

- action 1
- action 2
- action 3
"""
    return chat(prompt, 800)


# -----------------------
# 🎯 ACTION
# -----------------------
def decide_action(plan):
    prompt = f"""
Plan:
{plan}

Choose ONE:

- write
- analyze
- search
- scrape
- research
- save_file
- save_structured

Rules:

- Use "research" for trends, competitors, decisions
- research = search + scrape

- If URL → scrape
- Prefer real data over assumptions

Return JSON:
{{
 "action": "...",
 "input": "..."
}}
"""

    try:
        decision = json.loads(chat(prompt, 400))
    except:
        decision = {"action": "write", "input": "continue"}

    if "http" in str(decision.get("input")):
        decision["action"] = "scrape"

    return decision


# -----------------------
# 🛠 EXECUTE
# -----------------------
def execute_action(action):
    from tools import run_tool

    try:
        result = run_tool(action)
    except Exception as e:
        result = f"Tool error: {str(e)}"

    return result


# -----------------------
# 🔍 REFLECT (REAL DATA)
# -----------------------
def reflect(result):
    prompt = f"""
Goal:
{GOAL}

Result:
{result}

Analyze REAL data only.

FORMAT:

Evaluation:
<what actually happened>

Insights:
- insight 1
- insight 2
- insight 3

Next:
<real next step>
"""
    return chat(prompt, 800)


# -----------------------
# 🧠 LOOP
# -----------------------
def run_agent_stream(goal, max_steps=6):
    global GOAL, memory, RUN_ID

    GOAL = goal
    memory = []
    RUN_ID = str(uuid.uuid4())

    yield f"event: start\ndata: {goal}\n\n"

    for step in range(max_steps):
        yield f"event: step\ndata: {step+1}\n\n"

        plan = generate_plan()
        yield f"event: plan\ndata: {plan}\n\n"

        action = decide_action(plan)
        yield f"event: action\ndata: {json.dumps(action)}\n\n"

        result = execute_action(action)
        yield f"event: result\ndata: {str(result)}\n\n"

        reflection = reflect(result)
        yield f"event: reflection\ndata: {reflection}\n\n"

        memory.append({
            "step": step + 1,
            "plan": plan,
            "action": action,
            "result": result,
            "reflection": reflection
        })

        save_memory()
        time.sleep(0.3)

    yield f"event: done\ndata: complete\n\n"

