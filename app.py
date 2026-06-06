import streamlit as st
import ccxt.async_support as ccxt  # স্ট্যান্ডার্ড এসিনক্রোনাস সাপোর্ট
import asyncio
import pandas as pd
from datetime import datetime
import httpx  # CoinGecko ও Telegram API কলের জন্য

# Streamlit Page Configuration
st.set_page_config(page_title="Binance 200 EMA Dual Scanner", layout="wide")

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
        padding: 15px;
        border-radius: 12px;
    }
    /* কালার কোডিং স্টাইল */
    .status-up {
        color: #00ffcc !important;
        font-weight: bold;
        background: rgba(0, 255, 204, 0.1);
        padding: 4px 8px;
        border-radius: 4px;
    }
    .status-down {
        color: #ff3366 !important;
        font-weight: bold;
        background: rgba(255, 51, 102, 0.1);
        padding: 4px 8px;
        border-radius: 4px;
    }
    .binance-btn {
        display: inline-block;
        padding: 4px 10px;
        background: linear-gradient(135deg, #f3ba2f 0%, #d49b00 100%);
        color: #000 !important;
        font-weight: bold;
        border-radius: 6px;
        text-decoration: none;
        font-size: 0.9rem;
    }
    /* ছোট কয়েন বক্স টেবিল ফরম্যাট */
    .dataframe {
        font-size: 0.95rem !important;
        width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Premium Binance 200 EMA Dual Scanner")
st.write("১৫ মিনিট পর পর টপ ৩৫০টি ফিউচার কয়েন অটো-স্ক্যান করে ২০০ EMA এর UP (Green) এবং DOWN (Red) কয়েনগুলো আলাদা করে দেখায়।")

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

# --- COINGECKO API FOR TOP COINS ---

async def fetch_top_350_from_coingecko():
    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1"
            response = await client.get(url, timeout=15.0)
            
            url2 = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=2"
            response2 = await client.get(url2, timeout=15.0)
            
            symbols = []
            if response.status_code == 200:
                for coin in response.json():
                    sym = coin['symbol'].upper()
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
    """নির্দিষ্ট কয়েনের ২০০ EMA হিসাব করে UP বা DOWN ট্রেন্ড নির্ধারণ করে"""
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=250)
        if len(ohlcv) < 200:
            return None
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        last_close = df['close'].iloc[-1]
        last_ema = df['ema_200'].iloc[-1]
        
        if pd.isna(last_ema):
            return None
            
        distance = round(((last_close - last_ema) / last_ema) * 100, 2)
        
        # UP এবং DOWN কন্ডিশন আলাদা করা ও কালার কোড জেনারেট করা
        if last_close > last_ema:
            return {
                "Symbol": symbol,
                "Price": last_close,
                "200 EMA": round(last_ema, 4),
                "Distance (%)": distance,
                "Signal": "UP",
                "Status": f'<span class="status-up">🟢 200 EMA UP</span>'
            }
        else:
            return {
                "Symbol": symbol,
                "Price": last_close,
                "200 EMA": round(last_ema, 4),
                "Distance (%)": distance,
                "Signal": "DOWN",
                "Status": f'<span class="status-down">🔴 200 EMA DOWN</span>'
            }
    except Exception:
        pass
    return None

async def run_scanner():
    while True:
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
            live_status_box.markdown(f"### 🔄 নতুন ডুয়াল স্ক্যান শুরু হচ্ছে... (সময়: {current_time})")
            
            symbols_to_scan = await fetch_top_350_from_coingecko()
            
            if not symbols_to_scan:
                st.warning("কয়েন লিস্ট লোড করা যায়নি। ৩০ সেকেন্ড পর আবার চেষ্টা করা হচ্ছে...")
                await asyncio.sleep(30)
                continue
                
            all_scanned_coins = []
            total_coins = len(symbols_to_scan)
            
            batch_size = 10
            for i in range(0, total_coins, batch_size):
                batch = symbols_to_scan[i:i+batch_size]
                running_coin_names = ", ".join([sym.split('/')[0] for sym in batch])
                progress_perc = int(((i + len(batch)) / total_coins) * 100)
                
                live_status_box.markdown(f"""
                    <div class="scanning-box">
                        <p style="color: #38bdf8; font-size: 1.2rem; margin-bottom: 5px; font-weight: 600;">
                            🔍 ডুয়াল স্ক্যানিং প্রোগ্রেস: {progress_perc}% ({min(i+batch_size, total_coins)}/{total_coins})
                        </p>
                        <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 5px;">বর্তমানে নিচের ১০টি কয়েন স্ক্যান করা হচ্ছে:</p>
                        <div class="coin-list-text">{running_coin_names}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                tasks = [fetch_and_calculate_ema(exchange, symbol) for symbol in batch]
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    if res:
                        all_scanned_coins.append(res)
                
                await asyncio.sleep(0.3)
            
            live_status_box.empty()
            
            # UP এবং DOWN সংখ্যা আলাদা করা
            up_coins = [c for c in all_scanned_coins if c['Signal'] == 'UP']
            down_coins = [c for c in all_scanned_coins if c['Signal'] == 'DOWN']
            
            # মেট্রিক্স ড্যাশবোর্ড আপডেট
            with metrics_placeholder.container():
                col1, col2, col3 = st.columns(3)
                col1.metric("মোট স্ক্যান করা কয়েন", total_coins)
                col2.metric("🟢 200 EMA UP (Bullish)", len(up_coins))
                col3.metric("🔴 200 EMA DOWN (Bearish)", len(down_coins))
            
            if all_scanned_coins:
                df_result = pd.DataFrame(all_scanned_coins)
                
                # টেবিল সুন্দর করার জন্য কলাম রি-অ্যারেঞ্জ
                df_result['Action'] = df_result['Symbol'].apply(
                    lambda sym: f'<a href="{generate_binance_url(sym)}" target="_blank" class="binance-btn">🔗 Trade</a>'
                )
                
                # কলামের সিকোয়েন্স সাজানো ও অপ্রয়োজনীয় কলাম ড্রপ করা
                df_display = df_result[['Symbol', 'Price', '200 EMA', 'Distance (%)', 'Status', 'Action']]
                
                table_html = df_display.to_html(escape=False, index=False, classes='table table-dark table-striped')
                with table_placeholder.container():
                    st.markdown(f"### 📊 লাইভ ডুয়াল মার্কেট সিগন্যাল (Last Update: {datetime.now().strftime('%H:%M:%S')})")
                    st.markdown(table_html, unsafe_allow_html=True)
                
                # --- টেলিগ্রাম চ্যাঙ্ক নোটিফিকেশন জেনারেশন ---
                header = f"🚨 <b>Binance 200 EMA Dual Scanner Report</b> 🚨\n📅 সময়: {current_time}\n📊 মোট স্ক্যান: {total_coins}\n🟢 UP: {len(up_coins)} | 🔴 DOWN: {len(down_coins)}\n\n"
                header += "<b>📌 সিগন্যাল তালিকা:</b>\n"
                header += "--------------------------------------\n"
                
                current_chunk = header
                for coin in all_scanned_coins:
                    trade_url = generate_binance_url(coin['Symbol'])
                    coin_name = coin['Symbol'].split(':')[0]
                    emoji = "🟢 [UP]" if coin['Signal'] == "UP" else "🔴 [DOWN]"
                    
                    coin_text = f"🔹 <b>{coin_name}</b> -> {emoji}\n   • মূল্য: {coin['Price']}\n   • ২০০ EMA: {coin['200 EMA']}\n   • ব্যবধান: {coin['Distance (%)']}%\n   • <a href='{trade_url}'>🔗 Trade Here</a>\n\n"
                    
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
                    st.warning("কোনো ডাটা পাওয়া যায়নি।")
            
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
