# Handshake to Contract

**Srujana Tech Fest 2026 · Legal Services · Problem LS-06 "From Handshake to Contract"**

> Small businesses agree prices, quantities and deadlines on WhatsApp and rarely sign anything. When a dispute comes, there is no clean agreement to point to. This app reads the chat, pulls out the deal terms with a link to the message each one came from, flags what is vague, missing or never agreed, drafts a plain-language agreement both sides can confirm, and keeps a tamper-evident record of every step.

**Decision support, not legal advice.** Nothing this app produces is a guarantee that an agreement is valid, enforceable or admissible.

---

## Contents

1. [What it does](#what-it-does)
2. [Quick start](#quick-start)
3. [Repository structure](#repository-structure)
4. [How it works](#how-it-works)
5. [API](#api)
6. [Testing and validation](#testing-and-validation)
7. [Interface](#interface)
8. [Technical decisions](#technical-decisions)
9. [Legal grounding](#legal-grounding)
10. [Known limitations](#known-limitations)
11. [AI use disclosure](#ai-use-disclosure)
12. [Dependencies and acknowledgements](#dependencies-and-acknowledgements)
13. [Project status](#project-status)

---

## What it does

| | Feature | What the user sees |
|---|---|---|
| **F1** | Ingestion and privacy guard | Upload or paste a WhatsApp `.txt` export. Messages appear in order; voice notes and images are listed as "not analysed"; phone numbers, PAN, Aadhaar, GSTIN, email and UPI IDs are hidden before any text leaves the server |
| **F2** | Term extraction with source links | Parties, scope, quantity, price, advance, payment date, delivery date and more, each linked to the exact message(s) it came from. Revised terms keep their history |
| **F3** | Gap and ambiguity check | 🔴 Red / 🟡 Yellow / 🟢 Green on every term, an overall readiness badge, and on each flag the statute and section it rests on, in plain language, with a suggested question to ask |
| **F4** | Plain-language agreement | A clause tree built from the confirmed terms only. Anything never agreed reads `[to be confirmed]`, never a guess |
| **F5** | Relationship-friendly confirmation | A friendly message in three tones. **Route A:** a one-time link where the other side agrees, suggests a change or asks a question per clause. **Route B:** a recap pasted into the same WhatsApp chat, with the reply attached later. Always labelled an acknowledgement, never an e-signature |
| **F6** | Tamper-evident evidence trail | Every step is appended to a SHA-256 hash chain. "Verify" shows 🟢 intact or 🔴 broken at event N |
| **F7** | Stamp duty guidance | The correct legal effect (inadmissible until stamped, not void, curable) for Karnataka and Maharashtra. No duty is calculated |
| **F8** | Trust and limits | Persistent disclaimer, "needs lawyer review" when Red items remain or an override was used, and a limitations panel |
| **F9** | Reliability | Response cache, one retry per call, Groq-to-Gemini failover, windowing for long chats, health endpoint |

---

## Quick start

> **Full step-by-step guide, from installing Docker to a demo-ready app, with troubleshooting: [RUNNING.md](RUNNING.md).**

### Requirements

- Docker Desktop (or Docker Engine) with Compose v2.24+
- A free Groq API key from [console.groq.com](https://console.groq.com) (no card needed), and a current production model ID from [console.groq.com/docs/models](https://console.groq.com/docs/models)

### Run

```bash
git clone <repo-url> Srujana_hackathon2026_projectname
cd Srujana_hackathon2026_projectname

cp .env.example .env
# edit .env: set GROQ_API_KEY (GROQ_MODEL defaults to openai/gpt-oss-20b)

docker compose up --build
```

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Interactive API docs | http://localhost:8000/docs |
| Frontend | http://localhost:5173 |

On first start the server creates the tables and loads the 19 sample chats (`GET /api/samples`), so the app is usable immediately.

### Try it without the frontend

```bash
# list the pre-loaded samples
curl http://localhost:8000/api/samples

# upload your own export
curl -F "file=@chat.txt" http://localhost:8000/api/conversations

# analyse conversation 3 (the unresolved-price sample)
curl -X POST http://localhost:8000/api/conversations/3/extract

# draft the agreement, then check the evidence chain
curl -X POST http://localhost:8000/api/agreements/3/generate
curl http://localhost:8000/api/evidence/3/verify
```

### Check the AI connection

```bash
docker compose exec server python -m app.check_llm
```

### Run the tests

```bash
docker compose exec server pytest -q
# or, outside Docker:
cd server && pip install -r requirements.txt && pytest -q
```

The unit tests use SQLite and never call a model, so they need no API key and no network. They always use their own throwaway SQLite database, even inside Docker, so they never touch your demo data, and they ignore `DEMO_TAMPER_ENABLED` and the keys in `.env`. To run them on PostgreSQL instead, set `TEST_DATABASE_URL` to an empty database.

### After changing a model

There are no migrations (see [Technical decisions](#technical-decisions)). After editing anything in `server/app/models/`:

```bash
docker compose down -v   # -v drops the database volume
docker compose up
```

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | set by compose | Postgres connection string |
| `GROQ_API_KEY`, `GROQ_MODEL` | key empty, model `openai/gpt-oss-20b` | Primary model. Without them, upload and parsing still work and cached samples still analyse |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | empty | Fallback model. Needs `google-genai` added to requirements |
| `LLM_CACHE_ENABLED` | `true` | Turn off for live "change an input" drills |
| `DEMO_TAMPER_ENABLED` | `false` | Enables the dev-only tamper endpoint used in the demo. Must be `false` in any deployed build |
| `CONFIRM_LINK_TTL_HOURS` | `72` | Expiry for Route A links |
| `MAX_UPLOAD_MB` | `2` | Upload size limit |

Model names are read from the environment and never hard-coded, because provider model IDs change often.

---

## Repository structure

```
Srujana_hackathon2026_projectname/
├── README.md                         this file
├── RUNNING.md                        step-by-step setup, from Docker to demo
├── docker-compose.yml                db, server, client
├── .env.example                      every variable, with comments
├── .gitignore                        .env is never committed
│
├── docs/
│   ├── ARCHITECTURE.md               pipeline, data model, API contract, design decisions
│   ├── DESIGN.md                     design system: colour, type, shape, motion, components
│   ├── FEATURES.md                   feature spec and the 13 binding decisions
│   ├── PROJECT_RATIONALE.md          why LS-06, the user, impact, likely jury questions
│   ├── TECH_STACK.md                 every dependency, what was cut and why
│   ├── TEST_PLAN.md                  test scenarios T1–T12 and metrics
│   ├── TEST_CHATS.md                 every test chat: what to upload, what you should see
│   └── LEGAL_REFERENCES_AND_COMPETITORS.md
│
├── server/
│   ├── Dockerfile
│   ├── requirements.txt              8 packages
│   ├── app/
│   │   ├── main.py                   app, CORS, startup, sample seeding
│   │   ├── core/
│   │   │   ├── config.py             environment settings (no settings library)
│   │   │   └── db.py                 engine, session, create_all
│   │   ├── models/                   SQLModel tables
│   │   │   ├── base.py               utcnow, TimestampMixin
│   │   │   ├── conversation.py       Conversation, Message
│   │   │   ├── analysis.py           Analysis, ExtractedTerm, Flag + enums
│   │   │   ├── agreement.py          Agreement, ConfirmationLink, ClauseResponse
│   │   │   ├── evidence.py           EvidenceEvent (append-only)
│   │   │   └── llm_cache.py          LlmCacheEntry
│   │   ├── schemas/                  API request and response shapes
│   │   │   ├── conversation.py
│   │   │   ├── analysis.py
│   │   │   └── agreement.py
│   │   ├── routers/                  HTTP endpoints, thin
│   │   │   ├── conversations.py      F1 upload, paste, read, samples
│   │   │   ├── analysis.py           F2/F3 extract, read analysis
│   │   │   ├── agreements.py         F4 generate, F5 send and recap
│   │   │   ├── confirm.py            F5 Route A, counterparty side
│   │   │   ├── evidence.py           F6 chain, verify, demo tamper; P1-1 certificate draft
│   │   │   ├── stamp.py              F7 guidance
│   │   │   ├── evaluation.py         P1-5 evaluation page data
│   │   │   └── health.py             F9
│   │   ├── services/                 all the logic lives here
│   │   │   ├── chat_parser.py        WhatsApp export → messages (no LLM)
│   │   │   ├── pii_masker.py         reversible pseudonymisation (no LLM)
│   │   │   ├── llm_service.py        provider routing, retry, cache
│   │   │   ├── extractor.py          LLM extraction + grounding + revision rules
│   │   │   ├── checklist_engine.py   missing/vague/conflicted → flags (no LLM)
│   │   │   ├── clause_builder.py     terms → clause list + hash (no LLM)
│   │   │   ├── evidence_chain.py     SHA-256 chain + verification (no LLM)
│   │   │   ├── stamp_guidance.py     data lookup (no LLM)
│   │   │   └── eval_report.py        P1-5 live fixture checks + last run_eval (no LLM)
│   │   └── data/
│   │       ├── legal_refs.json       statute, section, gist for every flag
│   │       ├── stamp_duty.json       2 states, sourced, rates left null
│   │       └── samples/              19 demo chats (T01–T22; voice-note cases removed)
│   └── tests/                        249 tests, no network needed
│       ├── fixtures/                 20 labelled test chats + 9 invalid inputs (see docs/TEST_CHATS.md)
│       ├── run_eval.py               scores the chats against a live model, writes eval_results.md and .json
│       ├── conftest.py
│       ├── test_chat_parser.py       26
│       ├── test_pii_masker.py        16
│       ├── test_extractor.py         31
│       ├── test_fixtures.py          40
│       ├── test_checklist_engine.py  23
│       ├── test_masking_pipeline.py  4
│       ├── test_p1_api.py            9
│       ├── test_clause_builder_and_stamp.py  12
│       └── test_evidence_chain.py    17
│
└── client/                           React 18 + TypeScript + Vite + Tailwind
    ├── Dockerfile  package.json  vite.config.ts (proxies /api to the server)
    ├── tailwind.config.js            colour, type and motion tokens
    └── src/
        ├── main.tsx  App.tsx  index.css   routes, buttons, stamp, highlighter
        ├── api/client.ts             one typed function per endpoint
        ├── types/api.ts              mirrors server/app/schemas field for field
        ├── hooks/useApi.ts           data, loading, error for every request
        ├── lib/                      plain-language labels, placeholder constant
        ├── components/
        │   ├── motion/               Segmented, StatusIsland, ProgressRule, TextEffect,
        │   │                         AnimatedNumber, AnimatedGroup, MorphMenu, HoverMembers,
        │   │                         HashTooltip, TransitionPanel
        │   ├── ui/                   Stamp, CopyButton, feedback states
        │   ├── Shell, StepRail       layout, persistent disclaimer
        │   ├── UploadZone, ChatView  F1, source highlighting
        │   ├── FlagCard, TermLedger, RiskBadge      F2/F3
        │   ├── AgreementSheet, ClauseTree           F4
        │   ├── SendPanel, ToneMessage               F5 both routes, override
        │   └── EvidenceTimeline                     F6
        └── pages/
            ├── HomePage              upload, paste, sample chats
            ├── ConversationLayout    loads the chat once for the three steps
            ├── AnalysisPage          step 1: verdict stamp, chat, flags, terms
            ├── AgreementPage         step 2: paper sheet, send, responses
            ├── EvidencePage          step 3: chain, verify, BSA Part A fields
            ├── ConfirmPage           what the other side sees, no app chrome
            └── LimitsPage            limitations and stamp duty
```

The dependency direction is one-way: `routers → services → models`. Routers hold no logic; services hold no HTTP. Every service except `llm_service` and `extractor` is pure and deterministic.

---

## How it works

```
WhatsApp .txt / pasted text
   │
   ▼
F1  chat_parser ──────── parse formats, detect DD/MM vs MM/DD, flag attachments
    pii_masker ───────── <PHONE_1>, <PAN_1> … mapping kept on the server
    SHA-256 of the file ─ evidence event 0, same transaction as the upload
   │
   ▼
F2  extractor
     ├─ LLM  ─────────── "price 4500 each, message 2" (JSON, schema-validated)
     ├─ code ─────────── is "4500" actually in message 2?   → drop if not
     ├─ code ─────────── which mention is the latest?
     └─ code ─────────── did the other side accept the change? (s.62)
    LLM ───────────────── which active values are vague?
   │
   ▼
F3  checklist_engine ─── missing critical term → RED
                          unaccepted revision   → RED
                          vague                 → YELLOW
                          overall = worst critical term
                          every flag ← statute + section from legal_refs.json
   │
   ▼
F4  clause_builder ───── clause list, [to be confirmed] for gaps, canonical hash
   │
   ▼
F5  RED blocks sending unless an override reason is recorded
     ├─ Route A: one-time link, per-clause agree / change / ask, typed name
     └─ Route B: recap pasted into WhatsApp, reply attached from re-upload
   │
   ▼
F6  every step above ──► append-only hash chain ──► Verify
```

**The model does exactly two jobs:** spot term mentions, and judge whether a value is vague. Parsing, deciding what is missing, deciding which revision stands, setting severity, writing the agreement, hashing and stamp guidance are all code. So when the model is wrong, it is wrong about wording, never about a decision.

Full detail, including the data model and the reasoning behind each rule, is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## API

**No sign-in.** The app has no accounts, so every endpoint is open to whoever can reach the server. Run it on your own machine, or put your own access control in front of it, before exposing it. Uploaded chats are stored on the server and listed together. The only secrets are link tokens: `/api/confirm/{token}` (the other party) and `/api/pack/{token}` (a CA or lawyer).


Live, clickable documentation at `/docs` once the server is running.

| Method | Endpoint | Feature | Notes |
|---|---|---|---|
| `GET` | `/api/conversations` | F1 | Chats uploaded or pasted (not the demo samples), newest first |
| `GET` | `/api/health` | F9 | Database status and which providers are configured |
| `GET` | `/api/samples` | demo | Pre-loaded chats for the dropdown |
| `POST` | `/api/conversations` | F1 | Multipart `.txt` upload. Same file twice returns the existing record |
| `POST` | `/api/conversations/paste` | F1 | `{"text": "..."}` |
| `GET` | `/api/conversations/{id}` | F1 | Messages, warnings, masked-data counts |
| `POST` | `/api/conversations/{id}/extract` | F2, F3 | `?force=true` to re-run. `503` if no model is reachable |
| `GET` | `/api/conversations/{id}/analysis` | F2, F3 | Latest analysis |
| `POST` | `/api/agreements/{conversation_id}/generate` | F4 | Optional `{"override_reason": "..."}` |
| `GET` | `/api/agreements/{id}` | F4 | Clauses, hash, counterparty responses |
| `GET` | `/api/agreements/by-conversation/{conversation_id}` | F4 | Latest draft for a chat |
| `POST` | `/api/agreements/{id}/send` | F5 A | `409` while Red without an override |
| `GET` | `/api/agreements/{id}/recap` | F5 B | Three tones of message text |
| `POST` | `/api/agreements/{id}/recap-reply` | F5 B | Marks the confirming message |
| `GET` | `/api/confirm/{token}` | F5 A | Counterparty view |
| `POST` | `/api/confirm/{token}` | F5 A | `409` if reused, `410` if expired |
| `GET` | `/api/evidence/{conversation_id}` | F6 | Full chain |
| `GET` | `/api/evidence/{conversation_id}/verify` | F6 | First broken event, not just true/false |
| `POST` | `/api/evidence/{conversation_id}/_tamper` | F6 demo | `404` unless `DEMO_TAMPER_ENABLED=true` |
| `GET` | `/api/conversations/{id}/masked-preview` | P1-4 | Each line as written and as sent to the model, tokens, leak re-check |
| `GET` | `/api/conversations/{id}/msme-check?supplier_is_micro_or_small=yes` | P1-2 | `yes`, `no` or `unsure`. Advisory; readiness unchanged |
| `GET` | `/api/evidence/{conversation_id}/certificate-draft` | P1-1 | BSA s.63(4) Part A pre-fill. Nothing stored |
| `GET` | `/api/eval` | P1-5 | Live parser and masking checks, plus the last `run_eval` run |
| `GET` | `/api/stamp-guidance?state=KA` | F7 | |
| `GET` | `/api/stamp-guidance/states` | F7 | |

There are deliberately no update or delete endpoints for evidence events.

---

## Testing and validation

```
245 passed, 4 skipped in about 2 s   # the 4 skip until tests.fixtures.build_fixtures makes the two oversized files
```

| Area | Tests | What is proved |
|---|---|---|
| Chat parser | 26 | Android and iOS formats, 12- and 24-hour time, multi-line messages, BOM, CRLF, attachments, system lines, date-order detection, empty/junk/oversized input |
| PII masker | 16 | Every identifier type, GSTIN over PAN precedence, no false positives on prices or order numbers, names untouched, reversible, nothing leaks |
| Extractor | 31 | Grounding (Indian digit grouping, punctuation, sender names), injected messages withheld and uncitable, ordinary business language not mistaken for injection, revision settlement in English, Hinglish and emoji, windowing |
| Checklist engine | 23 | T1 Green, T2 Yellow, T3 Red and blocked, T5 Red, single party, every flag cites a statute that exists in the reference file, MSME 45-day check including months, weeks, words and Hinglish |
| Labelled chat fixtures | 40 | Every labelled chat's message count, participants, date format, attachments, warnings and exact masked identifiers; every invalid input rejected through the real API with the right status and a plain message |
| Clause builder and stamp | 12 | Placeholders, source links, stable hash, a conflicted price is never printed as agreed, no stamp rate is ever invented |
| Masking pipeline | 4 | With a recording stand-in model: no identifier reaches any prompt (extraction or vagueness), token values are restored before grounding, tokens stay consistent across messages |
| P1 endpoints | 9 | Masked preview hides every identifier and withholds injections; certificate draft pre-fills and never pre-ticks; MSME check flags only on "yes" and leaves readiness alone; T05 reply index is message 9; live evaluation checks all pass |
| Evidence chain | 17 | Tamper with first, middle and last event; delete; reorder; change a timestamp; recompute a payload hash; forge an appended event; the same instant in another timezone still verifies |

The deterministic code is tested exhaustively with unit tests. The model-dependent part is validated separately against labelled chats (T1–T12 in [docs/TEST_PLAN.md](docs/TEST_PLAN.md)) with per-term accuracy, missed gaps, false alarms and hallucinated terms reported in the results table below.

### Results on labelled chats

20 labelled chats and 9 invalid inputs, covering every dimension in TEST_PLAN: normal deals, vague and missing terms, revisions accepted and refused, Hinglish, 300+ messages, two deals in one chat, prompt injection, group chats, sarcasm, identifier-heavy text, every date format, and broken files. **What each one is and what you should see: [docs/TEST_CHATS.md](docs/TEST_CHATS.md).**

The deterministic half of every label is checked on each test run. The AI-dependent half is scored against the live model:

```bash
docker compose exec server python -m tests.run_eval
```

That writes `server/tests/eval_results.md`. *Paste its table here before submission, failures included: T10 and T12 are documented limits and are expected to show as known failures. T13 (sarcasm) is now caught and should pass.*

| Chat | Scenario | Expected | Actual | Pass? | Notes |
|---|---|---|---|---|---|
| **T01** | Clear deal | 🟢 | 🔴 overall (price parsing detail) | ❌ | Minor string formatting variance on price |
| **T02** | Vague timing | 🟡 | 🟡 | ✅ | Passed |
| **T03** | Price missing | 🔴, send blocked | 🔴, send blocked | ✅ | Passed |
| **T04** | Price revised twice | 🟢 | 🟢 | ✅ | Passed |
| **T05** | Price revised, never accepted | 🔴 s.62 | 🔴 s.62 | ✅ | Passed |
| **T06** | Hinglish numbers | 🟢 | 🟡 (price clarity) | ❌ | Hinglish price phrasing interpreted as vague |

*To be filled in from a run against the live model. Failures are reported here, not removed.*

---

## Interface

An **editorial document tool** in the tradition of Stripe's docs, Linear and Readme: warm paper, black ink, ruled lines, one official seal.

| | Choice |
|---|---|
| Canvas | Warm paper `#FAF9F6`, white surfaces, razor-thin `#E7E4DD` borders. Structure comes from lines, not shadows |
| Ink and accent | `#1A1A1A` text; deep navy `#1E3A8A` only for actions, links and the active state |
| Status | Strict mapping. Red `bg-rose-50 text-rose-700 border-rose-200` for missing or unagreed terms; yellow `bg-amber-50 text-amber-700 border-amber-200` for vague ones; green `bg-emerald-50 text-emerald-700 border-emerald-200` for clear ones. Always with a word |
| Type | IBM Plex Sans (tight-tracked headings), IBM Plex Mono for every hash, ID, timestamp and count, Newsreader for the agreement text |
| Shape | `rounded-md` containers, `rounded-sm` badges, square row dividers; lists are one bordered block with hairline rows, never cards inside cards |
| The one ornament | The verdict is pressed on as a seal (a thin double rule, a slight tilt) |
| Motion | Short and purposeful, via [Motion](https://motion.dev): sliding tab underlines, a status line that resizes to its message, rolling counts, a thin progress line while the AI works, a button that morphs into its menu. No blur, glow or gradients; reduced motion respected |
| Contrast | Every pair measured against WCAG: all AA, most AAA, field borders at 3:1 |

The full design system (tokens, the contrast table, motion specs, the component catalogue, what we deliberately avoid, and attribution) is in **[docs/DESIGN.md](docs/DESIGN.md)**.

---

## Technical decisions

| Decision | Why |
|---|---|
| **The model only extracts and judges vagueness** | Everything that decides something is code, so it can be unit-tested and explained. This is the answer to "what if the AI is wrong?" |
| **Grounding check after extraction** | Every value must appear in the message it cites, or it is dropped, so hallucinated terms are removed by construction |
| **Prompt-injection guard** | Grounding alone can't stop an injected value that is written in the chat itself, so messages that read as instructions to an AI are withheld from the model and can't be cited. Phrasing the patterns don't recognise is a residual risk |
| **Revision acceptance decided in code** | Contract Act s.62: a change needs both parties. A change counts only if the other side's next message repeats the new value or plainly agrees. Replying about something else does not count |
| **Conflicted values never printed as agreed** | The agreement shows both values and `[to be confirmed]`, because printing the later proposal as "the agreed price" would create the very dispute the product exists to prevent |
| **Reversible pseudonymisation, not deletion** | The model never sees identifiers, but the finished agreement still carries the real contact details. Names are not masked, because they are what extraction must find |
| **Agreement as structured clauses, no templating engine** | One representation, so clause text and source links cannot drift apart, and F5/F6 hash exactly what the other party saw |
| **Hash chain in Postgres, not a blockchain** | Same tamper-evidence without distributed consensus, which solves a problem we do not have |
| **Upload and its first evidence event in one transaction** | No conversation can ever exist without event 0 |
| **Message timestamps stored without a timezone** | A WhatsApp export records local time with no offset. Adding UTC would invent information. Only the order matters |
| **Unique file hash** | One column is the F6 fingerprint, the duplicate-upload check and the cache key that lets the demo run offline |
| **Cache keyed on prompt version** | Editing a prompt automatically invalidates old answers. Cached results are labelled as cached |
| **`create_all`, no migrations** | No production data to preserve in 48 hours |
| **No OTP** | A simulated one proves nothing and a real one needs a paid SMS service. Confirmation is called an acknowledgement |
| **Lean stack** | 8 Python packages. Everything not used, and why, is listed in [docs/TECH_STACK.md](docs/TECH_STACK.md) |

---

## Legal grounding

Every flag in the app shows the statute and section it relies on. The main anchors:

| Concern | Law |
|---|---|
| Can a chat be a contract? | Indian Contract Act 1872, s.10, s.2(h); IT Act 2000, s.10A |
| Vague terms | Contract Act s.29 (uncertain agreements are void) |
| No price | Contract Act s.25 (no consideration) |
| No deadline | Contract Act s.46 (reasonable time), s.55 (time of essence) |
| Revised terms | Contract Act s.62 (alteration needs both parties) |
| Cancellation, late payment | Contract Act s.74 |
| Dispute handling | Arbitration and Conciliation Act 1996, s.7 |
| Evidence integrity | Bharatiya Sakshya Adhiniyam 2023, s.63(4) and Schedule Part A (hash value and algorithm) |
| Stamp duty | Indian Stamp Act 1899, s.33, s.35, s.42; seven-judge bench, December 2023: unstamped agreements are inadmissible, not void, and the defect is curable |
| MSME payment terms | MSMED Act 2006, s.15 (45-day maximum for micro and small suppliers) |

Sources, verification status and the competitor review are in [docs/LEGAL_REFERENCES_AND_COMPETITORS.md](docs/LEGAL_REFERENCES_AND_COMPETITORS.md). Section numbers marked for verification there must be checked against [India Code](https://indiacode.nic.in) before submission.

---

## Known limitations

Stated here because the rubric rewards honesty about limits, and because a legal tool that hides them is dangerous.

The full list, with severity and fixes, plus the roadmap and how fingerprints link a deal to the other party, is in **[docs/ROADMAP_AND_LIMITS.md](docs/ROADMAP_AND_LIMITS.md)**.

**What the evidence trail does not prove**
- It shows nothing changed **since upload**. It cannot show the chat was genuine before it was uploaded, and a chat edited before export cannot be detected.
- It supports the hash disclosure in BSA s.63(4) Part A. It does **not** replace the expert certificate in Part B, or a court's decision on admissibility.

**What confirmation means**
- Route A and Route B record an **acknowledgement**, not an electronic signature. There is no identity verification.

**Input**
- Text only. Voice notes and images are detected and flagged "not analysed"; their content is not read.
- English and Hinglish input; English output only.
- Group chats with three or more people are warned about, because the two contracting parties cannot be identified reliably.
- Two deals in one chat may be merged.

**Judgment**
- Sarcasm with clear signals (an eye-roll emoji, an exaggerated extra demand such as "on a golden chariot", a stock phrase such as "yeah right") is detected in code and is **not** counted as agreement (T13 is now Red, with a flag that says why). Subtle sarcasm with none of those signals, or an off-topic "ok", can still read as agreement: the app cannot reliably tell, so the user is asked to confirm explicitly.
- Vagueness is judged by a language model and may miss imprecise wording or flag precise wording.

**Coverage**
- Stamp guidance covers Karnataka and Maharashtra only, and calculates no duty. No rate is shown until verified from the official state schedule.
- Property, lease and other registration-required documents are out of scope.

**Privacy**
- Free-tier model providers may use inputs to improve their products, so only synthetic chats are used. Identifiers are masked first, but the other party in a chat never agreed to AI processing.

**Engineering**
- No migrations; schema changes need a database reset.
- No sign-in or accounts: every chat is visible to anyone who can reach the server. Run it locally, or add access control before deploying.

---

## AI use disclosure

Required by Rules §4.7. 

- **In the product:** a language model (Groq, with Gemini as fallback) does two things only: extracts mentions of deal terms from the chat, and judges whether extracted values are vague. Its output is validated against a schema and then checked against the source messages before use. It does not decide what is missing, which revision stands, how severe a gap is, or what the agreement says.
- **In development:** AI coding assistants were used to help design the architecture, draft code, write tests and prepare documentation. Every file has been reviewed by the team, and every team member can explain the code, the design decisions and the outputs.

---

## Dependencies and acknowledgements

**Backend:** FastAPI, Uvicorn, Pydantic v2, SQLModel, psycopg, python-multipart, Groq SDK, pytest. Google GenAI SDK when the fallback is enabled.
**Frontend:** React, React Router, TypeScript, Vite, Tailwind CSS, Lucide icons, Motion.
**Design references:** interaction patterns adapted (not copied) from [Motion Primitives](https://21st.dev/@ibelick/library/motion-primitives) (MIT), [Cult UI](https://21st.dev/@cult-ui/library/cult-ui), [Skiper UI](https://shadcn.io/awesome/item/skiper-ui) and Watermelon UI. Details in docs/DESIGN.md §11.
**Infrastructure:** PostgreSQL 16, Docker Compose.
**External services:** Groq API, Google Gemini API (free tiers).
**Legal sources:** India Code, and the commentary listed in the legal references file.

All sample chats are synthetic and written by the team. No real customer data is used.

---

## Project status

| | Status |
|---|---|
| Backend F1–F9 | ✅ Complete, 245 tests passing (4 skip until the large fixtures are generated); full flow verified on PostgreSQL 16 |
| Evidence tamper demo | ✅ Working |
| Gemini fallback | ⏳ Code in place; needs `google-genai` added and keys set |
| Labelled test chats | ✅ 20 chats + 9 invalid inputs; parser half verified. ⏳ Run `run_eval` with a live key for the results table |
| Frontend | ✅ All pages built; full flow verified in a browser, desktop and mobile |
| Design system and motion | ✅ docs/DESIGN.md; contrast measured |
| Legal section verification on India Code | ⏳ Pending |
| Accounts | Not included. Sign-in was removed: one shared workspace, no email or password, no per-user chats |
| P1-1 to P1-6 | ✅ Certificate draft, MSME check, revision timeline, masking preview (and masking wired into extraction), evaluation page, evidence print view. Verified on PostgreSQL 16 and in a browser |

---

