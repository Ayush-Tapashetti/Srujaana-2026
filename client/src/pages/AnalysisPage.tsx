import { EyeOff, FileSearch, RefreshCw, ShieldAlert, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ChatView } from "../components/ChatView";
import { FlagCard } from "../components/FlagCard";
import { MsmeCheck } from "../components/MsmeCheck";
import { RevisionTimeline } from "../components/RevisionTimeline";
import { STATUS_CLASSES, severityTone } from "../components/RiskBadge";
import { TermLedger } from "../components/TermLedger";
import { AnimatedGroup } from "../components/motion/AnimatedGroup";
import { AnimatedNumber } from "../components/motion/AnimatedNumber";
import { ProgressRule } from "../components/motion/ProgressRule";
import { useIsland } from "../components/motion/StatusIsland";
import { ErrorNote, Notice, Skeleton, Spinner } from "../components/ui/Feedback";
import { Stamp } from "../components/ui/Stamp";
import { useAction, useApi } from "../hooks/useApi";
import { SEVERITY_ORDER, VERDICT } from "../lib/labels";
import type { Severity } from "../types/api";
import { useConversation } from "./ConversationLayout";

export function AnalysisPage() {
  const conversation = useConversation();
  const analysis = useApi(() => api.analysis(conversation.id), [conversation.id]);
  const extract = useAction();
  const island = useIsland();

  const [selected, setSelected] = useState<string | null>(null);
  const [highlighted, setHighlighted] = useState<number[]>([]);
  const [focusKey, setFocusKey] = useState(0);

  const select = (key: string, sources: number[]) => {
    setSelected(key);
    setHighlighted(sources);
    setFocusKey((k) => k + 1);
  };

  const run = async (force: boolean) => {
    const stop = island.busy(`Reading ${conversation.message_count} messages`);
    const result = await extract.run(() => api.extract(conversation.id, force));
    stop();
    if (result) {
      analysis.setData(result);
      setSelected(null);
      setHighlighted([]);
      // Neutral tone: the verdict seal carries the colour, not the status line.
      island.notify(
        result.readiness === "green" ? "success" : "info",
        "Check complete",
        `${result.flags.length} finding${result.flags.length === 1 ? "" : "s"}`,
      );
    } else {
      island.notify("error", "The check didn't run");
    }
  };

  const a = analysis.data;
  const flags = useMemo(
    () => [...(a?.flags ?? [])].sort((x, y) => SEVERITY_ORDER[x.severity] - SEVERITY_ORDER[y.severity]),
    [a],
  );
  const revised = (a?.terms ?? []).filter((t) => t.revision_history.length > 0);
  const hasPaymentTerm = (a?.terms ?? []).some((t) => t.type === "payment_due" && t.value);
  const notYetChecked = analysis.error?.status === 404;
  const maskedSummary = Object.entries(conversation.masked.counts)
    .map(([kind, n]) => `${n} ${kind.toLowerCase()}`)
    .join(", ");

  const tally: [Severity, number, string][] = a
    ? [
        ["red", flags.filter((f) => f.severity === "red").length, "to fix first"],
        ["yellow", flags.filter((f) => f.severity === "yellow").length, "worth clarifying"],
        ["green", a.terms.filter((t) => t.status === "clear").length, "clear"],
      ]
    : [];

  return (
    <div className="space-y-6">
      {conversation.warnings.length > 0 && (
        <div className="space-y-2">
          {conversation.warnings.map((w) => (
            <Notice key={w} icon={<TriangleAlert size={15} />}>
              {w}
            </Notice>
          ))}
        </div>
      )}

      {/* ---- The verdict ---- */}
      <section className="panel relative grid gap-5 p-5 md:grid-cols-[auto_1fr_auto] md:items-center md:gap-8">
        {extract.busy && <ProgressRule />}
        {a ? (
          <>
            <div className="grid min-h-[5rem] min-w-[12rem] place-items-center md:border-r md:border-line md:pr-8">
              <Stamp tone={severityTone(a.readiness)} size="lg" pressKey={a.id} sub={`${flags.length} FINDINGS`}>
                {VERDICT[a.readiness].stamp}
              </Stamp>
            </div>
            <div className="min-w-0">
              <p className="text-base font-medium text-fg">{VERDICT[a.readiness].line}</p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {tally.map(([sev, n, text]) => (
                  <span
                    key={sev}
                    className={`inline-flex items-baseline gap-1.5 rounded-sm border px-2 py-0.5 text-xs ${
                      n > 0 ? STATUS_CLASSES[sev] : "border-line bg-surface text-fg-faint"
                    }`}
                  >
                    <AnimatedNumber value={n} className="font-mono font-semibold" />
                    {text}
                  </span>
                ))}
              </div>
              <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1">
                <div className="flex gap-1.5">
                  <dt className="meta">model</dt>
                  <dd className="meta text-fg-muted">{a.model_used}</dd>
                </div>
                {a.filled_by_rules?.length > 0 && (
                  <div className="flex gap-1.5">
                    <dt className="meta">rules</dt>
                    <dd className="meta text-fg-muted">
                      AI missed {a.filled_by_rules.join(", ").replace(/_/g, " ")}; found by pattern rules
                    </dd>
                  </div>
                )}
                {a.from_cache && (
                  <div className="flex gap-1.5">
                    <dt className="meta">source</dt>
                    <dd className="meta text-fg-muted">cached result, not a fresh model run</dd>
                  </div>
                )}
                {conversation.masked.total > 0 && (
                  <div className="flex gap-1.5">
                    <dt className="meta">hidden</dt>
                    <dd className="meta text-fg-muted">
                      {maskedSummary}{" "}
                      <Link to="privacy" className="text-navy-600 underline-offset-2 hover:underline">
                        see what the AI saw
                      </Link>
                    </dd>
                  </div>
                )}
              </dl>
            </div>
            <div className="flex flex-wrap gap-2 md:flex-col md:items-stretch">
              <Link to="agreement" className="btn btn-primary">
                Draft the agreement
              </Link>
              <button type="button" className="btn btn-secondary" onClick={() => run(true)} disabled={extract.busy}>
                <RefreshCw size={14} className={extract.busy ? "animate-spin" : ""} aria-hidden />
                Check again
              </button>
            </div>
          </>
        ) : notYetChecked || extract.busy ? (
          <>
            <span className="grid h-11 w-11 place-items-center rounded-md border border-line bg-sunken text-navy-600">
              <FileSearch size={20} aria-hidden />
            </span>
            <div>
              <p className="text-base font-semibold text-fg">This chat hasn't been checked yet</p>
              <p className="mt-0.5 text-sm text-fg-muted">
                We'll read <span className="font-mono">{conversation.message_count}</span> messages, find the deal
                terms, and flag anything missing or never agreed. Usually a few seconds.
              </p>
            </div>
            {extract.busy ? (
              <Spinner label="Reading the chat…" />
            ) : (
              <button type="button" className="btn btn-primary" onClick={() => run(false)}>
                Check this chat
              </button>
            )}
          </>
        ) : analysis.loading ? (
          <Skeleton className="h-20 md:col-span-3" />
        ) : (
          <div className="md:col-span-3">
            <ErrorNote>{analysis.error?.message}</ErrorNote>
          </div>
        )}
      </section>

      {extract.error && (
        <ErrorNote
          action={
            <Link to="/" className="btn btn-secondary btn-sm">
              Try a sample
            </Link>
          }
        >
          {extract.error}
        </ErrorNote>
      )}

      {/* ---- Chat and findings, side by side ---- */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <section aria-labelledby="chat-heading" className="min-w-0 lg:sticky lg:top-16 lg:self-start">
          <div className="flex items-baseline justify-between gap-3">
            <h2 id="chat-heading" className="section-title">
              The chat
            </h2>
            <Link
              to="privacy"
              className="mb-2 inline-flex items-center gap-1 text-xs text-fg-faint transition-colors hover:text-navy-600"
            >
              <EyeOff size={12} aria-hidden /> What the AI sees
            </Link>
          </div>
          <div className="panel max-h-[74vh] overflow-y-auto bg-sunken/40 p-3">
            <ChatView
              messages={conversation.messages}
              participants={conversation.participants}
              highlighted={highlighted}
              focusKey={focusKey}
            />
          </div>
        </section>

        <section aria-labelledby="findings-heading" className="min-w-0 space-y-7">
          {a ? (
            <>
              <div>
                <h2 id="findings-heading" className="section-title">
                  What needs attention
                </h2>
                {flags.length === 0 ? (
                  <Notice>Nothing to flag. Every term is stated clearly.</Notice>
                ) : (
                  <AnimatedGroup className="panel divide-y divide-line overflow-hidden" replayKey={a.id}>
                    {flags.map((flag, i) => {
                      const key = `flag-${i}`;
                      return (
                        <FlagCard
                          key={key}
                          flag={flag}
                          selected={selected === key}
                          onSelect={() => select(key, flag.source_message_ids)}
                        />
                      );
                    })}
                  </AnimatedGroup>
                )}
              </div>

              <div>
                <h2 className="section-title">What the chat says was agreed</h2>
                <TermLedger terms={a.terms} missing={a.missing_critical} selectedKey={selected} onSelect={select} />
                <p className="mt-2 text-xs text-fg-faint">Select a term to see the message it came from.</p>
              </div>

              {revised.length > 0 && (
                <div>
                  <h2 className="section-title">How the terms changed</h2>
                  <div className="space-y-3">
                    {revised.map((t, i) => (
                      <RevisionTimeline
                        key={`${t.type}-${i}`}
                        term={t}
                        messages={conversation.messages}
                        onSelect={(ids) => select(`rev-${t.type}-${ids.join("-")}`, ids)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {hasPaymentTerm && (
                <div>
                  <h2 className="section-title">One question the chat can't answer</h2>
                  <MsmeCheck conversationId={conversation.id} onSelect={(ids) => select("msme", ids)} />
                </div>
              )}

              {a.dropped_ungrounded.length > 0 && (
                <details className="border-t border-line pt-4 text-sm">
                  <summary className="flex cursor-pointer list-none items-start gap-2 text-fg-muted">
                    <ShieldAlert size={15} className="mt-0.5 shrink-0 text-fg-faint" aria-hidden />
                    <span>
                      <span className="font-mono">{a.dropped_ungrounded.length}</span> item(s) the AI reported were
                      discarded, because they don't appear in the messages it pointed to
                    </span>
                  </summary>
                  <ul className="mt-2.5 space-y-1 pl-6">
                    {a.dropped_ungrounded.map((d, i) => (
                      <li key={i} className="text-xs text-fg-faint">
                        <span className="font-mono text-fg-muted">{d.type}</span> “{d.value}”: {d.reason}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </>
          ) : (
            !extract.busy && <Notice>Findings appear here once the chat is checked.</Notice>
          )}
          {extract.busy && (
            <div className="space-y-3" aria-hidden>
              <Skeleton className="h-40" />
              <Skeleton className="h-56" />
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
