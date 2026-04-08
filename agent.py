import os
import random
from openai import OpenAI

client = OpenAI()

MODEL = "gpt-4o-mini"  # or your preferred model


# =========================
# 🔧 CORE LLM CALL
# =========================
def call_llm(prompt):
    response = client.responses.create(
        model=MODEL,
        input=prompt,
        temperature=0.9
    )
    return response.output[0].content[0].text


# =========================
# 🧬 MUTATION ENGINE
# =========================
def mutate_idea(idea):
    mutations = [
        "Invert causality (effects create causes)",
        "Remove time completely",
        "Assume perception is entirely unreliable",
        "Assume reality only exists when unobserved",
        "Introduce contradiction as a required law",
        "Apply non-human / alien cognition",
        "Swap subject and object",
        "Assume memory creates reality, not records it",
    ]
    
    mutation = random.choice(mutations)

    return f"""
{idea}

[Mutation Applied]: {mutation}

Reconstruct the entire idea under this condition. Do NOT summarize — transform it.
"""


# =========================
# ⚔️ ADVERSARIAL ATTACK
# =========================
def adversarial_attack(idea):
    return f"""
Critically attack the following idea:

{idea}

- Why is it wrong?
- What hidden assumptions does it rely on?
- How would an opposing intelligence dismantle it?
- Where does it collapse logically?

Then rebuild a stronger or completely different model.
"""


# =========================
# 👽 ALIEN CONSTRAINT
# =========================
def alien_injection():
    constraints = [
        "Intelligence evolved with no sense of time",
        "There is no cause-and-effect relationship",
        "Identity does not exist",
        "Multiple contradictions must be true simultaneously",
        "Logic is unstable and changes over time",
        "Awareness cannot observe itself",
        "Memory is nonlinear and editable from the future",
    ]
    
    return f"""
Apply this non-human constraint:

{random.choice(constraints)}

Now rebuild the idea so it functions under this condition.
"""


# =========================
# ⚙️ MECHANISM ENFORCER
# =========================
def enforce_mechanism(idea):
    return f"""
Convert this into a working mechanism:

{idea}

Requirements:
- Define inputs and outputs
- Describe the process step-by-step
- Explain how it operates (not just what it means)
- Make it possible (in principle) to simulate

Avoid abstract language.
"""


# =========================
# 🚀 STEP GENERATOR
# =========================
def generate_step(previous_output, step_num):
    base_prompt = f"""
You are an advanced conceptual synthesis engine.

Current Step: {step_num}

Previous Output:
{previous_output}

Instructions:
- Generate a completely new conceptual direction (NOT a variation)
- Avoid common patterns: paradox, duality, interconnectedness
- Introduce something structurally different
- Do NOT converge — diverge

Label sections clearly:
- Title
- Concept
- Mechanism (initial)
"""

    return call_llm(base_prompt)


# =========================
# 🔁 MAIN LOOP
# =========================
def run_agent(initial_prompt, steps=6):
    output_log = []

    current = initial_prompt

    for step in range(1, steps + 1):
        print(f"\n--- Step {step} ---\n")

        # 1. Generate base idea
        generated = generate_step(current, step)

        # 2. Mutation
        mutated = call_llm(mutate_idea(generated))

        # 3. Adversarial attack
        attacked = call_llm(adversarial_attack(mutated))

        # 4. Alien injection
        aliened = call_llm(alien_injection() + "\n" + attacked)

        # 5. Mechanism enforcement
        final = call_llm(enforce_mechanism(aliened))

        # Save + print
        output_log.append({
            "step": step,
            "content": final
        })

        print(final)

        # Feed forward
        current = final

    return output_log


# =========================
# 🧪 RUN
# =========================
if __name__ == "__main__":
    prompt = """
Generate a completely original framework that challenges fundamental assumptions about reality.
"""

    results = run_agent(prompt, steps=6)
