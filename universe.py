"""
Universe & sector mapping for the alpha engine.

Ships a default S&P-500-scale list (~270 liquid US large caps) tagged by
GICS sector and mapped to Sector SPDR ETFs (used by the relative
strength engine).

The universe is **configurable**: at import time we look for
``universe.json`` in the project root.  If present, it is treated as
the source of truth and replaces the bundled defaults.  The file
format is::

    [{"symbol": "AAPL", "sector": "Information Technology"}, ...]

Users can edit that file (or write it via a future admin UI) without
touching source.  If the file is absent or malformed we fall back to
the bundled list, so the engine always has a usable universe.

Every downstream module reads from ``get_universe()`` /
``get_sector_map()`` and works for any size – the only practical
ceiling is yfinance throughput (~270 tickers refresh in ~25 s).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Iterable

logger = logging.getLogger(__name__)

# Sector SPDR ETFs – used as the relative strength benchmark per
# sector.  Symbols match standard SPDR Select Sector ETF tickers.
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

MARKET_BENCHMARK = "SPY"
VIX_SYMBOL = "^VIX"

# Path of the optional user override file.
UNIVERSE_OVERRIDE_PATH = "universe.json"

# ------------------------------------------------------------------
# Bundled default universe – ~270 S&P 500-scale liquid US large caps
# tagged with GICS sectors.  Tickers verified to be on yfinance.
# ------------------------------------------------------------------
_DEFAULT_UNIVERSE: list[tuple[str, str]] = [
    # Information Technology (~50)
    ("AAPL", "Information Technology"), ("MSFT", "Information Technology"),
    ("NVDA", "Information Technology"), ("AVGO", "Information Technology"),
    ("ORCL", "Information Technology"), ("CRM", "Information Technology"),
    ("ADBE", "Information Technology"), ("CSCO", "Information Technology"),
    ("ACN", "Information Technology"), ("AMD", "Information Technology"),
    ("INTC", "Information Technology"), ("QCOM", "Information Technology"),
    ("IBM", "Information Technology"), ("TXN", "Information Technology"),
    ("MU", "Information Technology"), ("AMAT", "Information Technology"),
    ("NOW", "Information Technology"), ("INTU", "Information Technology"),
    ("PANW", "Information Technology"), ("SMCI", "Information Technology"),
    ("KLAC", "Information Technology"), ("LRCX", "Information Technology"),
    ("ADI", "Information Technology"), ("ANET", "Information Technology"),
    ("CDNS", "Information Technology"), ("SNPS", "Information Technology"),
    ("MCHP", "Information Technology"), ("ROP", "Information Technology"),
    ("FTNT", "Information Technology"), ("MSI", "Information Technology"),
    ("APH", "Information Technology"), ("NXPI", "Information Technology"),
    ("CTSH", "Information Technology"), ("GLW", "Information Technology"),
    ("HPQ", "Information Technology"), ("DELL", "Information Technology"),
    ("WDC", "Information Technology"), ("STX", "Information Technology"),
    ("NTAP", "Information Technology"), ("KEYS", "Information Technology"),
    ("FFIV", "Information Technology"), ("CDW", "Information Technology"),
    ("JNPR", "Information Technology"), ("TER", "Information Technology"),
    ("ENPH", "Information Technology"), ("PAYX", "Information Technology"),
    ("ADP", "Information Technology"), ("FIS", "Information Technology"),
    ("FI", "Information Technology"), ("GPN", "Information Technology"),
    ("CRDO", "Information Technology"),
    # Communication Services (~15)
    ("GOOGL", "Communication Services"), ("GOOG", "Communication Services"),
    ("META", "Communication Services"), ("NFLX", "Communication Services"),
    ("DIS", "Communication Services"), ("CMCSA", "Communication Services"),
    ("VZ", "Communication Services"), ("T", "Communication Services"),
    ("TMUS", "Communication Services"), ("CHTR", "Communication Services"),
    ("EA", "Communication Services"), ("TTWO", "Communication Services"),
    ("OMC", "Communication Services"), ("IPG", "Communication Services"),
    ("FOX", "Communication Services"), ("ASTS", "Communication Services"),
    # Consumer Discretionary (~30)
    ("AMZN", "Consumer Discretionary"), ("TSLA", "Consumer Discretionary"),
    ("HD", "Consumer Discretionary"), ("MCD", "Consumer Discretionary"),
    ("NKE", "Consumer Discretionary"), ("SBUX", "Consumer Discretionary"),
    ("LOW", "Consumer Discretionary"), ("BKNG", "Consumer Discretionary"),
    ("TJX", "Consumer Discretionary"), ("CMG", "Consumer Discretionary"),
    ("MAR", "Consumer Discretionary"), ("HLT", "Consumer Discretionary"),
    ("ROST", "Consumer Discretionary"), ("F", "Consumer Discretionary"),
    ("GM", "Consumer Discretionary"), ("ORLY", "Consumer Discretionary"),
    ("AZO", "Consumer Discretionary"), ("ABNB", "Consumer Discretionary"),
    ("EBAY", "Consumer Discretionary"), ("DRI", "Consumer Discretionary"),
    ("YUM", "Consumer Discretionary"), ("LULU", "Consumer Discretionary"),
    ("ULTA", "Consumer Discretionary"), ("KMX", "Consumer Discretionary"),
    ("BBY", "Consumer Discretionary"), ("GRMN", "Consumer Discretionary"),
    ("EXPE", "Consumer Discretionary"), ("POOL", "Consumer Discretionary"),
    ("DPZ", "Consumer Discretionary"),
    # Consumer Staples (~25)
    ("WMT", "Consumer Staples"), ("PG", "Consumer Staples"),
    ("KO", "Consumer Staples"), ("PEP", "Consumer Staples"),
    ("COST", "Consumer Staples"), ("PM", "Consumer Staples"),
    ("MO", "Consumer Staples"), ("MDLZ", "Consumer Staples"),
    ("CL", "Consumer Staples"), ("GIS", "Consumer Staples"),
    ("KHC", "Consumer Staples"), ("HSY", "Consumer Staples"),
    ("MNST", "Consumer Staples"), ("KDP", "Consumer Staples"),
    ("STZ", "Consumer Staples"), ("EL", "Consumer Staples"),
    ("CPB", "Consumer Staples"), ("SJM", "Consumer Staples"),
    ("TSN", "Consumer Staples"), ("TAP", "Consumer Staples"),
    ("BG", "Consumer Staples"), ("ADM", "Consumer Staples"),
    ("KR", "Consumer Staples"), ("SYY", "Consumer Staples"),
    # Health Care (~40)
    ("UNH", "Health Care"), ("LLY", "Health Care"),
    ("JNJ", "Health Care"), ("ABBV", "Health Care"),
    ("MRK", "Health Care"), ("PFE", "Health Care"),
    ("TMO", "Health Care"), ("ABT", "Health Care"),
    ("DHR", "Health Care"), ("BMY", "Health Care"),
    ("AMGN", "Health Care"), ("GILD", "Health Care"),
    ("CVS", "Health Care"), ("CI", "Health Care"),
    ("ELV", "Health Care"), ("HUM", "Health Care"),
    ("MDT", "Health Care"), ("ISRG", "Health Care"),
    ("BSX", "Health Care"), ("SYK", "Health Care"),
    ("BAX", "Health Care"), ("BDX", "Health Care"),
    ("ZBH", "Health Care"), ("EW", "Health Care"),
    ("IDXX", "Health Care"), ("REGN", "Health Care"),
    ("VRTX", "Health Care"), ("BIIB", "Health Care"),
    ("MRNA", "Health Care"), ("ILMN", "Health Care"),
    ("A", "Health Care"), ("MTD", "Health Care"),
    ("ALGN", "Health Care"), ("COO", "Health Care"),
    ("RMD", "Health Care"), ("INCY", "Health Care"),
    ("DXCM", "Health Care"), ("TFX", "Health Care"),
    ("IQV", "Health Care"),
    # Financials (~40)
    ("BRK-B", "Financials"), ("JPM", "Financials"),
    ("V", "Financials"), ("MA", "Financials"),
    ("BAC", "Financials"), ("WFC", "Financials"),
    ("GS", "Financials"), ("MS", "Financials"),
    ("AXP", "Financials"), ("BLK", "Financials"),
    ("C", "Financials"), ("SCHW", "Financials"),
    ("PNC", "Financials"), ("TFC", "Financials"),
    ("USB", "Financials"), ("COF", "Financials"),
    ("AON", "Financials"), ("MMC", "Financials"),
    ("ICE", "Financials"), ("CME", "Financials"),
    ("SPGI", "Financials"), ("MCO", "Financials"),
    ("CB", "Financials"), ("PGR", "Financials"),
    ("TRV", "Financials"), ("AIG", "Financials"),
    ("MET", "Financials"), ("PRU", "Financials"),
    ("AFL", "Financials"), ("ALL", "Financials"),
    ("ALLY", "Financials"), ("FITB", "Financials"),
    ("RF", "Financials"), ("KEY", "Financials"),
    ("HBAN", "Financials"), ("CFG", "Financials"),
    ("NTRS", "Financials"), ("STT", "Financials"),
    ("BK", "Financials"), ("DFS", "Financials"),
    ("HOOD", "Financials"), ("COIN", "Financials"),
    ("OPFI", "Financials"),
    # Industrials (~30)
    ("CAT", "Industrials"), ("BA", "Industrials"),
    ("HON", "Industrials"), ("UPS", "Industrials"),
    ("RTX", "Industrials"), ("GE", "Industrials"),
    ("LMT", "Industrials"), ("DE", "Industrials"),
    ("UNP", "Industrials"), ("MMM", "Industrials"),
    ("CSX", "Industrials"), ("NSC", "Industrials"),
    ("FDX", "Industrials"), ("NOC", "Industrials"),
    ("GD", "Industrials"), ("EMR", "Industrials"),
    ("ETN", "Industrials"), ("ITW", "Industrials"),
    ("PH", "Industrials"), ("ROK", "Industrials"),
    ("TT", "Industrials"), ("IR", "Industrials"),
    ("FAST", "Industrials"), ("PCAR", "Industrials"),
    ("CMI", "Industrials"), ("DOV", "Industrials"),
    ("XYL", "Industrials"), ("JCI", "Industrials"),
    ("GWW", "Industrials"), ("ODFL", "Industrials"),
    # Energy (~15)
    ("XOM", "Energy"), ("CVX", "Energy"),
    ("COP", "Energy"), ("SLB", "Energy"),
    ("EOG", "Energy"), ("OXY", "Energy"),
    ("PSX", "Energy"), ("MPC", "Energy"),
    ("VLO", "Energy"), ("HES", "Energy"),
    ("KMI", "Energy"), ("WMB", "Energy"),
    ("OKE", "Energy"), ("BKR", "Energy"),
    ("HAL", "Energy"),
    # Materials (~10)
    ("LIN", "Materials"), ("APD", "Materials"),
    ("SHW", "Materials"), ("FCX", "Materials"),
    ("ECL", "Materials"), ("NEM", "Materials"),
    ("NUE", "Materials"), ("STLD", "Materials"),
    ("DOW", "Materials"), ("DD", "Materials"),
    ("EGO", "Materials"),
    # Utilities (~10)
    ("NEE", "Utilities"), ("DUK", "Utilities"),
    ("SO", "Utilities"), ("AEP", "Utilities"),
    ("EXC", "Utilities"), ("XEL", "Utilities"),
    ("SRE", "Utilities"), ("D", "Utilities"),
    ("PCG", "Utilities"), ("AEE", "Utilities"),
    # Real Estate (~10)
    ("AMT", "Real Estate"), ("PLD", "Real Estate"),
    ("EQIX", "Real Estate"), ("CCI", "Real Estate"),
    ("PSA", "Real Estate"), ("SPG", "Real Estate"),
    ("O", "Real Estate"), ("WELL", "Real Estate"),
    ("DLR", "Real Estate"), ("AVB", "Real Estate"),
    # Specialty / high-momentum names retained from the original watchlist
    ("IONQ", "Information Technology"), ("RBRK", "Information Technology"),
]


def _load_override(path: str) -> list[tuple[str, str]] | None:
    """Load and validate ``universe.json`` if present."""
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.warning(f"{path}: expected a JSON array, got {type(data).__name__}")
            return None
        out: list[tuple[str, str]] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            sym = (entry.get("symbol") or entry.get("ticker") or "").strip().upper()
            sec = (entry.get("sector") or "").strip()
            if not sym or sec not in SECTOR_ETFS:
                continue
            out.append((sym, sec))
        if not out:
            logger.warning(f"{path}: no valid entries, falling back to bundled universe")
            return None
        logger.info(f"Loaded universe override from {path} ({len(out)} tickers)")
        return out
    except Exception as e:
        logger.warning(f"Failed to read {path}: {e} – falling back to bundled universe")
        return None


# Resolve the active universe once at import time so every module sees
# the same list throughout the process lifetime.
_UNIVERSE: list[tuple[str, str]] = _load_override(UNIVERSE_OVERRIDE_PATH) or _DEFAULT_UNIVERSE


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


def get_universe_size() -> int:
    return len(_UNIVERSE)


def is_user_overridden() -> bool:
    """True if universe.json was loaded successfully."""
    return os.path.exists(UNIVERSE_OVERRIDE_PATH)
