"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Loader2, MessageSquarePlus, Search, Send, Settings2, Trash2, Users } from "lucide-react";
import {
  chatTime,
  deleteMessage,
  fetchConversation,
  fetchConversations,
  fetchMessages,
  joinByToken,
  markRead,
  sendMessage,
  type ChatConversation,
  type ChatConversationDetail,
  type ChatMessage,
} from "@/lib/chat";
import { initials } from "@/lib/person";
import { useAsyncData } from "@/lib/useAsyncData";
import { ConversationSettings, NewChatDialog } from "./ChatDialogs";

const LIST_POLL_MS = 15_000;
const THREAD_POLL_MS = 4_000;

function usePoll(fn: () => void, ms: number, enabled: boolean) {
  const ref = useRef(fn);
  useEffect(() => {
    ref.current = fn;
  });
  useEffect(() => {
    if (!enabled) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") ref.current();
    }, ms);
    return () => window.clearInterval(id);
  }, [ms, enabled]);
}

function preview(c: ChatConversation): string {
  const m = c.last_message;
  if (!m) return c.kind === "GROUP" ? `${c.member_count} a’zo` : "Hali xabar yo‘q";
  const who = m.mine ? "Siz: " : c.kind === "GROUP" ? `${m.sender_name.split(/\s+/)[0]}: ` : "";
  return who + (m.deleted ? "xabar o‘chirildi" : m.body || "");
}

