import streamlit as st
import ccxt.pro as ccxtpro  # Fast Async Binance Call এর জন্য
import asyncio
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime

# Streamlit Page Configuration
st.set_page_config(page_title="Binance 200 EMA Scanner", layout="wide")

# --- UI DESIGN / LUXURY CUSTOM CSS ---
st.markdown("""
    <style>
    /* Main Theme - ডার্ক লাক্সারি ব্যাকগ্রাউন্ড */
    .stApp {
        background: linear-gradient(135deg, #090d16 0%, #111827 100%);
        color: #f8fafc;
    }
    
    /* Glowing Title - টেক্সটে নিয়ন গ্রেডিয়েন্ট এবং শ্যাডো */
    h1 {
        color: #00d2ff !important;
        background: linear-gradient(to right, #00ffff, #0088ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Inter', sans-serif;
        font-weight: 900 !important;
        text-shadow: 0px 0px 20px rgba(0, 255, 255, 0.3);
    }
    
    /* Sidebar Border & Dark Theme */
    [data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1f2937;
    }
    
    /* Live Scanning Card Styling */
    .scanning-box {
        background: rgba(17, 24, 39, 0.85);
        border: 2px solid #38bdf8;
        box-shadow: 0px 0px 25px rgba(56, 189, 248, 0.4);
        padding: 25px;
        border-radius: 16px;
        text-align: center;
        margin: 20px 0;
        animation: pulse 1.5s infinite alternate;
    }
    
    /* Glowing Scanning Coin */
    .scanning-coin {
        font-size: 3rem !important;
        font-weight: 800;
        color: #ff007f !important;
        text-shadow: 0 0 15px rgba(255, 0, 127, 0.6);
        letter-spacing: 2px;
    }
    
    /* Pulse Animation Logic */
    @keyframes pulse {
        0% { transform: scale(0.99); box-shadow: 0 0 15px rgba(56, 189, 248, 0.3); }
        100% { transform: scale(1.01); box-shadow: 0 0 30px rgba(56, 189, 248, 0.6); }
    }
    
    /* Premium Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #ff007f 0%, #7928ca 100%) !important;
        color: white !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
        padding: 14px 30px !important;
        border-radius: 10px !important;
        border: none !important;
        box-shadow: 0 4px 20px rgba(255, 0, 127, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(255, 0, 127, 0.7) !important;
    }
    
    /* Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 20px;
        border-radius: 14px;
    }

    /* Custom Stylish Table Link */
    .binance-btn {
        display: inline-block;
        padding: 6px 12px;
        background: linear-gradient(135deg, #f3ba2f 0%, #d49b00 100%);
        color: #000 !important;
        font-weight: bold;
        border-radius: 6px;
        text-decoration: none;
        transition: 0.2s;
    }
    .binance-btn:hover {
        transform: scale(1.05);
        box-shadow: 0 0 10px rgba(243, 186, 47, 0.6);
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Premium Binance Futures 200 EMA Scanner")
st.write("১৫ মিনিট পর পর টপ ৩৫০টি ফিউচার কয়েন অটো-স্ক্যান করে ২০0 EMA এর উপরের কয়েনগুলো নিচে লাইভ আপডেট করে।")

# Placeholder elements for live data updating
live_status_box = st.empty()
metrics_placeholder = st.empty()
table_placeholder = st.empty()

# --- ASYNC CORE FUNCTIONS ---

async def fetch_top_350_futures(exchange):
    """২৪ ঘণ্টার ভলিউম অনুযায়ী টপ ৩৫০টি ফিউচার পেয়ার নিয়ে আসে"""
    try:
        markets = await exchange.load_markets()
        # শুধু USDT ফিউচার পেয়ার ফিল্টার (যেমন: BTC/USDT:USDT বা BTC/USDT)
        futures_pairs = [
            symbol for symbol, market in markets.items() 
            if market['linear'] and market['settle'] == 'USDT' and market['active']
        ]
        
        tickers = await exchange.fetch_tickers(futures_pairs)
        # ভলিউম অনুযায়ী সর্ট করা
        sorted_tickers = sorted(
            tickers.values(), 
            key=lambda x: x.get('quoteVolume', 0) if x.get('quoteVolume') is not None else 0, 
            reverse=True
        )
        
        top_350 = [ticker['symbol'] for ticker in sorted_tickers[:350]]
        return top_350
    except Exception as e:
        st.error(f"মার্কেট ডাটা লোড করতে সমস্যা হয়েছে: {e}")
        return []

async def fetch_and_calculate_ema(exchange, symbol):
    """নির্দিষ্ট কয়েনের ওহী ও EMA হিসাব করে (আইপি সেফ স্লিপসহ)"""
    try:
        # ১৫ মিনিটের টাইমফ্রেমের জন্য কমপক্ষে ২০০+ ক্যান্ডেল লাগবে (আমরা ২৫০টি নিচ্ছি)
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=250)
        if len(ohlcv) < 200:
            return None
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        last_close = df['close'].iloc[-1]
        last_ema = df['ema_200'].iloc[-1]
        
        if pd.isna(last_ema):
            return None
            
        # কন্ডিশন: বর্তমান ক্লোজিং প্রাইস ২০০ EMA এর উপরে কি না
        if last_close > last_ema:
            return {
                "Symbol": symbol,
                "Price": last_close,
                "200 EMA": round(last_ema, 4),
                "Distance (%)": round(((last_close - last_ema) / last_ema) * 100, 2)
            }
    except Exception:
        # কোনো কারণে এপিআই এরর দিলে স্কিপ করবে (আইপি ব্লকিং প্রোটেকশন)
        pass
    return None

async def run_scanner():
    """মূল স্ক্যানিং প্রসেস যা লুপ আকারে চলবে"""
    # Async সংযোগ তৈরি
    exchange = ccxtpro.binance({
        'enableRateLimit': True,  # বিল্ট-ইন রেট লিমিটার অন (আইপি ব্লক প্রতিরোধক)
        'options': {'defaultType': 'future'}
    })
    
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            live_status_box.markdown(f"### 🔄 নতুন স্ক্যান শুরু হচ্ছে... (সময়: {current_time})")
            
            # টপ ৩৫০ কয়েন রিফ্রেশ
            symbols_to_scan = await fetch_top_350_futures(exchange)
            if not symbols_to_scan:
                await asyncio.sleep(10)
                continue
                
            bullish_coins = []
            total_coins = len(symbols_to_scan)
            
            # ফাস্ট এবং আইপি-সেফ ব্যাচ স্ক্যানিং
            # একসাথে ১০টি করে রিকোয়েস্ট পাঠানো হবে যাতে ফাস্ট হয় এবং আইপি ব্লক না খায়
            batch_size = 10
            for i in range(0, total_coins, batch_size):
                batch = symbols_to_scan[i:i+batch_size]
                
                # লাইভ পপ-আপ অ্যানিমেশন বক্স আপডেট (ব্যাচের প্রথম কয়েন নাম দিয়ে)
                progress_perc = int(((i + len(batch)) / total_coins) * 100)
                live_status_box.markdown(f"""
                    <div class="scanning-box">
                        <p style="color: #38bdf8; font-size: 1.2rem; margin-bottom: 5px; font-weight: 600;">
                            🔍 বর্তমান স্ক্যানিং প্রোগ্রেস: {progress_perc}% ({min(i+batch_size, total_coins)}/{total_coins})
                        </p>
                        <div class="scanning-coin">{batch[0].split('/')[0]}</div>
                        <p style="color: #64748b; font-size: 0.9rem; margin-top: 5px;">
                            বাইনান্স সার্ভার কুলডাউন বিরতি ও সেফ মোড সক্রিয়...
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
                # ব্যাচ ওয়াইজ সমান্তরাল টাস্ক রান
                tasks = [fetch_and_calculate_ema(exchange, symbol) for symbol in batch]
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    if res:
                        bullish_coins.append(res)
                
                # আইপি রেট লিমিট প্রটেকশনের জন্য সামান্য মাইক্রো-বিরতি
                await asyncio.sleep(0.2)
            
            # স্ক্যান শেষে প্রোগ্রেস বক্স ক্লিয়ার
            live_status_box.empty()
            
            # --- মেট্রিক্স ও টেবিল ডিসপ্লে আপডেট ---
            with metrics_placeholder.container():
                col1, col2 = st.columns(2)
                col1.metric("মোট স্ক্যান করা কয়েন", total_coins)
                col2.metric("200 EMA-এর উপরে বুলিশ কয়েন", len(bullish_coins))
            
            if bullish_coins:
                df_result = pd.DataFrame(bullish_coins)
                
                # সরাসরি বাইন্যান্স ফিউচার ট্রেডিং লিঙ্ক জেনারেট করার লজিক
                def make_binance_link(symbol):
                    clean_symbol = symbol.replace('/', '').split(':')[0] # e.g., BTCUSDT
                    url = f"https://www.binance.com/en/futures/{clean_symbol}"
                    return f'<a href="{url}" target="_blank" class="binance-btn">🔗 Trade on Binance</a>'
                
                df_result['Action'] = df_result['Symbol'].apply(make_binance_link)
                
                # ডাটাফ্রেমকে আকর্ষনীয় HTML টেবিলে রূপান্তর
                table_html = df_result.to_html(escape=False, index=False, classes='table table-dark')
                
                with table_placeholder.container():
                    st.markdown(f"### 📈 বুলিশ কয়েন লিস্ট (Last Update: {datetime.now().strftime('%H:%M:%S')})")
                    st.markdown(table_html, unsafe_allow_html=True)
            else:
                with table_placeholder.container():
                    st.warning("এই মুহূর্তে ২০০ EMA এর উপরে কোনো কয়েন পাওয়া যায়নি।")
            
            # ১৫ মিনিট (৯০০ সেকেন্ড) বিরতি পরবর্তী লাইভ স্ক্যানের জন্য
            st.info("⏱️ স্ক্যান সম্পন্ন হয়েছে। পরবর্তী স্ক্যান ১৫ মিনিট পর স্বয়ংক্রিয়ভাবে শুরু হবে।")
            await asyncio.sleep(900)
            
        except Exception as e:
            st.error(f"লুপে সমস্যা হয়েছে: {e}")
            await asyncio.sleep(30) # এরর খেলে ৩০ সেকেন্ড পর আবার চেষ্টা করবে

# Streamlit App Execution
if __name__ == "__main__":
    # Async লুপ হ্যান্ডেলিং
    try:
        asyncio.run(run_scanner())
    except RuntimeError:
        # যদি অলরেডি ইভেন্ট লুপ চলতে থাকে (Streamlit রি-রান কেস)
        loop = asyncio.get_event_loop()
        loop.create_task(run_scanner())
