"""
Enhanced Trading Skill v1.0

Advanced trading analysis and decision support:
- Kelly Criterion position sizing
- Trade thesis generation and validation
- Options imbalance detection (put/call ratios, IV skew)
- Position re-evaluation and profit-taking logic
- Auto-trade entry/exit signals (paper trading)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


def calculate_kelly_criterion(win_prob: float, avg_win: float, avg_loss: float) -> float:
    """
    Calculate optimal position size using Kelly Criterion.
    
    Args:
        win_prob: Probability of winning (0.0 to 1.0)
        avg_win: Average win amount (as % of portfolio, e.g. 0.20 = 20%)
        avg_loss: Average loss amount (as % of portfolio, e.g. 0.10 = 10%)
    
    Returns:
        Fraction of portfolio to allocate (0.0 to 1.0)
        Uses half-Kelly for safety: returns kelly / 2
    """
    if avg_loss <= 0 or win_prob <= 0 or win_prob >= 1:
        return 0.0
    
    # Kelly formula: f* = (p * b - q) / b where b = avg_win/avg_loss, q = 1-p
    b = avg_win / avg_loss  # odds ratio
    q = 1.0 - win_prob
    kelly = (win_prob * b - q) / b if b > 0 else 0.0
    
    # Clamp and apply half-Kelly for safety
    kelly = max(0.0, min(kelly, 0.25))  # Never exceed 25% of portfolio
    return kelly / 2.0  # Half-Kelly


def calculate_position_size(portfolio_value: float, conviction: int,
                            risk_per_trade: float = 0.02) -> dict:
    """
    Calculate position size based on conviction and risk parameters.
    
    Args:
        portfolio_value: Total portfolio value in USD
        conviction: Conviction score 1-10
        risk_per_trade: Max % of portfolio to risk on one trade (default 2%)
    
    Returns:
        dict with position sizing recommendations
    """
    if portfolio_value <= 0:
        return {"error": "Invalid portfolio value"}
    
    conviction_factor = conviction / 10.0  # 0.1 to 1.0
    
    # Base allocation: Kelly-inspired but simplified
    base_allocation = risk_per_trade * conviction_factor * 3  # Max ~6% of portfolio
    
    # Cap based on conviction
    if conviction >= 9:
        max_allocation = min(base_allocation, 0.10)  # Max 10% for highest conviction
    elif conviction >= 7:
        max_allocation = min(base_allocation, 0.06)  # Max 6%
    elif conviction >= 5:
        max_allocation = min(base_allocation, 0.03)  # Max 3%
    else:
        max_allocation = 0.01  # Max 1% for low conviction
    
    dollar_amount = portfolio_value * max_allocation
    
    return {
        "portfolio_pct": round(max_allocation * 100, 1),
        "dollar_amount": round(dollar_amount, 2),
        "conviction_weighted": round(conviction_factor, 2),
        "risk_per_trade_pct": round(risk_per_trade * 100, 1),
        "recommendation": f"Allocate ${dollar_amount:,.0f} ({max_allocation*100:.1f}% of portfolio)"
    }


def detect_options_imbalances(ticker: str) -> dict:
    """
    Detect options market imbalances for a ticker.
    Analyzes put/call ratios, IV skew, and unusual activity.
    
    Args:
        ticker: Stock symbol (e.g., "AAPL")
    
    Returns:
        dict with imbalance analysis
    """
    try:
        t = yf.Ticker(ticker)
        price = t.fast_info.last_price
        if not price:
            return {"error": "Could not fetch price"}
        
        # Get options expirations
        exps = t.options
        if not exps:
            return {"error": "No options available"}
        
        # Analyze nearest two expirations
        results = {"ticker": ticker, "current_price": price, "expirations": {}}
        
        for exp in exps[:2]:
            try:
                chain = t.option_chain(exp)
                calls = chain.calls
                puts = chain.puts
                
                atm_strike = round(price / 5) * 5  # Round to nearest 5
                nearby_calls = calls[abs(calls['strike'] - price) / price < 0.05]
                nearby_puts = puts[abs(puts['strike'] - price) / price < 0.05]
                
                call_volume = nearby_calls['volume'].sum() if not nearby_calls.empty else 0
                put_volume = nearby_puts['volume'].sum() if not nearby_puts.empty else 0
                open_interest_ratio = (
                    nearby_puts['openInterest'].sum() / nearby_calls['openInterest'].sum()
                    if not nearby_calls.empty and nearby_calls['openInterest'].sum() > 0
                    else None
                )
                
                # Calculate IV skew (put IV vs call IV)
                avg_call_iv = nearby_calls['impliedVolatility'].mean() if not nearby_calls.empty else None
                avg_put_iv = nearby_puts['impliedVolatility'].mean() if not nearby_puts.empty else None
                
                put_call_volume_ratio = (
                    (put_volume / call_volume) if call_volume > 0 else None
                )
                
                days_out = (datetime.strptime(exp, '%Y-%m-%d') - datetime.now()).days
                
                exp_data = {
                    "days_to_expiry": days_out,
                    "put_call_volume_ratio": round(put_call_volume_ratio, 2) if put_call_volume_ratio else None,
                    "put_call_oi_ratio": round(open_interest_ratio, 2) if open_interest_ratio else None,
                    "avg_call_iv": round(avg_call_iv, 4) if avg_call_iv else None,
                    "avg_put_iv": round(avg_put_iv, 4) if avg_put_iv else None,
                }
                
                # Add signal interpretation
                if put_call_volume_ratio and put_call_volume_ratio > 1.5:
                    exp_data["signal"] = "BEARISH - Heavy put volume"
                elif put_call_volume_ratio and put_call_volume_ratio < 0.5:
                    exp_data["signal"] = "BULLISH - Heavy call volume"
                else:
                    exp_data["signal"] = "NEUTRAL"
                
                results["expirations"][exp] = exp_data
                
            except Exception:
                continue
        
        return results
        
    except Exception as e:
        return {"error": str(e)}


def generate_trade_thesis_prompt(ticker: str, price: float, strategy_type: str = "stock") -> str:
    """
    Generate a structured trade thesis prompt for the LLM.
    
    Args:
        ticker: Stock symbol
        price: Current price
        strategy_type: "stock", "options", "crypto", "etf"
    
    Returns:
        Formatted prompt string for LLM analysis
    """
    prompt = f"""Analyze {ticker} (${price:.2f}) for a potential {strategy_type} trade.

