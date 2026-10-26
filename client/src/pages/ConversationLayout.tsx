import { ArrowLeft } from "lucide-react";
import { createContext, useContext } from "react";
import { Link, Outlet, useParams } from "react-router-dom";
import { api } from "../api/client";
import { HoverMembers } from "../components/motion/HoverMembers";
import { StepRail } from "../components/StepRail";
import { ErrorNote, Skeleton } from "../components/ui/Feedback";
import { useApi } from "../hooks/useApi";
import { sampleTitle } from "../lib/labels";
import type { Conversation } from "../types/api";

const ConversationContext = createContext<Conversation | null>(null);

/** The loaded chat, shared by the Check, Agreement and Evidence pages. */
export function useConversation(): Conversation {
  const value = useContext(ConversationContext);
  if (!value) throw new Error("useConversation must be used inside ConversationLayout");
  return value;
}

export function ConversationLayout() {
  const { id } = useParams();
  const conversationId = Number(id);
  const conversation = useApi(() => api.conversation(conversationId), [conversationId]);

  if (!Number.isFinite(conversationId)) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <ErrorNote>That address doesn't point to a chat.</ErrorNote>
      </div>
    );
  }

  if (conversation.loading && !conversation.data) {
    return (
      <div className="mx-auto max-w-6xl space-y-4 px-4 py-8 sm:px-6">
        <Skeleton className="h-10 w-80" />
        <Skeleton className="h-[60vh]" />
      </div>
    );
  }

  if (conversation.error || !conversation.data) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <ErrorNote action={<Link className="btn btn-secondary btn-sm" to="/">Start again</Link>}>
          {conversation.error?.message ?? "This chat could not be loaded."}
        </ErrorNote>
      </div>
    );
  }

  const c = conversation.data;
  const title = c.is_sample && c.sample_label ? sampleTitle(c.sample_label) : c.original_filename;

  return (
    <ConversationContext.Provider value={c}>
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <div className="no-print mb-6 flex flex-col gap-4 border-b border-line pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <Link to="/" className="mb-2 inline-flex items-center gap-1 text-xs text-fg-faint hover:text-fg">
              <ArrowLeft size={12} aria-hidden /> All chats
            </Link>
            <div className="flex items-center gap-3.5">
              {c.participants.length > 0 && <HoverMembers names={c.participants.slice(0, 4)} />}
              <div className="min-w-0">
                <h1 className="truncate text-xl font-semibold tracking-tight text-fg">{title}</h1>
                <p className="mt-0.5 flex flex-wrap items-center gap-x-3 text-sm text-fg-muted">
                  <span>{c.participants.join(" and ") || "No participants found"}</span>
                  <span className="meta">{c.message_count} messages</span>
                  <span className="meta">ID {c.id}</span>
                </p>
              </div>
            </div>
          </div>
          <StepRail conversationId={c.id} />
        </div>
        <Outlet />
      </div>
    </ConversationContext.Provider>
  );
}
