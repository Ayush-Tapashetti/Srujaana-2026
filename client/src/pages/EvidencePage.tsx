import { FileText, FlaskConical, Fingerprint, Printer, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { useState } from "react";
import { api } from "../api/client";
import { EvidenceTimeline } from "../components/EvidenceTimeline";
import { AnimatedNumber } from "../components/motion/AnimatedNumber";
import { ProgressRule } from "../components/motion/ProgressRule";
import { useIsland } from "../components/motion/StatusIsland";
import { SharePanel } from "../components/SharePanel";
import { ErrorNote, Notice, Skeleton } from "../components/ui/Feedback";
import { Stamp } from "../components/ui/Stamp";
import { useAction, useApi } from "../hooks/useApi";
import type { Verification } from "../types/api";
import { useConversation } from "./ConversationLayout";

export function EvidencePage() {
  const conversation = useConversation();
  const chain = useApi(() => api.evidence(conversation.id), [conversation.id]);
  const health = useApi(() => api.health(), []);
  const action = useAction();
  const [result, setResult] = useState<Verification | null>(null);
  const [checks, setChecks] = useState(0);

  const island = useIsland();

  const report = (r: Verification) => {
    setResult(r);
    setChecks((n) => n + 1);
    if (r.intact) island.notify("success", "Record intact", `${r.checked} events checked`);
    else island.notify("error", `Broken at event ${r.broken_at_sequence}`, "Something was changed");
  };

  const verify = async () => {
    const stop = island.busy("Recomputing every fingerprint");
    const r = await action.run(() => api.verify(conversation.id));
    stop();
    if (r) report(r);
  };

  const tamper = async () => {
    const events = chain.data?.events ?? [];
    const target = events.length > 1 ? 1 : 0;
    const r = await action.run(() => api.tamper(conversation.id, target));
    if (r) {
      report(r);
      await chain.reload();
    }
  };

  const upload = chain.data?.events.find((e) => e.type === "upload");

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,4fr)]">
      <section aria-labelledby="chain-heading">
        <div className="flex items-baseline justify-between gap-3">
          <h2 id="chain-heading" className="section-title">
            Everything that happened to this chat, in order
          </h2>
          <Link to="print" className="mb-2 inline-flex items-center gap-1 text-xs text-fg-faint hover:text-navy-600">
            <Printer size={12} aria-hidden /> Print summary
          </Link>
        </div>
        {chain.loading && !chain.data ? (
          <div className="space-y-4">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        ) : chain.error ? (
          <ErrorNote>{chain.error.message}</ErrorNote>
        ) : (
          <EvidenceTimeline events={chain.data?.events ?? []} brokenAt={result?.broken_at_sequence ?? null} />
        )}
      </section>

      <aside className="space-y-6">
        <section className="panel relative p-5" aria-labelledby="verify-heading">
          {action.busy && <ProgressRule />}
          <h2 id="verify-heading" className="font-semibold text-fg">
            Check nothing has changed
          </h2>
          <p className="mt-1 text-sm text-fg-muted">
            Each step's fingerprint includes the one before it. Change any step and every fingerprint after it
            stops matching.
          </p>

          <div className="well mt-5 grid min-h-[7.5rem] place-items-center">
            {result ? (
              <Stamp
                tone={result.intact ? "green" : "red"}
                size="lg"
                pressKey={checks}
                sub={result.intact ? `${result.checked} events checked` : `at event ${result.broken_at_sequence}`}
              >
                {result.intact ? "Intact" : "Broken"}
              </Stamp>
            ) : (
              <p className="px-6 text-center text-sm text-fg-faint">Not checked yet</p>
            )}
          </div>
          {chain.data && (
            <p className="mt-3 flex items-baseline gap-1.5 text-sm text-fg-muted">
              <AnimatedNumber value={chain.data.events.length} className="text-lg font-bold text-fg" />
              events in this record, each linked to the one before
            </p>
          )}
          {result && !result.intact && result.reason && (
            <p className="mt-3 text-sm text-rose-700">{result.reason}</p>
          )}

          <div className="mt-5 flex flex-wrap gap-3">
            <button type="button" className="btn btn-primary" onClick={verify} disabled={action.busy}>
              <ShieldCheck size={16} aria-hidden /> Check integrity
            </button>
            {health.data?.demo_tamper_enabled && (
              <button type="button" className="btn btn-secondary" onClick={tamper} disabled={action.busy}>
                <FlaskConical size={16} aria-hidden /> Demo: alter one event
              </button>
            )}
          </div>
          {health.data?.demo_tamper_enabled && (
            <p className="mt-2 text-xs text-fg-faint">
              The demo button edits a stored event behind the scenes, the way someone might try to rewrite the
              record. It only exists in demo mode.
            </p>
          )}
          {action.error && (
            <div className="mt-3">
              <ErrorNote>{action.error}</ErrorNote>
            </div>
          )}
        </section>

        {upload && (
          <section className="panel p-5" aria-labelledby="parta-heading">
            <h2 id="parta-heading" className="flex items-center gap-2 font-semibold text-fg">
              <Fingerprint size={17} className="text-fg-faint" aria-hidden /> Fingerprint of the original file
            </h2>
            <p className="mt-1 text-sm text-fg-muted">
              The hash value and algorithm a party discloses in Part A of the certificate under section 63(4)
              of the Bharatiya Sakshya Adhiniyam, 2023.
            </p>
            <dl className="mt-3 space-y-2 rounded-md bg-sunken p-3 text-sm">
              <div>
                <dt className="text-xs text-fg-faint">Algorithm</dt>
                <dd className="text-fg">{String(upload.payload.algorithm ?? chain.data?.algorithm)}</dd>
              </div>
              <div>
                <dt className="text-xs text-fg-faint">Hash value</dt>
                <dd className="hash break-all">{conversation.content_sha256}</dd>
              </div>
            </dl>
            <Link to="certificate" className="btn btn-secondary btn-sm mt-3">
              <FileText size={14} aria-hidden /> Draft Part A of the certificate
            </Link>
            <p className="mt-3 text-xs text-fg-faint">
              Part B must be completed by an expert. This app does not do that, and doesn't decide whether a
              court will accept the record.
            </p>
          </section>
        )}

        <SharePanel conversationId={conversation.id} />

        {chain.data && <Notice icon={<ShieldCheck size={16} />}>{chain.data.limitation}</Notice>}
      </aside>
    </div>
  );
}
