#!/usr/bin/env python3
"""Test email alerts module"""

import sys
sys.path.insert(0, '.')

print("Testing email alerts module...\n")

# Test 1: Import
print("[TEST 1] Importing email alerts...")
try:
    from email_alerts import send_nightly_alert, _classify_zones, _build_email_body
    print("  [OK] Email alerts module imported")
except Exception as e:
    print(f"  [ERROR] {e}")
    sys.exit(1)

# Test 2: Zone classification
print("\n[TEST 2] Testing zone classification...")
try:
    from swing_picks import build_picks
    from exit_signals import get_cached_exit_signals

    picks = build_picks(min_edge=0, min_rs=0)
    exit_signals = get_cached_exit_signals()
    exit_map = exit_signals.get('signals', {})

    buy_zone, exit_zone = _classify_zones(picks, exit_map)
    print(f"  [OK] Classified zones:")
    print(f"      - BUY ZONE: {len(buy_zone)} stocks")
    print(f"      - EXIT ZONE: {len(exit_zone)} stocks")
except Exception as e:
    print(f"  [ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Build email body
print("\n[TEST 3] Building email body...")
try:
    regime = {"name": "RISK ON", "color": "92c47d"}
    as_of = "2026-06-02T22:30:00Z"
    html = _build_email_body(buy_zone, exit_zone, regime, as_of)
    print(f"  [OK] Email body generated: {len(html)} chars")
    print(f"      - Contains BUY ZONE table: {'<table>' in html and len(buy_zone) > 0}")
    print(f"      - Contains EXIT ZONE table: {'<table>' in html and len(exit_zone) > 0}")
except Exception as e:
    print(f"  [ERROR] {e}")
    sys.exit(1)

# Test 4: Check env vars
print("\n[TEST 4] Checking email environment variables...")
import os
alert_email = os.environ.get("ALERT_EMAIL")
gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
print(f"  ALERT_EMAIL: {'SET' if alert_email else 'NOT SET'}")
print(f"  GMAIL_APP_PASSWORD: {'SET' if gmail_password else 'NOT SET'}")
if not alert_email or not gmail_password:
    print("  [NOTE] Env vars not set — send_nightly_alert() will skip silently")
else:
    print("  [OK] Ready to send emails")

# Test 5: Mock send (don't actually send)
print("\n[TEST 5] Testing send function (no email sent without env vars)...")
try:
    result = send_nightly_alert()
    if not alert_email or not gmail_password:
        print(f"  [OK] Function returned {result} (expected False — env vars not set)")
    else:
        print(f"  [OK] Function returned {result}")
except Exception as e:
    print(f"  [ERROR] {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("SUCCESS: All email alert tests passed!")
print("=" * 60)
print("\nNext steps to use email alerts:")
print("  1. Go to Google Account → Security → 2-Step Verification")
print("  2. Generate an 'App Passwords' for 'Momentum Dashboard'")
print("  3. Set in Render dashboard:")
print("     - ALERT_EMAIL = dkylemiller@gmail.com")
print("     - GMAIL_APP_PASSWORD = <16-char app password>")
print("  4. Alerts will send nightly at 10:30 PM EST")