**Trade Thesis Framework Required:**

1. **Catalyst Analysis**: What specific events/dates could move this stock?
   - Earnings date (if known)
   - Product launches, regulatory decisions, partnerships
   - Macro/sector tailwinds

2. **Technical Setup**:
   - Current price relative to 50/200 DMA
   - Support/resistance levels
   - Volume analysis (above/below average)

3. **Fundamental Edge**:
   - Why is the market mispricing this?
   - What's the specific thesis?

4. **Risk Assessment**:
   - Biggest risk factor (specific, not generic)
   - What would invalidate the thesis?
   - Downside scenario - how much and why?

5. **Position Sizing**:
   - Recommended position size based on conviction
   - Kelly-optimal allocation

**Output Format:**
Thesis: [1 sentence]
Catalyst: [specific event + date if known]
Entry: ${price:.2f} (current) or limit at $X
Target: $Y (upside: Z%)
Stop: $A (downside: B%)
R/R: [ratio - must be >= 3:1]
Conviction: X/10"""
    return prompt


def generate_options_strategy_prompt(ticker: str, price: float, 
                                      sentiment: str = "bullish") -> str:
    """
    Generate a prompt for options strategy analysis.
    
    Args:
        ticker: Stock symbol
        price: Current price
        sentiment: "bullish", "bearish", "neutral", "volatile"
    
    Returns:
        Formatted prompt for options strategy
    """
    strategies = {
        "bullish": ["Long Call", "Bull Call Spread", "LEAPS Call", "Cash-Secured Put"],
        "bearish": ["Long Put", "Bear Put Spread", "Bear Call Spread"],
        "neutral": ["Covered Call", "Iron Condor", "Credit Spread"],
        "volatile": ["Long Straddle", "Long Strangle", "Calendar Spread"]
    }
    
    rec_strategies = ", ".join(strategies.get(sentiment, strategies["neutral"]))
    
    prompt = f"""Options Strategy for {ticker} (${price:.2f}) - {sentiment.upper()} outlook.

