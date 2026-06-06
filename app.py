import streamlit as st
import ccxt.async_support as ccxt  # স্ট্যান্ডার্ড এসিনক্রোনাস সাপোর্ট
import asyncio
import pandas as pd
from datetime import datetime
import httpx  # CoinGecko ও Telegram API কলের জন্য

# Streamlit Page Configuration
st.set_page_config(page_title="Binance 200 EMA Custom Dual Scanner", layout="wide")

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "8957518460:AAE_9HaugsNNYfjOzCpbHi2nJAEKf4GSiKs"
TELEGRAM_CHAT_ID = "6166836299"

# --- USER CUSTOM COINGECKO COIN LIST ---
CUSTOM_COINGECKO_IDS = [
    "bitcoin", "ethereum", "binancecoin", "solana", "ripple", 
    "cardano", "polkadot", "avalanche-2", "chainlink", "litecoin", 
    "dogecoin", "shiba-inu", "matic-network", "cosmos", "bitcoin-cash", 
    "ethereum-classic", "stellar", "near", "tron", "uniswap",
    "sui", "aptos", "toncoin", "injective-protocol", "sei-network", 
    "fantom", "algorand", "elrond-erd-2", "celestia", "mina-protocol", 
    "flow", "internet-computer", "eos", "kava", "astar", 
    "harmony", "hedera-hashgraph", "iota", "neo", "qtum", 
    "vechain", "zilliqa", "waves", "theta-token", "stratisevm",
    "arbitrum", "optimism", "starknet", "metis-token", "manta-network", 
    "skale", "celo", "loopring", "immutable-x", "omg", "oasis",
    "pepe", "dogwifhat", "bonk", "floki", "book-of-meme", 
    "memecoin", "myro", "1000sats", "corgiai", "coq-inu", 
    "turbo", "baby-doge-coin", "constitutiondao", "wen", "ai-doge", 
    "milady-meme-coin", "rats", "notcoin", "popcat", "cat-in-a-dogs-world", 
    "brett", "mog-coin", "first-neiro-on-ethereum", "moodeng", "goatseus-maximus", 
    "peanut-the-squirrel", "act-i-the-ai-prophecy", "comedian", "fartcoin", "pudgy-penguins", 
    "degen-base", "puffer-finned", "aixbt", "cheems", "sundog", 
    "official-trumpet", "chillguy",
    "fetch-ai", "render-token", "the-graph", "bittensor", "akash-network", 
    "singularitynet", "ocean-protocol", "phoenix-global", "arkham", "worldcoin", 
    "nfprompt", "sleepless-ai", "livepeer", "filecoin", "arweave", 
    "jasmycoin", "storj", "bluzelle", "ankr", "io-net", 
    "speculative-token", "nosana", "clore-ai", "golem", "ordinals", 
    "measurable-data-token", "cortex", "everipedia", "gitcoin", "clover-finance",
    "aave", "pendle", "maker", "curve-dao-token", "lido-dao", 
    "jupiter-exchange-solana", "thorchain", "dydx-chain", "ethereum-name-service", "compound-governance-token", 
    "synthetix-network-token", "sushi", "yearn-finance", "pancakeswap-token", "bakerytoken", 
    "raydium", "joe", "jito-governance-token", "orca", "cow-protocol", 
    "1inch", "balancer", "badger-dao", "alpha-finance", "recurrent-value",
    "ethena", "zero1-labs", "drift-protocol", "safe", "decentralized-usd", 
    "pyth-network", "axelar", "ondo-finance", "truefi", "alpaca-finance", 
    "bella-protocol", "bounce-token", "troy", "quickswap", "stafi", 
    "unifi-protocol-dao", "ether-fi", "renzo", "omni-network", "tensor", 
    "saga", "bounce-bit", "district0x", "wazirx", "scroll", 
    "hyperliquid", "magic-eden", "vethor-token", "chronobank", "system-omega",
    "celer-network", "combo-token", "huma-finance", "zora", "cetus-protocol", "kite-network",
    "gala", "axie-infinity", "the-sandbox", "decentraland", "pixel", 
    "beam", "yield-guide-games", "illuvium", "my-neighbor-alice", "enjincoin", 
    "magic", "portal", "xai", "chiliz", "superfarm", 
    "voxel", "mines-of-dalarnia", "alien-worlds", "ghost-token", "bigtime", 
    "token-fi", "vanarchain", "mbox", "revolution-games", "highstreet",
    "wormhole", "stargate-finance", "synapse", "moonbeam", "moonriver", 
    "kusama", "icon", "band-protocol", "tellor", "dia",
    "zcash", "monero", "dash", "horizen", "ontology", 
    "iotex", "ravencoin", "holotoken", "basic-attention-token", "kyber-network-crystal", 
    "0x", "ren", "woo-network", "stepn", "space-id", 
    "open-campus", "hooked-protocol", "cyberconnect", "maverick-protocol", "ark", 
    "polymath", "loom-network", "barnbridge", "voyager-token", "stratisevm", 
    "radicle", "mubarak"
]

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
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Premium Binance 200 EMA Custom Scanner")
st.write("কাস্টম কয়েন লিস্ট দিয়ে ২০০ EMA এর UP (Green) এবং DOWN (Red) ফিউচার পেয়ার অটো-স্ক্যানার।")

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
    clean_symbol = symbol.replace('/', '').replace(':USDT', '')
    return f"https://www.binance.com/en/futures/{clean_symbol}"

