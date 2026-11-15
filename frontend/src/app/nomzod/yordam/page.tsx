"use client";

import { useState, useCallback } from "react";
import {
  LifeBuoy,
  ShieldCheck,
  Bell,
  Send,
  Plus,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Trash2,
  Download,
  Edit3,
  X,
  MessageSquare,
  ChevronRight,
} from "lucide-react";
import {
  fetchMySupportTickets,
  createSupportTicket,
  fetchSupportTicketMessages,
  postCustomerSupportMessage,
  fetchMyPrivacyRequests,
  createPrivacyRequest,
  fetchMyNotificationPreferences,
  updateMyNotificationPreferences,
  CustomerSupportTicketItem,
  CustomerSupportMessageItem,
  CustomerPrivacyRequestItem,
  NotificationPreferenceItem,
} from "@/lib/api";
import { describeRequestError } from "@/lib/errors";
import { useAsyncData } from "@/lib/useAsyncData";

type ActiveTab = "TICKETS" | "PRIVACY" | "NOTIFICATIONS";

const EMPTY_TICKETS: CustomerSupportTicketItem[] = [];
const EMPTY_PRIVACY_REQUESTS: CustomerPrivacyRequestItem[] = [];
const EMPTY_PREFERENCES: NotificationPreferenceItem[] = [];

async function loadTicketItems(): Promise<CustomerSupportTicketItem[]> {
  return (await fetchMySupportTickets()).items || [];
}

async function loadPrivacyRequestItems(): Promise<CustomerPrivacyRequestItem[]> {
  return (await fetchMyPrivacyRequests()).items || [];
}

async function loadPreferenceItems(): Promise<NotificationPreferenceItem[]> {
  return (await fetchMyNotificationPreferences()).preferences || [];
}

export default function CandidateHelpPrivacyPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("TICKETS");

  // ---------------------------------------------------------------------------
  // Tab 1: Support Tickets State
  // ---------------------------------------------------------------------------
  const ticketsQuery = useAsyncData("support-tickets", loadTicketItems);
  const tickets = ticketsQuery.data ?? EMPTY_TICKETS;
  const isLoadingTickets = ticketsQuery.isLoading;
  const ticketsError = ticketsQuery.error ? describeRequestError(ticketsQuery.error, "Murojaatlarni yuklashda xatolik") : null;

  // Create Ticket Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newSubject, setNewSubject] = useState("");
  const [newCategory, setNewCategory] = useState("GENERAL");
  const [newPriority, setNewPriority] = useState("NORMAL");
  const [newBody, setNewBody] = useState("");
  const [isSubmittingTicket, setIsSubmittingTicket] = useState(false);
  const [createTicketError, setCreateTicketError] = useState<string | null>(null);
  const [createTicketSuccess, setCreateTicketSuccess] = useState<string | null>(null);

  // Active Ticket Thread Drawer / Modal State
  const [selectedTicket, setSelectedTicket] = useState<CustomerSupportTicketItem | null>(null);
  const [messages, setMessages] = useState<CustomerSupportMessageItem[]>([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [messagesError, setMessagesError] = useState<string | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);
  const [replyError, setReplyError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Tab 2: Privacy Requests State
  // ---------------------------------------------------------------------------
  const privacyQuery = useAsyncData("privacy-requests", loadPrivacyRequestItems);
  const privacyRequests = privacyQuery.data ?? EMPTY_PRIVACY_REQUESTS;
  const isLoadingPrivacy = privacyQuery.isLoading;
  const privacyError = privacyQuery.error
    ? describeRequestError(privacyQuery.error, "Maxfiylik so'rovlarini yuklashda xatolik")
    : null;

  // Create Privacy Request Modal
  const [isPrivacyModalOpen, setIsPrivacyModalOpen] = useState(false);
  const [privacyKind, setPrivacyKind] = useState<"EXPORT" | "DELETE" | "RECTIFY">("EXPORT");
  const [privacyReason, setPrivacyReason] = useState("");
  const [isSubmittingPrivacy, setIsSubmittingPrivacy] = useState(false);
  const [privacySuccessMsg, setPrivacySuccessMsg] = useState<string | null>(null);
  const [privacySubmitError, setPrivacySubmitError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Tab 3: Notification Preferences State
  // ---------------------------------------------------------------------------
  const prefsQuery = useAsyncData("notification-preferences", loadPreferenceItems);
  const preferences = prefsQuery.data ?? EMPTY_PREFERENCES;
  const isLoadingPrefs = prefsQuery.isLoading;
  const setPreferences = (updater: (prev: NotificationPreferenceItem[]) => NotificationPreferenceItem[]) =>
    prefsQuery.mutate((prev) => updater(prev ?? EMPTY_PREFERENCES));
  // Save errors; load errors come from `prefsQuery.error`.
  const [prefsSaveError, setPrefsError] = useState<string | null>(null);
  const prefsError =
    prefsSaveError ??
    (prefsQuery.error ? describeRequestError(prefsQuery.error, "Bildirishnoma sozlamalarini yuklashda xatolik") : null);
  const [prefsSuccessMsg, setPrefsSuccessMsg] = useState<string | null>(null);
  const [isSavingPrefs, setIsSavingPrefs] = useState(false);

  // Load Messages for a Ticket (API-064)
  const loadMessages = useCallback(async (ticketId: string) => {
    setIsLoadingMessages(true);
    setMessagesError(null);
    try {
      const res = await fetchSupportTicketMessages(ticketId);
      setMessages(res.items || []);
    } catch (err: unknown) {
      setMessagesError(err instanceof Error ? err.message : "Xabarlarni yuklashda xatolik");
      setMessages([]);
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  const loadTickets = ticketsQuery.reload;
  const loadPrivacyRequests = privacyQuery.reload;
  const loadPreferences = () => {
    setPrefsError(null);
    return prefsQuery.reload();
  };

  // Switching tabs refreshes that tab, as before; counts in the tab headers
  // stay populated because every list loads once on mount.
  const selectTab = (tab: ActiveTab) => {
    if (tab === activeTab) return;
    setActiveTab(tab);
    if (tab === "TICKETS") void loadTickets();
    if (tab === "PRIVACY") void loadPrivacyRequests();
    if (tab === "NOTIFICATIONS") void loadPreferences();
  };

  // Open ticket details
  const handleSelectTicket = (t: CustomerSupportTicketItem) => {
    setSelectedTicket(t);
    setReplyBody("");
    setReplyError(null);
    loadMessages(t.id);
  };

  // Submit new ticket (API-063 POST)
  const handleCreateTicketSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newSubject.trim().length < 3) {
      setCreateTicketError("Mavzu kamida 3 ta belgidan iborat bo'lishi kerak.");
      return;
    }
    if (newBody.trim().length < 5) {
      setCreateTicketError("Xabar matni kamida 5 ta belgidan iborat bo'lishi kerak.");
      return;
    }

    setIsSubmittingTicket(true);
    setCreateTicketError(null);
    setCreateTicketSuccess(null);
    try {
      const res = await createSupportTicket({
        subject: newSubject.trim(),
        body: newBody.trim(),
        category: newCategory,
        priority: newPriority,
      });
      setCreateTicketSuccess(`Murojaat #${res.ticket_id?.slice(0, 8)} muvaffaqiyatli yaratildi!`);
      setNewSubject("");
      setNewBody("");
      setTimeout(() => {
        setIsCreateModalOpen(false);
        setCreateTicketSuccess(null);
        loadTickets();
      }, 1200);
    } catch (err: unknown) {
      setCreateTicketError(err instanceof Error ? err.message : "Murojaat yaratishda xatolik");
    } finally {
      setIsSubmittingTicket(false);
    }
  };

  // Reply to ticket (API-064 POST)
  const handleReplySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket || !replyBody.trim()) return;

    setIsSubmittingReply(true);
    setReplyError(null);
    try {
      await postCustomerSupportMessage(selectedTicket.id, {
        body: replyBody.trim(),
      });
      setReplyBody("");
      await loadMessages(selectedTicket.id);
    } catch (err: unknown) {
      setReplyError(err instanceof Error ? err.message : "Xabar yuborishda xatolik");
    } finally {
      setIsSubmittingReply(false);
    }
  };

  // Submit privacy request (API-062 POST)
  const handlePrivacySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingPrivacy(true);
    setPrivacySubmitError(null);
    setPrivacySuccessMsg(null);
    try {
      const res = await createPrivacyRequest({
        kind: privacyKind,
        reason: privacyReason.trim() || undefined,
      });
      setPrivacySuccessMsg(`Maxfiylik so'rovi #${res.request_id?.slice(0, 8)} qabul qilindi!`);
      setPrivacyReason("");
      setTimeout(() => {
        setIsPrivacyModalOpen(false);
        setPrivacySuccessMsg(null);
        loadPrivacyRequests();
      }, 1200);
    } catch (err: unknown) {
      setPrivacySubmitError(err instanceof Error ? err.message : "So'rov yuborishda xatolik");
    } finally {
      setIsSubmittingPrivacy(false);
    }
  };

  // Toggle notification channel
  const handleTogglePref = (channel: string, purpose: string) => {
    setPreferences((prev) =>
      prev.map((p) => {
        if (p.channel === channel && p.purpose === purpose) {
          return { ...p, enabled: !p.enabled };
        }
        return p;
      })
    );
  };

  // Save notification preferences (API-059 PUT)
  const handleSavePreferences = async () => {
    setIsSavingPrefs(true);
    setPrefsError(null);
    setPrefsSuccessMsg(null);
    try {
      const res = await updateMyNotificationPreferences(preferences);
      const saved = res.preferences;
      if (saved) setPreferences(() => saved);
      setPrefsSuccessMsg("Bildirishnoma sozlamalari muvaffaqiyatli saqlandi!");
      setTimeout(() => setPrefsSuccessMsg(null), 3000);
    } catch (err: unknown) {
      setPrefsError(err instanceof Error ? err.message : "Sozlamalarni saqlashda xatolik");
    } finally {
      setIsSavingPrefs(false);
    }
  };

  return (
    <div className="w-full text-zinc-100 space-y-6">
      <div className="w-full space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <LifeBuoy className="w-6 h-6 text-sky-400" />
              Yordam Markazi, Maxfiylik & Bildirishnomalar Hubi
            </h1>
            <p className="text-xs text-[var(--fb-ink-secondary)] mt-1">
              Texnik qo‘llab-quvvatlash murojaatlari, shaxsiy ma’lumotlar maxfiyligi va bildirishnomalar boshqaruvi.
            </p>
          </div>
          <button
            onClick={() => {
              if (activeTab === "TICKETS") loadTickets();
              if (activeTab === "PRIVACY") loadPrivacyRequests();
              if (activeTab === "NOTIFICATIONS") loadPreferences();
            }}
            className="px-3.5 py-2 text-xs font-semibold rounded-xl skeuo-btn-secondary flex items-center gap-2 self-start md:self-auto"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[var(--fb-ink-muted)]" />
            Yangilash
          </button>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-2 border-b border-[var(--fb-hairline)] pb-1 overflow-x-auto">
          <button
            onClick={() => selectTab("TICKETS")}
            className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "TICKETS"
                ? "skeuo-btn-obsidian text-white"
                : "text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]"
            }`}
          >
            <MessageSquare className="w-4 h-4 text-sky-400" />
            <span>Murojaatlar & Yordam</span>
            <span className="px-1.5 py-0.2 rounded-full bg-sky-500/20 text-sky-300 text-[10px] font-mono">
              {tickets.length}
            </span>
          </button>

          <button
            onClick={() => selectTab("PRIVACY")}
            className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "PRIVACY"
                ? "skeuo-btn-obsidian text-white"
                : "text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]"
            }`}
          >
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Maxfiylik Huquqlari</span>
            <span className="px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-mono">
              {privacyRequests.length}
            </span>
          </button>

          <button
            onClick={() => selectTab("NOTIFICATIONS")}
            className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "NOTIFICATIONS"
                ? "skeuo-btn-obsidian text-white"
                : "text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]"
            }`}
          >
            <Bell className="w-4 h-4 text-amber-400" />
            <span>Bildirishnomalar Sozlamalari</span>
          </button>
        </div>

        {/* ------------------------------------------------------------------- */}
        {/* TAB 1: SUPPORT TICKETS & HELP DESK */}
        {/* ------------------------------------------------------------------- */}
        {activeTab === "TICKETS" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">Texnik Qo‘llab-Quvvatlash Chiptalari</h3>
                <p className="text-xs text-zinc-400">Platforma operatori va xavfsizlik xizmati bilan to‘g‘ridan-to‘g‘ri aloqa.</p>
              </div>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(true)}
                className="px-3.5 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white flex items-center gap-1.5 transition-all shadow-md shadow-primary/20"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Yangi Murojaat</span>
              </button>
            </div>

            {ticketsError && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{ticketsError}</span>
              </div>
            )}

            {isLoadingTickets ? (
              <div className="p-12 text-center text-xs text-zinc-400 flex items-center justify-center gap-2 bg-[#121214] border border-white/[0.08] rounded-xl">
                <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
                <span>Chiptalar yuklanmoqda...</span>
              </div>
            ) : tickets.length === 0 ? (
              <div className="p-12 text-center text-xs text-zinc-400 bg-[#121214] border border-white/[0.08] rounded-xl flex flex-col items-center justify-center gap-2">
                <LifeBuoy className="w-8 h-8 text-zinc-600 mb-1" />
                <span className="font-semibold text-white">Hozirda faol murojaatlar yo‘q</span>
                <span className="text-zinc-500">Savol yoki muammo tug‘ilsa, bemalol yangi murojaat yo‘llang.</span>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {tickets.map((t) => (
                  <div
                    key={t.id}
                    onClick={() => handleSelectTicket(t)}
                    className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] hover:border-white/[0.18] transition-all cursor-pointer flex flex-col justify-between gap-3 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex flex-col gap-1">
                        <span className="text-[10px] font-mono text-zinc-500">#{t.id.slice(0, 8)} • {t.category}</span>
                        <h4 className="text-xs font-bold text-white line-clamp-1">{t.subject}</h4>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                          t.status === "RESOLVED" || t.status === "CLOSED"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : t.status === "IN_PROGRESS"
                            ? "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}
                      >
                        {t.status}
                      </span>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-white/[0.04] text-[11px] text-zinc-400">
                      <span>{new Date(t.created_at).toLocaleDateString()}</span>
                      <span className="text-sky-400 font-medium flex items-center gap-1 hover:underline">
                        Suhbatni ochish <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------------- */}
        {/* TAB 2: PRIVACY RIGHTS & GDPR (API-062) */}
        {/* ------------------------------------------------------------------- */}
        {activeTab === "PRIVACY" && (
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-semibold text-white">Maxfiylik Huquqlari & Ma’lumotlar Himoyasi (GDPR)</h3>
              <p className="text-xs text-zinc-400">
                O‘zbekiston Respublikasi &ldquo;Shaxsga doir ma&apos;lumotlar to‘g‘risida&rdquo;gi Qonuni va GDPR doirasidagi huquqlaringiz.
              </p>
            </div>

            {/* Quick Action Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] flex flex-col justify-between gap-3 shadow-sm">
                <div className="flex flex-col gap-1.5">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                    <Download className="w-4 h-4" />
                  </div>
                  <h4 className="text-xs font-bold text-white">Ma’lumotlarni Eksport Qilish</h4>
                  <p className="text-[11px] text-zinc-400">
                    Barcha profilingiz, arizalar, shartnomalar va baholar arxivini xavfsiz JSON/ZIP formatda yuklab oling.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setPrivacyKind("EXPORT");
                    setIsPrivacyModalOpen(true);
                  }}
                  className="w-full py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-emerald-400 transition-all text-center"
                >
                  Eksport So‘rovi Berish
                </button>
              </div>

              <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] flex flex-col justify-between gap-3 shadow-sm">
                <div className="flex flex-col gap-1.5">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                    <Edit3 className="w-4 h-4" />
                  </div>
                  <h4 className="text-xs font-bold text-white">Ma’lumotlarni Tuzatish</h4>
                  <p className="text-[11px] text-zinc-400">
                    Agar profilingizda noto‘g‘ri yoki eskirgan ma’lumotlar bo‘lsa, rasmiy tuzatish so‘rovini yo‘llang.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setPrivacyKind("RECTIFY");
                    setIsPrivacyModalOpen(true);
                  }}
                  className="w-full py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-amber-400 transition-all text-center"
                >
                  Tuzatish So‘rovi Berish
                </button>
              </div>

              <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] flex flex-col justify-between gap-3 shadow-sm">
                <div className="flex flex-col gap-1.5">
                  <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                    <Trash2 className="w-4 h-4" />
                  </div>
                  <h4 className="text-xs font-bold text-white">Hisobni O‘chirish (Forget Me)</h4>
                  <p className="text-[11px] text-zinc-400">
                    Profilingizni o‘chirish huquqi (qonuniy saqlash muddati bo‘lmagan barcha shaxsiy ma’lumotlar o‘chiriladi).
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setPrivacyKind("DELETE");
                    setIsPrivacyModalOpen(true);
                  }}
                  className="w-full py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-rose-400 transition-all text-center"
                >
                  O‘chirish So‘rovi Berish
                </button>
              </div>
            </div>

            {/* Privacy Requests History Table */}
            <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-5 flex flex-col gap-3 shadow-sm">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
                Maxfiylik So‘rovlari Tarixi ({privacyRequests.length})
              </h4>
              {privacyError && (
                <div role="alert" className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{privacyError}</span>
                </div>
              )}
              {isLoadingPrivacy ? (
                <div className="p-8 text-center text-xs text-zinc-400 flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                  <span>Yuklanmoqda...</span>
                </div>
              ) : privacyRequests.length === 0 ? (
                <div className="p-8 text-center text-xs text-zinc-500">
                  Hozircha maxfiylik so‘rovlari yuborilmagan.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/[0.08] text-zinc-400">
                        <th className="py-2.5 px-3">Sana</th>
                        <th className="py-2.5 px-3">So‘rov Turi</th>
                        <th className="py-2.5 px-3">Holat</th>
                        <th className="py-2.5 px-3">Izoh / Asoslantirish</th>
                        <th className="py-2.5 px-3">Natija</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {privacyRequests.map((req) => (
                        <tr key={req.id} className="hover:bg-white/[0.02]">
                          <td className="py-2.5 px-3 text-zinc-400 whitespace-nowrap">
                            {new Date(req.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-2.5 px-3 font-mono font-semibold text-white">
                            {req.kind}
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                                req.status === "COMPLETED" || req.status === "RESOLVED"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : req.status === "REJECTED"
                                  ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                                  : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                              }`}
                            >
                              {req.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-zinc-300 max-w-xs truncate">
                            {req.reason || "—"}
                          </td>
                          <td className="py-2.5 px-3">
                            {req.result_file_id ? (
                              <span className="text-emerald-400 font-mono text-[11px] underline">
                                Fayl tayyor
                              </span>
                            ) : req.resolution_reason ? (
                              <span className="text-zinc-400 text-[11px]">{req.resolution_reason}</span>
                            ) : (
                              <span className="text-zinc-500 text-[11px]">Ko‘rib chiqilmoqda</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------- */}
        {/* TAB 3: NOTIFICATION PREFERENCES (API-059) */}
        {/* ------------------------------------------------------------------- */}
        {activeTab === "NOTIFICATIONS" && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-white">Bildirishnoma va Xabardor Qilish Sozlamalari</h3>
                <p className="text-xs text-zinc-400">
                  Qaysi kanallar (Email, SMS, Push) orqali bildirishnoma olishni xohlashingizni belgilang.
                </p>
              </div>
              <button
                type="button"
                onClick={handleSavePreferences}
                disabled={isSavingPrefs}
                className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white flex items-center gap-1.5 transition-all self-start sm:self-auto shadow-md shadow-primary/20"
              >
                {isSavingPrefs ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                <span>Sozlamalarni Saqlash</span>
              </button>
            </div>

            {prefsSuccessMsg && (
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{prefsSuccessMsg}</span>
              </div>
            )}

            {prefsError && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{prefsError}</span>
              </div>
            )}

            {isLoadingPrefs ? (
              <div className="p-12 text-center text-xs text-zinc-400 flex items-center justify-center gap-2 bg-[#121214] border border-white/[0.08] rounded-xl">
                <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
                <span>Sozlamalar yuklanmoqda...</span>
              </div>
            ) : (
              <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-5 divide-y divide-white/[0.06] shadow-sm">
                {[
                  {
                    purpose: "SECURITY",
                    title: "Xavfsizlik va Hisob Xavfi (Majburiy)",
                    desc: "Yangi qurilmadan kirish, parolni yangilash, sessiyalarni tugatish kabi muhim xavfsizlik ogohlantirishlari.",
                    mandatory: true,
                  },
                  {
                    purpose: "TRANSACTIONAL",
                    title: "Shartnoma va Jarayonlar",
                    desc: "Ariza holati o‘zgarishi, taklif kelishi, amaliyot shartnomalari va tasdiqlar haqida bildirishnomalar.",
                    mandatory: false,
                  },
                  {
                    purpose: "OPPORTUNITIES",
                    title: "Yangi E’lonlar va Takliflar",
                    desc: "Ko‘nikmalaringizga mos yangi bo‘sh ish o‘rinlari va amaliyot dasturlari tavsiyalari.",
                    mandatory: false,
                  },
                  {
                    purpose: "MARKETING",
                    title: "Yangiliklar va Platforma Xabarlari",
                    desc: "FlexBridge yangiliklari, foydali maslahatlar va vebinarlar haqidagi xabarlar.",
                    mandatory: false,
                  },
                ].map((item) => (
                  <div key={item.purpose} className="py-4 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex flex-col gap-1 max-w-lg">
                      <h4 className="text-xs font-semibold text-white flex items-center gap-2">
                        <span>{item.title}</span>
                        {item.mandatory && (
                          <span className="px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px]">
                            Majburiy
                          </span>
                        )}
                      </h4>
                      <p className="text-[11px] text-zinc-400">{item.desc}</p>
                    </div>

                    <div className="flex items-center gap-3">
                      {["EMAIL", "SMS", "PUSH"].map((ch) => {
                        const current = preferences.find(
                          (p) => p.channel === ch && p.purpose === item.purpose
                        );
                        const isEnabled = current ? current.enabled : false;

                        return (
                          <button
                            key={ch}
                            type="button"
                            disabled={item.mandatory && ch === "EMAIL"}
                            onClick={() => handleTogglePref(ch, item.purpose)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium border transition-all ${
                              isEnabled
                                ? "bg-primary/20 text-primary border-primary/40"
                                : "bg-[#18181b] text-zinc-500 border-white/[0.08] hover:bg-white/[0.04]"
                            }`}
                          >
                            {ch}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* CREATE TICKET MODAL */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-[#121214] border border-white/[0.12] rounded-xl shadow-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <h3 className="text-sm font-semibold text-white">Yangi Yordam Murojaati Yaratish</h3>
              <button onClick={() => setIsCreateModalOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {createTicketError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{createTicketError}</span>
              </div>
            )}

            {createTicketSuccess && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{createTicketSuccess}</span>
              </div>
            )}

            <form onSubmit={handleCreateTicketSubmit} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">Mavzu</label>
                <input
                  type="text"
                  required
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  placeholder="Muammo haqida qisqacha (masalan: Kundalik yuklashda xatolik)..."
                  className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-zinc-300 block mb-1">Kategoriya</label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-2.5 text-xs text-zinc-300 focus:outline-none focus:border-primary/50"
                  >
                    <option value="GENERAL">Umumiy Savol</option>
                    <option value="TECHNICAL">Texnik Muammo</option>
                    <option value="PLACEMENT">Amaliyot & Kundalik</option>
                    <option value="ACCOUNT">Profil & Kirish</option>
                    <option value="BILLING">To‘lov & Tarif</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-zinc-300 block mb-1">Muhimlik</label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value)}
                    className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-2.5 text-xs text-zinc-300 focus:outline-none focus:border-primary/50"
                  >
                    <option value="LOW">Past (Low)</option>
                    <option value="NORMAL">O‘rtacha (Normal)</option>
                    <option value="HIGH">Yuqori (High)</option>
                    <option value="URGENT">Favqulodda (Urgent)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">Xabar Matni</label>
                <textarea
                  rows={4}
                  required
                  value={newBody}
                  onChange={(e) => setNewBody(e.target.value)}
                  placeholder="Muammo tafsilotlari, xato xabari yoki savolingiz..."
                  className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-medium text-zinc-300"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingTicket}
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white flex items-center gap-1.5 shadow-md shadow-primary/20"
                >
                  {isSubmittingTicket ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  <span>Yuborish</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TICKET CONVERSATION DRAWER / MODAL */}
      {selectedTicket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl bg-[#121214] border border-white/[0.12] rounded-xl shadow-2xl flex flex-col h-[650px] overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-white/[0.08] flex items-center justify-between shrink-0 bg-[#151518]">
              <div className="flex flex-col gap-0.5">
                <span className="text-[10px] font-mono text-zinc-400">
                  Murojaat #{selectedTicket.id.slice(0, 8)} • {selectedTicket.category}
                </span>
                <h3 className="text-xs font-bold text-white line-clamp-1">{selectedTicket.subject}</h3>
              </div>
              <button onClick={() => setSelectedTicket(null)} className="text-zinc-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Messages Body */}
            <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-[#0d0d0f]">
              {messagesError && (
                <div role="alert" className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{messagesError}</span>
                </div>
              )}
              {isLoadingMessages ? (
                <div className="p-8 text-center text-xs text-zinc-400 flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
                  <span>Suhbat yuklanmoqda...</span>
                </div>
              ) : messages.length === 0 ? (
                <div className="p-8 text-center text-xs text-zinc-500">Xabarlar mavjud emas.</div>
              ) : (
                messages.map((m) => (
                  <div
                    key={m.id}
                    className={`p-3 rounded-xl text-xs max-w-[85%] flex flex-col gap-1 ${
                      m.internal
                        ? "bg-amber-500/10 border border-amber-500/20 text-amber-200 ml-auto"
                        : "bg-[#18181b] border border-white/[0.06] text-zinc-200 mr-auto"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3 text-[10px] font-mono text-zinc-500">
                      <span>{m.internal ? "Ichki Operator" : "Xabar"}</span>
                      <span>{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    </div>
                    <p className="whitespace-pre-wrap leading-relaxed">{m.body}</p>
                  </div>
                ))
              )}
            </div>

            {/* Reply Input */}
            <form onSubmit={handleReplySubmit} className="p-3 border-t border-white/[0.08] bg-[#121214] flex flex-col gap-2 shrink-0">
              {replyError && (
                <div className="p-2 rounded bg-rose-500/10 text-rose-300 text-[11px] flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{replyError}</span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  required
                  value={replyBody}
                  onChange={(e) => setReplyBody(e.target.value)}
                  placeholder="Javob yozish..."
                  className="flex-1 bg-[#18181b] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50"
                />
                <button
                  type="submit"
                  disabled={isSubmittingReply || !replyBody.trim()}
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white flex items-center gap-1.5 shadow-md shadow-primary/20 shrink-0"
                >
                  {isSubmittingReply ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  <span>Yuborish</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CREATE PRIVACY REQUEST MODAL */}
      {isPrivacyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-[#121214] border border-white/[0.12] rounded-xl shadow-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <h3 className="text-sm font-semibold text-white">Maxfiylik So‘rovi Berish</h3>
              <button onClick={() => setIsPrivacyModalOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {privacySubmitError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{privacySubmitError}</span>
              </div>
            )}

            {privacySuccessMsg && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{privacySuccessMsg}</span>
              </div>
            )}

            <form onSubmit={handlePrivacySubmit} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">So‘rov Turi</label>
                <div className="grid grid-cols-3 gap-2">
                  {(["EXPORT", "RECTIFY", "DELETE"] as const).map((k) => (
                    <button
                      key={k}
                      type="button"
                      onClick={() => setPrivacyKind(k)}
                      className={`py-2 px-2.5 rounded-lg text-xs font-semibold border transition-all ${
                        privacyKind === k
                          ? "bg-primary text-white border-primary"
                          : "bg-surface text-zinc-400 border-white/[0.08] hover:bg-white/[0.04]"
                      }`}
                    >
                      {k}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">So‘rov Sababi / Tafsilotlar</label>
                <textarea
                  rows={3}
                  value={privacyReason}
                  onChange={(e) => setPrivacyReason(e.target.value)}
                  placeholder="Ixtiyoriy: So'rov haqida qo'shimcha ma'lumot kiriting..."
                  className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setIsPrivacyModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-medium text-zinc-300"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingPrivacy}
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white flex items-center gap-1.5 shadow-md shadow-primary/20"
                >
                  {isSubmittingPrivacy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  <span>So‘rovni Yuborish</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
