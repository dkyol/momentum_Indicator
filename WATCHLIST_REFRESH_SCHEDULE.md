# Watchlist Refresh Schedule & Audit Trail

## Strategy

**Conservative, data-driven approach with full audit trail:**

- **Weekly (Sunday 7 PM ET):** Score all 52 stocks on MRVL convergence (0-5 scale)
- **Monthly (1st Sunday):** Review bottom performers + S&P 500 emerging candidates
- **Replacement threshold:** Only replace if candidate is 0.5+ points higher
- **Aggressive threshold:** Only enabled if 3+ stocks crash below 1.0 in one month
- **Turnover target:** 2-3 replacements/month (25-36/year = full refresh in 18 months)
- **Audit trail:** Every swap logged with date, scores, reason, improvement delta

---

## Monthly Review Checklist

### Week 1 (Refresh Review)

```
[1st Sunday of month, after weekly scan completes]

1. IDENTIFY BOTTOM PERFORMERS
   - Extract bottom 10 stocks (lowest average MRVL score over 4 weeks)
   - Flag if any are below 1.5 for 4+ consecutive weeks
   - Flag if any crashed below 1.0 in past week (aggressive mode trigger)

2. SCAN S&P 500 FOR EMERGING CANDIDATES
   - Run full S&P 500 watchlist scan
   - Filter for stocks scoring 2.0+ (emerging accumulation signals)
   - Exclude stocks already on watchlist
   - Group by sector (semiconductors, space, cloud, energy, etc.)

3. MATCH & COMPARE
   - For each bottom performer:
     - Find best matching candidate (same sector preferred)
     - Calculate score improvement (new_score - old_score)
     - Assess narrative strength (catalyst visibility, TAM, partnerships)
     - Score improvement must be >= 0.5 to proceed

4. GENERATE RECOMMENDATIONS
   - Conservative: 2-3 replacements max, only if 0.5+ improvement
   - Aggressive: 3-5 replacements, enabled if multiple <1.0
   - Rank by confidence (improvement delta + narrative strength)

5. RECORD IN AUDIT TRAIL
   - For each approved swap:
     - Date, removed symbol, added symbol
     - Score before/after, improvement delta
     - Reason code (e.g., "bottom performer + better candidate")
     - Narrative comparison
```

---

## Reason Codes for Audit Trail

```
BPM_LOW_SCORE      = Bottom performer, score < 1.5 for 4+ weeks
BPM_CRASH          = Bottom performer, crashed below 1.0
BPM_NO_CATALYST    = Bottom performer, no upcoming catalysts
CAND_EMERGING      = Emerging candidate from S&P 500, score 2.0+
CAND_BETTER_NARR   = Candidate has stronger narrative/catalysts
CAND_SAME_SECTOR   = Candidate in same sector, better signals
CAND_SCORE_DELTA   = Candidate 0.5+ points higher
AGG_MODE_ACTIVE    = Aggressive replacement mode (3+ <1.0)
MANUAL_REVIEW      = Analyst manual review (external factor)
```

---

## Audit Trail Entry Format

```json
{
  "date": "2026-07-06T22:30:00Z",
  "action": "REPLACE",
  "removed": {
    "symbol": "SLAB",
    "name": "Silicon Labs",
    "score": 1.0,
    "sector": "Semiconductors",
    "avg_score_4w": 1.2
  },
  "added": {
    "symbol": "PLCE",
    "name": "Planet Labs",
    "score": 2.2,
    "sector": "Satellite",
    "catalysts": "New constellation deployment Q3 2026"
  },
  "reason_codes": ["BPM_LOW_SCORE", "CAND_EMERGING", "CAND_SCORE_DELTA"],
  "score_improvement": 1.2,
  "confidence": "HIGH",
  "analyst_note": "SLAB showed no signals for 6 weeks, PLCE emerging accumulation in satellite sector"
}
```

---

## Monthly Report Template