**Recommended Strategies:** {rec_strategies}

**Analysis Required:**
1. IV Rank/Percentile (are options cheap or expensive?)
2. Best strategy for current IV environment
3. Specific strike and expiry selection
4. Max risk/reward calculation
5. Exit plan (close before expiry, always)

**Convince me this is an EDGE trade** - not just a directional bet.
What specific pricing imbalance exists that makes this trade attractive?"""
    return prompt


def re_evaluate_positions(positions: list, current_prices: dict) -> list:
    """
    Re-evaluate open positions and suggest profit-taking or stop-loss.
    
    Args:
        positions: List of dicts with ticker, entry_price, target, stop
        current_prices: Dict of ticker -> current_price
    
    Returns:
        List of re-evaluation results for each position
    """
    results = []
    
    for pos in positions:
        ticker = pos.get("ticker", "")
        entry = pos.get("entry_price", 0)
        target = pos.get("target_price", 0)
        stop = pos.get("stop_loss", 0)
        current = current_prices.get(ticker, 0)
        
        if entry <= 0 or current <= 0:
            results.append({"ticker": ticker, "action": "HOLD", "reason": "Insufficient data"})
            continue
        
        gain_pct = ((current - entry) / entry) * 100
        
        # Determine action
        action = "HOLD"
        reason = f"Current: ${current:.2f} ({gain_pct:+.1f}% from entry)"
        
        if stop > 0 and current <= stop:
            action = "EXIT - STOP LOSS HIT"
            reason += f" | Stop at ${stop:.2f} triggered"
        elif target > 0 and current >= target * 0.95:
            action = "TAKE PROFIT"
            reason += f" | Within 5% of target ${target:.2f}"
        elif gain_pct > 50:
            action = "TAKE PARTIAL PROFITS"
            reason += f" | Up 50%+ - consider selling 1/3 to 1/2"
        elif gain_pct < -20:
            action = "RE-EVALUATE THESIS"
            reason += f" | Down 20%+ - is thesis still intact?"
        
        results.append({
            "ticker": ticker,
            "entry": entry,
            "current": current,
            "gain_pct": round(gain_pct, 1),
            "action": action,
            "reason": reason
        })
    
    return results


def generate_revaluation_report(positions: list, current_prices: dict) -> str:
    """
    Generate a human-readable revaluation report for active positions.
    
    Args:
        positions: List of position dicts
        current_prices: Dict of current prices
    
    Returns:
        Markdown-formatted report
    """
    results = re_evaluate_positions(positions, current_prices)
    
    if not results:
        return "## 📊 Position Re-evaluation\n\nNo active positions to evaluate.\n"
    
    report = "## 📊 Position Re-evaluation\n\n"
    report += "| Ticker | Entry | Current | Gain/Loss | Action | Reason |\n"
    report += "|--------|-------|---------|-----------|--------|--------|\n"
    
    for r in results:
        gain_str = f"{r['gain_pct']:+.1f}%"
        report += f"| {r['ticker']} | ${r['entry']:.2f} | ${r['current']:.2f} | {gain_str} | **{r['action']}** | {r['reason']} |\n"
    
    report += "\n### Summary\n"
    
    take_profit = [r for r in results if 'PROFIT' in r['action']]
    stop_loss = [r for r in results if 'STOP' in r['action']]
    re_eval = [r for r in results if 'RE-EVALUATE' in r['action']]
    hold = [r for r in results if r['action'] == 'HOLD']
    
    if take_profit:
        report += f"- **Take Profit**: {', '.join(r['ticker'] for r in take_profit)}\n"
    if stop_loss:
        report += f"- **Stop Loss Hit**: {', '.join(r['ticker'] for r in stop_loss)}\n"
    if re_eval:
        report += f"- **Re-evaluate**: {', '.join(r['ticker'] for r in re_eval)}\n"
    if hold:
        report += f"- **Hold**: {', '.join(r['ticker'] for r in hold)}\n"
    
    return report


def should_auto_trade(conviction: int, win_prob: float, 
                       risk_reward: float, portfolio_value: float,
                       available_cash: float) -> dict:
    """
    Determine if a trade should be auto-executed (paper trading).
    
    Args:
        conviction: 1-10 conviction score
        win_prob: Estimated win probability (0-1)
        risk_reward: Risk/reward ratio
        portfolio_value: Current portfolio value
        available_cash: Available cash for trading
    
    Returns:
        dict with trade decision and reasoning
    """
    reasons = []
    decision = "NO"
    
    # Conviction check
    if conviction < 8:
        reasons.append(f"Conviction ({conviction}/10) below threshold (8)")
    
    # Win probability check
    if win_prob < 0.60:
        reasons.append(f"Win probability ({win_prob:.0%}) below threshold (60%)")
    
    # Risk/reward check
    if risk_reward < 3.0:
        reasons.append(f"R/R ratio ({risk_reward:.1f}) below threshold (3.0)")
    
    # Cash availability
    position_cost = portfolio_value * 0.05  # Max 5% per trade
    if available_cash < position_cost:
        reasons.append(f"Insufficient cash (${available_cash:,.0f} < ${position_cost:,.0f})")
    
    # All conditions met
    if conviction >= 8 and win_prob >= 0.60 and risk_reward >= 3.0 and available_cash >= position_cost:
        decision = "YES"
        reasons.append("All criteria met for auto-trade")
    
    return {
        "decision": decision,
        "conviction": conviction,
        "win_probability": win_prob,
        "risk_reward_ratio": risk_reward,
        "position_size": round(position_cost, 2),
        "available_cash": round(available_cash, 2),
        "reasons": reasons,
        "confidence": "HIGH" if decision == "YES" else "LOW"
    }


def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index (RSI). RSI < 30 = oversold, RSI > 70 = overbought."""
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD with signal line and histogram."""
    if len(prices) < slow + signal:
        return {"macd_line": 0, "signal_line": 0, "histogram": 0, "signal": "NEUTRAL", "interpretation": "Insufficient data"}

    def ema(data, period):
        mult = 2.0 / (period + 1)
        val = sum(data[:period]) / period
        for p in data[period:]:
            val = (p - val) * mult + val
        return val

    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)
    macd_line = fast_ema - slow_ema
    macd_history = []
    for i in range(slow, len(prices)):
        macd_history.append(ema(prices[:i + 1], fast) - ema(prices[:i + 1], slow))
    signal_line = ema(macd_history, signal) if len(macd_history) >= signal else macd_line
    histogram = macd_line - signal_line
    if macd_line > signal_line and histogram > 0:
        sig = "BULLISH"
        interp = "MACD above signal - positive momentum"
    elif macd_line < signal_line and histogram < 0:
        sig = "BEARISH"
        interp = "MACD below signal - negative momentum"
    else:
        sig = "NEUTRAL"
        interp = "MACD near signal - mixed momentum"
    return {"macd_line": round(macd_line, 4), "signal_line": round(signal_line, 4),
            "histogram": round(histogram, 4), "signal": sig, "interpretation": interp}


def calculate_bollinger_bands(prices, period=20, std_dev=2.0):
    """Calculate Bollinger Bands (upper, middle/SMA, lower)."""
    if len(prices) < period:
        return {"upper": 0, "middle": 0, "lower": 0, "bandwidth": 0, "position": "MIDDLE", "signal": "Insufficient data"}
    recent = prices[-period:]
    sma = sum(recent) / period
    var = sum((p - sma) ** 2 for p in recent) / period
    std = var ** 0.5
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    bw = (upper - lower) / sma if sma > 0 else 0
    cur = prices[-1]
    if cur > upper:
        pos, sig = "ABOVE_UPPER", "Above upper band - overbought or strong trend"
    elif cur < lower:
        pos, sig = "BELOW_LOWER", "Below lower band - oversold or strong downtrend"
    elif cur > sma:
        pos, sig = "UPPER_HALF", "Upper half of bands - bullish bias"
    elif cur < sma:
        pos, sig = "LOWER_HALF", "Lower half of bands - bearish bias"
    else:
        pos, sig = "MIDDLE", "At middle band - neutral"
    return {"upper": round(upper, 2), "middle": round(sma, 2), "lower": round(lower, 2),
            "bandwidth": round(bw, 4), "position": pos, "signal": sig}


def get_technical_signals(ticker, period_days=60):
    """Get combined RSI + MACD + Bollinger Bands signals for a ticker via yfinance."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="3mo")
        if hist.empty or len(hist) < 30:
            return {"error": "Insufficient data", "ticker": ticker}
        closes = hist["Close"].tolist()
        current_price = closes[-1]
        rsi = calculate_rsi(closes)
        macd = calculate_macd(closes)
        bb = calculate_bollinger_bands(closes)
        bullish_count = 0
        bearish_count = 0
        signals = []
        if rsi < 30:
            bullish_count += 2
            signals.append("RSI oversold ({:.1f})".format(rsi))
        elif rsi < 40:
            bullish_count += 1
            signals.append("RSI approaching oversold ({:.1f})".format(rsi))
        elif rsi > 70:
            bearish_count += 2
            signals.append("RSI overbought ({:.1f})".format(rsi))
        elif rsi > 60:
            bearish_count += 1
            signals.append("RSI approaching overbought ({:.1f})".format(rsi))
        else:
            signals.append("RSI neutral ({:.1f})".format(rsi))
        if macd["signal"] == "BULLISH":
            bullish_count += 1
            signals.append("MACD bullish crossover")
        elif macd["signal"] == "BEARISH":
            bearish_count += 1
            signals.append("MACD bearish crossover")
        else:
            signals.append("MACD neutral")
        if bb["position"] == "BELOW_LOWER":
            bullish_count += 1
            signals.append("Below lower Bollinger Band")
        elif bb["position"] == "ABOVE_UPPER":
            bearish_count += 1
            signals.append("Above upper Bollinger Band")
        else:
            signals.append("BB: {}".format(bb["position"]))
        net = bullish_count - bearish_count
        if net >= 2:
            overall = "STRONG BUY"
        elif net >= 1:
            overall = "BUY"
        elif net <= -2:
            overall = "STRONG SELL"
        elif net <= -1:
            overall = "SELL"
        else:
            overall = "HOLD"
        return {
            "ticker": ticker, "current_price": round(current_price, 2),
            "rsi": rsi, "macd": macd, "bollinger_bands": bb,
            "signals": signals, "bullish_score": bullish_count,
            "bearish_score": bearish_count, "net_score": net,
            "overall_signal": overall
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


__all__ = [
    'generate_trade_thesis_prompt',
    'calculate_kelly_criterion',
    'calculate_position_size',
    'detect_options_imbalances',
    'generate_options_strategy_prompt',
    're_evaluate_positions',
    'generate_revaluation_report',
    'should_auto_trade',
    'calculate_rsi',
    'calculate_macd',
    'calculate_bollinger_bands',
    'get_technical_signals',
]
