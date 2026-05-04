import os
import logging
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from stock_analytics import get_high_volume_data
from momentum_analyzer import get_momentum_summary
from scheduler import (
    get_cached_high_volume_stocks,
    get_cached_momentum_data,
    get_cached_sma_data,
    get_last_update_info,
    is_data_fresh,
    save_market_data,
)

# Alpha engine imports
from alpha_cache import get_alpha_meta
from alpha_engine import refresh_alpha_data
from edge_score import get_cached_edge_scores
from market_regime import get_cached_market_regime
from relative_strength import get_cached_relative_strength, get_rs_rating_map
from setups import get_cached_setups
from value_screener import get_cached_value_screen
from catalysts import get_cached_catalysts
from backtester import get_cached_backtest
from portfolio_stats import (
    backfill_snapshots_from_trades,
    compute_strategy_stats,
    get_closed_trade_history,
    get_equity_series,
    take_equity_snapshot,
    INITIAL_INVESTMENT,
)

# Import trader after app initialization to avoid circular imports
trader = None

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")


def initialize_cache():
    """Initialize market data cache on startup if not fresh"""
    if not is_data_fresh():
        logging.info("Initializing market data cache on startup...")
        try:
            save_market_data()
        except Exception as e:
            logging.error(f"Failed to initialize cache: {e}")


def initialize_alpha_cache():
    """Bootstrap the alpha engine in a background thread if no cache exists.

    The full pipeline (fundamentals + relative strength + setups +
    regime + catalysts + edge score) takes several minutes for the
    universe, so we never block the web server on it.  The new pages
    show "data being prepared" until the first refresh finishes.
    """
    if os.path.exists("cached_edge_score.json"):
        return
    logging.info("No alpha cache found - bootstrapping in background")

    def _bg():
        try:
            refresh_alpha_data(include_backtest=False)
        except Exception as e:
            logging.error(f"Background alpha bootstrap failed: {e}")

    threading.Thread(target=_bg, daemon=True).start()


# Call initialization
initialize_cache()
initialize_alpha_cache()


# Password for the site - use environment variable for security
SITE_PASSWORD = os.environ.get("SITE_PASSWORD", "Eb10f600!")


