/*
 * Swaps the content of one slot, such as the selected tab's body.
 * Pattern reference: Motion Primitives, "Transition Panel".
 * Written for this project; no code copied.
 */
import { AnimatePresence, motion } from "motion/react";
import type { ReactNode } from "react";

export function TransitionPanel({ activeKey, children }: { activeKey: string; children: ReactNode }) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={activeKey}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.16, ease: [0.25, 0.8, 0.25, 1] }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
