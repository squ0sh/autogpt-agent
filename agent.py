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

# 🌌 Layered truth system
BEST_IDEAS = {
    "empirical": None,
    "experiential": None,
    "structural": None,
    "speculative": None
}


# -----------------------
# 🛑 STOP
# -----------------------
def stop():
    global STOP_FLAG
    STOP_FLAG = True


# -----------------------
# 🧬 LOAD EVOLUTION
# -----------------------
def load_evolution():
    if not os.path.exists(MEMORY_FILE):
        return [], []

    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)

        evo = data.get("evolution", {})
        return evo.get("survivors", []), evo.get("failures", [])
    except:
        return [], []


# -----------------------
# 💀 RECORD FAILURE
# -----------------------
def record_failure(text):
    data = {}

    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
        except:
            data = {}

    if "evolution" not in data:
        data["evolution"] = {"survivors": [], "failures": []}

    data["evolution"]["failures"].append(text)

    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


# -----------------------
# 💾 SAVE MEMORY
# -----------------------
def save_memory():
    data = {}

    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
        except:
            data = {}

    if "evolution" not in data:
        data["evolution"] = {"survivors": [], "failures": []}

    # Save all layer winners
    for idea in BEST_IDEAS.values():
        if idea:
            data["evolution"]["survivors"].append(idea)

    data[RUN_ID] = {
        "goal": GOAL,
        "steps": memory,
        "best_ideas": BEST_IDEAS
    }

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
        temperature=0.9,
        max_tokens=max_tokens,
    )
    return res.choices[0].message.content.strip()


# -----------------------
# 🧠 PLAN
# -----------------------
def generate_plan():
    survivors, failures = load_evolution()
    step_number = len(memory) + 1

    return chat(f"""
Goal:
{GOAL}

Past Winners:
{survivors[-3:]}

Past Failures:
{failures[-3:]}

Step: {step_number}

Generate ONE step that:
- builds on success
- avoids failure
- pushes deeper insight
""", 500)


# -----------------------
# 🎯 ACTION
# -----------------------
def decide_action(plan):
    try:
        return json.loads(chat(f"""
Goal:
{GOAL}

Plan:
{plan}

Choose ONE:
search | analyze | write

Return JSON:
{{"action": "...", "input": "..."}}
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
        return f"Tool error: {str(e)}"


# -----------------------
# 🔍 SYNTHESIS
# -----------------------
def synthesize(result):
    return chat(f"""
Goal:
{GOAL}

Result:
{result}

Extract ONE deep insight.
""", 600)


# -----------------------
# ⚔️ DIVERGENCE
# -----------------------
def divergent_ideas(insight):
    return chat(f"""
Goal:
{GOAL}

Base Idea:
{insight}

Generate 3 mutually exclusive ideas.
""", 700)


# -----------------------
# 💀 DESTROY
# -----------------------
def destroy_each(ideas):
    return chat(f"""
Destroy each idea:

{ideas}

Find fatal flaws.
""", 700)


# -----------------------
# 🪓 ELIMINATE (TRACK FAILURE ONLY)
# -----------------------
def eliminate(ideas):
    return chat(f"""
From these ideas:

{ideas}

Pick the weakest and explain why.
""", 400)


# -----------------------
# 🧠 SELECT SURVIVOR
# -----------------------
def select_survivor(ideas, critique):
    return chat(f"""
Ideas:
{ideas}

Critique:
{critique}

Select strongest idea.
""", 400)


# -----------------------
# 🔁 REFINE
# -----------------------
def refine(idea, critique):
    return chat(f"""
Improve this idea:

{idea}

Using critique:
{critique}
""", 500)


# -----------------------
# 🧬 MUTATE
# -----------------------
def mutate(idea):
    return chat(f"""
Create a stronger variation:

{idea}
""", 400)


# -----------------------
# 🧬 NOVELTY
# -----------------------
def novelty_boost(idea):
    return chat(f"""
Make this idea more novel:

{idea}

Keep it meaningful.
""", 500)


# -----------------------
# 🧠 CLASSIFY
# -----------------------
def classify_idea(idea):
    return chat(f"""
Classify into ONE:

- empirical
- experiential
- structural
- speculative

Idea:
{idea}

Return only category.
""", 50).lower().strip()


# -----------------------
# 🏆 SELECT BEST (PER LAYER)
# -----------------------
def select_best(current, new):
    return chat(f"""
Current:
{current}

New:
{new}

Choose stronger.
Return only winner.
""", 300)


# -----------------------
# 🧠 FINAL REPORT
# -----------------------
def final_report():
    return chat(f"""
Goal:
{GOAL}

Steps:
{memory}

Layered Ideas:
{BEST_IDEAS}

Create a layered reality model.

Include:
- each layer’s best idea
- interactions between layers
- tensions
- paradoxes

DO NOT unify into one answer.
""", 1500)


# -----------------------
# 🚀 MAIN LOOP
# -----------------------
def run_agent_stream(goal, max_steps=7):
    global GOAL, memory, RUN_ID, STOP_FLAG, BEST_IDEAS

    GOAL = goal
    memory = []
    STOP_FLAG = False
    RUN_ID = str(uuid.uuid4())

    BEST_IDEAS = {
        "empirical": None,
        "experiential": None,
        "structural": None,
        "speculative": None
    }

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

        ideas = divergent_ideas(insight)
        yield f"event: divergence\ndata: {safe(ideas)}\n\n"

        destruction = destroy_each(ideas)
        yield f"event: destruction\ndata: {safe(destruction)}\n\n"

        eliminated = eliminate(ideas)
        yield f"event: eliminated\ndata: {safe(eliminated)}\n\n"

        record_failure(eliminated)

        survivor = select_survivor(ideas, destruction)
        yield f"event: survivor\ndata: {safe(survivor)}\n\n"

        refined = refine(survivor, destruction)
        yield f"event: refined\ndata: {safe(refined)}\n\n"

        mutation = mutate(refined)
        yield f"event: mutation\ndata: {safe(mutation)}\n\n"

        novel = novelty_boost(mutation)
        yield f"event: novelty\ndata: {safe(novel)}\n\n"

        category = classify_idea(novel)
        yield f"event: category\ndata: {safe(category)}\n\n"

        current = BEST_IDEAS.get(category)

        if current is None:
            BEST_IDEAS[category] = novel
        else:
            BEST_IDEAS[category] = select_best(current, novel)

        yield f"event: best_{category}\ndata: {safe(BEST_IDEAS[category])}\n\n"

        memory.append({
            "step": step + 1,
            "plan": plan,
            "insight": insight,
            "ideas": ideas,
            "survivor": survivor,
            "novel": novel,
            "category": category,
            "layer_state": BEST_IDEAS
        })

        save_memory()
        time.sleep(0.3)

    final = final_report()

    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: complete\n\n"