# --- COINGECKO MAPPING & SYMBOL GENERATION ---

async def map_coingecko_ids_to_binance(exchange, coin_ids):
    """আইপি ব্লকিং এড়িয়ে কয়েনগেকো লিস্টকে বাইনান্স ফিউচার্স পেয়ারে রূপান্তর করে"""
    binance_symbols = []
    try:
        ids_param = ",".join(coin_ids)
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids_param}&per_page=250&page=1"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=20.0)
            if response.status_code == 200:
                for coin in response.json():
                    ticker_symbol = coin['symbol'].upper()
                    # স্পেশাল নেম রিপ্লেসমেন্ট (যেমন: MATIC/POL কনভার্সন)
                    if ticker_symbol == "MATIC": ticker_symbol = "POL"
                    binance_symbols.append(f"{ticker_symbol}/USDT")
                    
            if len(coin_ids) > 240:
                url2 = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids_param}&per_page=250&page=2"
                response2 = await client.get(url2, timeout=20.0)
                if response2.status_code == 200:
                    for coin in response2.json():
                        ticker_symbol = coin['symbol'].upper()
                        if ticker_symbol == "MATIC": ticker_symbol = "POL"
                        binance_symbols.append(f"{ticker_symbol}/USDT")
                        
        if binance_symbols:
            return list(set(binance_symbols))
    except Exception:
        pass

    # --- ফেইল সেফ ব্যাকআপ লজিক (বাইনান্স ব্লক খেলেও এটি কাজ করবে) ---
    special_cases = {
        "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB", "solana": "SOL", "ripple": "XRP",
        "cardano": "ADA", "polkadot": "DOT", "avalanche-2": "AVAX", "chainlink": "LINK", "litecoin": "LTC",
        "dogecoin": "DOGE", "shiba-inu": "SHIB", "matic-network": "POL", "cosmos": "ATOM", "bitcoin-cash": "BCH",
        "near": "NEAR", "tron": "TRX", "uniswap": "UNI", "fantom": "FTM", "render-token": "RENDER", "fetch-ai": "FET"
    }
    
    fallback_list = []
    for cid in coin_ids:
        if cid in special_cases:
            fallback_list.append(f"{special_cases[cid]}/USDT")
        else:
            fallback_list.append(f"{cid.split('-')[0].upper()}/USDT")
    return list(set(fallback_list))

