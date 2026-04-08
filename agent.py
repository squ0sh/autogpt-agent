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
BEST_IDEA = None

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
        temperature=0.85,
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

Best Idea So Far:
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

Extract deep patterns and generate ONE insight.
Stay strictly aligned to the goal.
""", 600)


# -----------------------
# ⚔️ DIVERGENCE ENGINE 🔥
# -----------------------
def divergent_ideas(insight):
    return chat(f"""
Goal:
{GOAL}

Base Idea:
{insight}

Generate 3 COMPLETELY DIFFERENT interpretations.

Rules:
- Different paradigms
- Challenge each other
- Not minor variations

Format:
Idea 1:
Idea 2:
Idea 3:
""", 700)


# -----------------------
# 💀 DESTRUCTION (UPGRADED)
# -----------------------
def destroy(insight):
    return chat(f"""
Goal:
{GOAL}

Idea:
{insight}

Attack this idea HARD.

- What would disprove it?
- Where does it break?
- What assumptions are weak?

Be ruthless.
""", 500)


# -----------------------
# 🔁 REFINE
# -----------------------
def refine(insight, critique):
    return chat(f"""
Goal:
{GOAL}

Original Idea:
{insight}

Critique:
{critique}

Refine into a stronger version.
""", 500)


# -----------------------
# 🧬 MUTATION
# -----------------------
def mutate(insight):
    return chat(f"""
Goal:
{GOAL}

Idea:
{insight}

Create a surprising alternative interpretation.
""", 400)


# -----------------------
# 🧪 HYPOTHESIS
# -----------------------
def hypothesis(insight):
    return chat(f"""
Goal:
{GOAL}

Idea:
{insight}

Turn into a testable hypothesis.

Include:
- prediction
- method
""", 500)


# -----------------------
# 📊 SCORING
# -----------------------
def score(insight):
    return chat(f"""
Goal:
{GOAL}

Score (1-10):

Novelty:
Usefulness:
Plausibility:

Idea:
{insight}
""", 200)


# -----------------------
# 🏆 SELECT BEST IDEA
# -----------------------
def select_best(current, new):
    return chat(f"""
Goal:
{GOAL}

Current Best:
{current}

New Candidate:
{new}

Which is better and why?

Return ONLY the better idea.
""", 300)


# -----------------------
# 🧠 FINAL REPORT
# -----------------------
def final_report():
    return chat(f"""
Goal:
{GOAL}

All Steps:
{memory}

Best Idea:
{BEST_IDEA}

Create a breakthrough-level synthesis.

Include:
- evolution of ideas
- competing models
- failures
- final refined theory
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

        divergence = divergent_ideas(insight)
        yield f"event: divergence\ndata: {safe(divergence)}\n\n"

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

        # 🏆 EVOLUTIONARY SELECTION
        if BEST_IDEA is None:
            BEST_IDEA = refined
        else:
            BEST_IDEA = select_best(BEST_IDEA, refined)

        yield f"event: best\ndata: {safe(BEST_IDEA)}\n\n"

        memory.append({
            "step": step + 1,
            "plan": plan,
            "insight": insight,
            "divergence": divergence,
            "critique": critique,
            "refined": refined,
            "mutation": mutation,
            "hypothesis": hypo,
            "score": scoring,
            "best": BEST_IDEA
        })

        save_memory()

        time.sleep(0.3)

    final = final_report()

    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: complete\n\n"
