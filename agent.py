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
BEST_IDEA = None

MEMORY_FILE = "memory.json"
MIN_STEPS = 5


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
# 💾 MEMORY SAVE
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

    if BEST_IDEA:
        data["evolution"]["survivors"].append(BEST_IDEA)

    data[RUN_ID] = {
        "goal": GOAL,
        "steps": memory,
        "best_idea": BEST_IDEA
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
# 🧠 PLAN (WITH EVOLUTION)
# -----------------------
def generate_plan():
    step_number = len(memory) + 1
    survivors, failures = load_evolution()

    return chat(f"""
Goal:
{GOAL}

Best Idea So Far:
{BEST_IDEA}

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

Extract ONE deep insight aligned to the goal.
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

Generate 3 IDEAS that are MUTUALLY EXCLUSIVE.

- If one is true → others must fail
- Each challenges different assumptions
""", 700)


# -----------------------
# 💀 DESTROY EACH IDEA
# -----------------------
def destroy_each(ideas):
    return chat(f"""
Goal:
{GOAL}

Ideas:
{ideas}

Destroy EACH idea:

- fatal flaw
- how it fails
- how to falsify

Be aggressive.
""", 700)


# -----------------------
# 🪓 ELIMINATE
# -----------------------
def eliminate(ideas):
    return chat(f"""
Goal:
{GOAL}

Ideas:
{ideas}

Eliminate ONE idea permanently.

Rules:
- weakest must die
- cannot return later

Return:
Eliminated:
Reason:
""", 400)


# -----------------------
# 🧠 SELECT SURVIVOR
# -----------------------
def select_survivor(ideas, critique):
    return chat(f"""
Goal:
{GOAL}

Ideas:
{ideas}

Critique:
{critique}

ONLY ONE survives.

Return ONLY that idea.
""", 400)


# -----------------------
# 🔁 REFINE
# -----------------------
def refine(idea, critique):
    return chat(f"""
Improve ONLY this idea:

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
# 🧬 NOVELTY BOOST
# -----------------------
def novelty_boost(idea):
    return chat(f"""
Goal:
{GOAL}

Idea:
{idea}

Increase novelty:

- challenge assumptions
- introduce unconventional thinking
- keep it meaningful

Return improved idea.
""", 500)


# -----------------------
# 🧪 HYPOTHESIS
# -----------------------
def hypothesis(idea):
    return chat(f"""
Turn into testable hypothesis:

{idea}

Include:
- prediction
- method
""", 500)


# -----------------------
# 📊 SCORE
# -----------------------
def score(idea):
    return chat(f"""
Score (1-10):

Novelty:
Usefulness:
Plausibility:

IMPORTANT:
- Low novelty = weak idea

Idea:
{idea}
""", 200)


# -----------------------
# 🏆 SELECT BEST
# -----------------------
def select_best(current, new):
    return chat(f"""
Current:
{current}

New:
{new}

Only ONE survives.

Choose the stronger idea.
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

Best Idea:
{BEST_IDEA}

Provide:
- competing ideas
- eliminations
- evolution path
- final dominant theory
""", 1500)


# -----------------------
# 🚀 MAIN LOOP
# -----------------------
def run_agent_stream(goal, max_steps=7):
    global GOAL, memory, RUN_ID, STOP_FLAG, BEST_IDEA

    GOAL = goal
    memory = []
    STOP_FLAG = False
    RUN_ID = str(uuid.uuid4())
    BEST_IDEA = None

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

        # 🧬 NOVELTY INJECTION
        novel = novelty_boost(mutation)
        yield f"event: novelty\ndata: {safe(novel)}\n\n"

        hypo = hypothesis(novel)
        yield f"event: hypothesis\ndata: {safe(hypo)}\n\n"

        scoring = score(novel)
        yield f"event: score\ndata: {safe(scoring)}\n\n"

        if BEST_IDEA is None:
            BEST_IDEA = novel
        else:
            BEST_IDEA = select_best(BEST_IDEA, novel)

        yield f"event: best\ndata: {safe(BEST_IDEA)}\n\n"

        memory.append({
            "step": step + 1,
            "plan": plan,
            "insight": insight,
            "ideas": ideas,
            "eliminated": eliminated,
            "survivor": survivor,
            "refined": refined,
            "novel": novel,
            "score": scoring,
            "best": BEST_IDEA
        })

        save_memory()
        time.sleep(0.3)

    final = final_report()

    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: complete\n\n"
