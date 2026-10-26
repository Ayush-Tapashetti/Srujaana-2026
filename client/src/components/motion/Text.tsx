/*
 * The home headline arrives word by word, once, on load. It is the only
 * motion in the app that nobody asked for, so it is quick and plain: a short
 * rise and fade, no blur.
 *
 * Pattern reference: Motion Primitives, "Text Effect".
 * Written for this project; no code copied.
 */
import { motion } from "motion/react";
import type { ElementType } from "react";

interface TextEffectProps {
  children: string;
  as?: ElementType;
  className?: string;
}

export function TextEffect({ children, as: Tag = "p", className = "" }: TextEffectProps) {
  const words = children.split(" ");
  return (
    <Tag className={className} aria-label={children}>
      <motion.span
        aria-hidden
        initial="hidden"
        animate="visible"
        variants={{ visible: { transition: { staggerChildren: 0.035 } } }}
      >
        {words.map((word, i) => (
          <motion.span
            key={i}
            className="inline-block whitespace-pre"
            variants={{
              hidden: { opacity: 0, y: 8 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.25, 0.8, 0.25, 1] } },
            }}
          >
            {word}
            {i < words.length - 1 ? " " : ""}
          </motion.span>
        ))}
      </motion.span>
    </Tag>
  );
}
