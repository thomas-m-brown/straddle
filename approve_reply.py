#!/usr/bin/env python3
"""
Approve, edit, skip, or list pending job email replies.

Usage:
  approve_reply.py list
  approve_reply.py show <id>
  approve_reply.py send <id>
  approve_reply.py skip <id>
  approve_reply.py edit <id> 'new reply text'
"""

import os
import sys
import json
import smtplib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from email.mime.text import MIMEText
from dotenv import load_dotenv

BASE_DIR    = Path(__file__).parent
PENDING_DIR = BASE_DIR / "pending_replies"
HERMES_BIN  = "/home/thomasb/.local/bin/hermes"
EXPIRY_DAYS = 7

load_dotenv(BASE_DIR / ".env")

ICLOUD_ACC = {
    "email":     os.environ.get("ICLOUD_EMAIL", ""),
    "password":  os.environ.get("ICLOUD_PASS", ""),
    "smtp_host": "smtp.mail.me.com",
    "smtp_port": 587,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load(reply_id: str) -> dict:
    path = PENDING_DIR / f"{reply_id}.json"
    if not path.exists():
        print(f"No pending reply: {reply_id}")
        sys.exit(1)
    return json.loads(path.read_text())

def _save(record: dict):
    (PENDING_DIR / f"{record['id']}.json").write_text(json.dumps(record, indent=2))

def _age_days(record: dict) -> float:
    created = datetime.fromisoformat(record["created_at"])
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - created).total_seconds() / 86400

def _notify(text: str):
    try:
        subprocess.run(
            [HERMES_BIN, "send", "telegram", text],
            check=True, capture_output=True, timeout=30,
            env={**os.environ, "HERMES_HOME": str(Path.home() / ".hermes")},
        )
    except Exception:
        pass

def _expire_stale():
    """Auto-skip pending replies older than EXPIRY_DAYS. Called on list."""
    for f in PENDING_DIR.glob("*.json"):
        r = json.loads(f.read_text())
        if r["status"] == "pending" and _age_days(r) >= EXPIRY_DAYS:
            r["status"] = "skipped"
            r["skip_reason"] = "expired"
            _save(r)
            _notify(
                f"⏰ Job reply [{r['id']}] auto-skipped (>{EXPIRY_DAYS} days old)\n"
                f"Subject: {r['subject']}"
            )
            print(f"[{r['id']}] auto-skipped (expired)")

def _send_smtp(record: dict, body: str):
    acc = ICLOUD_ACC
    if not acc["password"]:
        print("iCloud SMTP password not set in .env")
        sys.exit(1)
    msg = MIMEText(body)
    msg["Subject"] = f"Re: {record['subject']}"
    msg["From"]    = f"Thomas Brown <{acc['email']}>"
    msg["To"]      = record["reply_to"]
    with smtplib.SMTP(acc["smtp_host"], acc["smtp_port"]) as smtp:
        smtp.starttls()
        smtp.login(acc["email"], acc["password"])
        smtp.send_message(msg)

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_list():
    _expire_stale()
    files = sorted(PENDING_DIR.glob("*.json"))
    if not files:
        print("No pending replies.")
        return
    print(f"{'ID':<10} {'Status':<10} {'Tone':<12} {'Age':>5}d  Subject")
    print("─" * 72)
    for f in files:
        r = json.loads(f.read_text())
        age = f"{_age_days(r):.1f}"
        print(f"{r['id']:<10} {r['status']:<10} {r.get('tone','?'):<12} {age:>5}  {r['subject'][:38]}")

def cmd_show(reply_id: str):
    r = _load(reply_id)
    print(f"ID:      {r['id']}")
    print(f"Status:  {r['status']}")
    print(f"Tone:    {r.get('tone', '?')}")
    print(f"Account: {r['account']}")
    print(f"From:    {r['from']}")
    print(f"To:      {r['reply_to']}")
    print(f"Subject: {r['subject']}")
    print(f"Date:    {r['date']}")
    print(f"Age:     {_age_days(r):.1f} days")
    print()
    print("── DRAFT ──")
    print(r["draft"])
    print("──────────")

def cmd_send(reply_id: str):
    r = _load(reply_id)
    if r["status"] != "pending":
        print(f"Reply {reply_id} already {r['status']}.")
        return
    _send_smtp(r, r["draft"])
    r["status"] = "sent"
    r["sent_at"] = datetime.now().isoformat()
    _save(r)
    _notify(
        f"✅ Job reply sent [{reply_id}]\n"
        f"To: {r['reply_to']}\n"
        f"Subject: Re: {r['subject']}"
    )
    print(f"Sent and marked: {reply_id}")

def cmd_skip(reply_id: str):
    r = _load(reply_id)
    if r["status"] != "pending":
        print(f"Reply {reply_id} already {r['status']}.")
        return
    r["status"] = "skipped"
    _save(r)
    print(f"Skipped: {reply_id}")

def cmd_edit(reply_id: str, new_body: str):
    r = _load(reply_id)
    if r["status"] != "pending":
        print(f"Reply {reply_id} already {r['status']}. Cannot edit.")
        return
    r["draft"] = new_body
    _save(r)
    print(f"Draft updated. Run: approve_reply.py send {reply_id}")

# ── Entry ─────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args or args[0] == "list":
        cmd_list()
    elif args[0] == "show" and len(args) == 2:
        cmd_show(args[1])
    elif args[0] == "send" and len(args) == 2:
        cmd_send(args[1])
    elif args[0] == "skip" and len(args) == 2:
        cmd_skip(args[1])
    elif args[0] == "edit" and len(args) >= 3:
        cmd_edit(args[1], " ".join(args[2:]))
    else:
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
