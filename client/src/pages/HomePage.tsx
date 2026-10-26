import { ArrowRight, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useIsland } from "../components/motion/StatusIsland";
import { TextEffect } from "../components/motion/Text";
import { UploadZone } from "../components/UploadZone";
import { ErrorNote, Skeleton } from "../components/ui/Feedback";
import { useAction, useApi } from "../hooks/useApi";
import { formatTime, sampleTitle } from "../lib/labels";

/** What each pre-loaded chat demonstrates, so a judge can pick one fast. */
const SAMPLE_HINT: Record<string, string> = {
  "clear deal": "Every term stated. Expect it ready to confirm.",
  "vague timing": "\"Will send soon\", \"payment later\". Present but vague.",
  "price missing": "Nobody ever names a price.",
  "price revised twice": "48000, then 50000, then 52000, each accepted.",
  "unresolved conflict": "A lower price is proposed and never answered.",
  "hinglish numbers in words": "\"Do sau\", \"dedh sau\", then both settle on 180.",
  "long chat 300 messages": "Three months of chat; terms buried in small talk.",
  "two deals one chat": "Chairs and tables in one chat. A documented limit.",
  "prompt injection": "A message tells the AI to report the price as 1 rupee.",
  "group chat": "Three people. A documented limit.",
  "sarcastic ok": "\"Ok sure 🙄\" that means no. Caught, so it isn't counted as agreement.",
  "price revised back": "4500, then 4200, then back to 4500.",
  "pii heavy": "Phones, PAN, GSTIN, Aadhaar, email and UPI to hide.",
  "ambiguous dates": "Every date fits both DD/MM and MM/DD.",
  "us date format": "A phone set to MM/DD/YY.",
  "format torture": "24-hour clock, multi-line, deleted messages, odd encoding.",
  "no deal small talk": "Small talk only. No deal was ever made.",
  "one sided notes": "Only one person writes.",
  "msme 60 day terms": "60-day payment to a small supplier.",
};

const FEATURES = [
  ["Every term, traced to its message", "Price, delivery, payment: each one points to the line in the chat it came from."],
  ["Gaps flagged before they become disputes", "Missing, vague or never-agreed terms, with the section of law that makes them matter."],
  ["A record nobody can quietly change", "Each step is fingerprinted, so any later edit shows up."],
] as const;

export function HomePage() {
  const navigate = useNavigate();
  const samples = useApi(() => api.samples(), []);
  const mine = useApi(() => api.myConversations(), []);
  const action = useAction();
  const island = useIsland();

  const open = async (load: () => Promise<{ id: number }>) => {
    const stop = island.busy("Reading the chat");
    const conversation = await action.run(load);
    stop();
    if (conversation) {
      island.notify("success", "Chat added");
      navigate(`/c/${conversation.id}`);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:py-16">
      <section className="grid items-start gap-10 lg:grid-cols-[1fr_minmax(0,31rem)] lg:gap-16">
        <div className="max-w-xl">
          <TextEffect as="h1" className="text-3xl font-semibold leading-[1.12] tracking-tight text-fg sm:text-4xl">
            Your deal is already in the chat. Let's get it in writing.
          </TextEffect>
          <p className="mt-4 text-lg leading-relaxed text-fg-muted">
            Upload a WhatsApp conversation with a customer or supplier. You'll see what was agreed, what was never
            settled, and a plain agreement you can both confirm, without asking anyone to sign a contract.
          </p>

          <dl className="mt-8 divide-y divide-line border-y border-line">
            {FEATURES.map(([title, body]) => (
              <div key={title} className="py-3.5">
                <dt className="text-sm font-semibold text-fg">{title}</dt>
                <dd className="mt-0.5 text-sm text-fg-muted">{body}</dd>
              </div>
            ))}
          </dl>

          <p className="mt-6 flex items-start gap-2 text-xs leading-relaxed text-fg-faint">
            <ShieldCheck size={14} className="mt-px shrink-0" aria-hidden />
            Phone numbers, PAN, Aadhaar, GSTIN and email addresses are hidden before any text is sent for analysis.
          </p>
        </div>

        <div className="space-y-3">
          <UploadZone
            busy={action.busy}
            onFile={(file) => open(() => api.upload(file))}
            onPaste={(text) => open(() => api.paste(text))}
          />
          {action.error && <ErrorNote>{action.error}</ErrorNote>}
        </div>
      </section>

      {mine.data && mine.data.length > 0 && (
        <section className="mt-16 lg:mt-20" aria-labelledby="mine-heading">
          <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line pb-3">
            <h2 id="mine-heading" className="text-lg font-semibold tracking-tight text-fg">
              Your chats
            </h2>
            <p className="meta">stored on this server</p>
          </div>
          <ul className="divide-y divide-line">
            {mine.data.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => navigate(`/c/${c.id}`)}
                  className="group grid w-full grid-cols-[3rem_1fr_auto] items-center gap-4 px-1 py-3.5 text-left transition-colors hover:bg-hover sm:grid-cols-[3rem_1fr_9rem_auto]"
                >
                  <span className="meta">#{c.id}</span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-fg">{c.label}</span>
                    <span className="block truncate text-sm text-fg-muted">
                      {c.participants.join(" and ") || "No participants found"} · {c.message_count} messages
                    </span>
                  </span>
                  <span className="meta hidden text-right sm:block">{c.created_at ? formatTime(c.created_at) : ""}</span>
                  <ArrowRight
                    size={15}
                    className="text-fg-faint transition-transform group-hover:translate-x-0.5 group-hover:text-navy-600"
                    aria-hidden
                  />
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-16 lg:mt-20" aria-labelledby="samples-heading">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line pb-3">
          <h2 id="samples-heading" className="text-lg font-semibold tracking-tight text-fg">
            Or open a sample chat
          </h2>
          <p className="text-xs text-fg-faint">Written by our team. No real customer data.</p>
        </div>

        {samples.loading && (
          <div className="mt-3 space-y-2">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        )}
        {samples.error && (
          <div className="mt-3">
            <ErrorNote>{samples.error.message}</ErrorNote>
          </div>
        )}
        {samples.data?.length === 0 && (
          <p className="py-4 text-sm text-fg-muted">
            No samples loaded. Put .txt chats in <code className="font-mono">server/app/data/samples</code> and restart
            the server.
          </p>
        )}

        <ul className="divide-y divide-line">
          {samples.data?.map((s) => {
            const title = sampleTitle(s.label);
            const code = s.label.match(/^T\d+/i)?.[0] ?? `#${s.id}`;
            return (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => navigate(`/c/${s.id}`)}
                  className="group grid w-full grid-cols-[3rem_1fr_auto] items-center gap-4 px-1 py-3.5 text-left transition-colors hover:bg-hover sm:grid-cols-[3rem_1fr_7rem_auto]"
                >
                  <span className="meta">{code}</span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-fg">{title}</span>
                    <span className="block truncate text-sm text-fg-muted">
                      {SAMPLE_HINT[title.toLowerCase()] ?? s.participants.join(" and ")}
                    </span>
                  </span>
                  <span className="meta hidden text-right sm:block">{s.message_count} messages</span>
                  <ArrowRight
                    size={15}
                    className="text-fg-faint transition-transform group-hover:translate-x-0.5 group-hover:text-navy-600"
                    aria-hidden
                  />
                </button>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
