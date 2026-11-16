"use client";

import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Check, Copy, Link2, Loader2, LogOut, RefreshCw, Search, ShieldOff, Trash2, UserPlus, X } from "lucide-react";
import {
  addGroupMembers,
  createGroup,
  disableInviteLink,
  enableInviteLink,
  fetchContacts,
  fetchMyContactCode,
  inviteUrl,
  RELATION_LABEL,
  removeGroupMember,
  renameGroup,
  rotateContactCode,
  setBlocked,
  startDirect,
  type ChatContact,
  type ChatConversationDetail,
} from "@/lib/chat";
import { initials } from "@/lib/person";
import { useAsyncData } from "@/lib/useAsyncData";

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  // Portal to <body>: glass cards use backdrop-filter, which would trap a fixed overlay inside them.
  if (typeof document === "undefined") return null;
  return createPortal(
    <div className="fixed inset-0 z-[90] flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-label={title} className="skeuo-card flex max-h-[88vh] w-full max-w-lg flex-col overflow-hidden rounded-t-[28px] sm:rounded-[28px]">
        <div className="flex items-center justify-between gap-3 px-5 pb-3 pt-5">
          <h2 className="text-lg font-semibold text-[var(--fb-ink)]">{title}</h2>
          <button type="button" onClick={onClose} className="fb-icon-btn fb-icon-btn-light h-9 w-9" aria-label="Yopish">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 overflow-y-auto px-5 pb-5">{children}</div>
      </div>
    </div>,
    document.body
  );
}

