import type { AgreementStatus, EventType, Severity, TermStatus, TermType } from "../types/api";

/** Names a shop owner would use, not the enum values. */
export const TERM_LABEL: Record<TermType, string> = {
  party: "Party",
  scope: "What's supplied",
  quantity: "Quantity",
  price: "Price",
  advance: "Advance",
  payment_due: "Payment due",
  delivery_date: "Delivery",
  acceptance: "Acceptance",
  cancellation: "Cancellation",
  dispute: "Disputes",
};

export const TERM_ORDER: TermType[] = [
  "party",
  "scope",
  "quantity",
  "price",
  "advance",
  "payment_due",
  "delivery_date",
  "acceptance",
  "cancellation",
  "dispute",
];

export const STATUS_LABEL: Record<TermStatus, string> = {
  clear: "Clear",
  vague: "Vague",
  missing: "Missing",
  conflicted: "Not agreed",
};

export const STATUS_SEVERITY: Record<TermStatus, Severity> = {
  clear: "green",
  vague: "yellow",
  missing: "red",
  conflicted: "red",
};

/** The verdict printed in the readiness stamp. */
export const VERDICT: Record<Severity, { stamp: string; line: string }> = {
  green: {
    stamp: "Ready to confirm",
    line: "Every key term is clear. You can send this for confirmation.",
  },
  yellow: {
    stamp: "Clarify first",
    line: "The key terms are there, but some are vague. Worth tightening before you send.",
  },
  red: {
    stamp: "Gaps to fix",
    line: "A key term is missing or was never agreed. Sending is blocked until it's resolved.",
  },
};

export const SEVERITY_ORDER: Record<Severity, number> = { red: 0, yellow: 1, green: 2 };

export const EVENT_LABEL: Record<EventType, string> = {
  upload: "Chat uploaded",
  extraction: "Chat checked",
  agreement_generated: "Agreement drafted",
  agreement_sent: "Sent for confirmation",
  counterparty_response: "Other side responded",
  recap_reply: "WhatsApp reply attached",
  override_acknowledged: "Override recorded",
};

export const AGREEMENT_STATUS_LABEL: Record<AgreementStatus, string> = {
  draft: "Draft",
  sent: "Sent",
  changes_requested: "Changes requested",
  confirmed: "Confirmed",
};

/** "T05 unresolved conflict" -> "Unresolved conflict" */
export function sampleTitle(label: string): string {
  const stripped = label.replace(/^T\d+\s*/i, "");
  return stripped.charAt(0).toUpperCase() + stripped.slice(1);
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function shortHash(hash: string, size = 10): string {
  return hash.length > size * 2 ? `${hash.slice(0, size)}…${hash.slice(-4)}` : hash;
}
