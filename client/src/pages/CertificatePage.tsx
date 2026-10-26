import { ArrowLeft, Printer, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ErrorNote, Skeleton } from "../components/ui/Feedback";
import { useApi } from "../hooks/useApi";
import type { CertificateField } from "../types/api";
import { useConversation } from "./ConversationLayout";

function Fields({ fields }: { fields: CertificateField[] }) {
  return (
    <dl className="divide-y divide-line border-y border-line">
      {fields.map((f) => (
        <div key={f.label} className="grid gap-x-6 gap-y-0.5 py-2 sm:grid-cols-[13rem_1fr]">
          <dt className="text-sm text-fg-muted">{f.label}</dt>
          <dd className="min-w-0">
            <span className={`block break-all text-sm text-fg ${/^[0-9a-f]{64}$/.test(f.value) ? "font-mono text-[0.8rem]" : ""}`}>
              {f.value}
            </span>
            <span className="meta">{f.source}</span>
          </dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * P1-1. BSA s.63(4) Part A, pre-filled with what the app knows. The party's
 * own details and affirmations are typed here and never leave the browser:
 * nothing on this page is sent back or stored.
 */
export function CertificatePage() {
  const conversation = useConversation();
  const draft = useApi(() => api.certificateDraft(conversation.id), [conversation.id]);
  const [party, setParty] = useState<Record<string, string>>({});
  const [affirmed, setAffirmed] = useState<Record<number, boolean>>({});

  const d = draft.data;

  return (
    <div className="space-y-5">
      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <Link to=".." relative="path" className="inline-flex items-center gap-1 text-xs text-fg-faint hover:text-fg">
          <ArrowLeft size={12} aria-hidden /> Back to evidence
        </Link>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => window.print()} disabled={!d}>
          <Printer size={14} aria-hidden /> Print or save as PDF
        </button>
      </div>

      {draft.error && <ErrorNote>{draft.error.message}</ErrorNote>}
      {draft.loading && !d && <Skeleton className="h-[70vh]" />}

      {d && (
        <article className="print-sheet panel mx-auto max-w-3xl space-y-7 p-6 sm:p-10">
          <header className="space-y-2 border-b border-line pb-5">
            <p className="inline-flex items-center gap-1.5 rounded-sm border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
              <TriangleAlert size={12} aria-hidden /> {d.status}
            </p>
            <h1 className="font-serif text-2xl leading-snug text-fg">{d.title}</h1>
            <p className="meta">
              chat {d.conversation_id} · prepared {new Date(d.generated_at).toLocaleString("en-IN")}
            </p>
          </header>

          <section className="space-y-2">
            <h2 className="section-title">1. The electronic record</h2>
            <Fields fields={d.record} />
          </section>

          <section className="space-y-2">
            <h2 className="section-title">2. Hash value</h2>
            <Fields fields={d.integrity} />
            {!d.chain_intact && (
              <ErrorNote>The evidence chain does not verify. Do not rely on this record until that is explained.</ErrorNote>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="section-title">3. The person giving this certificate</h2>
            <p className="no-print text-xs text-fg-faint">Typed here only. Nothing on this page is saved or sent.</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {d.party_fields.map((label) => (
                <label key={label} className="block">
                  <span className="text-sm text-fg-muted">{label}</span>
                  <input
                    className="field mt-1 w-full"
                    value={party[label] ?? ""}
                    onChange={(e) => setParty((p) => ({ ...p, [label]: e.target.value }))}
                    autoComplete="off"
                  />
                </label>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <h2 className="section-title">4. Statements</h2>
            <p className="text-sm text-fg-muted">Tick only what you can personally confirm.</p>
            <ul className="space-y-2.5">
              {d.statements.map((s, i) => (
                <li key={s.text}>
                  <label className="flex items-start gap-3 text-sm text-fg">
                    <input
                      type="checkbox"
                      checked={affirmed[i] ?? false}
                      onChange={(e) => setAffirmed((a) => ({ ...a, [i]: e.target.checked }))}
                      className="mt-0.5 h-4 w-4 shrink-0 rounded-sm border-line-input accent-navy-600"
                    />
                    {s.text}
                  </label>
                </li>
              ))}
            </ul>
          </section>

          <section className="grid gap-8 pt-4 sm:grid-cols-2">
            <div>
              <div className="h-12 border-b border-fg/60" />
              <p className="meta mt-1">signature</p>
            </div>
            <div>
              <div className="h-12 border-b border-fg/60" />
              <p className="meta mt-1">date and place</p>
            </div>
          </section>

          <footer className="space-y-1.5 border-t border-line pt-5">
            {d.cautions.map((c) => (
              <p key={c} className="text-xs leading-relaxed text-fg-muted">
                {c}
              </p>
            ))}
          </footer>
        </article>
      )}
    </div>
  );
}
