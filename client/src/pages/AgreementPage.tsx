import { CircleHelp, FilePen, Fingerprint, PencilLine, Printer, RefreshCw, ThumbsUp, TriangleAlert } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { AgreementSheet } from "../components/AgreementSheet";
import { ClauseTree } from "../components/ClauseTree";
import { AnimatedGroup } from "../components/motion/AnimatedGroup";
import { MorphMenu } from "../components/motion/MorphMenu";
import { useIsland } from "../components/motion/StatusIsland";
import { SendPanel } from "../components/SendPanel";
import { ErrorNote, Notice, Skeleton } from "../components/ui/Feedback";
import { Stamp } from "../components/ui/Stamp";
import { useAction, useApi } from "../hooks/useApi";
import { AGREEMENT_STATUS_LABEL, formatTime } from "../lib/labels";
import type { Agreement, ResponseAction } from "../types/api";
import { useConversation } from "./ConversationLayout";

const ACTION: Record<ResponseAction, { label: string; Icon: typeof ThumbsUp; cls: string }> = {
  agree: { label: "Agreed", Icon: ThumbsUp, cls: "text-emerald-700" },
  suggest_change: { label: "Asked for a change", Icon: PencilLine, cls: "text-amber-700" },
  ask_question: { label: "Asked a question", Icon: CircleHelp, cls: "text-navy-600" },
};

export function AgreementPage() {
  const conversation = useConversation();
  const agreement = useApi(() => api.latestAgreement(conversation.id), [conversation.id]);
  const analysis = useApi(() => api.analysis(conversation.id), [conversation.id]);
  const draft = useAction();

  const a = agreement.data;
  const needsReview = analysis.data?.readiness === "red" || Boolean(a?.override_reason);

  const island = useIsland();

  const generate = async () => {
    const stop = island.busy("Drafting the agreement");
    const next = await draft.run(() => api.generate(conversation.id));
    stop();
    if (next) {
      agreement.setData(next);
      island.notify("success", `Version ${next.version} drafted`);
    }
  };

  const copyFingerprint = async (hash: string) => {
    try {
      await navigator.clipboard.writeText(hash);
      island.notify("success", "Fingerprint copied");
    } catch {
      island.notify("error", "Couldn't copy", "Your browser blocked the clipboard");
    }
  };

  if (agreement.loading && !a) {
    return (
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,4fr)]">
        <Skeleton className="h-[70vh]" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!a) {
    const notAnalysed = analysis.error?.status === 404;
    return (
      <section className="panel mx-auto max-w-2xl p-8 text-center">
        <FilePen size={30} className="mx-auto text-navy-600" aria-hidden />
        <h2 className="mt-3 text-xl font-semibold text-fg">No agreement drafted yet</h2>
        <p className="mx-auto mt-1 max-w-md text-sm text-fg-muted">
          {notAnalysed
            ? "Check the chat first, so the agreement is built from terms we've found and verified."
            : "We'll write a short, plain agreement using only terms from the chat. Anything never agreed is left blank for you to fill."}
        </p>
        <div className="mt-5 flex justify-center gap-3">
          {notAnalysed ? (
            <Link to=".." relative="path" className="btn btn-primary">
              Check the chat first
            </Link>
          ) : (
            <button type="button" className="btn btn-primary" onClick={generate} disabled={draft.busy}>
              {draft.busy ? "Drafting…" : "Draft the agreement"}
            </button>
          )}
        </div>
        {draft.error && (
          <div className="mt-4 text-left">
            <ErrorNote>{draft.error}</ErrorNote>
          </div>
        )}
      </section>
    );
  }

  const byClause = new Map<string, Agreement["responses"]>();
  for (const r of a.responses) byClause.set(r.clause_id, [...(byClause.get(r.clause_id) ?? []), r]);
  const confirmed = a.status === "confirmed";

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,4fr)]">
      <div className="space-y-4">
        <div className="no-print flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-fg-muted">
            Status <span className="font-semibold text-fg">{AGREEMENT_STATUS_LABEL[a.status]}</span>
          </p>
          <div className="flex items-center gap-2">
            <button type="button" className="btn btn-primary btn-sm h-9" onClick={() => window.print()}>
              <Printer size={14} aria-hidden /> Print or save as PDF
            </button>
            <MorphMenu
              label="More"
              actions={[
                {
                  label: "Redraft from the latest check",
                  hint: "Creates a new version; earlier ones stay in the evidence trail",
                  icon: RefreshCw,
                  onSelect: generate,
                  disabled: draft.busy,
                },
                {
                  label: "Copy document fingerprint",
                  hint: "The SHA-256 of these clauses",
                  icon: Fingerprint,
                  onSelect: () => void copyFingerprint(a.clauses_hash),
                },
              ]}
            />
          </div>
        </div>

        {needsReview && (
          <div className="no-print">
            <Notice icon={<TriangleAlert size={16} />}>
              Needs a lawyer's review before you rely on it: key terms are missing or unconfirmed
              {a.override_reason ? ", and it was sent with an override" : ""}.
            </Notice>
          </div>
        )}

        <div className="relative">
          <AgreementSheet agreement={a} canPropose />
          {confirmed && (
            <div className="pointer-events-none absolute right-6 top-24 sm:right-16">
              <Stamp tone="ink" size="lg" pressKey={a.status} sub={a.responses[0]?.typed_name}>
                Confirmed
              </Stamp>
            </div>
          )}
        </div>
      </div>

      <aside className="no-print space-y-6">
        <section aria-labelledby="send-heading">
          <h2 id="send-heading" className="section-title">
            Get it confirmed
          </h2>
          <SendPanel agreement={a} analysis={analysis.data} onAgreement={agreement.setData} />
        </section>

        {a.responses.length > 0 && (
          <section aria-labelledby="responses-heading">
            <h2 id="responses-heading" className="section-title">
              Their responses
            </h2>
            <AnimatedGroup className="panel divide-y divide-line" replayKey={a.responses.length}>
              {[...byClause.entries()].map(([clauseId, responses]) => {
                const clause = a.clauses.find((c) => c.id === clauseId);
                return responses.map((r, i) => {
                  const { label, Icon, cls } = ACTION[r.action];
                  return (
                    <div key={`${clauseId}-${i}`} className="px-4 py-3 text-sm">
                      <p className="flex items-center gap-2">
                        <Icon size={15} className={cls} aria-hidden />
                        <span className="font-semibold text-fg">{clause?.heading ?? "Whole recap"}</span>
                        <span className={cls}>{label}</span>
                      </p>
                      {r.comment && <p className="mt-1 text-fg-muted">“{r.comment}”</p>}
                      <p className="mt-1 text-xs text-fg-faint">
                        {r.typed_name}, {formatTime(r.responded_at)}
                      </p>
                    </div>
                  );
                });
              })}
            </AnimatedGroup>
          </section>
        )}

        <section aria-labelledby="outline-heading">
          <h2 id="outline-heading" className="section-title">
            Where each clause came from
          </h2>
          <div className="panel p-3">
            <ClauseTree clauses={a.clauses} messages={conversation.messages} />
          </div>
        </section>
      </aside>
    </div>
  );
}
