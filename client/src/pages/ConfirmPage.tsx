import { CircleHelp, PencilLine, ThumbsUp, ThumbsDown } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { DISCLAIMER, Wordmark } from "../components/Shell";
import { ErrorNote, Skeleton } from "../components/ui/Feedback";
import { Stamp } from "../components/ui/Stamp";
import { useAction, useApi } from "../hooks/useApi";
import { PLACEHOLDER } from "../lib/placeholder";
import type { ResponseAction } from "../types/api";

const CHOICES: { action: ResponseAction; label: string; Icon: typeof ThumbsUp; on: string }[] = [
  { action: "agree", label: "Agreed", Icon: ThumbsUp, on: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  {
    action: "suggest_change",
    label: "Change this",
    Icon: PencilLine,
    on: "bg-amber-50 text-amber-700 border-amber-200",
  },
  { action: "ask_question", label: "I have a question", Icon: CircleHelp, on: "bg-navy-50 text-navy-700 border-navy-200" },
];

type Answer = { action: ResponseAction; comment: string; proposal?: "accept" | "reject" };

/** Choices when the sender has proposed new wording for this part. */
const PROPOSAL_CHOICES: {
  key: string;
  action: ResponseAction;
  proposal?: "accept" | "reject";
  label: string;
  Icon: typeof ThumbsUp;
  on: string;
}[] = [
  { key: "accept", action: "agree", proposal: "accept", label: "Accept the change", Icon: ThumbsUp, on: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  { key: "reject", action: "agree", proposal: "reject", label: "Keep it as it was", Icon: ThumbsDown, on: "bg-slate-100 text-slate-700 border-slate-300" },
  { key: "counter", action: "suggest_change", label: "Suggest something else", Icon: PencilLine, on: "bg-amber-50 text-amber-700 border-amber-200" },
  { key: "ask", action: "ask_question", label: "I have a question", Icon: CircleHelp, on: "bg-navy-50 text-navy-700 border-navy-200" },
];

/**
 * What the other party sees. No account, no app, no OTP. It has to feel like
 * a favour between people who trust each other, not a legal document.
 */
export function ConfirmPage() {
  const { token = "" } = useParams();
  const view = useApi(() => api.confirmView(token), [token]);
  const submit = useAction();
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [name, setName] = useState("");
  const [read, setRead] = useState(false);
  const [done, setDone] = useState(false);

  const v = view.data;
  // Blank clauses can't be agreed to, only suggested. They are optional.
  const answered = v ? v.clauses.filter((c) => !c.is_placeholder).every((c) => answers[c.id]) : false;
  const commentsOk = Object.values(answers).every((a) => a.action === "agree" || a.comment.trim().length > 0);

  return (
    <div className="min-h-screen">
      <header className="border-b border-line/70">
        <div className="mx-auto flex h-16 max-w-3xl items-center px-4">
          <Wordmark />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-10">
        {view.loading && <Skeleton className="h-96" />}
        {view.error && <ErrorNote>{view.error.message}</ErrorNote>}

        {v && (done || v.already_used) && (
          <section className="panel grid place-items-center gap-5 p-10 text-center">
            <Stamp tone="ink" size="lg" pressKey={String(done)}>
              Recorded
            </Stamp>
            <p className="max-w-md text-fg">
              {done
                ? "Thank you. Your answers have been sent back."
                : "This link has already been used, so it can't be answered again."}
            </p>
            <p className="text-sm text-fg-faint">{v.notice}</p>
          </section>
        )}

        {v && v.expired && !v.already_used && !done && (
          <ErrorNote>This link has expired. Ask the person who sent it for a new one.</ErrorNote>
        )}

        {v && !v.already_used && !v.expired && !done && (
          <form
            className="space-y-8"
            onSubmit={async (e) => {
              e.preventDefault();
              const result = await submit.run(() =>
                api.confirm(token, {
                  typed_name: name.trim(),
                  read_confirmation: read,
                  answers: v.clauses
                    .filter((c) => answers[c.id])
                    .map((c) => ({
                      clause_id: c.id,
                      action: answers[c.id]!.action,
                      comment: answers[c.id]!.comment.trim() || null,
                      proposal: answers[c.id]!.proposal ?? null,
                    })),
                }),
              );
              if (result) setDone(true);
            }}
          >
            <div>
              <h1 className="text-2xl font-semibold tracking-tight text-fg">
                Just checking we're on the same page
              </h1>
              <p className="mt-3 text-fg-muted">
                Here's a summary of what was agreed over WhatsApp. For each part, tell us if it's right, if
                something should change, or if you have a question.
              </p>
            </div>

            <ol className="panel divide-y divide-line">
              {v.clauses.map((clause, i) => {
                const answer = answers[clause.id];
                return (
                  <li key={clause.id} className="px-5 py-4">
                    <p className="text-xs text-fg-faint">
                      Part {i + 1}
                      {clause.is_placeholder && ", not agreed yet. Optional: suggest what it should say"}
                    </p>
                    <h2 className="font-semibold text-fg">{clause.heading}</h2>
                    <p className="mt-1 font-serif text-[1.05rem] leading-relaxed text-fg">
                      {clause.body.replaceAll(PLACEHOLDER, "(still to be agreed)")}
                    </p>

                    {clause.is_pending && clause.proposed_value && (
                      <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2.5 text-sm text-amber-900">
                        <p className="font-semibold">The sender suggests changing this to:</p>
                        <p className="mt-1 font-serif text-[1.05rem] leading-relaxed text-fg">
                          &ldquo;{clause.proposed_value}&rdquo;
                        </p>
                        <p className="mt-1 text-xs text-amber-800">
                          It only becomes part of the agreement if you accept it.
                        </p>
                      </div>
                    )}

                    <div role="radiogroup" aria-label={`Your answer for ${clause.heading}`} className="mt-4 flex flex-wrap gap-2">
                      {(clause.is_pending && clause.proposed_value
                        ? PROPOSAL_CHOICES.filter((c) => !(clause.is_placeholder && c.key === "reject")).map((c) => ({ ...c, id: c.key }))
                        : CHOICES.filter((c) => !(clause.is_placeholder && c.action === "agree")).map((c) => ({
                            ...c,
                            id: c.action,
                            proposal: undefined as "accept" | "reject" | undefined,
                          }))
                      ).map(({ id, action, proposal, label, Icon, on }) => {
                        const active = answer?.action === action && answer?.proposal === proposal;
                        return (
                          <button
                            key={id}
                            type="button"
                            role="radio"
                            aria-checked={active}
                            onClick={() =>
                              setAnswers((prev) => ({
                                ...prev,
                                [clause.id]: { action, proposal, comment: prev[clause.id]?.comment ?? "" },
                              }))
                            }
                            className={`inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-sm font-medium transition-colors active:translate-y-px ${
                              active ? on : "border-line-strong bg-surface text-fg-muted hover:bg-hover hover:text-fg"
                            }`}
                          >
                            <Icon size={14} aria-hidden /> {label}
                          </button>
                        );
                      })}
                    </div>

                    {answer && answer.action !== "agree" && (
                      <textarea
                        rows={2}
                        className="field mt-3 animate-node-pop"
                        placeholder={answer.action === "suggest_change" ? "What should it say?" : "What would you like to ask?"}
                        value={answer.comment}
                        onChange={(e) =>
                          setAnswers((prev) => ({ ...prev, [clause.id]: { ...answer, comment: e.target.value } }))
                        }
                        aria-label={`Comment on ${clause.heading}`}
                      />
                    )}
                  </li>
                );
              })}
            </ol>

            <div className="panel space-y-4 p-5">
              <label className="block">
                <span className="text-sm font-medium text-fg">Your full name</span>
                <input className="field mt-1.5" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
              </label>
              <label className="flex items-start gap-2.5 text-sm text-fg">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 accent-navy-600"
                  checked={read}
                  onChange={(e) => setRead(e.target.checked)}
                />
                I have read these terms.
              </label>
              <p className="text-xs text-fg-faint">{v.notice}</p>
              {submit.error && <ErrorNote>{submit.error}</ErrorNote>}
              <button
                type="submit"
                className="btn btn-primary"
                disabled={!answered || !commentsOk || !read || name.trim().length < 2 || submit.busy}
              >
                {submit.busy ? "Sending…" : "Send my answers"}
              </button>
              {!answered && <p className="text-xs text-fg-faint">Answer every part to send.</p>}
            </div>
          </form>
        )}

        <p className="mt-10 text-center text-xs text-fg-faint">{DISCLAIMER}</p>
      </main>
    </div>
  );
}
