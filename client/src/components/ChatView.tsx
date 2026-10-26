import { Mic } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import { formatTime } from "../lib/labels";
import type { Message } from "../types/api";

interface ChatViewProps {
  messages: Message[];
  participants: string[];
  /** Message indices to highlight: the sources of the selected term or flag. */
  highlighted: number[];
  /** Changes on every selection, so the highlighter sweeps again. */
  focusKey: number;
  className?: string;
}

/**
 * The original conversation. Selecting a term or flag sweeps a pale navy
 * highlighter across the message it came from, so every claim the app makes
 * can be checked against the chat. (Navy, not yellow: yellow means "vague".)
 */
export function ChatView({ messages, participants, highlighted, focusKey, className = "" }: ChatViewProps) {
  const lit = useMemo(() => new Set(highlighted), [highlighted]);
  const refs = useRef(new Map<number, HTMLLIElement>());
  const leftSide = participants[0];

  useEffect(() => {
    const first = highlighted.length ? Math.min(...highlighted) : null;
    if (first === null) return;
    refs.current.get(first)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focusKey, highlighted]);

  if (!messages.length) {
    return <p className="p-5 text-sm text-fg-muted">This chat has no messages.</p>;
  }

  return (
    <ol className={`space-y-2 ${className}`} aria-label="Chat messages">
      {messages.map((m) => {
        if (m.kind === "system") {
          return (
            <li key={m.index} className="py-1 text-center text-xs text-fg-faint">
              {m.body}
            </li>
          );
        }

        const mine = m.sender !== leftSide;
        const isLit = lit.has(m.index);

        return (
          <li
            key={m.index}
            ref={(el) => {
              if (el) refs.current.set(m.index, el);
              else refs.current.delete(m.index);
            }}
            className={`flex ${mine ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[86%] rounded-md border px-3 py-2 transition-colors ${
                mine ? "rounded-br-sm border-navy-100 bg-navy-50/60" : "rounded-bl-sm border-line bg-surface"
              } ${isLit ? "!border-navy-400 ring-1 ring-navy-400" : ""}`}
            >
              <div className="mb-0.5 flex items-baseline justify-between gap-4">
                <span className={`text-xs font-semibold ${mine ? "text-navy-700" : "text-fg"}`}>{m.sender}</span>
                <span className="meta whitespace-nowrap">
                  #{m.index} {formatTime(m.timestamp)}
                </span>
              </div>

              {m.kind === "attachment" ? (
                <p className="flex items-center gap-1.5 rounded-sm border border-dashed border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-700">
                  <Mic size={12} aria-hidden />
                  Voice note or image. Not analysed: add any terms it carries yourself.
                </p>
              ) : m.kind === "deleted" ? (
                <p className="text-sm italic text-fg-faint">This message was deleted</p>
              ) : (
                <p className="whitespace-pre-wrap break-words text-sm text-fg">
                  <span key={isLit ? `lit-${focusKey}` : "plain"} className={isLit ? "marked" : ""}>
                    {m.body}
                  </span>
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
