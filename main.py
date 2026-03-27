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


# ── Stock data ────────────────────────────────────────────────────────────────
# Static holdings per sector — mirrors the HD object in index.html.
# Swap these out for a real market-data API call (e.g. yfinance, Alpha Vantage)
# whenever you want genuine live prices.

HD = {
    "balanced": [
        {"t": "SPY",   "n": "SPDR S&P 500 ETF",       "p": 562.84, "ch": 0.42,  "lo": 430,  "hi": 580,  "pe": 22.4, "sg": "BUY",  "c": "#2563eb", "w": 20},
        {"t": "QQQ",   "n": "Invesco NASDAQ 100",      "p": 481.20, "ch": 0.68,  "lo": 360,  "hi": 510,  "pe": 28.1, "sg": "BUY",  "c": "#7c3aed", "w": 15},
        {"t": "MSFT",  "n": "Microsoft Corp",          "p": 420.34, "ch": -0.18, "lo": 310,  "hi": 450,  "pe": 35.2, "sg": "BUY",  "c": "#0891b2", "w": 10},
        {"t": "AAPL",  "n": "Apple Inc",               "p": 228.64, "ch": 0.89,  "lo": 165,  "hi": 240,  "pe": 31.4, "sg": "BUY",  "c": "#64748b", "w": 8},
        {"t": "NVDA",  "n": "NVIDIA Corp",             "p": 886.20, "ch": 1.82,  "lo": 450,  "hi": 1000, "pe": 62.4, "sg": "BUY",  "c": "#16a34a", "w": 7},
        {"t": "VTI",   "n": "Vanguard Total Market",   "p": 244.50, "ch": 0.31,  "lo": 195,  "hi": 258,  "pe": 21.8, "sg": "HOLD", "c": "#0a7c4e", "w": 12},
        {"t": "BND",   "n": "Vanguard Bond ETF",       "p": 73.42,  "ch": -0.05, "lo": 68,   "hi": 78,   "pe": None, "sg": "HOLD", "c": "#94a3b8", "w": 10},
        {"t": "GLD",   "n": "SPDR Gold Trust",         "p": 238.44, "ch": 0.44,  "lo": 175,  "hi": 255,  "pe": None, "sg": "BUY",  "c": "#b45309", "w": 5},
        {"t": "VNQ",   "n": "Vanguard Real Estate",    "p": 88.20,  "ch": 0.22,  "lo": 72,   "hi": 98,   "pe": 18.6, "sg": "HOLD", "c": "#db2777", "w": 8},
        {"t": "GOOGL", "n": "Alphabet Inc",            "p": 183.20, "ch": 0.12,  "lo": 130,  "hi": 198,  "pe": 24.8, "sg": "HOLD", "c": "#9333ea", "w": 5},
    ],
    "tech": [
        {"t": "QQQ",   "n": "Invesco NASDAQ 100",      "p": 481.20, "ch": 0.68,  "lo": 360,  "hi": 510,  "pe": 28.1, "sg": "BUY",  "c": "#7c3aed", "w": 22},
        {"t": "NVDA",  "n": "NVIDIA Corp",             "p": 886.20, "ch": 1.82,  "lo": 450,  "hi": 1000, "pe": 62.4, "sg": "BUY",  "c": "#16a34a", "w": 18},
        {"t": "MSFT",  "n": "Microsoft Corp",          "p": 420.34, "ch": -0.18, "lo": 310,  "hi": 450,  "pe": 35.2, "sg": "BUY",  "c": "#0891b2", "w": 15},
        {"t": "AAPL",  "n": "Apple Inc",               "p": 228.64, "ch": 0.89,  "lo": 165,  "hi": 240,  "pe": 31.4, "sg": "BUY",  "c": "#64748b", "w": 12},
        {"t": "META",  "n": "Meta Platforms",          "p": 528.10, "ch": 1.22,  "lo": 380,  "hi": 560,  "pe": 26.8, "sg": "BUY",  "c": "#2563eb", "w": 10},
        {"t": "GOOGL", "n": "Alphabet Inc",            "p": 183.20, "ch": 0.12,  "lo": 130,  "hi": 198,  "pe": 24.8, "sg": "HOLD", "c": "#9333ea", "w": 8},
        {"t": "AMD",   "n": "Advanced Micro Devices",  "p": 162.44, "ch": 2.14,  "lo": 100,  "hi": 220,  "pe": 48.2, "sg": "BUY",  "c": "#e11d48", "w": 7},
        {"t": "SMH",   "n": "VanEck Semiconductor",    "p": 222.60, "ch": 1.44,  "lo": 160,  "hi": 245,  "pe": 32.6, "sg": "BUY",  "c": "#b45309", "w": 8},
    ],
    "dividend": [
        {"t": "VYM",   "n": "Vanguard High Dividend",  "p": 122.30, "ch": 0.18,  "lo": 100,  "hi": 130,  "pe": 15.2, "sg": "BUY",  "c": "#0a7c4e", "w": 20},
        {"t": "SCHD",  "n": "Schwab US Dividend",      "p": 82.40,  "ch": 0.22,  "lo": 70,   "hi": 90,   "pe": 14.8, "sg": "BUY",  "c": "#2563eb", "w": 18},
        {"t": "JNJ",   "n": "Johnson & Johnson",       "p": 158.20, "ch": -0.08, "lo": 140,  "hi": 175,  "pe": 16.4, "sg": "HOLD", "c": "#b45309", "w": 12},
        {"t": "PG",    "n": "Procter & Gamble",        "p": 166.80, "ch": 0.14,  "lo": 148,  "hi": 178,  "pe": 25.8, "sg": "HOLD", "c": "#7c3aed", "w": 10},
        {"t": "KO",    "n": "Coca-Cola",               "p": 64.20,  "ch": 0.08,  "lo": 55,   "hi": 70,   "pe": 23.2, "sg": "HOLD", "c": "#e11d48", "w": 10},
        {"t": "O",     "n": "Realty Income",           "p": 54.60,  "ch": 0.32,  "lo": 45,   "hi": 62,   "pe": 42.8, "sg": "BUY",  "c": "#db2777", "w": 8},
        {"t": "VZ",    "n": "Verizon",                 "p": 40.20,  "ch": 0.12,  "lo": 32,   "hi": 46,   "pe": 10.2, "sg": "HOLD", "c": "#0891b2", "w": 8},
        {"t": "BND",   "n": "Vanguard Bond ETF",       "p": 73.42,  "ch": -0.05, "lo": 68,   "hi": 78,   "pe": None, "sg": "HOLD", "c": "#94a3b8", "w": 14},
    ],
    "growth": [
        {"t": "VUG",   "n": "Vanguard Growth ETF",     "p": 338.20, "ch": 0.52,  "lo": 268,  "hi": 360,  "pe": 32.1, "sg": "BUY",  "c": "#2563eb", "w": 18},
        {"t": "NVDA",  "n": "NVIDIA Corp",             "p": 886.20, "ch": 1.82,  "lo": 450,  "hi": 1000, "pe": 62.4, "sg": "BUY",  "c": "#16a34a", "w": 16},
        {"t": "TSLA",  "n": "Tesla Inc",               "p": 177.80, "ch": 2.44,  "lo": 140,  "hi": 280,  "pe": 44.2, "sg": "BUY",  "c": "#e11d48", "w": 14},
        {"t": "AMZN",  "n": "Amazon.com",              "p": 195.40, "ch": 0.88,  "lo": 145,  "hi": 210,  "pe": 38.6, "sg": "BUY",  "c": "#b45309", "w": 12},
        {"t": "META",  "n": "Meta Platforms",          "p": 528.10, "ch": 1.22,  "lo": 380,  "hi": 560,  "pe": 26.8, "sg": "BUY",  "c": "#0891b2", "w": 10},
        {"t": "MSFT",  "n": "Microsoft Corp",          "p": 420.34, "ch": -0.18, "lo": 310,  "hi": 450,  "pe": 35.2, "sg": "BUY",  "c": "#7c3aed", "w": 10},
        {"t": "CRWD",  "n": "CrowdStrike Holdings",    "p": 368.40, "ch": 1.64,  "lo": 220,  "hi": 400,  "pe": 72.4, "sg": "BUY",  "c": "#db2777", "w": 8},
        {"t": "SHOP",  "n": "Shopify Inc",             "p": 84.20,  "ch": 1.08,  "lo": 60,   "hi": 100,  "pe": 68.2, "sg": "HOLD", "c": "#9333ea", "w": 7},
    ],
    "defensive": [
        {"t": "VPU",   "n": "Vanguard Utilities ETF",  "p": 158.40, "ch": -0.12, "lo": 130,  "hi": 168,  "pe": 18.4, "sg": "HOLD", "c": "#2563eb", "w": 18},
        {"t": "XLP",   "n": "Consumer Staples SPDR",   "p": 82.60,  "ch": 0.08,  "lo": 70,   "hi": 88,   "pe": 20.2, "sg": "HOLD", "c": "#7c3aed", "w": 16},
        {"t": "XLV",   "n": "Health Care SPDR",        "p": 148.20, "ch": 0.22,  "lo": 128,  "hi": 162,  "pe": 17.8, "sg": "BUY",  "c": "#0891b2", "w": 14},
        {"t": "JNJ",   "n": "Johnson & Johnson",       "p": 158.20, "ch": -0.08, "lo": 140,  "hi": 175,  "pe": 16.4, "sg": "HOLD", "c": "#16a34a", "w": 10},
        {"t": "BND",   "n": "Vanguard Bond ETF",       "p": 73.42,  "ch": -0.05, "lo": 68,   "hi": 78,   "pe": None, "sg": "HOLD", "c": "#94a3b8", "w": 14},
        {"t": "GLD",   "n": "SPDR Gold Trust",         "p": 238.44, "ch": 0.44,  "lo": 175,  "hi": 255,  "pe": None, "sg": "BUY",  "c": "#b45309", "w": 10},
        {"t": "PG",    "n": "Procter & Gamble",        "p": 166.80, "ch": 0.14,  "lo": 148,  "hi": 178,  "pe": 25.8, "sg": "HOLD", "c": "#0a7c4e", "w": 10},
        {"t": "NEE",   "n": "NextEra Energy",          "p": 72.40,  "ch": 0.18,  "lo": 58,   "hi": 82,   "pe": 22.4, "sg": "HOLD", "c": "#db2777", "w": 8},
    ],
}

