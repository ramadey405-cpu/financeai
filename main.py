import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from model import predict_loan

app = Flask(__name__)

CORS(app, origins=[
   
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    os.environ.get("FRONTEND_URL", "")
])

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "CreditWise ML API v2"})

@app.route("/api/loan/predict", methods=["POST"])
def loan_predict():
    try:
        data = request.get_json(force=True)

        required = ["name", "age", "gender", "married", "dependents",
                    "education", "income", "loanamt", "term",
                    "credit_score", "employment_status", "employer_category",
                    "area", "type"]

        missing = [f for f in required if f not in data or str(data[f]).strip() == ""]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        result = predict_loan(data)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
