import { Scale } from "lucide-react";
import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

/** The persistent notice required by D10. Visible on every page. */
export const DISCLAIMER = "Decision support, not legal advice. Check anything important with a lawyer.";

export function Wordmark() {
  return (
    <Link to="/" className="group inline-flex items-center gap-2" aria-label="Handshake, home">
      <svg viewBox="0 0 64 64" className="h-6 w-6 -rotate-3 transition-transform group-hover:rotate-0" aria-hidden>
        <rect x="8" y="14" width="48" height="36" rx="3" fill="none" stroke="#1E3A8A" strokeWidth="3.5" />
        <rect x="14" y="20" width="36" height="24" rx="1.5" fill="none" stroke="#1E3A8A" strokeWidth="1.8" />
        <path d="M23 32.5l6 5.5 12-12" fill="none" stroke="#1E3A8A" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="whitespace-nowrap text-[0.95rem] font-semibold tracking-tight text-fg">
        Handshake<span className="hidden font-normal text-fg-faint sm:inline"> to contract</span>
      </span>
    </Link>
  );
}

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-sm px-2 py-1 transition-colors ${isActive ? "text-fg" : "text-fg-faint hover:text-fg"}`;

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="no-print sticky top-0 z-30 border-b border-line bg-canvas">
        <div className="mx-auto flex h-12 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Wordmark />
          <nav className="flex shrink-0 items-center gap-1 whitespace-nowrap text-sm">
            <NavLink to="/" end className={navClass}>
              <span className="sm:hidden">New</span>
              <span className="hidden sm:inline">New chat</span>
            </NavLink>
            <NavLink to="/evaluation" className={navClass}>
              <span className="sm:hidden">Tests</span>
              <span className="hidden sm:inline">How well it works</span>
            </NavLink>
            <NavLink to="/limits" className={navClass}>
              <span className="sm:hidden">Limits</span>
              <span className="hidden sm:inline">Limits and stamp duty</span>
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="no-print border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-3 text-xs text-fg-faint sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <span className="inline-flex items-center gap-1.5">
            <Scale size={13} aria-hidden />
            {DISCLAIMER}
          </span>
        </div>
      </footer>
    </div>
  );
}
