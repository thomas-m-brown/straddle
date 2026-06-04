# Straddle — Domain Glossary

## Job Application Reply
An email received in direct response to a job application Thomas submitted. Excludes unsolicited recruiter outreach, staffing agency marketing, ATS acknowledgement-only messages, and any email Thomas did not initiate by applying first.

Detected by: keyword match on subject/body AND prior email from Thomas to sender's domain found in iCloud Sent folder (IMAP search).

## Pending Reply
A drafted response awaiting Thomas's approval. States: `pending` → `sent` | `skipped` (both terminal). Editing mutates draft in-place; state stays `pending` until actioned. Auto-skipped after 7 days with Telegram notification. `skipped` is terminal.

## Draft
LLM-generated reply body for a Pending Reply. Properties:
- Tone category (one of three) drives content: Rejection, Interview, Ambiguous
- Length: 3–5 sentences guideline, not hard-truncated
- Signature email matches send account (iCloud → tom.mb99@icloud.com)
- Resume file used to inform tone/fit only; no direct quoting
- Temperature 0.4 (low creativity, consistent professional tone)

## Tone Category
Classification applied to each Job Application Reply before drafting. Three values:
- **Rejection** — signals: "unfortunately", "other candidates", "not selected", "position has been filled". Draft: gracious, brief, ask to keep on file.
- **Interview** — signals: "interview", "schedule", "next steps", "phone screen", "video call". Draft: enthusiastic, ask them to suggest times (no specific slots committed).
- **Ambiguous** — no clear signal. Draft: polite acknowledgment, request clarification.

## Approval
Thomas's explicit action to send a Pending Reply via Telegram. Approval channel: Telegram only. Approve CLI (`approve_reply.py`) used from terminal. No web UI.

## Resume Context
File at `~/straddle/prompts/resume.md`. Read at draft-time (not startup) so edits are reflected immediately. Used by LLM to understand Thomas's background and target role; not quoted verbatim in drafts.

## Sent-Folder Check
IMAP search of iCloud Sent mailbox for any prior outbound email from Thomas to the sender's domain. Used to confirm a received email is a reply to something Thomas initiated, not unsolicited outreach. Domain-level match (not exact address).
