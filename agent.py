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
RUNNING = False  # 🔒 LOCK

MEMORY_FILE = "memory.json"


# -----------------------
# 🛑 STOP
# -----------------------
def stop():
    global STOP_FLAG, RUNNING
    STOP_FLAG = True
    RUNNING = False


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
# 🧠 PLAN
# -----------------------
def generate_plan():
    return chat(f"""
Goal:
{GOAL}

Best Idea So Far:
{BEST_IDEA}

Generate ONE step that pushes deeper understanding.
Avoid repetition.
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
# ⚔️ DEBATE
# -----------------------
def debate(ideas):
    return chat(f"""
Goal:
{GOAL}

Ideas:
{ideas}

Force direct attacks between ideas.
No soft language. No resolution.
""", 700)


# -----------------------
# 🪓 ELIMINATION
# -----------------------
def eliminate(ideas):
    return chat(f"""
Goal:
{GOAL}

Ideas:
{ideas}

Eliminate ONE idea permanently.
It cannot return.
""", 400)


# -----------------------
# 🧠 DIALOGUE
# -----------------------
def dialogue(ideas):
    return chat(f"""
Goal:
{GOAL}

Ideas:
{ideas}

Now allow dialogue.

- Extract truth from each
- Do NOT merge
- Do NOT erase differences
""", 700)


# -----------------------
# 💀 DESTRUCTION
# -----------------------
def destroy(insight):
    return chat(f"""
Goal:
{GOAL}

Idea:
{insight}

Find fatal flaw and how to break it.
""", 500)


# -----------------------
# 🔁 REFINE
# -----------------------
def refine(insight, critique):
    return chat(f"""
Improve this idea using the critique:

Idea:
{insight}

Critique:
{critique}
""", 500)


# -----------------------
# 🧬 MUTATION
# -----------------------
def mutate(insight):
    return chat(f"""
Create a surprising variation of:

{insight}
""", 400)


# -----------------------
# 🧪 HYPOTHESIS
# -----------------------
def hypothesis(insight):
    return chat(f"""
Turn into testable hypothesis:

{insight}
""", 500)


# -----------------------
# 📊 SCORE
# -----------------------
def score(insight):
    return chat(f"""
Score 1–10:

Novelty
Usefulness
Plausibility

{insight}
""", 200)


# -----------------------
# 🏆 DOMINANCE
# -----------------------
def enforce_dominance(current, new):
    return chat(f"""
ONLY ONE survives:

Current:
{current}

New:
{new}

Return winner only.
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

Respect eliminations.

Provide:
- competing ideas
- eliminated ideas
- debate highlights
- dominant theory
- final model
""", 1500)


# -----------------------
# 🚀 MAIN LOOP
# -----------------------
def run_agent_stream(goal, max_steps=7):
    global GOAL, memory, RUN_ID, STOP_FLAG, BEST_IDEA, RUNNING

    # 🔒 PREVENT DOUBLE RUN
    if RUNNING:
        yield "event: error\ndata: Agent already running\n\n"
        return

    RUNNING = True
    print(f"RUN STARTED: {goal}")

    GOAL = goal
    memory = []
    STOP_FLAG = False
    RUN_ID = str(uuid.uuid4())
    BEST_IDEA = None

    try:
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

            divergence = divergent_ideas(insight)
            yield f"event: divergence\ndata: {safe(divergence)}\n\n"

            debate_result = debate(divergence)
            yield f"event: debate\ndata: {safe(debate_result)}\n\n"

            eliminated = eliminate(divergence)
            yield f"event: eliminated\ndata: {safe(eliminated)}\n\n"

            dialogue_result = dialogue(divergence)
            yield f"event: dialogue\ndata: {safe(dialogue_result)}\n\n"

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

            if BEST_IDEA is None:
                BEST_IDEA = refined
            else:
                BEST_IDEA = enforce_dominance(BEST_IDEA, refined)

            yield f"event: best\ndata: {safe(BEST_IDEA)}\n\n"

            memory.append({
                "step": step + 1,
                "plan": plan,
                "insight": insight,
                "divergence": divergence,
                "debate": debate_result,
                "eliminated": eliminated,
                "dialogue": dialogue_result,
                "critique": critique,
                "refined": refined,
                "best": BEST_IDEA
            })

            save_memory()
            time.sleep(0.3)

        final = final_report()
        yield f"event: final\ndata: {safe(final)}\n\n"
        yield f"event: done\ndata: complete\n\n"

    finally:
        # 🔓 ALWAYS RELEASE LOCK
        RUNNING = False
        print("RUN ENDED")
