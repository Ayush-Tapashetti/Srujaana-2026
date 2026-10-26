# Share with a CA or lawyer

One click gives a CA or lawyer a read-only **evidence summary for review**: no account, no install.

## What they see (`/pack/:token`)
- The chat: file, participants, message count, period.
- What the chat says: each term and flag, with the source messages quoted (identifiers masked).
- The agreement and who answered it (acknowledgements, not signatures).
- Every recorded event with its three hashes and a live **Verified / Broken** badge, recomputed on every page load.
- A draft of Part A of the s.63(4) BSA 2023 certificate: party fields blank, statements unticked.
- A limitations banner and Print / Save as PDF.

## How it works
| Piece | Where |
|---|---|
| Table `share_links` (token, expiry, revoked, view count) | `server/app/models/share.py` (new table, `create_all` adds it; **no database reset**) |
| `POST /api/evidence/{id}/share`, `GET .../shares`, `POST .../share/{share_id}/revoke` | `server/app/routers/share.py` |
| `GET /api/pack/{token}` (public) | same file; built from the existing analysis, agreement, `verify_chain` and `certificate_draft` |
| Owner panel (consent tick, expiry, copy, turn off) | `client/src/components/SharePanel.tsx`, shown on the Evidence page |
| Public page | `client/src/pages/PackPage.tsx` |

Sharing is **not** recorded as an evidence event: a new event type would change the chain's schema.

## Privacy decisions
- Phone, PAN, Aadhaar, GSTIN, email and UPI are masked with the same masker the AI step uses.
- Raw event payloads are never returned (they contain the owner's email). Each event becomes one masked sentence.
- Hashes are never masked: a hex digest can contain a digit run the masker would alter.
- Owner must tick "anyone with the link can read this". Links last 1, 7 (default) or 30 days, can be turned off, are capped at 10 live per chat, and the response is `noindex`, `no-store`, `no-referrer`.

## Wording
Call it an *evidence summary for review*. Not "court-ready", not a "legal pack". Part A is a draft the party completes; Part B needs an expert.

## Not built (optional upgrade)
Recomputing the hashes in the browser so the CA need not trust the server. It needs byte-identical JSON canonicalisation between Python and JavaScript (non-ASCII escaping, microsecond timestamps) and the raw payloads, which the pack deliberately withholds.
