# DESIGN.md: Handshake to Contract

The design system behind the interface: direction, colour, type, shape, motion, components, and where each pattern came from. Tokens live in [`client/tailwind.config.js`](../client/tailwind.config.js) and [`client/src/index.css`](../client/src/index.css); this file explains them.

---

## Contents

1. [Direction](#1-direction)
2. [Principles](#2-principles)
3. [Colour](#3-colour)
4. [Typography](#4-typography)
5. [Shape, borders and space](#5-shape-borders-and-space)
6. [Motion](#6-motion)
7. [Components](#7-components)
8. [Page anatomy](#8-page-anatomy)
9. [Voice and copy](#9-voice-and-copy)
10. [Accessibility](#10-accessibility)
11. [What we deliberately don't do](#11-what-we-deliberately-dont-do)
12. [References and attribution](#12-references-and-attribution)

---

## 1. Direction

> **An editorial document tool for legal and financial work.** The interface should feel like a well-set contract on a clean desk: warm paper, black ink, ruled lines, one official seal, in the tradition of Stripe's docs, Linear and Readme rather than a consumer app.

The product's job is to make an informal chat **defensible**. So the design borrows the vocabulary of documents that hold up: ruled ledgers, citations set off from body text, monospaced reference numbers, a seal on the verdict. Density is a feature. The user is reading evidence, and evidence should fit on the screen.

| Material | In the interface |
|---|---|
| Warm paper | The canvas, `#FAF9F6` |
| White sheet | Panels and the agreement, one hairline border each |
| Black ink | All primary text, `#1A1A1A` |
| Navy ink | Actions and links only, `#1E3A8A` |
| Ruled lines | Dividers between rows instead of separate cards |
| Typewritten references | Mono for hashes, IDs, timestamps, counts, model names |
| The seal | The verdict: the single ornament |

---

## 2. Principles

1. **Every claim can be traced.** Anything the app asserts (a term, a flag, a hash) is one click from the message, statute or event it rests on.
2. **Borders, not shadows.** Structure comes from razor-thin lines. Shadows exist only on things that genuinely float: menus, tooltips, the status line.
3. **One ornament.** The verdict seal is the only decorative element. Everything else is type, rules and space.
4. **Status colour is reserved.** Rose, amber and emerald mean exactly one thing each and appear nowhere else.
5. **Machine-made text looks machine-made.** If a computer generated it (a hash, an ID, a timestamp, a count), it is set in mono. If a person wrote it, it is set in sans or serif.

---

## 3. Colour

### 3.1 Neutrals

| Token | Hex | Role |
|---|---|---|
| `canvas` | `#FAF9F6` | The page: warm paper |
| `surface` | `#FFFFFF` | Panels, the agreement sheet, inputs |
| `sunken` | `#F4F2EE` | Table heads, wells, the chat background |
| `hover` | `#F5F3EF` | Row hover and selection |
| `line` | `#E7E4DD` | Hairline borders and dividers |
| `line.strong` | `#D5D1C7` | Secondary button borders, the dashed drop zone |
| `line.input` | `#8E887F` | Text-field borders: 3:1 on white, as WCAG 1.4.11 requires |

### 3.2 Ink

| Token | Hex | Role |
|---|---|---|
| `fg` | `#1A1A1A` | Primary text and headings |
| `fg.muted` | `#57534E` | Secondary text, descriptions |
| `fg.faint` | `#6F6A64` | Metadata, captions, mono labels |

### 3.3 Brand: navy

Built around `#1E3A8A` (`navy.600`). Navy marks **what you can act on**: primary buttons, links, the active step, the selected tab. Nothing decorative.

| Token | Hex | Role |
|---|---|---|
| `navy.50` | `#EFF3FB` | Your own chat messages; the "ink" seal |
| `navy.100` | `#DCE5F6` | The source highlighter; focus ring wash |
| `navy.200` | `#B9C8EC` | Summary rule on the agreement |
| `navy.300`–`400` | `#8EA5DB`, `#5B79C2` | Hover borders, selected message outline |
| `navy.500` | `#3355A6` | Focus outline |
| `navy.600` | `#1E3A8A` | **Brand.** Primary buttons, links, the active step |
| `navy.700` | `#192F70` | Button hover and border; sender name on your own messages |
| `navy.800`–`900` | `#142558`, `#0F1B40` | Pressed state |

### 3.4 Status: strict domain mapping

Tailwind's own palettes, always as these exact class sets (exported as `STATUS_CLASSES` from `components/RiskBadge.tsx`):

| Status | Means | Classes | Words it always carries |
|---|---|---|---|
| 🔴 Red | A critical term is missing, or a change was never agreed | `bg-rose-50 text-rose-700 border-rose-200` | Fix first, Missing, Not agreed, Broken |
| 🟡 Yellow | A term is present but vague or ambiguous | `bg-amber-50 text-amber-700 border-amber-200` | Worth clarifying, Vague |
| 🟢 Green | A term is clear, or the record verified | `bg-emerald-50 text-emerald-700 border-emerald-200` | Clear, Ready to confirm, Intact |

Rules:
- These three colours are used for status and nothing else.
- The highlighter that marks a source message is **navy**, not yellow, so yellow never means anything but "vague".
- A count of zero drops to neutral, so "0 to fix first" doesn't draw the eye in red.
- The status line (top centre) never contradicts the page. A check that finds gaps reports in the neutral tone, because the colour belongs to the seal.

### 3.5 Measured contrast

Computed with the WCAG 2.1 formula, not estimated.

| Pair | Ratio | Level |
|---|---|---|
| `fg` on `canvas` | 16.53:1 | AAA |
| `fg` on `surface` | 17.40:1 | AAA |
| `fg.muted` on `canvas` | 7.25:1 | AAA |
| `fg.muted` on `sunken` | 6.82:1 | AA |
| `fg.faint` on `canvas` | 5.09:1 | AA |
| `fg.faint` on `surface` | 5.36:1 | AA |
| `fg.faint` on `sunken` | 4.79:1 | AA |
| white on `navy.600` (primary button) | 10.36:1 | AAA |
| white on `navy.700` (button hover) | 12.49:1 | AAA |
| `navy.600` on `surface` (links) | 10.36:1 | AAA |
| `navy.700` on `navy.50` | 11.23:1 | AAA |
| `rose.700` on `rose.50` | 5.72:1 | AA |
| `amber.700` on `amber.50` | 4.84:1 | AA |
| `emerald.700` on `emerald.50` | 5.21:1 | AA |
| `rose.800` on `rose.50` (error text) | 7.30:1 | AAA |
| white on `rose.700` (danger button) | 6.29:1 | AA |
| `line.input` on `surface` (field border) | 3.51:1 | Meets 1.4.11 |

---

## 4. Typography

### 4.1 Families

| Family | Role | Why |
|---|---|---|
| **IBM Plex Sans** | The interface: headings (with tight tracking), labels, body | Engineered and plain-spoken, with a legal and financial heritage; reads well at small sizes |
| **IBM Plex Mono** | Hashes, IDs, timestamps, message numbers, counts, model names, clause numbers | The same family as the sans, so mono metadata sits in a line of sans text without clashing |
| **Newsreader** | The agreement's clauses, suggested questions, the stamp-duty statement | The agreement is a document, so it reads as one |

### 4.2 Scale

A dense document scale, set in `tailwind.config.js`.

| Token | Size / line height | Used for |
|---|---|---|
| `2xs` | 11 / 16 px | Mono metadata (`.meta`) |
| `xs` | 12 / 17.6 px | Badges, captions, table heads |
| `sm` | 13 / 20.8 px | UI body, rows, buttons |
| `base` | 15 / 24.8 px | Reading text, the verdict line |
| `lg` | 18 / 26.4 px | Lead paragraph, section titles on home |
| `xl` | 22 / 29.6 px | Page titles |
| `2xl` | 28 / 35.2 px | Agreement title |
| `3xl` / `4xl` | 36 / 46 px | Home headline, mobile / desktop |

### 4.3 Rules

- **Headings:** sans, semibold, `tracking-tight`, sentence case.
- **Capitals appear in one place only:** inside the seal, because seals are lettered that way. No all-caps labels, no eyebrow text above headings.
- **Section headings** above a panel use `.section-title`: 13 px semibold, black, nothing else.
- **Mono is for machine-made values only.** Never for a person's words, never for a label like "Status".
- **Line length** stays under about 75 characters; the agreement sheet is capped at 44 rem.

---

## 5. Shape, borders and space

### 5.1 Radius

| Element | Radius | Class |
|---|---|---|
| Panels, cards, inputs, buttons, menus | 6 px | `rounded-md` |
| Status badges, step numbers, seal | 2 px | `rounded-sm` |
| Dividers, table rows, list rows | 0 | (none) |
| Avatars | full | `rounded-full` (people are round) |

### 5.2 Borders and elevation

| Need | Do this |
|---|---|
| A container | `border border-line` on `surface` |
| Separate items inside it | `divide-y divide-line`, never a card per item |
| Something that floats (menu, tooltip, status line) | `border border-line` plus `shadow-float`, which is the only shadow token |
| Emphasise a selected row | `bg-hover`, or a 2 px coloured left edge for severity |
| A citation or a summary | A 2 px left rule (`border-l-2`), like a blockquote in a printed document |

### 5.3 Space

A 4 px base. Panels pad 20 px; rows pad 14 to 16 px vertically; page sections sit 24 px apart, and 64 to 80 px apart on the home page. The page width is capped at `max-w-6xl` (72 rem), so rows stay readable on wide screens.

---

## 6. Motion

Motion explains a change; it never decorates. Nothing uses blur, glow or a gradient.

### 6.1 Rules

- **It answers an action or shows work.** Selecting, switching, confirming, waiting.
- **One unprompted moment:** the home headline rises in word by word, once, in about half a second.
- **Short and quiet:** 140 to 400 ms, small distances (2 to 8 px), springs with little bounce (0.12 to 0.2).
- **Reduced motion** is respected twice: `MotionConfig reducedMotion="user"` wraps the app, and a CSS media query shortens every CSS animation.

### 6.2 Catalogue

| Moment | Trigger | Component | Pattern from |
|---|---|---|---|
| The verdict seal pressing on | A result arrives | `ui/Stamp.tsx` | Original |
| Highlighter across a source message | Select a term or flag | `ChatView.tsx`, `.marked` | Original |
| Evidence rows and rail drawing in | Evidence page opens | `EvidenceTimeline.tsx` | Original |
| Thin progress line along a panel's top | AI reading, chain verifying | `motion/ProgressRule.tsx` | Linear-style indeterminate bar |
| Home headline rising in | Page load, once | `motion/Text.tsx` | Motion Primitives, Text Effect |
| Underline or pill sliding to the choice | Switch tabs, tone, state | `motion/Segmented.tsx` | Motion Primitives, Animated Background |
| Step box sliding | Change step | `StepRail.tsx` | Motion Primitives, Animated Background |
| Tab content swapping | Switch tabs | `motion/TransitionPanel.tsx` | Motion Primitives, Transition Panel |
| Counts rolling to their value | Results arrive | `motion/AnimatedNumber.tsx` | Motion Primitives, Animated Number |
| Findings arriving in order | Results arrive | `motion/AnimatedGroup.tsx` | Motion Primitives, Animated Group |
| Status line resizing to its message | Any action | `motion/StatusIsland.tsx` | Cult UI and Skiper UI, Dynamic Island |
| Participant initials fanning out | Hover the avatars | `motion/HoverMembers.tsx` | Skiper UI, Hover Members |
| Full hash on hover | Hover or focus a hash | `motion/HashTooltip.tsx` | Skiper UI, Vercel-style tooltip |
| A button growing into its menu | Open "More" | `motion/MorphMenu.tsx` | Watermelon UI, animated menus |

---

## 7. Components

### 7.1 Buttons

| Variant | Class | Look | Use |
|---|---|---|---|
| Primary | `btn btn-primary` | Navy fill, darker navy border, a 1 px inner highlight on top | The one main action in a region |
| Secondary | `btn btn-secondary` | White, `line.strong` border; hover fills `hover` | Everything else |
| Danger | `btn btn-danger` | Rose fill | Proceeding past a Red flag, which gets recorded |
| Ghost | `btn btn-ghost` | Text only | Tertiary, low-stakes |
| Small | `+ btn-sm` | 28 px tall, 12 px text | Inline actions such as Copy |

All buttons are 36 px tall (28 for small), `rounded-md`, and drop 1 px when pressed. Labels say what happens ("Draft the agreement", "Check integrity"), never "Submit".

### 7.2 Status badge (`RiskBadge`)

`rounded-sm`, a 1 px border, 12 px medium text, a 12 px icon, with classes from section 3.4. The word is mandatory in practice: "Fix first", "Vague", "Clear".

### 7.3 The seal (`ui/Stamp`)

A capitalised mark in a 3 px **double** rule, tilted 2°, on a 70% tint of its status colour, with a mono second line ("5 FINDINGS", "AT EVENT 1"). It presses on with a small overshoot (380 ms). Its `pressKey` replays the press when the result changes, so a new verdict lands as a new seal.

| Tone | Text | Where |
|---|---|---|
| Rose | Gaps to fix, Broken | Verdict, verification |
| Amber | Clarify first | Verdict |
| Emerald | Ready to confirm, Intact | Verdict, verification |
| Navy | Confirmed, Recorded | Agreement sheet, the other side's page |

### 7.4 Rows and lists

| Component | Structure |
|---|---|
| `FlagCard` | A **row** in one bordered list: a 2 px left edge in its status colour, then the badge with its mono term label, title, explanation and a "Show in chat" link. The statute is set as a blockquote citation, with the section in mono. The suggested question is in serif italic, with a Copy button |
| `TermLedger` | A real table: a sunken header, hairline rows, a mono source column. Earlier values are struck through and marked "(change accepted)" or "(change not accepted)" |
| `EvidenceTimeline` | One panel with divided rows. Square mono-numbered nodes on a hairline rail. From the first broken event onward, nodes and rail turn rose, and the first broken row gets a rose wash |
| `ClauseTree` | A recursive outline: agreement, then clause and status dot, then the source message with a mono `#n` |
| Sample list (home) | Ruled rows: mono code (`T01`), title and hint, mono message count, arrow |
| `RevisionTimeline` (P1-3) | A hairline rail with round nodes: earlier values struck through in faint ink, the latest node filled navy. It ends in the judged reply, boxed in the strict emerald or rose status classes, quoting the message and saying in one line why it does or doesn't count. The s.62 citation sits under it in small text |
| `MsmeCheck` (P1-2) | A question, three small buttons (`aria-pressed`, the chosen one navy), then the same `FlagCard` row used everywhere and a sunken strip with the term and the days in mono |
| Masking preview (P1-4) | Two ruled columns, "In the chat" and "Sent to the AI". Hidden values get an amber highlighter on the left; tokens are mono navy chips on the right. Withheld injection lines read in rose italics. The verdict is the same seal: **NOTHING LEAKS** in green |
| Certificate draft (P1-1) | Printed like the agreement: one white sheet, an amber "draft" label, serif title, ruled field rows with the source of each value in mono underneath, plain inputs, unticked boxes, two signature rules. Prints alone |
| Evidence summary (P1-6) | A print sheet with a fixed-layout table: mono sequence, event and UTC time, then payload, prev and chain hashes stacked in mono at three ink weights. Rows never split across pages |
| Evaluation page (P1-5) | Collapsible ruled groups with a large mono `22/22` score and a status badge; a failing group opens itself. The AI half is a stat row plus a table, or a "not yet run" panel with the command and a Copy button |

### 7.5 Agreement sheet

A white sheet with one hairline border on the paper canvas. No shadow: it's a document, not a card. A mono header line ("Version 2 / drafted … / ID 2"), the summary set off by a 2 px navy rule, clauses as ruled rows with mono `01`, `02` numbers and serif body text. A gap renders as a rose "to be confirmed" blank with a dashed underline. Prints exactly as shown.

### 7.6 Status line (`StatusIsland`)

One white, bordered pill under the header, the only floating notice in the app. `busy(text)` shows a spinner until cleared; `notify(kind, text, detail?)` shows a result for 2.6 s, with the detail in mono. It resizes to its message; messages never stack.

### 7.7 Segmented control (`Segmented`)

- `variant="tabs"`: text tabs over a hairline, with a 2 px navy underline that slides. Used for upload mode and send route.
- `variant="segment"`: a sunken track with a white, bordered pill that slides. Used for message tone and stamp-duty state.

---

## 8. Page anatomy

The check page, where most of the demo happens:

```
┌────────────────────────────────────────────────────────────────────┐
│ ▣ Handshake to contract                     New chat   Limits      │  48px, hairline below
├────────────────────────────────────────────────────────────────────┤
│                    [ ⓘ Check complete  5 findings ]   status line  │
│ ← All chats                                                        │
│ (RT)(SF) Unresolved conflict              [1 Check]─2 Agreement─3  │
│          Ravi Traders and Sunrise…  10 messages  ID 3              │
│ ──────────────────────────────────────────────────────────────────│
│ ┌──────────────┬───────────────────────────────────┬────────────┐ │
│ │╔════════════╗│ A key term is missing or was…     │[Draft the  │ │
│ │║GAPS TO FIX ║│ [2 to fix first][3 worth…][5 clear]│ agreement] │ │
│ │║ 5 FINDINGS ║│ model  openai/gpt-oss-20b         │[Check again│ │
│ │╚════════════╝│                                   │            │ │
│ └──────────────┴───────────────────────────────────┴────────────┘ │
│ The chat                       What needs attention               │
│ ┌──────────────────────┐       ┌──────────────────────────────┐   │
│ │ Ravi       #0 14 Sept│       │▌[Fix first] Price            │   │
│ │ Need 45 chairs…      │       │▌The price was changed and…   │   │
│ │      Suresh #1 …     │       │▌ │ Indian Contract Act, s.62 │   │
│ │ ▓ #6 can you do 4200 │◄──────│▌ "Which rate are we both…"   │   │
│ │   (navy highlighter) │       ├──────────────────────────────┤   │
│ └──────────────────────┘       │▌[Fix first] Payment due …    │   │
│  sticky on desktop             └──────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

- Left-aligned throughout. Only the seal and empty states are centred.
- Under 1024 px everything stacks into one column; under 640 px the wordmark and navigation shorten. No page scrolls sideways at 390 px; this was measured on every page.

---

## 9. Voice and copy

| Do | Don't |
|---|---|
| "No agreement on the payment date" | "PAYMENT_DUE: MISSING" |
| "Draft the agreement" | "Submit" / "Generate" |
| "This link has already been used, so it can't be answered again." | "Error 409" |
| "Not analysed: add any terms it carries yourself." | "Unsupported media type" |
| "Decision support, not legal advice." | "AI-powered legal assistant" |

- Errors say what happened and what to do. They don't apologise.
- Empty states invite the next action ("This chat hasn't been checked yet", then the button).
- The other party's page never says "contract": "Just checking we're on the same page."

---

## 10. Accessibility

- Every text pair passes WCAG AA, most AAA (section 3.5). Field borders meet the 3:1 non-text rule.
- Status is never colour alone: every badge, flag and seal carries words.
- Everything is reachable by keyboard and shows a 2 px navy focus outline.
- Segmented controls are `radiogroup`s with `aria-checked`; the menu uses `role="menu"`; tooltips use `role="tooltip"` and `aria-describedby`; the progress line is a `progressbar`.
- The status line is `aria-live="polite"`.
- `prefers-reduced-motion` turns off every animation.
- The agreement, the certificate draft and the evidence summary print alone; navigation and panels are hidden by `.no-print`.

---

## 11. What we deliberately don't do

These are the commonest signs of a generated interface, and each one is checked for.

| Not used | Instead |
|---|---|
| Gradient fills or washes (`from-purple-600 to-indigo-600`) | Flat colour. The page is plain paper |
| Glassmorphism, `backdrop-blur` | Solid surfaces; the header is solid `canvas` with a hairline |
| Heavy drop shadows (`shadow-xl`) | `border border-line`. One small `shadow-float` for floating elements only |
| One large radius on everything (`rounded-2xl`) | 6 px for containers, 2 px for badges, square rows |
| Cards nested inside cards | One bordered container with divided rows |
| Glow effects, blur transitions, shimmer text | A thin progress line; short opacity-and-position transitions |
| All-caps eyebrow labels above headings | A plain sentence-case section title |
| Status colours used for decoration | Rose, amber and emerald for status only; navy for actions only |

---

## 12. References and attribution

The visual direction follows the editorial restraint of **Stripe's documentation**, **Linear** and **Readme**: hairline structure, dense rows, mono metadata, a single accent. No code or assets were taken from them.

The motion components were written for this project, taking their **patterns** from four open component libraries. No source code was copied; each file names the pattern it follows.

| Library | What we took | Licence note |
|---|---|---|
| [Motion Primitives](https://21st.dev/@ibelick/library/motion-primitives) by Julien Thibeaut | Animated Background, Text Effect, Animated Number, Animated Group, Transition Panel | MIT |
| [Cult UI](https://21st.dev/@cult-ui/library/cult-ui) | Dynamic Island | Check before reusing code |
| [Skiper UI](https://shadcn.io/awesome/item/skiper-ui) | Hover Members, Vercel-style tooltip, Dynamic Island | Free and paid tiers; check before reusing code |
| [Watermelon UI](https://21st.dev/@quantvansh/components/watermelon-animated-workspace-actions-menu.md) | The morph between a trigger and its menu | Check before reusing code |

All of it runs on [Motion](https://motion.dev) (`motion@11.18.2`, imported from `motion/react`) and Tailwind CSS. The seal, the highlighter and the evidence ledger are original to this project.
