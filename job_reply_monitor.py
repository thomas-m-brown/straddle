#!/usr/bin/env python3
"""
Job application email monitor.

Polls iCloud INBOX for unseen emails, confirms each is a reply to something
Thomas sent (Sent-folder domain check), classifies tone, drafts a reply via
local LLM, saves to pending_replies/, and notifies via Telegram.

Run via systemd timer (every 15 min). Safe to run repeatedly.
"""

import os
import sys
import json
import hashlib
import imaplib
import email
import requests
import subprocess
from datetime import datetime
from pathlib import Path
from email.header import decode_header as _dh
from dotenv import load_dotenv

# ── Paths & env ───────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
PENDING_DIR  = BASE_DIR / "pending_replies"
SEEN_FILE    = BASE_DIR / ".seen_job_emails.json"
RESUME_FILE  = BASE_DIR / "prompts" / "resume.md"
HERMES_BIN   = "/home/thomasb/.local/bin/hermes"

PENDING_DIR.mkdir(exist_ok=True)
load_dotenv(BASE_DIR / ".env")

STRADDLE_URL = os.environ.get("STRADDLE_URL", "http://100.118.201.46:11435")
API_KEY      = os.environ.get("STRADDLE_API_KEY", "")
MODEL        = os.environ.get("DEFAULT_MODEL") or "qwen2.5:7b"

ICLOUD = {
    "email":     os.environ.get("ICLOUD_EMAIL", "tom.mb99@icloud.com"),
    "password":  os.environ.get("ICLOUD_PASS", ""),
    "imap_host": "imap.mail.me.com",
    "imap_port": 993,
}

# ── Detection ─────────────────────────────────────────────────────────────────

# Phrases that signal a reply to an application Thomas submitted
JOB_PHRASES = [
    "your application",
    "thank you for applying",
    "we reviewed your",
    "we received your application",
    "regarding your application",
    "application for",
    "move forward",
    "next steps",
    "schedule an interview",
    "phone screen",
    "video interview",
    "technical interview",
    "unfortunately",
    "not selected",
    "other candidates",
    "we will keep your",
    "position has been filled",
]

# Tone signals
REJECTION_SIGNALS = [
    "unfortunately", "not selected", "other candidates",
    "position has been filled", "we will not", "decided to move forward with other",
]
INTERVIEW_SIGNALS = [
    "interview", "schedule", "next steps", "phone screen",
    "video call", "video interview", "technical screen", "meet with",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _decode(raw: str) -> str:
    if not raw:
        return ""
    parts = _dh(raw)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)

def _body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                return payload.decode(errors="replace")[:3000] if payload else ""
    payload = msg.get_payload(decode=True)
    return payload.decode(errors="replace")[:3000] if payload else ""

def _sender_domain(from_str: str) -> str:
    import re
    m = re.search(r"@([\w.\-]+)", from_str)
    return m.group(1).lower() if m else ""

def _load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()

def _save_seen(seen: set):
    SEEN_FILE.write_text(json.dumps(list(seen)))

def _read_resume() -> str:
    if RESUME_FILE.exists():
        return RESUME_FILE.read_text().strip()
    return ""

# ── Sent-folder domain check ──────────────────────────────────────────────────

def sent_contains_domain(imap, domain: str) -> bool:
    """Return True if Sent has any prior email from Thomas to *@domain."""
    sent_folders = ["Sent Messages", "Sent", "INBOX.Sent"]
    for folder in sent_folders:
        try:
            status, _ = imap.select(f'"{folder}"', readonly=True)
            if status != "OK":
                continue
            _, data = imap.search(None, f'TO "@{domain}"')
            if data and data[0]:
                return True
        except Exception:
            continue
    return False

# ── Fetch unseen ──────────────────────────────────────────────────────────────

def fetch_candidates(seen: set) -> list:
    results = []
    if not ICLOUD["password"]:
        print("iCloud password not set in .env", file=sys.stderr)
        return results
    try:
        with imaplib.IMAP4_SSL(ICLOUD["imap_host"], ICLOUD["imap_port"]) as imap:
            imap.login(ICLOUD["email"], ICLOUD["password"])
            imap.select("INBOX")
            _, data = imap.search(None, "UNSEEN")
            uids = data[0].split()
            for uid in uids:
                uid_str = f"iCloud:{uid.decode()}"
                if uid_str in seen:
                    continue
                _, msg_data = imap.fetch(uid, "(RFC822)")
                for part in msg_data:
                    if not (isinstance(part, tuple) and isinstance(part[1], bytes)):
                        continue
                    msg = email.message_from_bytes(part[1])
                    from_raw  = _decode(msg.get("From", ""))
                    subj      = _decode(msg.get("Subject", ""))
                    body      = _body(msg)
                    domain    = _sender_domain(from_raw)
                    text      = (subj + " " + body).lower()

                    # Must match a job phrase
                    if not any(p in text for p in JOB_PHRASES):
                        continue

                    # Must have a prior outbound email to sender's domain
                    if not domain or not sent_contains_domain(imap, domain):
                        continue

                    results.append({
                        "uid":      uid_str,
                        "from":     from_raw,
                        "reply_to": msg.get("Reply-To") or from_raw,
                        "subject":  subj,
                        "date":     msg.get("Date", ""),
                        "body":     body,
                        "domain":   domain,
                    })
                    break
    except Exception as e:
        print(f"IMAP error: {e}", file=sys.stderr)
    return results

