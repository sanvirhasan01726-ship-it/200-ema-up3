import streamlit as st
import ccxt.async_support as ccxt  # স্ট্যান্ডার্ড এসিনক্রোনাস সাপোর্ট
import asyncio
import pandas as pd
from datetime import datetime
import httpx  # Async Telegram API রিকোয়েস্টের জন্য

# Streamlit Page Configuration
st.set_page_config(page_title="Binance 200 EMA Scanner", layout="wide")

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "8957518460:AAE_9HaugsNNYfjOzCpbHi2nJAEKf4GSiKs"
TELEGRAM_CHAT_ID = "6166836299"

# --- UI DESIGN / LUXURY CUSTOM CSS ---
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
    }
    [data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1f2937;
    }
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
    .scanning-coin {
        font-size: 3rem !important;
        font-weight: 800;
        color: #ff007f !important;
        text-shadow: 0 0 15px rgba(255, 0, 127, 0.6);
        letter-spacing: 2px;
    }
    @keyframes pulse {
        0% { transform: scale(0.99); box-shadow: 0 0 15px rgba(56, 189, 248, 0.3); }
        100% { transform: scale(1.01); box-shadow: 0 0 30px rgba(56, 189, 248, 0.6); }
    }
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
    div[data-testid="metric-container"] {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 20px;
        border-radius: 14px;
    }
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
st.write("১৫ মিনিট পর পর টপ ৩৫০টি ফিউচার কয়েন অটো-স্ক্যান করে ২০০ EMA এর উপরের কয়েনগুলো নিচে লাইভ আপডেট করে এবং টেলিগ্রামে মেসেজ পাঠায়।")

# Placeholder elements for live data updating
live_status_box = st.empty()
metrics_placeholder = st.empty()
table_placeholder = st.empty()

# --- HELPER FUNCTIONS ---