```
WATCHLIST REFRESH REPORT — [MONTH YEAR]
=====================================================

MODE: CONSERVATIVE (2-3 replacements if promising)

BOTTOM PERFORMERS (Candidates for Removal):
 1. SLAB | Score 1.0 | No catalysts for 8 weeks
 2. SPLK | Score 1.2 | Consolidating, no breakout signals
 3. SPIR | Score 1.0 | Space sector lagging
 4. SMR  | Score 1.3 | Limited nuclear catalysts
 5. EDIT | Score 1.1 | Biotech, gene therapy stalled

EMERGING CANDIDATES (S&P 500 Scan, Score 2.0+):
 1. PLCE | Score 2.2 | Satellite sector, new constellation
 2. IONQ | Score 2.4 | Quantum computing momentum
 3. AXON | Score 2.1 | AI-powered law enforcement
 4. CWAN | Score 2.0 | Wireless infrastructure buildout
 5. ROKU | Score 2.0 | Streaming + advertising upside

RECOMMENDATIONS:
 1. REPLACE SLAB (1.0) → PLCE (2.2)
    Reason: Bottom performer + emerging satellite signals
    Improvement: +1.2 points
    Confidence: HIGH

 2. REPLACE SPLK (1.2) → IONQ (2.4)
    Reason: Consolidation boring + quantum emerging
    Improvement: +1.2 points
    Confidence: HIGH

 3. REPLACE SPIR (1.0) → AXON (2.1)
    Reason: Space weak, pivot to AI robotics
    Improvement: +1.1 points
    Confidence: MEDIUM

AGGRESSIVE MODE TRIGGERED: Yes (4 stocks < 1.0)
 → Enable 3-5 replacements instead of 2-3

AUDIT TRAIL: Updated watchlist_updates_log.json
```

---

## Tool Usage

### Check Current Watchlist
```bash
python -c "from watchlist_stocks import get_watchlist; \
  stocks = get_watchlist(); \
  print(f'Current: {len(stocks)} stocks')"
```

### Run Monthly Review
```bash
# 1. Scan all 52 stocks (already runs on Sunday)
python broad_scan_report.py

# 2. Get refresh report
python watchlist_refresh.py

# 3. Approve recommendations (manual step)
# Edit watchlist_updates_log.json to add approval notes

# 4. Apply approved swaps
python watchlist_refresh.py --apply
```

### View Audit Trail
```bash
cat watchlist_updates_log.json | python -m json.tool
```

---

## Key Metrics to Track

| Metric | Target | Review Frequency |
|--------|--------|------------------|
| Avg watchlist MRVL score | 2.5-3.0 | Weekly |
| % stocks in ACCUMULATING tier | 25-35% | Weekly |
| % stocks in EARLY SIGNALS tier | 40-50% | Weekly |
| Bottom performer avg score | >1.2 | Weekly |
| Monthly replacements | 2-3 (avg) | Monthly |
| Candidate pool size | 15-25 available | Monthly |
| Improvement delta per swap | 0.5-1.5 points | Monthly |

---

## Sample Audit Trail (First 6 Months)

```json
[
  {
    "date": "2026-07-06",
    "replacement_num": 1,
    "removed": "SLAB (1.0)",
    "added": "PLCE (2.2)",
    "improvement": 1.2,
    "reason": "Bottom performer + emerging satellite"
  },
  {
    "date": "2026-07-06",
    "replacement_num": 2,
    "removed": "SPLK (1.2)",
    "added": "IONQ (2.4)",
    "improvement": 1.2,
    "reason": "Consolidation boring + quantum momentum"
  },
  {
    "date": "2026-07-06",
    "replacement_num": 3,
    "removed": "SPIR (1.0)",
    "added": "AXON (2.1)",
    "improvement": 1.1,
    "reason": "Aggressive mode: 4 stocks <1.0"
  },
  {
    "date": "2026-08-03",
    "replacement_num": 4,
    "removed": "EDIT (1.1)",
    "added": "RKLB (2.3)",
    "improvement": 1.2,
    "reason": "Biotech weak, RKLB emerging space momentum"
  },
  {
    "date": "2026-08-03",
    "replacement_num": 5,
    "removed": "SMR (1.3)",
    "added": "CWAN (2.0)",
    "improvement": 0.7,
    "reason": "Conservative replacement, borderline candidate"
  },
  {
    "date": "2026-09-07",
    "note": "No replacements - watchlist stable, emerging candidates < 2.0",
    "action": "HOLD"
  }
]
```

---

## Next Steps

1. **This week:** Monitor bottom performers (SLAB, SPLK, SPIR, SMR, EDIT)
2. **1st Sunday of month:** Run full refresh review
3. **Monthly:** Execute 2-3 replacements if promising candidates available
4. **Track everything** in audit trail for transparency

This approach balances:
- **Stability:** Only 2-3 changes/month (not chaotic)
- **Optimization:** Always hunting for better opportunities
- **Discipline:** Data-driven replacements, not emotion
- **Transparency:** Every swap logged with reason and score delta
