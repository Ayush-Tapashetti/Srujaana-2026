import { Check, Copy, ExternalLink, Share2 } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import { useAction, useApi } from "../hooks/useApi";
import { formatTime } from "../lib/labels";
import type { ShareLink } from "../types/api";
import { useIsland } from "./motion/StatusIsland";
import { ErrorNote } from "./ui/Feedback";

const EXPIRY_CHOICES = [
  { days: 1, label: "1 day" },
  { days: 7, label: "7 days" },
  { days: 30, label: "30 days" },
];

function fullUrl(link: ShareLink): string {
  return `${window.location.origin}${link.url}`;
}

function statusOf(link: ShareLink): { text: string; tone: string } {
  if (link.revoked) return { text: "Turned off", tone: "text-fg-faint" };
  if (link.expired) return { text: "Expired", tone: "text-fg-faint" };
  return { text: `Live until ${formatTime(link.expires_at)}`, tone: "text-emerald-700" };
}

/**
 * Sharing is a deliberate act: the owner reads what it means, ticks that they
 * understand, picks how long it lasts, and can turn the link off at any time.
 */
export function SharePanel({ conversationId }: { conversationId: number }) {
  const links = useApi(() => api.shares(conversationId), [conversationId]);
  const action = useAction();
  const island = useIsland();
  const [understood, setUnderstood] = useState(false);
  const [days, setDays] = useState(7);
  const [justCopied, setJustCopied] = useState<number | null>(null);

  const copy = async (link: ShareLink) => {
    const text = fullUrl(link);
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard can be blocked on plain http; fall back to a hidden field.
      const area = document.createElement("textarea");
      area.value = text;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    setJustCopied(link.id);
    island.notify("success", "Link copied", "Send it to your CA or lawyer");
    window.setTimeout(() => setJustCopied((current) => (current === link.id ? null : current)), 1600);
  };

  const create = async () => {
    const link = await action.run(() => api.createShare(conversationId, days));
    if (link) {
      await links.reload();
      await copy(link);
    }
  };

  const revoke = async (link: ShareLink) => {
    const done = await action.run(() => api.revokeShare(conversationId, link.id));
    if (done) {
      island.notify("success", "Link turned off", "It no longer opens");
      await links.reload();
    }
  };

  const list = links.data ?? [];
  const live = list.filter((l) => !l.revoked && !l.expired);

  return (
    <section className="panel p-5" aria-labelledby="share-heading">
      <h2 id="share-heading" className="flex items-center gap-2 font-semibold text-fg">
        <Share2 size={17} className="text-fg-faint" aria-hidden /> Share with a CA or lawyer
      </h2>
      <p className="mt-1 text-sm text-fg-muted">
        Makes a read-only link to an evidence summary: the terms and flags, the agreement and who answered it,
        every recorded event with its fingerprint, and a draft of Part A. They need no account.
      </p>

      <ul className="mt-3 space-y-1 text-xs text-fg-muted">
        <li>Anyone who has the link can read the summary until it expires or you turn it off.</li>
        <li>Phone numbers, PAN, Aadhaar, GSTIN, email addresses and UPI IDs are hidden in what they see.</li>
        <li>They can't change anything. The page is not shown to search engines.</li>
      </ul>

      <label className="mt-4 flex cursor-pointer items-start gap-2 text-sm text-fg">
        <input
          type="checkbox"
          className="mt-0.5"
          checked={understood}
          onChange={(e) => setUnderstood(e.target.checked)}
        />
        <span>I understand that anyone with the link can read this summary.</span>
      </label>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-fg-muted">
          Lasts
          <select
            className="field !w-auto !py-1"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            aria-label="How long the link works"
          >
            {EXPIRY_CHOICES.map((c) => (
              <option key={c.days} value={c.days}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="btn btn-primary" onClick={create} disabled={!understood || action.busy}>
          <Share2 size={16} aria-hidden /> Create read-only link
        </button>
      </div>

      {action.error && (
        <div className="mt-3">
          <ErrorNote>{action.error}</ErrorNote>
        </div>
      )}
      {links.error && (
        <div className="mt-3">
          <ErrorNote>{links.error.message}</ErrorNote>
        </div>
      )}

      {list.length > 0 && (
        <div className="mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-fg-faint">
            Your links{live.length > 0 ? ` (${live.length} live)` : ""}
          </h3>
          <ul className="mt-2 divide-y divide-line rounded-md border border-line">
            {list.map((link) => {
              const st = statusOf(link);
              const active = !link.revoked && !link.expired;
              return (
                <li key={link.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2.5">
                  <div className="min-w-0">
                    <p className={`text-sm ${st.tone}`}>{st.text}</p>
                    <p className="meta">
                      Opened {link.view_count} time{link.view_count === 1 ? "" : "s"}
                      {link.last_viewed_at ? `, last ${formatTime(link.last_viewed_at)}` : ""}
                    </p>
                  </div>
                  {active && (
                    <div className="flex shrink-0 items-center gap-2">
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => copy(link)}>
                        {justCopied === link.id ? <Check size={14} aria-hidden /> : <Copy size={14} aria-hidden />}
                        {justCopied === link.id ? "Copied" : "Copy"}
                      </button>
                      <a className="btn btn-secondary btn-sm" href={link.url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink size={14} aria-hidden /> Open
                      </a>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm text-rose-700"
                        onClick={() => revoke(link)}
                        disabled={action.busy}
                      >
                        Turn off
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}
