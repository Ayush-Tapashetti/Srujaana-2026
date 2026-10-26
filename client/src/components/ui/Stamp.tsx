import type { ReactNode } from "react";

type Tone = "ink" | "red" | "amber" | "green" | "neutral";

/* Seal colours follow the status mapping exactly: rose, amber, emerald.
   "ink" (navy) is for records: Confirmed, Recorded. */
const TONE: Record<Tone, string> = {
  ink: "text-navy-600 bg-navy-50/70",
  red: "text-rose-700 bg-rose-50/70",
  amber: "text-amber-700 bg-amber-50/70",
  green: "text-emerald-700 bg-emerald-50/70",
  neutral: "text-fg-muted bg-sunken",
};

interface StampProps {
  tone: Tone;
  children: ReactNode;
  /** Second line inside the seal, set in mono, e.g. "AT EVENT 3". */
  sub?: ReactNode;
  size?: "md" | "lg";
  /** Changing this replays the press, so a new verdict lands as a new seal. */
  pressKey?: string | number;
  className?: string;
}

/**
 * The verdict seal: the one ornament in the interface. An official mark on a
 * legal record, set with a thin double rule and a slight tilt. Seals are
 * lettered in capitals, which is the only place the interface uses them.
 */
export function Stamp({ tone, children, sub, size = "md", pressKey, className = "" }: StampProps) {
  return (
    <span className={`inline-flex ${className}`} aria-live="polite">
      <span
        key={`seal-${pressKey ?? "static"}`}
        className={`seal animate-seal-press ${TONE[tone]} ${size === "lg" ? "text-base" : "text-xs"}`}
      >
        <span>{children}</span>
        {sub && <span className="mt-0.5 font-mono text-2xs font-medium tracking-[0.08em] opacity-80">{sub}</span>}
      </span>
    </span>
  );
}
