import os
import re
from flask import Flask, Response, request, send_from_directory, render_template
from agent import run_agent_stream, stop

app = Flask(__name__)


# -----------------------
# 🏠 HOME ROUTE (FIXES 404)
# -----------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------
# ⚡ STREAM ENDPOINT (SSE)
# -----------------------
@app.route("/run")
def run():
    goal = request.args.get("goal", "")

    def generate():
        try:
            for chunk in run_agent_stream(goal):
                yield chunk
        except Exception as e:
            # Prevents hard crashes → shows error in UI instead
            yield f"event: error\ndata: {str(e)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


# -----------------------
# 🛑 STOP ENDPOINT
# -----------------------
@app.route("/stop")
def stop_agent():
    stop()
    return {"status": "stopped"}


# -----------------------
# 📥 DOWNLOAD ROUTE
# -----------------------
@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory("outputs", filename, as_attachment=True)


# -----------------------
# 🌊 NO CACHE (IMPORTANT FOR STREAMING)
# -----------------------
@app.after_request
def add_headers(response):
    response.headers["Cache-Control"] = "no-cache"
    return response


# -----------------------
# 🚀 RUN SERVER (RAILWAY FIX)
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
