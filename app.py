import streamlit as st
import ccxt.async_support as ccxt  # স্ট্যান্ডার্ড এসিনক্রোনাস সাপোর্ট
import asyncio
import pandas as pd
from datetime import datetime
import httpx  # CoinGecko ও Telegram API কলের জন্য

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
    .scanning-box {
        background: rgba(17, 24, 39, 0.85);
        border: 2px solid #38bdf8;
        box-shadow: 0px 0px 25px rgba(56, 189, 248, 0.4);
        padding: 20px;
        border-radius: 16px;
        text-align: center;
        margin: 20px 0;
    }
    .coin-list-text {
        font-size: 1.1rem !important;
        font-weight: 600;
        color: #ff007f !important;
        letter-spacing: 1px;
        background: rgba(255, 0, 127, 0.1);
        padding: 10px;
        border-radius: 8px;
        border: 1px dashed rgba(255, 0, 127, 0.3);
        margin-top: 10px;
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
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Premium Binance Futures 200 EMA Scanner")
st.write("১৫ মিনিট পর পর টপ ৩৫০টি ফিউচার কয়েন অটো-স্ক্যান করে ২০০ EMA এর উপরের কয়েনগুলো নিচে লাইভ আপডেট করে এবং টেলিগ্রামে মেসেজ পাঠায়।")

live_status_box = st.empty()
metrics_placeholder = st.empty()
table_placeholder = st.empty()

# --- HELPER FUNCTIONS ---

async def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10.0)
    except Exception:
        pass

def generate_binance_url(symbol):
    clean_symbol = symbol.split(':')[0].replace('/', '')
    return f"https://www.binance.com/en/futures/{clean_symbol}"

# --- COINGECKO API FOR TOP COINS (NO BLOCKING) ---

async def fetch_top_350_from_coingecko():
    """মার্কেট ক্যাপ অনুযায়ী ক্র্যাশ-ফ্রি কয়েন লিস্ট কোইনগেকো থেকে নিয়ে আসবে"""
    try:
        async with httpx.AsyncClient() as client:
            # আমেরিকার সার্ভার আইপি থেকে কয়েনগেকো ব্লক করে না
            url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1"
            response = await client.get(url, timeout=15.0)
            
            url2 = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=2"
            response2 = await client.get(url2, timeout=15.0)
            
            symbols = []
            if response.status_code == 200:
                for coin in response.json():
                    sym = coin['symbol'].upper()
                    # স্টেবল কয়েন বাদ দেওয়া হচ্ছে
                    if sym not in ['USDT', 'USDC', 'BUSD', 'DAI', 'FDUSD']:
                        symbols.append(f"{sym}/USDT:USDT")
                        
            if response2.status_code == 200:
                for coin in response2.json():
                    sym = coin['symbol'].upper()
                    if sym not in ['USDT', 'USDC', 'BUSD', 'DAI', 'FDUSD']:
                        symbols.append(f"{sym}/USDT:USDT")
                        
            return symbols[:350]
    except Exception as e:
        st.error(f"CoinGecko API এরর: {e}")
    return []

async def fetch_and_calculate_ema(exchange, symbol):
    """নির্দিষ্ট কয়েনের ওহী ও পিওর পান্ডাস দিয়ে ২০০ EMA হিসাব করে"""
    try:
        # ওহী ডাটার জন্য আমরা বাইনান্সের অফিশিয়াল চার্ট ডিরেক্টরি রিকোয়েস্ট পাঠাবো
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=250)
        if len(ohlcv) < 200:
            return None
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
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
        # বাইনান্স এপিআই লোড করার জন্য অল্টারনেটিভ গ্লোবাল পাবলিক গেটওয়ে
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'urls': {
                'api': {
                    'public': 'https://api.binance.vision/api/v3',
                    'fapi': 'https://fapi.binance.com',
                }
            },
            'options': {'defaultType': 'swap'}
        })
        
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            live_status_box.markdown(f"### 🔄 নতুন স্ক্যান শুরু হচ্ছে... (সময়: {current_time})")
            
            # এবার কয়েন লিস্ট আসবে ডিরেক্ট CoinGecko থেকে, তাই কোনো এরর আসবে না
            symbols_to_scan = await fetch_top_350_from_coingecko()
            
            if not symbols_to_scan:
                st.warning("কয়েন লিস্ট লোড করা যায়নি। ৩০ সেকেন্ড পর আবার চেষ্টা করা হচ্ছে...")
                await asyncio.sleep(30)
                continue
                
            bullish_coins = []
            total_coins = len(symbols_to_scan)
            
            batch_size = 10
            for i in range(0, total_coins, batch_size):
                batch = symbols_to_scan[i:i+batch_size]
                running_coin_names = ", ".join([sym.split('/')[0] for sym in batch])
                progress_perc = int(((i + len(batch)) / total_coins) * 100)
                
                live_status_box.markdown(f"""
                    <div class="scanning-box">
                        <p style="color: #38bdf8; font-size: 1.2rem; margin-bottom: 5px; font-weight: 600;">
                            🔍 বর্তমান স্ক্যানিং প্রোগ্রেস: {progress_perc}% ({min(i+batch_size, total_coins)}/{total_coins})
                        </p>
                        <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 5px;">বর্তমানে নিচের ১০টি কয়েন স্ক্যান করা হচ্ছে:</p>
                        <div class="coin-list-text">{running_coin_names}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                tasks = [fetch_and_calculate_ema(exchange, symbol) for symbol in batch]
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    if res:
                        bullish_coins.append(res)
                
                await asyncio.sleep(0.3)  # রেট লিমিট এড়াতে সামান্য বিরতি
            
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
                
                # --- টেলিগ্রাম চ্যাঙ্ক নোটিফিকেশন ---
                header = f"🚨 <b>Binance 200 EMA Scanner Report</b> 🚨\n📅 সময়: {current_time}\n📊 মোট কয়েন: {total_coins}\n🔥 বুলিশ: {len(bullish_coins)}\n\n"
                current_chunk = header
                for coin in bullish_coins:
                    trade_url = generate_binance_url(coin['Symbol'])
                    coin_name = coin['Symbol'].split(':')[0]
                    coin_text = f"🔹 <b>{coin_name}</b>\n   • মূল্য: {coin['Price']}\n   • ২০০ EMA: {coin['200 EMA']}\n   • ব্যবধান: {coin['Distance (%)']}%\n   • <a href='{trade_url}'>🔗 Trade Here</a>\n\n"
                    
                    if len(current_chunk) + len(coin_text) > 3000:
                        await send_telegram_message(current_chunk)
                        await asyncio.sleep(0.5)
                        current_chunk = "<b>📈 Report (Continued...)</b>\n\n" + coin_text
                    else:
                        current_chunk += coin_text
                
                if current_chunk != header:
                    await send_telegram_message(current_chunk)
            else:
                with table_placeholder.container():
                    st.warning("এই মুহূর্তে ২০০ EMA এর উপরে কোনো কয়েন পাওয়া যায়নি।")
            
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
