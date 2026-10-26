# FEATURES.md: LS-06 "From Handshake to Contract" (v3, consolidated)

> Turn informal dealings (WhatsApp chats) into a clear, defensible record, without making the relationship feel legalistic.

**Supersedes v1 and v2.** This version folds in every decision made since: no OTP, a lean stack, owner-only value, a second confirmation route, and the test-spread plan. If a feature below ever seems to conflict with a binding decision (section 1), **the decision wins**.

**Companion files:** `PROJECT_RATIONALE.md` (why and impact), `LEGAL_REFERENCES_AND_COMPETITORS.md` (law and market), `TECH_STACK.md` (tools), `TEST_PLAN.md` (validation), `TECHNICAL_TERMS.md` (glossary).

**Deadlines:** P0 complete and demoable by **H34**. Demo video by **H36** (it decides the finalists). Full submission by **H48**.

---

## 1. Binding Decisions (Apply to Every Feature)

| # | Decision | Reason |
|---|---|---|
| D1 | **Input is text only:** a WhatsApp `.txt` export or pasted text. Voice notes and images show up in exports as attachment placeholders; the app **detects them and flags "not analysed, add the terms manually"**. No transcription or OCR in this build | One reliable end-to-end flow beats many half-built ones (rubric) |
| D2 | **An LLM does exactly two jobs:** (a) extract terms, (b) judge vagueness of extracted terms. **Everything else is code:** parsing, missing-term checks, agreement text (a fixed clause structure built in code), hashing, stamp guidance | Explainable, testable, and light on tokens |
| D3 | **No OTP anywhere.** Confirmation is an **acknowledgement**, never an eSign or identity check. Two routes: (A) a one-time link where the other party types their name and agrees per clause, (B) a WhatsApp recap whose reply is attached as evidence. The UI always says: "Acknowledgement recorded. Not a legal electronic signature" | A simulated OTP proves nothing, and a real one needs a paid SMS service |
| D4 | **Evidence is a SHA-256 hash chain.** It shows nothing changed **since upload**. It cannot prove the chat was genuine before upload. UI and README say so | Honest limits earn trust; hidden ones cost it |
| D5 | **Stamp duty is guidance only**, for **2 states** (Karnataka plus one more), from a sourced data file. **The app calculates no duty.** Rates appear only if verified from the official state schedule and carry `last_verified` | Domain correctness (20 points) beats coverage |
| D6 | **Synthetic data only.** PII masking runs before any text reaches an external LLM. Free-tier LLM terms may allow the provider to use inputs, so real customer chats are never sent | Privacy, and the rubric allows synthetic data |
| D7 | **Status colours mean one thing everywhere:** 🔴 Red = a critical term is missing or in unresolved conflict; 🟡 Yellow = present but vague; 🟢 Green = clear. **Overall = worst critical term.** Colour is always paired with a text label | Consistent logic and accessibility |
| D8 | **Red blocks "Send for confirmation" (both routes)** until resolved or explicitly overridden with a recorded acknowledgement. Yellow warns but allows | Defines behaviour precisely |
| D9 | **Output language is English.** Input may be English or Hinglish. Hindi/Kannada output is roadmap only | Scope control |
| D10 | **No claim of legal validity.** Persistent notice: decision support, not legal advice | Rubric professional-boundaries rule |
| D11 | **Owner-only value.** F1 to F4 and F6 to F8 work without the other party ever opening the app. Confirmation (F5) is a bonus, not the foundation | Answers the biggest adoption weakness: owners avoid asking customers |
| D12 | **Lean stack, frozen by H4.** One LLM provider first (Groq); add Gemini as fallback only after the core flow works. No new dependency unless a P0 feature is blocked | Two people, about 34 build hours |
| D13 | **LLM responses are cached** (keyed by hash of input plus prompt version) and labelled "cached" in the UI. A switch turns the cache off for live demos and judge drills | Reliability and token savings, without hiding behaviour |

---

## 2. Priority Tiers

| Tier | Meaning |
|---|---|
| **P0** | Required. Works end to end by H34 |
| **P1** | Only after P0 is stable. Target H36 to H46 |
| **Roadmap** | Mentioned in the presentation only. Not built |

---

## 3. P0 Features

### F1. Conversation Ingestion and Privacy Guard
**Purpose:** get a clean, ordered message list from a raw chat safely.

