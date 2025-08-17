import os, time, threading, statistics
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify
import requests

# === Konfiguracja ze zmiennych środowiskowych ===
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
REFRESH_MINUTES = int(os.getenv("REFRESH_MINUTES", "5"))
LOVABLE_WEBHOOK_URL = os.getenv("LOVABLE_WEBHOOK_URL", "").strip()  # <- WYMAGANE
MODE = os.getenv("MODE", "AUTO")  # AUTO/SCALP/DAY/SWING

# Telegram (opcjonalnie)
TG_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Endpoints Binance
REST = "https://api.binance.com"
FREST = "https://fapi.binance.com"
URL_KLINES = f"{REST}/api/v3/klines?symbol={SYMBOL}&interval=1m&limit=120"
URL_TICKER = f"{REST}/api/v3/ticker/24hr?symbol={SYMBOL}"
URL_FUNDING = f"{FREST}/fapi/v1/fundingRate?symbol={SYMBOL}&limit=1"
URL_OI = f"{FREST}/futures/data/openInterestHist?symbol={SYMBOL}&period=5m&limit=48"
URL_LIQS = f"{FREST}/fapi/v1/forceOrders?symbol={SYMBOL}&limit=50"

app = Flask(__name__)

# ====== Narzędzia ======
def tg_send(text: str):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": text},
            timeout=10,
        )
    except Exception:
        pass

def get_json(url: str) -> Any:
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()

def fetch_data() -> Dict[str, Any]:
    return {
        "klines": get_json(URL_KLINES),
        "ticker": get_json(URL_TICKER),
        "funding": get_json(URL_FUNDING),
        "oi": get_json(URL_OI),
        "liquidations": get_json(URL_LIQS),
        "symbol": SYMBOL,
        "mode": MODE,
        "ts": int(time.time() * 1000),
    }

# ====== Proste triggery (oszczędzanie wywołań AI) ======
def price_move_pct(ticker_now: Dict[str, Any], klines: List[List[Any]]) -> float:
    """Porównaj ostatnią cenę z ceną zamknięcia sprzed 5 świec."""
    last_price = float(ticker_now.get("lastPrice", 0.0))
    if len(klines) < 6:
        return 0.0
    close_5m_ago = float(klines[-6][4])
    if close_5m_ago == 0:
        return 0.0
    return (last_price - close_5m_ago) / close_5m_ago * 100.0

def volume_spike(klines: List[List[Any]]) -> bool:
    """Wolumen ostatniej świecy > 1.5x mediany 30 ostatnich świec."""
    if len(klines) < 31:
        return False
    vols = [float(k[5]) for k in klines[-31:-1]]
    med = statistics.median(vols)
    last_vol = float(klines[-1][5])
    return med > 0 and last_vol >= 1.5 * med

def oi_delta_pct(oi_series: List[Dict[str, Any]]) -> float:
    """Procentowa zmiana OI między dwoma ostatnimi punktami."""
    if len(oi_series) < 2:
        return 0.0
    a = float(oi_series[-2]["sumOpenInterest"])
    b = float(oi_series[-1]["sumOpenInterest"])
    if a == 0:
        return 0.0
    return (b - a) / a * 100.0

def big_liqs_count(liqs: List[Dict[str, Any]], threshold_usdt: float = 100_000.0) -> int:
    c = 0
    for x in liqs:
        # niektóre rekordy mają 'price', 'origQty'; liczymy notional = price * qty
        try:
            price = float(x.get("price", 0.0))
            qty = float(x.get("origQty", 0.0))
            notional = price * qty
            if notional >= threshold_usdt:
                c += 1
        except Exception:
            continue
    return c

def should_trigger(data: Dict[str, Any]) -> (bool, Dict[str, Any]):
    kl = data["klines"]
    tk = data["ticker"]
    oi = data["oi"]
    liqs = data["liquidations"]

    pm = price_move_pct(tk, kl)                # % zmiany ceny w 5m
    oi_chg = oi_delta_pct(oi)                  # % zmiany OI
    liq_big = big_liqs_count(liqs)             # liczb. dużych liq
    vol_spk = volume_spike(kl)                 # spike wolumenu

    reasons = []
    if abs(pm) >= 0.35: reasons.append(f"price_move_5m={pm:.2f}%")
    if abs(oi_chg) >= 0.8: reasons.append(f"oi_delta={oi_chg:.2f}%")
    if liq_big >= 3: reasons.append(f"liqs>=3")
    if vol_spk: reasons.append("volume_spike")

    return (len(reasons) > 0, {
        "price_move_5m_pct": round(pm, 3),
        "oi_delta_pct": round(oi_chg, 3),
        "big_liqs_count": liq_big,
        "volume_spike": vol_spk,
        "reasons": reasons
    })

# ====== Wysyłka do Lovable ======
def post_to_lovable(payload: Dict[str, Any]) -> requests.Response:
    if not LOVABLE_WEBHOOK_URL:
        raise RuntimeError("Brak LOVABLE_WEBHOOK_URL w env!")
    return requests.post(LOVABLE_WEBHOOK_URL, json=payload, timeout=20)

# ====== Pętla w tle ======
def loop_worker():
    while True:
        try:
            data = fetch_data()
            ok, trig = should_trigger(data)
            if ok:
                payload = {**data, "trigger": trig}
                r = post_to_lovable(payload)
                msg = f"→ Trigger: {', '.join(trig['reasons'])} | HTTP {r.status_code}"
                print(msg)
                tg_send(f"Jarvis trigger {SYMBOL}: {', '.join(trig['reasons'])}")
            else:
                print("no-trigger; skip")
        except Exception as e:
            print(f"[loop error] {e}")
        time.sleep(REFRESH_MINUTES * 60)

# ====== Fl
