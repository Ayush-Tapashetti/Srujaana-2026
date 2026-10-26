import type {
  Agreement,
  Analysis,
  CertificateDraft,
  ClauseAnswer,
  ConfirmView,
  Conversation,
  EvidenceChain,
  Evaluation,
  Health,
  MaskedPreview,
  MsmeCheck,
  Pack,
  ProposalResult,
  RecapResponse,
  SampleSummary,
  ShareLink,
  SendResponse,
  StampGuidance,
  StateOption,
  SupplierAnswer,
  Verification,
} from "../types/api";

/** The server writes every error as one plain sentence for the user. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body && !(init.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(0, "The server can't be reached. Check that it is running.");
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "detail" in body) {
        const d = (body as { detail: unknown }).detail;
        // 422s from FastAPI carry a list of field errors.
        if (typeof d === "string") detail = d;
        else if (Array.isArray(d) && d[0] && typeof d[0].msg === "string") {
          // Pydantic: "Value error, Use at least 8 characters…" -> the sentence.
          detail = String(d[0].msg).replace(/^Value error,\s*/, "");
        } else detail = "Some fields are missing or invalid.";
      }
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

const json = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });

export const api = {
  health: () => request<Health>("/api/health"),
  samples: () => request<SampleSummary[]>("/api/samples"),
  myConversations: () => request<SampleSummary[]>("/api/conversations"),

  // F1
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Conversation>("/api/conversations", { method: "POST", body: form });
  },
  paste: (text: string) => request<Conversation>("/api/conversations/paste", json({ text })),
  conversation: (id: number) => request<Conversation>(`/api/conversations/${id}`),

  // F2 / F3
  analysis: (id: number) => request<Analysis>(`/api/conversations/${id}/analysis`),
  extract: (id: number, force = false) =>
    request<Analysis>(`/api/conversations/${id}/extract${force ? "?force=true" : ""}`, {
      method: "POST",
    }),

  // F4 / F5
  latestAgreement: (conversationId: number) =>
    request<Agreement>(`/api/agreements/by-conversation/${conversationId}`),
  generate: (conversationId: number, overrideReason?: string) =>
    request<Agreement>(
      `/api/agreements/${conversationId}/generate`,
      json(overrideReason ? { override_reason: overrideReason } : {}),
    ),
  send: (agreementId: number) =>
    request<SendResponse>(`/api/agreements/${agreementId}/send`, { method: "POST" }),
  proposeClauseEdit: (agreementId: number, clauseId: string, newBody: string) =>
    request<ProposalResult>(
      `/api/agreements/${agreementId}/clauses/${encodeURIComponent(clauseId)}/propose`,
      json({ clause_id: clauseId, new_body: newBody }),
    ),
  recap: (agreementId: number) => request<RecapResponse>(`/api/agreements/${agreementId}/recap`),
  recapReply: (
    agreementId: number,
    body: { conversation_id: number; message_index: number; typed_name: string },
  ) => request<Agreement>(`/api/agreements/${agreementId}/recap-reply`, json(body)),

  confirmView: (token: string) => request<ConfirmView>(`/api/confirm/${token}`),
  confirm: (
    token: string,
    body: { typed_name: string; read_confirmation: boolean; answers: ClauseAnswer[] },
  ) => request<ConfirmView>(`/api/confirm/${token}`, json(body)),

  // F6
  evidence: (id: number) => request<EvidenceChain>(`/api/evidence/${id}`),
  verify: (id: number) => request<Verification>(`/api/evidence/${id}/verify`),
  tamper: (id: number, sequence: number) =>
    request<Verification>(`/api/evidence/${id}/_tamper?sequence=${sequence}`, { method: "POST" }),

  // Share with a CA or lawyer
  createShare: (id: number, days: number) =>
    request<ShareLink>(`/api/evidence/${id}/share`, json({ days })),
  shares: (id: number) => request<ShareLink[]>(`/api/evidence/${id}/shares`),
  revokeShare: (id: number, shareId: number) =>
    request<ShareLink>(`/api/evidence/${id}/share/${shareId}/revoke`, { method: "POST" }),
  /** Read-only page for a CA or lawyer, opened with the link's token. */
  pack: (token: string) => request<Pack>(`/api/pack/${encodeURIComponent(token)}`),

  // P1
  maskedPreview: (id: number) => request<MaskedPreview>(`/api/conversations/${id}/masked-preview`),
  msmeCheck: (id: number, answer: SupplierAnswer) =>
    request<MsmeCheck>(`/api/conversations/${id}/msme-check?supplier_is_micro_or_small=${answer}`),
  certificateDraft: (id: number) => request<CertificateDraft>(`/api/evidence/${id}/certificate-draft`),
  evaluation: () => request<Evaluation>("/api/eval"),

  // F7
  stamp: (state: string) =>
    request<StampGuidance>(`/api/stamp-guidance?state=${encodeURIComponent(state)}`),
  stampStates: () => request<StateOption[]>("/api/stamp-guidance/states"),
};
