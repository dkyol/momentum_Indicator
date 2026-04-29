"""
Universe & sector mapping for the alpha engine.

Replaces the hard-coded 15-ticker list with a curated S&P 100-style
list of liquid US large caps tagged by GICS sector and mapped to
Sector SPDR ETFs (used by the relative strength engine).

The universe is intentionally curated rather than scraped so that:
  * the app boots without external web requests
  * fundamentals / price refreshes are bounded and predictable
  * we have an explicit per-ticker sector tag (yfinance .info is
    slow and unreliable for sector lookups)

A user can extend the list freely – every downstream module reads
from get_universe() and works for any size.
"""

from __future__ import annotations

# Sector SPDR ETFs – used as the relative strength benchmark per
# sector. Symbols match standard SPDR Select Sector ETF tickers.
SECTOR_ETFS: dict[str, str] = {
    "Information Technology": "XLK",
    "Communication Services": "XLC",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Health Care": "XLV",
    "Financials": "XLF",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
}

# Broad market benchmark – used as the absolute relative-strength
# anchor and as the regime indicator.
MARKET_BENCHMARK = "SPY"

# Volatility & breadth references for the market-regime panel.
VIX_SYMBOL = "^VIX"

# (ticker, sector) pairs. Curated S&P 100-style large caps plus a
# handful of liquid mid-caps the original dashboard tracked. Sectors
# follow GICS naming and match SECTOR_ETFS keys.
_UNIVERSE: list[tuple[str, str]] = [
    # Information Technology
    ("AAPL", "Information Technology"),
    ("MSFT", "Information Technology"),
    ("NVDA", "Information Technology"),
    ("AVGO", "Information Technology"),
    ("ORCL", "Information Technology"),
    ("CRM", "Information Technology"),
    ("ADBE", "Information Technology"),
    ("CSCO", "Information Technology"),
    ("ACN", "Information Technology"),
    ("AMD", "Information Technology"),
    ("INTC", "Information Technology"),
    ("QCOM", "Information Technology"),
    ("IBM", "Information Technology"),
    ("TXN", "Information Technology"),
    ("MU", "Information Technology"),
    ("AMAT", "Information Technology"),
    ("NOW", "Information Technology"),
    ("INTU", "Information Technology"),
    ("PANW", "Information Technology"),
    ("SMCI", "Information Technology"),
    ("CRDO", "Information Technology"),
    # Communication Services
    ("GOOGL", "Communication Services"),
    ("META", "Communication Services"),
    ("NFLX", "Communication Services"),
    ("DIS", "Communication Services"),
    ("CMCSA", "Communication Services"),
    ("VZ", "Communication Services"),
    ("T", "Communication Services"),
    # Consumer Discretionary
    ("AMZN", "Consumer Discretionary"),
    ("TSLA", "Consumer Discretionary"),
    ("HD", "Consumer Discretionary"),
    ("MCD", "Consumer Discretionary"),
    ("NKE", "Consumer Discretionary"),
    ("SBUX", "Consumer Discretionary"),
    ("LOW", "Consumer Discretionary"),
    ("BKNG", "Consumer Discretionary"),
    ("TJX", "Consumer Discretionary"),
    # Consumer Staples
    ("WMT", "Consumer Staples"),
    ("PG", "Consumer Staples"),
    ("KO", "Consumer Staples"),
    ("PEP", "Consumer Staples"),
    ("COST", "Consumer Staples"),
    ("PM", "Consumer Staples"),
    ("MO", "Consumer Staples"),
    # Health Care
    ("UNH", "Health Care"),
    ("LLY", "Health Care"),
    ("JNJ", "Health Care"),
    ("ABBV", "Health Care"),
    ("MRK", "Health Care"),
    ("PFE", "Health Care"),
    ("TMO", "Health Care"),
    ("ABT", "Health Care"),
    ("DHR", "Health Care"),
    ("BMY", "Health Care"),
    ("AMGN", "Health Care"),
    ("GILD", "Health Care"),
    # Financials
    ("BRK-B", "Financials"),
    ("JPM", "Financials"),
    ("V", "Financials"),
    ("MA", "Financials"),
    ("BAC", "Financials"),
    ("WFC", "Financials"),
    ("GS", "Financials"),
    ("MS", "Financials"),
    ("AXP", "Financials"),
    ("BLK", "Financials"),
    ("C", "Financials"),
    ("SCHW", "Financials"),
    ("HOOD", "Financials"),
    ("COIN", "Financials"),
    # Industrials
    ("CAT", "Industrials"),
    ("BA", "Industrials"),
    ("HON", "Industrials"),
    ("UPS", "Industrials"),
    ("RTX", "Industrials"),
    ("GE", "Industrials"),
    ("LMT", "Industrials"),
    ("DE", "Industrials"),
    ("UNP", "Industrials"),
    # Energy
    ("XOM", "Energy"),
    ("CVX", "Energy"),
    ("COP", "Energy"),
    ("SLB", "Energy"),
    ("EOG", "Energy"),
    ("OXY", "Energy"),
    # Materials
    ("LIN", "Materials"),
    ("APD", "Materials"),
    ("SHW", "Materials"),
    ("FCX", "Materials"),
    ("EGO", "Materials"),
    # Utilities
    ("NEE", "Utilities"),
    ("DUK", "Utilities"),
    ("SO", "Utilities"),
    # Real Estate
    ("AMT", "Real Estate"),
    ("PLD", "Real Estate"),
    ("EQIX", "Real Estate"),
    # Specialty / high-momentum names from the original watchlist
    ("IONQ", "Information Technology"),
    ("ASTS", "Communication Services"),
    ("RBRK", "Information Technology"),
    ("OPFI", "Financials"),
]


def get_universe() -> list[str]:
    """Return the list of tickers in the active universe."""
    return [t for t, _ in _UNIVERSE]


def get_sector_map() -> dict[str, str]:
    """Return {ticker: GICS sector} for every name in the universe."""
    return {t: s for t, s in _UNIVERSE}


def get_sector_etf(sector: str) -> str | None:
    """Return the sector ETF ticker for a GICS sector name."""
    return SECTOR_ETFS.get(sector)


def get_all_benchmark_tickers() -> list[str]:
    """Tickers that always need price data even if not in the universe."""
    return [MARKET_BENCHMARK, VIX_SYMBOL] + list(SECTOR_ETFS.values())
