# Roadmap, Fingerprints and Honest Limits

**Handshake to Contract · Srujana Tech Fest 2026 · LS-06**

This document covers three things:

1. **Roadmap.** What we deliberately did not build in 48 hours, why each item matters, and how it would plug into the code that exists.
2. **Fingerprints.** How the SHA-256 fingerprints link a deal to the other party, both today and once accounts (OAuth) exist.
3. **Shortcomings.** Everything we know is weak, missing or unverified, including things the README doesn't say.

> Decision support, not legal advice. Sections of law named here should be checked on India Code before they are relied on.

---

## Contents

1. [Where we are today](#1-where-we-are-today)
2. [Roadmap features](#2-roadmap-features)
3. [Fingerprints and the other party](#3-fingerprints-and-the-other-party)
4. [Shortcomings](#4-shortcomings)
5. [Suggested order of work](#5-suggested-order-of-work)

---

## 1. Where we are today

| Built | Status |
|---|---|
| P0 (F1 to F10): upload, extraction with grounding, red/yellow/green checklist, plain agreement, two confirmation routes, evidence chain, stamp guidance, cache, tests | ✅ |
| P1-1 to P1-6: certificate draft, MSME check, revision timeline, masking preview, evaluation page, evidence print view | ✅ |
| Roadmap | ❌ Not built, by design (FEATURES.md section 5) |

The rule that shaped the roadmap: **nothing on it was needed to prove the core idea.** A shop owner can upload a chat, see the gaps, get a plain agreement and keep a tamper-evident record without any roadmap item.

---

## 2. Roadmap features

Each item lists what it is, why it matters, where it plugs in, what it depends on, and the main risk.

### 2.1 Voice-note transcription

| | |
|---|---|
| **What** | Transcribe voice notes so terms said aloud ("delivery by the 10th") are read, not just flagged |
| **Why** | Small-business deals in India happen in voice notes. Today they show as "not analysed" (decision D1). The voice-note test chats were removed until this exists |
| **Plugs in at** | `chat_parser` already marks attachments. A transcription step would add messages of a new kind, `voice_transcript`, linked to the attachment index, before `extractor` runs |
| **Needs** | Exports **with media** (larger files, more upload handling); a speech-to-text model that handles Hinglish and Kannada-English |
| **Risk** | Transcription errors become "facts". A transcribed value must be marked as transcribed and shown with lower confidence. Grounding then checks against the transcript, not the audio, which is a weaker guarantee |

### 2.2 Screenshot OCR

| | |
|---|---|
| **What** | Read text from images: quotations, purchase orders, payment screenshots |
| **Why** | A price is often sent as a photo of a quotation, not typed |
| **Plugs in at** | The same place as voice: new `image_text` messages tied to the attachment |
| **Needs** | Media exports; an OCR model that handles printed Indian invoices |
| **Risk** | The same as voice. A UPI screenshot can also be faked easily, so OCR text should never count as proof of payment |

### 2.3 WhatsApp bot

| | |
|---|---|
| **What** | The owner forwards the chat, or adds the bot, instead of exporting a file. The recap and confirmation happen inside WhatsApp |
| **Why** | Exporting a chat is the biggest friction in the current flow |
| **Plugs in at** | A new router that receives webhook messages and calls the same `ingest()` that upload uses |
| **Needs** | WhatsApp Business Platform access: business verification, approved message templates, and Meta's rules on when a business may message a user first |
| **Risk** | A third party (Meta) sits in the evidence path; policy changes can break the product; the other party must consent to the bot reading their messages |

### 2.4 Real SMS OTP

| | |
|---|---|
| **What** | The other party proves they control a phone number before confirming |
| **Why** | Today anyone holding the link can confirm and type any name (section 4.1) |
| **Plugs in at** | `confirm.py`: before accepting answers, verify an OTP sent to the number recorded for that party. Put the verified number's hash into the `counterparty_response` event |
| **Needs** | A DLT-registered SMS sender and template (required for commercial SMS in India), and a per-message cost |
| **Risk** | Proves control of a SIM, not who a person is. Still an acknowledgement, not a signature |

### 2.5 Aadhaar eSign

| | |
|---|---|
| **What** | A legally recognised electronic signature on the final agreement, through a licensed eSign service provider |
| **Why** | It turns "acknowledged" into "signed". Electronic signatures are recognised under the IT Act, 2000 (s.3A and the Second Schedule; check the current schedule) |
| **Plugs in at** | After status `confirmed`: send the agreement's hash to the eSign provider; store the signed document and the provider's response as a new evidence event |
| **Needs** | A contract with a licensed eSign service provider, per-signature fees, and Aadhaar handling rules |
| **Risk** | Highest compliance load on the list. Some documents cannot be eSigned and must be registered or physically stamped |

### 2.6 E-stamp purchase integration

| | |
|---|---|
| **What** | Buy the e-stamp paper from inside the app, instead of only explaining stamp duty |
| **Why** | Stamp guidance (F7) tells the owner what to do but leaves them to do it |
| **Plugs in at** | `stamp_guidance` already returns the state and the authority. A purchase flow would add the certificate number and amount as an evidence event |
| **Needs** | Verified duty rates per state (we show none today), a partnership with the e-stamping system each state uses, and payment handling |
| **Risk** | A wrong rate means underpaid duty and a penalty. Rates must come from the official state schedule, never from the model |

### 2.7 Trusted timestamping (anchoring the chain)

| | |
|---|---|
| **What** | Periodically send the chain head (the latest `chain_hash`) to an independent timestamp authority (RFC 3161), or publish it somewhere we cannot edit |
| **Why** | This is the **most important item for evidence strength.** Today the chain detects partial edits, but whoever controls the database could rebuild the whole chain with fresh hashes (section 4.2). An outside timestamp fixes the head in time |
| **Plugs in at** | A new evidence event `anchored` holding the authority's token. `verify_chain` gains a step: does the anchored head still appear in the chain? |
| **Needs** | A timestamp authority (several offer RFC 3161 endpoints), plus a scheduler |
| **Risk** | Low. Small and cheap, and it removes our biggest evidence weakness |

### 2.8 Hindi and Kannada output

| | |
|---|---|
| **What** | The agreement, flags and recap message in the owner's language |
| **Why** | The people this is built for often read English less comfortably than they speak Hinglish |
| **Plugs in at** | `clause_builder` and `legal_refs.json` are fixed templates, so translation means translated templates reviewed by a person, **not** model-translated text |
| **Needs** | Legally reviewed translations of every clause and flag |
| **Risk** | A translated clause that changes meaning. Each version needs its own hash, and one language must be named as the one that prevails |

### 2.9 Accounts and roles (OAuth)

> **Not built.** An earlier version had email + password accounts. They were removed, so today there is one shared workspace.

| | |
|---|---|
| **What** | Sign-in (Google or phone), so each business sees only its own chats, and the other party can have an account too |
| **Why** | Today there is one shared demo workspace: anyone with the URL can open any chat ID (section 4.3) |
| **Plugs in at** | A `User` table; an `owner_id` on `Conversation`; an auth dependency on every router. This is the first **schema change** since the start, so it needs migrations (Alembic) |
| **Needs** | An OAuth provider and session handling |
| **Risk** | Moderate. This is what turns fingerprints into proof of *who*, not just *what* (section 3.3) |

### 2.10 Public deployment

| | |
|---|---|
| **What** | A hosted instance real businesses can use |
| **Needs first** | Accounts (2.9); `DEMO_TAMPER_ENABLED=false`; a paid model plan whose terms don't allow training on inputs; a privacy notice; a lawful basis for processing the other party's messages under the DPDP Act, 2023 (check the rules in force); backups; rate limiting; HTTPS |
| **Risk** | Real customer data. **Nothing should be deployed publicly before 2.7 and 2.9**, and before the privacy points in section 4.7 are settled |

---

## 3. Fingerprints and the other party

### 3.1 What gets fingerprinted

A fingerprint is a SHA-256 hash: 64 characters that change completely if even one character of the input changes. The app creates four kinds.

| Fingerprint | Taken over | Stored as | Answers |
|---|---|---|---|
| **File fingerprint** | The exact bytes of the uploaded `.txt` export | `Conversation.content_sha256`; in the `upload` event | "Is this the same file that was uploaded?" |
| **Agreement fingerprint** | The clause list as built (headings, text, status, source messages), as sorted-key JSON | `Agreement.clauses_hash` | "Is this exactly the agreement that was drafted?" |
| **Event fingerprint** | Each evidence event's payload | `payload_sha256` | "Was this event's content edited?" |
| **Chain fingerprint** | Previous chain hash + event fingerprint + UTC time | `chain_hash`; the latest one is the **chain head** | "Was anything earlier removed, reordered or changed?" |

```
upload           file fingerprint ─┐
extraction                         ├─ each event's chain_hash includes the one before,
agreement_generated  agreement fp ─┤   so the chain head summarises the whole history
agreement_sent       agreement fp ─┤
counterparty_response agreement fp the other party SAW ─┘
```

### 3.2 How fingerprints connect us to the other party today

There are no accounts today, so the fingerprints prove **what** was agreed and **when it was recorded**, not **who** the other person is. Each confirmation route uses them as follows.

**Route A: the confirmation link**

```
Owner                         Server                                  Other party
  │ generate agreement ───────► clauses_hash = H(clauses)
  │                             event: agreement_generated {H}
  │ send ─────────────────────► token = random 256-bit, expires in 72 h
  │                             event: agreement_sent {H, expires_at}
  │ shares the link on WhatsApp ───────────────────────────────────► opens /confirm/<token>
  │                                                                  sees the clauses and H
  │                             ◄──────── agrees per clause, types a name
  │                             event: counterparty_response
  │                               {typed_name, clauses_hash_seen: H, answers}
  │                             link marked used (409 if reused, 410 if expired)
```

The key field is **`clauses_hash_seen`**. It records which version of the agreement the other party was shown. If the owner later edits and regenerates the agreement, the new version gets a new hash, so the earlier confirmation can never be presented as approving the new text. A mismatch is visible to anyone who compares the two hashes.

**Route B: the WhatsApp recap**

1. The owner sends a recap message on WhatsApp.
2. The other party replies, for example "Yes, all correct 👍".
3. The owner exports the chat again and uploads it. That upload gets its **own file fingerprint**.
4. The owner picks the reply message. The `recap_reply` event stores the agreement fingerprint, the source conversation and the message index, and the reply text.

The confirmation is now tied to a second fingerprinted file that contains the other party's own words, sent from their own WhatsApp account. That is the strongest "it was them" signal available without accounts: the reply came from their number, inside a conversation they can export themselves.

**What anyone can check today**

- Recompute the hash of the uploaded `.txt` with any SHA-256 tool (`sha256sum chat.txt`) and compare it with the certificate draft and the evidence summary. **A layperson can check this.**
- Click **Check integrity** to recompute every chain link.
- The agreement fingerprint is over canonical JSON, so in practice it is checked through the app, not by hand (section 4.2).

**Small additions that need no accounts**

| Idea | Effort | Effect |
|---|---|---|
| Put a short form of the agreement fingerprint (first 8 characters) in the WhatsApp recap text: "Ref: 3f9a1c07" | Small | The other party's "yes" sits directly under a reference to one exact version, inside their own WhatsApp history |
| Show the chain head on the confirmation page, and in the other party's receipt after they confirm | Small | **They now hold a copy of the head.** If we later rewrote our database, their copy would no longer match. This is a cheap form of anchoring (2.7) |
| A read-only page, `/verify/<fingerprint>`, that says which agreement a fingerprint belongs to, its status and its date, without showing the chat | Small | Either side, or a third party such as a mediator, can confirm a printout is genuine |
| A downloadable receipt for the other party (the clauses, their answers, the fingerprint and the chain head) | Small to medium | Both sides keep the same evidence, not just the owner |

### 3.3 After accounts (OAuth) and authentication

Accounts add the missing piece: a **verified identity** attached to each fingerprint.

```
Owner (signed in: Google sub / verified phone)
  │ uploads chat ── event: upload {file_fp, owner_id}
  │ drafts ──────── event: agreement_generated {H, owner_id}
  │ invites the other party by phone or email
  │
Other party (signs in with their own account; phone verified by OTP)
  │ sees the agreement and H
  │ confirms ────── event: counterparty_response
  │                   {clauses_hash_seen: H, party_id, verified_phone_hash, method}
  │
Both accounts now list the same agreement, with the same H and the same chain head.
```

What changes:

1. **Who, not just what.** The `counterparty_response` event stores an account identifier and how it was verified (OAuth subject, OTP-verified phone, later eSign) instead of a typed name. The typed name stays as a courtesy, not the proof.
2. **The party is matched to the chat.** The phone number the other party verifies can be compared with the number in the WhatsApp export header or in the chat, after masking. A match is strong evidence that the person confirming is the person in the conversation. A mismatch is a warning, not a block: people use more than one number.
3. **Both sides hold the same record.** The agreement shows up in both accounts. Each side can verify the chain independently, and each keeps the chain head from the moment they confirmed. Rewriting the record afterwards would need both of them to accept a different history.
4. **Linking two exports of the same chat.** If the other party uploads *their* export of the same conversation, the file fingerprints will differ: the exports name the sender differently ("You" against a saved contact name) and may format dates differently. So matching has to compare **per-message fingerprints** of the normalised text, not whole files. Two exports agreeing message by message is strong evidence neither was edited, which addresses the "genuine before upload" gap (section 4.2) as far as any software can.
5. **Signing and anchoring.** With identities in place, eSign (2.5) signs the agreement fingerprint, and trusted timestamping (2.7) fixes the chain head in time. Together: *this* person signed *this exact text*, and *this* record existed no later than *this* time.

What does **not** change: a fingerprint still proves only that nothing changed **after** it was taken. Accounts make the "who" stronger. They do not make an edited-before-upload chat genuine.

---

## 4. Shortcomings

Grouped by area. **Severity** is how much it would hurt a real user or a judge's question. "Fix" is the realistic remedy.

### 4.1 Identity and confirmation

| Shortcoming | Severity | Fix |
|---|---|---|
| No identity check. Anyone with the confirmation link can confirm and type any name | High | OTP (2.4), accounts (2.9), eSign (2.5) |
| The link is a bearer token in a URL. If it is forwarded or leaks from a phone's history, someone else can use it within 72 hours | Medium | Single use already; add OTP on open; shorter expiry for large deals |
| The confirmation is an acknowledgement, not a signature. The app says so, but a user may still overrate it | Medium | Keep the wording; eSign on the roadmap |
| Route B relies on the owner choosing the right reply message. A wrong pick is possible | Low | Show the picked message prominently; the other party's receipt (3.2) |

### 4.2 Evidence and fingerprints

| Shortcoming | Severity | Fix |
|---|---|---|
| **The chain lives in our own database.** Someone with database access could edit an event and recompute every later hash, producing a chain that verifies. Tamper-evident against partial edits, not against a full rewrite by the operator | **High** | Anchoring (2.7); give the other party the chain head (3.2) |
| A chat edited **before** export or upload cannot be detected | High | Cross-matching both parties' exports (3.3, point 4); stated in the UI |
| Event times come from our server clock | Medium | Trusted timestamps (2.7) |
| The agreement fingerprint can't easily be recomputed by hand (canonical JSON, not a file) | Low | A `/verify` page; publish the exact hashing recipe |
| The certificate draft follows the structure of the BSA s.63(4) certificate but **has not been checked against the official Schedule wording** | Medium | Check against the published Schedule, ideally with a lawyer |
| Part B (the expert's certificate) is not produced and cannot be | By design | Stated on the page |

### 4.3 Security and access

| Shortcoming | Severity | Fix |
|---|---|---|
| No authentication. Every chat, agreement and evidence record is visible to anyone who can reach the server, and anyone can create share links | High | Accounts (2.9). Until then, run locally or behind your own access control |
| No rate limiting on upload or extraction. Anyone could burn the model quota | Medium | A rate limiter per IP or account |
| The tamper endpoint exists in the codebase; it is off only because of a setting (`DEMO_TAMPER_ENABLED`) | Medium | Off by default in any non-demo build, and checked at startup |
| Fonts load from Google Fonts. Offline, the app falls back to system fonts. Not a security issue, but it does call a third party | Low | Self-host the fonts |

### 4.4 Privacy and masking

| Shortcoming | Severity | Fix |
|---|---|---|
| Masking is pattern-based. It catches Indian mobile numbers, PAN, Aadhaar, GSTIN, email and UPI IDs. It **misses** landlines, bank account numbers, IFSC codes, addresses and vehicle numbers | Medium | More patterns; an optional local named-entity pass |
| Names are deliberately **not** masked, because extraction must find the parties. Names do reach the model | Medium | A stated choice (D6); only synthetic chats are used |
| Placeholders still reveal the *kind* of data ("there is a phone number here") | Low | Acceptable |
| The other party never agreed to their messages being analysed by an AI. This matters under the DPDP Act, 2023 once real data is used | **High for real use** | Consent on the confirmation page; a paid model tier that doesn't train on inputs; a privacy notice |
| Free-tier model providers may use inputs to improve their products | High for real data | Synthetic data only (D6), as now |

### 4.5 Understanding the chat

| Shortcoming | Severity | Fix |
|---|---|---|
| Text only. Voice notes and images are flagged, not read | Medium | 2.1 and 2.2 |
| Subtle sarcasm, or an off-topic "ok", reads as agreement. Sarcasm with clear signals (eye-roll emoji, exaggerated extra demand, stock phrases) is caught (T13) | Medium | Explicit confirmation (F5) is the safeguard; that's why it exists |
| The s.62 rule looks only at the **next** text reply from the other side. A reply split over two messages, or an "ok" that answers an earlier question, can be misjudged | Medium | Look at a short window of replies; let the owner correct it |
| Group chats with three or more people: the two contracting parties can't be identified reliably | Medium | Warned (T12); let the owner pick the two parties |
| Two deals in one chat may be merged (T10) | Medium | Warned; a "split deals" step |
| Vagueness is judged by the model and can be wrong either way | Low | It only produces Yellow, never Red (D2) |
| The injection guard is pattern-based. A cleverly worded instruction could reach the model. Grounding still stops any value that isn't in the chat, so an injection can't invent a term; at worst it could make the model miss one | Low | Grounding remains the real defence |
| English output only | Medium for the target users | 2.8 |

### 4.6 Legal coverage

| Shortcoming | Severity | Fix |
|---|---|---|
| **Section references have not yet been verified on India Code** (a pending item in the README) | **High before any real use** | Check every entry in `legal_refs.json` against the official text |
| Stamp guidance covers Karnataka and Maharashtra only, and shows no duty rates | Medium | Add states only from verified official schedules |
| The MSME check counts a month as 30 days, takes the longest period stated, and does not check registration, who is the supplier, or when acceptance happened (s.15 runs from acceptance) | Medium | Advisory only, which the UI says; ask who the supplier is |
| Property, leases and other documents that must be registered are out of scope | By design | Stated |
| Not legal advice. The app supports decisions; it doesn't make them | By design | The disclaimer is on every page (D10) |

### 4.7 Engineering and validation

| Shortcoming | Severity | Fix |
|---|---|---|
| **The AI half has not been measured against a live model.** The evaluation page says "not yet run" until `run_eval` runs with a real key. We have no real accuracy number yet | **High for the pitch** | Run `python -m tests.run_eval` with the demo key and quote the result, failures included |
| `docker compose up --build` has not been run end to end by us (Docker Hub was unreachable where we built). Each part was tested separately, including PostgreSQL 16 | Medium | Run RUNNING.md section 8 once on a team laptop |
| Real Groq calls untested from our side; all flows used a stand-in model | Medium | `python -m app.check_llm` with the real key |
| The Gemini fallback is coded but needs `google-genai` added and a key | Low | Add when needed |
| No database migrations. A schema change needs `docker compose down -v`, which also wipes the AI cache | Medium | Alembic, needed anyway for accounts |
| The free-tier daily token quota limits how many chats can be checked live in one day | Medium for the demo | Warm the cache for the demo chats (RUNNING.md section 10) |
| One server process; no background jobs, backups or monitoring | Low for a demo | Needed before deployment |

---

## 5. Suggested order of work

Ordered by how much each step strengthens the claims the product already makes, against its cost.

| Order | Item | Why this position |
|---|---|---|
| 1 | Verify every legal section on India Code; run `run_eval` on a live key | Cheap, and both are claims we currently make without full proof |
| 2 | Fingerprint reference in the recap, chain head and receipt for the other party, `/verify` page (3.2) | Small, no accounts needed, and it shrinks the "operator could rewrite" gap |
| 3 | Trusted timestamping (2.7) | Small, and fixes the biggest evidence weakness |
| 4 | Accounts and roles (2.9), with migrations | Unlocks identity, privacy and deployment |
| 5 | SMS OTP (2.4) | First real identity signal for the other party |
| 6 | Voice transcription (2.1), then OCR (2.2) | Biggest gain in what the app can read |
| 7 | Hindi and Kannada output (2.8) | Reach; needs reviewed translations |
| 8 | Public deployment (2.10) | Only after 3, 4 and the privacy work |
| 9 | Aadhaar eSign (2.5), e-stamp purchase (2.6), WhatsApp bot (2.3) | Each needs a commercial partner, compliance work, or both |

*The short version for a judge: today the fingerprints prove **what** was agreed and that it hasn't changed since. Accounts and OTP add **who**. Anchoring adds **when**, in a way even we can't rewrite.*
