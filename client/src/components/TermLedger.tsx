import { STATUS_LABEL, STATUS_SEVERITY, TERM_LABEL, TERM_ORDER } from "../lib/labels";
import type { Term, TermType } from "../types/api";
import { RiskBadge } from "./RiskBadge";

interface TermLedgerProps {
  terms: Term[];
  missing: TermType[];
  selectedKey: string | null;
  onSelect: (key: string, sources: number[]) => void;
}

/**
 * What was agreed, as a ledger: one row per term, the value as written in
 * the chat, the messages it came from, and its status. Missing critical
 * terms get a row too, because "nothing was said" is a finding.
 */
export function TermLedger({ terms, missing, selectedKey, onSelect }: TermLedgerProps) {
  const rows = [...terms].sort((a, b) => TERM_ORDER.indexOf(a.type) - TERM_ORDER.indexOf(b.type));
  const absent = missing.filter((t) => !terms.some((term) => term.type === t));

  return (
    <div className="panel overflow-hidden">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Terms found in the chat</caption>
        <thead className="border-b border-line bg-sunken text-xs text-fg-muted">
          <tr>
            <th scope="col" className="px-4 py-2 font-medium">Term</th>
            <th scope="col" className="px-2 py-2 font-medium">As written in the chat</th>
            <th scope="col" className="hidden px-2 py-2 font-medium sm:table-cell">Source</th>
            <th scope="col" className="px-4 py-2 text-right font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((term, i) => {
            const key = `${term.type}-${i}`;
            const selected = key === selectedKey;
            return (
              <tr
                key={key}
                onClick={() => onSelect(key, term.source_message_ids)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(key, term.source_message_ids);
                  }
                }}
                tabIndex={0}
                aria-selected={selected}
                className={`cursor-pointer align-top transition-colors ${selected ? "bg-hover" : "hover:bg-hover/70"}`}
              >
                <th scope="row" className="whitespace-nowrap px-4 py-2.5 font-medium text-fg-muted">
                  {TERM_LABEL[term.type]}
                </th>
                <td className="px-2 py-2.5">
                  <span className="text-fg">{term.value}</span>
                  {term.revision_history.length > 0 && (
                    <span className="mt-1 block text-xs text-fg-faint">
                      Earlier:{" "}
                      {term.revision_history.map((r) => (
                        <s key={r.value} className="mr-1">
                          {r.value}
                        </s>
                      ))}
                      {term.revision_state === "settled" ? "(change accepted)" : "(change not accepted)"}
                    </span>
                  )}
                </td>
                <td className="hidden whitespace-nowrap px-2 py-2.5 sm:table-cell">
                  <span className="meta">{term.source_message_ids.map((n) => `#${n}`).join(" ")}</span>
                </td>
                <td className="px-4 py-2.5 text-right">
                  <RiskBadge severity={STATUS_SEVERITY[term.status]} label={STATUS_LABEL[term.status]} />
                </td>
              </tr>
            );
          })}
          {absent.map((type) => (
            <tr key={`absent-${type}`} className="align-top">
              <th scope="row" className="whitespace-nowrap px-4 py-2.5 font-medium text-fg-muted">
                {TERM_LABEL[type]}
              </th>
              <td className="px-2 py-2.5 italic text-fg-faint">Never mentioned in the chat</td>
              <td className="hidden px-2 py-2.5 sm:table-cell">
                <span className="meta">none</span>
              </td>
              <td className="px-4 py-2.5 text-right">
                <RiskBadge severity="red" label="Missing" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
