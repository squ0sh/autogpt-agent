from flask import Flask, jsonify, render_template, request
from agent import run_once

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/run", methods=["POST"])
def run():
    data = request.json
    goal = data.get("goal")

    result = run_once(goal)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
