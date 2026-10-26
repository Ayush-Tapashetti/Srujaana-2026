import { ExternalLink, Link2, Lock, MessageCircle, Paperclip } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import { useAction } from "../hooks/useApi";
import { TERM_LABEL, formatTime } from "../lib/labels";
import type { Agreement, Analysis, Conversation, RecapResponse, SendResponse } from "../types/api";
import { Segmented } from "./motion/Segmented";
import { TransitionPanel } from "./motion/TransitionPanel";
import { ToneMessage } from "./ToneMessage";
import { CopyButton } from "./ui/CopyButton";
import { ErrorNote } from "./ui/Feedback";

const ACK = "Recorded as an acknowledgement. This is not a legal electronic signature.";

const ROUTES = [
  { value: "recap", label: "Recap in WhatsApp", icon: MessageCircle },
  { value: "link", label: "Send a link", icon: Link2 },
] as const;

interface SendPanelProps {
  agreement: Agreement;
  analysis: Analysis | null;
  onAgreement: (a: Agreement) => void;
}

export function SendPanel({ agreement, analysis, onAgreement }: SendPanelProps) {
  const blocked = analysis?.readiness === "red" && !agreement.override_reason;
  const [route, setRoute] = useState<"recap" | "link">("recap");

  if (blocked) return <Blocked agreement={agreement} analysis={analysis} onAgreement={onAgreement} />;

  return (
    <div className="panel">
      <div className="px-5 pt-3">
        <Segmented options={ROUTES} value={route} onChange={setRoute} layoutId="send-route" label="How to get it confirmed" variant="tabs" />
      </div>

      {agreement.override_reason && (
        <p className="flex gap-2 border-b border-line bg-sunken/60 px-5 py-2.5 text-xs text-fg-muted">
          <Lock size={13} className="mt-0.5 shrink-0" aria-hidden />
          <span>
            Sent with an override: “{agreement.override_reason}”. Recorded in the evidence trail; the agreement still
            needs a lawyer's review.
          </span>
        </p>
      )}

      <TransitionPanel activeKey={route}>
        {route === "recap" ? (
          <RecapRoute agreement={agreement} onAgreement={onAgreement} />
        ) : (
          <LinkRoute agreement={agreement} />
        )}
      </TransitionPanel>
    </div>
  );
}

function Blocked({
  agreement,
  analysis,
  onAgreement,
}: {
  agreement: Agreement;
  analysis: Analysis | null;
  onAgreement: (a: Agreement) => void;
}) {
  const [reason, setReason] = useState("");
  const action = useAction();
  const reds = analysis?.flags.filter((f) => f.severity === "red") ?? [];

  return (
    <div className="panel overflow-hidden">
      <div className="border-b border-rose-200 bg-rose-50 px-5 py-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-rose-700">
          <Lock size={14} aria-hidden /> Sending is blocked
        </h3>
        <p className="mt-0.5 text-sm text-rose-800/80">
          {reds.length === 1 ? "One key term is" : `${reds.length} key terms are`} missing or never agreed. Sending now
          would ask the other side to confirm a gap.
        </p>
      </div>
      <ul className="divide-y divide-line">
        {reds.map((f, i) => (
          <li key={i} className="flex items-baseline gap-3 px-5 py-2 text-sm">
            <span className="meta w-24 shrink-0">{TERM_LABEL[f.term_type]}</span>
            <span className="text-fg">{f.title}</span>
          </li>
        ))}
      </ul>

      <form
        className="space-y-2.5 border-t border-line px-5 py-4"
        onSubmit={async (e) => {
          e.preventDefault();
          const next = await action.run(() => api.generate(agreement.conversation_id, reason.trim()));
          if (next) onAgreement(next);
        }}
      >
        <label htmlFor="override" className="block text-sm font-medium text-fg">
          Send anyway, and record why
        </label>
        <textarea
          id="override"
          rows={2}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="For example: we agreed the price on a call and I'll confirm it in the recap"
          className="field"
        />
        <p className="text-xs text-fg-faint">Your reason is stored in the evidence trail. It can't be removed later.</p>
        {action.error && <ErrorNote>{action.error}</ErrorNote>}
        <button type="submit" className="btn btn-danger" disabled={reason.trim().length < 5 || action.busy}>
          Record reason and continue
        </button>
      </form>
    </div>
  );
}

