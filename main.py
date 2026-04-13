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
    # ── Real NSE Nifty 50 data (sourced from National_Stock_Exchange_of_India_Ltd.csv)
    # ── Fields: t=ticker, p=LTP price(₹), ch=day%chg, lo/hi=52w range,
    # ──         ch365=365d%chg, ch30=30d%chg, vol=volume(lacs), turnover=turnover(crs)
    {"t":"ADANIPORTS","yf":"ADANIPORTS.NS","n":"Adani Ports & SEZ","p":715.0,"open":750.0,"high":766.0,"low":713.25,"ch":-6.22,"chng":-47.45,"lo":384.4,"hi":901.0,"ch365":79.22,"ch30":-4.65,"vol":72.2,"turnover":532.63,"pe":None,"sg":"BUY","c":"#2563eb","w":0,"ex":"NSE","sec":"INFRA","mc":"LARGE","div":0.0},
    {"t":"ASIANPAINT","yf":"ASIANPAINT.NS","n":"Asian Paints Ltd","p":3138.0,"open":3101.0,"high":3167.35,"low":3091.0,"ch":-0.2,"chng":-6.25,"lo":2117.15,"hi":3505.0,"ch365":45.66,"ch30":5.66,"vol":10.29,"turnover":322.53,"pe":None,"sg":"BUY","c":"#7c3aed","w":0,"ex":"NSE","sec":"CONSUMER","mc":"LARGE","div":0.0},
    {"t":"AXISBANK","yf":"AXISBANK.NS","n":"Axis Bank Ltd","p":661.0,"open":669.0,"high":674.9,"low":660.45,"ch":-2.78,"chng":-18.9,"lo":568.4,"hi":866.9,"ch365":10.19,"ch30":-21.49,"vol":102.53,"turnover":684.0,"pe":None,"sg":"HOLD","c":"#0891b2","w":0,"ex":"NSE","sec":"PVT_BANK","mc":"LARGE","div":0.0},
    {"t":"BAJAJ-AUTO","yf":"BAJAJ-AUTO.NS","n":"Bajaj Auto Ltd","p":3335.0,"open":3370.0,"high":3383.5,"low":3320.0,"ch":-1.67,"chng":-56.7,"lo":3041.0,"hi":4361.4,"ch365":9.3,"ch30":-12.05,"vol":3.42,"turnover":114.59,"pe":None,"sg":"HOLD","c":"#16a34a","w":0,"ex":"NSE","sec":"AUTO","mc":"LARGE","div":0.0},
    {"t":"BAJAJFINSV","yf":"BAJAJFINSV.NS","n":"Bajaj Finserv Ltd","p":16684.0,"open":17200.0,"high":17237.2,"low":16610.0,"ch":-3.94,"chng":-684.85,"lo":8273.7,"hi":19325.0,"ch365":91.38,"ch30":-9.1,"vol":3.42,"turnover":576.79,"pe":None,"sg":"BUY","c":"#db2777","w":0,"ex":"NSE","sec":"NBFC","mc":"LARGE","div":0.0},
    {"t":"BAJFINANCE","yf":"BAJFINANCE.NS","n":"Bajaj Finance Ltd","p":6780.0,"open":7021.0,"high":7047.9,"low":6775.0,"ch":-4.85,"chng":-345.8,"lo":4362.0,"hi":8050.0,"ch365":44.57,"ch30":-13.69,"vol":16.89,"turnover":1161.63,"pe":None,"sg":"BUY","c":"#e11d48","w":0,"ex":"NSE","sec":"NBFC","mc":"LARGE","div":0.0},
    {"t":"BHARTIARTL","yf":"BHARTIARTL.NS","n":"Bharti Airtel Ltd","p":735.85,"open":763.0,"high":763.0,"low":733.1,"ch":-3.83,"chng":-29.3,"lo":454.11,"hi":781.8,"ch365":58.55,"ch30":5.7,"vol":111.43,"turnover":830.06,"pe":None,"sg":"BUY","c":"#b45309","w":0,"ex":"NSE","sec":"TELECOM","mc":"LARGE","div":0.0},
    {"t":"BPCL","yf":"BPCL.NS","n":"Bharat Petroleum Corp","p":377.4,"open":397.15,"high":397.2,"low":375.0,"ch":-5.67,"chng":-22.7,"lo":357.0,"hi":503.0,"ch365":-1.22,"ch30":-12.45,"vol":100.23,"turnover":383.54,"pe":None,"sg":"SELL","c":"#9333ea","w":0,"ex":"NSE","sec":"ENERGY","mc":"LARGE","div":0.0},
    {"t":"BRITANNIA","yf":"BRITANNIA.NS","n":"Britannia Industries","p":3566.6,"open":3560.0,"high":3635.1,"low":3533.95,"ch":-0.19,"chng":-6.8,"lo":3317.3,"hi":4153.0,"ch365":0.3,"ch30":-3.42,"vol":3.73,"turnover":133.23,"pe":None,"sg":"HOLD","c":"#0a7c4e","w":0,"ex":"NSE","sec":"FMCG","mc":"MID","div":0.0},
    {"t":"CIPLA","yf":"CIPLA.NS","n":"Cipla Ltd","p":965.0,"open":892.0,"high":976.05,"low":890.65,"ch":7.23,"chng":65.05,"lo":726.5,"hi":1005.0,"ch365":31.89,"ch30":6.34,"vol":144.59,"turnover":1380.9,"pe":None,"sg":"BUY","c":"#64748b","w":0,"ex":"NSE","sec":"PHARMA","mc":"LARGE","div":0.0},
    {"t":"COALINDIA","yf":"COALINDIA.NS","n":"Coal India Ltd","p":155.9,"open":157.75,"high":159.4,"low":155.35,"ch":-1.67,"chng":-2.65,"lo":123.25,"hi":203.8,"ch365":25.78,"ch30":-10.94,"vol":118.3,"turnover":185.5,"pe":None,"sg":"HOLD","c":"#94a3b8","w":0,"ex":"NSE","sec":"METALS","mc":"LARGE","div":0.0},
    {"t":"DIVISLAB","yf":"DIVISLAB.NS","n":"Divi\'s Laboratories","p":4940.0,"open":4770.0,"high":5077.7,"low":4756.75,"ch":2.92,"chng":140.2,"lo":3153.3,"hi":5425.1,"ch365":42.39,"ch30":-1.57,"vol":15.71,"turnover":775.37,"pe":None,"sg":"BUY","c":"#1d4ed8","w":0,"ex":"NSE","sec":"PHARMA","mc":"LARGE","div":0.0},
    {"t":"DRREDDY","yf":"DRREDDY.NS","n":"Dr. Reddy\'s Laboratories","p":4750.0,"open":4580.0,"high":4820.0,"low":4576.15,"ch":3.45,"chng":158.4,"lo":4135.0,"hi":5614.6,"ch365":-1.17,"ch30":1.8,"vol":10.72,"turnover":508.97,"pe":None,"sg":"BUY","c":"#2563eb","w":0,"ex":"NSE","sec":"PHARMA","mc":"LARGE","div":0.0},
    {"t":"EICHERMOT","yf":"EICHERMOT.NS","n":"Eicher Motors Ltd","p":2440.75,"open":2495.0,"high":2506.1,"low":2421.5,"ch":-3.16,"chng":-79.65,"lo":2303.7,"hi":3037.0,"ch365":-5.95,"ch30":-5.77,"vol":5.55,"turnover":136.56,"pe":None,"sg":"SELL","c":"#7c3aed","w":0,"ex":"NSE","sec":"AUTO","mc":"LARGE","div":0.0},
    {"t":"GRASIM","yf":"GRASIM.NS","n":"Grasim Industries Ltd","p":1685.8,"open":1757.3,"high":1757.85,"low":1679.0,"ch":-4.58,"chng":-80.95,"lo":840.05,"hi":1893.0,"ch365":99.95,"ch30":-3.08,"vol":7.48,"turnover":127.84,"pe":None,"sg":"BUY","c":"#0891b2","w":0,"ex":"NSE","sec":"CEMENT","mc":"LARGE","div":0.0},
    {"t":"HCLTECH","yf":"HCLTECH.NS","n":"HCL Technologies Ltd","p":1111.65,"open":1120.0,"high":1126.0,"low":1103.3,"ch":-1.17,"chng":-13.15,"lo":814.35,"hi":1377.75,"ch365":34.79,"ch30":-4.73,"vol":22.07,"turnover":246.06,"pe":None,"sg":"BUY","c":"#16a34a","w":0,"ex":"NSE","sec":"IT","mc":"LARGE","div":0.0},
    {"t":"HDFC","yf":"HDFC.NS","n":"HDFC Ltd","p":2745.0,"open":2820.35,"high":2856.0,"low":2723.0,"ch":-4.28,"chng":-122.75,"lo":2179.3,"hi":3021.1,"ch365":25.27,"ch30":-5.72,"vol":33.53,"turnover":927.88,"pe":None,"sg":"SELL","c":"#db2777","w":0,"ex":"NSE","sec":"NBFC","mc":"LARGE","div":0.0},
    {"t":"HDFCBANK","yf":"HDFCBANK.NS","n":"HDFC Bank Ltd","p":1489.5,"open":1500.0,"high":1506.7,"low":1485.0,"ch":-2.39,"chng":-36.45,"lo":1342.0,"hi":1725.0,"ch365":6.18,"ch30":-9.88,"vol":93.12,"turnover":1394.1,"pe":None,"sg":"HOLD","c":"#e11d48","w":0,"ex":"NSE","sec":"PVT_BANK","mc":"LARGE","div":0.0},
    {"t":"HDFCLIFE","yf":"HDFCLIFE.NS","n":"HDFC Life Insurance","p":669.75,"open":685.0,"high":689.0,"low":667.1,"ch":-2.77,"chng":-19.05,"lo":617.4,"hi":775.65,"ch365":0.7,"ch30":-2.94,"vol":22.37,"turnover":151.4,"pe":None,"sg":"HOLD","c":"#b45309","w":0,"ex":"NSE","sec":"INSURANCE","mc":"LARGE","div":0.0},
    {"t":"HEROMOTOCO","yf":"HEROMOTOCO.NS","n":"Hero MotoCorp Ltd","p":2526.8,"open":2580.0,"high":2589.7,"low":2505.15,"ch":-2.62,"chng":-67.9,"lo":2505.15,"hi":3629.05,"ch365":-16.02,"ch30":-6.43,"vol":6.85,"turnover":174.04,"pe":None,"sg":"SELL","c":"#9333ea","w":0,"ex":"NSE","sec":"AUTO","mc":"LARGE","div":0.0},
    {"t":"HINDALCO","yf":"HINDALCO.NS","n":"Hindalco Industries","p":417.7,"open":441.8,"high":442.7,"low":414.7,"ch":-6.57,"chng":-29.35,"lo":220.35,"hi":551.85,"ch365":86.93,"ch30":-14.06,"vol":148.26,"turnover":631.93,"pe":None,"sg":"BUY","c":"#0a7c4e","w":0,"ex":"NSE","sec":"METALS","mc":"LARGE","div":0.0},
    {"t":"HINDUNILVR","yf":"HINDUNILVR.NS","n":"Hindustan Unilever Ltd","p":2340.9,"open":2344.0,"high":2365.0,"low":2325.2,"ch":-0.35,"chng":-8.15,"lo":2120.0,"hi":2859.3,"ch365":9.6,"ch30":-3.94,"vol":24.51,"turnover":572.85,"pe":None,"sg":"HOLD","c":"#64748b","w":0,"ex":"NSE","sec":"FMCG","mc":"LARGE","div":0.0},
    {"t":"ICICIBANK","yf":"ICICIBANK.NS","n":"ICICI Bank Ltd","p":720.45,"open":739.0,"high":742.05,"low":718.6,"ch":-4.07,"chng":-30.6,"lo":465.8,"hi":867.0,"ch365":52.41,"ch30":-13.14,"vol":189.88,"turnover":1385.86,"pe":None,"sg":"BUY","c":"#94a3b8","w":0,"ex":"NSE","sec":"PVT_BANK","mc":"LARGE","div":0.0},
    {"t":"INDUSINDBK","yf":"INDUSINDBK.NS","n":"IndusInd Bank Ltd","p":899.95,"open":951.0,"high":956.95,"low":898.0,"ch":-6.19,"chng":-59.35,"lo":789.0,"hi":1242.0,"ch365":5.25,"ch30":-22.08,"vol":67.46,"turnover":622.74,"pe":None,"sg":"SELL","c":"#1d4ed8","w":0,"ex":"NSE","sec":"PVT_BANK","mc":"LARGE","div":0.0},
    {"t":"INFY","yf":"INFY.NS","n":"Infosys Ltd","p":1689.55,"open":1702.55,"high":1718.35,"low":1684.0,"ch":-1.91,"chng":-32.85,"lo":1091.0,"hi":1848.0,"ch365":51.44,"ch30":-0.83,"vol":44.94,"turnover":764.67,"pe":None,"sg":"BUY","c":"#2563eb","w":0,"ex":"NSE","sec":"IT","mc":"LARGE","div":0.0},
    {"t":"IOC","yf":"IOC.NS","n":"Indian Oil Corporation","p":121.15,"open":125.6,"high":125.6,"low":120.5,"ch":-3.58,"chng":-4.5,"lo":84.0,"hi":141.5,"ch365":41.28,"ch30":-7.87,"vol":77.25,"turnover":94.57,"pe":None,"sg":"BUY","c":"#7c3aed","w":0,"ex":"NSE","sec":"ENERGY","mc":"LARGE","div":0.0},
    {"t":"ITC","yf":"ITC.NS","n":"ITC Ltd","p":223.6,"open":228.9,"high":230.05,"low":223.1,"ch":-3.33,"chng":-7.7,"lo":192.4,"hi":265.3,"ch365":15.35,"ch30":-5.53,"vol":270.27,"turnover":610.54,"pe":None,"sg":"HOLD","c":"#0891b2","w":0,"ex":"NSE","sec":"FMCG","mc":"LARGE","div":0.0},
    {"t":"JSWSTEEL","yf":"JSWSTEEL.NS","n":"JSW Steel Ltd","p":630.0,"open":668.25,"high":672.55,"low":624.25,"ch":-7.48,"chng":-50.9,"lo":336.0,"hi":776.5,"ch365":86.25,"ch30":-9.27,"vol":89.22,"turnover":574.61,"pe":None,"sg":"BUY","c":"#16a34a","w":0,"ex":"NSE","sec":"METALS","mc":"LARGE","div":0.0},
    {"t":"KOTAKBANK","yf":"KOTAKBANK.NS","n":"Kotak Mahindra Bank","p":1960.0,"open":2002.0,"high":2007.0,"low":1955.1,"ch":-3.69,"chng":-75.1,"lo":1626.0,"hi":2253.0,"ch365":5.24,"ch30":-11.35,"vol":26.48,"turnover":522.52,"pe":None,"sg":"HOLD","c":"#db2777","w":0,"ex":"NSE","sec":"PVT_BANK","mc":"LARGE","div":0.0},
    {"t":"LT","yf":"LT.NS","n":"Larsen & Toubro Ltd","p":1781.0,"open":1820.0,"high":1841.75,"low":1768.6,"ch":-3.72,"chng":-68.9,"lo":1092.0,"hi":1981.75,"ch365":59.59,"ch30":-0.85,"vol":27.97,"turnover":502.81,"pe":None,"sg":"BUY","c":"#e11d48","w":0,"ex":"NSE","sec":"INFRA","mc":"LARGE","div":0.0},
    {"t":"M&M","yf":"M&M.NS","n":"Mahindra & Mahindra","p":855.05,"open":885.0,"high":885.0,"low":843.0,"ch":-4.06,"chng":-36.15,"lo":660.25,"hi":979.0,"ch365":18.77,"ch30":-4.42,"vol":39.34,"turnover":338.08,"pe":None,"sg":"SELL","c":"#b45309","w":0,"ex":"NSE","sec":"AUTO","mc":"LARGE","div":0.0},
    {"t":"MARUTI","yf":"MARUTI.NS","n":"Maruti Suzuki India","p":7150.0,"open":7520.0,"high":7520.0,"low":7130.0,"ch":-5.58,"chng":-422.5,"lo":6400.0,"hi":8368.0,"ch365":1.34,"ch30":-2.02,"vol":11.55,"turnover":840.81,"pe":None,"sg":"SELL","c":"#9333ea","w":0,"ex":"NSE","sec":"AUTO","mc":"LARGE","div":0.0},
    {"t":"NESTLEIND","yf":"NESTLEIND.NS","n":"Nestle India Ltd","p":19250.0,"open":19148.85,"high":19434.1,"low":18982.5,"ch":0.38,"chng":71.95,"lo":16002.1,"hi":20609.15,"ch365":9.87,"ch30":0.17,"vol":0.56,"turnover":108.61,"pe":None,"sg":"HOLD","c":"#0a7c4e","w":0,"ex":"NSE","sec":"FMCG","mc":"LARGE","div":0.0},
    {"t":"NTPC","yf":"NTPC.NS","n":"NTPC Ltd","p":128.65,"open":133.2,"high":134.05,"low":128.0,"ch":-4.84,"chng":-6.55,"lo":88.15,"hi":152.1,"ch365":36.93,"ch30":-10.16,"vol":133.24,"turnover":173.94,"pe":None,"sg":"BUY","c":"#64748b","w":0,"ex":"NSE","sec":"POWER","mc":"LARGE","div":0.0},
    {"t":"ONGC","yf":"ONGC.NS","n":"ONGC Ltd","p":147.75,"open":152.25,"high":152.25,"low":146.25,"ch":-4.74,"chng":-7.35,"lo":77.05,"hi":172.75,"ch365":82.86,"ch30":-9.41,"vol":231.36,"turnover":344.33,"pe":None,"sg":"BUY","c":"#94a3b8","w":0,"ex":"NSE","sec":"ENERGY","mc":"LARGE","div":0.0},
    {"t":"POWERGRID","yf":"POWERGRID.NS","n":"Power Grid Corp","p":202.5,"open":204.05,"high":204.95,"low":200.8,"ch":-0.86,"chng":-1.75,"lo":136.88,"hi":209.95,"ch365":3.69,"ch30":6.36,"vol":96.11,"turnover":195.09,"pe":None,"sg":"HOLD","c":"#1d4ed8","w":0,"ex":"NSE","sec":"POWER","mc":"LARGE","div":0.0},
    {"t":"RELIANCE","yf":"RELIANCE.NS","n":"Reliance Industries Ltd","p":2405.1,"open":2467.8,"high":2477.6,"low":2401.5,"ch":-3.52,"chng":-87.85,"lo":1830.0,"hi":2751.35,"ch365":23.48,"ch30":-9.62,"vol":72.75,"turnover":1770.19,"pe":None,"sg":"HOLD","c":"#2563eb","w":0,"ex":"NSE","sec":"ENERGY","mc":"LARGE","div":0.0},
    {"t":"SBILIFE","yf":"SBILIFE.NS","n":"SBI Life Insurance","p":1130.85,"open":1154.0,"high":1154.0,"low":1105.25,"ch":-2.47,"chng":-28.65,"lo":825.2,"hi":1273.9,"ch365":33.19,"ch30":-3.52,"vol":23.16,"turnover":262.43,"pe":None,"sg":"BUY","c":"#7c3aed","w":0,"ex":"NSE","sec":"INSURANCE","mc":"LARGE","div":0.0},
    {"t":"SBIN","yf":"SBIN.NS","n":"State Bank of India","p":470.0,"open":486.25,"high":487.9,"low":467.1,"ch":-4.19,"chng":-20.55,"lo":240.15,"hi":542.3,"ch365":93.42,"ch30":-8.3,"vol":263.06,"turnover":1249.55,"pe":None,"sg":"BUY","c":"#0891b2","w":0,"ex":"NSE","sec":"PSU_BANK","mc":"LARGE","div":0.0},
    {"t":"SHREECEM","yf":"SHREECEM.NS","n":"Shree Cement Ltd","p":25900.0,"open":26450.0,"high":26539.9,"low":25812.0,"ch":-2.89,"chng":-770.5,"lo":22531.0,"hi":32048.0,"ch365":9.29,"ch30":-6.76,"vol":0.3,"turnover":76.94,"pe":None,"sg":"HOLD","c":"#16a34a","w":0,"ex":"NSE","sec":"CEMENT","mc":"MID","div":0.0},
    {"t":"SUNPHARMA","yf":"SUNPHARMA.NS","n":"Sun Pharmaceutical Ind","p":767.25,"open":775.0,"high":798.9,"low":762.0,"ch":-2.0,"chng":-15.65,"lo":502.3,"hi":851.0,"ch365":51.57,"ch30":-5.69,"vol":54.33,"turnover":424.05,"pe":None,"sg":"BUY","c":"#db2777","w":0,"ex":"NSE","sec":"PHARMA","mc":"LARGE","div":0.0},
    {"t":"TATACONSUM","yf":"TATACONSUM.NS","n":"Tata Consumer Products","p":769.9,"open":800.2,"high":805.0,"low":763.15,"ch":-4.69,"chng":-37.9,"lo":505.05,"hi":889.0,"ch365":49.55,"ch30":-4.82,"vol":26.17,"turnover":203.32,"pe":None,"sg":"BUY","c":"#e11d48","w":0,"ex":"NSE","sec":"FMCG","mc":"MID","div":0.0},
    {"t":"TATAMOTORS","yf":"TATAMOTORS.NS","n":"Tata Motors Ltd","p":459.4,"open":486.0,"high":486.75,"low":458.0,"ch":-6.77,"chng":-33.35,"lo":156.7,"hi":536.7,"ch365":167.95,"ch30":-9.68,"vol":517.88,"turnover":2430.36,"pe":None,"sg":"BUY","c":"#b45309","w":0,"ex":"NSE","sec":"AUTO","mc":"LARGE","div":0.0},
    {"t":"TATASTEEL","yf":"TATASTEEL.NS","n":"Tata Steel Ltd","p":1110.25,"open":1157.9,"high":1159.5,"low":1106.25,"ch":-5.4,"chng":-63.4,"lo":539.5,"hi":1534.5,"ch365":105.13,"ch30":-17.37,"vol":106.46,"turnover":1200.79,"pe":None,"sg":"BUY","c":"#9333ea","w":0,"ex":"NSE","sec":"METALS","mc":"LARGE","div":0.0},
    {"t":"TCS","yf":"TCS.NS","n":"Tata Consultancy Services","p":3439.2,"open":3425.0,"high":3490.0,"low":3411.9,"ch":-0.19,"chng":-6.7,"lo":2624.45,"hi":3989.9,"ch365":27.32,"ch30":-1.25,"vol":19.41,"turnover":670.58,"pe":None,"sg":"HOLD","c":"#0a7c4e","w":0,"ex":"NSE","sec":"IT","mc":"LARGE","div":0.0},
    {"t":"TECHM","yf":"TECHM.NS","n":"Tech Mahindra Ltd","p":1519.0,"open":1544.0,"high":1550.0,"low":1510.15,"ch":-2.59,"chng":-40.35,"lo":846.7,"hi":1630.0,"ch365":76.17,"ch30":-2.83,"vol":15.22,"turnover":232.97,"pe":None,"sg":"BUY","c":"#64748b","w":0,"ex":"NSE","sec":"IT","mc":"LARGE","div":0.0},
    {"t":"TITAN","yf":"TITAN.NS","n":"Titan Company Ltd","p":2293.0,"open":2377.8,"high":2385.1,"low":2285.05,"ch":-4.37,"chng":-104.8,"lo":1300.35,"hi":2677.9,"ch365":75.45,"ch30":-6.59,"vol":12.89,"turnover":298.54,"pe":None,"sg":"BUY","c":"#94a3b8","w":0,"ex":"NSE","sec":"CONSUMER","mc":"LARGE","div":0.0},
    {"t":"ULTRACEMCO","yf":"ULTRACEMCO.NS","n":"UltraTech Cement Ltd","p":7398.45,"open":7550.0,"high":7599.0,"low":7370.1,"ch":-2.76,"chng":-210.35,"lo":4770.0,"hi":8269.0,"ch365":53.5,"ch30":1.78,"vol":2.66,"turnover":198.32,"pe":None,"sg":"BUY","c":"#1d4ed8","w":0,"ex":"NSE","sec":"CEMENT","mc":"LARGE","div":0.0},
    {"t":"UPL","yf":"UPL.NS","n":"UPL Ltd","p":703.5,"open":726.0,"high":726.0,"low":701.0,"ch":-3.27,"chng":-23.8,"lo":414.15,"hi":864.7,"ch365":68.06,"ch30":-1.37,"vol":24.82,"turnover":176.35,"pe":None,"sg":"BUY","c":"#2563eb","w":0,"ex":"NSE","sec":"AGROCHEM","mc":"LARGE","div":0.0},
    {"t":"WIPRO","yf":"WIPRO.NS","n":"Wipro Ltd","p":621.3,"open":632.0,"high":634.4,"low":619.65,"ch":-2.42,"chng":-15.4,"lo":346.25,"hi":739.85,"ch365":77.51,"ch30":-7.01,"vol":41.39,"turnover":259.37,"pe":None,"sg":"BUY","c":"#7c3aed","w":0,"ex":"NSE","sec":"IT","mc":"LARGE","div":0.0}
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
GROQ_MODEL   = "mixtral-8x7b-32768"


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
