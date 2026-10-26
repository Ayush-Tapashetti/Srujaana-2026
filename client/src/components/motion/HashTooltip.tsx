/*
 * A short hash that shows the full value on hover or focus.
 * Pattern reference: Skiper UI, "Vercel-style tooltip".
 * Written for this project; no code copied.
 */
import { AnimatePresence, motion } from "motion/react";
import { useId, useState } from "react";
import { shortHash } from "../../lib/labels";

export function HashTooltip({ hash, label, size = 10 }: { hash: string; label: string; size?: number }) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span className="relative inline-flex" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        className="hash rounded-sm underline decoration-line-strong decoration-dotted underline-offset-4 hover:text-fg"
        aria-describedby={open ? id : undefined}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        {shortHash(hash, size)}
      </button>
      <AnimatePresence>
        {open && (
          <motion.span
            id={id}
            role="tooltip"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 2 }}
            transition={{ duration: 0.14 }}
            className="absolute bottom-full left-0 z-30 mb-2 w-[min(23rem,80vw)] rounded-md bg-fg px-3 py-2.5"
          >
            <span className="block text-2xs text-white/60">{label}</span>
            <span className="mt-1 block break-all font-mono text-2xs leading-relaxed text-white">{hash}</span>
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}
