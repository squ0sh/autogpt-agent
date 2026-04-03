from flask import Flask, jsonify, render_template_string
from agent import run_once

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Agent Control</title>
</head>
<body style="font-family: Arial; text-align: center; margin-top: 50px;">
    <h1>🧠 Your AI Agent</h1>
    <button onclick="runAgent()" style="padding: 15px; font-size: 18px;">
        Run Agent
    </button>
    <pre id="output" style="margin-top:20px; text-align:left;"></pre>

    <script>
        async function runAgent() {
            document.getElementById("output").innerText = "Running...";
            const res = await fetch('/run');
            const data = await res.json();
            document.getElementById("output").innerText = JSON.stringify(data, null, 2);
        }
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/run")
def run():
    result = run_once()
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
