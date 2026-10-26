import { CircleAlert, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

export function ErrorNote({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2.5 rounded-md border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-800"
    >
      <CircleAlert size={16} className="mt-0.5 shrink-0 text-rose-700" aria-hidden />
      <div className="flex-1">{children}</div>
      {action}
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-fg-muted" role="status">
      <Loader2 size={14} className="animate-spin text-navy-600" aria-hidden />
      {label}
    </span>
  );
}

/** A placeholder block while data loads. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-sunken ${className}`} aria-hidden />;
}

/** A neutral note: a hairline box, an icon, plain text. */
export function Notice({ children, icon }: { children: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex items-start gap-2.5 rounded-md border border-line bg-surface px-3.5 py-2.5 text-sm text-fg-muted">
      {icon && <span className="mt-0.5 shrink-0 text-fg-faint">{icon}</span>}
      <div>{children}</div>
    </div>
  );
}
