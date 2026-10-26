/*
 * Mirrors server/app/schemas. Field names stay snake_case on purpose, so the
 * two sides can be compared by eye (docs/ARCHITECTURE.md section 9).
 * If you change a field here, change it in the Pydantic schema too.
 */

export type Severity = "red" | "yellow" | "green";
export type TermStatus = "clear" | "vague" | "missing" | "conflicted";
export type RevisionState = "none" | "settled" | "unresolved";
export type MessageKind = "text" | "attachment" | "system" | "deleted";
export type DateOrder = "day_first" | "month_first" | "ambiguous";

export type TermType =
  | "party"
  | "scope"
  | "quantity"
  | "price"
  | "advance"
  | "payment_due"
  | "delivery_date"
  | "acceptance"
  | "cancellation"
  | "dispute";

// ---------- F1 -------------------------------------------------------------

export interface Message {
  /** 0-based position. Every source_message_ids refers to these. */
  index: number;
  /** ISO string with no timezone: the export records none. */
  timestamp: string;
  sender: string | null;
  body: string;
  kind: MessageKind;
}

export interface MaskedNote {
  counts: Record<string, number>;
  total: number;
}

export interface Conversation {
  id: number;
  original_filename: string;
  content_sha256: string;
  byte_size: number;
  created_at: string;
  date_order: DateOrder;
  participants: string[];
  warnings: string[];
  attachment_indices: number[];
  is_sample: boolean;
  sample_label: string | null;
  message_count: number;
  messages: Message[];
  masked: MaskedNote;
  deduplicated: boolean;
}

export interface SampleSummary {
  id: number;
  label: string;
  message_count: number;
  participants: string[];
  created_at: string | null;
}

// ---------- F2 / F3 --------------------------------------------------------

export interface Revision {
  value: string;
  source_message_ids: number[];
}

export interface Term {
  type: TermType;
  value: string | null;
  status: TermStatus;
  confidence: number;
  source_message_ids: number[];
  revision_state: RevisionState;
  revision_history: Revision[];
  /** P1-3: the other party's first text reply after the active value. */
  response_message_index: number | null;
}

export interface Flag {
  term_type: TermType;
  severity: Severity;
  title: string;
  why_it_matters: string;
  statute: string;
  section: string;
  statute_gist: string;
  suggested_question: string | null;
  source_message_ids: number[];
}

export interface DroppedMention {
  type: string;
  value: string;
  reason: string;
  cited: number[];
}

export interface Analysis {
  id: number;
  conversation_id: number;
  created_at: string;
  readiness: Severity;
  can_send: boolean;
  missing_critical: TermType[];
  terms: Term[];
  flags: Flag[];
  model_used: string;
  prompt_version: string;
  from_cache: boolean;
  dropped_ungrounded: DroppedMention[];
  /** Term types the AI missed and the pattern rules found (fresh runs only). */
  filled_by_rules: string[];
}

// ---------- F4 / F5 --------------------------------------------------------

export type AgreementStatus = "draft" | "sent" | "changes_requested" | "confirmed";
export type ResponseAction = "agree" | "suggest_change" | "ask_question";

export interface Clause {
  id: string;
  heading: string;
  body: string;
  status: string;
  source_message_ids: number[];
  is_placeholder: boolean;
  is_pending?: boolean;
  proposed_value?: string | null;
}

export interface ProposalResult {
  status: string;
  clause_id: string;
  proposed_value: string;
  whatsapp_snippet: string;
  notice: string;
}

export interface ClauseResponse {
  clause_id: string;
  action: ResponseAction;
  comment: string | null;
  typed_name: string;
  responded_at: string;
}

export interface Agreement {
  id: number;
  conversation_id: number;
  version: number;
  status: AgreementStatus;
  created_at: string;
  summary: string;
  notice: string;
  clauses: Clause[];
  clauses_hash: string;
  override_reason: string | null;
  responses: ClauseResponse[];
}

export interface Tone {
  key: "warm" | "neutral" | "formal";
  label: string;
  message: string;
}

export interface SendResponse {
  agreement_id: number;
  status: AgreementStatus;
  tones: Tone[];
  confirm_url: string;
  expires_at: string;
  notice: string;
}

export interface RecapResponse {
  agreement_id: number;
  tones: Tone[];
  notice: string;
}

export interface ConfirmView {
  agreement_id: number;
  clauses: Clause[];
  clauses_hash: string;
  already_used: boolean;
  expired: boolean;
  notice: string;
}

export interface ClauseAnswer {
  clause_id: string;
  action: ResponseAction;
  comment: string | null;
  /** Only when answering the owner's pending proposal on this clause. */
  proposal?: "accept" | "reject" | null;
}

// ---------- F6 -------------------------------------------------------------

export type EventType =
  | "upload"
  | "extraction"
  | "agreement_generated"
  | "agreement_sent"
  | "counterparty_response"
  | "recap_reply"
  | "override_acknowledged";

export interface EvidenceEvent {
  sequence: number;
  type: EventType;
  occurred_at: string;
  payload: Record<string, unknown>;
  payload_sha256: string;
  prev_hash: string;
  chain_hash: string;
}

export interface EvidenceChain {
  conversation_id: number;
  algorithm: string;
  events: EvidenceEvent[];
  limitation: string;
}

export interface Verification {
  intact: boolean;
  checked: number;
  broken_at_sequence: number | null;
  reason: string | null;
  limitation: string;
}