function ConversationList({
  items,
  activeId,
  onSelect,
  onNew,
  loading,
  error,
}: {
  items: ChatConversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  loading: boolean;
  error: Error | null;
}) {
  const [q, setQ] = useState("");
  const shown = items.filter((c) => !q || c.title.toLowerCase().includes(q.toLowerCase()));
  return (
    <section className="fb-panel skeuo-card flex min-h-0 flex-col gap-3 p-4" aria-label="Suhbatlar">
      <div className="flex items-center justify-between gap-2 px-1">
        <h2 className="text-base font-semibold text-[var(--fb-ink)]">Suhbatlar</h2>
        <button type="button" onClick={onNew} className="fb-icon-btn h-9 w-9" aria-label="Yangi suhbat yoki guruh">
          <MessageSquarePlus className="h-4 w-4" />
        </button>
      </div>
      <label className="flex items-center gap-2 rounded-2xl skeuo-input px-3 py-2">
        <Search className="h-4 w-4 text-[var(--fb-ink-muted)]" aria-hidden="true" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Qidirish" aria-label="Suhbatlarni qidirish" className="min-w-0 flex-1 bg-transparent text-sm outline-none" />
      </label>
      {error && <p role="alert" className="px-1 text-xs text-rose-700 dark:text-rose-300">{error.message}</p>}
      {loading && items.length === 0 ? (
        <p className="flex items-center gap-2 px-1 py-6 text-xs text-[var(--fb-ink-muted)]"><Loader2 className="h-4 w-4 animate-spin" /> Yuklanmoqda…</p>
      ) : shown.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl skeuo-well px-4 py-8 text-center">
          <p className="text-sm font-semibold text-[var(--fb-ink)]">{q ? "Topilmadi" : "Hali suhbat yo‘q"}</p>
          {!q && (
            <button type="button" onClick={onNew} className="rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold">Birinchi suhbatni boshlash</button>
          )}
        </div>
      ) : (
        <ul className="-mx-1 flex min-h-0 flex-col gap-1 overflow-y-auto px-1">
          {shown.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => onSelect(c.id)}
                aria-current={c.id === activeId ? "true" : undefined}
                className={`flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-left transition-colors ${
                  c.id === activeId ? "fb-nav-active" : "hover:bg-[var(--fb-well-deep)]"
                }`}
              >
                <span className="fb-avatar h-10 w-10 shrink-0 text-xs" aria-hidden="true">
                  {c.kind === "GROUP" ? <Users className="h-4 w-4" /> : initials(c.title)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-semibold">{c.title}</span>
                    <span className="shrink-0 text-[11px] opacity-70 tabular-nums">{c.last_message ? chatTime(c.last_message.created_at) : ""}</span>
                  </span>
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs opacity-70">{preview(c)}</span>
                    {c.unread_count > 0 && (
                      <span className="shrink-0 rounded-full bg-[var(--fb-accent)] px-1.5 py-0.5 text-[10px] font-bold text-white tabular-nums" aria-label={`${c.unread_count} ta o‘qilmagan`}>
                        {c.unread_count > 99 ? "99+" : c.unread_count}
                      </span>
                    )}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Thread({
  conversationId,
  meId,
  onBack,
  onActivity,
  onLeft,
}: {
  conversationId: string;
  meId: string;
  onBack: () => void;
  onActivity: () => void;
  onLeft: () => void;
}) {
  const detail = useAsyncData(`chat-detail:${conversationId}`, () => fetchConversation(conversationId));
  const latest = useAsyncData(`chat-msgs:${conversationId}`, () => fetchMessages(conversationId));
  const [older, setOlder] = useState<{ id: string; items: ChatMessage[]; hasMore: boolean | null }>({ id: conversationId, items: [], hasMore: null });
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  // Reset paged history when switching conversations (render-time adjustment).
  if (older.id !== conversationId) setOlder({ id: conversationId, items: [], hasMore: null });

  const messages = useMemo(() => {
    const seen = new Set<string>();
    return [...older.items, ...(latest.data?.items || [])].filter((m) => (seen.has(m.id) ? false : (seen.add(m.id), true)));
  }, [older.items, latest.data]);
  const hasMore = older.hasMore ?? latest.data?.has_more ?? false;
  const lastId = messages[messages.length - 1]?.id;

  usePoll(() => void latest.reload(), THREAD_POLL_MS, true);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [lastId]);

  useEffect(() => {
    if (!lastId) return;
    void markRead(conversationId).then(onActivity).catch(() => undefined);
  }, [conversationId, lastId, onActivity]);

  const loadOlder = async () => {
    const first = messages[0];
    if (!first) return;
    const page = await fetchMessages(conversationId, first.id);
    setOlder((o) => ({ id: conversationId, items: [...page.items, ...o.items], hasMore: page.has_more }));
  };

  const submit = async () => {
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    setError(null);
    try {
      await sendMessage(conversationId, body);
      setDraft("");
      await latest.reload();
      onActivity();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Yuborib bo‘lmadi");
    } finally {
      setSending(false);
    }
  };

  const d: ChatConversationDetail | undefined = detail.data;
  return (
    <section className="fb-panel skeuo-card flex min-h-0 flex-col" aria-label={d ? `Suhbat: ${d.title}` : "Suhbat"}>
      <header className="flex items-center gap-3 border-b border-[var(--fb-border)] px-4 py-3">
        <button type="button" onClick={onBack} className="fb-icon-btn fb-icon-btn-light h-9 w-9 lg:hidden" aria-label="Suhbatlar ro‘yxatiga qaytish">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <span className="fb-avatar h-10 w-10 shrink-0 text-xs" aria-hidden="true">
          {d?.kind === "GROUP" ? <Users className="h-4 w-4" /> : initials(d?.title)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-[var(--fb-ink)]">{d?.title ?? "…"}</p>
          <p className="truncate text-xs text-[var(--fb-ink-muted)]">
            {d ? (d.kind === "GROUP" ? `${d.member_count} a’zo${d.my_role === "OWNER" ? " · siz egasiz" : ""}` : d.blocked ? "Bloklangan" : "Shaxsiy suhbat") : ""}
          </p>
        </div>
        <button type="button" disabled={!d} onClick={() => setSettingsOpen(true)} className="fb-icon-btn fb-icon-btn-light h-9 w-9" aria-label="Suhbat sozlamalari">
          <Settings2 className="h-4 w-4" />
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4" aria-live="polite">
        {detail.error ? (
          <p role="alert" className="py-10 text-center text-sm text-[var(--fb-ink-secondary)]">{detail.error.message}</p>
        ) : latest.isLoading && !latest.data ? (
          <p className="flex items-center justify-center gap-2 py-10 text-xs text-[var(--fb-ink-muted)]"><Loader2 className="h-4 w-4 animate-spin" /> Xabarlar yuklanmoqda…</p>
        ) : (
          <ol className="flex flex-col gap-2">
            {hasMore && (
              <li className="flex justify-center pb-2">
                <button type="button" onClick={() => void loadOlder()} className="fb-capsule px-3 py-1 text-xs font-semibold">Oldingi xabarlar</button>
              </li>
            )}
            {messages.length === 0 && <li className="py-10 text-center text-sm text-[var(--fb-ink-muted)]">Birinchi xabarni yozing.</li>}
            {messages.map((m, i) => {
              const prev = messages[i - 1];
              const showName = d?.kind === "GROUP" && !m.mine && prev?.sender_id !== m.sender_id;
              return (
                <li key={m.id} className={`group flex flex-col ${m.mine ? "items-end" : "items-start"}`}>
                  {showName && <span className="mb-0.5 px-3 text-[11px] font-semibold text-[var(--fb-ink-muted)]">{m.sender_name}</span>}
                  <div className="flex max-w-[85%] items-end gap-1.5 sm:max-w-[70%]">
                    {m.mine && !m.deleted && (
                      <button
                        type="button"
                        onClick={() => void deleteMessage(m.id).then(() => latest.reload()).then(onActivity)}
                        className="rounded-full p-1 text-[var(--fb-ink-muted)] opacity-0 hover:text-rose-600 focus:opacity-100 group-hover:opacity-100"
                        aria-label="Xabarni o‘chirish"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                    <div
                      className={`rounded-[20px] px-3.5 py-2 text-sm leading-relaxed ${
                        m.deleted
                          ? "italic text-[var(--fb-ink-muted)] ring-1 ring-[var(--fb-hairline)]"
                          : m.mine
                            ? "fb-nav-active rounded-br-md"
                            : "bg-[var(--fb-well-deep)] text-[var(--fb-ink)] rounded-bl-md"
                      }`}
                    >
                      <p className="whitespace-pre-wrap break-words">{m.deleted ? "Xabar o‘chirildi" : m.body}</p>
                      <p className={`mt-0.5 text-right text-[10px] tabular-nums ${m.mine && !m.deleted ? "opacity-70" : "text-[var(--fb-ink-muted)]"}`}>{chatTime(m.created_at)}</p>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
        <div ref={bottom} />
      </div>

      <form
        className="flex items-end gap-2 border-t border-[var(--fb-border)] p-3"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <label htmlFor="chat-composer" className="sr-only">Xabar</label>
        <textarea
          id="chat-composer"
          rows={1}
          value={draft}
          disabled={Boolean(d?.blocked)}
          onChange={(e) => setDraft(e.target.value.slice(0, 4000))}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              void submit();
            }
          }}
          placeholder={d?.blocked ? "Bu suhbat bloklangan" : "Xabar yozing…"}
          title="Enter — yuborish, Shift+Enter — yangi qator"
          className="skeuo-input max-h-40 min-h-[44px] flex-1 resize-none rounded-2xl px-4 py-2.5 text-sm"
        />
        <button type="submit" disabled={sending || !draft.trim() || Boolean(d?.blocked)} className="fb-icon-btn h-11 w-11 shrink-0 disabled:opacity-40" aria-label="Yuborish">
          {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </form>
      {error && <p role="alert" className="px-4 pb-3 text-xs text-rose-700 dark:text-rose-300">{error}</p>}

      {settingsOpen && d && (
        <ConversationSettings
          detail={d}
          meId={meId}
          onClose={() => setSettingsOpen(false)}
          onChanged={() => {
            void detail.reload();
            onActivity();
          }}
          onLeft={() => {
            setSettingsOpen(false);
            onLeft();
          }}
        />
      )}
    </section>
  );
}

/** Two-pane messenger: conversation list + thread (one pane at a time on mobile). */
export default function ChatApp({ meId, joinToken, onJoinHandled }: { meId: string; joinToken?: string | null; onJoinHandled?: () => void }) {
  const list = useAsyncData("chat-conversations", fetchConversations);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [newOpen, setNewOpen] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);
  const reloadList = list.reload;
  const handledToken = useRef<string | null>(null);

  usePoll(() => void reloadList(), LIST_POLL_MS, true);

  useEffect(() => {
    if (!joinToken || handledToken.current === joinToken) return;
    handledToken.current = joinToken;
    joinByToken(joinToken)
      .then((c) => {
        setActiveId(c.id);
        void reloadList();
      })
      .catch((e: unknown) => setJoinError(e instanceof Error ? e.message : "Guruhga qo‘shilib bo‘lmadi"))
      .finally(() => onJoinHandled?.());
  }, [joinToken, onJoinHandled, reloadList]);

  const items = list.data?.items || [];
  const onActivity = React.useCallback(() => void reloadList(), [reloadList]);

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-[var(--fb-ink-muted)]">Hamkasblar, korxonalar va universitet bilan</p>
          <h1 className="fb-display mt-1">Xabarlar</h1>
        </div>
        <button type="button" onClick={() => setNewOpen(true)} className="inline-flex items-center gap-2 rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold">
          <MessageSquarePlus className="h-4 w-4" /> Yangi suhbat
        </button>
      </header>
      {joinError && <p role="alert" className="fb-panel skeuo-card px-4 py-3 text-sm text-rose-700 dark:text-rose-300">{joinError}</p>}

      <div className="grid h-[calc(100dvh-15rem)] min-h-[480px] grid-cols-1 gap-4 lg:grid-cols-[340px_minmax(0,1fr)]">
        <div className={`min-h-0 ${activeId ? "hidden lg:flex" : "flex"} flex-col`}>
          <ConversationList items={items} activeId={activeId} onSelect={setActiveId} onNew={() => setNewOpen(true)} loading={list.isLoading} error={list.error} />
        </div>
        <div className={`min-h-0 ${activeId ? "flex" : "hidden lg:flex"} flex-col`}>
          {activeId ? (
            <Thread
              key={activeId}
              conversationId={activeId}
              meId={meId}
              onBack={() => setActiveId(null)}
              onActivity={onActivity}
              onLeft={() => {
                setActiveId(null);
                void reloadList();
              }}
            />
          ) : (
            <section className="fb-panel skeuo-card flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
              <span className="fb-avatar h-14 w-14" aria-hidden="true"><Users className="h-6 w-6" /></span>
              <p className="text-base font-semibold text-[var(--fb-ink)]">Suhbatni tanlang</p>
              <p className="max-w-sm text-sm text-[var(--fb-ink-secondary)]">Shaxsiy yozishmalar va guruhlar shu yerda. Yangi guruh ochib, a’zolarni kontaktlardan yoki taklif havolasi orqali qo‘shing.</p>
            </section>
          )}
        </div>
      </div>

      {newOpen && (
        <NewChatDialog
          onClose={() => setNewOpen(false)}
          onOpened={(c) => {
            setNewOpen(false);
            setActiveId(c.id);
            void reloadList();
          }}
        />
      )}
    </div>
  );
}