**Behaviour**
- Accepts paste or `.txt` upload (type and size validated)
- Parses common WhatsApp export formats (12-hour and 24-hour time, multi-line messages, system lines; read as `utf-8-sig` to survive a BOM)
- Keeps the **original file unmodified** plus the parsed version
- Lists attachment placeholders as "not analysed" (D1)
- Masks phone numbers, Aadhaar, PAN and emails **before** any LLM call, and shows what was masked
- Friendly errors for empty, unsupported or oversized input

**Rubric:** Functional completeness, Validation, Domain (privacy).

---

### F2. Term Extraction with Source Links and Revisions
**Purpose:** pull out the deal terms and show where each came from.

**Terms:** parties, scope or deliverables, price (amount, GST included or excluded), advance, payment due, delivery or timeline, quantity or specs, cancellation or late-payment mentions.

**Behaviour**
- LLM output is forced into JSON and validated by Pydantic; one retry on invalid output, then a clear error
- Each term has `value`, `status` (clear / vague / missing), `confidence`, `source_message_ids`
- Clicking a term highlights the original message(s) in the chat view
- **Revisions:** the latest value is active; earlier values stay in `revision_history` and are marked "revised". (The timeline *view* is P1-3; the detection is P0)
- Works on English and Hinglish test chats
- Long chats are split into windows, and window results are merged without duplicates

```json
{
  "type": "payment_due",
  "value": "within 30 days of delivery",
  "status": "clear",
  "confidence": 0.9,
  "source_message_ids": [14, 15],
  "revision_history": [{"value": "15 days", "source_message_ids": [9]}]
}
```

**Rubric:** Technical depth, Domain (Contract Act s.62 for alterations).

---

### F3. Gap and Ambiguity Check
**Purpose:** tell the owner what could cause a dispute.

**Hybrid by design (D2, D7):** a **deterministic checklist** decides what is *missing* (Red); the **LLM** decides what is *vague* (Yellow).

| Term | Critical? | Red when | Yellow when |
|---|---|---|---|
| Parties | Yes | no counterparty identifiable | name only, no business identity or contact |
| Scope / deliverables | Yes | absent | vague description |
| Price | Yes | absent | approximate, or GST treatment unclear |
| Payment due | Yes | absent | relative with no anchor |
| Delivery / timeline | Yes | absent | vague time words |
| Conflicting revisions | Yes | two values, no clear final | n/a |
| Acceptance / quality criteria | No | n/a | missing |
| Cancellation / late payment | No | n/a | missing |
| Dispute handling | No | n/a | missing |

**Behaviour**
- Each flag shows: what is wrong, why it matters (one plain sentence), the source message, a suggested clarifying question, and the legal reason from `legal_refs.json`
- Overall readiness badge follows D7; sending follows D8
- Never invents a term. Missing means missing

**Rubric:** Domain correctness (20), Technical depth, Validation.

---

### F4. Plain-Language Agreement Draft
**Purpose:** a short agreement both sides can read in a minute.

**Behaviour**
- Built **in code** from a fixed clause structure filled with active term values (no free-form LLM drafting, D2). The API returns the agreement as a **list of clause objects** (`id`, `heading`, `body`, `status`, `source_message_ids`), and React renders them. No templating engine, and no second rendered-string copy that could drift from the structure
- Unresolved terms appear as `[to be confirmed]`, never guessed
- Shown as a **clause tree** (Parties, Scope, Price, Payment, Timeline, Changes, Cancellation, Disputes); each clause links to its source messages
- A "what we understood from your chat" summary sits above the formal text
- **PDF via a print-friendly view** ("Print / Save as PDF" in the browser). No server-side PDF library in P0
- Footer carries the D10 notice

**Rubric:** Functional completeness, UX, Domain.

---

### F5. Relationship-Friendly Confirmation (Two Routes, No OTP)
**Purpose:** remove the awkwardness of asking a long-standing customer for a contract, without faking identity checks.

**Shared**
- Three static tone presets for the message (Warm, Neutral, Formal). No LLM involved
- Status per agreement: Draft, Sent, Changes requested, Confirmed
- Every response is appended to the evidence chain
- Always labelled an acknowledgement (D3)

**Route A: one-time link**
- Random token (`secrets.token_urlsafe`), expiring, single use
- The other party sees the clauses read-only and, for each, chooses **Agree**, **Suggest a change** or **Ask a question**
- To submit they type their **full name** and tick "I have read these terms"
- Recorded: timestamp, typed name, and a hash of the clause values they saw
- A change request reopens **only the affected clause**
- For the demo, open the link in a second browser tab or a second device on the same network (or on a deployed URL if you deploy)