def login_required(f):
    """Decorator to require login for protected routes"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def _regime_for_template():
    """Return a regime dict shape suitable for the banner template."""
    r = get_cached_market_regime() or {}
    label_map = {
        "risk_on": ("Risk-On", "success"),
        "neutral": ("Neutral", "warning"),
        "risk_off": ("Risk-Off", "danger"),
    }
    label, css = label_map.get(r.get("regime"), ("Unknown", "secondary"))
    r["label"] = label
    r["css"] = css
    return r


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page for password protection"""
    if request.method == "POST":
        password = request.form.get("password", "").strip()
        if password == SITE_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("index"))
        else:
            flash("Incorrect password. Please try again.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    """Main page with stock prediction interface"""
    try:
        import pytz

        est_tz = pytz.timezone("US/Eastern")

        if is_data_fresh():
            high_volume_stocks = get_cached_high_volume_stocks()
            momentum_data = get_cached_momentum_data()
            sma_data = get_cached_sma_data()
            last_update = get_last_update_info()
            if last_update.get("last_update"):
                try:
                    update_dt = datetime.fromisoformat(last_update["last_update"])
                    if update_dt.tzinfo is None:
                        update_dt = pytz.UTC.localize(update_dt)
                    update_dt_est = update_dt.astimezone(est_tz)
                    current_time = (
                        f"Data queried on {update_dt_est.strftime('%B %d, %Y at %I:%M %p EST')} (cached data)"
                    )
                except Exception as e:
                    logging.error(f"Error parsing timestamp: {e}")
                    current_time = datetime.now(est_tz).strftime(
                        "Data queried on %B %d, %Y at %I:%M %p EST (cached data)"
                    )
            else:
                current_time = datetime.now(est_tz).strftime(
                    "Data queried on %B %d, %Y at %I:%M %p EST (cached data)"
                )
        else:
            logging.info("Cache is stale, fetching fresh data...")
            save_market_data()
            high_volume_stocks = get_cached_high_volume_stocks()
            momentum_data = get_cached_momentum_data()
            sma_data = get_cached_sma_data()
            current_time = datetime.now(est_tz).strftime(
                "Data queried on %B %d, %Y at %I:%M %p EST (fresh data)"
            )

        # Stitch RS rating into the existing momentum table.
        rs_map = get_rs_rating_map()
        for row in momentum_data or []:
            row["RS_Rating"] = rs_map.get(row.get("Symbol"))

        portfolio_summary = None
        try:
            global trader
            if trader is None:
                from paper_trader import trader as global_trader
                trader = global_trader
            portfolio_summary = trader.get_portfolio_summary()
        except Exception as e:
            app.logger.error(f"Error getting portfolio summary: {e}")
            portfolio_summary = None

        return render_template(
            "index.html",
            high_volume_stocks=high_volume_stocks,
            momentum_data=momentum_data,
            sma_data=sma_data,
            portfolio_summary=portfolio_summary,
            query_time=current_time,
            regime=_regime_for_template(),
        )
    except Exception as e:
        app.logger.error(f"Error loading high volume data: {str(e)}")
        return render_template(
            "index.html",
            high_volume_stocks=[],
            momentum_data=[],
            sma_data=[],
            portfolio_summary=None,
            query_time="Data unavailable",
            regime=_regime_for_template(),
        )


# ------------------------------------------------------------------
# Alpha pages
# ------------------------------------------------------------------


@app.route("/opportunities")
@login_required
def opportunities():
    payload = get_cached_edge_scores()
    return render_template(
        "opportunities.html",
        rows=payload.get("top", []),
        all_rows=payload.get("rows", []),
        regime=_regime_for_template(),
        meta=get_alpha_meta(),
    )


@app.route("/value")
@login_required
def value():
    rows = get_cached_value_screen()
    return render_template(
        "value.html",
        rows=rows,
        regime=_regime_for_template(),
        meta=get_alpha_meta(),
    )


@app.route("/setups")
@login_required
def setups():
    rows = get_cached_setups()
    rows = [r for r in rows if r.get("Setup_Count", 0) > 0]
    return render_template(
        "setups.html",
        rows=rows,
        regime=_regime_for_template(),
        meta=get_alpha_meta(),
    )


@app.route("/sectors")
@login_required
def sectors():
    payload = get_cached_relative_strength()
    return render_template(
        "sectors.html",
        rotation=payload.get("rotation", []),
        rows=payload.get("rows", []),
        market_returns=payload.get("market_returns", {}),
        regime=_regime_for_template(),
        meta=get_alpha_meta(),
    )


@app.route("/catalysts")
@login_required
def catalysts_view():
    rows = get_cached_catalysts()
    # Sort: earnings within 14 days first, then insider buying.
    rows.sort(
        key=lambda r: (
            -1 if r.get("earnings_within_14d") else 0,
            -1 if r.get("insider_buying_30d_plus") else 0,
            r.get("days_to_earnings") if r.get("days_to_earnings") is not None else 9999,
        )
    )
    return render_template(
        "catalysts.html",
        rows=rows,
        regime=_regime_for_template(),
        meta=get_alpha_meta(),
    )


@app.route("/backtest")
@login_required
def backtest():
    payload = get_cached_backtest()
    return render_template(
        "backtest.html",
        results=payload.get("results", []),
        holding_days=payload.get("holding_days"),
        lookback=payload.get("lookback"),
        universe_size=payload.get("universe_size"),
        regime=_regime_for_template(),
        meta=get_alpha_meta(),
    )


@app.route("/portfolio")
@login_required
def portfolio():
    """Portfolio performance dashboard - cumulative effect of running the strategy.

    Pulls active positions via the existing trader summary, builds the
    equity-snapshot series (backfilling from trade history on first load
    so the chart isn't blank), and computes the headline KPIs.
    """
    portfolio_summary = None
    try:
        global trader
        if trader is None:
            from paper_trader import trader as global_trader
            trader = global_trader
        portfolio_summary = trader.get_portfolio_summary()
    except Exception as e:
        app.logger.error(f"Error getting portfolio summary for /portfolio: {e}")
        portfolio_summary = None

    try:
        backfill_snapshots_from_trades()
    except Exception as e:
        app.logger.error(f"Equity backfill failed: {e}")

    try:
        equity_series = get_equity_series()
    except Exception as e:
        app.logger.error(f"get_equity_series failed: {e}")
        equity_series = []

    try:
        closed_trades = get_closed_trade_history()
    except Exception as e:
        app.logger.error(f"get_closed_trade_history failed: {e}")
        closed_trades = []

    # If we have an open trader summary today, merge today's live total
    # into the equity series so the chart's last point is fresh, even if
    # the daily snapshot job hasn't fired yet.
    if portfolio_summary and portfolio_summary.get("total_value") is not None:
        try:
            import pytz as _pytz
            today_iso = datetime.now(_pytz.timezone("US/Eastern")).strftime("%Y-%m-%d")
            live_row = {
                "date": today_iso,
                "total_value": float(portfolio_summary.get("total_value") or 0.0),
                "cash_balance": float(portfolio_summary.get("cash_balance") or 0.0),
                "position_value": float(portfolio_summary.get("position_value") or 0.0),
                "realized_pnl_cum": (
                    equity_series[-1]["realized_pnl_cum"] if equity_series else 0.0
                ),
                "unrealized_pnl": sum(
                    (p.get("pnl") or 0.0) for p in (portfolio_summary.get("positions") or [])
                ),
                "n_open_positions": len(portfolio_summary.get("positions") or []),
                "source": "live",
            }
            if equity_series and equity_series[-1]["date"] == today_iso:
                equity_series[-1] = live_row
            else:
                equity_series.append(live_row)
        except Exception as e:
            app.logger.error(f"Live equity merge failed: {e}")

    try:
        stats = compute_strategy_stats(closed_trades, equity_series)
    except Exception as e:
        app.logger.error(f"compute_strategy_stats failed: {e}")
        stats = compute_strategy_stats([], [])

    return render_template(
        "portfolio.html",
        portfolio_summary=portfolio_summary,
        equity_series=equity_series,
        closed_trades=closed_trades,
        closed_trades_reversed=list(reversed(closed_trades)),
        stats=stats,
        initial_investment=INITIAL_INVESTMENT,
        last_snapshot_date=(equity_series[-1]["date"] if equity_series else None),
        has_backfill=any(r.get("source") == "backfill" for r in equity_series),
        strategy_label="Momentum top-2 (paper)",
        regime=_regime_for_template(),
    )


@app.route("/refresh_alpha", methods=["POST"])
@login_required
def refresh_alpha():
    """Kick off a full alpha refresh in the background.

    Runs in a daemon thread so the request returns instantly; the
    dashboard pages will pick up the new cache files on the next
    page load.  ``include_backtest`` is opt-in because the backtester
    is the slowest step.
    """
    include_backtest = (
        request.form.get("include_backtest") == "1"
        or request.args.get("include_backtest") == "1"
    )

    # Cheap pre-check: if the refresh lock is currently held, surface
    # that to the UI immediately rather than firing a thread that will
    # silently no-op.  This is racy (the lock can be released between
    # the check and the thread start) but in that case the worker just
    # runs normally; we never falsely report "skipped" without reason.
    from alpha_cache import refresh_lock
    if refresh_lock.locked():
        return jsonify({
            "started": False,
            "skipped": "another refresh in progress",
            "include_backtest": include_backtest,
        })

    def _run():
        try:
            refresh_alpha_data(include_backtest=include_backtest)
        except Exception as e:
            app.logger.error(f"Alpha refresh failed: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"started": True, "include_backtest": include_backtest})


@app.route("/trigger_monitoring", methods=["POST"])
def trigger_monitoring():
    try:
        global trader
        if trader is None:
            from paper_trader import trader as global_trader
            trader = global_trader

        trader.monitoring_cycle()
        portfolio_summary = trader.get_portfolio_summary()

        return jsonify(
            {
                "success": True,
                "last_updated": (
                    portfolio_summary["last_updated"].strftime("%I:%M %p EST")
                    if portfolio_summary.get("last_updated")
                    else None
                ),
                "total_value": portfolio_summary.get("total_value", 0),
                "total_pnl": portfolio_summary.get("total_pnl", 0),
                "message": "Portfolio monitoring completed",
            }
        )
    except Exception as e:
        app.logger.error(f"Error in monitoring trigger: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return render_template("index.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("index.html"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
