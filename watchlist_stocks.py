#!/usr/bin/env python3
"""
Cross-Industry Watchlist for MRVL-Like Accumulation Patterns

Strategy: Scan broadly across industries and let the 5 MRVL indicators (RVOL, OBV, MFI, ADX, A/D)
identify which stocks are showing spring loading patterns. Narrative analysis comes AFTER we see
what's accumulating.

Includes:
- AI Infrastructure (custom chips, servers, networking, cooling)
- Space/Satellite Tech (LUNR, RKLB, SPIR, etc.)
- Semiconductors (broad coverage)
- Cloud/SaaS
- Quantum Computing
- Robotics/Automation
- Energy (renewables, nuclear, grid)
- Biotech/Synthetic Biology
- And others showing high growth potential

Scoring removed intentionally. Let MRVL indicators determine which stocks are worth buying.
"""

WATCHLIST = [
    # ============================================================================
    # AI INFRASTRUCTURE (Original focus)
    # ============================================================================
    {"symbol": "COHR", "name": "Coherent Corp",              "sector": "Photonics", "theme": "AI Infrastructure"},
    {"symbol": "LITE", "name": "Lumentum Holdings",          "sector": "Photonics", "theme": "AI Infrastructure"},
    {"symbol": "AVGO", "name": "Broadcom",                   "sector": "Semiconductors", "theme": "AI Infrastructure"},
    {"symbol": "SMCI", "name": "Super Micro Computer",       "sector": "Hardware", "theme": "AI Infrastructure"},
    {"symbol": "VIAV", "name": "VIAVI Solutions",            "sector": "Optical Test", "theme": "AI Infrastructure"},
    {"symbol": "VRT",  "name": "Vertiv",                     "sector": "Data Center", "theme": "AI Infrastructure"},
    {"symbol": "CRWV", "name": "CoreWeave",                  "sector": "Cloud", "theme": "AI Infrastructure"},
    {"symbol": "ANET", "name": "Arista Networks",            "sector": "Networking", "theme": "AI Infrastructure"},
    {"symbol": "DELL", "name": "Dell Technologies",          "sector": "Hardware", "theme": "AI Infrastructure"},
    {"symbol": "PSTG", "name": "Pure Storage",               "sector": "Storage", "theme": "AI Infrastructure"},

    # ============================================================================
    # SPACE & SATELLITE TECH (Broader tech expansion)
    # ============================================================================
    {"symbol": "LUNR", "name": "Lunar",                      "sector": "Space", "theme": "Space Tech"},
    {"symbol": "RKLB", "name": "Rocket Lab",                 "sector": "Space", "theme": "Space Tech"},
    {"symbol": "SPIR", "name": "Spire Global",               "sector": "Satellite", "theme": "Space Tech"},
    {"symbol": "AXIOM", "name": "Axiom Space",               "sector": "Space", "theme": "Space Tech"},
    {"symbol": "PLCE", "name": "Planet Labs",                "sector": "Satellite", "theme": "Space Tech"},

    # ============================================================================
    # SEMICONDUCTORS (Broad coverage)
    # ============================================================================
    {"symbol": "NVDA", "name": "NVIDIA",                     "sector": "Semiconductors", "theme": "AI Chips"},
    {"symbol": "AMD",  "name": "Advanced Micro Devices",     "sector": "Semiconductors", "theme": "AI Chips"},
    {"symbol": "QCOM", "name": "Qualcomm",                   "sector": "Semiconductors", "theme": "Mobile AI"},
    {"symbol": "NXPI", "name": "NXP Semiconductors",         "sector": "Semiconductors", "theme": "Edge AI"},
    {"symbol": "MU",   "name": "Micron Technology",          "sector": "Semiconductors", "theme": "Memory"},
    {"symbol": "SLAB", "name": "Silicon Labs",               "sector": "Semiconductors", "theme": "IoT/Edge"},
    {"symbol": "ASML", "name": "ASML",                       "sector": "Semiconductors", "theme": "Chip Equipment"},
    {"symbol": "LRCX", "name": "Lam Research",               "sector": "Semiconductors", "theme": "Chip Equipment"},
    {"symbol": "KLAC", "name": "KLA Corporation",            "sector": "Semiconductors", "theme": "Chip Equipment"},

    # ============================================================================
    # CLOUD & SAAS (Artificial intelligence expansion)
    # ============================================================================
    {"symbol": "MSFT", "name": "Microsoft",                  "sector": "Cloud", "theme": "Azure AI"},
    {"symbol": "GOOGL", "name": "Alphabet",                  "sector": "Cloud", "theme": "Google Cloud AI"},
    {"symbol": "AMZN", "name": "Amazon",                     "sector": "Cloud", "theme": "AWS AI"},
    {"symbol": "SNOW", "name": "Snowflake",                  "sector": "Cloud", "theme": "Data/ML"},
    {"symbol": "DDOG", "name": "Datadog",                    "sector": "SaaS", "theme": "Monitoring/AI"},
    {"symbol": "OKTA", "name": "Okta",                       "sector": "SaaS", "theme": "Identity"},
    {"symbol": "NET",  "name": "Cloudflare",                 "sector": "Cloud", "theme": "Edge Computing"},

    # ============================================================================
    # QUANTUM COMPUTING (Emerging AI-adjacent)
    # ============================================================================
    {"symbol": "IONQ", "name": "IonQ",                       "sector": "Quantum", "theme": "Quantum Computing"},
    {"symbol": "RIGETTI", "name": "Rigetti Computing",       "sector": "Quantum", "theme": "Quantum Computing"},

    # ============================================================================
    # ROBOTICS & AUTOMATION (AI-powered)
    # ============================================================================
    {"symbol": "TSLA", "name": "Tesla",                      "sector": "Automotive", "theme": "AI Robots/FSD"},
    {"symbol": "ABB",  "name": "ABB",                        "sector": "Industrial", "theme": "Robotics"},
    {"symbol": "IRBT", "name": "iRobot",                     "sector": "Robotics", "theme": "Consumer Robots"},
    {"symbol": "MARA", "name": "Marathon",                   "sector": "Robotics", "theme": "Humanoid Robots"},

    # ============================================================================
    # ENERGY (Grid modernization, AI-powered optimization)
    # ============================================================================
    {"symbol": "PLUG", "name": "Plug Power",                 "sector": "Energy", "theme": "Hydrogen Fuel"},
    {"symbol": "LCID", "name": "Lucid Motors",               "sector": "Automotive", "theme": "EV/AI"},
    {"symbol": "NIO",  "name": "NIO",                        "sector": "Automotive", "theme": "EV/AI"},
    {"symbol": "RUN",  "name": "Sunrun",                     "sector": "Renewable", "theme": "Solar"},
    {"symbol": "ENPH", "name": "Enphase Energy",             "sector": "Renewable", "theme": "Solar"},
    {"symbol": "CEG",  "name": "Constellation Energy",       "sector": "Nuclear", "theme": "Nuclear Power"},
    {"symbol": "SMR",  "name": "NuScale Power",              "sector": "Nuclear", "theme": "Small Reactors"},

    # ============================================================================
    # BIOTECH & SYNTHETIC BIOLOGY (AI-accelerated discovery)
    # ============================================================================
    {"symbol": "EDIT", "name": "EDITAS Medicine",            "sector": "Biotech", "theme": "CRISPR/Gene Edit"},
    {"symbol": "CRSP", "name": "CRISPR Therapeutics",        "sector": "Biotech", "theme": "CRISPR"},
    {"symbol": "GKOS", "name": "Ginkgo Bioworks",            "sector": "Biotech", "theme": "Synthetic Bio"},
    {"symbol": "BNTX", "name": "BioNTech",                   "sector": "Biotech", "theme": "mRNA/AI"},

    # ============================================================================
    # NETWORKING & TELECOM (AI infrastructure, 5G/6G buildout)
    # ============================================================================
    {"symbol": "MSTR", "name": "MicroStrategy",              "sector": "Enterprise", "theme": "Data/BI"},
    {"symbol": "SPLK", "name": "Splunk",                     "sector": "Enterprise", "theme": "Log Analytics"},
    {"symbol": "CRM",  "name": "Salesforce",                 "sector": "SaaS", "theme": "CRM/AI"},

    # ============================================================================
    # BENCHMARK (For comparison)
    # ============================================================================
    {"symbol": "MRVL", "name": "Marvell Technology",         "sector": "Semiconductors", "theme": "MRVL Benchmark (300% March-June 2026)"},
]


def get_watchlist():
    """Return full watchlist with metadata."""
    return WATCHLIST


def get_watchlist_symbols():
    """Return just the tickers for scanning."""
    return [item["symbol"] for item in WATCHLIST]


def get_watchlist_by_sector(sector: str):
    """Get all stocks in a specific sector."""
    return [item for item in WATCHLIST if item.get("sector") == sector]


def get_watchlist_by_theme(theme: str):
    """Get all stocks in a specific theme."""
    return [item for item in WATCHLIST if item.get("theme") == theme]


def get_sectors():
    """Get list of all sectors in watchlist."""
    return sorted(set(item.get("sector") for item in WATCHLIST if item.get("sector")))


def get_themes():
    """Get list of all themes in watchlist."""
    return sorted(set(item.get("theme") for item in WATCHLIST if item.get("theme")))
