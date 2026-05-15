"""
Alpaca Paper Trading Skill v2.0

Manages paper trading account for testing strategies.
Supports both STOCKS and OPTIONS.

Free paper trading at: https://app.alpaca.markets/paper/dashboard/overview

Setup:
1. Create Alpaca account at https://alpaca.markets
2. Get paper trading API keys from dashboard
3. Set environment variables:
   - ALPACA_API_KEY=your_key
   - ALPACA_SECRET_KEY=your_secret
4. Enable options trading in Alpaca dashboard (Paper Trading → Options)
"""

import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta


def _retry(func, max_retries=3, base_delay=2):
    """Retry a function with exponential backoff."""
    last_err = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(base_delay * (attempt + 1))
    raise last_err

BASE_DIR = Path(__file__).parent.parent
TRADES_FILE = BASE_DIR / "docs" / "PAPER_TRADES.md"
POSITIONS_FILE = BASE_DIR / "docs" / "PAPER_POSITIONS.md"
LOCAL_PORTFOLIO_FILE = BASE_DIR / "cache" / "paper_portfolio.json"

# ─────────────────────────────────────────────
# CLIENT
# ─────────────────────────────────────────────

def get_alpaca_client():
    """Get Alpaca trading client."""
    try:
        import alpaca_trade_api as tradeapi
        api_key = os.environ.get("ALPACA_API_KEY", "")
        secret_key = os.environ.get("ALPACA_SECRET_KEY", "")
        if not api_key or not secret_key:
            return None
        return tradeapi.REST(
            key_id=api_key, secret_key=secret_key,
            base_url='https://paper-api.alpaca.markets'
        )
    except ImportError:
        return None
    except Exception:
        return None

def _alpaca_headers():
    """Get headers for direct REST API calls (for options)."""
    return {
        "APCA-API-KEY-ID": os.environ.get("ALPACA_API_KEY", ""),
        "APCA-API-SECRET-KEY": os.environ.get("ALPACA_SECRET_KEY", ""),
        "Content-Type": "application/json"
    }

def _alpaca_base():
    return "https://paper-api.alpaca.markets/v2"

# ─────────────────────────────────────────────
# ACCOUNT & POSITIONS (for learning/feedback)
# ─────────────────────────────────────────────

def get_account_info() -> dict:
    """Get paper trading account information with retry."""
    api = get_alpaca_client()
    if not api:
        return {"error": "Alpaca not configured"}
    try:
        account = _retry(lambda: api.get_account())
        result = {
            "buying_power": float(account.buying_power),
            "portfolio_value": float(account.portfolio_value),
            "cash": float(account.cash),
            "equity": float(account.equity),
            "status": account.status,
        }
        return result
    except Exception as e:
        return {"error": str(e)}

def get_positions() -> list:
    """Get current stock positions from Alpaca with retry."""
    api = get_alpaca_client()
    if not api:
        return []
    try:
        positions = _retry(lambda: api.list_positions())
        return [{
            "symbol": p.symbol, "qty": int(p.qty),
            "side": getattr(p, 'side', 'long'),
            "avg_entry": float(p.avg_entry_price),
            "current_price": float(p.current_price),
            "market_value": float(p.market_value),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_plpc": float(p.unrealized_plpc),
            "type": "stock"
        } for p in positions]
    except Exception:
        return []

def get_all_positions_including_options() -> list:
    """Get ALL positions including options via direct REST API."""
    positions = get_positions()
    try:
        headers = _alpaca_headers()
        base = _alpaca_base()
        r = requests.get(f"{base}/positions", headers=headers, timeout=15)
        if r.status_code == 200:
            for p in r.json():
                if p.get('asset_class') == 'option':
                    qty = int(p.get('qty', 0))
                    cost = float(p.get('cost_basis', 0))
                    positions.append({
                        "symbol": p.get('symbol', ''),
                        "underlying": p.get('underlying_symbol', ''),
                        "qty": qty,
                        "side": p.get('side', 'long'),
                        "avg_entry": cost / max(qty, 1) / 100,
                        "current_price": float(p.get('current_price', 0)),
                        "market_value": float(p.get('market_value', 0)),
                        "unrealized_pl": float(p.get('unrealized_pl', 0)),
                        "unrealized_plpc": float(p.get('unrealized_plpc', 0)),
                        "type": "option"
                    })
    except Exception:
        pass
    return positions

def get_portfolio_history(period: str = "1M") -> dict:
    """Get portfolio performance history."""
    api = get_alpaca_client()
    if not api:
        return {"error": "Alpaca not configured"}
    try:
        history = api.get_portfolio_history(period=period)
        return {
            "equity": history.equity, "timestamp": history.timestamp,
            "profit_loss": history.profit_loss,
            "profit_loss_pct": history.profit_loss_pct
        }
    except Exception as e:
        return {"error": str(e)}

def get_trade_history(limit: int = 50) -> list:
    """Get recent trade fills from Alpaca for agent learning."""
    try:
        headers = _alpaca_headers()
        base = _alpaca_base()
        r = requests.get(
            f"{base}/account/activities?activity_types=FILL&limit={limit}",
            headers=headers, timeout=15
        )
        if r.status_code == 200:
            trades = []
            for a in r.json():
                if a.get('type') == 'fill':
                    sym = a.get('symbol', '')
                    trades.append({
                        "symbol": sym,
                        "side": a.get('side', ''),
                        "qty": int(a.get('qty', 0)),
                        "price": float(a.get('price', 0)),
                        "timestamp": a.get('transaction_time', ''),
                        "type": "option" if len(sym) > 5 else "stock"
                    })
            return trades
    except Exception:
        pass
    return []

