"""
Alpaca Paper Trading Skill

Manages paper trading account for testing strategies.
Free paper trading at: https://app.alpaca.markets/paper/dashboard/overview

Setup:
1. Create Alpaca account at https://alpaca.markets
2. Get paper trading API keys from dashboard
3. Set environment variables:
   - ALPACA_API_KEY=your_key
   - ALPACA_SECRET_KEY=your_secret
"""

import os
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
TRADES_FILE = BASE_DIR / "docs" / "PAPER_TRADES.md"
POSITIONS_FILE = BASE_DIR / "docs" / "PAPER_POSITIONS.md"

def get_alpaca_client():
    """Get Alpaca trading client."""
    try:
        import alpaca_trade_api as tradeapi
        api_key = os.environ.get("ALPACA_API_KEY", "")
        secret_key = os.environ.get("ALPACA_SECRET_KEY", "")
        
        if not api_key or not secret_key:
            return None
            
        return tradeapi.REST(
            key_id=api_key,
            secret_key=secret_key,
            base_url='https://paper-api.alpaca.markets'  # Paper trading URL
        )
    except ImportError:
        return None
    except Exception:
        return None

def get_account_info() -> dict:
    """Get paper trading account information."""
    api = get_alpaca_client()
    if not api:
        return {"error": "Alpaca not configured"}
    
    try:
        account = api.get_account()
        return {
            "buying_power": float(account.buying_power),
            "portfolio_value": float(account.portfolio_value),
            "cash": float(account.cash),
            "equity": float(account.equity),
            "status": account.status
        }
    except Exception as e:
        return {"error": str(e)}

def get_positions() -> list:
    """Get current paper trading positions."""
    api = get_alpaca_client()
    if not api:
        return []
    
    try:
        positions = api.list_positions()
        return [{
            "symbol": p.symbol,
            "qty": int(p.qty),
            "avg_entry": float(p.avg_entry_price),
            "current_price": float(p.current_price),
            "market_value": float(p.market_value),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_plpc": float(p.unrealized_plpc)
        } for p in positions]
    except Exception:
        return []

def place_paper_order(symbol: str, qty: int, side: str, order_type: str = "market", 
                      limit_price: float = None, stop_price: float = None) -> dict:
    """
    Place a paper trade order.
    
    Args:
        symbol: Stock ticker (e.g., "AAPL")
        qty: Number of shares
        side: "buy" or "sell"
        order_type: "market", "limit", "stop", "stop_limit"
        limit_price: Required for limit orders
        stop_price: Required for stop orders
    
    Returns:
        Order details or error
    """
    api = get_alpaca_client()
    if not api:
        return {"error": "Alpaca not configured. Set ALPACA_API_KEY and ALPACA_SECRET_KEY env vars."}
    
    try:
        order_params = {
            "symbol": symbol.upper(),
            "qty": qty,
            "side": side,
            "type": order_type,
            "time_in_force": "day"
        }
        
        if limit_price and order_type in ["limit", "stop_limit"]:
            order_params["limit_price"] = limit_price
        if stop_price and order_type in ["stop", "stop_limit"]:
            order_params["stop_price"] = stop_price
        
        order = api.submit_order(**order_params)
        
        # Log the trade
        trade_record = {
            "date": datetime.now().isoformat(),
            "symbol": symbol.upper(),
            "side": side,
            "qty": qty,
            "type": order_type,
            "order_id": order.id,
            "status": order.status
        }
        _log_trade(trade_record)
        
        return {
            "order_id": order.id,
            "status": order.status,
            "symbol": symbol.upper(),
            "side": side,
            "qty": qty
        }
    except Exception as e:
        return {"error": str(e)}

def _log_trade(trade: dict):
    """Log trade to file."""
    trades = []
    if TRADES_FILE.exists():
        content = TRADES_FILE.read_text()
        # Parse existing trades (simple markdown table)
    
    # Append to trades file
    with open(TRADES_FILE, "a") as f:
        f.write(f"\n| {trade['date'][:10]} | {trade['symbol']} | {trade['side']} | {trade['qty']} | {trade['type']} | {trade['status']} |")

def get_open_orders() -> list:
    """Get open orders."""
    api = get_alpaca_client()
    if not api:
        return []
    
    try:
        orders = api.list_orders(status="open")
        return [{
            "id": o.id,
            "symbol": o.symbol,
            "side": o.side,
            "qty": int(o.qty),
            "type": o.type,
            "submitted_at": str(o.submitted_at)
        } for o in orders]
    except Exception:
        return []

def cancel_order(order_id: str) -> dict:
    """Cancel an open order."""
    api = get_alpaca_client()
    if not api:
        return {"error": "Alpaca not configured"}
    
    try:
        api.cancel_order(order_id)
        return {"status": "cancelled", "order_id": order_id}
    except Exception as e:
        return {"error": str(e)}

def get_portfolio_history(period: str = "1M") -> dict:
    """Get portfolio performance history."""
    api = get_alpaca_client()
    if not api:
        return {"error": "Alpaca not configured"}
    
    try:
        history = api.get_portfolio_history(period=period)
        return {
            "equity": history.equity,
            "timestamp": history.timestamp,
            "profit_loss": history.profit_loss,
            "profit_loss_pct": history.profit_loss_pct
        }
    except Exception as e:
        return {"error": str(e)}

__all__ = [
    'get_alpaca_client',
    'get_account_info',
    'get_positions',
    'place_paper_order',
    'get_open_orders',
    'cancel_order',
    'get_portfolio_history'
]