# ── Tone classification ───────────────────────────────────────────────────────

def classify_tone(msg: dict) -> str:
    text = (msg["subject"] + " " + msg["body"]).lower()
    if any(s in text for s in REJECTION_SIGNALS):
        return "rejection"
    if any(s in text for s in INTERVIEW_SIGNALS):
        return "interview"
    return "ambiguous"

# ── Draft ─────────────────────────────────────────────────────────────────────

TONE_INSTRUCTIONS = {
    "rejection": (
        "This is a rejection email. Write a gracious, brief reply (3–4 sentences). "
        "Thank them for their time and consideration. "
        "Politely ask to be kept in mind for future openings that match your background. "
        "Do not express disappointment."
    ),
    "interview": (
        "This email is inviting Thomas to an interview or next step. "
        "Write an enthusiastic, professional reply (3–5 sentences). "
        "Confirm strong interest in the role. "
        "Ask them to suggest available times rather than proposing specific slots. "
        "Express readiness to provide any additional information needed."
    ),
    "ambiguous": (
        "The intent of this email is unclear. Write a polite, brief acknowledgment (2–3 sentences). "
        "Thank them for reaching out and ask for clarification on the next step or what they need from Thomas."
    ),
}

def draft_reply(msg: dict, tone: str) -> str:
    resume = _read_resume()
    system = f"""You are Thomas Brown's professional email assistant.
Thomas is a 26-year-old CS student (Butler CC, 4.0 GPA) targeting remote Cloud/DevOps/Platform Engineering roles.
He is actively job searching.

{TONE_INSTRUCTIONS[tone]}

Sign every reply exactly as:
Thomas Brown
tom.mb99@icloud.com | (316) 945-6882 | Wichita, KS

Use Thomas's background below only to inform tone and fit — do not quote it verbatim.
Output ONLY the email body. No subject line. No preamble.

--- THOMAS'S BACKGROUND ---
{resume}
"""
    user_content = (
        f"From: {msg['from']}\n"
        f"Subject: {msg['subject']}\n"
        f"Date: {msg['date']}\n\n"
        f"{msg['body']}"
    )
    try:
        resp = requests.post(
            f"{STRADDLE_URL}/v1/chat/completions",
            headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user_content},
                ],
                "temperature": 0.4,
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return content if content else "[Draft returned empty — write reply manually.]"
    except Exception as e:
        return f"[Draft failed: {e}]\n\nWrite reply manually."

# ── Save & notify ─────────────────────────────────────────────────────────────

def save_pending(msg: dict, draft: str, tone: str) -> str:
    reply_id = hashlib.sha1(msg["uid"].encode()).hexdigest()[:8]
    record = {
        "id":         reply_id,
        "created_at": datetime.now().isoformat(),
        "account":    "iCloud",
        "uid":        msg["uid"],
        "from":       msg["from"],
        "reply_to":   msg["reply_to"],
        "subject":    msg["subject"],
        "date":       msg["date"],
        "original":   msg["body"],
        "tone":       tone,
        "draft":      draft,
        "status":     "pending",
    }
    (PENDING_DIR / f"{reply_id}.json").write_text(json.dumps(record, indent=2))
    return reply_id

def notify_telegram(msg: dict, draft: str, reply_id: str, tone: str):
    tone_tag = {"rejection": "❌ Rejection", "interview": "📅 Interview", "ambiguous": "❓ Unclear"}[tone]
    text = (
        f"📬 Job reply pending [{reply_id}] — {tone_tag}\n\n"
        f"From:    {msg['from']}\n"
        f"Subject: {msg['subject']}\n\n"
        f"━━ DRAFT ━━\n{draft}\n━━━━━━━━━━\n\n"
        f"approve_reply.py send {reply_id}\n"
        f"approve_reply.py skip {reply_id}\n"
        f"approve_reply.py edit {reply_id} 'new text'"
    )
    try:
        subprocess.run(
            [HERMES_BIN, "send", "telegram", text],
            check=True, capture_output=True, timeout=30,
            env={**os.environ, "HERMES_HOME": str(Path.home() / ".hermes")},
        )
        print(f"[{reply_id}] Telegram sent.")
    except Exception as e:
        print(f"[{reply_id}] Telegram failed: {e}", file=sys.stderr)
        print(f"  Pending saved: {PENDING_DIR}/{reply_id}.json")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    seen = _load_seen()
    new_seen = set()
    found = 0

    candidates = fetch_candidates(seen)
    for msg in candidates:
        new_seen.add(msg["uid"])
        tone     = classify_tone(msg)
        draft    = draft_reply(msg, tone)
        reply_id = save_pending(msg, draft, tone)
        notify_telegram(msg, draft, reply_id, tone)
        print(f"[{reply_id}] {tone} — {msg['subject']!r}")
        found += 1

    _save_seen(seen | new_seen)
    print(f"Done. {found} job email(s) queued.")

if __name__ == "__main__":
    main()
