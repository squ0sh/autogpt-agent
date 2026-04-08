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
        temperature=1.0,
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

Best Idea:
{BEST_IDEA}

Step: {step_number}

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

They must contradict each other.
""", 700)


# -----------------------
# 🪓 ELIMINATION
# -----------------------
def eliminate(ideas_text):
    return chat(f"""
Goal:
{GOAL}

Ideas:
{ideas_text}

Choose ONE idea to eliminate permanently.
Explain why it fails.
""", 400)


# -----------------------
# 💀 DESTRUCTION
# -----------------------
def destroy(insight):
    return chat(f"""
Idea:
{insight}

Destroy this idea.

- biggest flaw
- how it breaks
- how to falsify
""", 500)


# -----------------------
# 🔁 REFINE
# -----------------------
def refine(insight, critique):
    return chat(f"""
Idea:
{insight}

Critique:
{critique}

Make it stronger.
""", 500)


# -----------------------
# 🧬 FORCE NOVELTY (NEW)
# -----------------------
def force_novelty(insight):
    return chat(f"""
Goal:
{GOAL}

Idea:
{insight}

Transform this into something TRULY NEW.

Rules:
- Must NOT resemble existing frameworks
- Introduce a new mechanism
- Should feel unfamiliar or uncomfortable

Do NOT refine — mutate it.
""", 700)


# -----------------------
# 🧪 REALITY TEST (NEW)
# -----------------------
def reality_test(insight):
    return chat(f"""
Idea:
{insight}

Test it:

- What would this look like in reality?
- What proves it?
- What disproves it?
""", 500)


# -----------------------
# 🧬 MUTATION
# -----------------------
def mutate(insight):
    return chat(f"""
Idea:
{insight}

Create a surprising variation.
""", 400)


# -----------------------
# 🧪 HYPOTHESIS
# -----------------------
def hypothesis(insight):
    return chat(f"""
Idea:
{insight}

Make testable:

- prediction
- method
""", 500)


# -----------------------
# 📊 SCORE
# -----------------------
def score(insight):
    return chat(f"""
Score 1-10:

Novelty:
Usefulness:
Plausibility:

Idea:
{insight}
""", 200)


# -----------------------
# 🏆 SELECTION (UPGRADED)
# -----------------------
def select_best(current, new):
    return chat(f"""
Choose ONE:

Current:
{current}

New:
{new}

Criteria priority:
1. Novelty
2. Transformative potential
3. Depth

Reject safe or familiar ideas.

Return ONLY winner.
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

Produce a breakthrough synthesis including:

- evolution of ideas
- contradictions
- paradigm shifts
- final theory
""", 1500)


# -----------------------
# 🚀 MAIN LOOP
# -----------------------
def run_agent_stream(goal, max_steps=8):
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

        # 🧠 PLAN
        plan = generate_plan()
        yield f"event: plan\ndata: {safe(plan)}\n\n"

        # 🎯 ACTION
        action = decide_action(plan)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        # 🛠 EXECUTE
        result = execute_action(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        # 🔍 SYNTHESIS
        insight = synthesize(result)
        yield f"event: insight\ndata: {safe(insight)}\n\n"

        # ⚔️ DIVERGENCE
        divergence = divergent_ideas(insight)
        yield f"event: divergence\ndata: {safe(divergence)}\n\n"

        # 🪓 ELIMINATION
        eliminated = eliminate(divergence)
        yield f"event: eliminated\ndata: {safe(eliminated)}\n\n"

        # 💀 DESTRUCTION
        critique = destroy(insight)
        yield f"event: critique\ndata: {safe(critique)}\n\n"

        # 🔁 REFINE
        refined = refine(insight, critique)
        yield f"event: refined\ndata: {safe(refined)}\n\n"

        # 🧬 FORCE NOVELTY
        novel = force_novelty(refined)
        yield f"event: novel\ndata: {safe(novel)}\n\n"

        # 🧪 REALITY TEST
        tested = reality_test(novel)
        yield f"event: test\ndata: {safe(tested)}\n\n"

        # 🧬 MUTATE
        mutation = mutate(novel)
        yield f"event: mutation\ndata: {safe(mutation)}\n\n"

        # 🧪 HYPOTHESIS
        hypo = hypothesis(novel)
        yield f"event: hypothesis\ndata: {safe(hypo)}\n\n"

        # 📊 SCORE
        scoring = score(novel)
        yield f"event: score\ndata: {safe(scoring)}\n\n"

        # 🏆 SURVIVAL
        if BEST_IDEA is None:
            BEST_IDEA = novel
        else:
            BEST_IDEA = select_best(BEST_IDEA, novel)

        yield f"event: best\ndata: {safe(BEST_IDEA)}\n\n"

        # 🧠 PARADIGM SHIFT (EVERY 3 STEPS)
        if step % 3 == 0 and step != 0:
            paradigm = chat(f"""
Goal:
{GOAL}

All previous thinking:
{memory}

Abandon everything.

Generate a radically different direction.
""", 700)

            yield f"event: paradigm_shift\ndata: {safe(paradigm)}\n\n"

        # 💾 MEMORY
        memory.append({
            "step": step + 1,
            "plan": plan,
            "insight": insight,
            "novel": novel,
            "test": tested,
            "best": BEST_IDEA
        })

        save_memory()
        time.sleep(0.3)

    # 🧠 FINAL
    final = final_report()

    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: complete\n\n"
