# TEST_PLAN.md: LS-06 Validation Plan

**Why this matters:** Validation and robustness is 10 points, and the rubric also lets judges ask you to change an input live. Spread matters more than count: **8 to 12 well-chosen chats** plus **30 to 50 small unit tests** beat dozens of similar chats.

Companion: `FEATURES.md` (v3, F10), `TECH_STACK.md`.

---

## 1. Two Kinds of Tests

| Layer | Examples | Method | Volume |
|---|---|---|---|
| **Deterministic code** | Chat parser, PII masker, checklist engine, hash chain, stamp lookup, token handling | `pytest` unit tests, near-exhaustive | 30 to 50 small tests |
| **LLM-dependent** | Term extraction, vagueness judgment | Labelled chat fixtures, scored by metrics, run once and cached | 8 to 12 chats |

Don't judge the model with unit tests, and don't judge the parser with chats.

## 2. Dimensions to Cover

Every row should appear in at least one chat. One chat can cover several rows.

| Dimension | Values |
|---|---|
| Completeness | All critical terms present, one missing, several missing |
| Clarity | Clear, vague, mixed |
| Revisions | None, one, several, conflicting with no final value |
| Language | English, Hinglish, numbers in words or mixed ("do hazaar", "50k") |
| Format | 12-hour and 24-hour timestamps, multi-line messages, emojis, system lines |
| Length | Short (about 10 messages), medium (about 80), long (300+) |
| Participants | Two people; one group chat as a known limitation |
| Attachments | Voice-note or image placeholder, especially one carrying the deadline |
| Noise | Casual chatter around the deal; two deals in one chat |
| Deal type | Goods supply, a service, a custom or repair order |
| Adversarial | Message instructing the AI, sarcasm, PII-heavy text |
| Invalid input | Empty, junk, wrong type, oversized |

## 3. Suggested Mix

| Share | Type | Purpose |
|---|---|---|
| about 35% | Normal, realistic deals | Prove it works |
| about 30% | Edge cases: vague, revised, Hinglish, long, voice note | Prove robustness |
| about 15% | Hard or adversarial: conflicts, sarcasm, injection, multi-deal | Show honest limits |
| about 20% | Invalid or junk input | Prove safe failure |

---

## 4. Chat Scenarios (Minimum T1 to T8, Target T1 to T12)

| # | Scenario | Expected behaviour |
|---|---|---|
| T1 | Clear deal: price, scope, due date and delivery all stated | 🟢 overall; agreement fully populated |
| T2 | Vague timing ("will send soon", "pay later") | 🟡 on timeline and payment |
| T3 | Price missing | 🔴; sending blocked (D8) |
| T4 | Price revised twice | Latest active; two revisions in history |
| T5 | Conflicting values with no clear final | 🔴 "unresolved conflict" |
| T6 | Hinglish chat with numbers in words | Terms extracted correctly or marked vague, never invented |
| T7 | Voice-note placeholder carries the deadline | Flagged "not analysed"; deadline shown as missing |
| T8 | Empty, junk or oversized file | Friendly error, no crash |
| T9 | Long chat (300+ messages) | Windowing works, no truncation, no duplicate terms |
| T10 | Two deals in one chat | Flags ambiguity, or extracts the wrong deal and says so (documented failure) |
| T11 | A chat message saying "ignore previous instructions…" | Treated as plain text, not obeyed |
| T12 | Group chat with 3 or more people | Parties flagged as unclear (documented limitation) |

**Honest failure to show (rubric requires one):** a chat where "ok" or "done" refers to something else, or is sarcastic with no clear signal (no emoji, no stock phrase, no exaggeration). The app cannot reliably tell, so it routes to explicit confirmation. Sarcasm WITH clear signals is caught (T13). Also state that a chat edited *before* upload cannot be detected.

### Boundary pairs (most bugs sit at the edges)
- "Pay within 30 days of delivery" (clear) versus "pay later" (vague) versus no payment mention (missing)
- A price revised once versus revised back to the original value
- A deadline in a text message versus the same deadline only in a voice-note placeholder

---

## 5. Fixture Format

```
server/tests/fixtures/chats/T04_price_revised_twice.txt
server/tests/fixtures/chats/T04_price_revised_twice.expected.json
```

```json
{
  "scenario": "T04 price revised twice",
  "expected_terms": {
    "price": {"status": "clear", "active_value": "52000", "revision_count": 2},
    "payment_due": {"status": "vague"}
  },
  "expected_overall": "yellow",
  "must_not_contain": ["delivery_penalty"]
}
```

**Label every chat before running it**, so you don't bend labels to fit the output.

---

## 6. Metrics to Report

| Metric | How |
|---|---|
| Extraction accuracy **per term type** | Compare to labels; report each term separately, since a single overall number hides weak spots |
| **Missed gaps** (false negatives) | Track separately, because a missed gap is worse than a false alarm |
| **False alarms** (false positives) | Count flags on clear terms |
| **Hallucinated terms** | Terms with no valid source message. Target: zero |
| Status correctness | Does Red, Yellow or Green match the label? |
| Source-link correctness | Does the highlighted message contain the value? |

## 7. Non-Chat Tests

| Area | Cases |
|---|---|
| **Hash chain** | Tamper with the first, middle and last event; delete an event; reorder two events; empty chain; verify intact chain |
| **Privacy** | Assert the text sent to the LLM contains no phone, Aadhaar, PAN or email; masker handles Indian formats and false positives like order numbers |
| **Reliability** | Invalid JSON from the model, timeout, rate-limit error triggering fallback, cache hit, cache disabled |
| **Stamp guidance** | Supported state, unsupported state, missing document type |
| **Confirmation (route A)** | Expired token, reused token, unknown token, missing typed name, double-click on submit, change request reopens only that clause |
| **Recap (route B)** | Updated export with no reply, reply attached to the wrong message, same file uploaded twice |
| **API and UI** | Oversized file, wrong type, empty result states, long text wrapping, keyboard use, text labels beside colours |

---

## 8. Live "Change an Input" Drills

Judges may ask you to change an input or test a scenario live. Rehearse these with the **cache switched off** (D13):

1. Delete the price from a clear chat: 🟢 becomes 🔴, and sending is blocked.
2. Add a revised deadline: the revision history updates.
3. Paste a chat in a different style (Hinglish or a different timestamp format).
4. Edit one stored event and run Verify: it must fail.
5. Open an already-used confirmation link: it must be rejected.

Keep a backup recording in case the network or an API fails.

---

## 9. Results Table for the README

| Chat | Scenario | Expected | Actual | Pass? | Notes |
|---|---|---|---|---|---|
| T01 | Clear deal | 🟢 | | | |

Include the failures. The rubric says honest limitations don't hurt a score, while concealed failures do.

## 10. Time Budget

About **3 hours** in total. Write unit tests as you build each module. Write the 8 core chats in the **first 12 hours**, so you can use them while developing and not only at the end.
