import { CircleAlert, CircleCheck, CircleDot } from "lucide-react";
import type { Severity } from "../types/api";

/*
 * Status colours. Strict domain mapping, one meaning everywhere (D7):
 *   red     critical term missing or in unresolved conflict
 *   yellow  term present but vague or ambiguous
 *   green   term clear or record verified
 */
export const STATUS_CLASSES: Record<Severity, string> = {
  red: "bg-rose-50 text-rose-700 border-rose-200",
  yellow: "bg-amber-50 text-amber-700 border-amber-200",
  green: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

const ICON: Record<Severity, typeof CircleCheck> = {
  red: CircleAlert,
  yellow: CircleDot,
  green: CircleCheck,
};

const WORD: Record<Severity, string> = { red: "Red", yellow: "Yellow", green: "Green" };

interface RiskBadgeProps {
  severity: Severity;
  /** The text label. Colour is never the only signal. */
  label?: string;
  className?: string;
}

export function RiskBadge({ severity, label, className = "" }: RiskBadgeProps) {
  const Icon = ICON[severity];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-sm border px-1.5 py-px text-xs font-medium ${STATUS_CLASSES[severity]} ${className}`}
    >
      <Icon size={12} strokeWidth={2.25} aria-hidden />
      {label ?? WORD[severity]}
    </span>
  );
}

export function severityTone(severity: Severity): "red" | "amber" | "green" {
  return severity === "yellow" ? "amber" : severity;
}
