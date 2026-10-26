import { CornerDownRight } from "lucide-react";
import { TERM_LABEL, formatTime } from "../lib/labels";
import type { Message, Term } from "../types/api";
import { RiskBadge } from "./RiskBadge";

interface RevisionTimelineProps {
  term: Term;
  messages: Message[];
  onSelect: (sources: number[]) => void;
}

/**
 * P1-3. How one term changed, step by step, ending in the one reply the
 * s.62 rule judged. Each step links back to its message in the chat.
 *
 * The rule itself runs on the server; this only shows what it looked at,
 * so the "Not agreed" badge can be checked by eye.
 */
export function RevisionTimeline({ term, messages, onSelect }: RevisionTimelineProps) {
  const byIndex = new Map(messages.map((m) => [m.index, m]));
  const steps = [
    ...term.revision_history.map((r) => ({ value: r.value, ids: r.source_message_ids, active: false })),
    { value: term.value ?? "", ids: term.source_message_ids, active: true },
  ];
  const reply = term.response_message_index != null ? byIndex.get(term.response_message_index) : undefined;
  const settled = term.revision_state === "settled";
  const proposer = byIndex.get(Math.max(...term.source_message_ids))?.sender;

  return (
    <div className="panel p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-fg">{TERM_LABEL[term.type]}</h3>
        <RiskBadge
          severity={settled ? "green" : "red"}
          label={settled ? "Change accepted" : "Change not accepted"}
        />
      </div>

      <ol className="relative space-y-0">
        {steps.map((step, i) => {
          const at = Math.max(...step.ids);
          const m = byIndex.get(at);
          return (
            <li key={`${step.value}-${i}`} className="relative grid grid-cols-[1.25rem_1fr] gap-3 pb-3">
              {/* the rail */}
              <span aria-hidden className="absolute left-[0.6rem] top-4 h-full w-px bg-line" />
              <span
                aria-hidden
                className={`relative mt-1.5 h-2.5 w-2.5 justify-self-center rounded-full border ${
                  step.active ? "border-navy-600 bg-navy-600" : "border-line-strong bg-surface"
                }`}
              />
              <button
                type="button"
                onClick={() => onSelect(step.ids)}
                className="rounded-sm text-left transition-colors hover:bg-hover"
              >
                <span className={`block text-sm ${step.active ? "font-semibold text-fg" : "text-fg-faint line-through"}`}>
                  {step.value}
                </span>
                <span className="meta">
                  #{at} · {m?.sender ?? "unknown"}
                  {m ? ` · ${formatTime(m.timestamp)}` : ""}
                  {step.active ? " · latest" : ""}
                </span>
              </button>
            </li>
          );
        })}

        <li className="grid grid-cols-[1.25rem_1fr] gap-3">
          <CornerDownRight size={14} aria-hidden className={`mt-1 justify-self-center ${settled ? "text-emerald-700" : "text-rose-700"}`} />
          {reply ? (
            <button
              type="button"
              onClick={() => onSelect([reply.index])}
              className={`rounded-md border px-3 py-2 text-left text-sm transition-colors hover:bg-hover ${
                settled ? "border-emerald-200 bg-emerald-50" : "border-rose-200 bg-rose-50"
              }`}
            >
              <span className="meta block">
                Next reply from {reply.sender} · #{reply.index} · {formatTime(reply.timestamp)}
              </span>
              <span className="mt-0.5 block text-fg">“{reply.body}”</span>
              <span className={`mt-1 block text-xs ${settled ? "text-emerald-700" : "text-rose-700"}`}>
                {settled
                  ? "Repeats the new value or says yes, so the change counts as agreed."
                  : "Doesn't repeat the new value or say yes, so the change is only a proposal."}
              </span>
            </button>
          ) : (
            <p className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {proposer ? `Nobody but ${proposer} wrote after this.` : "No reply from the other side."} A change
              needs both sides, so it is only a proposal.
            </p>
          )}
        </li>
      </ol>
      <p className="mt-3 text-xs text-fg-faint">
        Indian Contract Act, 1872, s.62: a contract is changed only when both parties agree to the change.
      </p>
    </div>
  );
}
