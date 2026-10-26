import { ArrowLeft, EyeOff, ShieldCheck, ShieldX } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Segmented } from "../components/motion/Segmented";
import { ErrorNote, Notice, Skeleton } from "../components/ui/Feedback";
import { Stamp } from "../components/ui/Stamp";
import { useApi } from "../hooks/useApi";
import type { MaskedLine } from "../types/api";
import { useConversation } from "./ConversationLayout";

const TOKEN = /(<[A-Z]+_\d+>)/;

const LABEL: Record<string, string> = {
  PHONE: "phone number",
  EMAIL: "email",
  PAN: "PAN",
  AADHAAR: "Aadhaar",
  GSTIN: "GSTIN",
  UPI: "UPI ID",
};

type Segment = { text: string; token?: string };

/**
 * Lines up the original with what was sent. Masking only replaces values,
 * so the text between tokens is identical in both, and whatever sits
 * between those shared pieces in the original is the hidden value.
 */
function align(original: string, sent: string): { before: Segment[]; after: Segment[] } | null {
  const parts = sent.split(TOKEN);
  const before: Segment[] = [];
  const after: Segment[] = [];
  let pos = 0;
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i] ?? "";
    if (i % 2 === 0) {
      if (!original.startsWith(part, pos)) return null;
      if (part) {
        before.push({ text: part });
        after.push({ text: part });
      }
      pos += part.length;
    } else {
      const next = parts[i + 1] ?? "";
      const end = next ? original.indexOf(next, pos) : i + 1 === parts.length - 1 ? original.length : -1;
      if (end < pos) return null;
      before.push({ text: original.slice(pos, end), token: part });
      after.push({ text: part, token: part });
      pos = end;
    }
  }
  return pos === original.length ? { before, after } : null;
}

