import streamlit as st
import ccxt.pro as ccxtpro
import asyncio
import pandas as pd
import requests
import time
from datetime import datetime

# --- TELEGRAM CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8957518460:AAE_9HaugsNNYfjOzCpbHi2nJAEKf4GSiKs"
TELEGRAM_CHAT_ID = "6166836299"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(page_title="24/7 Binance EMA Scanner", layout="wide")

# --- UI DESIGN / LUXURY COMPACT CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #090d16 0%, #111827 100%); color: #f8fafc; }
    h1 { color: #00d2ff !important; background: linear-gradient(to right, #00ffff, #0088ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-family: 'Inter', sans-serif; font-weight: 900 !important; text-shadow: 0px 0px 20px rgba(0, 255, 255, 0.3); margin-bottom: 5px !important; }
    .scanning-box { background: rgba(17, 24, 39, 0.85); border: 2px solid #38bdf8; box-shadow: 0px 0px 15px rgba(56, 189, 248, 0.3); padding: 15px; border-radius: 12px; text-align: center; margin: 10px 0; }
    .scanning-coin { font-size: 2.2rem !important; font-weight: 800; color: #ff007f !important; text-shadow: 0 0 10px rgba(255, 0, 127, 0.5); }
    div[data-testid="metric-container"] { background-color: #111827; border: 1px solid #1f2937; padding: 10px 15px; border-radius: 10px; }
    .dataframe { font-size: 13px !important; width: 100% !important; border-collapse: collapse !important; }
    .dataframe th { background-color: #1f2937 !important; color: #00d2ff !important; padding: 6px !important; }
    .dataframe td { padding: 5px !important; border-bottom: 1px solid #1f2937 !important; }
    .binance-btn { display: inline-block; padding: 3px 8px; background: linear-gradient(135deg, #f3ba2f 0%, #d49b00 100%); color: #000 !important; font-weight: bold; font-size: 11px; border-radius: 4px; text-decoration: none; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Premium Binance 24/7 Top 100 Scanner")
st.write("কানেকশন লিক প্রোটেক্টেড এডিশন। `async with` কনটেক্সট ম্যানেজার দ্বারা এপিআই সেশন সম্পূর্ণ নিরাপদ করা হয়েছে।")

# সেশন স্টেট ইনিশিয়ালাইজেশন
if "last_scan_time" not in st.session_state:
    st.session_state.last_scan_time = "এখনো স্ক্যান হয়নি"
    st.session_state.bullish_coins = []
    st.session_state.total_scanned = 0
    st.session_state.current_progress = "স্ট্যান্ডবাই (স্ক্যান শুরু করার জন্য নিচের বাটনে চাপুন)"
    st.session_state.active_coin = "None"
    st.session_state.is_scanning = False

# --- CORE SCANNING FUNCTIONS ---

async def fetch_top_100_futures(exchange):
    try:
        markets = await exchange.fetch_markets()
        futures_pairs = [m['symbol'] for m in markets if m.get('active') and m.get('linear') and m.get('swap') and m.get('settle') == 'USDT']
        tickers = await exchange.fetch_tickers(futures_pairs)
        sorted_tickers = sorted(tickers.values(), key=lambda x: x.get('quoteVolume', 0) if x.get('quoteVolume') is not None else 0, reverse=True)
        return [ticker['symbol'] for ticker in sorted_tickers[:100]]
    except Exception as e:
        print(f"Market Sync Error: {e}")
        return []

async def fetch_and_calculate_ema(exchange, symbol):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=250)
        if len(ohlcv) < 200: return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        last_close = df['close'].iloc[-1]
        last_ema = df['ema_200'].iloc[-1]
        if not pd.isna(last_ema) and last_close > last_ema:
            return {"Symbol": symbol.split(':')[0], "Price": last_close, "200 EMA": round(last_ema, 4), "Distance (%)": round(((last_close - last_ema) / last_ema) * 100, 2)}
    except: pass
    return None

async def run_single_scan():
    st.session_state.is_scanning = True
    
    # কনফিগারেশন সেটআপ
    exchange_config = {
        'enableRateLimit': True, 
        'options': {
            'defaultType': 'future', 
            'adjustForTimeDifference': True
        }
    }
    
    # 'async with' ব্যবহার করার ফলে ফাংশন শেষ হওয়া মাত্রই সেশন, কানেক্টর সব ১০০% ক্লোজ হতে বাধ্য
    async with ccxtpro.binance(exchange_config) as exchange:
        try:
            symbols_to_scan = await fetch_top_100_futures(exchange)
            
            if not symbols_to_scan:
                st.session_state.is_scanning = False
                return

            bullish_list = []
            total_coins = len(symbols_to_scan)
            st.session_state.total_scanned = total_coins
            
            batch_size = 5
            for i in range(0, total_coins, batch_size):
                batch = symbols_to_scan[i:i+batch_size]
                perc = int(((i + len(batch)) / total_coins) * 100)
                st.session_state.active_coin = batch[0].split('/')[0]
                st.session_state.current_progress = f"🔍 স্ক্যানিং প্রোগ্রেস: {perc}% ({min(i+batch_size, total_coins)}/{total_coins})"
                
                # UI লাইভ আপডেট
                progress_placeholder.markdown(f"""
                    <div class="scanning-box">
                        <p style="color: #38bdf8; font-size: 1.1rem; margin-bottom: 2px; font-weight: 600;">{st.session_state.current_progress}</p>
                        <div class="scanning-coin">🔄 {st.session_state.active_coin}</div>
                    </div>
                """, unsafe_allow_html=True)

                tasks = [fetch_and_calculate_ema(exchange, symbol) for symbol in batch]
                results = await asyncio.gather(*tasks)
                for res in results:
                    if res: bullish_list.append(res)
                await asyncio.sleep(0.1)

            # ডাটা সেশন স্টেটে সংরক্ষণ
            st.session_state.bullish_coins = bullish_list
            st.session_state.last_scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.current_progress = "সম্পন্ন (পরবর্তী লাইভ রান ১৫ মিনিট পর অটোমেটিক শুরু হবে)"
            
            # --- TELEGRAM ALERTS ---
            if bullish_list:
                tg_msg = f"🔔 *Binance 15M Top 100 EMA Report*\n⏰ সময়: `{st.session_state.last_scan_time}`\n📊 মোট স্ক্যান: `{total_coins}` | বুলিশ কয়েন: `{len(bullish_list)}`\n\n"
                for coin in bullish_list[:25]:
                    tg_msg += f"• `{coin['Symbol']}`: ${coin['Price']} (+{coin['Distance (%)']}%)\n"
            else:
                tg_msg = f"ℹ️ *Binance Scan Completed*\n⏰ সময়: `{st.session_state.last_scan_time}`\nকোনো বুলিশ কয়েন পাওয়া যায়নি।"
            send_telegram_message(tg_msg)

        except Exception as scan_error:
            print(f"Scan Loop Error: {scan_error}")
            
    # সেশন রিলিজ প্রসেস নিশ্চিত করতে এবং রিফ্রেশ ব্লকিং এড়াতে ০.৩ সেকেন্ডের একটি গ্যাপ
    await asyncio.sleep(0.3)
    st.session_state.is_scanning = False
    st.session_state.active_coin = "FINISHED"

# --- UI RENDER CORNER ---

progress_placeholder = st.empty()

# রিয়েল-টাইম কাউন্টার ও স্ট্যাটাস রেন্ডারার
@st.fragment(run_every=10)
def render_live_dashboard():
    if not st.session_state.is_scanning and st.session_state.last_scan_time != "এখনো স্ক্যান হয়নি":
        # চেক করা হচ্ছে ১৫ মিনিট পার হয়েছে কিনা
        last_time = datetime.strptime(st.session_state.last_scan_time, "%Y-%m-%d %H:%M:%S")
        elapsed_seconds = (datetime.now() - last_time).total_seconds()
        if elapsed_seconds >= 900:  
            with st.spinner("১৫ মিনিট পূর্ণ হয়েছে! নতুন স্ক্যান শুরু হচ্ছে..."):
                asyncio.run(run_single_scan())
                st.rerun()

    if st.session_state.is_scanning:
        progress_placeholder.markdown(f"""
            <div class="scanning-box">
                <p style="color: #38bdf8; font-size: 1.1rem; margin-bottom: 2px; font-weight: 600;">{st.session_state.current_progress}</p>
                <div class="scanning-coin">🔄 {st.session_state.active_coin}</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        progress_placeholder.info(f"🟢 লাইভ ইঞ্জিন স্ট্যাটাস: {st.session_state.current_progress}")

    col1, col2, col3 = st.columns(3)
    col1.metric("মোট ফিল্টারড কয়েন", st.session_state.total_scanned)
    col2.metric("200 EMA বুলিশ কয়েন", len(st.session_state.bullish_coins))
    col3.metric("সর্বশেষ ডাটা সিঙ্ক", st.session_state.last_scan_time)

    if st.session_state.bullish_coins:
        df_result = pd.DataFrame(st.session_state.bullish_coins)
        df_result['Action'] = df_result['Symbol'].apply(lambda x: f'<a href="https://www.binance.com/en/futures/{x}USDT" target="_blank" class="binance-btn">🔗 Trade</a>')
        table_html = df_result.to_html(escape=False, index=False, classes='table table-dark')
        st.markdown("### 📈 কমপ্যাক্ট টপ ১০০ বুলিশ ড্যাশবোর্ড")
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.warning("এখনো কোনো বুলিশ কয়েন রেকর্ড হয়নি। নিচে 'ম্যানুয়ালি স্ক্যান শুরু করুন' বাটনে ক্লিক করুন।")

# ড্যাশবোর্ড রেন্ডার
render_live_dashboard()

# ম্যানুয়াল ট্রিগার বাটন
if not st.session_state.is_scanning:
    if st.button("🚀 ম্যানুয়ালি স্ক্যান শুরু করুন (Force Run)"):
        with st.spinner("প্রথম রাউন্ড স্ক্যান চলছে..."):
            asyncio.run(run_single_scan())
            st.rerun()
