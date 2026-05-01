"""
Crypto Tracker Skill

Handles all cryptocurrency-related functionality:
- Price tracking (BTC, ETH, XRP, etc.)
- Market cap analysis
- Crypto-specific investment ideas
- Integration with yfinance and CoinGecko API (no key needed)
"""

import requests
import yfinance as yf
from io import StringIO
import sys

def fetch_crypto_prices(cryptos: list = None) -> dict:
    """
    Fetch crypto prices from yfinance or CoinGecko (FREE, no API key).
    
    Args:
        cryptos: List of crypto tickers (e.g., ["BTC-USD", "ETH-USD"])
    
    Returns:
        dict: {ticker: price}
    """
    if cryptos is None:
        cryptos = ["BTC-USD", "ETH-USD", "XRP-USD"]
    
    result = {}
    for crypto in cryptos:
        try:
            # Try yfinance first
            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                t = yf.Ticker(crypto)
                price = t.fast_info.last_price
            except Exception:
                price = None
            finally:
                sys.stderr = old_stderr
            
            # Fallback to CoinGecko if yfinance fails (no API key needed!)
            if price is None:
                symbol = crypto.split('-')[0].lower()
                try:
                    r = requests.get(
                        f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd",
                        timeout=10
                    )
                    data = r.json()
                    price = data.get(symbol, {}).get('usd')
                except Exception:
                    pass
            
            if price:
                result[crypto] = price
        except Exception:
            pass
    
    return result

def get_crypto_market_cap(crypto: str = "bitcoin") -> dict:
    """
    Get market cap and rank from CoinGecko (no API key needed).
    
    Returns:
        dict: {price, market_cap, market_cap_rank, total_volume}
    """
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{crypto}?localization=false&tickers=false&market_data=true",
            timeout=10
        )
        data = r.json()
        market_data = data.get('market_data', {})
        
        return {
            'price': market_data.get('current_price', {}).get('usd'),
            'market_cap': market_data.get('market_cap', {}).get('usd'),
            'rank': data.get('market_cap_rank'),
            'volume': market_data.get('total_volume', {}).get('usd'),
            'change_24h': market_data.get('price_change_percentage_24h')
        }
    except Exception:
        return {}

def analyze_crypto_portfolio(holdings: list) -> str:
    """
    Analyze crypto holdings in portfolio.
    
    Args:
        holdings: List of {ticker, shares, cost_basis}
    
    Returns:
        str: Markdown summary of crypto positions
    """
    if not holdings:
        return ""
    
    crypto_holdings = [h for h in holdings if 'USD' in h.get('ticker', '')]
    
    if not crypto_holdings:
        return ""
    
    summary = "## 🪙 Crypto Holdings Analysis\n\n"
    summary += "| Crypto | Shares | Cost Basis | Current Price | P&L |\n"
    summary += "|--------|--------|-----------|---------------|-----|\n"
    
    for h in crypto_holdings:
        ticker = h['ticker']
        price_data = fetch_crypto_prices([ticker])
        current_price = price_data.get(ticker)
        
        if current_price:
            current_value = h['shares'] * current_price
            pnl = ((current_price - h['purchase_price']) / h['purchase_price'] * 100) if h['purchase_price'] > 0 else 0
            summary += f"| {ticker} | {h['shares']:.4f} | ${h['cost_basis']:,.0f} | ${current_price:.2f} | {pnl:+.1f}% |\n"
    
    return summary

def get_crypto_investment_ideas() -> str:
    """
    Generate crypto-specific investment ideas.
    Focuses on once-in-a-lifetime opportunities.
    """
    ideas = "## 🚀 Crypto Opportunities\n\n"
    
    # Get current prices
    prices = fetch_crypto_prices(["BTC-USD", "ETH-USD", "XRP-USD"])
    
    ideas += "### Current Prices:\n"
    for crypto, price in prices.items():
        ideas += f"- {crypto}: ${price:,.2f}\n"
    
    ideas += "\n### Once-in-a-Lifetime Crypto Plays:\n"
    ideas += "1. **Bitcoin (BTC-USD)** - Digital gold, institutional adoption\n"
    ideas += "2. **Ethereum (ETH-USD)** - Smart contract king, DeFi backbone\n"
    ideas += "3. **Crypto crashes (50%+ drops)** - Generational buying opportunities\n"
    ideas += "4. **Bitcoin ETF approvals** - Institutional inflows catalyst\n"
    
    return ideas

__all__ = [
    'fetch_crypto_prices',
    'get_crypto_market_cap',
    'analyze_crypto_portfolio',
    'get_crypto_investment_ideas'
]
