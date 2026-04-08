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
        temperature=0.9,
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

Rules:
- They cannot all be true simultaneously
- Each must contradict a core assumption of the others

Format:

Idea A:
...

Idea B:
...

Idea C:
...
""", 700)


# -----------------------
# ⚔️ HARD DEBATE
# -----------------------
def debate(ideas_text):
    return chat(f"""
Goal:
{GOAL}

Ideas:
{ideas_text}

Force a DIRECT debate.

Rules:
- Each idea attacks the others
- Identify contradictions clearly
- No soft language
- Do NOT resolve

Format:

Attack 1:
...

Attack 2:
...

Attack 3:
...
""", 700)


# -----------------------
# 🪓 IRREVERSIBLE ELIMINATION
# -----------------------
def eliminate(ideas_text):
    return chat(f"""
Goal:
{GOAL}

Ideas:
{ideas_text}

Choose ONE idea to eliminate permanently.

Rules:
- It is removed forever
- It MUST NOT appear again
- Be decisive

Return:

Eliminated Idea:
Reason:
""", 400)


# -----------------------
# 🧠 DIALOGUE
# -----------------------
def dialogue(ideas_text):
    return chat(f"""
Goal:
{GOAL}

Ideas:
{ideas_text}

Now shift into dialogue.

Rules:
- Each idea tries to understand the others
- Extract what might be TRUE in each
- Do NOT merge
- Do NOT erase differences

Focus:
- translation between perspectives
- shared patterns

Output:
Refined perspectives after dialogue
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

Destroy this idea.

- Identify fatal flaw
- Show how it breaks
- Explain falsification

Be decisive.
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

Strengthen the idea.
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

Create a surprising variation.
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

Make it testable.

Include:
- prediction
- method
""", 500)


# -----------------------
# 📊 SCORE
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
# 🏆 DOMINANCE
# -----------------------
def enforce_dominance(current, new):
    return chat(f"""
Goal:
{GOAL}

Current Dominant:
{current}

Challenger:
{new}

ONLY ONE survives.

- No compromise
- No blending

Return ONLY the winner.
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

Constraints:
- Respect eliminations (no revival)
- Identify dominant idea
- Show unresolved conflicts

Produce:

1. Competing ideas
2. Eliminated ideas
3. Debate highlights
4. Dialogue insights
5. Dominant theory (clear winner)
6. Final integrated model (based on dominance only)
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

        # PLAN
        plan = generate_plan()
        yield f"event: plan\ndata: {safe(plan)}\n\n"

        # ACTION
        action = decide_action(plan)
        yield f"event: action\ndata: {safe(json.dumps(action))}\n\n"

        # EXECUTE
        result = execute_action(action)
        yield f"event: result\ndata: {safe(result)}\n\n"

        # SYNTHESIS
        insight = synthesize(result)
        yield f"event: insight\ndata: {safe(insight)}\n\n"

        # ⚔️ DIVERGENCE
        divergence = divergent_ideas(insight)
        yield f"event: divergence\ndata: {safe(divergence)}\n\n"

        # ⚔️ DEBATE
        debate_result = debate(divergence)
        yield f"event: debate\ndata: {safe(debate_result)}\n\n"

        # 🪓 ELIMINATION
        eliminated = eliminate(divergence)
        yield f"event: eliminated\ndata: {safe(eliminated)}\n\n"

        # 🧠 DIALOGUE
        dialogue_result = dialogue(divergence)
        yield f"event: dialogue\ndata: {safe(dialogue_result)}\n\n"

        # 💀 DESTRUCTION
        critique = destroy(insight)
        yield f"event: critique\ndata: {safe(critique)}\n\n"

        # 🔁 REFINE
        refined = refine(insight, critique)
        yield f"event: refined\ndata: {safe(refined)}\n\n"

        # 🧬 MUTATION
        mutation = mutate(refined)
        yield f"event: mutation\ndata: {safe(mutation)}\n\n"

        # 🧪 HYPOTHESIS
        hypo = hypothesis(refined)
        yield f"event: hypothesis\ndata: {safe(hypo)}\n\n"

        # 📊 SCORE
        scoring = score(refined)
        yield f"event: score\ndata: {safe(scoring)}\n\n"

        # 🏆 DOMINANCE
        if BEST_IDEA is None:
            BEST_IDEA = refined
        else:
            BEST_IDEA = enforce_dominance(BEST_IDEA, refined)

        yield f"event: best\ndata: {safe(BEST_IDEA)}\n\n"

        # 🧠 MEMORY
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
            "mutation": mutation,
            "hypothesis": hypo,
            "score": scoring,
            "best": BEST_IDEA
        })

        save_memory()
        time.sleep(0.3)

    # FINAL OUTPUT
    final = final_report()
    yield f"event: final\ndata: {safe(final)}\n\n"
    yield f"event: done\ndata: complete\n\n"
