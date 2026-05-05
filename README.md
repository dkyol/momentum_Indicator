# Momentum Indicator Dashboard

A personal stock investing dashboard that tracks relative volume, alpha signals, setup patterns, and portfolio equity. Built with Flask + PostgreSQL, deployed on Render with data refreshed by GitHub Actions cron jobs.

## Architecture

```
GitHub Actions (cron jobs)
  └─ scripts/refresh_rvol.py       every 15 min during market hours
  └─ scripts/refresh_alpha.py      daily post-open + nightly with backtest
  └─ scripts/equity_snapshot.py    end-of-day portfolio snapshot
         │
         ▼
   Neon (PostgreSQL)
         │
         ▼
   Render (Flask web service)
   → Dashboard UI served at your Render URL
```

## Cron schedule (all times UTC)

| Job | Schedule | Command | What it does |
|---|---|---|---|
| RVOL refresh | `*/15 13-21 * * 1-5` | `refresh_rvol.py` | Intraday relative volume vs. 20-day baseline |
| Alpha daily | `5 14 * * 1-5` | `refresh_alpha.py` | Fundamentals, value screen, RS, setups, regime, catalysts, edge score |
| Alpha nightly | `30 3 * * 2-7` | `refresh_alpha.py --with-backtest` | Full pipeline + 3-year signal backtest |
| Equity snapshot | `10 21 * * 1-5` | `equity_snapshot.py` | EOD portfolio equity curve capture |

Manual runs: GitHub → Actions → Scheduled Refresh → Run workflow → pick a job.

## Setup

### 1. Neon (database)

1. Create a project at [neon.tech](https://neon.tech)
2. Copy the **pooled** connection string — it looks like `postgresql://user:pass@host/db?sslmode=require`
3. Schema is auto-created on first cron run via `models.create_tables()`

### 2. GitHub secrets

In repo Settings → Secrets and variables → Actions:

| Secret | Value |
|---|---|
| `DATABASE_URL` | Neon pooled connection string |
| `FAILURE_WEBHOOK_URL` | *(optional)* Slack/Discord webhook URL for failure pings |

### 3. Render (web service)

1. Connect the repo in the Render dashboard — it will detect `render.yaml` automatically
2. Set the `DATABASE_URL` environment variable to the same Neon connection string
3. Deploy; the service auto-deploys on every push to `main`

> **Free tier note:** Render spins down after 15 min of inactivity. First request after sleep takes ~30-60s. Use [UptimeRobot](https://uptimerobot.com) with a 14-min ping interval to keep it warm if needed.

## Local development

```bash
# Install deps
uv sync

# Run the Flask dev server
DATABASE_URL=<your_neon_url> flask --app main run --debug

# Run a refresh script manually
DATABASE_URL=<your_neon_url> python scripts/refresh_alpha.py
DATABASE_URL=<your_neon_url> python scripts/refresh_rvol.py
DATABASE_URL=<your_neon_url> python scripts/equity_snapshot.py
```

If `DATABASE_URL` is unset, the app falls back to local JSON caches (useful for quick offline inspection).

## Key modules

| File | Purpose |
|---|---|
| `app.py` | Flask routes and dashboard UI |
| `alpha_engine.py` | Orchestrates the full alpha pipeline |
| `rvol.py` | Intraday relative volume computation |
| `backtester.py` | 3-year signal replay (10-day holding periods) |
| `portfolio_stats.py` | Equity curve, drawdown, and trade analytics |
| `models.py` | SQLAlchemy ORM — `Trade`, `Position`, `Portfolio`, `EquitySnapshot` |
| `edge_score.py` | Composite score (value + RS + setups + catalysts) |

## Updating dependencies

```bash
# Add/remove a package
uv add <package>     # or: uv remove <package>

# Regenerate requirements.txt for Render + GitHub Actions
uv export --no-hashes --format requirements-txt > requirements.txt
```
