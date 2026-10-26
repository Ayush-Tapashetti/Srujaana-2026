/*
 * Children arrive in order, a beat apart, when results land.
 * Pattern reference: Motion Primitives, "Animated Group".
 * Written for this project; no code copied.
 */
import { motion } from "motion/react";
import { Children, type ReactNode } from "react";

interface AnimatedGroupProps {
  children: ReactNode;
  className?: string;
  /** Change this to replay, e.g. the analysis id. */
  replayKey?: string | number;
}

export function AnimatedGroup({ children, className = "", replayKey }: AnimatedGroupProps) {
  return (
    <motion.div
      key={replayKey}
      className={className}
      initial="hidden"
      animate="visible"
      variants={{ visible: { transition: { staggerChildren: 0.05 } } }}
    >
      {Children.map(children, (child) =>
        child ? (
          <motion.div
            variants={{
              hidden: { opacity: 0, y: 6 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.26, ease: [0.25, 0.8, 0.25, 1] } },
            }}
          >
            {child}
          </motion.div>
        ) : null,
      )}
    </motion.div>
  );
}