// ---------- F7 / F9 --------------------------------------------------------

export interface StampPoint {
  text: string;
  statute: string;
  section: string;
}

export interface StampGuidance {
  supported: boolean;
  state_code: string;
  state_name: string | null;
  state_act: string | null;
  authority: string | null;
  source_url: string | null;
  last_verified: string | null;
  duty_rate: string | null;
  rate_note: string | null;
  estamping_available: boolean;
  headline: string;
  plain_language: string;
  points: StampPoint[];
  checklist: string[];
  message: string | null;
}

export interface StateOption {
  code: string;
  name: string;
}

export interface Health {
  status: "ok" | "degraded";
  database: boolean;
  groq_configured: boolean;
  gemini_configured: boolean;
  llm_cache_enabled: boolean;
  demo_tamper_enabled: boolean;
}

// ---------- P1 -------------------------------------------------------------

/** P1-4: what the chat says next to what the model is shown. */
export interface MaskedLine {
  index: number;
  sender: string | null;
  original: string;
  sent: string | null;
  masked: boolean;
  withheld: boolean;
}

export interface MaskedToken {
  token: string;
  label: string;
  occurrences: number;
}

export interface MaskedPreview {
  conversation_id: number;
  prompt_version: string;
  counts: Record<string, number>;
  total: number;
  tokens: MaskedToken[];
  lines: MaskedLine[];
  leak_check_passed: boolean;
}

/** P1-2. */
export type SupplierAnswer = "yes" | "no" | "unsure";

export interface MsmeCheck {
  answer: SupplierAnswer;
  payment_term: string | null;
  period_days: number | null;
  limit_days: number;
  exceeds_limit: boolean;
  flag: Flag | null;
  note: string;
}

/** P1-1. */
export interface CertificateField {
  label: string;
  value: string;
  source: string;
}

export interface CertificateDraft {
  conversation_id: number;
  title: string;
  status: string;
  record: CertificateField[];
  integrity: CertificateField[];
  party_fields: string[];
  statements: { text: string; affirmed: boolean }[];
  chain_intact: boolean;
  cautions: string[];
  generated_at: string;
}

/** P1-5. */
export interface CheckRow {
  id: string;
  scenario: string;
  passed: boolean;
  detail: string;
  skipped: boolean;
}

export interface CheckGroup {
  title: string;
  description: string;
  passed: number;
  total: number;
  rows: CheckRow[];
}

export interface AiRow {
  id: string;
  scenario: string;
  expected: string;
  actual: string;
  passed: boolean;
  known_failure: boolean;
  note: string;
  dropped_ungrounded: number;
}

export interface AiRun {
  ran_at: string;
  model: string | null;
  prompt_version: string | null;
  current_prompt_version: string;
  stale: boolean;
  fresh: boolean;
  passed: number;
  total: number;
  dropped_ungrounded: number;
  rows: AiRow[];
}

export interface Evaluation {
  fixtures_found: boolean;
  live: CheckGroup[];
  ai: AiRun | null;
  how_to_run: string;
}

// ---------- Share with a CA or lawyer ----------------------------------------

/** One read-only link, as the owner sees it. */
export interface ShareLink {
  id: number;
  /** Path only, e.g. "/pack/abc"; add window.location.origin for the full link. */
  url: string;
  created_at: string;
  expires_at: string;
  revoked: boolean;
  expired: boolean;
  view_count: number;
  last_viewed_at: string | null;
}

export interface PackTerm {
  type: TermType;
  value: string | null;
  status: TermStatus;
  revision_state: string;
  source_message_ids: number[];
}

export interface PackFlag {
  severity: Severity;
  title: string;
  why_it_matters: string;
  statute: string;
  section: string;
  suggested_question: string | null;
  source_message_ids: number[];
}

export interface PackSource {
  index: number;
  sender: string | null;
  timestamp: string;
  body: string;
}

export interface PackClause {
  id: string;
  heading: string;
  body: string;
  status: string;
  source_message_ids: number[];
  is_placeholder: boolean;
}

export interface PackResponse {
  clause_id: string;
  action: ResponseAction;
  comment: string | null;
  typed_name: string;
  responded_at: string;
}

export interface PackEvent {
  sequence: number;
  type: EventType;
  occurred_at: string;
  summary: string;
  payload_sha256: string;
  prev_hash: string;
  chain_hash: string;
  /** False from the first altered event onward. */
  verified: boolean;
}

export interface PackField {
  label: string;
  value: string;
  source: string;
}

/** What a CA or lawyer sees. Read-only; identifiers are masked by the server. */
export interface Pack {
  title: string;
  notices: string[];
  generated_at: string;
  expires_at: string;
  case: { file_name: string; participants: string[]; message_count: number; period: string };
  summary: { readiness: Severity; terms: PackTerm[]; flags: PackFlag[] } | null;
  sources: PackSource[];
  agreement: {
    version: number;
    status: string;
    clauses_hash: string;
    clauses: PackClause[];
    responses: PackResponse[];
    acknowledgement_note: string;
  } | null;
  timeline: PackEvent[];
  chain: {
    algorithm: string;
    intact: boolean;
    checked: number;
    broken_at_sequence: number | null;
    reason: string | null;
  };
  certificate: {
    title: string;
    status: string;
    record: PackField[];
    integrity: PackField[];
    party_fields: string[];
    statements: { text: string; affirmed: boolean }[];
    cautions: string[];
  };
  identifiers_hidden: number;
}
