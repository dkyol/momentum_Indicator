"""
Email Alert System

Sends a nightly HTML email summarizing the day's BUY and EXIT signals.
Uses Gmail SMTP — no external service dependencies.

Environment variables:
  ALERT_EMAIL: recipient (dkylemiller@gmail.com)
  GMAIL_APP_PASSWORD: 16-char Gmail App Password from Google Account → Security → 2-Step Verification → App Passwords
  (optional) ALERT_FROM_EMAIL: sender (defaults to ALERT_EMAIL)
"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from exit_signals import get_cached_exit_signals
from swing_picks import build_picks
from watchlist_scanner import get_cached_watchlist_scan

logger = logging.getLogger(__name__)


def _classify_zones(picks: list[dict], exit_map: dict) -> tuple[list[dict], list[dict]]:
    """
    Classify picks into BUY ZONE and EXIT ZONE.

    BUY ZONE: has active Setups + Edge_Score > 50 + RSI_14 < 55
    EXIT ZONE: exit_signal != "HOLD"
    """
    buy_zone = [
        r for r in picks
        if r.get("Setups")
        and (r.get("Edge_Score") or 0) > 50
        and (r.get("RSI_14") is None or r.get("RSI_14") < 55)
    ]

    exit_zone_symbols = {sym for sym, sig in exit_map.items() if sig.get("exit_signal") != "HOLD"}

    pick_map = {r["Symbol"]: r for r in picks}
    exit_zone = []
    for sym in sorted(exit_zone_symbols):
        sig = exit_map[sym]
        pick_row = pick_map.get(sym, {})
        if pick_row:
            row = dict(pick_row)
        else:
            row = {"Symbol": sym}
        row["Exit_Signal"] = sig.get("exit_signal")
        row["Exit_Reason"] = sig.get("exit_reason")
        row["Distance_To_Target_Pct"] = sig.get("distance_to_target_pct")
        row["Distance_To_Stop_Pct"] = sig.get("distance_to_stop_pct")
        exit_zone.append(row)
    exit_zone.sort(key=lambda r: (r.get("Edge_Score") or 0), reverse=True)

    return buy_zone, exit_zone


def _build_email_body(
    buy_zone: list[dict],
    exit_zone: list[dict],
    regime: dict | None,
    as_of: str | None,
    account_size: float = 10000,
    watchlist_candidates: list[dict] | None = None,
) -> str:
    """Build HTML email body with tables for BUY, BREAKOUT WATCH, and EXIT zones."""

    now = datetime.now().strftime("%a %b %d")
    regime_name = (regime.get("name") or "UNKNOWN") if regime else "UNKNOWN"
    regime_color = (regime.get("color") or "secondary") if regime else "secondary"

    # Empty zones case
    if not buy_zone and not exit_zone and not watchlist_candidates:
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #666;">No Actionable Signals Tonight</h2>
            <p>Market regime: <span style="background: #{regime_color}; padding: 4px 8px; border-radius: 4px; color: white;">{regime_name}</span></p>
            <p>Check back tomorrow for trading opportunities.</p>
            <p style="font-size: 11px; color: #999;">Sent {now}</p>
        </body>
        </html>
        """

    watchlist_count = len(watchlist_candidates) if watchlist_candidates else 0
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.5; }}
            h1 {{ color: #222; margin-bottom: 5px; }}
            .header {{ margin-bottom: 20px; }}
            .regime-badge {{ background: #{regime_color}; color: white; padding: 4px 8px; border-radius: 4px; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th {{ background: #f0f0f0; padding: 8px; text-align: left; border-bottom: 2px solid #ddd; font-weight: bold; }}
            td {{ padding: 8px; border-bottom: 1px solid #eee; }}
            tr.rsi-strong {{ background: #e8f5e9; }} /* RSI < 40 */
            tr.rsi-developing {{ background: #fff3e0; }} /* RSI 40-55 */
            .section-buy {{ background: #c8e6c9; padding: 12px; border-radius: 4px; margin-bottom: 20px; }}
            .section-watchlist {{ background: #fff9c4; padding: 12px; border-radius: 4px; margin-bottom: 20px; }}
            .section-exit {{ background: #ffcdd2; padding: 12px; border-radius: 4px; margin-bottom: 20px; }}
            .section-title {{ font-weight: bold; font-size: 14px; margin-bottom: 10px; }}
            .signal-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 2px; }}
            .dot-strong {{ background: #2e7d32; }} /* green */
            .dot-developing {{ background: #fdd835; }} /* yellow */
            .dot-absent {{ background: #bdbdbd; }} /* gray */
            .badge-sell {{ background: #d32f2f; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
            .badge-trail {{ background: #f57c00; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
            .badge-watch {{ background: #1976d2; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
            .badge-breakout {{ background: #2e7d32; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
            .badge-conviction {{ background: #f57c00; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
            .badge-accum {{ background: #fdd835; color: #333; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #999; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Trade Planner Alert</h1>
            <p>
                <strong>{len(buy_zone)} BUY</strong> | <strong>{watchlist_count} BREAKOUT</strong> | <strong>{len(exit_zone)} EXIT</strong>
                | Market: <span class="regime-badge">{regime_name}</span>
            </p>
            <p style="font-size: 12px; color: #999;">Generated {now}</p>
        </div>
    """

    # BUY ZONE section
    if buy_zone:
        html += f"""
        <div class="section-buy">
            <div class="section-title">BUY ZONE ({len(buy_zone)} stocks)</div>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Setup</th>
                        <th>Close</th>
                        <th>RSI</th>
                        <th>Stop</th>
                        <th>Target</th>
                        <th>R:R</th>
                        <th>Shares</th>
                        <th>Edge</th>
                    </tr>
                </thead>
                <tbody>
        """
        for row in buy_zone:
            rsi = row.get("RSI_14")
            if rsi and rsi < 40:
                tr_class = 'class="rsi-strong"'
            elif rsi and rsi < 55:
                tr_class = 'class="rsi-developing"'
            else:
                tr_class = ""

            html += f"""
                    <tr {tr_class}>
                        <td><strong>{row.get('Symbol', '—')}</strong></td>
                        <td><small>{row.get('Primary_Setup', '—')}</small></td>
                        <td>${row.get('Close', 0):.2f}</td>
                        <td>{f"{rsi:.0f}" if rsi else "—"}</td>
                        <td>${row.get('Stop_Level', 0):.2f}</td>
                        <td>${row.get('Target_Price', 0):.2f}</td>
                        <td>{row.get('RR_Ratio', '—')}</td>
                        <td>{row.get('Shares', '—')} shares</td>
                        <td>{row.get('Edge_Score', '—')}</td>
                    </tr>
            """
        html += """
                </tbody>
            </table>
            <small style="color: #666;">Based on ${:,.0f} account at 1% risk per trade</small>
        </div>
        """.format(account_size)

    # BREAKOUT WATCH section (watchlist top candidates)
    if watchlist_candidates:
        html += f"""
        <div class="section-watchlist">
            <div class="section-title">BREAKOUT WATCH ({len(watchlist_candidates)} stocks monitoring)</div>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Score</th>
                        <th>Signals</th>
                        <th>Recommendation</th>
                        <th>Close</th>
                        <th>RSI</th>
                    </tr>
                </thead>
                <tbody>
        """
        for row in watchlist_candidates:
            score = row.get("score", 0)
            rec = row.get("recommendation", "WATCH ONLY")
            signals = row.get("signals", {})

            # Badge for recommendation
            if rec == "BREAKOUT BUY":
                badge = '<span class="badge-breakout">BREAKOUT</span>'
            elif rec == "HIGH CONVICTION":
                badge = '<span class="badge-conviction">CONVICTION</span>'
            elif rec == "ACCUMULATING":
                badge = '<span class="badge-accum">ACCUMULATING</span>'
            else:
                badge = '<span class="badge-watch">WATCH</span>'

            # Signal indicator dots
            signal_html = ""
            for signal_name in ["rvol", "obv", "mfi", "adx", "ad_line"]:
                signal_status = signals.get(signal_name, False)
                if signal_status == "strong":
                    dot_class = "dot-strong"
                elif signal_status == "developing":
                    dot_class = "dot-developing"
                else:
                    dot_class = "dot-absent"
                signal_html += f'<span class="signal-dot {dot_class}" title="{signal_name}"></span>'

            rsi = row.get("rsi")
            html += f"""
                    <tr>
                        <td><strong>{row.get('symbol', '—')}</strong></td>
                        <td>{score:.1f}/5.0</td>
                        <td>{signal_html}</td>
                        <td>{badge}</td>
                        <td>${row.get('close', 0):.2f}</td>
                        <td>{f"{rsi:.0f}" if rsi else "—"}</td>
                    </tr>
            """
        html += """
                </tbody>
            </table>
            <small style="color: #666;">Green = strong signal | Yellow = developing | Gray = absent</small>
        </div>
        """

    # EXIT ZONE section
    if exit_zone:
        html += f"""
        <div class="section-exit">
            <div class="section-title">EXIT ZONE ({len(exit_zone)} stocks)</div>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Signal</th>
                        <th>Reason</th>
                        <th>Close</th>
                        <th>Recommendation</th>
                        <th>Edge</th>
                    </tr>
                </thead>
                <tbody>
        """
        for row in exit_zone:
            signal = row.get("Exit_Signal", "HOLD")
            if signal in ("TAKE_PROFIT", "OVERBOUGHT"):
                badge = '<span class="badge-sell">SELL</span>'
            elif signal == "STOP_THREATENED":
                badge = '<span class="badge-trail">TRAIL</span>'
            elif signal == "TREND_BROKEN":
                badge = '<span class="badge-watch">WATCH</span>'
            else:
                badge = 'HOLD'

            html += f"""
                    <tr>
                        <td><strong>{row.get('Symbol', '—')}</strong></td>
                        <td><strong>{signal}</strong></td>
                        <td><small>{row.get('Exit_Reason', '—')}</small></td>
                        <td>${row.get('Close', 0):.2f}</td>
                        <td>{badge}</td>
                        <td>{row.get('Edge_Score', '—')}</td>
                    </tr>
            """
        html += """
                </tbody>
            </table>
        </div>
        """

    html += """
        <div class="footer">
            <p>
                <a href="https://momentum-indicator.onrender.com/trade-planner" style="color: #1976d2; text-decoration: none;">
                    View full dashboard →
                </a>
            </p>
            <p>This is an automated alert from your Momentum Dashboard.</p>
        </div>
    </body>
    </html>
    """

    return html


def send_nightly_alert() -> bool:
    """
    Send nightly email alert summarizing BUY, BREAKOUT WATCH, and EXIT signals.

    Returns True if email sent, False if skipped (env vars not set) or failed.
    """
    alert_email = os.environ.get("ALERT_EMAIL")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not alert_email or not gmail_app_password:
        logger.info("Alert email skipped: ALERT_EMAIL or GMAIL_APP_PASSWORD not set")
        return False

    try:
        # Build picks and exit signals
        picks = build_picks(min_edge=0, min_rs=0)
        exit_signals = get_cached_exit_signals()
        exit_map = exit_signals.get("signals", {})

        buy_zone, exit_zone = _classify_zones(picks, exit_map)

        # Get watchlist candidates (score >= 2.5 for actionable signals)
        watchlist_scan = get_cached_watchlist_scan()
        watchlist_candidates = [
            s for s in watchlist_scan.get("stocks", [])
            if s.get("score", 0) >= 2.5
        ][:5]  # Top 5 only

        # Get market regime for display
        try:
            from app import _regime_for_template
            regime = _regime_for_template()
        except Exception:
            regime = None

        as_of = exit_signals.get("as_of")

        # Build email
        subject = f"[Trade Planner] {len(buy_zone)} BUY, {len(watchlist_candidates)} BREAKOUT, {len(exit_zone)} EXIT — {datetime.now().strftime('%a %b %d')}"
        html_body = _build_email_body(buy_zone, exit_zone, regime, as_of, watchlist_candidates=watchlist_candidates)

        from_email = os.environ.get("ALERT_FROM_EMAIL", alert_email)

        # Send via Gmail SMTP
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = alert_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(alert_email, gmail_app_password)
            server.sendmail(from_email, alert_email, msg.as_string())

        logger.info(f"Alert email sent to {alert_email}: {len(buy_zone)} BUY, {len(watchlist_candidates)} BREAKOUT, {len(exit_zone)} EXIT")
        return True

    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        return False