**Route B: WhatsApp recap (no app needed for the other party)**
1. The app generates a recap message to paste into the same WhatsApp chat
2. Later the owner uploads the updated chat export
3. The app lists messages after the recap, and the owner marks the one(s) that confirm it
4. The confirming message is recorded with its source link, plus a new file hash, in the evidence chain

**Rubric:** Problem understanding, UX, Originality.

---

### F6. Tamper-Evident Evidence Trail
**Purpose:** preserve what was said and agreed, and show later modification.

**Behaviour**
- SHA-256 of the original upload is recorded at upload
- Every event (upload, extraction, agreement version, link sent, response, recap reply, confirmation) joins a **hash chain**: `h_n = SHA256(h_{n-1} || SHA256(event_payload) || timestamp)`
- **Verify integrity:** 🟢 Intact or 🔴 Broken at event N
- **Tamper demo:** a dev-only endpoint edits one stored record, and verification then fails
- Append-only API: no update or delete endpoints
- UI text states the D4 limit

**Rubric:** Technical depth, Domain (BSA s.63), Originality.

---

### F7. Stamp Duty Guidance
**Purpose:** explain the stamping risk correctly.

**Behaviour**
- For Karnataka plus one other state (D5): an unstamped agreement is generally **not void** but may be **inadmissible as evidence until duty and any penalty are paid**; the defect is **curable**
- A "how to get it stamped" checklist and the e-stamping route
- Each data entry carries `source_url` and `last_verified`
- Unknown state or document type shows "check your state stamp authority or a lawyer"

**Rubric:** Domain correctness (20).

---

### F8. Trust and Limits Panel
- Persistent disclaimer (D10)
- **"Needs lawyer review"** flag when any critical term is Red or an override was used
- **Limitations panel:** supported input, languages, legal data last verified, what the evidence trail does not prove, what the app does not do
- **AI-use disclosure** in the README (the event requires it)

**Rubric:** Domain, Validation, Presentation.

---

### F9. Reliability Layer
- Timeouts, JSON validation and **one retry** (a short hand-written loop) on every LLM call
- **Response cache** (D13)
- **Groq first.** **Gemini fallback added by about H28** once the core flow is stable; if not, cache plus the recorded video cover an outage
- Windowing for long chats to respect per-minute token caps
- Health endpoint and clear error states
- Model names come from environment variables, never hard-coded

**Rubric:** Functional completeness and reliability (15).

---

### F10. Validation Evidence
- Labelled test chats and expected outputs (see `TEST_PLAN.md`; minimum T1 to T8, target T1 to T12)
- `pytest` unit tests for the parser, PII mask, checklist engine, hash chain (including tamper detection) and stamp lookup
- README results table with per-term accuracy, missed gaps, hallucinated terms, and known failures
- Rehearsed live "change an input" drills

**Rubric:** Validation and robustness (10).

---

## 4. P1 Features (After P0 Is Stable)

All six are built. None needs a roadmap item, and none changes the database schema: every new value is computed at read time, so no `docker compose down -v` is needed to upgrade.

| ID | Feature | Status | Where |
|---|---|---|---|
| P1-1 | **BSA s.63(4) Part A draft assist:** pre-fills the record (file, size, messages, period, export method, upload time) and the hash value, algorithm, chain head and chain check | ✅ Labelled "draft for the party to review". The party types their name and device on the page (never sent or stored) and ticks the statements themselves; all start unticked. Part B needs an expert, and the page says so. Printable | `GET /api/evidence/{id}/certificate-draft`, Evidence → "Draft Part A" |
| P1-2 | **MSME payment-term check:** asks "Is the supplier registered as a micro or small enterprise (Udyam)?" Yes / No / Not sure; Yes and a term over 45 days gives a Yellow s.15 flag | ✅ Stateless and advisory: never changes readiness. Reads days, weeks and months, in digits, English words and Hinglish ("do mahine") | `GET /api/conversations/{id}/msme-check?supplier_is_micro_or_small=yes\|no\|unsure`, Check page |
| P1-3 | **Revision timeline view** | ✅ Each value, who proposed it and when, ending in the exact reply the s.62 rule judged (`response_message_index`, computed with the same `next_reply` helper as the rule) | Check page, "How the terms changed" |
| P1-4 | **PII masking preview**, and masking wired into extraction | ✅ The extractor now pseudonymises every transcript with one shared token map before any LLM call and restores real values before grounding (D6). The preview shows each line as written and as sent, re-scans every sent line, and is built from the extractor's own `model_body`, so it cannot drift from what is really sent | `GET /api/conversations/{id}/masked-preview`, Check page → "What the AI sees" |
| P1-5 | **In-app evaluation page** | ✅ Parser, bad-input and masking checks run live on every load (no AI). The AI half shows the last `run_eval` run (now also written as JSON) with its date, model and prompt version, flagged stale when the prompt has changed, or "not yet run" | `GET /api/eval`, header → "How well it works" |
| P1-6 | **Evidence summary print view** | ✅ Every event, UTC time and all three hashes, with a live chain check; "Print or save as PDF" | Evidence → "Print summary" |

