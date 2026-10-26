import { BookOpen, ExternalLink } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import { Segmented } from "../components/motion/Segmented";
import { ErrorNote, Notice, Skeleton } from "../components/ui/Feedback";
import { useApi } from "../hooks/useApi";

/** Stated plainly, because a legal tool that hides its limits is dangerous. */
const LIMITS: { heading: string; points: string[] }[] = [
  {
    heading: "What the evidence trail proves",
    points: [
      "It shows nothing changed after the chat was uploaded. It can't show the chat was genuine before that, or that it wasn't edited before export.",
      "It supports the hash disclosure in Part A of the section 63(4) certificate. It does not replace the expert's Part B, or a court's decision.",
    ],
  },
  {
    heading: "What confirmation means",
    points: ["A confirmation here is an acknowledgement, not a legal electronic signature. Nobody's identity is verified."],
  },
  {
    heading: "What it reads",
    points: [
      "Text only. Voice notes and images are spotted and flagged, but not listened to or read.",
      "English and Hinglish chats. The agreement is written in English.",
      "Chats between two people. Group chats are flagged, because we can't tell who the two sides are.",
      "Two separate deals in one chat may be mixed together.",
    ],
  },
  {
    heading: "Where it can be wrong",
    points: [
      "Obvious sarcasm (an eye-roll emoji, an exaggerated extra demand, a phrase like \"yeah right\") is not counted as agreement. Subtle sarcasm with none of those signs, or an \"ok\" that answers a different question, can still read as agreement. Ask the other side to confirm explicitly.",
      "Vague wording is judged by an AI model and can be missed. When we can't trace a term to a message, we show it as missing rather than guess.",
    ],
  },
  {
    heading: "Privacy",
    points: [
      "Phone numbers, PAN, Aadhaar, GSTIN, email and UPI IDs are hidden before any text goes to the AI model. Names are not, because they're part of the deal.",
      "The other person in the chat never agreed to it being analysed. Use sample or your own test chats for trying this out.",
    ],
  },
];

export function LimitsPage() {
  const [state, setState] = useState("KA");
  const states = useApi(() => api.stampStates(), []);
  const guidance = useApi(() => api.stamp(state), [state]);
  const g = guidance.data;

  return (
    <div className="mx-auto grid max-w-7xl gap-12 px-4 py-10 sm:px-6 lg:grid-cols-2 lg:py-14">
      <section aria-labelledby="limits-heading">
        <h1 id="limits-heading" className="text-2xl font-semibold tracking-tight text-fg">
          What this can and can't do
        </h1>
        <p className="mt-3 max-w-prose text-fg-muted">
          This is decision support, not legal advice. It helps you see what's in a chat and what isn't. Check
          anything important with a lawyer.
        </p>
        <div className="mt-8 space-y-7">
          {LIMITS.map((group) => (
            <div key={group.heading}>
              <h2 className="font-semibold text-fg">{group.heading}</h2>
              <ul className="mt-2 space-y-2">
                {group.points.map((p) => (
                  <li key={p} className="flex gap-3 text-sm leading-relaxed text-fg-muted">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 bg-line-strong" aria-hidden />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="stamp-heading" className="lg:pt-2">
        <div className="panel p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="stamp-heading" className="text-xl font-semibold text-fg">
              Stamp duty
            </h2>
            <Segmented
              options={(states.data ?? [{ code: "KA", name: "Karnataka" }]).map((s) => ({ value: s.code, label: s.name }))}
              value={state}
              onChange={setState}
              layoutId="stamp-state"
              label="State"
            />
          </div>

          {guidance.loading && <Skeleton className="mt-5 h-64" />}
          {guidance.error && (
            <div className="mt-5">
              <ErrorNote>{guidance.error.message}</ErrorNote>
            </div>
          )}

          {g && (
            <div className="mt-5 space-y-5">
              <p className="font-serif text-lg leading-relaxed text-fg">{g.headline}</p>
              <p className="text-sm text-fg-muted">{g.plain_language}</p>

              <ul className="space-y-2.5">
                {g.points.map((p) => (
                  <li key={p.text} className="flex gap-2.5 text-sm">
                    <BookOpen size={15} className="mt-0.5 shrink-0 text-fg-faint" aria-hidden />
                    <span className="text-fg-muted">
                      <span className="font-semibold text-fg">
                        {p.statute}, {p.section}.
                      </span>{" "}
                      {p.text}
                    </span>
                  </li>
                ))}
              </ul>

              <div>
                <h3 className="text-sm font-semibold text-fg">Getting it stamped</h3>
                <ol className="mt-2 space-y-1.5">
                  {g.checklist.map((step, i) => (
                    <li key={step} className="grid grid-cols-[1.5rem_1fr] text-sm text-fg-muted">
                      <span className="tabular-nums text-fg-faint">{i + 1}.</span>
                      {step}
                    </li>
                  ))}
                </ol>
              </div>

              <Notice>
                {g.duty_rate
                  ? `Rate: ${g.duty_rate}.`
                  : "We don't show a duty rate. Rates are set by each state and depend on the type of document, so we'd rather show none than a wrong one."}{" "}
                {g.state_act && `${g.state_name} follows the ${g.state_act}.`}
              </Notice>

              {g.source_url && (
                <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-fg-faint">
                  <a href={g.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-fg hover:underline">
                    {g.authority} <ExternalLink size={12} aria-hidden />
                  </a>
                  <span>Last checked {g.last_verified}</span>
                </p>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
