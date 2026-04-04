from flask import Flask, render_template, request, Response
from agent import run_agent_stream, stop_agent

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/run-stream")
def run_stream():
    goal = request.args.get("goal", "")

    def generate():
        for chunk in run_agent_stream(goal):
            yield f"data: {chunk}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/stop", methods=["POST"])
def stop():
    stop_agent()
    return {"status": "stopped"}


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
