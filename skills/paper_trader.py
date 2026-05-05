"""
Paper Trader Skill v1.0

Simulated trade execution and portfolio management:
- Execute paper trades (buy/sell stocks, options)
- Track paper portfolio with P&L
- Trade history logging
- Position management (add, reduce, close)
- Performance analytics (win rate, avg gain/loss, profit factor)
"""

import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PAPER_PORTFOLIO_FILE = BASE_DIR / "cache" / "paper_portfolio.json"
TRADE_HISTORY_FILE = BASE_DIR / "cache" / "trade_history.json"
PAPER_LOG_FILE = BASE_DIR / "logs" / "paper_trades.log"


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


def get_paper_portfolio():
    default = {
        "cash": 100000.0,
        "initial_cash": 100000.0,
        "positions": {},
        "total_value": 100000.0,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return _load_json(PAPER_PORTFOLIO_FILE, default)


def save_paper_portfolio(portfolio):
    portfolio["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_json(PAPER_PORTFOLIO_FILE, portfolio)


def get_trade_history():
    return _load_json(TRADE_HISTORY_FILE, {"trades": []})["trades"]


def _record_trade(trade):
    history = _load_json(TRADE_HISTORY_FILE, {"trades": []})
    trade["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history["trades"].append(trade)
    _save_json(TRADE_HISTORY_FILE, history)
    PAPER_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PAPER_LOG_FILE, "a") as f:
        f.write("[{}] {} {} x{} @ ${:.2f} | P&L: ${:.2f}\n".format(
            trade["timestamp"], trade["action"], trade["ticker"],
            trade.get("quantity", ""), trade.get("price", 0),
            trade.get("realized_pnl", 0)))


def execute_paper_trade(ticker, action, quantity, price, trade_type="stock", **kwargs):
    portfolio = get_paper_portfolio()
    total_cost = quantity * price
    if trade_type in ("call", "put"):
        total_cost *= 100

    result = {
        "ticker": ticker, "action": action, "quantity": quantity,
        "price": price, "total_cost": total_cost, "trade_type": trade_type,
        "status": "PENDING", "realized_pnl": 0.0,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if action == "BUY":
        if total_cost > portfolio["cash"]:
            result["status"] = "REJECTED"
            result["reason"] = "Insufficient cash"
            _record_trade(result)
            return result
        portfolio["cash"] -= total_cost
        if trade_type in ("call", "put"):
            expiry = kwargs.get("expiry", "unknown")
            strike = kwargs.get("strike", 0)
            pos_key = "{}{}{}{}".format(ticker, expiry, "C" if trade_type == "call" else "P", strike)
        else:
            pos_key = ticker
        if pos_key in portfolio["positions"]:
            pos = portfolio["positions"][pos_key]
            old_qty = pos.get("shares", pos.get("contracts", 0))
            new_qty = old_qty + quantity
            pos["avg_cost"] = ((pos["avg_cost"] * old_qty) + (price * quantity)) / new_qty
            if trade_type in ("call", "put"):
                pos["contracts"] = new_qty
            else:
                pos["shares"] = new_qty
        else:
            pos_data = {"type": trade_type, "avg_cost": price,
                        "opened": datetime.now().strftime("%Y-%m-%d")}
            if trade_type in ("call", "put"):
                pos_data["contracts"] = quantity
                pos_data["underlying"] = kwargs.get("underlying", ticker)
                pos_data["strike"] = kwargs.get("strike", 0)
                pos_data["expiry"] = kwargs.get("expiry", "unknown")
            else:
                pos_data["shares"] = quantity
            portfolio["positions"][pos_key] = pos_data
        result["status"] = "FILLED"
        result["cash_remaining"] = portfolio["cash"]

    elif action == "SELL":
        pos_key = ticker
        if trade_type in ("call", "put"):
            expiry = kwargs.get("expiry", "unknown")
            strike = kwargs.get("strike", 0)
            pos_key = "{}{}{}{}".format(ticker, expiry, "C" if trade_type == "call" else "P", strike)
        if pos_key not in portfolio["positions"]:
            result["status"] = "REJECTED"
            result["reason"] = "No position found"
            _record_trade(result)
            return result
        pos = portfolio["positions"][pos_key]
        held_qty = pos.get("shares", pos.get("contracts", 0))
        if quantity > held_qty:
            result["status"] = "REJECTED"
            result["reason"] = "Insufficient position"
            _record_trade(result)
            return result
        avg_cost = pos["avg_cost"]
        if trade_type in ("call", "put"):
            realized_pnl = (price - avg_cost) * quantity * 100
        else:
            realized_pnl = (price - avg_cost) * quantity
        result["realized_pnl"] = round(realized_pnl, 2)
        result["avg_cost"] = avg_cost
        portfolio["cash"] += total_cost
        remaining = held_qty - quantity
        if remaining <= 0:
            del portfolio["positions"][pos_key]
        else:
            if trade_type in ("call", "put"):
                pos["contracts"] = remaining
            else:
                pos["shares"] = remaining
        result["status"] = "FILLED"
        result["cash_remaining"] = portfolio["cash"]

    save_paper_portfolio(portfolio)
    _record_trade(result)
    return result


def execute_from_recommendation(rec, current_price):
    ticker = rec.get("ticker", "UNKNOWN")
    action = rec.get("action", "BUY")
    conviction = rec.get("conviction", 5)
    trade_type = rec.get("type", "stock")
    portfolio = get_paper_portfolio()

    total_value = portfolio["cash"]
    for pk, pv in portfolio.get("positions", {}).items():
        q = pv.get("shares", pv.get("contracts", 0))
        total_value += q * pv.get("avg_cost", 0) * (100 if pv.get("type") in ("call", "put") else 1)

    if conviction >= 9:
        pct = 0.10
    elif conviction >= 8:
        pct = 0.06
    elif conviction >= 7:
        pct = 0.03
    else:
        pct = 0.01

    dollar_amount = total_value * pct
    if current_price <= 0:
        return {"status": "SKIPPED", "reason": "Invalid price"}

    if trade_type in ("call", "put"):
        quantity = max(1, int(dollar_amount / (current_price * 100)))
    else:
        quantity = max(1, int(dollar_amount / current_price))

    kwargs = {}
    if trade_type in ("call", "put"):
        kwargs["underlying"] = ticker
        kwargs["strike"] = rec.get("strike", current_price)
        kwargs["expiry"] = rec.get("expiry", "unknown")

    return execute_paper_trade(ticker, action, quantity, current_price, trade_type, **kwargs)


def get_paper_portfolio_summary(current_prices=None):
    portfolio = get_paper_portfolio()
    positions_detail = []
    total_position_value = 0.0
    total_unrealized_pnl = 0.0

    for pos_key, pos in portfolio.get("positions", {}).items():
        qty = pos.get("shares", pos.get("contracts", 0))
        avg_cost = pos.get("avg_cost", 0)
        trade_type = pos.get("type", "stock")
        underlying = pos.get("underlying", pos_key)
        current = current_prices.get(underlying, avg_cost) if current_prices else avg_cost

        if trade_type in ("call", "put"):
            market_value = qty * current * 100
            cost_basis = qty * avg_cost * 100
        else:
            market_value = qty * current
            cost_basis = qty * avg_cost

        unrealized = market_value - cost_basis
        total_position_value += market_value
        total_unrealized_pnl += unrealized
        positions_detail.append({
            "symbol": pos_key, "underlying": underlying, "type": trade_type,
            "quantity": qty, "avg_cost": avg_cost, "current_price": current,
            "market_value": round(market_value, 2), "cost_basis": round(cost_basis, 2),
            "unrealized_pnl": round(unrealized, 2),
            "unrealized_pnl_pct": round((unrealized / cost_basis * 100) if cost_basis > 0 else 0, 1),
            "opened": pos.get("opened", "unknown")
        })

    total_value = portfolio["cash"] + total_position_value
    initial = portfolio.get("initial_cash", 100000.0)
    total_return_pct = ((total_value - initial) / initial * 100) if initial > 0 else 0

    return {
        "cash": round(portfolio["cash"], 2),
        "positions_value": round(total_position_value, 2),
        "total_value": round(total_value, 2),
        "initial_value": initial,
        "total_return_pct": round(total_return_pct, 2),
        "unrealized_pnl": round(total_unrealized_pnl, 2),
        "num_positions": len(positions_detail),
        "positions": positions_detail,
        "last_updated": portfolio.get("last_updated", "unknown")
    }


def get_trade_performance():
    trades = get_trade_history()
    if not trades:
        return {"total_trades": 0, "win_rate": "N/A", "avg_pnl": "N/A",
                "total_pnl": 0.0, "best_trade": "N/A", "worst_trade": "N/A"}
    realized = [t for t in trades if t.get("realized_pnl", 0) != 0]
    if not realized:
        return {"total_trades": len(trades), "closed_trades": 0, "win_rate": "N/A",
                "avg_pnl": "N/A", "total_pnl": 0.0}
    pnls = [t["realized_pnl"] for t in realized]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total_pnl = sum(pnls)
    avg_pnl = total_pnl / len(pnls)
    win_rate = len(wins) / len(pnls) * 100 if pnls else 0
    return {
        "total_trades": len(trades), "closed_trades": len(realized),
        "win_rate": "{:.1f}%".format(win_rate),
        "avg_pnl": "${:,.2f}".format(avg_pnl),
        "total_pnl": round(total_pnl, 2),
        "best_trade": "${:,.2f}".format(max(pnls)),
        "worst_trade": "${:,.2f}".format(min(pnls)),
        "num_wins": len(wins), "num_losses": len(losses),
        "avg_win": "${:,.2f}".format(sum(wins) / len(wins)) if wins else "$0",
        "avg_loss": "${:,.2f}".format(sum(losses) / len(losses)) if losses else "$0",
        "profit_factor": round(abs(sum(wins) / sum(losses)), 2) if losses and sum(losses) != 0 else float('inf')
    }


def reset_paper_portfolio(initial_cash=100000.0):
    portfolio = {
        "cash": initial_cash, "initial_cash": initial_cash,
        "positions": {}, "total_value": initial_cash,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_paper_portfolio(portfolio)
    _save_json(TRADE_HISTORY_FILE, {"trades": []})
    return {"status": "RESET", "initial_cash": initial_cash}


def format_portfolio_report(current_prices=None):
    summary = get_paper_portfolio_summary(current_prices)
    perf = get_trade_performance()
    lines = []
    lines.append("## Paper Trading Portfolio\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append("| Cash | ${:,.2f} |".format(summary["cash"]))
    lines.append("| Positions Value | ${:,.2f} |".format(summary["positions_value"]))
    lines.append("| **Total Value** | **${:,.2f}** |".format(summary["total_value"]))
    lines.append("| Total Return | {:+.2f}% |".format(summary["total_return_pct"]))
    lines.append("| Unrealized P&L | ${:+,.2f} |".format(summary["unrealized_pnl"]))
    lines.append("| Open Positions | {} |".format(summary["num_positions"]))
    if summary["positions"]:
        lines.append("\n### Open Positions\n")
        lines.append("| Symbol | Type | Qty | Avg Cost | Current | P&L |")
        lines.append("|--------|------|-----|----------|---------|------|")
        for p in summary["positions"]:
            lines.append("| {} | {} | {} | ${:.2f} | ${:.2f} | {:+.1f}% |".format(
                p["symbol"], p["type"], p["quantity"], p["avg_cost"],
                p["current_price"], p["unrealized_pnl_pct"]))
    lines.append("\n### Trade Performance\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append("| Total Trades | {} |".format(perf["total_trades"]))
    lines.append("| Win Rate | {} |".format(perf.get("win_rate", "N/A")))
    lines.append("| Avg P&L | {} |".format(perf.get("avg_pnl", "N/A")))
    lines.append("| Total Realized P&L | ${:+,.2f} |".format(perf["total_pnl"]))
    if perf.get("best_trade"):
        lines.append("| Best Trade | {} |".format(perf["best_trade"]))
    if perf.get("worst_trade"):
        lines.append("| Worst Trade | {} |".format(perf["worst_trade"]))
    if perf.get("profit_factor"):
        lines.append("| Profit Factor | {} |".format(perf["profit_factor"]))
    return "\n".join(lines)


__all__ = [
    "get_paper_portfolio", "save_paper_portfolio", "execute_paper_trade",
    "execute_from_recommendation", "get_paper_portfolio_summary",
    "get_trade_performance", "reset_paper_portfolio", "format_portfolio_report",
    "get_trade_history",
]