async def fetch_and_calculate_ema(exchange, symbol):
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
        # ব্লক এড়াতে অল্টারনেটিভ ক্লাউড ফ্রেন্ডলি প্রক্সি ইউআরএল
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'urls': {
                'api': {
                    'public': 'https://api.binance4.com/api/v3',
                    'fapi': 'https://fapi.binance.com',
                }
            },
            'options': {'defaultType': 'swap'}
        })
        
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            live_status_box.markdown(f"### 🔄 আপনার কাস্টম কয়েন লিস্ট স্ক্যান হচ্ছে... (সময়: {current_time})")
            
            symbols_to_scan = await map_coingecko_ids_to_binance(exchange, CUSTOM_COINGECKO_IDS)
            
            if not symbols_to_scan:
                st.warning("কয়েন লিস্ট জেনারেট করা যায়নি। ৩০ সেকেন্ড পর আবার চেষ্টা করা হচ্ছে...")
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
                            🔍 কাস্টম স্ক্যানিং প্রোগ্রেস: {progress_perc}% ({min(i+batch_size, total_coins)}/{total_coins})
                        </p>
                        <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 5px;">বর্তমানে নিচের কয়েনগুলো স্ক্যান করা হচ্ছে:</p>
                        <div class="coin-list-text">{running_coin_names}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                tasks = [fetch_and_calculate_ema(exchange, symbol) for symbol in batch]
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    if res:
                        all_scanned_coins.append(res)
                
                await asyncio.sleep(0.4)
            
            live_status_box.empty()
            
            up_coins = [c for c in all_scanned_coins if c['Signal'] == 'UP']
            down_coins = [c for c in all_scanned_coins if c['Signal'] == 'DOWN']
            
            with metrics_placeholder.container():
                col1, col2, col3 = st.columns(3)
                col1.metric("মোট সফল স্ক্যান", len(all_scanned_coins))
                col2.metric("🟢 200 EMA UP", len(up_coins))
                col3.metric("🔴 200 EMA DOWN", len(down_coins))
            
            if all_scanned_coins:
                df_result = pd.DataFrame(all_scanned_coins)
                df_result['Action'] = df_result['Symbol'].apply(
                    lambda sym: f'<a href="{generate_binance_url(sym)}" target="_blank" class="binance-btn">🔗 Trade</a>'
                )
                
                df_display = df_result[['Symbol', 'Price', '200 EMA', 'Distance (%)', 'Status', 'Action']]
                table_html = df_display.to_html(escape=False, index=False, classes='table table-dark table-striped')
                
                with table_placeholder.container():
                    st.markdown(f"### 📊 মার্কেট সিগন্যাল ড্যাশবোর্ড (Last Update: {datetime.now().strftime('%H:%M:%S')})")
                    st.markdown(table_html, unsafe_allow_html=True)
                
                # --- টেলিগ্রাম অ্যালার্ট ---
                header = f"🚨 <b>Binance 200 EMA Custom Report</b> 🚨\n📅 সময়: {current_time}\n🟢 UP: {len(up_coins)} | 🔴 DOWN: {len(down_coins)}\n\n"
                current_chunk = header
                
                for coin in all_scanned_coins:
                    trade_url = generate_binance_url(coin['Symbol'])
                    emoji = "🟢 [UP]" if coin['Signal'] == "UP" else "🔴 [DOWN]"
                    coin_text = f"🔹 <b>{coin['Symbol']}</b> -> {emoji}\n   • মূল্য: {coin['Price']}\n   • ব্যবধান: {coin['Distance (%)']}%\n   • <a href='{trade_url}'>🔗 Trade Here</a>\n\n"
                    
                    if len(current_chunk) + len(coin_text) > 3000:
                        await send_telegram_message(current_chunk)
                        await asyncio.sleep(0.5)
                        current_chunk = "<b>📈 Custom Report (Continued...)</b>\n\n" + coin_text
                    else:
                        current_chunk += coin_text
                
                if current_chunk != header:
                    await send_telegram_message(current_chunk)
            
            st.info("⏱️ কাস্টম স্ক্যান সম্পন্ন হয়েছে। পরবর্তী স্ক্যান ১৫ মিনিট পর স্বয়ংক্রিয়ভাবে শুরু হবে।")
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
