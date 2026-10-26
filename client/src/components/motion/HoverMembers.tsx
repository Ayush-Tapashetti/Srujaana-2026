/*
 * The two people in the deal, as overlapping initials that fan out on hover
 * and name themselves.
 * Pattern reference: Skiper UI, "Hover Members".
 * Written for this project; no code copied.
 */
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

const TINT = [
  "border-navy-200 bg-navy-50 text-navy-700",
  "border-line-strong bg-sunken text-fg-muted",
  "border-line bg-surface text-fg-faint",
];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

export function HoverMembers({ names }: { names: string[] }) {
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState<number | null>(null);

  return (
    <div
      className="flex items-center"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => {
        setOpen(false);
        setHovered(null);
      }}
      aria-label={`Participants: ${names.join(" and ")}`}
      role="group"
    >
      {names.map((name, i) => (
        <motion.div
          key={name}
          className="relative"
          animate={{ marginLeft: i === 0 ? 0 : open ? 4 : -8 }}
          transition={{ type: "spring", bounce: 0.2, duration: 0.35 }}
          onMouseEnter={() => setHovered(i)}
          onFocus={() => setHovered(i)}
          onBlur={() => setHovered(null)}
          tabIndex={0}
          style={{ zIndex: names.length - i }}
        >
          <span
            className={`grid h-8 w-8 place-items-center rounded-full border font-mono text-2xs font-medium ring-2 ring-canvas ${
              TINT[i % TINT.length]
            }`}
          >
            {initials(name)}
          </span>
          <AnimatePresence>
            {hovered === i && (
              <motion.span
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 2 }}
                transition={{ duration: 0.14 }}
                className="absolute left-1/2 top-full z-20 mt-1.5 -translate-x-1/2 whitespace-nowrap rounded-sm bg-fg px-2 py-1 text-xs font-medium text-white"
              >
                {name}
              </motion.span>
            )}
          </AnimatePresence>
        </motion.div>
      ))}
    </div>
  );
}
