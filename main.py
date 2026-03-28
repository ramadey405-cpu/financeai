import os
import requests as http_requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from model import predict_loan

app = Flask(__name__)
CORS(app)  # Allow all origins — fine for a portfolio/demo project

# ─────────────────────────────────────────────────────────────────────────────
#  LIVE PRICE HELPER  (yfinance — optional, gracefully degrades to static data)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False


def _live_price(ticker_ns: str) -> dict | None:
    """
    Fetch live quote for an NSE/BSE ticker via yfinance.
    ticker_ns should already include the suffix, e.g. "RELIANCE.NS" or "TCS.NS".
    Returns dict with keys: p (price), ch (% change) — or None on failure.
    """
    if not _YF_AVAILABLE:
        return None
    try:
        t = yf.Ticker(ticker_ns)
        info = t.fast_info
        price  = round(info.last_price, 2)
        prev   = info.previous_close
        change = round((price - prev) / prev * 100, 2) if prev else 0.0
        return {"p": price, "ch": change}
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  ORIGINAL US PORTFOLIO DATA  (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
HD_US = {
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

# ─────────────────────────────────────────────────────────────────────────────
#  INDIAN MARKET DATA  —  NSE / BSE
#
#  Schema per stock (prices in INR ₹):
#    t   = NSE ticker symbol
#    yf  = yfinance ticker (ticker + ".NS" for NSE, ".BO" for BSE-only)
#    n   = Full company name
#    p   = Last known price (₹)  — overridden by live fetch if yfinance available
#    ch  = % change (day)
#    lo  = 52-week low  (₹)
#    hi  = 52-week high (₹)
#    pe  = Price/Earnings ratio  (None for ETFs/bonds)
#    sg  = Analyst signal  BUY / HOLD / SELL
#    c   = Chart color hex
#    w   = Portfolio weight %
#    ex  = Exchange  "NSE" | "BSE" | "BOTH"
#    sec = Sector
#    mc  = Market cap tier  "LARGE" | "MID" | "SMALL"
#    div = Dividend yield %  (approximate)
# ─────────────────────────────────────────────────────────────────────────────

# ── Master Indian stock universe (120 + stocks) ───────────────────────────────
INDIAN_UNIVERSE = [

    # ── NIFTY 50 / LARGE CAP ─────────────────────────────────────────────────
    # IT & Technology
    {"t":"TCS",      "yf":"TCS.NS",      "n":"Tata Consultancy Services", "p":3842, "ch":0.34,  "lo":3056, "hi":4592, "pe":28.4, "sg":"BUY",  "c":"#2563eb", "w":0, "ex":"BOTH", "sec":"IT",          "mc":"LARGE", "div":1.8},
    {"t":"INFY",     "yf":"INFY.NS",     "n":"Infosys Ltd",               "p":1482, "ch":-0.21, "lo":1218, "hi":1964, "pe":22.6, "sg":"BUY",  "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"IT",          "mc":"LARGE", "div":2.4},
    {"t":"WIPRO",    "yf":"WIPRO.NS",    "n":"Wipro Ltd",                 "p":462,  "ch":0.44,  "lo":380,  "hi":584,  "pe":18.8, "sg":"HOLD", "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"IT",          "mc":"LARGE", "div":0.2},
    {"t":"HCLTECH",  "yf":"HCLTECH.NS",  "n":"HCL Technologies",         "p":1542, "ch":0.62,  "lo":1236, "hi":1996, "pe":24.2, "sg":"BUY",  "c":"#16a34a", "w":0, "ex":"BOTH", "sec":"IT",          "mc":"LARGE", "div":3.2},
    {"t":"TECHM",    "yf":"TECHM.NS",    "n":"Tech Mahindra Ltd",         "p":1282, "ch":1.04,  "lo":988,  "hi":1762, "pe":26.8, "sg":"BUY",  "c":"#db2777", "w":0, "ex":"BOTH", "sec":"IT",          "mc":"LARGE", "div":1.6},
    {"t":"LTIM",     "yf":"LTIM.NS",     "n":"LTIMindtree Ltd",           "p":5124, "ch":0.88,  "lo":4286, "hi":6767, "pe":32.4, "sg":"BUY",  "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"IT",          "mc":"LARGE", "div":0.8},
    {"t":"MPHASIS",  "yf":"MPHASIS.NS",  "n":"Mphasis Ltd",               "p":2486, "ch":0.56,  "lo":1912, "hi":3044, "pe":28.6, "sg":"HOLD", "c":"#9333ea", "w":0, "ex":"BOTH", "sec":"IT",          "mc":"MID",   "div":1.4},
    {"t":"PERSISTENT","yf":"PERSISTENT.NS","n":"Persistent Systems",      "p":4862, "ch":1.24,  "lo":3788, "hi":6142, "pe":48.2, "sg":"BUY",  "c":"#0a7c4e", "w":0, "ex":"BOTH", "sec":"IT",          "mc":"MID",   "div":0.4},
    {"t":"COFORGE",  "yf":"COFORGE.NS",  "n":"Coforge Ltd",               "p":7242, "ch":0.96,  "lo":4982, "hi":9184, "pe":42.6, "sg":"BUY",  "c":"#b45309", "w":0, "ex":"BOTH", "sec":"IT",          "mc":"MID",   "div":0.6},
    {"t":"OFSS",     "yf":"OFSS.NS",     "n":"Oracle Financial Services",  "p":9124, "ch":0.28,  "lo":6842, "hi":10288,"pe":34.8, "sg":"HOLD", "c":"#64748b", "w":0, "ex":"BOTH", "sec":"IT",          "mc":"MID",   "div":2.2},

    # Banking & Finance
    {"t":"HDFCBANK", "yf":"HDFCBANK.NS", "n":"HDFC Bank Ltd",             "p":1642, "ch":0.18,  "lo":1407, "hi":1880, "pe":18.4, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"LARGE", "div":1.2},
    {"t":"ICICIBANK","yf":"ICICIBANK.NS","n":"ICICI Bank Ltd",             "p":1224, "ch":0.42,  "lo":986,  "hi":1362, "pe":17.6, "sg":"BUY",  "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"LARGE", "div":0.8},
    {"t":"SBIN",     "yf":"SBIN.NS",     "n":"State Bank of India",        "p":782,  "ch":-0.32, "lo":607,  "hi":912,  "pe":10.2, "sg":"BUY",  "c":"#15803d", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"LARGE", "div":1.8},
    {"t":"AXISBANK", "yf":"AXISBANK.NS", "n":"Axis Bank Ltd",              "p":1124, "ch":0.56,  "lo":886,  "hi":1340, "pe":14.8, "sg":"BUY",  "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"LARGE", "div":0.1},
    {"t":"KOTAKBANK","yf":"KOTAKBANK.NS","n":"Kotak Mahindra Bank",        "p":1786, "ch":-0.14, "lo":1543, "hi":2162, "pe":20.4, "sg":"HOLD", "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"LARGE", "div":0.1},
    {"t":"INDUSINDBK","yf":"INDUSINDBK.NS","n":"IndusInd Bank Ltd",        "p":964,  "ch":-0.84, "lo":771,  "hi":1694, "pe":9.4,  "sg":"HOLD", "c":"#b45309", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"LARGE", "div":1.4},
    {"t":"PNB",      "yf":"PNB.NS",      "n":"Punjab National Bank",       "p":102,  "ch":0.28,  "lo":80,   "hi":142,  "pe":8.6,  "sg":"HOLD", "c":"#94a3b8", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"LARGE", "div":1.2},
    {"t":"BANKBARODA","yf":"BANKBARODA.NS","n":"Bank of Baroda",           "p":228,  "ch":0.44,  "lo":182,  "hi":298,  "pe":7.2,  "sg":"BUY",  "c":"#0a7c4e", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"LARGE", "div":2.6},
    {"t":"CANBK",    "yf":"CANBK.NS",    "n":"Canara Bank",                "p":98,   "ch":0.62,  "lo":78,   "hi":128,  "pe":6.4,  "sg":"BUY",  "c":"#db2777", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"LARGE", "div":2.8},
    {"t":"FEDERALBNK","yf":"FEDERALBNK.NS","n":"Federal Bank Ltd",         "p":182,  "ch":0.38,  "lo":138,  "hi":218,  "pe":11.2, "sg":"BUY",  "c":"#9333ea", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"MID",   "div":0.8},
    {"t":"IDFCFIRSTB","yf":"IDFCFIRSTB.NS","n":"IDFC First Bank",          "p":68,   "ch":-0.58, "lo":52,   "hi":98,   "pe":18.4, "sg":"HOLD", "c":"#64748b", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"MID",   "div":0.0},
    {"t":"RBLBANK",  "yf":"RBLBANK.NS",  "n":"RBL Bank Ltd",               "p":182,  "ch":0.44,  "lo":138,  "hi":264,  "pe":12.8, "sg":"HOLD", "c":"#2563eb", "w":0, "ex":"BOTH", "sec":"BANKING",     "mc":"MID",   "div":0.6},

    # NBFC & Financial Services
    {"t":"BAJFINANCE","yf":"BAJFINANCE.NS","n":"Bajaj Finance Ltd",         "p":6842, "ch":0.72,  "lo":5468, "hi":8192, "pe":28.6, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"NBFC",        "mc":"LARGE", "div":0.4},
    {"t":"BAJAJFINSV","yf":"BAJAJFINSV.NS","n":"Bajaj Finserv Ltd",        "p":1684, "ch":0.48,  "lo":1342, "hi":2042, "pe":22.4, "sg":"BUY",  "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"NBFC",        "mc":"LARGE", "div":0.1},
    {"t":"CHOLAFIN", "yf":"CHOLAFIN.NS", "n":"Cholamandalam Invest & Fin", "p":1242, "ch":0.84,  "lo":862,  "hi":1542, "pe":26.8, "sg":"BUY",  "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"NBFC",        "mc":"MID",   "div":0.2},
    {"t":"MUTHOOTFIN","yf":"MUTHOOTFIN.NS","n":"Muthoot Finance Ltd",      "p":1924, "ch":0.36,  "lo":1286, "hi":2148, "pe":14.4, "sg":"BUY",  "c":"#b45309", "w":0, "ex":"BOTH", "sec":"NBFC",        "mc":"MID",   "div":1.4},
    {"t":"LICHSGFIN","yf":"LICHSGFIN.NS","n":"LIC Housing Finance",        "p":624,  "ch":-0.22, "lo":462,  "hi":782,  "pe":8.6,  "sg":"HOLD", "c":"#16a34a", "w":0, "ex":"BOTH", "sec":"NBFC",        "mc":"MID",   "div":1.8},
    {"t":"SHRIRAMFIN","yf":"SHRIRAMFIN.NS","n":"Shriram Finance Ltd",      "p":2642, "ch":0.62,  "lo":2042, "hi":3124, "pe":15.2, "sg":"BUY",  "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"NBFC",        "mc":"MID",   "div":0.8},

    # Insurance
    {"t":"LICI",     "yf":"LICI.NS",     "n":"Life Insurance Corp of India","p":924, "ch":0.28,  "lo":724,  "hi":1222, "pe":13.4, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"INSURANCE",   "mc":"LARGE", "div":1.2},
    {"t":"SBILIFE",  "yf":"SBILIFE.NS",  "n":"SBI Life Insurance",          "p":1542,"ch":0.14,  "lo":1228, "hi":1964, "pe":68.4, "sg":"HOLD", "c":"#15803d", "w":0, "ex":"BOTH", "sec":"INSURANCE",   "mc":"LARGE", "div":0.2},
    {"t":"HDFCLIFE", "yf":"HDFCLIFE.NS", "n":"HDFC Life Insurance",         "p":642, "ch":0.32,  "lo":511,  "hi":786,  "pe":82.4, "sg":"HOLD", "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"INSURANCE",   "mc":"LARGE", "div":0.3},
    {"t":"ICICIPRULI","yf":"ICICIPRULI.NS","n":"ICICI Prudential Life",     "p":682, "ch":0.44,  "lo":524,  "hi":842,  "pe":72.6, "sg":"HOLD", "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"INSURANCE",   "mc":"MID",   "div":0.4},
    {"t":"GICRE",    "yf":"GICRE.NS",    "n":"General Insurance Corp",      "p":382, "ch":-0.18, "lo":284,  "hi":462,  "pe":12.4, "sg":"HOLD", "c":"#b45309", "w":0, "ex":"BOTH", "sec":"INSURANCE",   "mc":"MID",   "div":2.4},

    # Energy & Oil
    {"t":"RELIANCE", "yf":"RELIANCE.NS", "n":"Reliance Industries Ltd",    "p":2842, "ch":0.62,  "lo":2228, "hi":3217, "pe":24.8, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"ENERGY",      "mc":"LARGE", "div":0.4},
    {"t":"ONGC",     "yf":"ONGC.NS",     "n":"Oil & Natural Gas Corp",      "p":268,  "ch":-0.42, "lo":186,  "hi":344,  "pe":7.4,  "sg":"HOLD", "c":"#b45309", "w":0, "ex":"BOTH", "sec":"ENERGY",      "mc":"LARGE", "div":4.8},
    {"t":"IOC",      "yf":"IOC.NS",      "n":"Indian Oil Corporation",      "p":142,  "ch":-0.28, "lo":108,  "hi":196,  "pe":6.2,  "sg":"HOLD", "c":"#64748b", "w":0, "ex":"BOTH", "sec":"ENERGY",      "mc":"LARGE", "div":5.6},
    {"t":"BPCL",     "yf":"BPCL.NS",     "n":"Bharat Petroleum Corp",       "p":312,  "ch":0.18,  "lo":236,  "hi":388,  "pe":8.4,  "sg":"BUY",  "c":"#0a7c4e", "w":0, "ex":"BOTH", "sec":"ENERGY",      "mc":"LARGE", "div":4.2},
    {"t":"HINDPETRO","yf":"HINDPETRO.NS","n":"Hindustan Petroleum Corp",    "p":372,  "ch":0.36,  "lo":268,  "hi":458,  "pe":7.8,  "sg":"BUY",  "c":"#db2777", "w":0, "ex":"BOTH", "sec":"ENERGY",      "mc":"LARGE", "div":3.8},
    {"t":"GAIL",     "yf":"GAIL.NS",     "n":"GAIL India Ltd",              "p":208,  "ch":0.48,  "lo":154,  "hi":246,  "pe":11.4, "sg":"BUY",  "c":"#16a34a", "w":0, "ex":"BOTH", "sec":"ENERGY",      "mc":"LARGE", "div":2.8},
    {"t":"PETRONET", "yf":"PETRONET.NS", "n":"Petronet LNG Ltd",            "p":302,  "ch":0.22,  "lo":228,  "hi":362,  "pe":12.8, "sg":"BUY",  "c":"#9333ea", "w":0, "ex":"BOTH", "sec":"ENERGY",      "mc":"MID",   "div":3.2},

    # Power & Utilities
    {"t":"NTPC",     "yf":"NTPC.NS",     "n":"NTPC Ltd",                    "p":362,  "ch":0.54,  "lo":264,  "hi":428,  "pe":16.2, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"POWER",       "mc":"LARGE", "div":2.6},
    {"t":"POWERGRID","yf":"POWERGRID.NS","n":"Power Grid Corp of India",    "p":314,  "ch":0.38,  "lo":228,  "hi":368,  "pe":18.4, "sg":"BUY",  "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"POWER",       "mc":"LARGE", "div":3.8},
    {"t":"ADANIGREEN","yf":"ADANIGREEN.NS","n":"Adani Green Energy Ltd",    "p":1624, "ch":1.24,  "lo":826,  "hi":2144, "pe":148.4,"sg":"HOLD", "c":"#16a34a", "w":0, "ex":"BOTH", "sec":"POWER",       "mc":"LARGE", "div":0.0},
    {"t":"ADANIPOWER","yf":"ADANIPOWER.NS","n":"Adani Power Ltd",           "p":582,  "ch":0.68,  "lo":386,  "hi":798,  "pe":8.2,  "sg":"BUY",  "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"POWER",       "mc":"LARGE", "div":0.0},
    {"t":"TATAPOWER","yf":"TATAPOWER.NS","n":"Tata Power Co Ltd",           "p":378,  "ch":0.82,  "lo":268,  "hi":462,  "pe":28.4, "sg":"BUY",  "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"POWER",       "mc":"MID",   "div":0.6},
    {"t":"TORNTPOWER","yf":"TORNTPOWER.NS","n":"Torrent Power Ltd",         "p":1424, "ch":0.44,  "lo":1068, "hi":1842, "pe":22.6, "sg":"BUY",  "c":"#b45309", "w":0, "ex":"BOTH", "sec":"POWER",       "mc":"MID",   "div":1.2},
    {"t":"CESC",     "yf":"CESC.NS",     "n":"CESC Ltd",                    "p":168,  "ch":-0.12, "lo":128,  "hi":208,  "pe":12.4, "sg":"HOLD", "c":"#0a7c4e", "w":0, "ex":"BOTH", "sec":"POWER",       "mc":"MID",   "div":2.4},

    # Metals & Mining
    {"t":"TATASTEEL","yf":"TATASTEEL.NS","n":"Tata Steel Ltd",              "p":142,  "ch":-0.84, "lo":108,  "hi":184,  "pe":12.6, "sg":"HOLD", "c":"#64748b", "w":0, "ex":"BOTH", "sec":"METALS",      "mc":"LARGE", "div":2.8},
    {"t":"JSWSTEEL", "yf":"JSWSTEEL.NS", "n":"JSW Steel Ltd",               "p":882,  "ch":0.42,  "lo":682,  "hi":1062, "pe":14.8, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"METALS",      "mc":"LARGE", "div":1.6},
    {"t":"HINDALCO", "yf":"HINDALCO.NS", "n":"Hindalco Industries",         "p":628,  "ch":0.28,  "lo":462,  "hi":758,  "pe":11.4, "sg":"BUY",  "c":"#b45309", "w":0, "ex":"BOTH", "sec":"METALS",      "mc":"LARGE", "div":0.6},
    {"t":"VEDL",     "yf":"VEDL.NS",     "n":"Vedanta Ltd",                  "p":448,  "ch":-0.62, "lo":222,  "hi":526,  "pe":9.8,  "sg":"HOLD", "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"METALS",      "mc":"LARGE", "div":8.4},
    {"t":"NMDC",     "yf":"NMDC.NS",     "n":"NMDC Ltd",                     "p":216,  "ch":0.38,  "lo":162,  "hi":268,  "pe":9.2,  "sg":"BUY",  "c":"#16a34a", "w":0, "ex":"BOTH", "sec":"METALS",      "mc":"LARGE", "div":4.2},
    {"t":"COALINDIA","yf":"COALINDIA.NS","n":"Coal India Ltd",               "p":442,  "ch":-0.28, "lo":338,  "hi":542,  "pe":7.8,  "sg":"HOLD", "c":"#94a3b8", "w":0, "ex":"BOTH", "sec":"METALS",      "mc":"LARGE", "div":5.8},
    {"t":"SAIL",     "yf":"SAIL.NS",     "n":"Steel Authority of India",     "p":128,  "ch":-0.48, "lo":88,   "hi":172,  "pe":11.2, "sg":"HOLD", "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"METALS",      "mc":"LARGE", "div":2.2},
    {"t":"JINDALSTEL","yf":"JINDALSTEL.NS","n":"Jindal Steel & Power",       "p":882,  "ch":0.64,  "lo":608,  "hi":1068, "pe":12.8, "sg":"BUY",  "c":"#db2777", "w":0, "ex":"BOTH", "sec":"METALS",      "mc":"MID",   "div":0.6},

    # Automobiles
    {"t":"MARUTI",   "yf":"MARUTI.NS",   "n":"Maruti Suzuki India",         "p":11842,"ch":0.44,  "lo":9048, "hi":13680,"pe":26.4, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"AUTO",        "mc":"LARGE", "div":1.0},
    {"t":"TATAMOTORS","yf":"TATAMOTORS.NS","n":"Tata Motors Ltd",            "p":782,  "ch":0.88,  "lo":564,  "hi":1064, "pe":8.2,  "sg":"BUY",  "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"AUTO",        "mc":"LARGE", "div":0.0},
    {"t":"M&M",      "yf":"M&M.NS",      "n":"Mahindra & Mahindra",         "p":2842, "ch":0.72,  "lo":1688, "hi":3264, "pe":26.8, "sg":"BUY",  "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"AUTO",        "mc":"LARGE", "div":0.6},
    {"t":"BAJAJ-AUTO","yf":"BAJAJ-AUTO.NS","n":"Bajaj Auto Ltd",             "p":8642, "ch":0.38,  "lo":6248, "hi":10148,"pe":22.4, "sg":"BUY",  "c":"#16a34a", "w":0, "ex":"BOTH", "sec":"AUTO",        "mc":"LARGE", "div":1.6},
    {"t":"HEROMOTOCO","yf":"HEROMOTOCO.NS","n":"Hero MotoCorp Ltd",          "p":4682, "ch":0.28,  "lo":3428, "hi":5842, "pe":18.4, "sg":"HOLD", "c":"#b45309", "w":0, "ex":"BOTH", "sec":"AUTO",        "mc":"LARGE", "div":2.4},
    {"t":"EICHERMOT","yf":"EICHERMOT.NS","n":"Eicher Motors Ltd",            "p":4242, "ch":0.52,  "lo":3128, "hi":5128, "pe":28.6, "sg":"BUY",  "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"AUTO",        "mc":"LARGE", "div":0.8},
    {"t":"TVSMOTORS","yf":"TVSMOTORS.NS","n":"TVS Motor Company",            "p":2242, "ch":0.68,  "lo":1742, "hi":2842, "pe":42.4, "sg":"BUY",  "c":"#9333ea", "w":0, "ex":"BOTH", "sec":"AUTO",        "mc":"MID",   "div":0.6},
    {"t":"ASHOKLEY", "yf":"ASHOKLEY.NS", "n":"Ashok Leyland Ltd",            "p":228,  "ch":0.44,  "lo":168,  "hi":286,  "pe":18.8, "sg":"BUY",  "c":"#db2777", "w":0, "ex":"BOTH", "sec":"AUTO",        "mc":"MID",   "div":2.2},
    {"t":"BALKRISIND","yf":"BALKRISIND.NS","n":"Balkrishna Industries",      "p":2842, "ch":0.38,  "lo":2128, "hi":3242, "pe":28.4, "sg":"BUY",  "c":"#0a7c4e", "w":0, "ex":"BOTH", "sec":"AUTO",        "mc":"MID",   "div":0.6},

    # Pharmaceuticals & Healthcare
    {"t":"SUNPHARMA","yf":"SUNPHARMA.NS","n":"Sun Pharmaceutical Ind",      "p":1682, "ch":0.42,  "lo":1148, "hi":1788, "pe":32.4, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"PHARMA",      "mc":"LARGE", "div":0.8},
    {"t":"DRREDDY",  "yf":"DRREDDY.NS",  "n":"Dr. Reddy's Laboratories",    "p":5842, "ch":0.28,  "lo":4682, "hi":7284, "pe":18.8, "sg":"BUY",  "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"PHARMA",      "mc":"LARGE", "div":0.4},
    {"t":"CIPLA",    "yf":"CIPLA.NS",    "n":"Cipla Ltd",                    "p":1382, "ch":0.64,  "lo":1042, "hi":1688, "pe":24.2, "sg":"BUY",  "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"PHARMA",      "mc":"LARGE", "div":0.4},
    {"t":"DIVISLAB", "yf":"DIVISLAB.NS", "n":"Divi's Laboratories",          "p":4842, "ch":0.82,  "lo":3528, "hi":5842, "pe":54.8, "sg":"BUY",  "c":"#16a34a", "w":0, "ex":"BOTH", "sec":"PHARMA",      "mc":"LARGE", "div":0.4},
    {"t":"BIOCON",   "yf":"BIOCON.NS",   "n":"Biocon Ltd",                   "p":288,  "ch":-0.42, "lo":212,  "hi":364,  "pe":48.4, "sg":"HOLD", "c":"#b45309", "w":0, "ex":"BOTH", "sec":"PHARMA",      "mc":"MID",   "div":0.2},
    {"t":"TORNTPHARM","yf":"TORNTPHARM.NS","n":"Torrent Pharmaceuticals",    "p":2842, "ch":0.36,  "lo":2128, "hi":3442, "pe":38.6, "sg":"BUY",  "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"PHARMA",      "mc":"MID",   "div":0.6},
    {"t":"AUROPHARMA","yf":"AUROPHARMA.NS","n":"Aurobindo Pharma Ltd",       "p":1182, "ch":0.44,  "lo":842,  "hi":1442, "pe":16.4, "sg":"BUY",  "c":"#db2777", "w":0, "ex":"BOTH", "sec":"PHARMA",      "mc":"MID",   "div":0.4},
    {"t":"LUPIN",    "yf":"LUPIN.NS",    "n":"Lupin Ltd",                    "p":1842, "ch":0.62,  "lo":1242, "hi":2248, "pe":22.8, "sg":"BUY",  "c":"#9333ea", "w":0, "ex":"BOTH", "sec":"PHARMA",      "mc":"MID",   "div":0.6},
    {"t":"APOLLOHOSP","yf":"APOLLOHOSP.NS","n":"Apollo Hospitals Enterprise","p":6642, "ch":0.84,  "lo":4982, "hi":7542, "pe":82.4, "sg":"BUY",  "c":"#0a7c4e", "w":0, "ex":"BOTH", "sec":"HEALTHCARE",  "mc":"LARGE", "div":0.2},

    # FMCG & Consumer
    {"t":"HINDUNILVR","yf":"HINDUNILVR.NS","n":"Hindustan Unilever Ltd",    "p":2342, "ch":-0.18, "lo":2082, "hi":2924, "pe":52.4, "sg":"HOLD", "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"FMCG",        "mc":"LARGE", "div":1.8},
    {"t":"ITC",      "yf":"ITC.NS",      "n":"ITC Ltd",                     "p":468,  "ch":0.28,  "lo":382,  "hi":542,  "pe":28.4, "sg":"BUY",  "c":"#16a34a", "w":0, "ex":"BOTH", "sec":"FMCG",        "mc":"LARGE", "div":2.4},
    {"t":"NESTLEIND","yf":"NESTLEIND.NS","n":"Nestle India Ltd",             "p":2242, "ch":-0.14, "lo":1988, "hi":2682, "pe":68.4, "sg":"HOLD", "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"FMCG",        "mc":"LARGE", "div":1.4},
    {"t":"BRITANNIA","yf":"BRITANNIA.NS","n":"Britannia Industries",         "p":4842, "ch":0.18,  "lo":4082, "hi":6042, "pe":48.4, "sg":"HOLD", "c":"#b45309", "w":0, "ex":"BOTH", "sec":"FMCG",        "mc":"LARGE", "div":1.6},
    {"t":"DABUR",    "yf":"DABUR.NS",    "n":"Dabur India Ltd",              "p":512,  "ch":-0.12, "lo":452,  "hi":672,  "pe":48.2, "sg":"HOLD", "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"FMCG",        "mc":"LARGE", "div":0.8},
    {"t":"MARICO",   "yf":"MARICO.NS",   "n":"Marico Ltd",                   "p":562,  "ch":0.22,  "lo":482,  "hi":682,  "pe":44.6, "sg":"HOLD", "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"FMCG",        "mc":"LARGE", "div":1.4},
    {"t":"GODREJCP", "yf":"GODREJCP.NS", "n":"Godrej Consumer Products",    "p":1042, "ch":0.38,  "lo":882,  "hi":1382, "pe":38.4, "sg":"HOLD", "c":"#9333ea", "w":0, "ex":"BOTH", "sec":"FMCG",        "mc":"LARGE", "div":0.8},
    {"t":"COLPAL",   "yf":"COLPAL.NS",   "n":"Colgate-Palmolive India",      "p":2842, "ch":0.14,  "lo":2242, "hi":3442, "pe":42.8, "sg":"HOLD", "c":"#db2777", "w":0, "ex":"BOTH", "sec":"FMCG",        "mc":"MID",   "div":1.6},
    {"t":"EMAMILTD", "yf":"EMAMILTD.NS", "n":"Emami Ltd",                    "p":582,  "ch":0.28,  "lo":442,  "hi":782,  "pe":28.4, "sg":"HOLD", "c":"#0a7c4e", "w":0, "ex":"BOTH", "sec":"FMCG",        "mc":"MID",   "div":1.2},

    # Infrastructure & Construction
    {"t":"LT",       "yf":"LT.NS",       "n":"Larsen & Toubro Ltd",          "p":3642, "ch":0.52,  "lo":2782, "hi":3964, "pe":28.4, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"INFRA",       "mc":"LARGE", "div":1.0},
    {"t":"ULTRACEMCO","yf":"ULTRACEMCO.NS","n":"UltraTech Cement Ltd",       "p":10242,"ch":0.38,  "lo":7982, "hi":12248,"pe":32.4, "sg":"BUY",  "c":"#64748b", "w":0, "ex":"BOTH", "sec":"INFRA",       "mc":"LARGE", "div":0.6},
    {"t":"GRASIM",   "yf":"GRASIM.NS",   "n":"Grasim Industries Ltd",        "p":2642, "ch":0.44,  "lo":1842, "hi":2982, "pe":22.4, "sg":"BUY",  "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"INFRA",       "mc":"LARGE", "div":0.8},
    {"t":"SHREECEM", "yf":"SHREECEM.NS", "n":"Shree Cement Ltd",              "p":24842,"ch":0.28,  "lo":19842,"hi":29248,"pe":38.4, "sg":"HOLD", "c":"#b45309", "w":0, "ex":"BOTH", "sec":"INFRA",       "mc":"LARGE", "div":0.4},
    {"t":"ACC",      "yf":"ACC.NS",      "n":"ACC Ltd",                       "p":2042, "ch":0.34,  "lo":1642, "hi":2682, "pe":18.8, "sg":"HOLD", "c":"#16a34a", "w":0, "ex":"BOTH", "sec":"INFRA",       "mc":"MID",   "div":1.2},
    {"t":"AMBUJACEMENT","yf":"AMBUJACEMENT.NS","n":"Ambuja Cements Ltd",      "p":582,  "ch":0.44,  "lo":448,  "hi":742,  "pe":24.6, "sg":"BUY",  "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"INFRA",       "mc":"LARGE", "div":0.6},
    {"t":"DLF",      "yf":"DLF.NS",      "n":"DLF Ltd",                       "p":842,  "ch":0.62,  "lo":568,  "hi":1024, "pe":42.8, "sg":"BUY",  "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"REALTY",      "mc":"LARGE", "div":0.4},
    {"t":"GODREJPROP","yf":"GODREJPROP.NS","n":"Godrej Properties Ltd",       "p":2842, "ch":0.88,  "lo":1882, "hi":3284, "pe":68.4, "sg":"BUY",  "c":"#db2777", "w":0, "ex":"BOTH", "sec":"REALTY",      "mc":"MID",   "div":0.0},
    {"t":"PRESTIGE", "yf":"PRESTIGE.NS", "n":"Prestige Estates Projects",    "p":1642, "ch":0.72,  "lo":1148, "hi":2148, "pe":48.6, "sg":"BUY",  "c":"#9333ea", "w":0, "ex":"BOTH", "sec":"REALTY",      "mc":"MID",   "div":0.2},

    # Telecom
    {"t":"BHARTIARTL","yf":"BHARTIARTL.NS","n":"Bharti Airtel Ltd",          "p":1642, "ch":0.42,  "lo":1082, "hi":1832, "pe":68.4, "sg":"BUY",  "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"TELECOM",     "mc":"LARGE", "div":0.4},
    {"t":"INDUSTOWER","yf":"INDUSTOWER.NS","n":"Indus Towers Ltd",            "p":342,  "ch":-0.28, "lo":224,  "hi":436,  "pe":16.4, "sg":"HOLD", "c":"#94a3b8", "w":0, "ex":"BOTH", "sec":"TELECOM",     "mc":"LARGE", "div":2.8},
    {"t":"IDEA",     "yf":"IDEA.NS",     "n":"Vodafone Idea Ltd",             "p":14,   "ch":-1.42, "lo":9,    "hi":22,   "pe":None, "sg":"SELL", "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"TELECOM",     "mc":"MID",   "div":0.0},

    # Capital Goods & Engineering
    {"t":"SIEMENS",  "yf":"SIEMENS.NS",  "n":"Siemens Ltd",                  "p":6842, "ch":0.48,  "lo":4842, "hi":7982, "pe":68.4, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"CAPITAL_GOODS","mc":"MID",  "div":0.4},
    {"t":"ABB",      "yf":"ABB.NS",      "n":"ABB India Ltd",                 "p":6642, "ch":0.62,  "lo":4842, "hi":8142, "pe":72.6, "sg":"BUY",  "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"CAPITAL_GOODS","mc":"MID",  "div":0.2},
    {"t":"BHEL",     "yf":"BHEL.NS",     "n":"Bharat Heavy Electricals",      "p":242,  "ch":0.84,  "lo":148,  "hi":342,  "pe":42.4, "sg":"BUY",  "c":"#16a34a", "w":0, "ex":"BOTH", "sec":"CAPITAL_GOODS","mc":"LARGE","div":0.4},
    {"t":"CUMMINSIND","yf":"CUMMINSIND.NS","n":"Cummins India Ltd",           "p":3242, "ch":0.44,  "lo":2282, "hi":4082, "pe":42.8, "sg":"BUY",  "c":"#b45309", "w":0, "ex":"BOTH", "sec":"CAPITAL_GOODS","mc":"MID",  "div":1.4},
    {"t":"HAVELLS",  "yf":"HAVELLS.NS",  "n":"Havells India Ltd",             "p":1682, "ch":0.36,  "lo":1182, "hi":2042, "pe":52.4, "sg":"BUY",  "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"CAPITAL_GOODS","mc":"MID",  "div":0.8},

    # Consumer Discretionary & Retail
    {"t":"TITAN",    "yf":"TITAN.NS",    "n":"Titan Company Ltd",             "p":3342, "ch":0.52,  "lo":2442, "hi":3882, "pe":82.4, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"CONSUMER",    "mc":"LARGE", "div":0.4},
    {"t":"NYKAA",    "yf":"NYKAA.NS",    "n":"FSN E-Commerce (Nykaa)",        "p":182,  "ch":1.22,  "lo":118,  "hi":248,  "pe":None, "sg":"HOLD", "c":"#db2777", "w":0, "ex":"BOTH", "sec":"CONSUMER",    "mc":"MID",   "div":0.0},
    {"t":"DMART",    "yf":"DMART.NS",    "n":"Avenue Supermarts (D-Mart)",    "p":3742, "ch":0.28,  "lo":3082, "hi":5042, "pe":84.6, "sg":"HOLD", "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"CONSUMER",    "mc":"LARGE", "div":0.0},
    {"t":"ZOMATO",   "yf":"ZOMATO.NS",   "n":"Zomato Ltd",                    "p":228,  "ch":1.64,  "lo":128,  "hi":298,  "pe":None, "sg":"BUY",  "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"CONSUMER",    "mc":"LARGE", "div":0.0},
    {"t":"PAYTM",    "yf":"PAYTM.NS",    "n":"One 97 Communications (Paytm)","p":642,  "ch":-0.48, "lo":312,  "hi":998,  "pe":None, "sg":"HOLD", "c":"#0a7c4e", "w":0, "ex":"BOTH", "sec":"FINTECH",     "mc":"MID",   "div":0.0},
    {"t":"POLICYBZR","yf":"POLICYBZR.NS","n":"PB Fintech (PolicyBazaar)",     "p":1642, "ch":1.08,  "lo":882,  "hi":1982, "pe":None, "sg":"BUY",  "c":"#9333ea", "w":0, "ex":"BOTH", "sec":"FINTECH",     "mc":"MID",   "div":0.0},

    # Indices & ETFs (NSE)
    {"t":"NIFTYBEES","yf":"NIFTYBEES.NS","n":"Nippon Nifty BeES ETF",        "p":242,  "ch":0.38,  "lo":186,  "hi":266,  "pe":None, "sg":"BUY",  "c":"#1d4ed8", "w":0, "ex":"NSE",  "sec":"ETF",         "mc":"LARGE", "div":0.8},
    {"t":"JUNIORBEES","yf":"JUNIORBEES.NS","n":"Nippon Junior BeES ETF",     "p":698,  "ch":0.42,  "lo":524,  "hi":788,  "pe":None, "sg":"BUY",  "c":"#7c3aed", "w":0, "ex":"NSE",  "sec":"ETF",         "mc":"MID",   "div":0.4},
    {"t":"GOLDBEES", "yf":"GOLDBEES.NS", "n":"Nippon Gold BeES ETF",         "p":58,   "ch":0.18,  "lo":44,   "hi":66,   "pe":None, "sg":"HOLD", "c":"#b45309", "w":0, "ex":"NSE",  "sec":"ETF",         "mc":"LARGE", "div":0.0},
    {"t":"SETFNIF50","yf":"SETFNIF50.NS","n":"SBI Nifty 50 ETF",             "p":242,  "ch":0.36,  "lo":186,  "hi":268,  "pe":None, "sg":"BUY",  "c":"#16a34a", "w":0, "ex":"NSE",  "sec":"ETF",         "mc":"LARGE", "div":0.8},

    # Conglomerates / Adani Group
    {"t":"ADANIENT", "yf":"ADANIENT.NS", "n":"Adani Enterprises Ltd",        "p":2442, "ch":0.82,  "lo":1642, "hi":3242, "pe":48.4, "sg":"HOLD", "c":"#e11d48", "w":0, "ex":"BOTH", "sec":"CONGLOMERATE","mc":"LARGE", "div":0.1},
    {"t":"ADANIPORTS","yf":"ADANIPORTS.NS","n":"Adani Ports & SEZ",           "p":1242, "ch":0.54,  "lo":842,  "hi":1482, "pe":22.4, "sg":"BUY",  "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"INFRA",       "mc":"LARGE", "div":0.4},

    # Tata Group
    {"t":"TATACHEM", "yf":"TATACHEM.NS", "n":"Tata Chemicals Ltd",           "p":1042, "ch":-0.28, "lo":824,  "hi":1342, "pe":24.8, "sg":"HOLD", "c":"#1d4ed8", "w":0, "ex":"BOTH", "sec":"CHEMICALS",   "mc":"MID",   "div":1.4},
    {"t":"TATAELXSI","yf":"TATAELXSI.NS","n":"Tata Elxsi Ltd",               "p":6842, "ch":0.48,  "lo":5282, "hi":8842, "pe":42.8, "sg":"HOLD", "c":"#0891b2", "w":0, "ex":"BOTH", "sec":"IT",          "mc":"MID",   "div":1.2},
    {"t":"TATACOMM", "yf":"TATACOMM.NS", "n":"Tata Communications Ltd",      "p":1742, "ch":0.34,  "lo":1328, "hi":2248, "pe":38.4, "sg":"HOLD", "c":"#16a34a", "w":0, "ex":"BOTH", "sec":"TELECOM",     "mc":"MID",   "div":1.8},
    {"t":"TITAN",    "yf":"TITAN.NS",    "n":"Titan Company Ltd",             "p":3342, "ch":0.52,  "lo":2442, "hi":3882, "pe":82.4, "sg":"BUY",  "c":"#7c3aed", "w":0, "ex":"BOTH", "sec":"CONSUMER",    "mc":"LARGE", "div":0.4},
]

# Remove duplicates (Titan appears twice — dedup by ticker)
_seen = set()
_deduped = []
for s in INDIAN_UNIVERSE:
    if s["t"] not in _seen:
        _seen.add(s["t"])
        _deduped.append(s)
INDIAN_UNIVERSE = _deduped


# ── Curated Indian sector portfolios ─────────────────────────────────────────
def _pick(tickers: list[str], weights: list[int]) -> list[dict]:
    """Return stocks from INDIAN_UNIVERSE matching tickers, with weights assigned."""
    idx = {s["t"]: s for s in INDIAN_UNIVERSE}
    result = []
    for t, w in zip(tickers, weights):
        if t in idx:
            stock = dict(idx[t])   # copy so we don't mutate the universe
            stock["w"] = w
            result.append(stock)
    return result

HD_INDIA = {
    # ── Nifty 50 balanced blue-chip ──────────────────────────────────────────
    "nifty50": _pick(
        ["RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","LT","SBIN","AXISBANK",
         "BAJFINANCE","HINDUNILVR","NTPC","MARUTI","SUNPHARMA","BHARTIARTL","ITC",
         "KOTAKBANK","M&M","TATAMOTORS","HCLTECH","TITAN"],
        [10,9,8,7,7,6,5,5,4,4,4,4,4,3,3,3,3,3,3,3]
    ),

    # ── Indian IT sector ─────────────────────────────────────────────────────
    "india_it": _pick(
        ["TCS","INFY","HCLTECH","WIPRO","TECHM","LTIM","PERSISTENT","COFORGE",
         "MPHASIS","OFSS","TATAELXSI"],
        [22,18,14,10,8,8,6,6,4,2,2]
    ),

    # ── Indian Banking & Finance ──────────────────────────────────────────────
    "india_banking": _pick(
        ["HDFCBANK","ICICIBANK","SBIN","AXISBANK","KOTAKBANK","BAJFINANCE",
         "BAJAJFINSV","INDUSINDBK","FEDERALBNK","BANKBARODA","LICI","SBILIFE",
         "CHOLAFIN","MUTHOOTFIN","PNB"],
        [18,15,12,10,8,7,5,5,4,3,3,3,2,2,3]
    ),

    # ── Indian Energy & PSU ───────────────────────────────────────────────────
    "india_energy": _pick(
        ["RELIANCE","NTPC","POWERGRID","ONGC","BPCL","GAIL","IOC","ADANIGREEN",
         "ADANIPOWER","TATAPOWER","HINDPETRO","PETRONET","COALINDIA"],
        [22,12,10,8,7,7,6,6,5,5,4,4,4]
    ),

    # ── Indian Pharma & Healthcare ────────────────────────────────────────────
    "india_pharma": _pick(
        ["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP","LUPIN",
         "TORNTPHARM","AUROPHARMA","BIOCON"],
        [22,18,16,12,10,8,6,5,3]
    ),

    # ── Indian Auto sector ────────────────────────────────────────────────────
    "india_auto": _pick(
        ["MARUTI","TATAMOTORS","M&M","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT",
         "TVSMOTORS","ASHOKLEY","BALKRISIND"],
        [22,18,15,12,10,8,6,5,4]
    ),

    # ── Indian FMCG ───────────────────────────────────────────────────────────
    "india_fmcg": _pick(
        ["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","MARICO",
         "GODREJCP","COLPAL","EMAMILTD"],
        [22,18,14,12,10,8,6,6,4]
    ),

    # ── Metals & Mining ───────────────────────────────────────────────────────
    "india_metals": _pick(
        ["JSWSTEEL","TATASTEEL","HINDALCO","VEDL","NMDC","COALINDIA",
         "SAIL","JINDALSTEL"],
        [22,18,16,12,10,8,8,6]
    ),

    # ── Infrastructure & Real Estate ─────────────────────────────────────────
    "india_infra": _pick(
        ["LT","ULTRACEMCO","ADANIPORTS","GRASIM","SHREECEM","ACC",
         "AMBUJACEMENT","DLF","GODREJPROP","BHEL"],
        [20,14,12,10,8,8,8,8,6,6]
    ),

    # ── Dividend income ───────────────────────────────────────────────────────
    "india_dividend": _pick(
        ["COALINDIA","IOC","ONGC","BPCL","HINDPETRO","GAIL","VEDL",
         "NMDC","BANKBARODA","CANBK","NIFTYBEES","GOLDBEES","ITC","PNB"],
        [12,10,10,8,8,7,7,6,6,5,5,4,4,8]
    ),

    # ── New-age / Growth / Tech startups ─────────────────────────────────────
    "india_newage": _pick(
        ["ZOMATO","NYKAA","PAYTM","POLICYBZR","ADANIGREEN","ADANIENT",
         "TATAPOWER","PERSISTENT","COFORGE","BHARTIARTL"],
        [15,12,10,10,12,10,8,8,8,7]
    ),

    # ── Midcap value ──────────────────────────────────────────────────────────
    "india_midcap": _pick(
        ["CHOLAFIN","MUTHOOTFIN","SHRIRAMFIN","FEDERALBNK","MPHASIS",
         "PERSISTENT","COFORGE","TORNTPHARM","AUROPHARMA","CUMMINSIND",
         "HAVELLS","BALKRISIND","PRESTIGE","GODREJPROP","TORNTPOWER"],
        [8,7,7,6,6,6,6,6,6,6,6,6,6,6,7]
    ),

    # ── Small & defensive (PSU + dividend) ───────────────────────────────────
    "india_defensive": _pick(
        ["COALINDIA","NTPC","POWERGRID","ONGC","GAIL","NIFTYBEES",
         "GOLDBEES","SBIN","LICI","NMDC","CESC","BHARTIARTL","ITC"],
        [10,10,9,8,8,8,7,7,7,7,7,6,6]
    ),
}

# ── Combined lookup ─────────────────────────────────────────────────────────
HD = {**HD_US, **HD_INDIA}

# ─────────────────────────────────────────────────────────────────────────────
#  API ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "CreditWise ML API v2"})


@app.route("/api/stocks", methods=["GET"])
def stocks():
    sector    = request.args.get("sector", "balanced").lower()
    live      = request.args.get("live", "false").lower() == "true"
    data      = HD.get(sector, HD["balanced"])

    if live and _YF_AVAILABLE:
        enriched = []
        for s in data:
            yf_ticker = s.get("yf", s["t"] + ".NS")
            quote = _live_price(yf_ticker)
            if quote:
                s = {**s, **quote}   # overlay live p and ch
            enriched.append(s)
        data = enriched

    return jsonify({"stocks": data, "sector": sector,
                    "currency": "INR" if sector.startswith("india_") or sector in
                    ("nifty50",) else "USD",
                    "live": live and _YF_AVAILABLE})


@app.route("/api/stocks/search", methods=["GET"])
def search_stocks():
    """Search NSE/BSE universe by ticker or name fragment."""
    q      = request.args.get("q", "").upper()
    sector = request.args.get("sector", "").upper()
    mc     = request.args.get("mc", "").upper()       # LARGE | MID | SMALL
    ex     = request.args.get("ex", "").upper()       # NSE | BSE | BOTH
    limit  = int(request.args.get("limit", 50))

    results = INDIAN_UNIVERSE
    if q:
        results = [s for s in results if q in s["t"] or q in s["n"].upper()]
    if sector:
        results = [s for s in results if s.get("sec","").upper() == sector]
    if mc:
        results = [s for s in results if s.get("mc","").upper() == mc]
    if ex:
        results = [s for s in results if ex in s.get("ex","BOTH")]

    return jsonify({"results": results[:limit], "total": len(results)})


@app.route("/api/stocks/sectors", methods=["GET"])
def list_sectors():
    """Return all available portfolio keys and Indian sector list."""
    indian_sectors = sorted(set(s["sec"] for s in INDIAN_UNIVERSE))
    portfolios = sorted(HD.keys())
    return jsonify({
        "portfolios": portfolios,
        "indian_sectors": indian_sectors,
        "universe_size": len(INDIAN_UNIVERSE),
    })


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


# ─────────────────────────────────────────────────────────────────────────────
#  GROQ AI ANALYSIS  (unchanged from original)
# ─────────────────────────────────────────────────────────────────────────────
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
        headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                 "Content-Type": "application/json"},
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
        currency = "₹" if sector.startswith("india_") or sector == "nifty50" else "$"
        holdings_text = "\n".join(
            f"  - {s['t']} ({s['n']}): {currency}{s['p']:,.0f} | P/E {s['pe']} "
            f"| Signal {s['sg']} | Weight {s['w']}%"
            for s in stocks
        )
        prompt = (
            f"Portfolio: {sector} sector, {horizon} horizon, {currency}{amount:,} invested.\n"
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
        currency = "₹" if sector.startswith("india_") or sector == "nifty50" else "$"
        holdings_text = "\n".join(
            f"  - {s['t']} ({s['n']}): {currency}{s['p']:,.0f} "
            f"| P/E {s['pe']} | Signal {s['sg']}"
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