async def send_telegram_message(message: str):
    """টেলিগ্রাম বটে মেসেজ পাঠানোর জন্য এসিনক্রোনাস ফাংশন"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            if response.status_code != 200:
                st.error(f"টেলিগ্রাম মেসেজ পাঠাতে ব্যর্থ: {response.text}")
    except Exception as e:
        st.error(f"টেলিগ্রাম এপিআই ত্রুটি: {e}")

def generate_binance_url(symbol):
    """কয়েন সিম্বল থেকে ট্রেডিং ইউআরএল জেনারেট করার সাধারণ ফাংশন"""
    clean_symbol = symbol.split(':')[0].replace('/', '')
    return f"https://www.binance.com/en/futures/{clean_symbol}"

# --- ASYNC CORE FUNCTIONS ---

async def fetch_top_350_futures(exchange):
    """২৪ ঘণ্টার ভলিউম অনুযায়ী পার্পেচুয়াল সোয়াপ (USDT-M Futures) পেয়ার নিয়ে আসে"""
    try:
        markets = await exchange.load_markets()
        
        futures_pairs = []
        for symbol, market in markets.items():
            if market.get('active') and market.get('linear') and market.get('swap'):
                if market.get('settle') == 'USDT':
                    futures_pairs.append(symbol)
        
        tickers = await exchange.fetch_tickers(futures_pairs)
        
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
    """নির্দিষ্ট কয়েনের ওহী ও পিওর পান্ডাস দিয়ে ২০০ EMA হিসাব করে"""
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=250)
        if len(ohlcv) < 200:
            return None
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # pandas_ta এর বদলে পিওর পান্ডাস দিয়ে দ্রুত ও নিখুঁত EMA বের করার লজিক
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        last_close = df['close'].iloc[-1]
        last_ema = df['ema_200'].iloc[-1]
        
        if pd.isna(last_ema):
            return None
            
        if last_close > last_ema:
            return {
                "Symbol": symbol,
                "Price": last_close,
                "200 EMA": round(last_ema, 4),
                "Distance (%)": round(((last_close - last_ema) / last_ema) * 100, 2)
            }
    except Exception:
        pass
    return None

async def run_scanner():
    """মূল স্ক্যানিং প্রসেস যা লুপ আকারে চলবে"""
    while True:
        # ক্লাউড সার্ভারের রেস্ট্রিকশন এড়াতে অল্টারনেটিভ ইউএসএ/গ্লোবাল এপিআই গেটওয়ে সেট করা হলো
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'urls': {
                'api': {
                    'public': 'https://api.binance4.com/api/v3',  # ইউএসএ ফ্রেন্ডলি অল্টারনেটিভ এন্ডপয়েন্ট
                    'fapi': 'https://fapi.binance.com',            # ফিউচারস এপিআই মেইন গেটওয়ে
                }
            },
            'options': {
                'defaultType': 'swap'
            }
        })
        
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            live_status_box.markdown(f"### 🔄 নতুন স্ক্যান শুরু হচ্ছে... (সময়: {current_time})")
            
            symbols_to_scan = await fetch_top_350_futures(exchange)
            if not symbols_to_scan:
                await asyncio.sleep(10)
                continue
                
            bullish_coins = []
            total_coins = len(symbols_to_scan)
            
            batch_size = 10
            for i in range(0, total_coins, batch_size):
                batch = symbols_to_scan[i:i+batch_size]
                
                progress_perc = int(((i + len(batch)) / total_coins) * 100)
                live_status_box.markdown(f"""
                    <div class="scanning-box">
                        <p style="color: #38bdf8; font-size: 1.2rem; margin-bottom: 5px; font-weight: 600;">
                            🔍 বর্তমান স্ক্যানিং প্রোগ্রেস: {progress_perc}% ({min(i+batch_size, total_coins)}/{total_coins})
                        </p>
                        <div class="scanning-coin">{batch[0].split('/')[0]}</div>
                        <p style="color: #64748b; font-size: 0.9rem; margin-top: 5px;">
                            বাইনান্স সার্ভার কুলডাউন বিরতি ও সেф মোড সক্রিয়...
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
                tasks = [fetch_and_calculate_ema(exchange, symbol) for symbol in batch]
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    if res:
                        bullish_coins.append(res)
                
                await asyncio.sleep(0.2)
            
            live_status_box.empty()
            
            with metrics_placeholder.container():
                col1, col2 = st.columns(2)
                col1.metric("মোট স্ক্যান করা কয়েন", total_coins)
                col2.metric("200 EMA-এর উপরে বুলিশ কয়েন", len(bullish_coins))
            
            if bullish_coins:
                df_result = pd.DataFrame(bullish_coins)
                df_result['Action'] = df_result['Symbol'].apply(
                    lambda sym: f'<a href="{generate_binance_url(sym)}" target="_blank" class="binance-btn">🔗 Trade on Binance</a>'
                )
                
                table_html = df_result.to_html(escape=False, index=False, classes='table table-dark')
                
                with table_placeholder.container():
                    st.markdown(f"### 📈 বুলিশ কয়েন লিস্ট (Last Update: {datetime.now().strftime('%H:%M:%S')})")
                    st.markdown(table_html, unsafe_allow_html=True)
                
                # --- টেলিগ্রাম সেফ মেসেজ জেনারেশন (Chunks) ---
                header = f"🚨 <b>Binance 200 EMA Scanner Report</b> 🚨\n"
                header += f"📅 সময়: {current_time}\n"
                header += f"📊 মোট স্ক্যান করা কয়েন: {total_coins}\n"
                header += f"🔥 বুলিশ কয়েন পাওয়া গেছে: {len(bullish_coins)}\n\n"
                header += "<b>📈 কয়েনসমূহের তালিকা (Price > 200 EMA):</b>\n"
                header += "--------------------------------------\n"
                
                current_chunk = header
                chunk_count = 1
                
                for coin in bullish_coins:
                    trade_url = generate_binance_url(coin['Symbol'])
                    coin_name = coin['Symbol'].split(':')[0]
                    
                    coin_text = f"🔹 <b>{coin_name}</b>\n"
                    coin_text += f"   • মূল্য: {coin['Price']}\n"
                    coin_text += f"   • ২০০ EMA: {coin['200 EMA']}\n"
                    coin_text += f"   • ব্যবধান: {coin['Distance (%)']}%\n"
                    coin_text += f"   • <a href='{trade_url}'>🔗 Trade Here</a>\n\n"
                    
                    if len(current_chunk) + len(coin_text) > 3000:
                        await send_telegram_message(current_chunk + f"<i>[Part {chunk_count}]</i>")
                        await asyncio.sleep(0.5)
                        current_chunk = f"<b>📈 200 EMA Scanner Report (Continued...)</b>\n--------------------------------------\n\n" + coin_text
                        chunk_count += 1
                    else:
                        current_chunk += coin_text
                
                if current_chunk != header:
                    if chunk_count > 1:
                        await send_telegram_message(current_chunk + f"<i>[Part {chunk_count} - End]</i>")
                    else:
                        await send_telegram_message(current_chunk)
                    
            else:
                with table_placeholder.container():
                    st.warning("এই মুহূর্তে ২০০ EMA এর উপরে কোনো কয়েন পাওয়া যায়নি।")
                
                empty_msg = f"🔄 <b>Scanner Update ({current_time}):</b>\nএই মুহূর্তে ২০০ EMA এর উপরে কোনো বুলিশ কয়েন পাওয়া যায়নি।"
                await send_telegram_message(empty_msg)
            
            st.info("⏱️ স্ক্যান সম্পন্ন হয়েছে। পরবর্তী স্ক্যান ১৫ মিনিট পর স্বয়ংক্রিয়ভাবে শুরু হবে।")
            await asyncio.sleep(900)
            
        except Exception as e:
            st.error(f"লুপে সমস্যা হয়েছে: {e}")
            await asyncio.sleep(30)
            
        finally:
            await exchange.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_scanner())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(run_scanner())
