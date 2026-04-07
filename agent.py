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


# -----------------------
# 🛑 STOP FUNCTION (FIXED)
# -----------------------
def stop():
    global STOP_FLAG
    STOP_FLAG = True


# -----------------------
# ⚡ STREAM SAFE
# -----------------------
def safe(text):
    return str(text).replace("\n", "\\n")


# -----------------------
# 🧠 CORE CHAT
# -----------------------
def chat(prompt, max_tokens=1200):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


# -----------------------
# 🧠 STEP GENERATION
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    prompt = f"""
You are a high-level research agent.

Goal:
{GOAL}

Previous steps:
{memory}

Current step: {step_number}

RULES:
- ONLY generate ONE step
- Push toward NEW INSIGHT
- Avoid repetition

FORMAT:
Step {step_number}: <title>

- action 1
- action 2
- action 3
"""

    return chat(prompt, 600)


# -----------------------
# 🎯 ACTION SELECTION
# -----------------------
def decide_action(plan):
    prompt = f"""
Plan:
{plan}

Choose ONE action:
- search
- analyze
- write

Return JSON:
{{"action": "...", "input": "..."}}
"""

    try:
        return json.loads(chat(prompt, 300))
    except:
        return {"action": "analyze", "input": "continue reasoning"}


# -----------------------
# 🛠 TOOL EXECUTION
# -----------------------
def execute_action(action):
    try:
        from tools import run_tool
        result = run_tool(action)
    except Exception as e:
        result = f"Tool error: {str(e)}"

    return result


# -----------------------
# 🔍 SYNTHESIS
# -----------------------
def synthesize(result):
    prompt = f"""
Goal:
{GOAL}

New Information:
{result}

Extract:

1. Key Patterns
2. Hidden Connections
3. New Insight (must be original)
"""
    return chat(prompt, 700)


# -----------------------
# ⚔️ CRITIQUE
# -----------------------
def critique(insight):
    prompt = f"""
Critically analyze this:

{insight}

Return:

Weaknesses:
- ...

Contradictions:
- ...

What might be wrong:
- ...
"""
    return chat(prompt, 600)


# -----------------------
# 🧪 HYPOTHESIS
# -----------------------
def generate_hypothesis(insight):
    prompt = f"""
From this idea:

{insight}

Generate a TESTABLE hypothesis.

Format:
Hypothesis:
Prediction:
How to test:
"""
    return chat(prompt, 600)


# -----------------------
# 📊 SCORING
# -----------------------
def score(insight):
    prompt = f"""
Score this idea (1-10):

{insight}

Return:

Novelty:
Usefulness:
Confidence:
"""
    return chat(prompt, 300)


# -----------------------
# 🧠 GOAL CHECK
# -----------------------
def is_goal_complete():
    prompt = f"""
Goal:
{GOAL}

Steps:
{memory}

Has the goal been FULLY achieved?

Return ONLY:
YES or NO
"""
    result = chat(prompt, 10).lower()
    return "yes" in result


# -----------------------
# 🧠 FINAL OUTPUT
# -----------------------
def generate_final():
    compiled = ""

    for step in memory:
        compiled += f"""
Step {step['step']}

Insight:
{step['insight']}

Critique:
{step['critique']}

Hypothesis:
{step['hypothesis']}

Score:
{step['score']}

---
"""

    prompt = f"""
Create a FINAL SYNTHESIS REPORT.

Goal:
{GOAL}

Data:
{compiled}

Include:
- Core Patterns
- Contradictions
- Breakthrough Ideas
- Best Hypothesis
"""
    return chat(prompt, 1500)


# -----------------------
# 🚀 MAIN LOOP
# -----------------------
def run_agent_stream(goal, max_steps=6):
    global GOAL, memory, RUN_ID, STOP_FLAG

    GOAL = goal
    memory = []
    STOP_FLAG = False
    RUN_ID = str(uuid.uuid4())

    yield f"event: start\ndata: {safe(goal)}\n\n"

    step = 0

    while step < max_steps:

        # 🛑 STOP CHECK (FIXED)
        if STOP_FLAG:
            yield f"event: stopped\ndata: stopped by user\n\n"
            return

        yield f"event: step\ndata: {step+1}\n\n"

        plan = generate_plan()
        yield f"event: plan\ndata: {safe(plan)}\n\n"

        action = decide_action(plan)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        result = execute_action(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        # 🔥 BREAKTHROUGH PIPELINE
        insight = synthesize(result)
        yield f"event: insight\ndata: {safe(insight)}\n\n"

        critique_text = critique(insight)
        yield f"event: critique\ndata: {safe(critique_text)}\n\n"

        hypothesis = generate_hypothesis(insight)
        yield f"event: hypothesis\ndata: {safe(hypothesis)}\n\n"

        score_text = score(insight)
        yield f"event: score\ndata: {safe(score_text)}\n\n"

        memory.append({
            "step": step + 1,
            "plan": plan,
            "action": action,
            "result": result,
            "insight": insight,
            "critique": critique_text,
            "hypothesis": hypothesis,
            "score": score_text
        })

        save_memory()

        if is_goal_complete():
            break

        step += 1
        time.sleep(0.3)

    final = generate_final()

    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: complete\n\n"
