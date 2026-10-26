import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { EVENT_LABEL, formatTime } from "../lib/labels";
import type { EvidenceEvent } from "../types/api";
import { HashTooltip } from "./motion/HashTooltip";

/** One plain sentence per event, from its payload. */
function describe(event: EvidenceEvent): string {
  const p = event.payload;
  const n = (k: string) => (typeof p[k] === "number" || typeof p[k] === "string" ? String(p[k]) : "");
  switch (event.type) {
    case "upload":
      return `${n("filename")}, ${n("message_count")} messages, fingerprinted with ${n("algorithm")}.`;
    case "extraction":
      return `${n("term_count")} terms found; readiness ${n("readiness")}${p.from_cache ? " (cached result)" : ""}. ${n(
        "dropped_ungrounded",
      )} unsupported item(s) discarded.`;
    case "agreement_generated":
      return `Version ${n("version")} drafted while readiness was ${n("readiness")}.${
        p.override_reason ? ` Override recorded: “${n("override_reason")}”` : ""
      }`;
    case "agreement_sent":
      return `One-time confirmation link created, valid until ${formatTime(n("expires_at"))}.`;
    case "counterparty_response":
      return `${n("typed_name")} responded to ${Array.isArray(p.answers) ? p.answers.length : 0} clause(s). Acknowledgement, not a signature.`;
    case "recap_reply":
      return `${n("typed_name")} replied in WhatsApp: “${n("message_text")}”`;
    default:
      return "";
  }
}

/**
 * The record as a ledger: one row per event, a numbered node on a rail, and
 * the rail drawn in once on load. From the first broken event onward, nodes
 * and rail turn rose.
 */
export function EvidenceTimeline({ events, brokenAt }: { events: EvidenceEvent[]; brokenAt: number | null }) {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <ol className="panel divide-y divide-line" aria-label="Evidence events">
      {events.map((event, i) => {
        const broken = brokenAt !== null && event.sequence >= brokenAt;
        const isFirstBroken = event.sequence === brokenAt;
        const expanded = open === event.sequence;

        return (
          <li
            key={event.sequence}
            className={`relative grid grid-cols-[2rem_1fr] gap-x-4 px-5 py-4 animate-row-in ${isFirstBroken ? "bg-rose-50/60" : ""}`}
            style={{ animationDelay: `${i * 70}ms` }}
          >
            {/* The rail between this node and the next. */}
            {i < events.length - 1 && (
              <span
                aria-hidden
                className={`absolute bottom-0 left-[2.45rem] top-11 w-px origin-top animate-link-draw ${
                  broken ? "bg-rose-300" : "bg-line-strong"
                }`}
                style={{ animationDelay: `${i * 70 + 120}ms` }}
              />
            )}
            {i > 0 && (
              <span
                aria-hidden
                className={`absolute left-[2.45rem] top-0 h-4 w-px ${broken ? "bg-rose-300" : "bg-line-strong"}`}
              />
            )}

            <span
              className={`relative z-10 grid h-7 w-7 place-items-center rounded-sm border font-mono text-xs font-medium ${
                isFirstBroken
                  ? "border-rose-300 bg-rose-50 text-rose-700"
                  : broken
                    ? "border-rose-200 bg-surface text-rose-700/70"
                    : "border-line-strong bg-surface text-fg-muted"
              }`}
            >
              {event.sequence}
            </span>

            <div className="min-w-0">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                <h3 className="text-sm font-semibold text-fg">{EVENT_LABEL[event.type] ?? event.type}</h3>
                <time className="meta" dateTime={event.occurred_at}>
                  {formatTime(event.occurred_at)}
                </time>
              </div>
              <p className="mt-0.5 text-sm text-fg-muted">{describe(event)}</p>

              <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1">
                <HashTooltip hash={event.chain_hash} label={`Event ${event.sequence} link fingerprint (SHA-256)`} />
                <button
                  type="button"
                  onClick={() => setOpen(expanded ? null : event.sequence)}
                  aria-expanded={expanded}
                  className="inline-flex items-center gap-1 text-xs text-fg-faint hover:text-fg"
                >
                  {expanded ? "Hide hashes" : "Show hashes"}
                  <ChevronDown size={12} className={`transition-transform ${expanded ? "rotate-180" : ""}`} />
                </button>
              </div>

              {expanded && (
                <dl className="well mt-3 grid gap-1.5 p-3 text-xs">
                  {(
                    [
                      ["Previous link", event.prev_hash],
                      ["Contents", event.payload_sha256],
                      ["This link", event.chain_hash],
                    ] as const
                  ).map(([label, value]) => (
                    <div key={label} className="grid gap-0.5 sm:grid-cols-[6.5rem_1fr]">
                      <dt className="text-fg-faint">{label}</dt>
                      <dd className="hash break-all">{value}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
