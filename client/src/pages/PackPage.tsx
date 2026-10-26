import { CircleAlert, CircleCheck, Printer, ShieldCheck } from "lucide-react";
import { useEffect, useMemo } from "react";
import type { ReactNode } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { Wordmark } from "../components/Shell";
import { ErrorNote, Notice, Skeleton } from "../components/ui/Feedback";
import { useApi } from "../hooks/useApi";
import { EVENT_LABEL, STATUS_LABEL, TERM_LABEL, formatTime } from "../lib/labels";
import type { Pack, PackField, PackSource, Severity } from "../types/api";

const SEVERITY_BADGE: Record<Severity, string> = {
  red: "border-rose-200 bg-rose-50 text-rose-700",
  yellow: "border-amber-200 bg-amber-50 text-amber-700",
  green: "border-emerald-200 bg-emerald-50 text-emerald-700",
};

const READINESS_TEXT: Record<Severity, string> = {
  green: "Every key term was clear",
  yellow: "Key terms present, some vague",
  red: "A key term is missing or was never agreed",
};

const ACTION_TEXT: Record<string, string> = {
  agree: "Agreed",
  suggest_change: "Asked for a change",
  ask_question: "Asked a question",
};

/** Keeps search engines away even if the link is pasted somewhere public. */
function useNoIndex(): void {
  useEffect(() => {
    const tag = document.createElement("meta");
    tag.name = "robots";
    tag.content = "noindex, nofollow, noarchive";
    document.head.appendChild(tag);
    const previousTitle = document.title;
    document.title = "Evidence summary for review";
    return () => {
      tag.remove();
      document.title = previousTitle;
    };
  }, []);
}

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="break-inside-avoid-page">
      <h2 id={id} className="section-title">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Quoted({ ids, sources }: { ids: number[]; sources: Map<number, PackSource> }) {
  const shown = ids.map((i) => sources.get(i)).filter((s): s is PackSource => s !== undefined);
  if (shown.length === 0) return null;
  return (
    <ul className="mt-2 space-y-1">
      {shown.map((s) => (
        <li key={s.index} className="rounded-sm border-l-2 border-line-strong bg-sunken px-2.5 py-1.5 text-xs text-fg-muted">
          <span className="meta mr-2">#{s.index}</span>
          {s.sender && <span className="font-medium text-fg">{s.sender}: </span>}
          <span className="whitespace-pre-wrap break-words">{s.body}</span>
        </li>
      ))}
    </ul>
  );
}

function Fields({ rows }: { rows: PackField[] }) {
  return (
    <dl className="divide-y divide-line">
      {rows.map((f) => (
        <div key={f.label} className="grid gap-1 px-4 py-2.5 sm:grid-cols-[14rem_1fr]">
          <dt className="text-sm text-fg-muted">{f.label}</dt>
          <dd className="min-w-0 break-all text-sm text-fg">
            {f.value}
            <span className="meta ml-2 whitespace-normal">{f.source}</span>
          </dd>
        </div>
      ))}
    </dl>
  );
}

