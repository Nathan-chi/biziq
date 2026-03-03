"""
BizIQ - Stage 3: Real Market Data Service
Connects to multiple free APIs to get live commodity & forex prices
"""

import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import sqlite3
import json

# ─────────────────────────────────────────────────────────
# API KEYS — Sign up free at these sites and paste your keys:
# ─────────────────────────────────────────────────────────
ALPHA_VANTAGE_KEY = "19A4HKRPGNZ7PFMN"   # Free at: alphavantage.co
OPEN_EXCHANGE_KEY = "d103f19eb3fa4cb188f25cd60c531ad0"   # Free at: openexchangerates.org

# ─────────────────────────────────────────────────────────
# DATABASE — Cache prices so we don't hit API limits
# ─────────────────────────────────────────────────────────

def init_market_db():
    conn = sqlite3.connect("biziq.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            change_pct REAL DEFAULT 0,
            source TEXT,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_cached_price(symbol: str, max_age_minutes: int = 60):
    """Return cached price if it's fresh enough"""
    conn = sqlite3.connect("biziq.db")
    conn.row_factory = sqlite3.Row
    cutoff = (datetime.now() - timedelta(minutes=max_age_minutes)).isoformat()
    row = conn.execute("""
        SELECT * FROM market_cache
        WHERE symbol = ? AND fetched_at > ?
        ORDER BY fetched_at DESC LIMIT 1
    """, (symbol, cutoff)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_to_cache(symbol: str, name: str, price: float, currency: str, change_pct: float, source: str):
    """Save price to cache and history"""
    conn = sqlite3.connect("biziq.db")
    # Update cache
    conn.execute("DELETE FROM market_cache WHERE symbol = ?", (symbol,))
    conn.execute("""
        INSERT INTO market_cache (symbol, name, price, currency, change_pct, source)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (symbol, name, price, currency, change_pct, source))
    # Save to history
    conn.execute("""
        INSERT INTO market_history (symbol, price, date)
        VALUES (?, ?, ?)
    """, (symbol, price, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()


def get_price_history(symbol: str, days: int = 30):
    """Get historical prices for a symbol"""
    conn = sqlite3.connect("biziq.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT date, AVG(price) as price FROM market_history
        WHERE symbol = ?
        GROUP BY date
        ORDER BY date DESC
        LIMIT ?
    """, (symbol, days)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────
# API FETCHERS
# ─────────────────────────────────────────────────────────

async def fetch_commodity_alpha_vantage(symbol: str, name: str) -> Optional[dict]:
    """
    Fetch commodity prices from Alpha Vantage (free tier: 25 calls/day)
    """
    cached = get_cached_price(symbol)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
            r = await client.get(url)
            data = r.json()

        quote = data.get("Global Quote", {})
        if not quote:
            return None

        price = float(quote.get("05. price", 0))
        change_pct = float(quote.get("10. change percent", "0%").replace("%", ""))

        save_to_cache(symbol, name, price, "USD", change_pct, "alpha_vantage")
        return {"symbol": symbol, "name": name, "price": price, "currency": "USD", "change_pct": change_pct}

    except Exception as e:
        print(f"Alpha Vantage error for {symbol}: {e}")
        return None


async def fetch_forex_usd_ngn() -> Optional[float]:
    """
    Fetch USD to NGN exchange rate from Open Exchange Rates
    """
    cached = get_cached_price("USD_NGN", max_age_minutes=30)
    if cached:
        return cached["price"]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"https://openexchangerates.org/api/latest.json?app_id={OPEN_EXCHANGE_KEY}&symbols=NGN"
            r = await client.get(url)
            data = r.json()

        ngn_rate = data["rates"]["NGN"]
        save_to_cache("USD_NGN", "USD/NGN Exchange Rate", ngn_rate, "NGN", 0, "open_exchange_rates")
        return ngn_rate

    except Exception as e:
        print(f"Forex error: {e}")
        return 1580.0  # Fallback rate


async def fetch_world_bank_commodity(indicator: str, name: str) -> Optional[dict]:
    """
    Fetch commodity prices from World Bank
    """
    cached = get_cached_price(f"WB_{indicator}")
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            url = f"https://api.worldbank.org/v2/en/indicator/{indicator}?format=json&mrv=2&per_page=2"
            r = await client.get(url)
            data = r.json()

        if not data or len(data) < 2 or not data[1]:
            return None

        entries = [e for e in data[1] if e.get("value") is not None]
        if not entries:
            return None

        latest = entries[0]
        previous = entries[1] if len(entries) > 1 else entries[0]

        price = float(latest["value"])
        prev_price = float(previous["value"])
        change_pct = ((price - prev_price) / prev_price * 100) if prev_price else 0

        symbol = f"WB_{indicator}"
        save_to_cache(symbol, name, price, "USD", change_pct, "world_bank")
        return {"symbol": symbol, "name": name, "price": price, "currency": "USD", "change_pct": round(change_pct, 2)}

    except Exception as e:
        print(f"World Bank error for {indicator}: {e}")
        return None


# ─────────────────────────────────────────────────────────
# MAIN MARKET DATA FUNCTION
# ─────────────────────────────────────────────────────────

COMMODITY_MAP = [
    ("alpha",      "WHEAT",             "Wheat (Global)",         "per bushel",  "Flour (50kg)"),
    ("alpha",      "SUGAR",             "Sugar (Global)",         "per lb",      "Sugar (50kg)"),
    ("alpha",      "CORN",              "Corn (Global)",          "per bushel",  "Corn/Maize (50kg)"),
    ("alpha",      "BRENT",             "Brent Crude (Fuel)",     "per barrel",  "Diesel/Petrol Proxy"),
    ("worldbank",  "CMO/PALM_OIL_USD",  "Palm Oil (World Bank)",  "per MT",      "Palm Oil (25L)"),
    ("worldbank",  "CMO/RICE_05_USD",   "Rice (World Bank)",      "per MT",      "Rice (50kg)"),
    ("worldbank",  "CMO/COCOA_USD",     "Cocoa (World Bank)",     "per kg",      "Cocoa Powder/Beans"),
    ("worldbank",  "CMO/SO_USD",        "Soybeans (World Bank)",  "per MT",      "Soybeans (100kg)"),
    ("worldbank",  "CMO/UREA_USD",      "Fertilizer (Urea)",      "per MT",      "Fertilizer (50kg)"),
    ("worldbank",  "CMO/COTTON_A_USD",  "Cotton (World Bank)",    "per kg",      "Cotton/Fabric Bale"),
]

def usd_to_ngn(usd_price: float, rate: float, local_unit_multiplier: float = 1.0) -> float:
    return round(usd_price * rate * local_unit_multiplier)

def generate_advice(name: str, change_pct: float) -> str:
    if change_pct > 10:
        return f"Price surging +{change_pct:.1f}% — reduce orders or find alternatives"
    elif change_pct > 5:
        return f"Rising +{change_pct:.1f}% — consider stocking up now"
    elif change_pct > 0:
        return f"Slightly up {change_pct:.1f}% — monitor closely"
    elif change_pct > -5:
        return f"Slight dip {change_pct:.1f}% — good time to restock normally"
    else:
        return f"Price down {change_pct:.1f}% — excellent time to bulk buy!"


def get_supplier_info(item: str, location: str = "Nigeria") -> str:
    """Provides local market suggestions based on item and business location."""
    # Common Nigerian markets for commodities
    markets = {
        "Flour (50kg)": {
            "Abuja": "Wuse Market (Wholesale Wing) or Garki Model Market",
            "Lagos": "Alaba Market or Iddo Terminal",
            "Kano": "Singa Market",
            "default": "Main city wholesale markets"
        },
        "Sugar (50kg)": {
            "Abuja": "Deidei International Market",
            "Lagos": "Mile 12 Market or Daleko Market",
            "Kano": "Kofar Wanbai Market",
            "default": "Regional commodity depots"
        },
        "Rice (50kg)": {
            "Abuja": "Utako Market (Grains Section)",
            "Lagos": "Mile 12 Market or Ikorodu Market",
            "Kano": "Dawanau Grains Market (Largest in West Africa)",
            "default": "Local Grains Market"
        },
        "Palm Oil (25L)": {
            "Abuja": "Kuje Market or Nyanya Market",
            "Lagos": "Oyingbo Market or Mushin Market",
            "Kano": "Sabon Gari Market",
            "default": "Regional oil processing hubs"
        },
        "Corn/Maize (50kg)": {
            "Abuja": "Zuba Grains Market",
            "Lagos": "Mile 12 Market",
            "Kano": "Dawanau Market",
            "default": "Grains depot"
        }
    }
    
    item_info = markets.get(item, {"default": "Local wholesalers"})
    
    # Check if city is mentioned in location string
    loc_lower = location.lower()
    if "abuja" in loc_lower: return item_info.get("Abuja", item_info["default"])
    if "lagos" in loc_lower: return item_info.get("Lagos", item_info["default"])
    if "kano" in loc_lower: return item_info.get("Kano", item_info["default"])
    
    # Specific logic for industrial items
    if "Fertilizer" in item: return "Agro-allied supply centers or Government depots"
    if "Diesel" in item: return "NNPC Retail or Independent Mega Stations"
    if "Cotton" in item: return "Textile markets like Oshodi or Kantin Kwari (Kano)"
    
    return item_info.get("default", "Wholesale district")


async def get_all_market_data(location: str = "Nigeria") -> list:
    ngn_rate = await fetch_forex_usd_ngn()
    tasks = []
    for fetch_type, symbol, name, unit, local_name in COMMODITY_MAP:
        if fetch_type == "alpha":
            tasks.append(fetch_commodity_alpha_vantage(symbol, name))
        elif fetch_type == "worldbank":
            tasks.append(fetch_world_bank_commodity(symbol, name))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    market_data = []
    for i, result in enumerate(results):
        f_type, symbol, name, unit, local_name = COMMODITY_MAP[i]

        if isinstance(result, Exception) or result is None:
            # Try to get fallback using the base symbol
            result = get_fallback_price(symbol)

        if result:
            # Multiplier adjustment for local units (rough demo scale to match NGN street prices)
            multi_map = {
                "WHEAT": 8.0,      # Bushel to 50kg flour roughly
                "SUGAR": 120.0,    # Lb to 50kg bag
                "BRENT": 1.2,      # Crude to local fuel proxy
                "CMO/PALM_OIL_USD": 0.04,  # MT to 25L
                "CMO/RICE_05_USD": 0.08,   # MT to 50kg
                "CMO/SO_USD": 0.15,        # MT to 100kg
                "CMO/UREA_USD": 0.06,      # MT to 50kg
                "CMO/COCOA_USD": 1.0,      # Per kg
                "CMO/COTTON_A_USD": 50.0,  # Per kg to bale
            }
            multiplier = multi_map.get(symbol, 1.0)
            ngn_price = usd_to_ngn(result["price"], ngn_rate, multiplier)
            
            change_pct = result.get("change_pct", 0)
            market_data.append({
                "symbol": symbol,
                "item": local_name,
                "global_name": name,
                "price_usd": round(result["price"], 4),
                "price_ngn": ngn_price,
                "price": ngn_price,
                "unit": unit,
                "trend": round(change_pct, 2),
                "up": change_pct > 0,
                "advice": generate_advice(local_name, change_pct),
                "supplier": get_supplier_info(local_name, location),
                "source": result.get("source", "cache"),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })

    return market_data


def get_fallback_price(symbol: str) -> dict:
    fallbacks = {
        "WHEAT":            {"price": 5.42,  "change_pct": 2.1,  "source": "fallback"},
        "SUGAR":            {"price": 0.21,  "change_pct": 14.5, "source": "fallback"},
        "CORN":             {"price": 4.85,  "change_pct": 1.8,  "source": "fallback"},
        "BRENT":            {"price": 82.10, "change_pct": -1.5, "source": "fallback"},
        "CMO/PALM_OIL_USD": {"price": 862,   "change_pct": 1.2,  "source": "fallback"},
        "CMO/RICE_05_USD":  {"price": 421,   "change_pct": 3.8,  "source": "fallback"},
        "CMO/COCOA_USD":    {"price": 4.25,  "change_pct": 5.2,  "source": "fallback"},
        "CMO/SO_USD":       {"price": 980,   "change_pct": -2.1, "source": "fallback"},
        "CMO/UREA_USD":     {"price": 340,   "change_pct": 0.5,  "source": "fallback"},
        "CMO/COTTON_A_USD": {"price": 1.95,  "change_pct": -3.2, "source": "fallback"},
    }
    return fallbacks.get(symbol)
