/*
 * Option switcher in two forms, both with a highlight that slides to the
 * chosen option (pattern: Motion Primitives, "Animated Background").
 *
 *   variant="tabs"     text tabs over a hairline, with a 2px navy underline
 *   variant="segment"  a sunken track holding a white, bordered pill
 *
 * Written for this project; no code copied.
 */
import { motion } from "motion/react";
import type { LucideIcon } from "lucide-react";

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
  icon?: LucideIcon;
}

interface SegmentedProps<T extends string> {
  options: readonly SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Unique per control, so highlights don't jump between controls. */
  layoutId: string;
  label: string;
  variant?: "tabs" | "segment";
}

const SLIDE = { type: "spring", bounce: 0.12, duration: 0.38 } as const;

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  layoutId,
  label,
  variant = "segment",
}: SegmentedProps<T>) {
  if (variant === "tabs") {
    return (
      <div role="radiogroup" aria-label={label} className="flex gap-5 border-b border-line">
        {options.map(({ value: v, label: text, icon: Icon }) => {
          const active = v === value;
          return (
            <button
              key={v}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => onChange(v)}
              className={`relative -mb-px inline-flex items-center gap-1.5 pb-2.5 pt-1 text-sm font-medium transition-colors ${
                active ? "text-fg" : "text-fg-faint hover:text-fg-muted"
              }`}
            >
              {Icon && <Icon size={14} aria-hidden />}
              {text}
              {active && (
                <motion.span
                  layoutId={layoutId}
                  transition={SLIDE}
                  aria-hidden
                  className="absolute inset-x-0 bottom-0 h-0.5 bg-navy-600"
                />
              )}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="inline-flex gap-0.5 rounded-md border border-line bg-sunken p-0.5"
    >
      {options.map(({ value: v, label: text, icon: Icon }) => {
        const active = v === value;
        return (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(v)}
            className={`relative isolate inline-flex h-7 items-center gap-1.5 rounded-[4px] px-3 text-xs font-medium transition-colors ${
              active ? "text-fg" : "text-fg-faint hover:text-fg-muted"
            }`}
          >
            {active && (
              <motion.span
                layoutId={layoutId}
                transition={SLIDE}
                aria-hidden
                className="absolute inset-0 -z-10 rounded-[4px] border border-line bg-surface"
              />
            )}
            {Icon && <Icon size={13} aria-hidden />}
            {text}
          </button>
        );
      })}
    </div>
  );
}