function PackBody({ pack }: { pack: Pack }) {
  const sources = useMemo(() => new Map<number, PackSource>(pack.sources.map((s): [number, PackSource] => [s.index, s])), [pack.sources]);
  const intact = pack.chain.intact;

  return (
    <div className="space-y-9">
      <div className="space-y-2">
        {pack.notices.map((n) => (
          <Notice key={n} icon={<ShieldCheck size={16} />}>
            {n}
          </Notice>
        ))}
      </div>

      {/* The one-line answer to "who checks the chain?" */}
      <div
        className={`flex items-start gap-3 rounded-md border px-4 py-3 ${
          intact ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-rose-200 bg-rose-50 text-rose-800"
        }`}
        role="status"
      >
        {intact ? <CircleCheck size={20} className="mt-0.5 shrink-0" aria-hidden /> : <CircleAlert size={20} className="mt-0.5 shrink-0" aria-hidden />}
        <div>
          <p className="font-semibold">
            {intact
              ? `Record intact: ${pack.chain.checked} events checked just now`
              : `Record broken at event ${pack.chain.broken_at_sequence}`}
          </p>
          <p className="text-sm">
            {intact
              ? `Each event's fingerprint (${pack.chain.algorithm}) includes the one before it, and every link was recomputed when this page loaded.`
              : (pack.chain.reason ?? "Something was changed after it was recorded.")}
          </p>
        </div>
      </div>

      <Section id="case-heading" title="The chat">
        <dl className="panel grid gap-x-6 gap-y-2 p-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-fg-faint">File</dt>
            <dd className="break-all text-fg">{pack.case.file_name}</dd>
          </div>
          <div>
            <dt className="text-xs text-fg-faint">Messages</dt>
            <dd className="text-fg">{pack.case.message_count}</dd>
          </div>
          <div>
            <dt className="text-xs text-fg-faint">Participants</dt>
            <dd className="text-fg">{pack.case.participants.join(", ") || "Not identified"}</dd>
          </div>
          <div>
            <dt className="text-xs text-fg-faint">Period</dt>
            <dd className="text-fg">{pack.case.period}</dd>
          </div>
        </dl>
      </Section>

      <Section id="summary-heading" title="What the chat says">
        {pack.summary === null ? (
          <Notice>The owner has not run the check on this chat yet, so there are no terms to show.</Notice>
        ) : (
          <div className="space-y-5">
            <p>
              <span className={`inline-block rounded-sm border px-2 py-0.5 text-xs font-semibold ${SEVERITY_BADGE[pack.summary.readiness]}`}>
                {READINESS_TEXT[pack.summary.readiness]}
              </span>
            </p>

            <div className="panel overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-line text-xs text-fg-faint">
                  <tr>
                    <th className="px-4 py-2 font-medium">Term</th>
                    <th className="px-4 py-2 font-medium">As found</th>
                    <th className="px-4 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 font-medium">Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {pack.summary.terms.map((t, i) => (
                    <tr key={`${t.type}-${i}`}>
                      <td className="px-4 py-2 text-fg-muted">{TERM_LABEL[t.type]}</td>
                      <td className="px-4 py-2 text-fg">{t.value ?? "—"}</td>
                      <td className="px-4 py-2 text-fg-muted">{STATUS_LABEL[t.status]}</td>
                      <td className="meta px-4 py-2">{t.source_message_ids.map((n) => `#${n}`).join(" ") || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {pack.summary.flags.length > 0 && (
              <ul className="space-y-3">
                {pack.summary.flags.map((f, i) => (
                  <li key={`${f.title}-${i}`} className="panel p-4">
                    <p className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-sm border px-1.5 py-0.5 text-2xs font-semibold uppercase ${SEVERITY_BADGE[f.severity]}`}>
                        {f.severity}
                      </span>
                      <span className="font-medium text-fg">{f.title}</span>
                    </p>
                    <p className="mt-1.5 text-sm text-fg-muted">{f.why_it_matters}</p>
                    <p className="mt-1 text-xs text-fg-faint">
                      {f.statute}, {f.section}
                    </p>
                    <Quoted ids={f.source_message_ids} sources={sources} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </Section>

      <Section id="agreement-heading" title="The agreement and who answered it">
        {pack.agreement === null ? (
          <Notice>No agreement has been drafted from this chat yet.</Notice>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-fg-muted">
              Version {pack.agreement.version}, {pack.agreement.status}. Fingerprint of the clauses:{" "}
              <span className="hash break-all">{pack.agreement.clauses_hash}</span>
            </p>
            <ol className="panel divide-y divide-line">
              {pack.agreement.clauses
                .filter((c) => !c.is_placeholder)
                .map((c) => {
                  const answers = pack.agreement?.responses.filter((r) => r.clause_id === c.id || r.clause_id === "_all") ?? [];
                  return (
                    <li key={c.id} className="px-4 py-3">
                      <p className="font-medium text-fg">{c.heading}</p>
                      <p className="mt-0.5 whitespace-pre-wrap text-sm text-fg-muted">{c.body}</p>
                      {answers.map((r, i) => (
                        <p key={i} className="mt-1.5 text-xs text-fg-muted">
                          <span className="font-medium text-fg">{r.typed_name}</span>: {ACTION_TEXT[r.action] ?? r.action}
                          {r.comment ? ` — “${r.comment}”` : ""} <span className="meta">{formatTime(r.responded_at)}</span>
                        </p>
                      ))}
                    </li>
                  );
                })}
            </ol>
            {pack.agreement.responses.length === 0 && <Notice>Nobody has answered this agreement yet.</Notice>}
            <p className="text-xs text-fg-faint">{pack.agreement.acknowledgement_note}</p>
          </div>
        )}
      </Section>

      <Section id="timeline-heading" title="Everything that happened to this chat, in order">
        <ol className="panel divide-y divide-line">
          {pack.timeline.map((e) => (
            <li key={e.sequence} className="px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium text-fg">
                  <span className="meta mr-2">{e.sequence}</span>
                  {EVENT_LABEL[e.type]}
                </p>
                <span
                  className={`inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-2xs font-semibold uppercase ${
                    e.verified ? SEVERITY_BADGE.green : SEVERITY_BADGE.red
                  }`}
                >
                  {e.verified ? <CircleCheck size={12} aria-hidden /> : <CircleAlert size={12} aria-hidden />}
                  {e.verified ? "Verified" : "Broken"}
                </span>
              </div>
              <p className="mt-0.5 text-sm text-fg-muted">{e.summary}</p>
              <p className="meta mt-1">{formatTime(e.occurred_at)}</p>
              <dl className="mt-2 space-y-0.5">
                <div className="flex gap-2">
                  <dt className="meta w-20 shrink-0">content</dt>
                  <dd className="hash break-all">{e.payload_sha256}</dd>
                </div>
                <div className="flex gap-2">
                  <dt className="meta w-20 shrink-0">previous</dt>
                  <dd className="hash break-all">{e.prev_hash}</dd>
                </div>
                <div className="flex gap-2">
                  <dt className="meta w-20 shrink-0">this link</dt>
                  <dd className="hash break-all">{e.chain_hash}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ol>
      </Section>

      <Section id="parta-heading" title={pack.certificate.title}>
        <p className="mb-3 text-sm text-fg-muted">{pack.certificate.status}</p>
        <div className="space-y-4">
          <div className="panel">
            <Fields rows={pack.certificate.record} />
          </div>
          <div className="panel">
            <Fields rows={pack.certificate.integrity} />
          </div>

          <div className="panel p-4">
            <h3 className="text-sm font-semibold text-fg">To be completed by the party</h3>
            <ul className="mt-2 space-y-3">
              {pack.certificate.party_fields.map((label) => (
                <li key={label} className="text-sm text-fg-muted">
                  {label}
                  <span className="mt-1 block h-5 border-b border-dashed border-line-strong" aria-hidden />
                </li>
              ))}
            </ul>
          </div>

          <div className="panel p-4">
            <h3 className="text-sm font-semibold text-fg">Statements the party confirms for themselves</h3>
            <ul className="mt-2 space-y-2">
              {pack.certificate.statements.map((s) => (
                <li key={s.text} className="flex items-start gap-2 text-sm text-fg-muted">
                  {/* Always unticked: only the party can affirm these. */}
                  <span aria-hidden className="mt-0.5 inline-block h-4 w-4 shrink-0 rounded-sm border border-line-strong" />
                  <span>{s.text}</span>
                </li>
              ))}
            </ul>
          </div>

          <ul className="space-y-1.5 text-xs text-fg-muted">
            {pack.certificate.cautions.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      </Section>

      <p className="border-t border-line pt-4 text-xs text-fg-faint">
        {pack.identifiers_hidden > 0
          ? `${pack.identifiers_hidden} identifier(s) from the chat are hidden in this view. `
          : ""}
        Generated {formatTime(pack.generated_at)}. This link works until {formatTime(pack.expires_at)} or until the
        owner turns it off.
      </p>
    </div>
  );
}

/**
 * What a CA or lawyer opens. No account, no app chrome (it isn't their app),
 * read-only, and not shown to search engines.
 */
export function PackPage() {
  const { token = "" } = useParams();
  useNoIndex();
  const view = useApi(() => api.pack(token), [token]);

  return (
    <div className="min-h-screen">
      <header className="no-print border-b border-line/70">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between px-4">
          <Wordmark />
          <button type="button" className="btn btn-primary btn-sm" onClick={() => window.print()} disabled={!view.data}>
            <Printer size={14} aria-hidden /> Print or save as PDF
          </button>
        </div>
      </header>

      <main className="print-sheet mx-auto max-w-3xl px-4 py-10">
        <h1 className="text-2xl font-semibold tracking-tight text-fg">Evidence summary for review</h1>
        <p className="mb-8 mt-1 text-sm text-fg-muted">Read-only. Prepared from a WhatsApp chat export.</p>

        {view.loading && !view.data && (
          <div className="space-y-4">
            <Skeleton className="h-16" />
            <Skeleton className="h-64" />
          </div>
        )}
        {view.error && <ErrorNote>{view.error.message}</ErrorNote>}
        {view.data && <PackBody pack={view.data} />}
      </main>
    </div>
  );
}
