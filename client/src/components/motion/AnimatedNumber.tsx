/*
 * A count that rolls up to its value instead of appearing.
 *
 * Pattern reference: Motion Primitives, "Animated Number" (a spring-driven
 * motion value rendered through a transform).
 * Written for this project; no code copied.
 */
import { motion, useSpring, useTransform } from "motion/react";
import { useEffect } from "react";

export function AnimatedNumber({ value, className = "" }: { value: number; className?: string }) {
  const spring = useSpring(0, { mass: 0.8, stiffness: 80, damping: 16 });
  const display = useTransform(spring, (v) => Math.round(v).toLocaleString("en-IN"));

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return (
    <motion.span className={`tabular-nums ${className}`} aria-label={String(value)}>
      {display}
    </motion.span>
  );
}