# ─────────────────────────────────────────────
# TRADE EXECUTION
# ─────────────────────────────────────────────

def place_stock_order(symbol, qty, side="buy", order_type="market"):
    """Place a stock order on Alpaca paper trading."""
    api = get_alpaca_client()
    if not api:
        return {"error": "Alpaca not configured", "status": "SKIPPED"}
    try:
        order = api.submit_order(
            symbol=symbol.upper(), qty=qty, side=side,
            type=order_type, time_in_force="day"
        )
        result = {"status": order.status, "order_id": order.id,
                  "symbol": symbol.upper(), "side": side, "qty": qty, "type": "stock"}
        _log_trade(result)
        return result
    except Exception as e:
        result = {"status": "REJECTED", "symbol": symbol.upper(), "side": side,
                  "qty": qty, "type": "stock", "error": str(e)}
        _log_trade(result)
        return result

def place_option_order(underlying, option_symbol, qty, side="buy", order_type="market"):
    """Place an options order on Alpaca paper trading via direct REST API."""
    try:
        headers = _alpaca_headers()
        base = _alpaca_base()
        order_data = {
            "symbol": option_symbol.upper(), "qty": str(qty),
            "side": side, "type": order_type, "time_in_force": "day"
        }
        r = requests.post(f"{base}/orders", json=order_data, headers=headers, timeout=15)
        if r.status_code in [200, 201, 202]:
            order = r.json()
            result = {"status": order.get("status", "submitted"), "order_id": order.get("id", ""),
                      "symbol": option_symbol.upper(), "underlying": underlying.upper(),
                      "side": side, "qty": qty, "type": "option"}
            _log_trade(result)
            return result
        else:
            result = {"status": "REJECTED", "symbol": option_symbol.upper(),
                      "underlying": underlying.upper(), "side": side, "qty": qty,
                      "type": "option", "error": f"HTTP {r.status_code}: {r.text[:100]}"}
            _log_trade(result)
            return result
    except Exception as e:
        result = {"status": "REJECTED", "symbol": option_symbol.upper(),
                  "side": side, "qty": qty, "type": "option", "error": str(e)}
        _log_trade(result)
        return result

def _log_trade(trade):
    """Log trade to local file for agent learning."""
    trade["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(TRADES_FILE, "a") as f:
            f.write(f"\n| {trade['timestamp'][:10]} | {trade.get('symbol','')} | "
                    f"{trade.get('side','')} | {trade.get('qty','')} | "
                    f"{trade.get('type','')} | {trade.get('status','')} |")
    except Exception:
        pass
    try:
        portfolio = _load_json(LOCAL_PORTFOLIO_FILE,
                               {"cash": 100000.0, "initial_cash": 100000.0,
                                "positions": {}, "total_value": 100000.0})
        portfolio["last_updated"] = trade["timestamp"]
        _save_json(LOCAL_PORTFOLIO_FILE, portfolio)
    except Exception:
        pass

def _load_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

# ─────────────────────────────────────────────
# OPTIONS CHAIN
# ─────────────────────────────────────────────

def get_option_chain(underlying, expiry_days_out=35):
    """Get options chain for an underlying from Alpaca."""
    try:
        headers = _alpaca_headers()
        base = _alpaca_base()
        target = (datetime.now() + timedelta(days=expiry_days_out)).strftime("%Y-%m-%d")
        r = requests.get(
            f"{base}/options/contracts?underlying_symbols={underlying.upper()}"
            f"&expiration_date.lte={target}&limit=100",
            headers=headers, timeout=15
        )
        if r.status_code == 200:
            contracts = r.json().get("option_contracts", [])
            return {"underlying": underlying.upper(), "contracts": contracts[:20],
                    "count": len(contracts)}
    except Exception:
        pass
    return {"underlying": underlying.upper(), "contracts": [], "count": 0}

def find_option_symbol(underlying, option_type, strike, expiry_days_out=35):
    """Find the OCC option symbol for a specific option."""
    chain = get_option_chain(underlying, expiry_days_out)
    for c in chain.get("contracts", []):
        if (c.get("type", "").lower() == option_type.lower() and
            abs(float(c.get("strike_price", 0)) - strike) < 0.01):
            return c.get("symbol", "")
    return ""

# ─────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────

def get_open_orders():
    """Get open orders."""
    api = get_alpaca_client()
    if not api:
        return []
    try:
        orders = api.list_orders(status="open")
        return [{"id": o.id, "symbol": o.symbol, "side": o.side,
                 "qty": int(o.qty), "type": o.type, "submitted_at": str(o.submitted_at)}
                for o in orders]
    except Exception:
        return []

def cancel_order(order_id):
    """Cancel an open order."""
    api = get_alpaca_client()
    if not api:
        return {"error": "Alpaca not configured"}
    try:
        api.cancel_order(order_id)
        return {"status": "cancelled", "order_id": order_id}
    except Exception as e:
        return {"error": str(e)}

__all__ = [
    'get_alpaca_client', 'get_account_info', 'get_positions',
    'get_all_positions_including_options', 'get_portfolio_history',
    'get_trade_history', 'place_stock_order', 'place_option_order',
    'get_option_chain', 'find_option_symbol',
    'get_open_orders', 'cancel_order'
]