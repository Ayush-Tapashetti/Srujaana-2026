/*
 * One status line for every action: checking, copied, drafted, verified.
 * It resizes to its message instead of stacking toasts, so there is only
 * ever one place to look.
 *
 * Pattern references: Cult UI and Skiper UI, "Dynamic Island" (a container
 * that morphs to its content). Restyled for the editorial theme: white,
 * one hairline border, no blur.
 * Written for this project; no code copied.
 */
import { AnimatePresence, motion } from "motion/react";
import { CircleAlert, CircleCheck, Info, Loader2 } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

type Kind = "busy" | "success" | "error" | "info";

interface IslandMessage {
  id: number;
  kind: Kind;
  text: string;
  detail?: string;
}

interface IslandApi {
  /** Show a working state. Returns a function that clears it. */
  busy: (text: string) => () => void;
  notify: (kind: Exclude<Kind, "busy">, text: string, detail?: string) => void;
}

const IslandContext = createContext<IslandApi | null>(null);

export function useIsland(): IslandApi {
  const api = useContext(IslandContext);
  if (!api) throw new Error("useIsland must be used inside StatusIslandProvider");
  return api;
}

const ICON: Record<Exclude<Kind, "busy">, { Icon: typeof Info; cls: string }> = {
  success: { Icon: CircleCheck, cls: "text-emerald-700" },
  error: { Icon: CircleAlert, cls: "text-rose-700" },
  info: { Icon: Info, cls: "text-navy-600" },
};

const MORPH = { type: "spring", bounce: 0.15, duration: 0.4 } as const;

export function StatusIslandProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<IslandMessage | null>(null);
  const seq = useRef(0);
  const timer = useRef<number>();

  const show = useCallback((kind: Kind, text: string, detail?: string) => {
    window.clearTimeout(timer.current);
    const id = ++seq.current;
    setMessage({ id, kind, text, detail });
    if (kind !== "busy") {
      timer.current = window.setTimeout(() => {
        setMessage((m) => (m?.id === id ? null : m));
      }, 2600);
    }
    return id;
  }, []);

  const api = useMemo<IslandApi>(
    () => ({
      busy: (text) => {
        const id = show("busy", text);
        return () => setMessage((m) => (m?.id === id ? null : m));
      },
      notify: (kind, text, detail) => {
        show(kind, text, detail);
      },
    }),
    [show],
  );

  return (
    <IslandContext.Provider value={api}>
      {children}
      <div
        className="no-print pointer-events-none fixed inset-x-0 top-[3.75rem] z-50 flex justify-center px-4"
        aria-live="polite"
      >
        <AnimatePresence>
          {message && (
            <motion.div
              layout
              key="island"
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={MORPH}
              className="pointer-events-auto overflow-hidden rounded-md border border-line bg-surface shadow-float"
            >
              <AnimatePresence mode="popLayout" initial={false}>
                <motion.div
                  key={message.id}
                  layout
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className="flex items-center gap-2.5 whitespace-nowrap px-3.5 py-2 text-sm"
                >
                  {message.kind === "busy" ? (
                    <Loader2 size={14} className="animate-spin text-navy-600" aria-hidden />
                  ) : (
                    (() => {
                      const { Icon, cls } = ICON[message.kind];
                      return <Icon size={15} className={cls} aria-hidden />;
                    })()
                  )}
                  <span className="font-medium text-fg">{message.text}</span>
                  {message.detail && <span className="meta">{message.detail}</span>}
                </motion.div>
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </IslandContext.Provider>
  );
}