## 4b. Accounts (built after P1, then removed)

Email + password sign-up and sign-in were built and later taken out. The app is a single shared workspace with no accounts, no passwords and no tokens for the owner. The two link tokens remain: the Route A confirmation link and the CA/lawyer pack link. Accounts are back on the roadmap (ROADMAP_AND_LIMITS 2.9).

## 5. Roadmap (Not Built)

Voice-note transcription, screenshot OCR, WhatsApp bot, real SMS OTP, Aadhaar eSign, e-stamp purchase integration, trusted timestamping to anchor the chain, Hindi/Kannada output, accounts and roles, public deployment.

---

## 6. API Surface

| Method | Endpoint | Feature |
|---|---|---|
| `POST` | `/api/conversations` | F1 |
| `POST` | `/api/conversations/{id}/extract` | F2 |
| `GET` | `/api/conversations/{id}/analysis` | F2, F3 |
| `POST` | `/api/agreements/{id}/generate` | F4 |
| `GET` | `/api/agreements/{id}` | F4 |
| `POST` | `/api/agreements/{id}/send` | F5 route A (creates link) |
| `GET` | `/api/confirm/{token}` | F5 route A (read clauses) |
| `POST` | `/api/confirm/{token}` | F5 route A (submit response) |
| `GET` | `/api/agreements/{id}/recap` | F5 route B (message text) |
| `POST` | `/api/agreements/{id}/recap-reply` | F5 route B (attach confirming message) |
| `GET` | `/api/evidence/{id}` | F6 |
| `GET` | `/api/evidence/{id}/verify` | F6 |
| `GET` | `/api/stamp-guidance?state=` | F7 |
| `GET` | `/api/health` | F9 |

---

## 7. Build Plan (Two People, About 34 Hours to P0)

| Window | Person A (backend) | Person B (frontend) |
|---|---|---|
| H0 to H4 | Repo, Docker Compose, DB models, **freeze the stack** | Vite, Tailwind dark theme, routing, shared types |
| H4 to H8 | F1 parser and PII mask, unit tests | Upload screen, chat view |
| H8 to H14 *(check 1)* | F2 extraction on Groq, cache, retry | Terms panel with source highlighting |
| H14 to H20 *(check 2)* | F3 checklist engine, test chats T1 to T8 | Badges, flags, readiness meter |
| H20 to H28 | F4 clause builder, F6 hash chain, F5 backend | Clause tree, print view, confirm page |
| H28 to H34 | F7 data, Gemini fallback, F10 tests and results | F8 panels, route B screens, error states, polish |
| **H34 to H36** | **Record demo video** | **Record demo video** |
| H36 to H48 | P1 items, README, final fixes | Presentation, Q&A and live-drill rehearsal |

Keep the app demonstrable at every progress check.

---

## 8. Demo Script (3 to 4 Minutes)

1. A deal agreed over WhatsApp and later disputed.
2. Upload a sample chat; parsed messages and the masked-data note appear.
3. Terms highlight their source messages; a revised deadline shows its history.
4. Flags: Red on missing payment date, Yellow on "delivery soon", each with a plain reason.
5. Resolve gaps; the agreement appears as a clause tree.
6. Send the friendly message. In a second tab the other party agrees to one clause and suggests a change to another.
7. Show the evidence chain: Verify (green), tamper a record, Verify (red).
8. Close with stamp guidance, the limitations panel and the disclaimer.

---

## 9. Submission and Rules Checklist

- [ ] Demo video submitted by **H36**
- [ ] Repository, README, working demo and supporting files by **H48**
- [ ] README covers: overview, setup, dependencies, technical decisions, known limitations
- [ ] **AI-tool use disclosed**, and every team member can explain the code
- [ ] External libraries, datasets and APIs acknowledged
- [ ] No private data and no paid-service dependency
- [ ] Legal references verified against official sources (see the legal file's checklist)
- [ ] Repo and docs accessible to the evaluation team