function Row({ line, mode }: { line: MaskedLine; mode: "both" | "sent" }) {
  const aligned = line.sent && line.masked ? align(line.original, line.sent) : null;

  const original = aligned
    ? aligned.before.map((s, i) =>
        s.token ? (
          <mark key={i} className="rounded-sm bg-amber-50 px-0.5 text-amber-800 ring-1 ring-amber-200">
            {s.text}
          </mark>
        ) : (
          <span key={i}>{s.text}</span>
        ),
      )
    : line.original;

  const sent = line.withheld ? (
    <span className="italic text-rose-700">Withheld: reads as an instruction to an AI, so it is never sent.</span>
  ) : line.sent === null ? (
    <span className="italic text-fg-faint">Not sent (system line)</span>
  ) : aligned ? (
    aligned.after.map((s, i) =>
      s.token ? (
        <span key={i} className="rounded-sm border border-navy-200 bg-navy-50 px-1 font-mono text-[0.8em] text-navy-700">
          {s.text}
        </span>
      ) : (
        <span key={i}>{s.text}</span>
      ),
    )
  ) : (
    line.sent
  );

  return (
    <li className={`grid gap-x-6 gap-y-1 px-4 py-2.5 text-sm ${mode === "both" ? "md:grid-cols-2" : ""}`}>
      {mode === "both" && (
        <div className="min-w-0">
          <span className="meta mr-2">#{line.index}</span>
          <span className="font-medium text-fg-muted">{line.sender ?? "system"}: </span>
          <span className="break-words text-fg">{original}</span>
        </div>
      )}
      <div className={`min-w-0 ${mode === "both" ? "md:border-l md:border-line md:pl-6" : ""}`}>
        {mode === "sent" && <span className="meta mr-2">#{line.index}</span>}
        <span className="font-medium text-fg-muted">{line.sender ?? "system"}: </span>
        <span className="break-words text-fg">{sent}</span>
      </div>
    </li>
  );
}

/** P1-4. The before/after of D6, built from the real transcript. */
export function MaskedPreviewPage() {
  const conversation = useConversation();
  const preview = useApi(() => api.maskedPreview(conversation.id), [conversation.id]);
  const [mode, setMode] = useState<"both" | "sent">("both");
  const [onlyChanged, setOnlyChanged] = useState(true);

  const p = preview.data;
  const lines = useMemo(
    () => (p?.lines ?? []).filter((l) => !onlyChanged || l.masked || l.withheld),
    [p, onlyChanged],
  );

  return (
    <div className="space-y-6">
      <Link to=".." relative="path" className="inline-flex items-center gap-1 text-xs text-fg-faint hover:text-fg">
        <ArrowLeft size={12} aria-hidden /> Back to the check
      </Link>

      <section className="panel grid gap-5 p-5 md:grid-cols-[auto_1fr] md:items-center md:gap-8">
        <div className="grid min-h-[5rem] min-w-[12rem] place-items-center md:border-r md:border-line md:pr-8">
          {p ? (
            <Stamp tone={p.leak_check_passed ? "green" : "red"} size="lg" sub={`${p.total} HIDDEN`}>
              {p.leak_check_passed ? "Nothing leaks" : "Leak found"}
            </Stamp>
          ) : (
            <Skeleton className="h-16 w-40" />
          )}
        </div>
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-base font-semibold text-fg">
            <EyeOff size={16} className="text-fg-faint" aria-hidden /> What the AI is shown
          </h2>
          <p className="mt-1 text-sm text-fg-muted">
            Before any text leaves our server, each phone number, email, PAN, Aadhaar, GSTIN and UPI ID is swapped
            for a placeholder. The same number gets the same placeholder everywhere, and the real values are put
            back only after the AI replies. Names stay: they are what the agreement needs.
          </p>
          {p && p.tokens.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {p.tokens.map((t) => (
                <li key={t.token} className="rounded-sm border border-line bg-surface px-2 py-0.5 text-xs text-fg-muted">
                  <span className="font-mono text-navy-700">{t.token}</span> {LABEL[t.label] ?? t.label.toLowerCase()},{" "}
                  {t.occurrences}×
                </li>
              ))}
            </ul>
          )}
          {p && (
            <p className="meta mt-3 flex items-center gap-1.5">
              {p.leak_check_passed ? (
                <ShieldCheck size={12} className="text-emerald-700" aria-hidden />
              ) : (
                <ShieldX size={12} className="text-rose-700" aria-hidden />
              )}
              re-scanned every sent line for identifiers · prompt {p.prompt_version}
            </p>
          )}
        </div>
      </section>

      {preview.error && <ErrorNote>{preview.error.message}</ErrorNote>}

      <section aria-labelledby="lines-heading">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 id="lines-heading" className="section-title mb-0">
            {mode === "both" ? "As written, and as sent" : "Exactly as sent"}
          </h2>
          <div className="flex flex-wrap items-center gap-4">
            <label className="inline-flex items-center gap-2 text-sm text-fg-muted">
              <input
                type="checkbox"
                checked={onlyChanged}
                onChange={(e) => setOnlyChanged(e.target.checked)}
                className="h-4 w-4 rounded-sm border-line-input accent-navy-600"
              />
              Only changed lines
            </label>
            <Segmented
              layoutId="mask-mode"
              label="View"
              value={mode}
              onChange={setMode}
              options={[
                { value: "both", label: "Side by side" },
                { value: "sent", label: "Sent only" },
              ]}
            />
          </div>
        </div>

        {preview.loading && !p ? (
          <Skeleton className="h-64" />
        ) : lines.length === 0 ? (
          <Notice>
            {onlyChanged
              ? "No line needed changing: this chat has no phone numbers, IDs or emails, and nothing reads as an instruction to an AI."
              : "This chat has no messages."}
          </Notice>
        ) : (
          <div className="panel overflow-hidden">
            {mode === "both" && (
              <div className="hidden grid-cols-2 gap-x-6 border-b border-line bg-sunken px-4 py-2 text-xs font-medium text-fg-muted md:grid">
                <span>In the chat</span>
                <span className="pl-6">Sent to the AI</span>
              </div>
            )}
            <ul className="divide-y divide-line">
              {lines.map((line) => (
                <Row key={line.index} line={line} mode={mode} />
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
