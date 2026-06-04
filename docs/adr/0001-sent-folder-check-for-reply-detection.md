# ADR 0001 — Sent-Folder Check for Job Reply Detection

**Status:** Accepted

## Context
The monitor must distinguish Job Application Replies (emails responding to applications Thomas sent) from unsolicited recruiter outreach. Keyword matching alone cannot make this distinction reliably — phrases like "your application" and "next steps" appear in both.

## Decision
Use IMAP search of the iCloud Sent mailbox to confirm a prior outbound email from Thomas exists to the sender's domain before treating an inbound email as a Job Application Reply.

## Alternatives considered
- **Keywords only** — zero maintenance, but false positives from unsolicited outreach would generate noise drafts requiring manual skipping.
- **Applied-companies allowlist** — accurate, but requires Thomas to manually maintain a file of applied domains; friction defeats the automation goal.

## Consequences
- Requires IMAP credentials to have read access to Sent mailbox (already available via `mail_hub.py`).
- Domain-level match means a reply from `careers@company.com` is confirmed if Thomas sent anything to `*@company.com`. Edge case: Thomas applied via a third-party ATS domain (e.g. `greenhouse.io`) — the reply comes from the company domain but Sent has the ATS domain. This will be a miss; acceptable for MVP.
- Extra IMAP round-trip per detected email (~1–2s). Acceptable at 15-min poll cadence.
