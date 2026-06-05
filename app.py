import streamlit as st
import ccxt.pro as ccxtpro  # Fast Async Binance Call এর জন্য
import asyncio
import pandas as pd
import requests
import threading
import time
from datetime import datetime

# --- TELEGRAM CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8957518460:AAE_9HaugsNNYfjOzCpbHi2nJAEKf4GSiKs"
TELEGRAM_CHAT_ID = "6166836299"

def send_telegram_message(message):
    """টেলিগ্রামে মেসেজ পাঠানোর ব্যাকএন্ড ফাংশন"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Delivery Error: {e}")

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(page_title="24/7 Binance EMA Scanner", layout="wide")

# --- UI DESIGN / LUXURY COMPACT CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #090d16 0%, #111827 100%);
        color: #f8fafc;
    }
    h1 {
        color: #00d2ff !important;
        background: linear-gradient(to right, #00ffff, #0088ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Inter', sans-serif;
        font-weight: 900 !important;
        text-shadow: 0px 0px 20px rgba(0, 255, 255, 0.3);
        margin-bottom: 5px !important;
        padding-bottom: 0px !important;
    }
    .scanning-box {
        background: rgba(17, 24, 39, 0.85);
        border: 2px solid #38bdf8;
        box-shadow: 0px 0px 15px rgba(56, 189, 248, 0.3);
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        margin: 10px 0;
        animation: pulse 1.5s infinite alternate;
    }
    .scanning-coin {
        font-size: 2.2rem !important;
        font-weight: 800;
        color: #ff007f !important;
        text-shadow: 0 0 10px rgba(255, 0, 127, 0.5);
        letter-spacing: 1px;
    }
    @keyframes pulse {
        0% { transform: scale(0.99); }
        100% { transform: scale(1.01); }
    }
    div[data-testid="metric-container"] {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 10px 15px;
        border-radius: 10px;
    }
    .dataframe {
        font-size: 13px !important;
        width: 100% !important;
        border-collapse: collapse !important;
    }
    .dataframe th {
        background-color: #1f2937 !important;
        color: #00d2ff !important;
        padding: 6px !important;
        text-align: left !important;
    }
    .dataframe td {
        padding: 5px !important;
        border-bottom: 1px solid #1f2937 !important;
    }
    .binance-btn {
        display: inline-block;
        padding: 3px 8px;
        background: linear-gradient(135deg, #f3ba2f 0%, #d49b00 100%);
        color: #000 !important;
        font-weight: bold;
        font-size: 11px;
        border-radius: 4px;
        text-decoration: none;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Premium Binance 24/7 Top 100 Scanner")
st.write("বাইনান্সের সর্বোচ্চ ভলিউম ওয়ালা টপ ১০০টি USDT-M ফিউচার কয়েন ১৫ মিনিট পর পর অটো-স্ক্যান করা হয়।")

# Global Cache Store (UI ও ব্যাকগ্রাউন্ড থ্রেডের ডাটা সিঙ্ক করার জন্য)
@st.cache_resource
def get_global_data():
    return {
        "last_scan_time": "এখনো স্ক্যান শুরু হয়নি",
        "bullish_coins": [],
        "total_scanned": 0,
        "current_progress": "স্ট্যান্ডবাই (প্রথম রান হচ্ছে...)",
        "active_coin": "অপেক্ষা করুন..."
    }

global_data = get_global_data()

# UI প্লেসহোল্ডারস
progress_placeholder = st.empty()
metrics_placeholder = st.empty()
table_placeholder = st.empty()

# --- ASYNC BACKGROUND CORE ---

async def fetch_top_100_futures(exchange):
    """২৪ ঘণ্টার ভলিউম অনুযায়ী সুনির্দিষ্টভাবে টপ ১০০ USDT-M ফিউচার মার্কেট নিয়ে আসে"""
    try:
        markets = await exchange.fetch_markets()
        
        futures_pairs = []
        for market in markets:
            if market.get('active') and market.get('linear') and market.get('swap'):
                if market.get('settle') == 'USDT':
                    futures_pairs.append(market['symbol'])
        
        tickers = await exchange.fetch_tickers(futures_pairs)
        sorted_tickers = sorted(
            tickers.values(), 
            key=lambda x: x.get('quoteVolume', 0) if x.get('quoteVolume') is not None else 0, 
            reverse=True
        )
        return [ticker['symbol'] for ticker in sorted_tickers[:100]]
    except Exception as e:
        print(f"Market Sync Error: {e}")
        return []

async def fetch_and_calculate_ema(exchange, symbol):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=250)
        if len(ohlcv) < 200:
            return None
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        last_close = df['close'].iloc[-1]
        last_ema = df['ema_200'].iloc[-1]
        
        if not pd.isna(last_ema) and last_close > last_ema:
            return {
                "Symbol": symbol.split(':')[0],
                "Price": last_close,
                "200 EMA": round(last_ema, 4),
                "Distance (%)": round(((last_close - last_ema) / last_ema) * 100, 2)
            }
    except Exception:
        pass
    return None

async def scan_process():
    """মূল স্ক্যানিং প্রসেস (FAPI এন্ডপয়েন্ট ফিক্সড করা হয়েছে)"""
    exchange = ccxtpro.binance({
        'enableRateLimit': True, 
        'options': {
            'defaultType': 'future',  # ফিউচার এন্ডপয়েন্ট ফিক্সড (dapi এরর আসবে না)
            'adjustForTimeDifference': True
        }
    })
    
    symbols_to_scan = await fetch_top_100_futures(exchange)
    
    if not symbols_to_scan:
        await exchange.close()
        return
    
    bullish_list = []
    total_coins = len(symbols_to_scan)
    global_data["total_scanned"] = total_coins
    
    batch_size = 5  
    for i in range(0, total_coins, batch_size):
        batch = symbols_to_scan[i:i+batch_size]
        perc = int(((i + len(batch)) / total_coins) * 100)
        
        current_coin_name = batch[0].split('/')[0]
        global_data["active_coin"] = current_coin_name
        global_data["current_progress"] = f"🔍 স্ক্যানিং প্রোগ্রেস: {perc}% ({min(i+batch_size, total_coins)}/{total_coins})"
        
        tasks = [fetch_and_calculate_ema(exchange, symbol) for symbol in batch]
        results = await asyncio.gather(*tasks)
        
        for res in results:
            if res:
                bullish_list.append(res)
        await asyncio.sleep(0.15)
        
    await exchange.close()
    
    global_data["bullish_coins"] = bullish_list
    global_data["last_scan_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    global_data["current_progress"] = "সম্পন্ন (পরবর্তী লাইভ রান ১৫ মিনিট পর)"
    global_data["active_coin"] = "FINISHED"
    
    # --- টেলিগ্রাম অ্যালার্ট মেসেজ ---
    if bullish_list:
        tg_msg = f"🔔 *Binance 15M Top 100 EMA Bullish Report*\n"
        tg_msg += f"⏰ সময়: `{global_data['last_scan_time']}`\n"
        tg_msg += f"📊 মোট স্ক্যান: `{total_coins}` | বুলিশ কয়েন: `{len(bullish_list)}`\n\n"
        tg_msg += "*কয়েন লিস্ট (Price / Distance):*\n"
        
        for coin in bullish_list[:25]:
            tg_msg += f"• `{coin['Symbol']}`: ${coin['Price']} (+{coin['Distance (%)']}% Above EMA)\n"
        
        if len(bullish_list) > 25:
            tg_msg += f"\n_...এবং আরও {len(bullish_list)-25}টি কয়েন রয়েছে।_"
    else:
        tg_msg = f"ℹ️ *Binance 15M Top 100 EMA Scan Completed*\n⏰ সময়: `{global_data['last_scan_time']}`\nকোনো বুলিশ কয়েন পাওয়া যায়নি।"
        
    send_telegram_message(tg_msg)

def start_background_loop():
    while True:
        try:
            asyncio.run(scan_process())
        except Exception as e:
            print(f"Background Daemon Loop Error: {e}")
        time.sleep(900)

# প্রথমবার চালুর সময় ব্যাকগ্রাউন্ড থ্রেড তৈরি করা
if 'thread_started' not in st.session_state:
    st.session_state.thread_started = True
    bg_thread = threading.Thread(target=start_background_loop, daemon=True)
    bg_thread.start()

# --- FRONTEND UI RENDERING ---

if "🔍 স্ক্যানিং" in global_data["current_progress"]:
    progress_placeholder.markdown(f"""
        <div class="scanning-box">
            <p style="color: #38bdf8; font-size: 1.1rem; margin-bottom: 2px; font-weight: 600;">
                {global_data["current_progress"]}
            </p>
            <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 5px;">বর্তমানে স্ক্যান হচ্ছে:</p>
            <div class="scanning-coin">🔄 {global_data["active_coin"]}</div>
        </div>
    """, unsafe_allow_html=True)
else:
    progress_placeholder.info(f"🟢 লাইভ ইঞ্জিন স্ট্যাটাস: {global_data['current_progress']}")

with metrics_placeholder.container():
    col1, col2, col3 = st.columns(3)
    col1.metric("মোট ফিল্টারড কয়েন", global_data["total_scanned"])
    col2.metric("200 EMA বুলিশ কয়েন", len(global_data["bullish_coins"]))
    col3.metric("সর্বশেষ ডাটা সিঙ্ক", global_data["last_scan_time"])

if global_data["bullish_coins"]:
    df_result = pd.DataFrame(global_data["bullish_coins"])
    
    def make_binance_link(symbol):
        clean_symbol = symbol.replace('/', '')
        url = f"https://www.binance.com/en/futures/{clean_symbol}"
        return f'<a href="{url}" target="_blank" class="binance-btn">🔗 Trade</a>'
    
    df_result['Action'] = df_result['Symbol'].apply(make_binance_link)
    table_html = df_result.to_html(escape=False, index=False, classes='table table-dark')
    
    with table_placeholder.container():
        st.markdown("### 📈 কমপ্যাক্ট টপ ১০০ বুলিশ ড্যাশবোর্ড")
        st.markdown(table_html, unsafe_allow_html=True)
else:
    table_placeholder.warning("এখনো কোনো বুলিশ কয়েন রেকর্ড হয়নি। প্রথম রাউন্ড স্ক্যান প্রোগ্রেস সম্পন্ন হওয়া পর্যন্ত অপেক্ষা করুন (সর্বোচ্চ ৩০-৪০ সেকেন্ড)।")

# ডাটা ম্যানুয়ালি বা রিয়েল-টাইমে রিলোড করার বাটন
if st.button("🔄 ড্যাশবোর্ড ডাটা আপডেট করুন"):
    st.rerun()
