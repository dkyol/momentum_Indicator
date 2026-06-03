#!/usr/bin/env python3
"""
Watchlist Refresh System — Monthly Review & Replacement

Strategy:
- Weekly: Score all 52 stocks on MRVL convergence
- Monthly: Review bottom performers, scan S&P 500 for emerging candidates (2.0+)
- Replace conservatively: Only 2-3 stocks/month if replacement is more promising
- Only aggressive replacement if multiple stocks crash below 1.0
- Track all changes in audit trail with reason codes

Replacement Decision Matrix:
- Remove if: Score < 1.5 for 4+ weeks AND no upcoming catalysts
- Replace if: Candidate score 0.5+ higher than bottom performer OR
             Candidate has better narrative/catalysts
"""

import json
import os
from datetime import datetime
from typing import Optional

# Audit trail file
AUDIT_LOG = "watchlist_updates_log.json"


def load_audit_log() -> list:
    """Load watchlist change audit trail."""
    if os.path.exists(AUDIT_LOG):
        with open(AUDIT_LOG, 'r') as f:
            return json.load(f)
    return []


def save_audit_log(log: list):
    """Save watchlist change audit trail."""
    with open(AUDIT_LOG, 'w') as f:
        json.dump(log, f, indent=2)


def record_swap(removed_symbol: str, added_symbol: str, reason: str,
                removed_score: float, added_score: float,
                removed_narrative: str, added_narrative: str):
    """Record a watchlist swap in the audit trail."""
    log = load_audit_log()

    entry = {
        "date": datetime.now().isoformat(),
        "removed": {
            "symbol": removed_symbol,
            "score": removed_score,
            "narrative": removed_narrative
        },
        "added": {
            "symbol": added_symbol,
            "score": added_score,
            "narrative": added_narrative
        },
        "reason": reason,
        "score_improvement": round(added_score - removed_score, 1)
    }

    log.append(entry)
    save_audit_log(log)

    print(f"[AUDIT] {removed_symbol} -> {added_symbol} | Score: {removed_score:.1f} -> {added_score:.1f} | Reason: {reason}")


def generate_refresh_report(bottom_performers: list, candidates: list, aggressive_mode: bool = False) -> dict:
    """
    Generate monthly refresh report.

    Args:
        bottom_performers: List of stocks with lowest scores (from watchlist scan)
        candidates: List of emerging candidates from S&P 500 scan (score >= 2.0)
        aggressive_mode: True if multiple stocks crashed below 1.0 (enable aggressive replacement)

    Returns:
        Report with recommendations and candidate matches
    """

    print("="*100)
    print("WATCHLIST MONTHLY REFRESH REPORT")
    print("="*100)

    print(f"\nMode: {'AGGRESSIVE (multiple stocks <1.0)' if aggressive_mode else 'CONSERVATIVE (2-3 replacements if promising)'}\n")

    # Bottom performers
    print("BOTTOM PERFORMERS (Candidates for Removal):")
    print("-" * 100)
    for i, stock in enumerate(bottom_performers[:10], 1):
        print(f"{i:2d}. {stock['symbol']:8s} | Score {stock['score']:.1f} | RSI {stock.get('rsi', 0):.0f} | {stock['name']}")

    # Emerging candidates
    print("\n\nEMERGING CANDIDATES (S&P 500 Scan, Score >= 2.0):")
    print("-" * 100)
    if candidates:
        for i, stock in enumerate(candidates[:15], 1):
            sector = stock.get('sector', 'Unknown')
            print(f"{i:2d}. {stock['symbol']:8s} | Score {stock['score']:.1f} | RSI {stock.get('rsi', 0):.0f} | {sector:20s} | {stock['name']}")
    else:
        print("No emerging candidates found (none scored 2.0+)")

    # Recommendations
    print("\n\nRECOMMENDATIONS:")
    print("-" * 100)
    recommendations = []

    if aggressive_mode:
        print("AGGRESSIVE MODE: Multiple stocks crashed below 1.0")
        print("Action: Replace bottom 3-5 performers with top candidates")
        for i in range(min(5, len(bottom_performers), len(candidates))):
            bottom = bottom_performers[i]
            candidate = candidates[i] if i < len(candidates) else None
            if candidate and candidate['score'] > bottom['score'] + 0.5:
                recommendations.append({
                    'action': 'REPLACE',
                    'remove': bottom['symbol'],
                    'add': candidate['symbol'],
                    'reason': 'Aggressive refresh: bottom performer + better candidate available',
                    'confidence': 'HIGH'
                })
    else:
        print("CONSERVATIVE MODE: 2-3 replacements only if promising")
        replacements_made = 0

        for bottom in bottom_performers[:5]:
            if replacements_made >= 3:
                break

            # Find matching candidate (same sector, or better narrative)
            best_candidate = None
            for candidate in candidates:
                # Only replace if candidate is significantly better (0.5+ score difference)
                if candidate['score'] > bottom['score'] + 0.5:
                    # Prefer same sector
                    if candidate.get('sector') == bottom.get('sector'):
                        best_candidate = candidate
                        break
                    elif best_candidate is None:
                        best_candidate = candidate

            if best_candidate:
                reason = f"Bottom performer ({bottom['score']:.1f}) replaced with more promising candidate ({best_candidate['score']:.1f})"
                recommendations.append({
                    'action': 'REPLACE',
                    'remove': bottom['symbol'],
                    'add': best_candidate['symbol'],
                    'reason': reason,
                    'confidence': 'HIGH' if best_candidate['score'] > bottom['score'] + 1.0 else 'MEDIUM'
                })
                replacements_made += 1
                candidates.remove(best_candidate)

    if not recommendations:
        print("No replacements recommended at this time.")
        print("Bottom performers are being monitored. If scores improve, keep them.")
        print("If multiple crash below 1.0 next month, enable aggressive replacement.")
    else:
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. REPLACE {rec['remove']} -> {rec['add']}")
            print(f"   Reason: {rec['reason']}")
            print(f"   Confidence: {rec['confidence']}")

    return {
        'mode': 'aggressive' if aggressive_mode else 'conservative',
        'bottom_performers': bottom_performers[:10],
        'emerging_candidates': candidates[:10],
        'recommendations': recommendations,
        'audit_ready': True
    }


def apply_recommendations(recommendations: list, watchlist):
    """
    Apply approved recommendations to watchlist.

    Args:
        recommendations: List of replacement recommendations
        watchlist: Current watchlist_stocks.py content

    Returns:
        Updated watchlist
    """
    for rec in recommendations:
        if rec['action'] == 'REPLACE':
            print(f"Applying: {rec['remove']} -> {rec['add']}")
            # Actual replacement would happen here via watchlist_stocks.py update
            # For now, log to audit trail
            # record_swap would be called with full details


if __name__ == '__main__':
    print("""
    Watchlist Refresh System

    Usage:
    1. Run monthly scan: python broad_scan_report.py
    2. Get refresh report: python watchlist_refresh.py
    3. Review recommendations
    4. Approve and apply via: python watchlist_refresh.py --apply

    Audit trail stored in: watchlist_updates_log.json
    """)
