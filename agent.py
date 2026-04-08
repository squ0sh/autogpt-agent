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
# 🛑 STOP
# -----------------------
def stop():
    global STOP_FLAG
    STOP_FLAG = True


# -----------------------
# 💾 MEMORY
# -----------------------
def save_memory():
    data = {}
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
        except:
            data = {}

    data[RUN_ID] = {"goal": GOAL, "steps": memory}

    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


# -----------------------
# ⚡ SAFE STREAM
# -----------------------
def safe(text):
    return str(text).replace("\n", "\\n")


# -----------------------
# 🧠 CORE CHAT
# -----------------------
def chat(prompt, max_tokens=1200):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=max_tokens,
    )
    return res.choices[0].message.content.strip()


# -----------------------
# 🧠 PLAN
# -----------------------
def generate_plan():
    step_number = len(memory) + 1

    return chat(f"""
Goal:
{GOAL}

Step {step_number}

Create ONE step that pushes toward new insight.
Avoid repetition.
""", 500)


# -----------------------
# 🎯 ACTION
# -----------------------
def decide_action(plan):
    try:
        return json.loads(chat(f"""
Plan:
{plan}

Choose:
search | analyze | write

Return JSON
""", 200))
    except:
        return {"action": "analyze", "input": "continue reasoning"}


# -----------------------
# 🛠 EXECUTE
# -----------------------
def execute_action(action):
    from tools import run_tool
    try:
        return run_tool(action)
    except Exception as e:
        return str(e)


# -----------------------
# 🔍 SYNTHESIS
# -----------------------
def synthesize(result):
    return chat(f"""
Extract deep patterns + generate ONE strong insight:

{result}
""", 600)


# -----------------------
# ⚔️ COMPETING MODELS
# -----------------------
def competing_models(insight):
    return chat(f"""
Create TWO competing explanations:

Insight:
{insight}

Model A:
Model B:

Which is better and why?
""", 600)


# -----------------------
# 💀 DESTRUCTION
# -----------------------
def destroy(insight):
    return chat(f"""
Destroy this idea completely:

{insight}

Why is it wrong?
""", 400)


# -----------------------
# 🔁 REFINE
# -----------------------
def refine(insight, critique):
    return chat(f"""
Original Idea:
{insight}

Critique:
{critique}

Refine into a stronger idea.
""", 500)


# -----------------------
# 🧬 MUTATION
# -----------------------
def mutate(insight):
    return chat(f"""
Generate a surprising or unconventional variation of this idea:

{insight}
""", 400)


# -----------------------
# 🧪 HYPOTHESIS
# -----------------------
def hypothesis(insight):
    return chat(f"""
Turn this into a testable hypothesis:

{insight}

Include:
- prediction
- test method
""", 500)


# -----------------------
# 📊 SCORE
# -----------------------
def score(insight):
    return chat(f"""
Score 1-10:

Novelty:
Usefulness:
Confidence:

{insight}
""", 200)


# -----------------------
# 🧠 GOAL CHECK
# -----------------------
def done():
    return "yes" in chat(f"""
Goal:
{GOAL}

Steps:
{memory}

Done?
""", 10).lower()


# -----------------------
# 🧠 FINAL
# -----------------------
def final_report():
    return chat(f"""
Create a breakthrough-level synthesis:

{memory}

Include:
- best idea
- rejected ideas
- strongest hypothesis
""", 1500)


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

    for step in range(max_steps):

        if STOP_FLAG:
            yield "event: stopped\ndata: stopped\n\n"
            return

        yield f"event: step\ndata: {step+1}\n\n"

        plan = generate_plan()
        yield f"event: plan\ndata: {safe(plan)}\n\n"

        action = decide_action(plan)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        result = execute_action(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        insight = synthesize(result)
        yield f"event: insight\ndata: {safe(insight)}\n\n"

        models = competing_models(insight)
        yield f"event: models\ndata: {safe(models)}\n\n"

        critique = destroy(insight)
        yield f"event: critique\ndata: {safe(critique)}\n\n"

        refined = refine(insight, critique)
        yield f"event: refined\ndata: {safe(refined)}\n\n"

        mutation = mutate(refined)
        yield f"event: mutation\ndata: {safe(mutation)}\n\n"

        hypo = hypothesis(refined)
        yield f"event: hypothesis\ndata: {safe(hypo)}\n\n"

        scoring = score(refined)
        yield f"event: score\ndata: {safe(scoring)}\n\n"

        memory.append({
            "step": step + 1,
            "insight": insight,
            "models": models,
            "critique": critique,
            "refined": refined,
            "mutation": mutation,
            "hypothesis": hypo,
            "score": scoring
        })

        save_memory()

        if done():
            break

        time.sleep(0.3)

    final = final_report()

    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: complete\n\n"
