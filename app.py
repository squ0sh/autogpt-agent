import os
from flask import Flask, render_template, request, Response
from agent import run_agent_stream

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


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