function ContactPicker({
  selected,
  onToggle,
  single,
  exclude = [],
}: {
  selected: string[];
  onToggle: (c: ChatContact) => void;
  single?: boolean;
  exclude?: string[];
}) {
  const [q, setQ] = useState("");
  const contacts = useAsyncData("chat-contacts", () => fetchContacts());
  const items = (contacts.data || []).filter((c) => !exclude.includes(c.user_id) && (!q || c.display_name.toLowerCase().includes(q.toLowerCase())));
  return (
    <div className="flex flex-col gap-2">
      <label className="flex items-center gap-2 rounded-2xl skeuo-input px-3.5 py-2.5">
        <Search className="h-4 w-4 text-[var(--fb-ink-muted)]" aria-hidden="true" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ism bo‘yicha qidirish" aria-label="Kontaktlarni qidirish" className="min-w-0 flex-1 bg-transparent text-sm outline-none" />
      </label>
      {contacts.isLoading ? (
        <p className="flex items-center gap-2 py-6 text-xs text-[var(--fb-ink-muted)]"><Loader2 className="h-4 w-4 animate-spin" /> Kontaktlar yuklanmoqda…</p>
      ) : contacts.error ? (
        <p role="alert" className="py-4 text-xs text-rose-700 dark:text-rose-300">{contacts.error.message}</p>
      ) : items.length === 0 ? (
        <p className="rounded-2xl skeuo-well px-4 py-5 text-center text-xs text-[var(--fb-ink-secondary)]">
          {q ? "Hech kim topilmadi." : "Hozircha kontaktlar yo‘q. Hamkasblar, ariza bergan korxona yoki universitetingiz xodimlari shu yerda chiqadi. Boshqalar bilan kontakt kod orqali bog‘laning."}
        </p>
      ) : (
        <ul className="flex max-h-72 flex-col gap-1.5 overflow-y-auto">
          {items.map((c) => {
            const on = selected.includes(c.user_id);
            return (
              <li key={c.user_id}>
                <button type="button" onClick={() => onToggle(c)} aria-pressed={single ? undefined : on} className="fb-file-row w-full text-left">
                  <span className="fb-avatar h-9 w-9 text-xs" aria-hidden="true">{initials(c.display_name)}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold text-[var(--fb-ink)]">{c.display_name}</span>
                    <span className="block text-[11px] text-[var(--fb-ink-muted)]">{RELATION_LABEL[c.relation] || c.relation}</span>
                  </span>
                  {!single && (
                    <span className={`flex h-6 w-6 items-center justify-center rounded-full ${on ? "fb-nav-active" : "ring-1 ring-[var(--fb-hairline)]"}`}>
                      {on && <Check className="h-3.5 w-3.5" />}
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function NewChatDialog({ onClose, onOpened }: { onClose: () => void; onOpened: (c: ChatConversationDetail) => void }) {
  const [mode, setMode] = useState<"direct" | "group">("direct");
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [members, setMembers] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mine = useAsyncData("chat-my-code", fetchMyContactCode);
  const [copied, setCopied] = useState(false);

  const run = async (fn: () => Promise<ChatConversationDetail>) => {
    setBusy(true);
    setError(null);
    try {
      onOpened(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Xatolik");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Yangi suhbat" onClose={onClose}>
      <div className="fb-seg mb-4" role="group" aria-label="Suhbat turi">
        <button type="button" aria-pressed={mode === "direct"} onClick={() => setMode("direct")}>Shaxsiy</button>
        <button type="button" aria-pressed={mode === "group"} onClick={() => setMode("group")}>Guruh</button>
      </div>
      {error && <p role="alert" className="mb-3 rounded-2xl bg-rose-500/10 px-3.5 py-2.5 text-xs text-rose-700 dark:text-rose-300">{error}</p>}

      {mode === "direct" ? (
        <div className="flex flex-col gap-4">
          <ContactPicker single selected={[]} onToggle={(c) => !busy && run(() => startDirect({ user_id: c.user_id }))} />
          <form
            className="flex flex-col gap-2 border-t border-[var(--fb-border)] pt-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (code.trim().length === 8) run(() => startDirect({ contact_code: code.trim().toUpperCase() }));
            }}
          >
            <label htmlFor="chat-code" className="text-xs font-medium text-[var(--fb-ink-secondary)]">Kontakt kod orqali</label>
            <div className="flex gap-2">
              <input
                id="chat-code"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/[^a-z0-9]/gi, "").slice(0, 8).toUpperCase())}
                placeholder="8 belgili kod"
                className="skeuo-input min-w-0 flex-1 rounded-2xl px-3.5 py-2.5 font-semibold tracking-[0.2em]"
              />
              <button type="submit" disabled={busy || code.length !== 8} className="rounded-full skeuo-btn-obsidian px-4 text-xs font-semibold disabled:opacity-50">Yozish</button>
            </div>
          </form>
          <div className="flex items-center justify-between gap-3 rounded-2xl skeuo-well px-4 py-3">
            <div className="min-w-0">
              <p className="text-[11px] text-[var(--fb-ink-muted)]">Sizning kodingiz — faqat ishongan odamga bering</p>
              <p className="text-lg font-bold tracking-[0.2em] text-[var(--fb-ink)]">{mine.data?.contact_code ?? "········"}</p>
            </div>
            <div className="flex gap-1.5">
              <button
                type="button"
                className="fb-icon-btn fb-icon-btn-light h-9 w-9"
                aria-label="Kodni nusxalash"
                onClick={() => {
                  if (!mine.data) return;
                  void navigator.clipboard?.writeText(mine.data.contact_code).then(() => setCopied(true));
                }}
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </button>
              <button
                type="button"
                className="fb-icon-btn fb-icon-btn-light h-9 w-9"
                aria-label="Yangi kod yaratish (eskisi ishlamay qoladi)"
                title="Yangi kod (eskisi ishlamay qoladi)"
                onClick={() => void rotateContactCode().then((r) => { mine.mutate(() => r); setCopied(false); })}
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (title.trim()) run(() => createGroup(title.trim(), members));
          }}
        >
          <label className="flex flex-col gap-1.5 text-xs font-medium text-[var(--fb-ink-secondary)]">
            Guruh nomi
            <input value={title} onChange={(e) => setTitle(e.target.value.slice(0, 80))} placeholder="Masalan: Backend amaliyotchilari" className="skeuo-input rounded-2xl px-3.5 py-2.5 text-sm" />
          </label>
          <p className="text-xs font-medium text-[var(--fb-ink-secondary)]">A’zolar ({members.length})</p>
          <ContactPicker selected={members} onToggle={(c) => setMembers((m) => (m.includes(c.user_id) ? m.filter((x) => x !== c.user_id) : [...m, c.user_id]))} />
          <p className="text-[11px] text-[var(--fb-ink-muted)]">Kontaktlaringizda bo‘lmaganlarni keyin taklif havolasi orqali qo‘shasiz.</p>
          <button type="submit" disabled={busy || !title.trim()} className="rounded-full skeuo-btn-obsidian px-5 py-2.5 text-sm font-semibold disabled:opacity-50">
            {busy ? "Yaratilmoqda…" : "Guruh yaratish"}
          </button>
        </form>
      )}
    </Modal>
  );
}

export function ConversationSettings({
  detail,
  meId,
  onClose,
  onChanged,
  onLeft,
}: {
  detail: ChatConversationDetail;
  meId: string;
  onClose: () => void;
  onChanged: () => void;
  onLeft: () => void;
}) {
  const isOwner = detail.my_role === "OWNER";
  const [title, setTitle] = useState(detail.title);
  const [adding, setAdding] = useState<string[]>([]);
  const [link, setLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const act = async (fn: () => Promise<unknown>, after?: () => void) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      after?.();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Xatolik");
    } finally {
      setBusy(false);
    }
  };

  if (detail.kind === "DIRECT") {
    return (
      <Modal title={detail.title} onClose={onClose}>
        {error && <p role="alert" className="mb-3 text-xs text-rose-700 dark:text-rose-300">{error}</p>}
        <p className="mb-4 text-sm text-[var(--fb-ink-secondary)]">
          {detail.blocked ? "Bu suhbat bloklangan: hech biringiz xabar yubora olmaysiz." : "Bloklasangiz, u sizga yoza olmaydi va kontaktlaringizdan yo‘qoladi."}
        </p>
        <button
          type="button"
          disabled={busy || !detail.partner_id}
          onClick={() => act(() => setBlocked(detail.partner_id as string, !detail.blocked))}
          className="inline-flex items-center gap-2 rounded-full skeuo-btn-secondary px-4 py-2.5 text-xs font-semibold"
        >
          <ShieldOff className="h-4 w-4" /> {detail.blocked ? "Blokdan chiqarish" : "Bloklash"}
        </button>
      </Modal>
    );
  }

  const memberIds = detail.members.map((m) => m.user_id);
  return (
    <Modal title="Guruh sozlamalari" onClose={onClose}>
      {error && <p role="alert" className="mb-3 rounded-2xl bg-rose-500/10 px-3.5 py-2.5 text-xs text-rose-700 dark:text-rose-300">{error}</p>}
      <div className="flex flex-col gap-5">
        {isOwner && (
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (title.trim()) void act(() => renameGroup(detail.id, title.trim())); }}>
            <input aria-label="Guruh nomi" value={title} onChange={(e) => setTitle(e.target.value.slice(0, 80))} className="skeuo-input min-w-0 flex-1 rounded-2xl px-3.5 py-2.5 text-sm" />
            <button type="submit" disabled={busy || title.trim() === detail.title} className="rounded-full skeuo-btn-obsidian px-4 text-xs font-semibold disabled:opacity-50">Saqlash</button>
          </form>
        )}

        <section aria-labelledby="chat-members">
          <h3 id="chat-members" className="mb-2 text-xs font-medium text-[var(--fb-ink-secondary)]">A’zolar ({detail.members.length})</h3>
          <ul className="flex flex-col gap-1.5">
            {detail.members.map((m) => (
              <li key={m.user_id} className="fb-file-row">
                <span className="fb-avatar h-8 w-8 text-[11px]" aria-hidden="true">{initials(m.display_name)}</span>
                <span className="min-w-0 flex-1 truncate text-sm font-semibold text-[var(--fb-ink)]">
                  {m.display_name}{m.user_id === meId ? " (siz)" : ""}
                </span>
                {m.role === "OWNER" && <span className="fb-capsule px-2.5 py-0.5 text-[11px] font-semibold">Egasi</span>}
                {isOwner && m.user_id !== meId && (
                  <button type="button" disabled={busy} onClick={() => act(() => removeGroupMember(detail.id, m.user_id))} className="rounded-full p-1.5 text-[var(--fb-ink-muted)] hover:text-rose-600" aria-label={`${m.display_name}ni guruhdan chiqarish`}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>

        {isOwner && (
          <section className="flex flex-col gap-2" aria-labelledby="chat-add">
            <h3 id="chat-add" className="text-xs font-medium text-[var(--fb-ink-secondary)]">A’zo qo‘shish</h3>
            <ContactPicker exclude={memberIds} selected={adding} onToggle={(c) => setAdding((a) => (a.includes(c.user_id) ? a.filter((x) => x !== c.user_id) : [...a, c.user_id]))} />
            <button type="button" disabled={busy || adding.length === 0} onClick={() => act(() => addGroupMembers(detail.id, adding), () => setAdding([]))} className="inline-flex w-fit items-center gap-2 rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold disabled:opacity-50">
              <UserPlus className="h-4 w-4" /> Qo‘shish ({adding.length})
            </button>
          </section>
        )}

        {isOwner && (
          <section className="flex flex-col gap-2 rounded-2xl skeuo-well px-4 py-3" aria-labelledby="chat-link">
            <h3 id="chat-link" className="flex items-center gap-2 text-xs font-semibold text-[var(--fb-ink-secondary)]"><Link2 className="h-4 w-4" /> Taklif havolasi</h3>
            {link ? (
              <>
                <input readOnly value={inviteUrl(link)} aria-label="Taklif havolasi" onFocus={(e) => e.currentTarget.select()} className="skeuo-input rounded-xl px-3 py-2 text-xs" />
                <p className="text-[11px] text-[var(--fb-ink-muted)]">Havola faqat hozir ko‘rinadi. Kimda bo‘lsa, guruhga qo‘shila oladi — o‘chirsangiz, ishlamay qoladi.</p>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => void navigator.clipboard?.writeText(inviteUrl(link))} className="inline-flex items-center gap-1.5 rounded-full skeuo-btn-obsidian px-3.5 py-1.5 text-xs font-semibold"><Copy className="h-3.5 w-3.5" /> Nusxalash</button>
                  <button type="button" onClick={() => act(() => disableInviteLink(detail.id), () => setLink(null))} className="rounded-full skeuo-btn-secondary px-3.5 py-1.5 text-xs font-semibold">O‘chirish</button>
                </div>
              </>
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                <button type="button" disabled={busy} onClick={() => act(async () => setLink((await enableInviteLink(detail.id)).invite_token))} className="rounded-full skeuo-btn-obsidian px-3.5 py-1.5 text-xs font-semibold">
                  {detail.invite_link_active ? "Yangi havola yaratish" : "Havola yaratish"}
                </button>
                {detail.invite_link_active && (
                  <button type="button" disabled={busy} onClick={() => act(() => disableInviteLink(detail.id))} className="rounded-full skeuo-btn-secondary px-3.5 py-1.5 text-xs font-semibold">Faol havolani o‘chirish</button>
                )}
              </div>
            )}
          </section>
        )}

        <button
          type="button"
          disabled={busy}
          onClick={() => act(() => removeGroupMember(detail.id, meId), onLeft)}
          className="inline-flex w-fit items-center gap-2 rounded-full px-3 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-500/10"
        >
          <LogOut className="h-4 w-4" /> Guruhdan chiqish
        </button>
      </div>
    </Modal>
  );
}
