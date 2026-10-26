/*
 * A button that grows into its own menu and shrinks back into it.
 * Pattern reference: Watermelon UI, animated menus (a shared-layout morph
 * between trigger and panel).
 * Written for this project; no code copied.
 */
import { AnimatePresence, motion } from "motion/react";
import { MoreHorizontal, X, type LucideIcon } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

export interface MenuAction {
  label: string;
  hint?: string;
  icon: LucideIcon;
  onSelect: () => void;
  disabled?: boolean;
}

const MORPH = { type: "spring", bounce: 0.12, duration: 0.34 } as const;

export function MorphMenu({ actions, label = "More" }: { actions: MenuAction[]; label?: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const layoutId = useId();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative h-9">
      <AnimatePresence initial={false}>
        {!open ? (
          <motion.button
            key="trigger"
            layoutId={layoutId}
            transition={MORPH}
            type="button"
            onClick={() => setOpen(true)}
            aria-haspopup="menu"
            aria-expanded={false}
            className="btn btn-secondary"
            style={{ borderRadius: 6 }}
          >
            <motion.span layout="position" className="inline-flex items-center gap-1.5">
              <MoreHorizontal size={15} aria-hidden /> {label}
            </motion.span>
          </motion.button>
        ) : (
          <motion.div
            key="panel"
            layoutId={layoutId}
            transition={MORPH}
            role="menu"
            className="absolute right-0 top-0 z-40 w-72 overflow-hidden border border-line bg-surface shadow-float"
            style={{ borderRadius: 6 }}
          >
            <div className="flex items-center justify-between border-b border-line px-3 py-2">
              <span className="text-xs font-medium text-fg-muted">{label}</span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close menu"
                className="rounded-sm p-0.5 text-fg-faint hover:bg-hover hover:text-fg"
              >
                <X size={14} />
              </button>
            </div>
            <motion.ul
              className="p-1"
              initial="hidden"
              animate="visible"
              variants={{ visible: { transition: { staggerChildren: 0.03, delayChildren: 0.06 } } }}
            >
              {actions.map(({ label: text, hint, icon: Icon, onSelect, disabled }) => (
                <motion.li
                  key={text}
                  variants={{ hidden: { opacity: 0, y: 3 }, visible: { opacity: 1, y: 0 } }}
                >
                  <button
                    type="button"
                    role="menuitem"
                    disabled={disabled}
                    onClick={() => {
                      setOpen(false);
                      onSelect();
                    }}
                    className="flex w-full items-start gap-2.5 rounded-sm px-2.5 py-2 text-left text-sm text-fg transition-colors hover:bg-hover disabled:opacity-40"
                  >
                    <Icon size={15} className="mt-0.5 shrink-0 text-fg-muted" aria-hidden />
                    <span>
                      <span className="block font-medium">{text}</span>
                      {hint && <span className="block text-xs text-fg-faint">{hint}</span>}
                    </span>
                  </button>
                </motion.li>
              ))}
            </motion.ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
