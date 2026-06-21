#!/usr/bin/env python3
"""Tiny parser used by the council post-commit hook + hermes shift.
Reads the JSON output of external_council_voice.py from stdin,
emits three lines: majority, proposal_id, count-summary.
Falling out to "?" on any error keeps the shell pipeline simple."""
import json, sys

try:
    d = json.loads(sys.stdin.read())
    print(d.get("external_majority", "?"))
    print(d.get("proposal_id", "?"))
    print(
        "a={} r={} x={}".format(
            d.get("approve_count", 0),
            d.get("reject_count", 0),
            d.get("abstain_count", 0),
        )
    )
except Exception:
    print("?")
    print("?")
    print("?")
