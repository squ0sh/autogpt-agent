import os
import json
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# -----------------------
# 🧠 GPT HELPER
# -----------------------
def gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=800,
    )
    return response.choices[0].message.content.strip()


# -----------------------
# 📄 FILE WRITER
# -----------------------
def write_file(content, filename=None):
    if not filename:
        filename = f"file_{datetime.now().strftime('%H%M%S')}.txt"

    path = os.path.join(OUTPUT_DIR, filename)

    with open(path, "w") as f:
        f.write(content)

    return f"Saved file: {path}"


# -----------------------
# 📊 STRUCTURED JSON GENERATOR
# -----------------------
def generate_json(prompt):
    result = gpt(f"""
    Return structured JSON only.

    {prompt}
    """)
    try:
        return json.loads(result)
    except:
        return {"raw": result}


# -----------------------
# 🧠 CONTENT GENERATOR
# -----------------------
def generate_text(prompt):
    return gpt(prompt)


# -----------------------
# 🧾 SAVE JSON
# -----------------------
def save_json(data, filename=None):
    if not filename:
        filename = f"data_{datetime.now().strftime('%H%M%S')}.json"

    path = os.path.join(OUTPUT_DIR, filename)

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    return f"Saved JSON: {path}"


# -----------------------
# 🎯 MAIN TOOL ROUTER
# -----------------------
def run_tool(action):
    tool = action.get("action")
    input_data = action.get("input", "")

    if tool == "write":
        content = generate_text(input_data)
        return write_file(content)

    elif tool == "analyze":
        return generate_text(f"Analyze this:\n{input_data}")

    elif tool == "search":
        return generate_text(f"Research and summarize:\n{input_data}")

    elif tool == "json":
        data = generate_json(input_data)
        return save_json(data)

    else:
        return f"Unknown tool: {tool}"
