"""Portfolio performance analytics for the paper trader.

This module is intentionally framework-free: every function takes plain
Python data (lists / dicts / numbers) and returns plain Python data, so
the same logic can be unit-tested without spinning up Flask or
SQLAlchemy.  The Flask layer (`app.py`) is responsible for fetching the
data via the ORM and passing it into these helpers.

The "strategy" we measure here is whatever has been writing to the
`trades` and `equity_snapshots` tables - today that is the momentum
paper trader, but the API is strategy-agnostic so a future Edge-Score
trader can plug in unchanged.
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Iterable

import pytz

from models import (
    EquitySnapshot,
    Portfolio,
    Position,
    Trade,
    create_tables,
    get_session,
)

logger = logging.getLogger(__name__)

INITIAL_INVESTMENT = 10000.0
EST = pytz.timezone("US/Eastern")


# ---------------------------------------------------------------------------
# Snapshot capture (writes to DB)
# ---------------------------------------------------------------------------


def _today_est_iso() -> str:
    return datetime.now(EST).strftime("%Y-%m-%d")


def take_equity_snapshot(get_current_price=None, snapshot_date: str | None = None) -> dict | None:
    """Persist a single end-of-day equity snapshot for today (US/Eastern).

    Idempotent per `snapshot_date` - calling repeatedly the same day
    updates the existing row rather than inserting duplicates.

    `get_current_price` is an optional callable `(symbol) -> float|None`
    used to value open positions.  When omitted the snapshot still
    records cash + realized PnL and falls back to position cost basis
    for `position_value`.

    Returns a dict summary of the saved row, or None on failure.
    """
    create_tables()
    session = get_session()
    snapshot_date = snapshot_date or _today_est_iso()

    try:
        portfolio = session.query(Portfolio).first()
        cash = float(portfolio.cash_balance) if portfolio else INITIAL_INVESTMENT

        # Realized PnL (cumulative across all closed SELL trades to date).
        realized_total = 0.0
        for trade in (
            session.query(Trade)
            .filter(Trade.trade_type == "SELL", Trade.pnl.isnot(None))
            .all()
        ):
            try:
                realized_total += float(trade.pnl or 0.0)
            except (TypeError, ValueError):
                continue

        # Open positions: try live mark, fall back to cost basis.
        position_value = 0.0
        unrealized = 0.0
        active = session.query(Position).filter_by(is_active=True).all()
        for pos in active:
            cost_basis = float(pos.quantity) * float(pos.average_cost)
            mark = None
            if get_current_price is not None:
                try:
                    mark = get_current_price(pos.symbol)
                except Exception as e:
                    logger.warning(f"Snapshot price fetch failed for {pos.symbol}: {e}")
                    mark = None
            if mark is not None:
                pv = float(pos.quantity) * float(mark)
                position_value += pv
                unrealized += pv - cost_basis
            else:
                position_value += cost_basis  # neutral mark

        total_value = cash + position_value

        existing = (
            session.query(EquitySnapshot)
            .filter_by(snapshot_date=snapshot_date)
            .first()
        )
        now_utc = datetime.utcnow()
        if existing:
            existing.captured_at = now_utc
            existing.cash_balance = cash
            existing.position_value = position_value
            existing.total_value = total_value
            existing.realized_pnl_cum = realized_total
            existing.unrealized_pnl = unrealized
            existing.n_open_positions = len(active)
            existing.source = 'live'
            row = existing
        else:
            row = EquitySnapshot(
                snapshot_date=snapshot_date,
                captured_at=now_utc,
                cash_balance=cash,
                position_value=position_value,
                total_value=total_value,
                realized_pnl_cum=realized_total,
                unrealized_pnl=unrealized,
                n_open_positions=len(active),
                source='live',
            )
            session.add(row)
        session.commit()
        logger.info(
            f"Equity snapshot {snapshot_date}: total ${total_value:.2f} "
            f"(cash ${cash:.2f}, positions ${position_value:.2f}, "
            f"realized ${realized_total:.2f}, unrealized ${unrealized:.2f})"
        )
        return {
            "snapshot_date": snapshot_date,
            "cash_balance": cash,
            "position_value": position_value,
            "total_value": total_value,
            "realized_pnl_cum": realized_total,
            "unrealized_pnl": unrealized,
            "n_open_positions": len(active),
        }
    except Exception as e:
        session.rollback()
        logger.error(f"take_equity_snapshot failed: {e}")
        return None
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Backfill from historical trades (read-only derivation, also writes)
# ---------------------------------------------------------------------------


def backfill_snapshots_from_trades() -> int:
    """If `equity_snapshots` is empty, derive a best-effort historical
    series from existing closed `Trade` rows.

    For every distinct trade date we walk SELL trades in chronological
    order, accumulate realized PnL, and write a snapshot row marked
    `source='backfill'`.  This won't include intraday unrealized swings
    (we never recorded them), but it gives the equity-curve chart a
    meaningful day-zero shape so it's not empty when the page first
    loads.

    Returns the number of snapshots written.  Returns 0 if snapshots
    already exist (we never overwrite live snapshots) or no trades
    are available.
    """
    create_tables()
    session = get_session()
    try:
        if session.query(EquitySnapshot).count() > 0:
            return 0

        # Only closed SELL trades realize PnL; BUYs are neutral cash <-> position
        # rebalances and must not contribute to the cumulative realized curve.
        trades = (
            session.query(Trade)
            .filter(Trade.trade_type == "SELL", Trade.timestamp.isnot(None))
            .order_by(Trade.timestamp.asc())
            .all()
        )
        if not trades:
            return 0

        # Group trades by US/Eastern calendar date and roll cumulative PnL.
        by_date: dict[str, float] = {}
        cum = 0.0
        for t in trades:
            try:
                ts = t.timestamp
                if ts.tzinfo is None:
                    ts = pytz.UTC.localize(ts)
                d = ts.astimezone(EST).strftime("%Y-%m-%d")
            except Exception:
                continue
            try:
                cum += float(t.pnl or 0.0)
            except (TypeError, ValueError):
                pass
            by_date[d] = cum  # last-write-wins per day == EOD cumulative

        if not by_date:
            return 0

        now_utc = datetime.utcnow()
        written = 0
        for d, cum_pnl in sorted(by_date.items()):
            row = EquitySnapshot(
                snapshot_date=d,
                captured_at=now_utc,
                cash_balance=INITIAL_INVESTMENT + cum_pnl,
                position_value=0.0,  # unknown historically
                total_value=INITIAL_INVESTMENT + cum_pnl,
                realized_pnl_cum=cum_pnl,
                unrealized_pnl=0.0,
                n_open_positions=0,
                source='backfill',
            )
            session.add(row)
            written += 1
        session.commit()
        logger.info(f"Backfilled {written} equity snapshots from trade history")
        return written
    except Exception as e:
        session.rollback()
        logger.error(f"backfill_snapshots_from_trades failed: {e}")
        return 0
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Read-side helpers
# ---------------------------------------------------------------------------


def get_equity_series() -> list[dict]:
    """Return the full equity snapshot series, oldest first."""
    create_tables()
    session = get_session()
    try:
        rows = (
            session.query(EquitySnapshot)
            .order_by(EquitySnapshot.snapshot_date.asc())
            .all()
        )
        return [
            {
                "date": r.snapshot_date,
                "total_value": float(r.total_value or 0.0),
                "cash_balance": float(r.cash_balance or 0.0),
                "position_value": float(r.position_value or 0.0),
                "realized_pnl_cum": float(r.realized_pnl_cum or 0.0),
                "unrealized_pnl": float(r.unrealized_pnl or 0.0),
                "n_open_positions": int(r.n_open_positions or 0),
                "source": r.source or "live",
            }
            for r in rows
        ]
    finally:
        session.close()


def get_closed_trade_history() -> list[dict]:
    """Return all closed (SELL) trades chronologically with running cumulative PnL."""
    create_tables()
    session = get_session()
    try:
        trades = (
            session.query(Trade)
            .filter(Trade.trade_type == "SELL")
            .order_by(Trade.timestamp.asc())
            .all()
        )
        result = []
        cum = 0.0
        for t in trades:
            try:
                pnl = float(t.pnl or 0.0)
            except (TypeError, ValueError):
                pnl = 0.0
            cum += pnl

            entry_price = None
            hold_days = None
            if t.position_id:
                pos = session.query(Position).filter_by(id=t.position_id).first()
                if pos:
                    entry_price = float(pos.entry_price) if pos.entry_price else None
                    if pos.entry_time and t.timestamp:
                        try:
                            delta = t.timestamp - pos.entry_time
                            hold_days = round(delta.total_seconds() / 86400.0, 2)
                        except Exception:
                            hold_days = None

            pnl_pct = None
            if entry_price and entry_price > 0:
                try:
                    pnl_pct = (float(t.price) / entry_price - 1.0) * 100.0
                except (TypeError, ValueError, ZeroDivisionError):
                    pnl_pct = None

            ts = t.timestamp
            try:
                if ts and ts.tzinfo is None:
                    ts = pytz.UTC.localize(ts)
                ts_iso = ts.astimezone(EST).isoformat() if ts else None
            except Exception:
                ts_iso = ts.isoformat() if ts else None

            result.append({
                "timestamp": ts_iso,
                "symbol": t.symbol,
                "trade_type": t.trade_type,
                "quantity": float(t.quantity or 0.0),
                "entry_price": entry_price,
                "exit_price": float(t.price or 0.0),
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "cumulative_pnl": cum,
                "reason": t.reason or "",
                "hold_days": hold_days,
            })
        return result
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Pure stats computations
# ---------------------------------------------------------------------------


def _max_drawdown_pct(values: list[float]) -> float:
    """Worst peak-to-trough drawdown of a value series, expressed as a
    percentage of the running peak.  Returns a negative number (or 0)."""
    if not values:
        return 0.0
    peak = values[0]
    worst = 0.0
    for v in values:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (v - peak) / peak * 100.0
            if dd < worst:
                worst = dd
    return round(worst, 2)


def _streaks(signs: list[int]) -> tuple[int, int]:
    """Return (longest_positive_run, longest_negative_run)."""
    longest_pos = longest_neg = cur_pos = cur_neg = 0
    for s in signs:
        if s > 0:
            cur_pos += 1
            cur_neg = 0
            if cur_pos > longest_pos:
                longest_pos = cur_pos
        elif s < 0:
            cur_neg += 1
            cur_pos = 0
            if cur_neg > longest_neg:
                longest_neg = cur_neg
        else:
            cur_pos = cur_neg = 0
    return longest_pos, longest_neg


def compute_strategy_stats(
    closed_trades: list[dict],
    equity_series: list[dict],
    initial_investment: float = INITIAL_INVESTMENT,
) -> dict:
    """Compute the headline KPIs surfaced on the Portfolio page.

    All inputs are plain dicts (see `get_closed_trade_history` and
    `get_equity_series`), so this function is fully testable without
    a database.
    """
    n_trades = len(closed_trades)

    if equity_series:
        latest = equity_series[-1]
        current_total = float(latest["total_value"])
    else:
        current_total = initial_investment

    total_pnl = current_total - initial_investment
    total_return_pct = (total_pnl / initial_investment * 100.0) if initial_investment else 0.0

    realized_pnl_cum = (
        float(equity_series[-1]["realized_pnl_cum"]) if equity_series
        else sum(float(t.get("pnl") or 0.0) for t in closed_trades)
    )

    # Drawdown: prefer the equity series; fall back to a synthetic
    # "initial + cumulative realized PnL" series from the trades so the
    # stat isn't blank before the first daily snapshot has run.
    if equity_series:
        eq_values = [float(r["total_value"]) for r in equity_series]
    else:
        eq_values = [initial_investment]
        running = initial_investment
        for t in closed_trades:
            running += float(t.get("pnl") or 0.0)
            eq_values.append(running)
    max_dd_pct = _max_drawdown_pct(eq_values)

    if not closed_trades:
        return {
            "n_trades": 0,
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "realized_pnl_cum": round(realized_pnl_cum, 2),
            "max_drawdown_pct": max_dd_pct,
            "win_rate_pct": None,
            "avg_win": None,
            "avg_loss": None,
            "expectancy": None,
            "profit_factor": None,
            "longest_win_streak": 0,
            "longest_loss_streak": 0,
            "best_trade": None,
            "worst_trade": None,
            "avg_hold_days": None,
            "current_total_value": round(current_total, 2),
        }

    pnls = [float(t.get("pnl") or 0.0) for t in closed_trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    win_rate = (len(wins) / len(pnls) * 100.0) if pnls else None
    avg_win = (sum(wins) / len(wins)) if wins else None
    avg_loss = (sum(losses) / len(losses)) if losses else None
    expectancy = (sum(pnls) / len(pnls)) if pnls else None
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

    signs = [1 if p > 0 else (-1 if p < 0 else 0) for p in pnls]
    longest_win_streak, longest_loss_streak = _streaks(signs)

    best_idx = max(range(len(pnls)), key=lambda i: pnls[i])
    worst_idx = min(range(len(pnls)), key=lambda i: pnls[i])

    holds = [
        float(t.get("hold_days"))
        for t in closed_trades
        if t.get("hold_days") is not None
    ]
    avg_hold_days = (sum(holds) / len(holds)) if holds else None

    return {
        "n_trades": n_trades,
        "total_pnl": round(total_pnl, 2),
        "total_return_pct": round(total_return_pct, 2),
        "realized_pnl_cum": round(realized_pnl_cum, 2),
        "max_drawdown_pct": max_dd_pct,
        "win_rate_pct": round(win_rate, 1) if win_rate is not None else None,
        "avg_win": round(avg_win, 2) if avg_win is not None else None,
        "avg_loss": round(avg_loss, 2) if avg_loss is not None else None,
        "expectancy": round(expectancy, 2) if expectancy is not None else None,
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "longest_win_streak": longest_win_streak,
        "longest_loss_streak": longest_loss_streak,
        "best_trade": {
            "symbol": closed_trades[best_idx].get("symbol"),
            "pnl": round(pnls[best_idx], 2),
            "pnl_pct": closed_trades[best_idx].get("pnl_pct"),
            "timestamp": closed_trades[best_idx].get("timestamp"),
        },
        "worst_trade": {
            "symbol": closed_trades[worst_idx].get("symbol"),
            "pnl": round(pnls[worst_idx], 2),
            "pnl_pct": closed_trades[worst_idx].get("pnl_pct"),
            "timestamp": closed_trades[worst_idx].get("timestamp"),
        },
        "avg_hold_days": round(avg_hold_days, 2) if avg_hold_days is not None else None,
        "current_total_value": round(current_total, 2),
    }