@app.route("/api/stocks", methods=["GET"])
def stocks():
    sector = request.args.get("sector", "balanced").lower()
    data = HD.get(sector, HD["balanced"])
    return jsonify({"stocks": data, "sector": sector})


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

import requests as http_requests

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama3-8b-8192"

def _groq(prompt: str, system: str = "") -> str:
    if not GROQ_API_KEY:
        return "GROQ_API_KEY not configured on the server."
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = http_requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": GROQ_MODEL, "max_tokens": 800, "messages": messages},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


@app.route("/api/analysis", methods=["POST"])
def portfolio_analysis():
    try:
        body    = request.get_json(force=True)
        sector  = body.get("sector", "balanced")
        horizon = body.get("horizon", "medium")
        amount  = body.get("amount", 10000)
        stocks  = HD.get(sector, HD["balanced"])
        holdings_text = "\n".join(
            f"  - {s['t']} ({s['n']}): ${s['p']} | P/E {s['pe']} | Signal {s['sg']} | Weight {s['w']}%"
            for s in stocks
        )
        prompt = (
            f"Portfolio: {sector} sector, {horizon} horizon, ${amount:,} invested.\n"
            f"Holdings:\n{holdings_text}\n\n"
            "Provide a concise investment analysis covering:\n"
            "1. Portfolio strengths\n"
            "2. Key risks\n"
            "3. Top 2 actionable recommendations\n"
            "Keep it under 250 words, professional tone."
        )
        system = "You are a senior portfolio analyst. Be concise, data-driven, and actionable."
        text   = _groq(prompt, system)
        return jsonify({"analysis": text, "sector": sector})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/screen", methods=["POST"])
def screen_stocks():
    try:
        body   = request.get_json(force=True)
        sector = body.get("sector", "balanced")
        stocks = HD.get(sector, HD["balanced"])
        holdings_text = "\n".join(
            f"  - {s['t']} ({s['n']}): ${s['p']} | P/E {s['pe']} | Signal {s['sg']}"
            for s in stocks
        )
        prompt = (
            f"Screen these {sector} portfolio stocks and rank the top 3 buys:\n"
            f"{holdings_text}\n\n"
            "For each pick give: ticker, one-line reason, target price range.\n"
            "Keep it under 200 words."
        )
        system = "You are a quantitative equity analyst. Be brief and specific."
        text   = _groq(prompt, system)
        return jsonify({"screen": text, "sector": sector})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
