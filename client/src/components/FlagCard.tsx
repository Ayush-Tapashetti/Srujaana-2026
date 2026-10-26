import { MessageSquareQuote } from "lucide-react";
import { TERM_LABEL } from "../lib/labels";
import type { Flag } from "../types/api";
import { RiskBadge } from "./RiskBadge";
import { CopyButton } from "./ui/CopyButton";

interface FlagRowProps {
  flag: Flag;
  selected: boolean;
  onSelect: () => void;
}

const EDGE = { red: "bg-rose-500", yellow: "bg-amber-400", green: "bg-emerald-500" };

/**
 * One finding, as a row in a single list (no card inside a card). The
 * statute is set as an indented citation inside the row: this is where
 * domain correctness is shown rather than claimed.
 */
export function FlagCard({ flag, selected, onSelect }: FlagRowProps) {
  const hasSource = flag.source_message_ids.length > 0;

  return (
    <article className={`relative transition-colors ${selected ? "bg-hover" : ""}`}>
      <span aria-hidden className={`absolute inset-y-0 left-0 w-0.5 ${EDGE[flag.severity]}`} />
      <button type="button" onClick={onSelect} className="w-full px-5 pb-2 pt-4 text-left" aria-pressed={selected}>
        <div className="mb-1.5 flex flex-wrap items-center gap-2">
          <RiskBadge severity={flag.severity} label={flag.severity === "red" ? "Fix first" : "Worth clarifying"} />
          <span className="meta">{TERM_LABEL[flag.term_type]}</span>
        </div>
        <h3 className="text-[0.95rem] font-semibold leading-snug text-fg">{flag.title}</h3>
        <p className="mt-1 text-sm text-fg-muted">{flag.why_it_matters}</p>
        {hasSource && (
          <p className="mt-1.5 text-xs font-medium text-navy-600 hover:underline">
            Show in chat: <span className="font-mono">{flag.source_message_ids.map((i) => `#${i}`).join(" ")}</span>
          </p>
        )}
      </button>

      <div className="space-y-3 px-5 pb-4">
        <blockquote className="border-l-2 border-line-strong pl-3 text-sm">
          <cite className="block text-xs font-semibold not-italic text-fg">
            {flag.statute}, <span className="font-mono font-medium">{flag.section}</span>
          </cite>
          <p className="mt-0.5 text-fg-muted">{flag.statute_gist}</p>
        </blockquote>

        {flag.suggested_question && (
          <div className="flex items-start gap-2.5">
            <MessageSquareQuote size={15} className="mt-0.5 shrink-0 text-fg-faint" aria-hidden />
            <p className="flex-1 font-serif text-[0.95rem] italic leading-relaxed text-fg">
              “{flag.suggested_question}”
            </p>
            <CopyButton text={flag.suggested_question} label="Copy" done="Question copied" />
          </div>
        )}
      </div>
    </article>
  );
}
