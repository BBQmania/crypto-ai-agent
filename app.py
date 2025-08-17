import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "Crypto AI Agent is running!"

# Endpoint na sygnały
@app.route("/signal", methods=["POST"])
def signal():
    data = request.json
    return jsonify({"received": data})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
