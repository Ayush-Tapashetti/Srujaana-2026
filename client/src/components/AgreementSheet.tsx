import { Fragment, useState } from "react";
import { api } from "../api/client";
import { formatTime, shortHash } from "../lib/labels";
import { PLACEHOLDER } from "../lib/placeholder";
import type { Agreement } from "../types/api";

/** Renders "[to be confirmed]" as a visible blank to fill, not plain text. */
function ClauseBody({ body }: { body: string }) {
  const parts = body.split(PLACEHOLDER);
  return (
    <>
      {parts.map((part, i) => (
        <Fragment key={i}>
          {part}
          {i < parts.length - 1 && (
            <span className="whitespace-nowrap rounded-sm border-b border-dashed border-rose-300 bg-rose-50 px-1 font-sans text-[0.8em] font-medium text-rose-700">
              to be confirmed
            </span>
          )}
        </Fragment>
      ))}
    </>
  );
}

/**
 * The agreement as a white sheet on the paper-coloured page, with one
 * hairline border and no shadow. It prints exactly as shown.
 */
export function AgreementSheet({
  agreement,
  canPropose = false,
}: {
  agreement: Agreement;
  /** Owner view only: shows "Propose change" on each clause. */
  canPropose?: boolean;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  // clause id -> { proposed text, ready-to-paste WhatsApp message }
  const [proposals, setProposals] = useState<Record<string, { value: string; snippet?: string }>>({});

  const pendingFor = (id: string, serverValue?: string | null) =>
    proposals[id] ?? (serverValue ? { value: serverValue } : undefined);

  async function submit(clauseId: string) {
    const text = draft.trim();
    if (!text) {
      setError("Type the change you want to propose.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.proposeClauseEdit(agreement.id, clauseId, text);
      setProposals((p) => ({ ...p, [clauseId]: { value: res.proposed_value, snippet: res.whatsapp_snippet } }));
      setEditingId(null);
      setDraft("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the proposal.");
    } finally {
      setBusy(false);
    }
  }

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setError("Copy failed. Select the message and copy it by hand.");
    }
  }

  const waLink = (text: string) => `https://wa.me/?text=${encodeURIComponent(text)}`;

  return (
    <article className="print-sheet mx-auto max-w-[44rem] rounded-md border border-line bg-surface px-7 py-9 text-fg sm:px-12 sm:py-11">
      <header className="border-b border-line pb-5">
        <p className="meta">
          Version {agreement.version} / drafted {formatTime(agreement.created_at)} / ID {agreement.id}
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight">Agreement from our WhatsApp conversation</h2>
      </header>

      <section className="mt-6 border-l-2 border-navy-200 pl-4">
        <h3 className="text-xs font-semibold text-fg-muted">What we understood from the chat</h3>
        <p className="mt-1 font-serif text-[1rem] leading-relaxed text-fg">
          <ClauseBody body={agreement.summary} />
        </p>
      </section>

      <ol className="mt-8 divide-y divide-line border-y border-line">
        {agreement.clauses.map((clause, i) => (
          <li key={clause.id} className="grid grid-cols-[2rem_1fr] gap-x-2 py-4">
            <span className="pt-0.5 font-mono text-xs text-fg-faint">{String(i + 1).padStart(2, "0")}</span>
            <div>
              <h3 className="text-sm font-semibold text-fg">{clause.heading}</h3>
              <p className="mt-1 font-serif text-[1.05rem] leading-[1.7] text-fg">
                <ClauseBody body={clause.body} />
              </p>

              {(() => {
                const pending = pendingFor(clause.id, clause.proposed_value);
                return pending ? (
                  <div className="mt-2 rounded-sm border border-amber-300 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900">
                    <p className="font-semibold">Pending Mutual Confirmation</p>
                    <p className="mt-0.5">Proposed: &ldquo;{pending.value}&rdquo;</p>
                    <p className="mt-0.5 text-amber-800">
                      Not part of the agreement until the other side accepts it. Send them the
                      confirmation link and they can accept or decline it there, or agree in the chat.
                    </p>
                    {pending.snippet && (
                      <div className="no-print mt-2">
                        <p className="select-all whitespace-pre-wrap rounded-sm border border-amber-200 bg-white px-2 py-1.5 font-sans text-fg">
                          {pending.snippet}
                        </p>
                        <div className="mt-1.5 flex flex-wrap gap-2">
                          <button type="button" className="btn btn-sm btn-secondary" onClick={() => void copy(pending.snippet!)}>
                            {copied ? "Copied" : "Copy message"}
                          </button>
                          <a className="btn btn-sm btn-secondary" href={waLink(pending.snippet)} target="_blank" rel="noreferrer">
                            Open in WhatsApp
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                ) : null;
              })()}

              {canPropose && !clause.id.startsWith("_") && agreement.status !== "confirmed" && (
                <div className="no-print mt-2">
                  {editingId === clause.id ? (
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        void submit(clause.id);
                      }}
                      className="space-y-2"
                    >
                      <label className="sr-only" htmlFor={`propose-${clause.id}`}>
                        Proposed wording for {clause.heading}
                      </label>
                      <textarea
                        id={`propose-${clause.id}`}
                        autoFocus
                        rows={2}
                        maxLength={1000}
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        placeholder="What should this say instead?"
                        className="w-full rounded-sm border border-line bg-surface px-2 py-1.5 text-sm"
                      />
                      {error && <p className="text-xs text-rose-700">{error}</p>}
                      <div className="flex gap-2">
                        <button type="submit" disabled={busy} className="btn btn-sm btn-primary">
                          {busy ? "Saving..." : "Create message"}
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-ghost"
                          onClick={() => {
                            setEditingId(null);
                            setError(null);
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-sm btn-secondary"
                      onClick={() => {
                        setEditingId(clause.id);
                        setDraft("");
                        setError(null);
                      }}
                    >
                      Propose change
                    </button>
                  )}
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>

      <footer className="mt-6 space-y-1.5 text-xs leading-relaxed text-fg-muted">
        <p>{agreement.notice}</p>
        <p>
          Document fingerprint (SHA-256){" "}
          <span className="break-all font-mono text-2xs text-fg" title={agreement.clauses_hash}>
            {shortHash(agreement.clauses_hash, 16)}
          </span>
        </p>
      </footer>
    </article>
  );
}
