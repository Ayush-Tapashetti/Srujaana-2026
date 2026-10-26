import { ArrowLeft, Printer } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ErrorNote, Skeleton } from "../components/ui/Feedback";
import { useApi } from "../hooks/useApi";
import { EVENT_LABEL } from "../lib/labels";
import { useConversation } from "./ConversationLayout";

/** P1-6. Every event, its time and every hash, on paper. */
export function EvidencePrintPage() {
  const conversation = useConversation();
  const chain = useApi(() => api.evidence(conversation.id), [conversation.id]);
  const verify = useApi(() => api.verify(conversation.id), [conversation.id]);

  const c = chain.data;
  const v = verify.data;

  return (
    <div className="space-y-5">
      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <Link to=".." relative="path" className="inline-flex items-center gap-1 text-xs text-fg-faint hover:text-fg">
          <ArrowLeft size={12} aria-hidden /> Back to evidence
        </Link>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => window.print()} disabled={!c}>
          <Printer size={14} aria-hidden /> Print or save as PDF
        </button>
      </div>

      {(chain.error || verify.error) && <ErrorNote>{chain.error?.message ?? verify.error?.message}</ErrorNote>}
      {chain.loading && !c && <Skeleton className="h-[60vh]" />}

      {c && (
        <article className="print-sheet panel mx-auto max-w-4xl space-y-6 p-6 sm:p-8">
          <header className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-4">
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-fg">Evidence summary</h1>
              <p className="mt-1 text-sm text-fg-muted">
                {conversation.original_filename} · {conversation.participants.join(" and ")}
              </p>
            </div>
            <dl className="text-right">
              <dt className="meta">chain check at {new Date().toLocaleString("en-IN")}</dt>
              <dd
                className={`mt-0.5 inline-block rounded-sm border px-2 py-0.5 text-xs font-semibold ${
                  !v
                    ? "border-line text-fg-faint"
                    : v.intact
                      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                      : "border-rose-200 bg-rose-50 text-rose-700"
                }`}
              >
                {!v ? "checking" : v.intact ? `Intact, ${v.checked} events` : `Broken at event ${v.broken_at_sequence}`}
              </dd>
            </dl>
          </header>

          <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-[11rem_1fr]">
            <dt className="text-fg-muted">Algorithm</dt>
            <dd className="text-fg">{c.algorithm}</dd>
            <dt className="text-fg-muted">File hash at upload</dt>
            <dd className="hash break-all">{conversation.content_sha256}</dd>
            <dt className="text-fg-muted">Link rule</dt>
            <dd className="font-mono text-xs text-fg-muted">chain = SHA-256(previous chain | payload hash | UTC time)</dd>
          </dl>

          <table className="w-full table-fixed border-collapse text-left text-xs">
            <colgroup>
              <col className="w-10" />
              <col className="w-40" />
              <col />
            </colgroup>
            <thead className="border-y border-line bg-sunken text-fg-muted">
              <tr>
                <th scope="col" className="px-2 py-1.5 font-medium">#</th>
                <th scope="col" className="px-2 py-1.5 font-medium">Event and time (UTC)</th>
                <th scope="col" className="px-2 py-1.5 font-medium">Hashes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {c.events.map((e) => (
                <tr
                  key={e.sequence}
                  className={`break-inside-avoid align-top ${v && v.broken_at_sequence === e.sequence ? "bg-rose-50" : ""}`}
                >
                  <td className="px-2 py-2 font-mono text-fg-muted">{e.sequence}</td>
                  <td className="px-2 py-2">
                    <span className="block font-medium text-fg">{EVENT_LABEL[e.type]}</span>
                    <span className="meta">{e.occurred_at}</span>
                  </td>
                  <td className="space-y-0.5 px-2 py-2 font-mono text-[0.7rem] leading-snug">
                    <span className="block break-all text-fg-muted">payload {e.payload_sha256}</span>
                    <span className="block break-all text-fg-faint">prev&nbsp;&nbsp;&nbsp; {e.prev_hash}</span>
                    <span className="block break-all text-fg">chain&nbsp;&nbsp; {e.chain_hash}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <footer className="space-y-1 border-t border-line pt-4 text-xs text-fg-muted">
            <p>{c.limitation}</p>
            <p>Anyone can recompute these hashes from the stored events. A changed event breaks every link after it.</p>
            <p>Decision support, not legal advice.</p>
          </footer>
        </article>
      )}
    </div>
  );
}
