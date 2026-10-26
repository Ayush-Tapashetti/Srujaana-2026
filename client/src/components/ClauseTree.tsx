import { ChevronRight, FileText } from "lucide-react";
import { useState, type ReactNode } from "react";
import type { Clause, Message } from "../types/api";

/** A generic node, so one component renders agreement, clause, then source. */
interface TreeNode {
  id: string;
  label: ReactNode;
  meta?: ReactNode;
  children?: TreeNode[];
}

function Node({ node, depth }: { node: TreeNode; depth: number }) {
  const [open, setOpen] = useState(depth === 0);
  const hasChildren = Boolean(node.children?.length);

  return (
    <li>
      <div
        className="flex items-start gap-1.5 rounded-sm py-1 pr-2 text-sm hover:bg-hover"
        style={{ paddingLeft: `${depth * 14 + 4}px` }}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            aria-label={open ? "Collapse" : "Expand"}
            className="mt-0.5 rounded-sm text-fg-faint hover:text-fg"
          >
            <ChevronRight size={14} className={`transition-transform duration-150 ${open ? "rotate-90" : ""}`} />
          </button>
        ) : (
          <span className="w-[14px]" aria-hidden />
        )}
        <div className="min-w-0 flex-1">
          {node.label}
          {node.meta}
        </div>
      </div>
      {hasChildren && open && (
        <ul className="relative">
          <span
            aria-hidden
            className="absolute bottom-2 top-0 w-px origin-top bg-line animate-link-draw"
            style={{ left: `${depth * 14 + 10}px` }}
          />
          {node.children!.map((child) => (
            <Node key={child.id} node={child} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  );
}

const DOT: Record<string, string> = {
  clear: "bg-emerald-500",
  vague: "bg-amber-400",
  missing: "bg-rose-500",
  conflicted: "bg-rose-500",
};

const WORD: Record<string, string> = {
  clear: "Clear",
  vague: "Vague",
  missing: "To be confirmed",
  conflicted: "Not agreed",
};

/**
 * The agreement's outline: each clause, its status, and under it the chat
 * messages it was built from. A custom recursive component, because no tree
 * library knows what a source message is.
 */
export function ClauseTree({ clauses, messages }: { clauses: Clause[]; messages: Message[] }) {
  const byIndex = new Map(messages.map((m) => [m.index, m]));

  const root: TreeNode = {
    id: "root",
    label: (
      <span className="inline-flex items-center gap-1.5 font-semibold text-fg">
        <FileText size={13} className="text-fg-faint" aria-hidden /> Agreement
      </span>
    ),
    children: clauses.map((clause) => ({
      id: clause.id,
      label: (
        <span className="flex items-center gap-2 text-fg">
          <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOT[clause.status] ?? "bg-fg-faint"}`} aria-hidden />
          <span className="truncate">{clause.heading}</span>
        </span>
      ),
      meta: <span className="ml-3.5 block text-xs text-fg-faint">{WORD[clause.status] ?? clause.status}</span>,
      children: clause.source_message_ids.map((i) => {
        const m = byIndex.get(i);
        return {
          id: `${clause.id}-${i}`,
          label: (
            <span className="flex gap-1.5 text-xs text-fg-muted">
              <span className="shrink-0 font-mono text-navy-600">#{i}</span>
              <span>{m ? `${m.sender}: ${m.body}` : "message not found"}</span>
            </span>
          ),
        };
      }),
    })),
  };

  return (
    <ul aria-label="Agreement outline">
      <Node node={root} depth={0} />
    </ul>
  );
}
