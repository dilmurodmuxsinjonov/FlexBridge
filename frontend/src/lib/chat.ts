import { errorText } from "./errorText";

export type ChatRelation = "COLLEAGUE" | "EMPLOYER" | "APPLICANT" | "UNIVERSITY" | "STUDENT" | "CHAT";

export interface ChatContact {
  user_id: string;
  display_name: string;
  relation: ChatRelation;
}

export interface ChatLastMessage {
  body: string | null;
  deleted: boolean;
  sender_id: string;
  sender_name: string;
  mine: boolean;
  created_at: string;
}

export interface ChatConversation {
  id: string;
  kind: "DIRECT" | "GROUP";
  title: string;
  partner_id: string | null;
  member_count: number;
  my_role: "OWNER" | "MEMBER" | null;
  unread_count: number;
  last_message: ChatLastMessage | null;
  updated_at: string;
}

export interface ChatConversationDetail extends ChatConversation {
  members: Array<{ user_id: string; display_name: string; role: "OWNER" | "MEMBER" }>;
  invite_link_active: boolean | null;
  blocked: boolean;
}

export interface ChatMessage {
  id: string;
  sender_id: string;
  sender_name?: string;
  body: string | null;
  deleted: boolean;
  mine: boolean;
  created_at: string;
}

export const RELATION_LABEL: Record<ChatRelation, string> = {
  COLLEAGUE: "Hamkasb",
  EMPLOYER: "Ish beruvchi",
  APPLICANT: "Nomzod",
  UNIVERSITY: "Universitet",
  STUDENT: "Talaba",
  CHAT: "Suhbatdosh",
};

const CHAT_ERRORS: Record<string, string> = {
  CHAT_NOT_A_CONTACT: "Bu foydalanuvchi bilan bog‘lanish uchun uning kontakt kodi kerak.",
  CHAT_CODE_NOT_FOUND: "Bunday kontakt kod topilmadi.",
  CHAT_SELF_NOT_ALLOWED: "O‘zingizga yozib bo‘lmaydi.",
  CHAT_BLOCKED: "Bu suhbat bloklangan.",
  CHAT_NOT_FOUND: "Suhbat topilmadi yoki siz undan chiqqansiz.",
  CHAT_OWNER_REQUIRED: "Buni faqat guruh egasi qila oladi.",
  CHAT_INVITE_INVALID: "Taklif havolasi yaroqsiz yoki o‘chirilgan.",
  CHAT_GROUP_TOO_LARGE: "Guruhda 200 kishidan ko‘p bo‘lishi mumkin emas.",
  INVALID_CHAT_MESSAGE: "Xabar bo‘sh yoki juda uzun (4000 belgigacha).",
  INVALID_CHAT_TITLE: "Guruh nomi 1–80 belgi bo‘lishi kerak.",
  CHAT_MESSAGE_NOT_YOURS: "Faqat o‘z xabaringizni o‘chira olasiz.",
};

async function call<T>(path: string, init: RequestInit & { json?: unknown } = {}, fallback = "CHAT_REQUEST_FAILED"): Promise<T> {
  const { json, ...rest } = init;
  const res = await fetch(`/api/bff/chat/${path}`, {
    ...rest,
    headers: { Accept: "application/json", ...(json !== undefined ? { "Content-Type": "application/json" } : {}) },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const code = typeof data?.error === "string" ? data.error : "";
    throw new Error(CHAT_ERRORS[code] || errorText(data, fallback));
  }
  return data as T;
}

export const fetchMyContactCode = () => call<{ contact_code: string }>("me");
export const rotateContactCode = () => call<{ contact_code: string }>("me/contact-code/rotate", { method: "POST", json: {} });
export const fetchContacts = (q = "") =>
  call<{ items: ChatContact[] }>(`contacts${q ? `?q=${encodeURIComponent(q)}` : ""}`).then((r) => r.items || []);
export const fetchConversations = () =>
  call<{ items: ChatConversation[]; unread_total: number }>("conversations").then((r) => ({ items: r.items || [], unread_total: r.unread_total || 0 }));
export const fetchConversation = (id: string) => call<ChatConversationDetail>(`conversations/${id}`);
export const startDirect = (target: { user_id?: string; contact_code?: string }) =>
  call<ChatConversationDetail>("direct", { method: "POST", json: target });
export const createGroup = (title: string, member_ids: string[]) =>
  call<ChatConversationDetail>("groups", { method: "POST", json: { title, member_ids } });
export const renameGroup = (id: string, title: string) => call<ChatConversationDetail>(`groups/${id}`, { method: "PATCH", json: { title } });
export const addGroupMembers = (id: string, member_ids: string[]) =>
  call<ChatConversationDetail>(`groups/${id}/members`, { method: "POST", json: { member_ids } });
export const removeGroupMember = (id: string, userId: string) =>
  call<{ ok: boolean; left: boolean }>(`groups/${id}/members/${userId}`, { method: "DELETE" });
export const enableInviteLink = (id: string) => call<{ invite_token: string }>(`groups/${id}/invite-link`, { method: "POST", json: {} });
export const disableInviteLink = (id: string) => call<{ invite_token: null }>(`groups/${id}/invite-link`, { method: "DELETE" });
export const joinByToken = (token: string) => call<ChatConversationDetail>("join", { method: "POST", json: { token } });
export const fetchMessages = (id: string, before?: string) =>
  call<{ items: ChatMessage[]; has_more: boolean }>(`conversations/${id}/messages${before ? `?before=${before}` : ""}`);
export const sendMessage = (id: string, body: string) => call<ChatMessage>(`conversations/${id}/messages`, { method: "POST", json: { body } });
export const markRead = (id: string) => call<{ ok: boolean }>(`conversations/${id}/read`, { method: "POST", json: {} });
export const deleteMessage = (messageId: string) => call<{ ok: boolean }>(`messages/${messageId}`, { method: "DELETE" });
export const setBlocked = (userId: string, blocked: boolean) =>
  call<{ ok: boolean; blocked: boolean }>(`blocks/${userId}`, { method: blocked ? "POST" : "DELETE", ...(blocked ? { json: {} } : {}) });

/** "14:05" today, "Kecha" yesterday, otherwise "12.11". */
export function chatTime(iso: string, now = new Date()): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  const y = new Date(now);
  y.setDate(now.getDate() - 1);
  if (d.toDateString() === y.toDateString()) return "Kecha";
  return `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}`;
}

/** Shareable invite URL for a group token. */
export const inviteUrl = (token: string, origin = typeof window !== "undefined" ? window.location.origin : "") =>
  `${origin}/xabarlar?qoshilish=${encodeURIComponent(token)}`;
