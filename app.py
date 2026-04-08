import os
from flask import Flask, Response, request, render_template, send_from_directory
from agent import run_agent

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/stream")
def stream():
    goal = request.args.get("goal", "")

    def event_stream():
        for event in run_agent(goal):
            yield event

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/stop", methods=["POST"])
def stop_route():
    stop()
    return "stopped"


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory("outputs", filename, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
