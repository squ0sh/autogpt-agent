import os
from flask import Flask, jsonify, render_template, request, Response
from agent import run_once, run_agent_stream

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


# ✅ Existing mode (UNCHANGED)
@app.route("/run", methods=["POST"])
def run():
    data = request.json
    goal = data.get("goal")

    result = run_once(goal)
    return jsonify(result)


# ⚡ NEW STREAM MODE
@app.route("/stream")
def stream():
    goal = request.args.get("goal", "")

    def generate():
        for chunk in run_agent_stream(goal):
            yield chunk

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)

