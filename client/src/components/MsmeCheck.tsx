import { Building2 } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import { useAction } from "../hooks/useApi";
import type { MsmeCheck as MsmeResult, SupplierAnswer } from "../types/api";
import { FlagCard } from "./FlagCard";
import { ErrorNote, Spinner } from "./ui/Feedback";

const ANSWERS: { value: SupplierAnswer; label: string }[] = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
  { value: "unsure", label: "Not sure" },
];

/**
 * P1-2. Whether the supplier is Udyam-registered is not in the chat, so we
 * ask instead of guessing. The answer is not stored and never changes the
 * readiness verdict: it is advice the owner may not know they need.
 */
export function MsmeCheck({ conversationId, onSelect }: { conversationId: number; onSelect: (ids: number[]) => void }) {
  const [answer, setAnswer] = useState<SupplierAnswer | null>(null);
  const [result, setResult] = useState<MsmeResult | null>(null);
  const action = useAction();

  const choose = async (value: SupplierAnswer) => {
    setAnswer(value);
    const r = await action.run(() => api.msmeCheck(conversationId, value));
    if (r) setResult(r);
  };

  return (
    <section aria-labelledby="msme-heading" className="panel overflow-hidden">
      <div className="p-4">
        <h3 id="msme-heading" className="flex items-center gap-2 text-sm font-semibold text-fg">
          <Building2 size={15} className="text-fg-faint" aria-hidden />
          Is the supplier registered as a micro or small enterprise (Udyam)?
        </h3>
        <p className="mt-1 text-xs text-fg-muted">
          Buyers from micro and small suppliers must pay within 45 days. The chat can't tell us this, so we ask.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2" role="group" aria-label="Supplier registration">
          {ANSWERS.map((a) => (
            <button
              key={a.value}
              type="button"
              aria-pressed={answer === a.value}
              onClick={() => choose(a.value)}
              disabled={action.busy}
              className={`btn btn-sm ${answer === a.value ? "btn-primary" : "btn-secondary"}`}
            >
              {a.label}
            </button>
          ))}
          {action.busy && <Spinner label="Checking" />}
        </div>
      </div>

      {action.error && (
        <div className="px-4 pb-4">
          <ErrorNote>{action.error}</ErrorNote>
        </div>
      )}

      {result && !action.busy && (
        <div className="border-t border-line">
          {result.flag ? (
            <FlagCard flag={result.flag} selected={false} onSelect={() => onSelect(result.flag?.source_message_ids ?? [])} />
          ) : null}
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 bg-sunken/60 px-4 py-3 text-sm">
            {result.payment_term && (
              <span className="text-fg">
                <span className="meta mr-1.5">payment</span>“{result.payment_term}”
                {result.period_days != null && (
                  <span className="meta ml-1.5">
                    = {result.period_days} days, limit {result.limit_days}
                  </span>
                )}
              </span>
            )}
            <span className="text-fg-muted">{result.note}</span>
          </div>
        </div>
      )}
    </section>
  );
}
