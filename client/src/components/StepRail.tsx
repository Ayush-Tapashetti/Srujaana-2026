import { motion } from "motion/react";
import { NavLink } from "react-router-dom";

/**
 * The three stages after upload. A real sequence, so it is numbered. The
 * active box slides between steps (Motion Primitives, "Animated Background").
 */
const STEPS = [
  { to: "", label: "Check the chat" },
  { to: "agreement", label: "Agreement" },
  { to: "evidence", label: "Evidence" },
] as const;

export function StepRail({ conversationId }: { conversationId: number }) {
  return (
    <nav aria-label="Steps" className="no-print">
      <ol className="flex flex-wrap items-center gap-1 text-sm">
        {STEPS.map((step, i) => (
          <li key={step.label} className="flex items-center gap-1">
            {i > 0 && <span aria-hidden className="h-px w-4 bg-line-strong" />}
            <NavLink
              end
              to={`/c/${conversationId}${step.to ? `/${step.to}` : ""}`}
              className={({ isActive }) =>
                `relative isolate inline-flex h-8 items-center gap-2 rounded-md px-2.5 transition-colors ${
                  isActive ? "text-fg" : "text-fg-faint hover:text-fg"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="step-pill"
                      transition={{ type: "spring", bounce: 0.12, duration: 0.4 }}
                      aria-hidden
                      className="absolute inset-0 -z-10 rounded-md border border-line bg-surface"
                    />
                  )}
                  <span
                    className={`grid h-5 w-5 place-items-center rounded-sm font-mono text-2xs font-medium ${
                      isActive ? "bg-navy-600 text-white" : "border border-line-strong text-fg-faint"
                    }`}
                  >
                    {i + 1}
                  </span>
                  <span className="font-medium">{step.label}</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ol>
    </nav>
  );
}
