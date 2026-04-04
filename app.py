import os
from flask import Flask, Response, request, render_template
from agent import run_agent_stream, stop

app = Flask(__name__)


# -----------------------
# 🏠 HOME
# -----------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------
# ⚡ STREAM ROUTE (SSE)
# -----------------------
@app.route("/stream")
def stream():
    goal = request.args.get("goal", "")

    def event_stream():
        for event in run_agent_stream(goal):
            yield event

    return Response(event_stream(), mimetype="text/event-stream")


# -----------------------
# 🛑 STOP ROUTE
# -----------------------
@app.route("/stop", methods=["POST"])
def stop_route():
    stop()
    return "stopped"


# -----------------------
# 🚀 RUN SERVER
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
