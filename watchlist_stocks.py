"""
AI Infrastructure Watchlist — 23 stocks + MRVL benchmark

Scored against the MRVL framework:
- Business Narrative (30 pts): AI tailwinds + partnerships
- Catalyst Visibility (20 pts): Near-term catalysts
- Valuation Setup (20 pts): P/E vs. growth
- Technical Setup (15 pts): Volume/RSI/ADX signals
- Growth Potential (15 pts): Multi-year TAM

Monitored weekly for MRVL-like volume indicator convergence (RVOL, OBV, MFI, ADX, A/D).
"""

WATCHLIST = [
    # Tier 1 — High-conviction, highest MRVL-like scores (75+)
    {"symbol": "COHR", "name": "Coherent Corp",              "score": 96, "tier": 1, "narrative": "NVIDIA $2B optical partner, CPO"},
    {"symbol": "LITE", "name": "Lumentum Holdings",          "score": 94, "tier": 1, "narrative": "Photonics supply +85% growth YoY"},
    {"symbol": "AVGO", "name": "Broadcom",                   "score": 92, "tier": 1, "narrative": "Custom AI chips for hyperscalers"},
    {"symbol": "SMCI", "name": "Super Micro Computer",       "score": 88, "tier": 1, "narrative": "AI server builder +123% YoY"},
    {"symbol": "VIAV", "name": "VIAVI Solutions",            "score": 82, "tier": 1, "narrative": "Optical testing monopoly, 60-70% share"},
    {"symbol": "VRT",  "name": "Vertiv",                     "score": 82, "tier": 1, "narrative": "Data center cooling + power architecture"},
    {"symbol": "ANET", "name": "Arista Networks",            "score": 78, "tier": 1, "narrative": "AI cluster 400G/800G networking"},

    # Tier 2 — Secondary setups (65-75)
    {"symbol": "DELL", "name": "Dell Technologies",          "score": 72, "tier": 2, "narrative": "AI server & infrastructure market expansion"},
    {"symbol": "TSLA", "name": "Tesla",                      "score": 72, "tier": 2, "narrative": "FSD AI, Optimus robot, Dojo AI supercomputer"},
    {"symbol": "PSTG", "name": "Pure Storage",               "score": 71, "tier": 2, "narrative": "AI data storage infrastructure"},
    {"symbol": "AMD",  "name": "Advanced Micro Devices",     "score": 70, "tier": 2, "narrative": "GPU/CPU competition with NVDA"},
    {"symbol": "NXPI", "name": "NXP Semiconductors",         "score": 69, "tier": 2, "narrative": "Edge AI chips for IoT/automotive"},
    {"symbol": "QCOM", "name": "Qualcomm",                   "score": 68, "tier": 2, "narrative": "On-device AI inference snapdragon"},

    # Tier 3 — Speculative setups (55-65)
    {"symbol": "KLAC", "name": "KLA Corporation",            "score": 63, "tier": 3, "narrative": "Semiconductor process control equipment"},
    {"symbol": "LRCX", "name": "Lam Research",               "score": 62, "tier": 3, "narrative": "Semiconductor deposition equipment"},
    {"symbol": "MOD",  "name": "Modine Manufacturing",       "score": 61, "tier": 3, "narrative": "Data center thermal management"},
    {"symbol": "ETN",  "name": "Eaton",                      "score": 58, "tier": 3, "narrative": "Electrical infrastructure, UPS, power"},
    {"symbol": "GTLS", "name": "Chart Industries",           "score": 56, "tier": 3, "narrative": "Cooling gas infrastructure"},
    {"symbol": "MSFT", "name": "Microsoft",                  "score": 55, "tier": 3, "narrative": "Azure AI platform & copilot integration"},

    # Tier 4 — Long shots (under 55)
    {"symbol": "MU",   "name": "Micron Technology",          "score": 52, "tier": 4, "narrative": "AI memory (HBM) ramp-up"},
    {"symbol": "SLAB", "name": "Silicon Labs",               "score": 51, "tier": 4, "narrative": "IoT/edge AI microcontroller chips"},
    {"symbol": "TTM",  "name": "TTM Technologies",           "score": 48, "tier": 4, "narrative": "Printed circuit boards for AI hardware"},

    # Tier 0 — Benchmark (MRVL case study)
    {"symbol": "MRVL", "name": "Marvell Technology",         "score": 95, "tier": 0, "narrative": "BENCHMARK: custom AI chips, 300% move March-June"},
]


def get_watchlist() -> list[dict]:
    """Return full watchlist with metadata."""
    return WATCHLIST


def get_watchlist_symbols() -> list[str]:
    """Return just the tickers for scanning."""
    return [item["symbol"] for item in WATCHLIST]


def get_watchlist_by_tier(tier: int) -> list[dict]:
    """Get all stocks in a specific tier."""
    return [item for item in WATCHLIST if item["tier"] == tier]