function RecapRoute({ agreement, onAgreement }: { agreement: Agreement; onAgreement: (a: Agreement) => void }) {
  const [recap, setRecap] = useState<RecapResponse | null>(null);
  const load = useAction();

  if (!recap) {
    return (
      <div className="space-y-3 px-5 py-4">
        <p className="text-sm text-fg-muted">
          The easiest way to confirm: paste a short summary into the same WhatsApp chat. The other side just replies.
          No link, nothing to install, no paperwork.
        </p>
        {load.error && <ErrorNote>{load.error}</ErrorNote>}
        <button
          type="button"
          className="btn btn-primary"
          disabled={load.busy}
          onClick={async () => {
            const r = await load.run(() => api.recap(agreement.id));
            if (r) setRecap(r);
          }}
        >
          Write the recap
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="px-5 py-4">
        <ToneMessage tones={recap.tones} />
      </div>
      <AttachReply agreement={agreement} onAgreement={onAgreement} />
      <p className="border-t border-line px-5 py-2.5 text-xs text-fg-faint">{ACK}</p>
    </>
  );
}

function AttachReply({ agreement, onAgreement }: { agreement: Agreement; onAgreement: (a: Agreement) => void }) {
  const [chat, setChat] = useState<Conversation | null>(null);
  const [pick, setPick] = useState<number | null>(null);
  const [name, setName] = useState("");
  const action = useAction();

  return (
    <div className="border-t border-line px-5 py-4">
      <h4 className="flex items-center gap-2 text-sm font-semibold text-fg">
        <Paperclip size={14} aria-hidden /> When they reply, attach it
      </h4>
      <p className="mt-0.5 text-sm text-fg-muted">
        Export the chat again after their reply and upload it. Then pick the message where they confirmed.
      </p>

      {!chat ? (
        <label className="btn btn-secondary btn-sm mt-3 cursor-pointer">
          Upload the updated chat
          <input
            type="file"
            accept=".txt,text/plain"
            className="sr-only"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              const c = await action.run(() => api.upload(file));
              if (c) setChat(c);
            }}
          />
        </label>
      ) : (
        <form
          className="mt-3 space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            if (pick === null) return;
            const next = await action.run(() =>
              api.recapReply(agreement.id, { conversation_id: chat.id, message_index: pick, typed_name: name.trim() }),
            );
            if (next) onAgreement(next);
          }}
        >
          <fieldset className="max-h-56 divide-y divide-line overflow-y-auto rounded-md border border-line">
            <legend className="sr-only">Which message confirms the recap?</legend>
            {chat.messages
              .filter((m) => m.kind === "text")
              .slice(-12)
              .reverse()
              .map((m) => (
                <label
                  key={m.index}
                  className={`flex cursor-pointer gap-2.5 px-3 py-2 text-sm ${pick === m.index ? "bg-navy-50" : "hover:bg-hover"}`}
                >
                  <input
                    type="radio"
                    name="reply"
                    className="mt-1 accent-navy-600"
                    checked={pick === m.index}
                    onChange={() => setPick(m.index)}
                  />
                  <span>
                    <span className="meta mr-1.5">#{m.index}</span>
                    <span className="font-semibold text-fg">{m.sender}:</span> <span className="text-fg-muted">{m.body}</span>
                  </span>
                </label>
              ))}
          </fieldset>
          <input
            className="field"
            placeholder="Their name, as they'd write it"
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-label="Name of the person who replied"
          />
          <button type="submit" className="btn btn-primary btn-sm" disabled={pick === null || name.trim().length < 2 || action.busy}>
            Attach this reply as confirmation
          </button>
        </form>
      )}
      {action.error && (
        <div className="mt-3">
          <ErrorNote>{action.error}</ErrorNote>
        </div>
      )}
    </div>
  );
}

function LinkRoute({ agreement }: { agreement: Agreement }) {
  const [sent, setSent] = useState<SendResponse | null>(null);
  const action = useAction();
  const url = sent ? `${window.location.origin}${sent.confirm_url}` : "";

  if (!sent) {
    return (
      <div className="space-y-3 px-5 py-4">
        <p className="text-sm text-fg-muted">
          A one-time page where the other side can agree to each clause, suggest a change, or ask a question. They
          don't need an account.
        </p>
        {action.error && <ErrorNote>{action.error}</ErrorNote>}
        <button
          type="button"
          className="btn btn-primary"
          disabled={action.busy}
          onClick={async () => {
            const r = await action.run(() => api.send(agreement.id));
            if (r) setSent(r);
          }}
        >
          Create a confirmation link
        </button>
      </div>
    );
  }

  const tones = sent.tones.map((t) => ({ ...t, message: t.message.replace(sent.confirm_url, url) }));

  return (
    <>
      <div className="space-y-2 border-b border-line px-5 py-4">
        <p className="meta">Valid until {formatTime(sent.expires_at)} / works once</p>
        <p className="break-all font-mono text-xs text-navy-700">{url}</p>
        <div className="flex flex-wrap gap-2 pt-1">
          <CopyButton text={url} label="Copy link" done="Link copied" />
          <a href={sent.confirm_url} target="_blank" rel="noreferrer" className="btn btn-ghost btn-sm">
            <ExternalLink size={13} aria-hidden /> Open as the other side
          </a>
        </div>
      </div>
      <div className="px-5 py-4">
        <ToneMessage tones={tones} />
      </div>
      <p className="border-t border-line px-5 py-2.5 text-xs text-fg-faint">{ACK}</p>
    </>
  );
}
