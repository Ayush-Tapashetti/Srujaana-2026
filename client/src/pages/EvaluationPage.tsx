import { CircleCheck, CircleMinus, CircleX, Terminal } from "lucide-react";
import { api } from "../api/client";
import { AnimatedNumber } from "../components/motion/AnimatedNumber";
import { RiskBadge } from "../components/RiskBadge";
import { CopyButton } from "../components/ui/CopyButton";
import { ErrorNote, Notice, Skeleton } from "../components/ui/Feedback";
import { useApi } from "../hooks/useApi";
import type { CheckGroup } from "../types/api";

function Mark({ passed, skipped }: { passed: boolean; skipped?: boolean }) {
  if (skipped) return <CircleMinus size={15} className="text-fg-faint" aria-label="not run here" />;
  return passed ? (
    <CircleCheck size={15} className="text-emerald-700" aria-label="passed" />
  ) : (
    <CircleX size={15} className="text-rose-700" aria-label="failed" />
  );
}

function Group({ group }: { group: CheckGroup }) {
  const all = group.passed === group.total;
  return (
    <details className="panel group overflow-hidden" open={!all}>
      <summary className="flex cursor-pointer list-none items-center gap-4 px-4 py-3 hover:bg-hover">
        <span className="min-w-[4.5rem] font-mono text-lg font-semibold text-fg">
          <AnimatedNumber value={group.passed} />/{group.total}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-fg">{group.title}</span>
          <span className="block text-xs text-fg-muted">{group.description}</span>
        </span>
        <RiskBadge severity={all ? "green" : "red"} label={all ? "All pass" : "Failing"} />
      </summary>
      <ul className="divide-y divide-line border-t border-line">
        {group.rows.map((r) => (
          <li key={r.id} className="grid grid-cols-[1.25rem_3rem_1fr] items-start gap-3 px-4 py-2 text-sm">
            <span className="mt-0.5">
              <Mark passed={r.passed} skipped={r.skipped} />
            </span>
            <span className="meta mt-0.5">{r.id}</span>
            <span className="min-w-0">
              <span className="block text-fg">{r.scenario}</span>
              <span className="block truncate text-xs text-fg-faint">{r.detail}</span>
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}

/**
 * P1-5. What we tested, in the app. The live half runs on every load and
 * needs no AI. The AI half is the last recorded run, with its date, model
 * and prompt version, so a stale number can't pass for a current one.
 */
export function EvaluationPage() {
  const report = useApi(() => api.evaluation(), []);
  const r = report.data;

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-10 sm:px-6">
      <header className="max-w-2xl">
        <h1 className="text-2xl font-semibold tracking-tight text-fg">How well it works</h1>
        <p className="mt-2 text-fg-muted">
          Every number here comes from the labelled test chats in the repository. Failures are shown, not hidden,
          including the cases we know it gets wrong.
        </p>
      </header>

      {report.error && <ErrorNote>{report.error.message}</ErrorNote>}
      {report.loading && !r && <Skeleton className="h-72" />}

      {r && !r.fixtures_found && (
        <Notice>The labelled test chats aren't in this build, so the live checks can't run.</Notice>
      )}

      {r && r.fixtures_found && (
        <section aria-labelledby="live-heading" className="space-y-3">
          <div className="flex items-baseline justify-between gap-3">
            <h2 id="live-heading" className="section-title mb-0">
              Checked live, just now
            </h2>
            <span className="meta">no AI used</span>
          </div>
          {r.live.map((g) => (
            <Group key={g.title} group={g} />
          ))}
        </section>
      )}

      {r && (
        <section aria-labelledby="ai-heading" className="space-y-3">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 id="ai-heading" className="section-title mb-0">
              AI extraction, last recorded run
            </h2>
            {r.ai && (
              <span className="meta">
                {new Date(r.ai.ran_at).toLocaleString("en-IN")} · {r.ai.model} · prompt {r.ai.prompt_version}
                {r.ai.fresh ? " · fresh" : " · cache allowed"}
              </span>
            )}
          </div>

          {!r.ai ? (
            <div className="panel p-5">
              <p className="text-sm font-semibold text-fg">Not yet run on this machine</p>
              <p className="mt-1 text-sm text-fg-muted">
                This runs every labelled chat through the real model, so it uses your API quota. Run it once from
                a terminal, then reload this page.
              </p>
              <div className="well mt-3 flex items-center justify-between gap-3 px-3 py-2">
                <code className="flex items-center gap-2 font-mono text-xs text-fg">
                  <Terminal size={13} className="text-fg-faint" aria-hidden /> {r.how_to_run}
                </code>
                <CopyButton text={r.how_to_run} />
              </div>
            </div>
          ) : (
            <>
              {r.ai.stale && (
                <Notice>
                  The prompt has changed since this run (now {r.ai.current_prompt_version}). Run it again before
                  quoting these numbers.
                </Notice>
              )}
              <div className="panel grid gap-4 p-5 sm:grid-cols-3">
                <div>
                  <p className="font-mono text-2xl font-semibold text-fg">
                    <AnimatedNumber value={r.ai.passed} />/{r.ai.total}
                  </p>
                  <p className="text-xs text-fg-muted">chats matched their label</p>
                </div>
                <div>
                  <p className="font-mono text-2xl font-semibold text-fg">
                    <AnimatedNumber value={r.ai.rows.filter((x) => x.known_failure && !x.passed).length} />
                  </p>
                  <p className="text-xs text-fg-muted">documented failures, as expected</p>
                </div>
                <div>
                  <p className="font-mono text-2xl font-semibold text-fg">
                    <AnimatedNumber value={r.ai.dropped_ungrounded} />
                  </p>
                  <p className="text-xs text-fg-muted">AI claims discarded by the grounding check</p>
                </div>
              </div>
              <div className="panel overflow-x-auto">
                <table className="w-full min-w-[40rem] text-left text-sm">
                  <thead className="border-b border-line bg-sunken text-xs text-fg-muted">
                    <tr>
                      <th scope="col" className="px-4 py-2 font-medium">Chat</th>
                      <th scope="col" className="px-2 py-2 font-medium">Scenario</th>
                      <th scope="col" className="px-2 py-2 font-medium">Expected</th>
                      <th scope="col" className="px-2 py-2 font-medium">Actual</th>
                      <th scope="col" className="px-4 py-2 font-medium">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {r.ai.rows.map((row) => (
                      <tr key={row.id} className="align-top">
                        <td className="px-4 py-2 font-mono text-xs text-fg-muted">{row.id}</td>
                        <td className="px-2 py-2">
                          <span className="block text-fg">{row.scenario}</span>
                          {row.note && <span className="block text-xs text-fg-faint">{row.note}</span>}
                        </td>
                        <td className="px-2 py-2 font-mono text-xs">{row.expected}</td>
                        <td className="px-2 py-2 font-mono text-xs">{row.actual}</td>
                        <td className="px-4 py-2">
                          {row.passed ? (
                            <RiskBadge severity="green" label="Pass" />
                          ) : row.known_failure ? (
                            <RiskBadge severity="yellow" label="Known limit" />
                          ) : (
                            <RiskBadge severity="red" label="Fail" />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}
    </div>
  );
}
