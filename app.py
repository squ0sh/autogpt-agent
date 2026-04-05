import os
from flask import Flask, Response, request, send_from_directory
from agent import run_agent_stream, stop
import re

app = Flask(__name__)


# -----------------------
# ⚡ STREAM ENDPOINT (SSE)
# -----------------------
@app.route("/run")
def run():
    goal = request.args.get("goal", "")

    def generate():
        for chunk in run_agent_stream(goal):
            yield chunk

    return Response(generate(), mimetype="text/event-stream")


# -----------------------
# 🛑 STOP ENDPOINT
# -----------------------
@app.route("/stop")
def stop_agent():
    stop()
    return {"status": "stopped"}


# -----------------------
# 📥 FILE DOWNLOAD ROUTE
# -----------------------
@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory("outputs", filename, as_attachment=True)


# -----------------------
# 🎯 FORMAT FILE LINKS
# -----------------------
def format_file_link(text):
    """
    Converts:
    Saved file: outputs/final_xxx.txt

    Into:
    clickable download link
    """
    match = re.search(r"outputs/(.+\.txt)", text)
    if match:
        filename = match.group(1)
        return f"<a href='/download/{filename}' target='_blank'>⬇️ Download Final Result</a>"
    return text


# -----------------------
# 🌊 STREAM WRAPPER (OPTIONAL SAFETY)
# -----------------------
@app.after_request
def add_headers(response):
    response.headers["Cache-Control"] = "no-cache"
    return response


# -----------------------
# 🚀 MAIN
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
