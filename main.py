import os
import requests as http_requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from model import predict_loan

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
#  LIVE PRICE HELPER  (yfinance — optional, degrades to static data)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False


def _live_price(ticker_ns: str) -> dict | None:
    if not _YF_AVAILABLE:
        return None
    try:
        t      = yf.Ticker(ticker_ns)
        info   = t.fast_info
        price  = round(info.last_price, 2)
        prev   = info.previous_close
        change = round((price - prev) / prev * 100, 2) if prev else 0.0
        return {"p": price, "ch": change}
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  US PORTFOLIO DATA
# ─────────────────────────────────────────────────────────────────────────────
HD_US = {
    "balanced": [
        {"t":"SPY",   "n":"SPDR S&P 500 ETF",       "p":562.84,"ch":0.42, "lo":430, "hi":580, "pe":22.4,"sg":"BUY", "c":"#2563eb","w":20},
        {"t":"QQQ",   "n":"Invesco NASDAQ 100",      "p":481.20,"ch":0.68, "lo":360, "hi":510, "pe":28.1,"sg":"BUY", "c":"#7c3aed","w":15},
        {"t":"MSFT",  "n":"Microsoft Corp",          "p":420.34,"ch":-0.18,"lo":310, "hi":450, "pe":35.2,"sg":"BUY", "c":"#0891b2","w":10},
        {"t":"AAPL",  "n":"Apple Inc",               "p":228.64,"ch":0.89, "lo":165, "hi":240, "pe":31.4,"sg":"BUY", "c":"#64748b","w":8},
        {"t":"NVDA",  "n":"NVIDIA Corp",             "p":886.20,"ch":1.82, "lo":450, "hi":1000,"pe":62.4,"sg":"BUY", "c":"#16a34a","w":7},
        {"t":"VTI",   "n":"Vanguard Total Market",   "p":244.50,"ch":0.31, "lo":195, "hi":258, "pe":21.8,"sg":"HOLD","c":"#0a7c4e","w":12},
        {"t":"BND",   "n":"Vanguard Bond ETF",       "p":73.42, "ch":-0.05,"lo":68,  "hi":78,  "pe":None,"sg":"HOLD","c":"#94a3b8","w":10},
        {"t":"GLD",   "n":"SPDR Gold Trust",         "p":238.44,"ch":0.44, "lo":175, "hi":255, "pe":None,"sg":"BUY", "c":"#b45309","w":5},
        {"t":"VNQ",   "n":"Vanguard Real Estate",    "p":88.20, "ch":0.22, "lo":72,  "hi":98,  "pe":18.6,"sg":"HOLD","c":"#db2777","w":8},
        {"t":"GOOGL", "n":"Alphabet Inc",            "p":183.20,"ch":0.12, "lo":130, "hi":198, "pe":24.8,"sg":"HOLD","c":"#9333ea","w":5},
    ],
    "tech": [
        {"t":"QQQ",  "n":"Invesco NASDAQ 100",     "p":481.20,"ch":0.68, "lo":360,"hi":510, "pe":28.1,"sg":"BUY", "c":"#7c3aed","w":22},
        {"t":"NVDA", "n":"NVIDIA Corp",            "p":886.20,"ch":1.82, "lo":450,"hi":1000,"pe":62.4,"sg":"BUY", "c":"#16a34a","w":18},
        {"t":"MSFT", "n":"Microsoft Corp",         "p":420.34,"ch":-0.18,"lo":310,"hi":450, "pe":35.2,"sg":"BUY", "c":"#0891b2","w":15},
        {"t":"AAPL", "n":"Apple Inc",              "p":228.64,"ch":0.89, "lo":165,"hi":240, "pe":31.4,"sg":"BUY", "c":"#64748b","w":12},
        {"t":"META", "n":"Meta Platforms",         "p":528.10,"ch":1.22, "lo":380,"hi":560, "pe":26.8,"sg":"BUY", "c":"#2563eb","w":10},
        {"t":"GOOGL","n":"Alphabet Inc",           "p":183.20,"ch":0.12, "lo":130,"hi":198, "pe":24.8,"sg":"HOLD","c":"#9333ea","w":8},
        {"t":"AMD",  "n":"Advanced Micro Devices", "p":162.44,"ch":2.14, "lo":100,"hi":220, "pe":48.2,"sg":"BUY", "c":"#e11d48","w":7},
        {"t":"SMH",  "n":"VanEck Semiconductor",   "p":222.60,"ch":1.44, "lo":160,"hi":245, "pe":32.6,"sg":"BUY", "c":"#b45309","w":8},
    ],
    "dividend": [
        {"t":"VYM", "n":"Vanguard High Dividend","p":122.30,"ch":0.18, "lo":100,"hi":130,"pe":15.2,"sg":"BUY", "c":"#0a7c4e","w":20},
        {"t":"SCHD","n":"Schwab US Dividend",    "p":82.40, "ch":0.22, "lo":70, "hi":90, "pe":14.8,"sg":"BUY", "c":"#2563eb","w":18},
        {"t":"JNJ", "n":"Johnson & Johnson",     "p":158.20,"ch":-0.08,"lo":140,"hi":175,"pe":16.4,"sg":"HOLD","c":"#b45309","w":12},
        {"t":"PG",  "n":"Procter & Gamble",      "p":166.80,"ch":0.14, "lo":148,"hi":178,"pe":25.8,"sg":"HOLD","c":"#7c3aed","w":10},
        {"t":"KO",  "n":"Coca-Cola",             "p":64.20, "ch":0.08, "lo":55, "hi":70, "pe":23.2,"sg":"HOLD","c":"#e11d48","w":10},
        {"t":"O",   "n":"Realty Income",         "p":54.60, "ch":0.32, "lo":45, "hi":62, "pe":42.8,"sg":"BUY", "c":"#db2777","w":8},
        {"t":"VZ",  "n":"Verizon",               "p":40.20, "ch":0.12, "lo":32, "hi":46, "pe":10.2,"sg":"HOLD","c":"#0891b2","w":8},
        {"t":"BND", "n":"Vanguard Bond ETF",     "p":73.42, "ch":-0.05,"lo":68, "hi":78, "pe":None,"sg":"HOLD","c":"#94a3b8","w":14},
    ],
    "growth": [
        {"t":"VUG",  "n":"Vanguard Growth ETF",  "p":338.20,"ch":0.52, "lo":268,"hi":360, "pe":32.1,"sg":"BUY", "c":"#2563eb","w":18},
        {"t":"NVDA", "n":"NVIDIA Corp",          "p":886.20,"ch":1.82, "lo":450,"hi":1000,"pe":62.4,"sg":"BUY", "c":"#16a34a","w":16},
        {"t":"TSLA", "n":"Tesla Inc",            "p":177.80,"ch":2.44, "lo":140,"hi":280, "pe":44.2,"sg":"BUY", "c":"#e11d48","w":14},
        {"t":"AMZN", "n":"Amazon.com",           "p":195.40,"ch":0.88, "lo":145,"hi":210, "pe":38.6,"sg":"BUY", "c":"#b45309","w":12},
        {"t":"META", "n":"Meta Platforms",       "p":528.10,"ch":1.22, "lo":380,"hi":560, "pe":26.8,"sg":"BUY", "c":"#0891b2","w":10},
        {"t":"MSFT", "n":"Microsoft Corp",       "p":420.34,"ch":-0.18,"lo":310,"hi":450, "pe":35.2,"sg":"BUY", "c":"#7c3aed","w":10},
        {"t":"CRWD", "n":"CrowdStrike Holdings", "p":368.40,"ch":1.64, "lo":220,"hi":400, "pe":72.4,"sg":"BUY", "c":"#db2777","w":8},
        {"t":"SHOP", "n":"Shopify Inc",          "p":84.20, "ch":1.08, "lo":60, "hi":100, "pe":68.2,"sg":"HOLD","c":"#9333ea","w":7},
    ],
    "defensive": [
        {"t":"VPU","n":"Vanguard Utilities ETF", "p":158.40,"ch":-0.12,"lo":130,"hi":168,"pe":18.4,"sg":"HOLD","c":"#2563eb","w":18},
        {"t":"XLP","n":"Consumer Staples SPDR",  "p":82.60, "ch":0.08, "lo":70, "hi":88, "pe":20.2,"sg":"HOLD","c":"#7c3aed","w":16},
        {"t":"XLV","n":"Health Care SPDR",       "p":148.20,"ch":0.22, "lo":128,"hi":162,"pe":17.8,"sg":"BUY", "c":"#0891b2","w":14},
        {"t":"JNJ","n":"Johnson & Johnson",      "p":158.20,"ch":-0.08,"lo":140,"hi":175,"pe":16.4,"sg":"HOLD","c":"#16a34a","w":10},
        {"t":"BND","n":"Vanguard Bond ETF",      "p":73.42, "ch":-0.05,"lo":68, "hi":78, "pe":None,"sg":"HOLD","c":"#94a3b8","w":14},
        {"t":"GLD","n":"SPDR Gold Trust",        "p":238.44,"ch":0.44, "lo":175,"hi":255,"pe":None,"sg":"BUY", "c":"#b45309","w":10},
        {"t":"PG", "n":"Procter & Gamble",       "p":166.80,"ch":0.14, "lo":148,"hi":178,"pe":25.8,"sg":"HOLD","c":"#0a7c4e","w":10},
        {"t":"NEE","n":"NextEra Energy",         "p":72.40, "ch":0.18, "lo":58, "hi":82, "pe":22.4,"sg":"HOLD","c":"#db2777","w":8},
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
#  INDIAN STOCK MANUAL DATASET — NSE / BSE
#  ~500 stocks across 25+ sectors  |  all prices in INR (₹)
#
#  Fields:
#    t   = NSE ticker        yf  = yfinance symbol (.NS / .BO)
#    n   = Company name      p   = Price ₹        ch  = Day % chg
#    lo  = 52-wk low ₹       hi  = 52-wk high ₹   pe  = P/E ratio
#    sg  = BUY/HOLD/SELL     c   = chart colour    w   = portfolio weight
#    ex  = NSE|BSE|BOTH      sec = sector tag      mc  = LARGE|MID|SMALL
#    div = dividend yield %
# ─────────────────────────────────────────────────────────────────────────────

INDIAN_UNIVERSE = [

    # ══════════════════════════════════════════════════════════════════════════
    #  INFORMATION TECHNOLOGY
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"TCS",        "yf":"TCS.NS",        "n":"Tata Consultancy Services",      "p":3842,  "ch":0.34,  "lo":3056, "hi":4592, "pe":28.4, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"BOTH","sec":"IT","mc":"LARGE","div":1.8},
    {"t":"INFY",       "yf":"INFY.NS",       "n":"Infosys Ltd",                    "p":1482,  "ch":-0.21, "lo":1218, "hi":1964, "pe":22.6, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"IT","mc":"LARGE","div":2.4},
    {"t":"WIPRO",      "yf":"WIPRO.NS",      "n":"Wipro Ltd",                      "p":462,   "ch":0.44,  "lo":380,  "hi":584,  "pe":18.8, "sg":"HOLD", "c":"#7c3aed","w":0,"ex":"BOTH","sec":"IT","mc":"LARGE","div":0.2},
    {"t":"HCLTECH",    "yf":"HCLTECH.NS",    "n":"HCL Technologies Ltd",           "p":1542,  "ch":0.62,  "lo":1236, "hi":1996, "pe":24.2, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"IT","mc":"LARGE","div":3.2},
    {"t":"TECHM",      "yf":"TECHM.NS",      "n":"Tech Mahindra Ltd",              "p":1282,  "ch":1.04,  "lo":988,  "hi":1762, "pe":26.8, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"IT","mc":"LARGE","div":1.6},
    {"t":"LTIM",       "yf":"LTIM.NS",       "n":"LTIMindtree Ltd",                "p":5124,  "ch":0.88,  "lo":4286, "hi":6767, "pe":32.4, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"IT","mc":"LARGE","div":0.8},
    {"t":"MPHASIS",    "yf":"MPHASIS.NS",    "n":"Mphasis Ltd",                    "p":2486,  "ch":0.56,  "lo":1912, "hi":3044, "pe":28.6, "sg":"HOLD", "c":"#9333ea","w":0,"ex":"BOTH","sec":"IT","mc":"MID",  "div":1.4},
    {"t":"PERSISTENT", "yf":"PERSISTENT.NS", "n":"Persistent Systems Ltd",         "p":4862,  "ch":1.24,  "lo":3788, "hi":6142, "pe":48.2, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"IT","mc":"MID",  "div":0.4},
    {"t":"COFORGE",    "yf":"COFORGE.NS",    "n":"Coforge Ltd",                    "p":7242,  "ch":0.96,  "lo":4982, "hi":9184, "pe":42.6, "sg":"BUY",  "c":"#b45309","w":0,"ex":"BOTH","sec":"IT","mc":"MID",  "div":0.6},
    {"t":"OFSS",       "yf":"OFSS.NS",       "n":"Oracle Financial Services",      "p":9124,  "ch":0.28,  "lo":6842, "hi":10288,"pe":34.8, "sg":"HOLD", "c":"#64748b","w":0,"ex":"BOTH","sec":"IT","mc":"MID",  "div":2.2},
    {"t":"TATAELXSI",  "yf":"TATAELXSI.NS",  "n":"Tata Elxsi Ltd",                 "p":6842,  "ch":0.48,  "lo":5282, "hi":8842, "pe":42.8, "sg":"HOLD", "c":"#0891b2","w":0,"ex":"BOTH","sec":"IT","mc":"MID",  "div":1.2},
    {"t":"KPITTECH",   "yf":"KPITTECH.NS",   "n":"KPIT Technologies Ltd",          "p":1482,  "ch":1.12,  "lo":982,  "hi":1842, "pe":58.4, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"BOTH","sec":"IT","mc":"MID",  "div":0.4},
    {"t":"LTTS",       "yf":"LTTS.NS",       "n":"L&T Technology Services",        "p":4642,  "ch":0.68,  "lo":3682, "hi":5842, "pe":38.6, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"IT","mc":"MID",  "div":1.2},
    {"t":"HEXAWARE",   "yf":"HEXAWARE.NS",   "n":"Hexaware Technologies Ltd",      "p":862,   "ch":0.44,  "lo":668,  "hi":1082, "pe":32.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"IT","mc":"MID",  "div":1.6},
    {"t":"NIITTECH",   "yf":"NIITTECH.NS",   "n":"NIIT Technologies Ltd",          "p":4242,  "ch":0.36,  "lo":3182, "hi":5142, "pe":28.6, "sg":"HOLD", "c":"#e11d48","w":0,"ex":"BOTH","sec":"IT","mc":"MID",  "div":1.8},
    {"t":"CYIENT",     "yf":"CYIENT.NS",     "n":"Cyient Ltd",                     "p":1682,  "ch":0.54,  "lo":1182, "hi":2282, "pe":22.4, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"IT","mc":"MID",  "div":2.2},
    {"t":"MASTEK",     "yf":"MASTEK.NS",     "n":"Mastek Ltd",                     "p":2442,  "ch":0.82,  "lo":1682, "hi":3082, "pe":18.8, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"IT","mc":"SMALL","div":1.4},
    {"t":"RATEGAIN",   "yf":"RATEGAIN.NS",   "n":"RateGain Travel Technologies",   "p":682,   "ch":1.24,  "lo":442,  "hi":982,  "pe":48.6, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"NSE", "sec":"IT","mc":"SMALL","div":0.0},
    {"t":"ZENSAR",     "yf":"ZENSAR.NS",     "n":"Zensar Technologies Ltd",        "p":682,   "ch":0.44,  "lo":482,  "hi":882,  "pe":18.4, "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"IT","mc":"SMALL","div":1.6},
    {"t":"INFOEDGE",   "yf":"NAUKRI.NS",     "n":"Info Edge India (Naukri)",       "p":6842,  "ch":0.84,  "lo":4642, "hi":7942, "pe":88.4, "sg":"BUY",  "c":"#64748b","w":0,"ex":"BOTH","sec":"IT","mc":"MID",  "div":0.2},
    {"t":"INDIAMART",  "yf":"INDIAMART.NS",  "n":"IndiaMART InterMESH Ltd",        "p":2442,  "ch":0.62,  "lo":1842, "hi":3642, "pe":42.8, "sg":"HOLD", "c":"#2563eb","w":0,"ex":"NSE", "sec":"IT","mc":"MID",  "div":0.4},

    # ══════════════════════════════════════════════════════════════════════════
    #  BANKING — PUBLIC SECTOR
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"SBIN",       "yf":"SBIN.NS",       "n":"State Bank of India",            "p":782,   "ch":-0.32, "lo":607,  "hi":912,  "pe":10.2, "sg":"BUY",  "c":"#15803d","w":0,"ex":"BOTH","sec":"PSU_BANK","mc":"LARGE","div":1.8},
    {"t":"PNB",        "yf":"PNB.NS",        "n":"Punjab National Bank",           "p":102,   "ch":0.28,  "lo":80,   "hi":142,  "pe":8.6,  "sg":"HOLD", "c":"#94a3b8","w":0,"ex":"BOTH","sec":"PSU_BANK","mc":"LARGE","div":1.2},
    {"t":"BANKBARODA", "yf":"BANKBARODA.NS", "n":"Bank of Baroda",                 "p":228,   "ch":0.44,  "lo":182,  "hi":298,  "pe":7.2,  "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"PSU_BANK","mc":"LARGE","div":2.6},
    {"t":"CANBK",      "yf":"CANBK.NS",      "n":"Canara Bank",                    "p":98,    "ch":0.62,  "lo":78,   "hi":128,  "pe":6.4,  "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"PSU_BANK","mc":"LARGE","div":2.8},
    {"t":"UNIONBANK",  "yf":"UNIONBANK.NS",  "n":"Union Bank of India",            "p":118,   "ch":0.38,  "lo":88,   "hi":168,  "pe":7.8,  "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"PSU_BANK","mc":"LARGE","div":2.4},
    {"t":"INDIANB",    "yf":"INDIANB.NS",    "n":"Indian Bank",                    "p":548,   "ch":0.54,  "lo":398,  "hi":682,  "pe":8.2,  "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"PSU_BANK","mc":"MID",  "div":2.2},
    {"t":"MAHABANK",   "yf":"MAHABANK.NS",   "n":"Bank of Maharashtra",            "p":56,    "ch":0.36,  "lo":42,   "hi":72,   "pe":9.4,  "sg":"BUY",  "c":"#2563eb","w":0,"ex":"BOTH","sec":"PSU_BANK","mc":"MID",  "div":2.6},
    {"t":"BANKINDIA",  "yf":"BANKINDIA.NS",  "n":"Bank of India",                  "p":112,   "ch":0.28,  "lo":82,   "hi":148,  "pe":8.8,  "sg":"HOLD", "c":"#0891b2","w":0,"ex":"BOTH","sec":"PSU_BANK","mc":"MID",  "div":2.0},
    {"t":"CENTRALBK",  "yf":"CENTRALBK.NS",  "n":"Central Bank of India",          "p":54,    "ch":0.44,  "lo":38,   "hi":76,   "pe":10.2, "sg":"HOLD", "c":"#7c3aed","w":0,"ex":"BOTH","sec":"PSU_BANK","mc":"MID",  "div":1.8},
    {"t":"UCOBANK",    "yf":"UCOBANK.NS",    "n":"UCO Bank",                       "p":42,    "ch":0.48,  "lo":28,   "hi":62,   "pe":12.4, "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"PSU_BANK","mc":"SMALL","div":1.2},
    {"t":"IOB",        "yf":"IOB.NS",        "n":"Indian Overseas Bank",           "p":48,    "ch":0.42,  "lo":32,   "hi":68,   "pe":14.6, "sg":"HOLD", "c":"#16a34a","w":0,"ex":"BOTH","sec":"PSU_BANK","mc":"SMALL","div":1.0},

    # ══════════════════════════════════════════════════════════════════════════
    #  BANKING — PRIVATE SECTOR
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"HDFCBANK",   "yf":"HDFCBANK.NS",   "n":"HDFC Bank Ltd",                  "p":1642,  "ch":0.18,  "lo":1407, "hi":1880, "pe":18.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"LARGE","div":1.2},
    {"t":"ICICIBANK",  "yf":"ICICIBANK.NS",  "n":"ICICI Bank Ltd",                 "p":1224,  "ch":0.42,  "lo":986,  "hi":1362, "pe":17.6, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"LARGE","div":0.8},
    {"t":"AXISBANK",   "yf":"AXISBANK.NS",   "n":"Axis Bank Ltd",                  "p":1124,  "ch":0.56,  "lo":886,  "hi":1340, "pe":14.8, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"LARGE","div":0.1},
    {"t":"KOTAKBANK",  "yf":"KOTAKBANK.NS",  "n":"Kotak Mahindra Bank",            "p":1786,  "ch":-0.14, "lo":1543, "hi":2162, "pe":20.4, "sg":"HOLD", "c":"#e11d48","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"LARGE","div":0.1},
    {"t":"INDUSINDBK", "yf":"INDUSINDBK.NS", "n":"IndusInd Bank Ltd",              "p":964,   "ch":-0.84, "lo":771,  "hi":1694, "pe":9.4,  "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"LARGE","div":1.4},
    {"t":"YESBANK",    "yf":"YESBANK.NS",    "n":"Yes Bank Ltd",                   "p":18,    "ch":-0.56, "lo":12,   "hi":28,   "pe":22.4, "sg":"HOLD", "c":"#94a3b8","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"LARGE","div":0.0},
    {"t":"FEDERALBNK", "yf":"FEDERALBNK.NS", "n":"Federal Bank Ltd",               "p":182,   "ch":0.38,  "lo":138,  "hi":218,  "pe":11.2, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"MID",  "div":0.8},
    {"t":"IDFCFIRSTB", "yf":"IDFCFIRSTB.NS", "n":"IDFC First Bank",                "p":68,    "ch":-0.58, "lo":52,   "hi":98,   "pe":18.4, "sg":"HOLD", "c":"#64748b","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"MID",  "div":0.0},
    {"t":"RBLBANK",    "yf":"RBLBANK.NS",    "n":"RBL Bank Ltd",                   "p":182,   "ch":0.44,  "lo":138,  "hi":264,  "pe":12.8, "sg":"HOLD", "c":"#2563eb","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"MID",  "div":0.6},
    {"t":"KARNATAKABK","yf":"KTKBANK.NS",    "n":"Karnataka Bank Ltd",             "p":182,   "ch":0.38,  "lo":142,  "hi":248,  "pe":8.4,  "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"SMALL","div":2.4},
    {"t":"CSBBANK",    "yf":"CSBBANK.NS",    "n":"CSB Bank Ltd",                   "p":322,   "ch":0.44,  "lo":242,  "hi":422,  "pe":14.6, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"SMALL","div":0.8},
    {"t":"DCBBANK",    "yf":"DCBBANK.NS",    "n":"DCB Bank Ltd",                   "p":112,   "ch":0.28,  "lo":88,   "hi":148,  "pe":8.8,  "sg":"HOLD", "c":"#16a34a","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"SMALL","div":0.6},
    {"t":"SOUTHBANK",  "yf":"SOUTHBANK.NS",  "n":"South Indian Bank",              "p":22,    "ch":0.46,  "lo":16,   "hi":32,   "pe":10.2, "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"SMALL","div":1.2},
    {"t":"LAKSHVILAS", "yf":"LAKSHVILAS.NS", "n":"Lakshmi Vilas Bank",             "p":8,     "ch":-0.62, "lo":5,    "hi":14,   "pe":None, "sg":"SELL", "c":"#e11d48","w":0,"ex":"BOTH","sec":"PVT_BANK","mc":"SMALL","div":0.0},

    # ══════════════════════════════════════════════════════════════════════════
    #  NBFC & FINANCIAL SERVICES
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"BAJFINANCE",  "yf":"BAJFINANCE.NS",  "n":"Bajaj Finance Ltd",            "p":6842,  "ch":0.72,  "lo":5468, "hi":8192, "pe":28.6, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"NBFC","mc":"LARGE","div":0.4},
    {"t":"BAJAJFINSV",  "yf":"BAJAJFINSV.NS",  "n":"Bajaj Finserv Ltd",            "p":1684,  "ch":0.48,  "lo":1342, "hi":2042, "pe":22.4, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"NBFC","mc":"LARGE","div":0.1},
    {"t":"CHOLAFIN",    "yf":"CHOLAFIN.NS",    "n":"Cholamandalam Invest & Fin",   "p":1242,  "ch":0.84,  "lo":862,  "hi":1542, "pe":26.8, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"NBFC","mc":"MID",  "div":0.2},
    {"t":"MUTHOOTFIN",  "yf":"MUTHOOTFIN.NS",  "n":"Muthoot Finance Ltd",          "p":1924,  "ch":0.36,  "lo":1286, "hi":2148, "pe":14.4, "sg":"BUY",  "c":"#b45309","w":0,"ex":"BOTH","sec":"NBFC","mc":"MID",  "div":1.4},
    {"t":"LICHSGFIN",   "yf":"LICHSGFIN.NS",   "n":"LIC Housing Finance",          "p":624,   "ch":-0.22, "lo":462,  "hi":782,  "pe":8.6,  "sg":"HOLD", "c":"#16a34a","w":0,"ex":"BOTH","sec":"NBFC","mc":"MID",  "div":1.8},
    {"t":"SHRIRAMFIN",  "yf":"SHRIRAMFIN.NS",  "n":"Shriram Finance Ltd",          "p":2642,  "ch":0.62,  "lo":2042, "hi":3124, "pe":15.2, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"NBFC","mc":"MID",  "div":0.8},
    {"t":"MANAPPURAM",  "yf":"MANAPPURAM.NS",  "n":"Manappuram Finance Ltd",       "p":182,   "ch":0.44,  "lo":128,  "hi":228,  "pe":10.4, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"NBFC","mc":"MID",  "div":2.2},
    {"t":"RECLTD",      "yf":"RECLTD.NS",      "n":"REC Ltd",                      "p":528,   "ch":0.62,  "lo":348,  "hi":654,  "pe":8.4,  "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"NBFC","mc":"LARGE","div":3.8},
    {"t":"PFC",         "yf":"PFC.NS",         "n":"Power Finance Corporation",    "p":448,   "ch":0.58,  "lo":282,  "hi":580,  "pe":7.2,  "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"NBFC","mc":"LARGE","div":3.6},
    {"t":"IRFC",        "yf":"IRFC.NS",        "n":"Indian Railway Finance Corp",  "p":172,   "ch":0.44,  "lo":112,  "hi":228,  "pe":18.4, "sg":"BUY",  "c":"#64748b","w":0,"ex":"BOTH","sec":"NBFC","mc":"MID",  "div":1.2},
    {"t":"M&MFIN",      "yf":"M&MFIN.NS",      "n":"Mahindra & Mahindra Fin Serv", "p":282,   "ch":0.38,  "lo":218,  "hi":382,  "pe":18.6, "sg":"HOLD", "c":"#2563eb","w":0,"ex":"BOTH","sec":"NBFC","mc":"MID",  "div":1.6},
    {"t":"SUNDARMFIN",  "yf":"SUNDARMFIN.NS",  "n":"Sundaram Finance Ltd",         "p":4282,  "ch":0.28,  "lo":3282, "hi":5082, "pe":22.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"NBFC","mc":"MID",  "div":0.8},
    {"t":"ABCAPITAL",   "yf":"ABCAPITAL.NS",   "n":"Aditya Birla Capital Ltd",     "p":182,   "ch":0.54,  "lo":142,  "hi":242,  "pe":14.6, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"NBFC","mc":"MID",  "div":0.4},
    {"t":"AAVAS",       "yf":"AAVAS.NS",       "n":"Aavas Financiers Ltd",         "p":1642,  "ch":0.44,  "lo":1282, "hi":2142, "pe":28.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"NBFC","mc":"MID",  "div":0.0},
    {"t":"HOMEFIRST",   "yf":"HOMEFIRST.NS",   "n":"Home First Finance Company",   "p":982,   "ch":0.62,  "lo":742,  "hi":1282, "pe":24.6, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"NSE", "sec":"NBFC","mc":"SMALL","div":0.0},

    # ══════════════════════════════════════════════════════════════════════════
    #  INSURANCE
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"LICI",       "yf":"LICI.NS",       "n":"Life Insurance Corp of India",  "p":924,   "ch":0.28,  "lo":724,  "hi":1222, "pe":13.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"INSURANCE","mc":"LARGE","div":1.2},
    {"t":"SBILIFE",    "yf":"SBILIFE.NS",    "n":"SBI Life Insurance",            "p":1542,  "ch":0.14,  "lo":1228, "hi":1964, "pe":68.4, "sg":"HOLD", "c":"#15803d","w":0,"ex":"BOTH","sec":"INSURANCE","mc":"LARGE","div":0.2},
    {"t":"HDFCLIFE",   "yf":"HDFCLIFE.NS",   "n":"HDFC Life Insurance",           "p":642,   "ch":0.32,  "lo":511,  "hi":786,  "pe":82.4, "sg":"HOLD", "c":"#0891b2","w":0,"ex":"BOTH","sec":"INSURANCE","mc":"LARGE","div":0.3},
    {"t":"ICICIPRULI", "yf":"ICICIPRULI.NS", "n":"ICICI Prudential Life",         "p":682,   "ch":0.44,  "lo":524,  "hi":842,  "pe":72.6, "sg":"HOLD", "c":"#7c3aed","w":0,"ex":"BOTH","sec":"INSURANCE","mc":"MID",  "div":0.4},
    {"t":"GICRE",      "yf":"GICRE.NS",      "n":"General Insurance Corp",        "p":382,   "ch":-0.18, "lo":284,  "hi":462,  "pe":12.4, "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"INSURANCE","mc":"MID",  "div":2.4},
    {"t":"NIACL",      "yf":"NIACL.NS",      "n":"New India Assurance Co",        "p":192,   "ch":0.22,  "lo":148,  "hi":248,  "pe":18.6, "sg":"HOLD", "c":"#16a34a","w":0,"ex":"BOTH","sec":"INSURANCE","mc":"MID",  "div":1.6},
    {"t":"ICICIGI",    "yf":"ICICIGI.NS",    "n":"ICICI Lombard General Ins",     "p":1842,  "ch":0.38,  "lo":1442, "hi":2242, "pe":38.4, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"INSURANCE","mc":"MID",  "div":0.6},
    {"t":"STARHEALTH", "yf":"STARHEALTH.NS", "n":"Star Health & Allied Ins",      "p":542,   "ch":0.28,  "lo":412,  "hi":742,  "pe":48.6, "sg":"HOLD", "c":"#db2777","w":0,"ex":"NSE", "sec":"INSURANCE","mc":"MID",  "div":0.0},

    # ══════════════════════════════════════════════════════════════════════════
    #  ENERGY & OIL
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"RELIANCE",   "yf":"RELIANCE.NS",   "n":"Reliance Industries Ltd",       "p":2842,  "ch":0.62,  "lo":2228, "hi":3217, "pe":24.8, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"ENERGY","mc":"LARGE","div":0.4},
    {"t":"ONGC",       "yf":"ONGC.NS",       "n":"Oil & Natural Gas Corp",        "p":268,   "ch":-0.42, "lo":186,  "hi":344,  "pe":7.4,  "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"ENERGY","mc":"LARGE","div":4.8},
    {"t":"IOC",        "yf":"IOC.NS",        "n":"Indian Oil Corporation",        "p":142,   "ch":-0.28, "lo":108,  "hi":196,  "pe":6.2,  "sg":"HOLD", "c":"#64748b","w":0,"ex":"BOTH","sec":"ENERGY","mc":"LARGE","div":5.6},
    {"t":"BPCL",       "yf":"BPCL.NS",       "n":"Bharat Petroleum Corp",        "p":312,   "ch":0.18,  "lo":236,  "hi":388,  "pe":8.4,  "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"ENERGY","mc":"LARGE","div":4.2},
    {"t":"HINDPETRO",  "yf":"HINDPETRO.NS",  "n":"Hindustan Petroleum Corp",     "p":372,   "ch":0.36,  "lo":268,  "hi":458,  "pe":7.8,  "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"ENERGY","mc":"LARGE","div":3.8},
    {"t":"GAIL",       "yf":"GAIL.NS",       "n":"GAIL India Ltd",               "p":208,   "ch":0.48,  "lo":154,  "hi":246,  "pe":11.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"ENERGY","mc":"LARGE","div":2.8},
    {"t":"PETRONET",   "yf":"PETRONET.NS",   "n":"Petronet LNG Ltd",             "p":302,   "ch":0.22,  "lo":228,  "hi":362,  "pe":12.8, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"ENERGY","mc":"MID",  "div":3.2},
    {"t":"OIL",        "yf":"OIL.NS",        "n":"Oil India Ltd",                "p":542,   "ch":0.38,  "lo":368,  "hi":698,  "pe":9.4,  "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"ENERGY","mc":"MID",  "div":3.6},
    {"t":"MRPL",       "yf":"MRPL.NS",       "n":"Mangalore Refinery & Petro",   "p":182,   "ch":0.44,  "lo":128,  "hi":248,  "pe":8.6,  "sg":"HOLD", "c":"#2563eb","w":0,"ex":"BOTH","sec":"ENERGY","mc":"MID",  "div":2.4},
    {"t":"CHENNPETRO", "yf":"CHENNPETRO.NS", "n":"Chennai Petroleum Corp Ltd",   "p":682,   "ch":0.28,  "lo":482,  "hi":848,  "pe":6.8,  "sg":"HOLD", "c":"#0891b2","w":0,"ex":"BOTH","sec":"ENERGY","mc":"SMALL","div":4.2},
    {"t":"GULFOILLUB", "yf":"GULFOILLUB.NS", "n":"Gulf Oil Lubricants India",    "p":942,   "ch":0.36,  "lo":682,  "hi":1142, "pe":22.4, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"NSE", "sec":"ENERGY","mc":"SMALL","div":2.8},

    # ══════════════════════════════════════════════════════════════════════════
    #  POWER & UTILITIES
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"NTPC",       "yf":"NTPC.NS",       "n":"NTPC Ltd",                     "p":362,   "ch":0.54,  "lo":264,  "hi":428,  "pe":16.2, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"POWER","mc":"LARGE","div":2.6},
    {"t":"POWERGRID",  "yf":"POWERGRID.NS",  "n":"Power Grid Corp of India",     "p":314,   "ch":0.38,  "lo":228,  "hi":368,  "pe":18.4, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"POWER","mc":"LARGE","div":3.8},
    {"t":"ADANIGREEN", "yf":"ADANIGREEN.NS", "n":"Adani Green Energy Ltd",       "p":1624,  "ch":1.24,  "lo":826,  "hi":2144, "pe":148.4,"sg":"HOLD", "c":"#16a34a","w":0,"ex":"BOTH","sec":"POWER","mc":"LARGE","div":0.0},
    {"t":"ADANIPOWER", "yf":"ADANIPOWER.NS", "n":"Adani Power Ltd",              "p":582,   "ch":0.68,  "lo":386,  "hi":798,  "pe":8.2,  "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"POWER","mc":"LARGE","div":0.0},
    {"t":"TATAPOWER",  "yf":"TATAPOWER.NS",  "n":"Tata Power Co Ltd",            "p":378,   "ch":0.82,  "lo":268,  "hi":462,  "pe":28.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"POWER","mc":"MID",  "div":0.6},
    {"t":"TORNTPOWER", "yf":"TORNTPOWER.NS", "n":"Torrent Power Ltd",            "p":1424,  "ch":0.44,  "lo":1068, "hi":1842, "pe":22.6, "sg":"BUY",  "c":"#b45309","w":0,"ex":"BOTH","sec":"POWER","mc":"MID",  "div":1.2},
    {"t":"CESC",       "yf":"CESC.NS",       "n":"CESC Ltd",                     "p":168,   "ch":-0.12, "lo":128,  "hi":208,  "pe":12.4, "sg":"HOLD", "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"POWER","mc":"MID",  "div":2.4},
    {"t":"NHPC",       "yf":"NHPC.NS",       "n":"NHPC Ltd",                     "p":82,    "ch":0.36,  "lo":62,   "hi":112,  "pe":14.2, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"POWER","mc":"MID",  "div":3.2},
    {"t":"SJVN",       "yf":"SJVN.NS",       "n":"SJVN Ltd",                     "p":118,   "ch":0.44,  "lo":82,   "hi":168,  "pe":22.4, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"POWER","mc":"MID",  "div":2.8},
    {"t":"RPOWER",     "yf":"RPOWER.NS",     "n":"Reliance Power Ltd",           "p":28,    "ch":-0.36, "lo":14,   "hi":42,   "pe":None, "sg":"SELL", "c":"#64748b","w":0,"ex":"BOTH","sec":"POWER","mc":"SMALL","div":0.0},
    {"t":"JPPOWER",    "yf":"JPPOWER.NS",    "n":"Jaiprakash Power Ventures",    "p":18,    "ch":0.28,  "lo":12,   "hi":26,   "pe":None, "sg":"SELL", "c":"#94a3b8","w":0,"ex":"BOTH","sec":"POWER","mc":"SMALL","div":0.0},
    {"t":"GREENPWR",   "yf":"GREENPWR.NS",   "n":"Green Power International",    "p":42,    "ch":0.48,  "lo":28,   "hi":62,   "pe":28.4, "sg":"HOLD", "c":"#16a34a","w":0,"ex":"NSE", "sec":"POWER","mc":"SMALL","div":0.0},
    {"t":"INDIAGRID",  "yf":"INDIAGRID.NS",  "n":"IndiGrid InvIT",               "p":142,   "ch":0.18,  "lo":112,  "hi":168,  "pe":None, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"NSE", "sec":"POWER","mc":"MID",  "div":8.4},

    # ══════════════════════════════════════════════════════════════════════════
    #  METALS & MINING
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"TATASTEEL",  "yf":"TATASTEEL.NS",  "n":"Tata Steel Ltd",               "p":142,   "ch":-0.84, "lo":108,  "hi":184,  "pe":12.6, "sg":"HOLD", "c":"#64748b","w":0,"ex":"BOTH","sec":"METALS","mc":"LARGE","div":2.8},
    {"t":"JSWSTEEL",   "yf":"JSWSTEEL.NS",   "n":"JSW Steel Ltd",                "p":882,   "ch":0.42,  "lo":682,  "hi":1062, "pe":14.8, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"METALS","mc":"LARGE","div":1.6},
    {"t":"HINDALCO",   "yf":"HINDALCO.NS",   "n":"Hindalco Industries",          "p":628,   "ch":0.28,  "lo":462,  "hi":758,  "pe":11.4, "sg":"BUY",  "c":"#b45309","w":0,"ex":"BOTH","sec":"METALS","mc":"LARGE","div":0.6},
    {"t":"VEDL",       "yf":"VEDL.NS",       "n":"Vedanta Ltd",                  "p":448,   "ch":-0.62, "lo":222,  "hi":526,  "pe":9.8,  "sg":"HOLD", "c":"#e11d48","w":0,"ex":"BOTH","sec":"METALS","mc":"LARGE","div":8.4},
    {"t":"NMDC",       "yf":"NMDC.NS",       "n":"NMDC Ltd",                     "p":216,   "ch":0.38,  "lo":162,  "hi":268,  "pe":9.2,  "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"METALS","mc":"LARGE","div":4.2},
    {"t":"COALINDIA",  "yf":"COALINDIA.NS",  "n":"Coal India Ltd",               "p":442,   "ch":-0.28, "lo":338,  "hi":542,  "pe":7.8,  "sg":"HOLD", "c":"#94a3b8","w":0,"ex":"BOTH","sec":"METALS","mc":"LARGE","div":5.8},
    {"t":"SAIL",       "yf":"SAIL.NS",       "n":"Steel Authority of India",     "p":128,   "ch":-0.48, "lo":88,   "hi":172,  "pe":11.2, "sg":"HOLD", "c":"#7c3aed","w":0,"ex":"BOTH","sec":"METALS","mc":"LARGE","div":2.2},
    {"t":"JINDALSTEL", "yf":"JINDALSTEL.NS", "n":"Jindal Steel & Power",         "p":882,   "ch":0.64,  "lo":608,  "hi":1068, "pe":12.8, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"METALS","mc":"MID",  "div":0.6},
    {"t":"JSWENERGY",  "yf":"JSWENERGY.NS",  "n":"JSW Energy Ltd",               "p":542,   "ch":0.44,  "lo":342,  "hi":692,  "pe":28.4, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"METALS","mc":"MID",  "div":0.6},
    {"t":"MOIL",       "yf":"MOIL.NS",       "n":"MOIL Ltd",                     "p":382,   "ch":0.36,  "lo":262,  "hi":482,  "pe":16.4, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"METALS","mc":"SMALL","div":2.8},
    {"t":"NATIONALUM", "yf":"NATIONALUM.NS", "n":"National Aluminium Co",        "p":182,   "ch":0.28,  "lo":128,  "hi":248,  "pe":12.4, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"BOTH","sec":"METALS","mc":"MID",  "div":3.8},
    {"t":"RATNAMANI",  "yf":"RATNAMANI.NS",  "n":"Ratnamani Metals & Tubes",     "p":3242,  "ch":0.42,  "lo":2482, "hi":4282, "pe":28.6, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"NSE", "sec":"METALS","mc":"SMALL","div":0.6},
    {"t":"APL",        "yf":"APL.NS",        "n":"APL Apollo Tubes Ltd",         "p":1642,  "ch":0.54,  "lo":1142, "hi":2142, "pe":38.4, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"NSE", "sec":"METALS","mc":"MID",  "div":0.4},
    {"t":"HINDZINC",   "yf":"HINDZINC.NS",   "n":"Hindustan Zinc Ltd",           "p":342,   "ch":-0.28, "lo":242,  "hi":428,  "pe":14.6, "sg":"HOLD", "c":"#16a34a","w":0,"ex":"BOTH","sec":"METALS","mc":"LARGE","div":4.8},

    # ══════════════════════════════════════════════════════════════════════════
    #  AUTOMOBILES
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"MARUTI",     "yf":"MARUTI.NS",     "n":"Maruti Suzuki India",          "p":11842, "ch":0.44,  "lo":9048, "hi":13680,"pe":26.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"AUTO","mc":"LARGE","div":1.0},
    {"t":"TATAMOTORS", "yf":"TATAMOTORS.NS", "n":"Tata Motors Ltd",              "p":782,   "ch":0.88,  "lo":564,  "hi":1064, "pe":8.2,  "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"AUTO","mc":"LARGE","div":0.0},
    {"t":"M&M",        "yf":"M&M.NS",        "n":"Mahindra & Mahindra",          "p":2842,  "ch":0.72,  "lo":1688, "hi":3264, "pe":26.8, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"AUTO","mc":"LARGE","div":0.6},
    {"t":"BAJAJ-AUTO", "yf":"BAJAJ-AUTO.NS", "n":"Bajaj Auto Ltd",               "p":8642,  "ch":0.38,  "lo":6248, "hi":10148,"pe":22.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"AUTO","mc":"LARGE","div":1.6},
    {"t":"HEROMOTOCO", "yf":"HEROMOTOCO.NS", "n":"Hero MotoCorp Ltd",            "p":4682,  "ch":0.28,  "lo":3428, "hi":5842, "pe":18.4, "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"AUTO","mc":"LARGE","div":2.4},
    {"t":"EICHERMOT",  "yf":"EICHERMOT.NS",  "n":"Eicher Motors Ltd",            "p":4242,  "ch":0.52,  "lo":3128, "hi":5128, "pe":28.6, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"AUTO","mc":"LARGE","div":0.8},
    {"t":"TVSMOTORS",  "yf":"TVSMOTORS.NS",  "n":"TVS Motor Company",            "p":2242,  "ch":0.68,  "lo":1742, "hi":2842, "pe":42.4, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"AUTO","mc":"MID",  "div":0.6},
    {"t":"ASHOKLEY",   "yf":"ASHOKLEY.NS",   "n":"Ashok Leyland Ltd",            "p":228,   "ch":0.44,  "lo":168,  "hi":286,  "pe":18.8, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"AUTO","mc":"MID",  "div":2.2},
    {"t":"BALKRISIND", "yf":"BALKRISIND.NS", "n":"Balkrishna Industries",        "p":2842,  "ch":0.38,  "lo":2128, "hi":3242, "pe":28.4, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"AUTO","mc":"MID",  "div":0.6},
    {"t":"MOTHERSON",  "yf":"MOTHERSON.NS",  "n":"Samvardhana Motherson Intl",   "p":142,   "ch":0.62,  "lo":98,   "hi":198,  "pe":28.6, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"BOTH","sec":"AUTO","mc":"LARGE","div":0.6},
    {"t":"BOSCHLTD",   "yf":"BOSCHLTD.NS",   "n":"Bosch Ltd",                    "p":32842, "ch":0.24,  "lo":24842,"hi":38842,"pe":38.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"AUTO","mc":"LARGE","div":0.6},
    {"t":"BHARATFORG", "yf":"BHARATFORG.NS", "n":"Bharat Forge Ltd",             "p":1282,  "ch":0.44,  "lo":942,  "hi":1682, "pe":38.6, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"AUTO","mc":"MID",  "div":0.6},
    {"t":"MINDAIND",   "yf":"MINDAIND.NS",   "n":"Minda Industries Ltd",         "p":1042,  "ch":0.58,  "lo":782,  "hi":1382, "pe":38.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"AUTO","mc":"MID",  "div":0.4},
    {"t":"SUNDRMFAST", "yf":"SUNDRMFAST.NS", "n":"Sundram Fasteners Ltd",        "p":1142,  "ch":0.34,  "lo":882,  "hi":1442, "pe":28.6, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"AUTO","mc":"MID",  "div":0.8},
    {"t":"EXIDEIND",   "yf":"EXIDEIND.NS",   "n":"Exide Industries Ltd",         "p":382,   "ch":0.28,  "lo":282,  "hi":482,  "pe":28.4, "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"AUTO","mc":"MID",  "div":0.6},
    {"t":"AMARAJABAT", "yf":"AMARAJABAT.NS", "n":"Amara Raja Energy & Mobility", "p":1082,  "ch":0.44,  "lo":782,  "hi":1382, "pe":22.4, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"AUTO","mc":"MID",  "div":0.8},

    # ══════════════════════════════════════════════════════════════════════════
    #  PHARMACEUTICALS & HEALTHCARE
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"SUNPHARMA",  "yf":"SUNPHARMA.NS",  "n":"Sun Pharmaceutical Ind",       "p":1682,  "ch":0.42,  "lo":1148, "hi":1788, "pe":32.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"PHARMA","mc":"LARGE","div":0.8},
    {"t":"DRREDDY",    "yf":"DRREDDY.NS",    "n":"Dr. Reddy's Laboratories",     "p":5842,  "ch":0.28,  "lo":4682, "hi":7284, "pe":18.8, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"PHARMA","mc":"LARGE","div":0.4},
    {"t":"CIPLA",      "yf":"CIPLA.NS",      "n":"Cipla Ltd",                    "p":1382,  "ch":0.64,  "lo":1042, "hi":1688, "pe":24.2, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"PHARMA","mc":"LARGE","div":0.4},
    {"t":"DIVISLAB",   "yf":"DIVISLAB.NS",   "n":"Divi's Laboratories",          "p":4842,  "ch":0.82,  "lo":3528, "hi":5842, "pe":54.8, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"PHARMA","mc":"LARGE","div":0.4},
    {"t":"BIOCON",     "yf":"BIOCON.NS",     "n":"Biocon Ltd",                   "p":288,   "ch":-0.42, "lo":212,  "hi":364,  "pe":48.4, "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"PHARMA","mc":"MID",  "div":0.2},
    {"t":"TORNTPHARM", "yf":"TORNTPHARM.NS", "n":"Torrent Pharmaceuticals",      "p":2842,  "ch":0.36,  "lo":2128, "hi":3442, "pe":38.6, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"PHARMA","mc":"MID",  "div":0.6},
    {"t":"AUROPHARMA", "yf":"AUROPHARMA.NS", "n":"Aurobindo Pharma Ltd",         "p":1182,  "ch":0.44,  "lo":842,  "hi":1442, "pe":16.4, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"PHARMA","mc":"MID",  "div":0.4},
    {"t":"LUPIN",      "yf":"LUPIN.NS",      "n":"Lupin Ltd",                    "p":1842,  "ch":0.62,  "lo":1242, "hi":2248, "pe":22.8, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"PHARMA","mc":"MID",  "div":0.6},
    {"t":"APOLLOHOSP", "yf":"APOLLOHOSP.NS", "n":"Apollo Hospitals Enterprise",  "p":6642,  "ch":0.84,  "lo":4982, "hi":7542, "pe":82.4, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"HEALTHCARE","mc":"LARGE","div":0.2},
    {"t":"ALKEM",      "yf":"ALKEM.NS",      "n":"Alkem Laboratories Ltd",       "p":4842,  "ch":0.38,  "lo":3642, "hi":5842, "pe":22.6, "sg":"BUY",  "c":"#64748b","w":0,"ex":"BOTH","sec":"PHARMA","mc":"MID",  "div":0.6},
    {"t":"IPCALAB",    "yf":"IPCALAB.NS",    "n":"IPCA Laboratories Ltd",        "p":1542,  "ch":0.44,  "lo":1082, "hi":1942, "pe":28.4, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"BOTH","sec":"PHARMA","mc":"MID",  "div":0.4},
    {"t":"GLENMARK",   "yf":"GLENMARK.NS",   "n":"Glenmark Pharmaceuticals",     "p":1242,  "ch":0.62,  "lo":842,  "hi":1582, "pe":22.8, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"PHARMA","mc":"MID",  "div":0.4},
    {"t":"NATCOPHARM", "yf":"NATCOPHARM.NS", "n":"Natco Pharma Ltd",             "p":1442,  "ch":0.44,  "lo":982,  "hi":1842, "pe":18.4, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"PHARMA","mc":"SMALL","div":0.6},
    {"t":"GRANULES",   "yf":"GRANULES.NS",   "n":"Granules India Ltd",           "p":542,   "ch":0.36,  "lo":382,  "hi":682,  "pe":18.2, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"NSE", "sec":"PHARMA","mc":"SMALL","div":0.4},
    {"t":"LAURUSLABS",  "yf":"LAURUSLABS.NS", "n":"Laurus Labs Ltd",              "p":482,   "ch":0.48,  "lo":342,  "hi":642,  "pe":28.4, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"NSE", "sec":"PHARMA","mc":"MID",  "div":0.4},
    {"t":"MAXHEALTH",  "yf":"MAXHEALTH.NS",  "n":"Max Healthcare Institute",     "p":942,   "ch":0.72,  "lo":682,  "hi":1142, "pe":68.4, "sg":"BUY",  "c":"#db2777","w":0,"ex":"NSE", "sec":"HEALTHCARE","mc":"MID",  "div":0.0},
    {"t":"METROPOLIS", "yf":"METROPOLIS.NS", "n":"Metropolis Healthcare Ltd",    "p":1542,  "ch":0.44,  "lo":1142, "hi":2042, "pe":42.6, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"NSE", "sec":"HEALTHCARE","mc":"SMALL","div":0.6},
    {"t":"THYROCARE",  "yf":"THYROCARE.NS",  "n":"Thyrocare Technologies Ltd",   "p":642,   "ch":0.38,  "lo":442,  "hi":842,  "pe":28.4, "sg":"HOLD", "c":"#0a7c4e","w":0,"ex":"NSE", "sec":"HEALTHCARE","mc":"SMALL","div":0.8},

    # ══════════════════════════════════════════════════════════════════════════
    #  FMCG & CONSUMER GOODS
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"HINDUNILVR", "yf":"HINDUNILVR.NS", "n":"Hindustan Unilever Ltd",       "p":2342,  "ch":-0.18, "lo":2082, "hi":2924, "pe":52.4, "sg":"HOLD", "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"FMCG","mc":"LARGE","div":1.8},
    {"t":"ITC",        "yf":"ITC.NS",        "n":"ITC Ltd",                      "p":468,   "ch":0.28,  "lo":382,  "hi":542,  "pe":28.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"FMCG","mc":"LARGE","div":2.4},
    {"t":"NESTLEIND",  "yf":"NESTLEIND.NS",  "n":"Nestle India Ltd",             "p":2242,  "ch":-0.14, "lo":1988, "hi":2682, "pe":68.4, "sg":"HOLD", "c":"#e11d48","w":0,"ex":"BOTH","sec":"FMCG","mc":"LARGE","div":1.4},
    {"t":"BRITANNIA",  "yf":"BRITANNIA.NS",  "n":"Britannia Industries",         "p":4842,  "ch":0.18,  "lo":4082, "hi":6042, "pe":48.4, "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"FMCG","mc":"LARGE","div":1.6},
    {"t":"DABUR",      "yf":"DABUR.NS",      "n":"Dabur India Ltd",              "p":512,   "ch":-0.12, "lo":452,  "hi":672,  "pe":48.2, "sg":"HOLD", "c":"#0891b2","w":0,"ex":"BOTH","sec":"FMCG","mc":"LARGE","div":0.8},
    {"t":"MARICO",     "yf":"MARICO.NS",     "n":"Marico Ltd",                   "p":562,   "ch":0.22,  "lo":482,  "hi":682,  "pe":44.6, "sg":"HOLD", "c":"#7c3aed","w":0,"ex":"BOTH","sec":"FMCG","mc":"LARGE","div":1.4},
    {"t":"GODREJCP",   "yf":"GODREJCP.NS",   "n":"Godrej Consumer Products",     "p":1042,  "ch":0.38,  "lo":882,  "hi":1382, "pe":38.4, "sg":"HOLD", "c":"#9333ea","w":0,"ex":"BOTH","sec":"FMCG","mc":"LARGE","div":0.8},
    {"t":"COLPAL",     "yf":"COLPAL.NS",     "n":"Colgate-Palmolive India",      "p":2842,  "ch":0.14,  "lo":2242, "hi":3442, "pe":42.8, "sg":"HOLD", "c":"#db2777","w":0,"ex":"BOTH","sec":"FMCG","mc":"MID",  "div":1.6},
    {"t":"EMAMILTD",   "yf":"EMAMILTD.NS",   "n":"Emami Ltd",                    "p":582,   "ch":0.28,  "lo":442,  "hi":782,  "pe":28.4, "sg":"HOLD", "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"FMCG","mc":"MID",  "div":1.2},
    {"t":"TATACONSUM", "yf":"TATACONSUM.NS", "n":"Tata Consumer Products Ltd",   "p":1042,  "ch":0.44,  "lo":842,  "hi":1342, "pe":68.4, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"BOTH","sec":"FMCG","mc":"MID",  "div":0.8},
    {"t":"VBL",        "yf":"VBL.NS",        "n":"Varun Beverages Ltd",          "p":542,   "ch":0.62,  "lo":382,  "hi":688,  "pe":48.6, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"NSE", "sec":"FMCG","mc":"MID",  "div":0.4},
    {"t":"JYOTHYLAB",  "yf":"JYOTHYLAB.NS",  "n":"Jyothy Labs Ltd",              "p":382,   "ch":0.36,  "lo":282,  "hi":482,  "pe":38.4, "sg":"HOLD", "c":"#7c3aed","w":0,"ex":"BOTH","sec":"FMCG","mc":"SMALL","div":1.4},
    {"t":"PGHH",       "yf":"PGHH.NS",       "n":"Procter & Gamble Hygiene",     "p":15842, "ch":0.18,  "lo":12842,"hi":18642,"pe":58.4, "sg":"HOLD", "c":"#16a34a","w":0,"ex":"BOTH","sec":"FMCG","mc":"MID",  "div":1.8},
    {"t":"GILLETTE",   "yf":"GILLETTE.NS",   "n":"Gillette India Ltd",           "p":6842,  "ch":0.22,  "lo":5442, "hi":8242, "pe":48.6, "sg":"HOLD", "c":"#e11d48","w":0,"ex":"BOTH","sec":"FMCG","mc":"MID",  "div":1.2},

    # ══════════════════════════════════════════════════════════════════════════
    #  INFRASTRUCTURE, CEMENT & CONSTRUCTION
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"LT",         "yf":"LT.NS",         "n":"Larsen & Toubro Ltd",          "p":3642,  "ch":0.52,  "lo":2782, "hi":3964, "pe":28.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"INFRA","mc":"LARGE","div":1.0},
    {"t":"ULTRACEMCO", "yf":"ULTRACEMCO.NS", "n":"UltraTech Cement Ltd",         "p":10242, "ch":0.38,  "lo":7982, "hi":12248,"pe":32.4, "sg":"BUY",  "c":"#64748b","w":0,"ex":"BOTH","sec":"CEMENT","mc":"LARGE","div":0.6},
    {"t":"GRASIM",     "yf":"GRASIM.NS",     "n":"Grasim Industries Ltd",        "p":2642,  "ch":0.44,  "lo":1842, "hi":2982, "pe":22.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"CEMENT","mc":"LARGE","div":0.8},
    {"t":"SHREECEM",   "yf":"SHREECEM.NS",   "n":"Shree Cement Ltd",             "p":24842, "ch":0.28,  "lo":19842,"hi":29248,"pe":38.4, "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"CEMENT","mc":"LARGE","div":0.4},
    {"t":"ACC",        "yf":"ACC.NS",        "n":"ACC Ltd",                      "p":2042,  "ch":0.34,  "lo":1642, "hi":2682, "pe":18.8, "sg":"HOLD", "c":"#16a34a","w":0,"ex":"BOTH","sec":"CEMENT","mc":"MID",  "div":1.2},
    {"t":"AMBUJACEMENT","yf":"AMBUJACEMENT.NS","n":"Ambuja Cements Ltd",          "p":582,   "ch":0.44,  "lo":448,  "hi":742,  "pe":24.6, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"CEMENT","mc":"LARGE","div":0.6},
    {"t":"RAMCOCEM",   "yf":"RAMCOCEM.NS",   "n":"The Ramco Cements Ltd",        "p":882,   "ch":0.38,  "lo":682,  "hi":1082, "pe":22.4, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"CEMENT","mc":"MID",  "div":0.8},
    {"t":"JKCEMENT",   "yf":"JKCEMENT.NS",   "n":"JK Cement Ltd",               "p":3842,  "ch":0.44,  "lo":2842, "hi":4842, "pe":28.6, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"CEMENT","mc":"MID",  "div":0.8},
    {"t":"DALMIACEM",  "yf":"DALMIACEM.NS",  "n":"Dalmia Bharat Ltd",            "p":1842,  "ch":0.36,  "lo":1342, "hi":2442, "pe":22.8, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"CEMENT","mc":"MID",  "div":0.4},
    {"t":"KNRCON",     "yf":"KNRCON.NS",     "n":"KNR Constructions Ltd",        "p":242,   "ch":0.48,  "lo":182,  "hi":342,  "pe":12.4, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"NSE", "sec":"INFRA","mc":"SMALL","div":0.2},
    {"t":"NCC",        "yf":"NCC.NS",        "n":"NCC Ltd",                      "p":242,   "ch":0.62,  "lo":182,  "hi":342,  "pe":14.8, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"BOTH","sec":"INFRA","mc":"SMALL","div":1.2},
    {"t":"PNCINFRA",   "yf":"PNCINFRA.NS",   "n":"PNC Infratech Ltd",            "p":382,   "ch":0.44,  "lo":282,  "hi":482,  "pe":12.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"NSE", "sec":"INFRA","mc":"SMALL","div":0.6},
    {"t":"IRCON",      "yf":"IRCON.NS",      "n":"IRCON International Ltd",      "p":242,   "ch":0.48,  "lo":182,  "hi":342,  "pe":16.4, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"INFRA","mc":"MID",  "div":1.4},
    {"t":"RVNL",       "yf":"RVNL.NS",       "n":"Rail Vikas Nigam Ltd",         "p":382,   "ch":0.62,  "lo":242,  "hi":642,  "pe":28.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"INFRA","mc":"MID",  "div":1.6},
    {"t":"ENGINERSIN", "yf":"ENGINERSIN.NS", "n":"Engineers India Ltd",          "p":182,   "ch":0.38,  "lo":128,  "hi":242,  "pe":22.4, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"INFRA","mc":"SMALL","div":2.4},

    # ══════════════════════════════════════════════════════════════════════════
    #  REAL ESTATE
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"DLF",        "yf":"DLF.NS",        "n":"DLF Ltd",                      "p":842,   "ch":0.62,  "lo":568,  "hi":1024, "pe":42.8, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"REALTY","mc":"LARGE","div":0.4},
    {"t":"GODREJPROP", "yf":"GODREJPROP.NS", "n":"Godrej Properties Ltd",        "p":2842,  "ch":0.88,  "lo":1882, "hi":3284, "pe":68.4, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"REALTY","mc":"MID",  "div":0.0},
    {"t":"PRESTIGE",   "yf":"PRESTIGE.NS",   "n":"Prestige Estates Projects",    "p":1642,  "ch":0.72,  "lo":1148, "hi":2148, "pe":48.6, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"REALTY","mc":"MID",  "div":0.2},
    {"t":"OBEROIRLTY", "yf":"OBEROIRLTY.NS", "n":"Oberoi Realty Ltd",            "p":1842,  "ch":0.54,  "lo":1282, "hi":2242, "pe":22.4, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"REALTY","mc":"MID",  "div":0.4},
    {"t":"PHOENIXLTD", "yf":"PHOENIXLTD.NS", "n":"Phoenix Mills Ltd",            "p":1642,  "ch":0.68,  "lo":1142, "hi":2042, "pe":42.6, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"BOTH","sec":"REALTY","mc":"MID",  "div":0.4},
    {"t":"BRIGADE",    "yf":"BRIGADE.NS",    "n":"Brigade Enterprises Ltd",      "p":1142,  "ch":0.82,  "lo":782,  "hi":1542, "pe":38.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"REALTY","mc":"MID",  "div":0.4},
    {"t":"SOBHA",      "yf":"SOBHA.NS",      "n":"Sobha Ltd",                    "p":1642,  "ch":0.62,  "lo":1082, "hi":2042, "pe":42.8, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"REALTY","mc":"SMALL","div":0.4},
    {"t":"MAHLIFE",    "yf":"MAHLIFE.NS",    "n":"Mahindra Lifespace Developers", "p":542,   "ch":0.72,  "lo":382,  "hi":742,  "pe":None, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"REALTY","mc":"SMALL","div":0.0},
    {"t":"SUNTECK",    "yf":"SUNTECK.NS",    "n":"Sunteck Realty Ltd",           "p":482,   "ch":0.48,  "lo":342,  "hi":682,  "pe":28.4, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"REALTY","mc":"SMALL","div":0.4},

    # ══════════════════════════════════════════════════════════════════════════
    #  TELECOM
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"BHARTIARTL", "yf":"BHARTIARTL.NS", "n":"Bharti Airtel Ltd",            "p":1642,  "ch":0.42,  "lo":1082, "hi":1832, "pe":68.4, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"TELECOM","mc":"LARGE","div":0.4},
    {"t":"INDUSTOWER", "yf":"INDUSTOWER.NS", "n":"Indus Towers Ltd",             "p":342,   "ch":-0.28, "lo":224,  "hi":436,  "pe":16.4, "sg":"HOLD", "c":"#94a3b8","w":0,"ex":"BOTH","sec":"TELECOM","mc":"LARGE","div":2.8},
    {"t":"IDEA",       "yf":"IDEA.NS",       "n":"Vodafone Idea Ltd",            "p":14,    "ch":-1.42, "lo":9,    "hi":22,   "pe":None, "sg":"SELL", "c":"#e11d48","w":0,"ex":"BOTH","sec":"TELECOM","mc":"MID",  "div":0.0},
    {"t":"TATACOMM",   "yf":"TATACOMM.NS",   "n":"Tata Communications Ltd",      "p":1742,  "ch":0.34,  "lo":1328, "hi":2248, "pe":38.4, "sg":"HOLD", "c":"#7c3aed","w":0,"ex":"BOTH","sec":"TELECOM","mc":"MID",  "div":1.8},
    {"t":"GTLINFRA",   "yf":"GTLINFRA.NS",   "n":"GTL Infrastructure Ltd",       "p":2,     "ch":-0.50, "lo":1,    "hi":4,    "pe":None, "sg":"SELL", "c":"#94a3b8","w":0,"ex":"BOTH","sec":"TELECOM","mc":"SMALL","div":0.0},

    # ══════════════════════════════════════════════════════════════════════════
    #  CAPITAL GOODS & ENGINEERING
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"SIEMENS",    "yf":"SIEMENS.NS",    "n":"Siemens Ltd",                  "p":6842,  "ch":0.48,  "lo":4842, "hi":7982, "pe":68.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"CAPITAL_GOODS","mc":"MID",  "div":0.4},
    {"t":"ABB",        "yf":"ABB.NS",        "n":"ABB India Ltd",                "p":6642,  "ch":0.62,  "lo":4842, "hi":8142, "pe":72.6, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"CAPITAL_GOODS","mc":"MID",  "div":0.2},
    {"t":"BHEL",       "yf":"BHEL.NS",       "n":"Bharat Heavy Electricals",     "p":242,   "ch":0.84,  "lo":148,  "hi":342,  "pe":42.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"CAPITAL_GOODS","mc":"LARGE","div":0.4},
    {"t":"CUMMINSIND", "yf":"CUMMINSIND.NS", "n":"Cummins India Ltd",            "p":3242,  "ch":0.44,  "lo":2282, "hi":4082, "pe":42.8, "sg":"BUY",  "c":"#b45309","w":0,"ex":"BOTH","sec":"CAPITAL_GOODS","mc":"MID",  "div":1.4},
    {"t":"HAVELLS",    "yf":"HAVELLS.NS",    "n":"Havells India Ltd",            "p":1682,  "ch":0.36,  "lo":1182, "hi":2042, "pe":52.4, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"CAPITAL_GOODS","mc":"MID",  "div":0.8},
    {"t":"THERMAX",    "yf":"THERMAX.NS",    "n":"Thermax Ltd",                  "p":3842,  "ch":0.44,  "lo":2782, "hi":4842, "pe":58.4, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"CAPITAL_GOODS","mc":"MID",  "div":0.6},
    {"t":"GRINDWELL",  "yf":"GRINDWELL.NS",  "n":"Grindwell Norton Ltd",         "p":2042,  "ch":0.38,  "lo":1542, "hi":2542, "pe":42.4, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"CAPITAL_GOODS","mc":"SMALL","div":0.8},
    {"t":"KEC",        "yf":"KEC.NS",        "n":"KEC International Ltd",        "p":742,   "ch":0.62,  "lo":542,  "hi":942,  "pe":28.4, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"BOTH","sec":"CAPITAL_GOODS","mc":"MID",  "div":0.6},
    {"t":"KALPATPOWR", "yf":"KALPATPOWR.NS", "n":"Kalpataru Projects Intl",      "p":1042,  "ch":0.48,  "lo":742,  "hi":1342, "pe":22.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"CAPITAL_GOODS","mc":"SMALL","div":0.6},
    {"t":"SCHNEIDER",  "yf":"SCHNEIDER.NS",  "n":"Schneider Electric Infra",     "p":742,   "ch":0.54,  "lo":542,  "hi":942,  "pe":48.4, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"NSE", "sec":"CAPITAL_GOODS","mc":"SMALL","div":0.4},
    {"t":"VOLTAMP",    "yf":"VOLTAMP.NS",    "n":"Voltamp Transformers Ltd",     "p":8242,  "ch":0.36,  "lo":5842, "hi":10242,"pe":28.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"NSE", "sec":"CAPITAL_GOODS","mc":"SMALL","div":0.8},

    # ══════════════════════════════════════════════════════════════════════════
    #  CONSUMER DISCRETIONARY & RETAIL
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"TITAN",      "yf":"TITAN.NS",      "n":"Titan Company Ltd",            "p":3342,  "ch":0.52,  "lo":2442, "hi":3882, "pe":82.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"CONSUMER","mc":"LARGE","div":0.4},
    {"t":"DMART",      "yf":"DMART.NS",      "n":"Avenue Supermarts (D-Mart)",   "p":3742,  "ch":0.28,  "lo":3082, "hi":5042, "pe":84.6, "sg":"HOLD", "c":"#0891b2","w":0,"ex":"BOTH","sec":"CONSUMER","mc":"LARGE","div":0.0},
    {"t":"TRENT",      "yf":"TRENT.NS",      "n":"Trent Ltd",                    "p":5842,  "ch":0.88,  "lo":3842, "hi":7842, "pe":148.4,"sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"CONSUMER","mc":"MID",  "div":0.2},
    {"t":"RELAXO",     "yf":"RELAXO.NS",     "n":"Relaxo Footwears Ltd",         "p":842,   "ch":0.28,  "lo":642,  "hi":1142, "pe":48.4, "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"CONSUMER","mc":"MID",  "div":0.4},
    {"t":"BATA",       "yf":"BATA.NS",       "n":"Bata India Ltd",               "p":1442,  "ch":0.18,  "lo":1082, "hi":1842, "pe":42.8, "sg":"HOLD", "c":"#7c3aed","w":0,"ex":"BOTH","sec":"CONSUMER","mc":"MID",  "div":0.8},
    {"t":"CAMPUS",     "yf":"CAMPUS.NS",     "n":"Campus Activewear Ltd",        "p":282,   "ch":0.44,  "lo":182,  "hi":442,  "pe":38.6, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"NSE", "sec":"CONSUMER","mc":"SMALL","div":0.0},
    {"t":"VMART",      "yf":"VMART.NS",      "n":"V-Mart Retail Ltd",            "p":2442,  "ch":0.62,  "lo":1842, "hi":3242, "pe":68.4, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"NSE", "sec":"CONSUMER","mc":"SMALL","div":0.2},
    {"t":"KALYANKJIL", "yf":"KALYANKJIL.NS", "n":"Kalyan Jewellers India",       "p":542,   "ch":0.72,  "lo":342,  "hi":742,  "pe":42.6, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"NSE", "sec":"CONSUMER","mc":"MID",  "div":0.2},
    {"t":"SENCO",      "yf":"SENCO.NS",      "n":"Senco Gold Ltd",               "p":842,   "ch":0.48,  "lo":582,  "hi":1142, "pe":22.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"NSE", "sec":"CONSUMER","mc":"SMALL","div":0.4},
    {"t":"SHOPPERSSTOP","yf":"SHOPERSTOP.NS","n":"Shoppers Stop Ltd",             "p":742,   "ch":0.38,  "lo":542,  "hi":1042, "pe":None, "sg":"HOLD", "c":"#7c3aed","w":0,"ex":"BOTH","sec":"CONSUMER","mc":"SMALL","div":0.0},
    {"t":"PAGEIND",    "yf":"PAGEIND.NS",    "n":"Page Industries Ltd",          "p":38842, "ch":0.24,  "lo":32842,"hi":48842,"pe":68.4, "sg":"HOLD", "c":"#16a34a","w":0,"ex":"BOTH","sec":"CONSUMER","mc":"MID",  "div":1.2},
    {"t":"WHIRLPOOL",  "yf":"WHIRLPOOL.NS",  "n":"Whirlpool of India Ltd",       "p":1442,  "ch":-0.22, "lo":1082, "hi":2042, "pe":42.4, "sg":"HOLD", "c":"#e11d48","w":0,"ex":"BOTH","sec":"CONSUMER","mc":"MID",  "div":0.6},
    {"t":"VOLTAS",     "yf":"VOLTAS.NS",     "n":"Voltas Ltd",                   "p":1542,  "ch":0.44,  "lo":1082, "hi":1942, "pe":68.4, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"CONSUMER","mc":"MID",  "div":0.4},
    {"t":"CROMPTON",   "yf":"CROMPTON.NS",   "n":"Crompton Greaves Consumer",    "p":282,   "ch":0.36,  "lo":202,  "hi":382,  "pe":38.4, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"NSE", "sec":"CONSUMER","mc":"MID",  "div":0.4},
    {"t":"AMBER",      "yf":"AMBER.NS",      "n":"Amber Enterprises India",      "p":4842,  "ch":0.58,  "lo":3282, "hi":6242, "pe":48.6, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"NSE", "sec":"CONSUMER","mc":"MID",  "div":0.0},

    # ══════════════════════════════════════════════════════════════════════════
    #  NEW-AGE TECH / FINTECH / STARTUPS
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"ZOMATO",     "yf":"ZOMATO.NS",     "n":"Zomato Ltd",                   "p":228,   "ch":1.64,  "lo":128,  "hi":298,  "pe":None, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"NEWAGE","mc":"LARGE","div":0.0},
    {"t":"NYKAA",      "yf":"NYKAA.NS",      "n":"FSN E-Commerce (Nykaa)",       "p":182,   "ch":1.22,  "lo":118,  "hi":248,  "pe":None, "sg":"HOLD", "c":"#db2777","w":0,"ex":"BOTH","sec":"NEWAGE","mc":"MID",  "div":0.0},
    {"t":"PAYTM",      "yf":"PAYTM.NS",      "n":"One 97 Communications (Paytm)","p":642,   "ch":-0.48, "lo":312,  "hi":998,  "pe":None, "sg":"HOLD", "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"FINTECH","mc":"MID",  "div":0.0},
    {"t":"POLICYBZR",  "yf":"POLICYBZR.NS",  "n":"PB Fintech (PolicyBazaar)",    "p":1642,  "ch":1.08,  "lo":882,  "hi":1982, "pe":None, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"BOTH","sec":"FINTECH","mc":"MID",  "div":0.0},
    {"t":"DELHIVERY",  "yf":"DELHIVERY.NS",  "n":"Delhivery Ltd",                "p":342,   "ch":0.62,  "lo":222,  "hi":482,  "pe":None, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"NSE", "sec":"NEWAGE","mc":"MID",  "div":0.0},
    {"t":"CARTRADE",   "yf":"CARTRADE.NS",   "n":"CarTrade Tech Ltd",            "p":742,   "ch":0.88,  "lo":442,  "hi":1042, "pe":None, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"NSE", "sec":"NEWAGE","mc":"SMALL","div":0.0},
    {"t":"EASEMYTRIP", "yf":"EASEMYTRIP.NS", "n":"Easy Trip Planners Ltd",       "p":24,    "ch":1.24,  "lo":14,   "hi":42,   "pe":None, "sg":"HOLD", "c":"#7c3aed","w":0,"ex":"NSE", "sec":"NEWAGE","mc":"SMALL","div":0.0},

    # ══════════════════════════════════════════════════════════════════════════
    #  CHEMICALS & SPECIALTY
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"PIDILITIND",  "yf":"PIDILITIND.NS", "n":"Pidilite Industries Ltd",      "p":2842,  "ch":0.44,  "lo":2282, "hi":3442, "pe":82.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"CHEMICALS","mc":"LARGE","div":0.4},
    {"t":"TATACHEM",   "yf":"TATACHEM.NS",   "n":"Tata Chemicals Ltd",           "p":1042,  "ch":-0.28, "lo":824,  "hi":1342, "pe":24.8, "sg":"HOLD", "c":"#0891b2","w":0,"ex":"BOTH","sec":"CHEMICALS","mc":"MID",  "div":1.4},
    {"t":"SRF",        "yf":"SRF.NS",        "n":"SRF Ltd",                      "p":2442,  "ch":0.38,  "lo":1842, "hi":2942, "pe":28.4, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"CHEMICALS","mc":"MID",  "div":0.6},
    {"t":"NAVINFLUOR",  "yf":"NAVINFLUOR.NS", "n":"Navin Fluorine International", "p":3242,  "ch":0.48,  "lo":2442, "hi":4242, "pe":38.6, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"CHEMICALS","mc":"MID",  "div":0.4},
    {"t":"ATUL",       "yf":"ATUL.NS",       "n":"Atul Ltd",                     "p":6242,  "ch":0.32,  "lo":4842, "hi":7842, "pe":22.8, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"CHEMICALS","mc":"MID",  "div":0.4},
    {"t":"DEEPAKNITR",  "yf":"DEEPAKNITR.NS", "n":"Deepak Nitrite Ltd",           "p":2242,  "ch":0.54,  "lo":1642, "hi":2842, "pe":28.4, "sg":"BUY",  "c":"#b45309","w":0,"ex":"NSE", "sec":"CHEMICALS","mc":"MID",  "div":0.6},
    {"t":"GALAXYSURF",  "yf":"GALAXYSURF.NS", "n":"Galaxy Surfactants Ltd",       "p":3242,  "ch":0.38,  "lo":2442, "hi":4042, "pe":28.6, "sg":"BUY",  "c":"#db2777","w":0,"ex":"NSE", "sec":"CHEMICALS","mc":"SMALL","div":0.8},
    {"t":"CLEAN",      "yf":"CLEAN.NS",      "n":"Clean Science and Technology", "p":1342,  "ch":0.44,  "lo":942,  "hi":1742, "pe":42.6, "sg":"BUY",  "c":"#9333ea","w":0,"ex":"NSE", "sec":"CHEMICALS","mc":"SMALL","div":0.4},
    {"t":"FINEORG",    "yf":"FINEORG.NS",    "n":"Fine Organic Industries",      "p":4042,  "ch":0.28,  "lo":2842, "hi":5042, "pe":28.4, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"NSE", "sec":"CHEMICALS","mc":"SMALL","div":0.6},
    {"t":"VINDHYATEL",  "yf":"VINDHYATEL.NS", "n":"Vindhya Telelinks Ltd",        "p":2042,  "ch":0.38,  "lo":1542, "hi":2542, "pe":18.4, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"NSE", "sec":"CHEMICALS","mc":"SMALL","div":1.4},

    # ══════════════════════════════════════════════════════════════════════════
    #  AGROCHEMICALS & FERTILISERS
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"UPL",        "yf":"UPL.NS",        "n":"UPL Ltd",                      "p":542,   "ch":-0.38, "lo":382,  "hi":748,  "pe":None, "sg":"HOLD", "c":"#16a34a","w":0,"ex":"BOTH","sec":"AGROCHEM","mc":"LARGE","div":1.2},
    {"t":"PIIND",      "yf":"PIIND.NS",       "n":"PI Industries Ltd",             "p":3842,  "ch":0.42,  "lo":2842, "hi":4842, "pe":38.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"AGROCHEM","mc":"MID",  "div":0.4},
    {"t":"SUMICHEM",   "yf":"SUMICHEM.NS",   "n":"Sumitomo Chemical India",      "p":482,   "ch":0.36,  "lo":342,  "hi":642,  "pe":38.6, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"NSE", "sec":"AGROCHEM","mc":"MID",  "div":0.6},
    {"t":"COROMANDEL", "yf":"COROMANDEL.NS", "n":"Coromandel International",     "p":1242,  "ch":0.44,  "lo":882,  "hi":1642, "pe":18.4, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"AGROCHEM","mc":"MID",  "div":1.4},
    {"t":"CHAMBLFERT", "yf":"CHAMBLFERT.NS", "n":"Chambal Fertilisers & Chem",   "p":482,   "ch":0.28,  "lo":342,  "hi":622,  "pe":12.8, "sg":"BUY",  "c":"#b45309","w":0,"ex":"BOTH","sec":"AGROCHEM","mc":"MID",  "div":2.4},
    {"t":"GNFC",       "yf":"GNFC.NS",       "n":"Gujarat Narmada Valley Fert",  "p":682,   "ch":0.38,  "lo":482,  "hi":882,  "pe":14.2, "sg":"BUY",  "c":"#db2777","w":0,"ex":"BOTH","sec":"AGROCHEM","mc":"SMALL","div":2.8},

    # ══════════════════════════════════════════════════════════════════════════
    #  TEXTILES & APPAREL
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"PAGEIND",    "yf":"PAGEIND.NS",    "n":"Page Industries Ltd",          "p":38842, "ch":0.24,  "lo":32842,"hi":48842,"pe":68.4, "sg":"HOLD", "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"TEXTILES","mc":"MID",  "div":1.2},
    {"t":"RAYMOND",    "yf":"RAYMOND.NS",    "n":"Raymond Ltd",                  "p":1842,  "ch":0.48,  "lo":1242, "hi":2442, "pe":22.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"TEXTILES","mc":"MID",  "div":0.4},
    {"t":"WELSPUNIND", "yf":"WELSPUNIND.NS", "n":"Welspun India Ltd",            "p":182,   "ch":0.62,  "lo":128,  "hi":248,  "pe":14.8, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"TEXTILES","mc":"MID",  "div":0.8},
    {"t":"VARDHMAN",   "yf":"VARDHMAN.NS",   "n":"Vardhman Textiles Ltd",        "p":382,   "ch":0.38,  "lo":282,  "hi":482,  "pe":12.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"TEXTILES","mc":"MID",  "div":1.2},
    {"t":"SUPREMEIND", "yf":"SUPREMEIND.NS", "n":"Supreme Industries Ltd",       "p":4242,  "ch":0.44,  "lo":3042, "hi":5242, "pe":38.4, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"PLASTICS","mc":"MID",  "div":0.8},

    # ══════════════════════════════════════════════════════════════════════════
    #  HOSPITALITY, TOURISM & AVIATION
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"INDHOTEL",   "yf":"INDHOTEL.NS",   "n":"Indian Hotels Co (Taj)",       "p":582,   "ch":0.72,  "lo":382,  "hi":742,  "pe":68.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"HOSPITALITY","mc":"LARGE","div":0.4},
    {"t":"EIHOTEL",    "yf":"EIHOTEL.NS",    "n":"EIH Ltd (Oberoi Hotels)",      "p":382,   "ch":0.62,  "lo":242,  "hi":482,  "pe":58.4, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"HOSPITALITY","mc":"MID",  "div":0.4},
    {"t":"LEMONTREE",  "yf":"LEMONTREE.NS",  "n":"Lemon Tree Hotels Ltd",        "p":128,   "ch":0.78,  "lo":82,   "hi":168,  "pe":48.6, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"NSE", "sec":"HOSPITALITY","mc":"MID",  "div":0.2},
    {"t":"INTERGLOBE", "yf":"INTERGLOBE.NS", "n":"InterGlobe Aviation (IndiGo)", "p":4242,  "ch":0.62,  "lo":2842, "hi":5242, "pe":18.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"NSE", "sec":"AVIATION","mc":"LARGE","div":0.0},
    {"t":"SPICEJET",   "yf":"SPICEJET.NS",   "n":"SpiceJet Ltd",                 "p":42,    "ch":-1.24, "lo":22,   "hi":82,   "pe":None, "sg":"SELL", "c":"#e11d48","w":0,"ex":"BOTH","sec":"AVIATION","mc":"SMALL","div":0.0},

    # ══════════════════════════════════════════════════════════════════════════
    #  MEDIA & ENTERTAINMENT
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"ZEEL",       "yf":"ZEEL.NS",       "n":"Zee Entertainment Enterprises","p":142,   "ch":-0.28, "lo":108,  "hi":298,  "pe":28.4, "sg":"HOLD", "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"MEDIA","mc":"MID",  "div":0.4},
    {"t":"SUNTV",      "yf":"SUNTV.NS",      "n":"Sun TV Network Ltd",           "p":682,   "ch":0.22,  "lo":482,  "hi":882,  "pe":14.2, "sg":"HOLD", "c":"#e11d48","w":0,"ex":"BOTH","sec":"MEDIA","mc":"MID",  "div":2.8},
    {"t":"PVR",        "yf":"PVR.NS",        "n":"PVR INOX Ltd",                 "p":1442,  "ch":0.48,  "lo":982,  "hi":1982, "pe":None, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"NSE", "sec":"MEDIA","mc":"MID",  "div":0.0},
    {"t":"TIPS",       "yf":"TIPS.NS",       "n":"TIPS Music Ltd",               "p":682,   "ch":0.58,  "lo":442,  "hi":942,  "pe":28.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"NSE", "sec":"MEDIA","mc":"SMALL","div":0.4},

    # ══════════════════════════════════════════════════════════════════════════
    #  EXCHANGE & MARKET INFRASTRUCTURE
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"BSE",        "yf":"BSE.NS",        "n":"BSE Ltd",                      "p":2842,  "ch":0.62,  "lo":1642, "hi":3842, "pe":42.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"NSE", "sec":"EXCHANGE","mc":"MID",  "div":1.2},
    {"t":"MCX",        "yf":"MCX.NS",        "n":"Multi Commodity Exchange",     "p":4242,  "ch":0.44,  "lo":2842, "hi":5242, "pe":28.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"NSE", "sec":"EXCHANGE","mc":"MID",  "div":1.4},
    {"t":"CDSL",       "yf":"CDSL.NS",       "n":"Central Depository Services",  "p":1442,  "ch":0.62,  "lo":982,  "hi":1842, "pe":48.4, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"NSE", "sec":"EXCHANGE","mc":"MID",  "div":1.2},
    {"t":"CAMS",       "yf":"CAMS.NS",       "n":"Computer Age Management Serv", "p":3642,  "ch":0.44,  "lo":2642, "hi":4642, "pe":42.6, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"NSE", "sec":"EXCHANGE","mc":"MID",  "div":1.8},

    # ══════════════════════════════════════════════════════════════════════════
    #  CONGLOMERATES & ADANI / TATA / BIRLA / MAHINDRA GROUP
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"ADANIENT",   "yf":"ADANIENT.NS",   "n":"Adani Enterprises Ltd",        "p":2442,  "ch":0.82,  "lo":1642, "hi":3242, "pe":48.4, "sg":"HOLD", "c":"#e11d48","w":0,"ex":"BOTH","sec":"CONGLOMERATE","mc":"LARGE","div":0.1},
    {"t":"ADANIPORTS", "yf":"ADANIPORTS.NS", "n":"Adani Ports & SEZ",            "p":1242,  "ch":0.54,  "lo":842,  "hi":1482, "pe":22.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"INFRA","mc":"LARGE","div":0.4},
    {"t":"ADANITRANS", "yf":"ADANITRANS.NS", "n":"Adani Transmission Ltd",       "p":842,   "ch":0.62,  "lo":542,  "hi":1242, "pe":None, "sg":"HOLD", "c":"#b45309","w":0,"ex":"BOTH","sec":"POWER","mc":"LARGE","div":0.0},
    {"t":"ADANITOTAL", "yf":"ATGL.NS",       "n":"Adani Total Gas Ltd",          "p":742,   "ch":0.44,  "lo":482,  "hi":1042, "pe":68.4, "sg":"HOLD", "c":"#16a34a","w":0,"ex":"BOTH","sec":"ENERGY","mc":"MID",  "div":0.1},
    {"t":"AIAENG",     "yf":"AIAENG.NS",     "n":"AIA Engineering Ltd",          "p":3842,  "ch":0.28,  "lo":2842, "hi":4642, "pe":28.4, "sg":"BUY",  "c":"#0a7c4e","w":0,"ex":"BOTH","sec":"CAPITAL_GOODS","mc":"MID","div":0.6},

    # ══════════════════════════════════════════════════════════════════════════
    #  DEFENCE
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"HAL",        "yf":"HAL.NS",        "n":"Hindustan Aeronautics Ltd",    "p":4242,  "ch":0.84,  "lo":2842, "hi":5242, "pe":28.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"DEFENCE","mc":"LARGE","div":1.4},
    {"t":"BEL",        "yf":"BEL.NS",        "n":"Bharat Electronics Ltd",       "p":282,   "ch":0.62,  "lo":182,  "hi":342,  "pe":38.4, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"DEFENCE","mc":"LARGE","div":1.2},
    {"t":"BDL",        "yf":"BDL.NS",        "n":"Bharat Dynamics Ltd",          "p":1142,  "ch":0.72,  "lo":742,  "hi":1542, "pe":42.6, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"BOTH","sec":"DEFENCE","mc":"MID",  "div":0.8},
    {"t":"COCHINSHIP", "yf":"COCHINSHIP.NS", "n":"Cochin Shipyard Ltd",          "p":1642,  "ch":0.84,  "lo":942,  "hi":2242, "pe":28.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"DEFENCE","mc":"MID",  "div":1.4},
    {"t":"MAZAGON",    "yf":"MAZAGON.NS",    "n":"Mazagon Dock Shipbuilders",    "p":4242,  "ch":0.78,  "lo":2642, "hi":5442, "pe":22.4, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"BOTH","sec":"DEFENCE","mc":"MID",  "div":1.2},
    {"t":"DATACENT",   "yf":"DATAPATTNS.NS", "n":"Data Patterns India Ltd",      "p":2242,  "ch":0.64,  "lo":1542, "hi":3242, "pe":48.6, "sg":"BUY",  "c":"#b45309","w":0,"ex":"NSE", "sec":"DEFENCE","mc":"SMALL","div":0.4},

    # ══════════════════════════════════════════════════════════════════════════
    #  LOGISTICS & SHIPPING
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"CONCOR",     "yf":"CONCOR.NS",     "n":"Container Corp of India",      "p":742,   "ch":0.38,  "lo":542,  "hi":942,  "pe":28.4, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"BOTH","sec":"LOGISTICS","mc":"LARGE","div":1.4},
    {"t":"GESHIP",     "yf":"GESHIP.NS",     "n":"Great Eastern Shipping Co",    "p":942,   "ch":0.44,  "lo":682,  "hi":1182, "pe":6.8,  "sg":"BUY",  "c":"#0891b2","w":0,"ex":"BOTH","sec":"LOGISTICS","mc":"MID",  "div":2.8},
    {"t":"MAHLOG",     "yf":"MAHLOG.NS",     "n":"Mahindra Logistics Ltd",       "p":382,   "ch":0.48,  "lo":282,  "hi":542,  "pe":48.4, "sg":"HOLD", "c":"#7c3aed","w":0,"ex":"NSE", "sec":"LOGISTICS","mc":"SMALL","div":0.0},
    {"t":"BLUEDART",   "yf":"BLUEDART.NS",   "n":"Blue Dart Express Ltd",        "p":6842,  "ch":0.28,  "lo":5242, "hi":8242, "pe":42.4, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"BOTH","sec":"LOGISTICS","mc":"MID",  "div":0.4},
    {"t":"SNOWMAN",    "yf":"SNOWMAN.NS",    "n":"Snowman Logistics Ltd",        "p":82,    "ch":0.48,  "lo":58,   "hi":112,  "pe":38.4, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"NSE", "sec":"LOGISTICS","mc":"SMALL","div":0.4},

    # ══════════════════════════════════════════════════════════════════════════
    #  ETFs  (NSE Listed)
    # ══════════════════════════════════════════════════════════════════════════
    {"t":"NIFTYBEES",  "yf":"NIFTYBEES.NS",  "n":"Nippon Nifty BeES ETF",        "p":242,   "ch":0.38,  "lo":186,  "hi":266,  "pe":None, "sg":"BUY",  "c":"#1d4ed8","w":0,"ex":"NSE", "sec":"ETF","mc":"LARGE","div":0.8},
    {"t":"JUNIORBEES", "yf":"JUNIORBEES.NS", "n":"Nippon Junior BeES ETF",       "p":698,   "ch":0.42,  "lo":524,  "hi":788,  "pe":None, "sg":"BUY",  "c":"#7c3aed","w":0,"ex":"NSE", "sec":"ETF","mc":"MID",  "div":0.4},
    {"t":"GOLDBEES",   "yf":"GOLDBEES.NS",   "n":"Nippon Gold BeES ETF",         "p":58,    "ch":0.18,  "lo":44,   "hi":66,   "pe":None, "sg":"HOLD", "c":"#b45309","w":0,"ex":"NSE", "sec":"ETF","mc":"LARGE","div":0.0},
    {"t":"SETFNIF50",  "yf":"SETFNIF50.NS",  "n":"SBI Nifty 50 ETF",             "p":242,   "ch":0.36,  "lo":186,  "hi":268,  "pe":None, "sg":"BUY",  "c":"#16a34a","w":0,"ex":"NSE", "sec":"ETF","mc":"LARGE","div":0.8},
    {"t":"BANKBEES",   "yf":"BANKBEES.NS",   "n":"Nippon Bank BeES ETF",         "p":488,   "ch":0.28,  "lo":368,  "hi":562,  "pe":None, "sg":"BUY",  "c":"#0891b2","w":0,"ex":"NSE", "sec":"ETF","mc":"LARGE","div":0.6},
    {"t":"ICICIB22",   "yf":"ICICIB22.NS",   "n":"ICICI Pru Bharat 22 ETF",      "p":92,    "ch":0.32,  "lo":68,   "hi":108,  "pe":None, "sg":"BUY",  "c":"#e11d48","w":0,"ex":"NSE", "sec":"ETF","mc":"LARGE","div":1.2},
    {"t":"MAFANG",     "yf":"MAFANG.NS",     "n":"Mirae Asset Hang Seng ETF",    "p":42,    "ch":-0.24, "lo":28,   "hi":58,   "pe":None, "sg":"HOLD", "c":"#9333ea","w":0,"ex":"NSE", "sec":"ETF","mc":"MID",  "div":0.0},
    {"t":"SILVERBEES", "yf":"SILVERBEES.NS", "n":"Nippon Silver BeES ETF",       "p":14,    "ch":0.28,  "lo":10,   "hi":18,   "pe":None, "sg":"HOLD", "c":"#94a3b8","w":0,"ex":"NSE", "sec":"ETF","mc":"MID",  "div":0.0},
    {"t":"ITBEES",     "yf":"ITBEES.NS",     "n":"Nippon IT BeES ETF",           "p":42,    "ch":0.44,  "lo":32,   "hi":52,   "pe":None, "sg":"BUY",  "c":"#2563eb","w":0,"ex":"NSE", "sec":"ETF","mc":"MID",  "div":0.4},

]

# ── Dedup by ticker ──────────────────────────────────────────────────────────
_seen = set()
_deduped = []
for _s in INDIAN_UNIVERSE:
    if _s["t"] not in _seen:
        _seen.add(_s["t"])
        _deduped.append(_s)
INDIAN_UNIVERSE = _deduped

# ── Index for fast lookup ────────────────────────────────────────────────────
_INDIA_IDX = {s["t"]: s for s in INDIAN_UNIVERSE}


def _pick(tickers: list, weights: list) -> list:
    result = []
    for t, w in zip(tickers, weights):
        if t in _INDIA_IDX:
            stock = dict(_INDIA_IDX[t])
            stock["w"] = w
            result.append(stock)
    return result


# ── Curated Indian portfolios (18 total) ─────────────────────────────────────
HD_INDIA = {
    "nifty50": _pick(
        ["RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","LT","SBIN","AXISBANK",
         "BAJFINANCE","HINDUNILVR","NTPC","MARUTI","SUNPHARMA","BHARTIARTL","ITC",
         "KOTAKBANK","M&M","TATAMOTORS","HCLTECH","TITAN"],
        [10,9,8,7,7,6,5,5,4,4,4,4,4,3,3,3,3,3,3,3]
    ),
    "india_it": _pick(
        ["TCS","INFY","HCLTECH","WIPRO","TECHM","LTIM","PERSISTENT","COFORGE",
         "MPHASIS","OFSS","TATAELXSI","KPITTECH","LTTS","CYIENT","INFOEDGE"],
        [20,15,12,9,8,7,6,5,4,3,3,2,2,2,2]
    ),
    "india_banking": _pick(
        ["HDFCBANK","ICICIBANK","SBIN","AXISBANK","KOTAKBANK","BAJFINANCE",
         "BAJAJFINSV","INDUSINDBK","FEDERALBNK","BANKBARODA","LICI","SBILIFE",
         "CHOLAFIN","MUTHOOTFIN","PNB","RECLTD","PFC"],
        [16,13,11,9,7,6,5,5,4,3,3,3,3,3,2,2,4]
    ),
    "india_energy": _pick(
        ["RELIANCE","NTPC","POWERGRID","ONGC","BPCL","GAIL","IOC","ADANIGREEN",
         "ADANIPOWER","TATAPOWER","HINDPETRO","PETRONET","COALINDIA","OIL"],
        [20,11,10,8,7,6,6,5,5,5,4,4,4,5]
    ),
    "india_pharma": _pick(
        ["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP","LUPIN",
         "TORNTPHARM","AUROPHARMA","ALKEM","IPCALAB","GLENMARK","LAURUSLABS"],
        [20,16,14,10,8,7,6,5,4,4,3,3]
    ),
    "india_auto": _pick(
        ["MARUTI","TATAMOTORS","M&M","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT",
         "TVSMOTORS","ASHOKLEY","BALKRISIND","MOTHERSON","BOSCHLTD","BHARATFORG"],
        [20,16,13,11,9,7,6,5,4,3,3,3]
    ),
    "india_fmcg": _pick(
        ["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","MARICO",
         "GODREJCP","COLPAL","EMAMILTD","TATACONSUM","VBL","PGHH"],
        [20,16,12,10,8,7,6,6,4,4,4,3]
    ),
    "india_metals": _pick(
        ["JSWSTEEL","TATASTEEL","HINDALCO","VEDL","NMDC","COALINDIA",
         "SAIL","JINDALSTEL","NATIONALUM","HINDZINC","APL","RATNAMANI"],
        [20,16,13,10,8,7,7,5,4,4,3,3]
    ),
    "india_infra": _pick(
        ["LT","ULTRACEMCO","ADANIPORTS","GRASIM","SHREECEM","ACC",
         "AMBUJACEMENT","DLF","GODREJPROP","BHEL","RVNL","NCC","IRCON"],
        [18,12,10,9,7,7,7,6,5,5,5,5,4]
    ),
    "india_dividend": _pick(
        ["COALINDIA","IOC","ONGC","BPCL","HINDPETRO","GAIL","VEDL",
         "NMDC","BANKBARODA","CANBK","NIFTYBEES","GOLDBEES","ITC","PNB",
         "RECLTD","PFC","NHPC"],
        [10,9,9,7,7,6,6,5,5,4,5,4,4,4,5,5,5]
    ),
    "india_newage": _pick(
        ["ZOMATO","NYKAA","PAYTM","POLICYBZR","ADANIGREEN","ADANIENT",
         "TATAPOWER","PERSISTENT","COFORGE","BHARTIARTL","DELHIVERY","BSE"],
        [14,11,9,9,11,9,7,7,7,6,5,5]
    ),
    "india_midcap": _pick(
        ["CHOLAFIN","MUTHOOTFIN","SHRIRAMFIN","FEDERALBNK","MPHASIS",
         "PERSISTENT","COFORGE","TORNTPHARM","AUROPHARMA","CUMMINSIND",
         "HAVELLS","BALKRISIND","PRESTIGE","GODREJPROP","TORNTPOWER","ALKEM"],
        [7,7,6,6,6,6,6,6,6,6,6,5,5,5,5,6]
    ),
    "india_defensive": _pick(
        ["COALINDIA","NTPC","POWERGRID","ONGC","GAIL","NIFTYBEES",
         "GOLDBEES","SBIN","LICI","NMDC","CESC","BHARTIARTL","ITC","BEL"],
        [9,9,9,8,7,7,6,7,6,6,6,6,6,4]
    ),
    "india_defence": _pick(
        ["HAL","BEL","BDL","COCHINSHIP","MAZAGON","DATACENT","BHEL","LT"],
        [25,20,15,12,12,6,5,5]
    ),
    "india_smallcap": _pick(
        ["RATEGAIN","MASTEK","ZENSAR","KPITTECH","GRANULES","LAURUSLABS",
         "SNOWMAN","CAMPUS","KNRCON","NCC","PNCINFRA","ENGINERSIN","THYROCARE",
         "METROPOLIS","SOBHA","MAHLIFE","SUNTECK","FINEORG","CLEAN","GALAXYSURF"],
        [6,6,5,6,5,5,4,5,5,5,5,5,5,5,4,4,4,4,4,8]
    ),
    "india_chemicals": _pick(
        ["PIDILITIND","SRF","NAVINFLUOR","ATUL","DEEPAKNITR","TATACHEM",
         "GALAXYSURF","CLEAN","FINEORG","PIIND","SUMICHEM","COROMANDEL"],
        [18,14,12,10,10,8,7,6,6,6,6,7]
    ),
    "india_realty": _pick(
        ["DLF","GODREJPROP","PRESTIGE","OBEROIRLTY","PHOENIXLTD","BRIGADE",
         "SOBHA","MAHLIFE","SUNTECK"],
        [22,18,14,12,11,9,6,4,4]
    ),
    "india_healthcare": _pick(
        ["APOLLOHOSP","MAXHEALTH","METROPOLIS","THYROCARE","SUNPHARMA",
         "DRREDDY","CIPLA","DIVISLAB","SBILIFE","HDFCLIFE","STARHEALTH","ICICIGI"],
        [16,12,8,7,12,10,8,8,5,4,5,5]
    ),
}

# ── Combined master lookup ───────────────────────────────────────────────────
HD = {**HD_US, **HD_INDIA}


# ─────────────────────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "CreditWise ML API v2",
                    "indian_universe": len(INDIAN_UNIVERSE),
                    "portfolios": len(HD)})


@app.route("/api/stocks", methods=["GET"])
def stocks():
    sector   = request.args.get("sector", "balanced").lower()
    live     = request.args.get("live", "false").lower() == "true"
    data     = list(HD.get(sector, HD["balanced"]))
    currency = "INR" if (sector.startswith("india_") or sector == "nifty50") else "USD"

    if live and _YF_AVAILABLE:
        enriched = []
        for s in data:
            yf_ticker = s.get("yf", s["t"] + ".NS")
            quote = _live_price(yf_ticker)
            if quote:
                s = {**s, **quote}
            enriched.append(s)
        data = enriched

    return jsonify({"stocks": data, "sector": sector,
                    "currency": currency,
                    "live": live and _YF_AVAILABLE,
                    "count": len(data)})


@app.route("/api/stocks/search", methods=["GET"])
def search_stocks():
    """Search the Indian universe. Params: q, sector, mc, ex, sg, limit."""
    q      = request.args.get("q", "").upper()
    sector = request.args.get("sector", "").upper()
    mc     = request.args.get("mc", "").upper()
    ex     = request.args.get("ex", "").upper()
    sg     = request.args.get("sg", "").upper()
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
    if sg:
        results = [s for s in results if s.get("sg","").upper() == sg]

    return jsonify({"results": results[:limit],
                    "total": len(results),
                    "returned": min(limit, len(results))})


@app.route("/api/stocks/sectors", methods=["GET"])
def list_sectors():
    indian_sectors = sorted(set(s["sec"] for s in INDIAN_UNIVERSE))
    return jsonify({
        "portfolios":      sorted(HD.keys()),
        "us_portfolios":   sorted(HD_US.keys()),
        "india_portfolios":sorted(HD_INDIA.keys()),
        "indian_sectors":  indian_sectors,
        "universe_size":   len(INDIAN_UNIVERSE),
    })


@app.route("/api/stocks/universe", methods=["GET"])
def full_universe():
    """Return the complete Indian stock universe (paginated)."""
    page  = int(request.args.get("page", 1))
    size  = min(int(request.args.get("size", 50)), 100)
    start = (page - 1) * size
    end   = start + size
    return jsonify({
        "page":    page,
        "size":    size,
        "total":   len(INDIAN_UNIVERSE),
        "pages":   -(-len(INDIAN_UNIVERSE) // size),
        "stocks":  INDIAN_UNIVERSE[start:end],
    })


@app.route("/api/loan/predict", methods=["POST"])
def loan_predict():
    try:
        data = request.get_json(force=True)
        required = ["name","age","gender","married","dependents","education",
                    "income","loanamt","term","credit_score",
                    "employment_status","employer_category","area","type"]
        missing = [f for f in required
                   if f not in data or str(data[f]).strip() == ""]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
        return jsonify(predict_loan(data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
#  GROQ AI  (unchanged)
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
        body     = request.get_json(force=True)
        sector   = body.get("sector", "balanced")
        horizon  = body.get("horizon", "medium")
        amount   = body.get("amount", 10000)
        holdings = HD.get(sector, HD["balanced"])
        currency = "₹" if (sector.startswith("india_") or sector == "nifty50") else "$"
        lines    = "\n".join(
            f"  - {s['t']} ({s['n']}): {currency}{s['p']:,.0f} "
            f"| P/E {s['pe']} | Signal {s['sg']} | Weight {s['w']}%"
            for s in holdings
        )
        prompt = (
            f"Portfolio: {sector}, {horizon} horizon, {currency}{amount:,} invested.\n"
            f"Holdings:\n{lines}\n\n"
            "Provide a concise investment analysis: (1) strengths, "
            "(2) key risks, (3) top 2 actionable recommendations. "
            "Under 250 words, professional tone."
        )
        return jsonify({"analysis": _groq(prompt, "You are a senior portfolio analyst. Be concise, data-driven, and actionable."),
                        "sector": sector})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/screen", methods=["POST"])
def screen_stocks():
    try:
        body     = request.get_json(force=True)
        sector   = body.get("sector", "balanced")
        holdings = HD.get(sector, HD["balanced"])
        currency = "₹" if (sector.startswith("india_") or sector == "nifty50") else "$"
        lines    = "\n".join(
            f"  - {s['t']} ({s['n']}): {currency}{s['p']:,.0f} "
            f"| P/E {s['pe']} | Signal {s['sg']}"
            for s in holdings
        )
        prompt = (
            f"Screen {sector} stocks and rank the top 3 buys:\n{lines}\n\n"
            "For each: ticker, one-line reason, target price range. Under 200 words."
        )
        return jsonify({"screen": _groq(prompt, "You are a quantitative equity analyst. Be brief and specific."),
                        "sector": sector})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
