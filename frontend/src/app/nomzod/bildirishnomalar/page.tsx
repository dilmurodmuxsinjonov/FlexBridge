"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bell,
  CheckCircle2,
  AlertCircle,
  Clock,
  Eye,
  Check,
  RefreshCw,
  Loader2,
  Filter,
  FileText,
  Calendar,
  Briefcase,
  HelpCircle,
} from "lucide-react";
import {
  fetchMyNotifications,
  markNotificationRead,
  NotificationItem,
} from "@/lib/api";

export default function NotificationsInboxPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [unreadOnly, setUnreadOnly] = useState<boolean>(false);
  const [markingId, setMarkingId] = useState<string | null>(null);

  const loadNotifications = async (isUnread: boolean) => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchMyNotifications(isUnread, 50);
      setItems(res.items || []);
    } catch (caught: unknown) {
      const err = caught as Error & { status?: number };
      if (err.status === 401) {
        setError("Tizimga kirish talab etiladi. Iltimos, profilingizga kiring.");
      } else {
        setError(err.message || "Bildirishnomalarni yuklashda xatolik yuz berdi");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch on mount/dependency change; loader resets its loading/error flags
    loadNotifications(unreadOnly);
  }, [unreadOnly]);

  const handleMarkRead = async (id: string) => {
    try {
      setMarkingId(id);
      await markNotificationRead(id);
      setItems((prev) =>
        prev.map((item) =>
          item.id === id ? { ...item, is_read: true, read_at: new Date().toISOString() } : item
        )
      );
      setActionSuccess("Xabar o'qilgan deb belgilandi.");
      setTimeout(() => setActionSuccess(null), 3000);
    } catch (caught: unknown) {
      const err = caught as Error & { status?: number };
      setError(err.message || "Xabarni yangilashda xatolik yuz berdi");
    } finally {
      setMarkingId(null);
    }
  };

  const unreadCount = items.filter((i) => !i.is_read).length;

  return (
    <div className="w-full text-zinc-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.08] pb-6 mb-8">
        <div>
          <div className="flex items-center gap-2 text-primary text-xs font-semibold uppercase tracking-wider mb-1">
            <Bell className="w-4 h-4" />
            <span>Xabarnomalar Markazi</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold font-heading text-white">
            Bildirishnomalar va Xabarlar
          </h1>
          <p className="text-zinc-400 text-sm mt-1">
            Platforma yangiliklari, suhbatlar, arizalar va amaliyot bo&apos;yicha xabarlar qutisi.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto">
          {/* Unread Filter Toggle */}
          <div className="flex items-center p-0.5 rounded bg-white/[0.04] border border-white/[0.08] text-xs">
            <button
              onClick={() => setUnreadOnly(false)}
              className={`px-3 py-1.5 rounded transition-colors ${
                !unreadOnly
                  ? "bg-primary text-white font-medium shadow-sm"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              Barchasi
            </button>
            <button
              onClick={() => setUnreadOnly(true)}
              className={`px-3 py-1.5 rounded transition-colors ${
                unreadOnly
                  ? "bg-primary text-white font-medium shadow-sm"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              Faqat o&apos;qilmagan
            </button>
          </div>

          <button
            onClick={() => loadNotifications(unreadOnly)}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3 py-2 text-xs font-medium bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] rounded transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Yangilash
          </button>
        </div>
      </div>

      {/* Notification Banners */}
      {actionSuccess && (
        <div className="mb-6 p-4 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-3">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-3">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Telemetry Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <div className="p-4 rounded bg-[#121214] border border-white/[0.08]">
          <span className="text-xs text-zinc-400 uppercase tracking-wider block">Jami Xabarlar</span>
          <span className="text-2xl font-bold text-white mt-1 block font-mono">{items.length}</span>
        </div>
        <div className="p-4 rounded bg-[#121214] border border-white/[0.08]">
          <span className="text-xs text-zinc-400 uppercase tracking-wider block">O&apos;qilmagan Xabarlar</span>
          <span className="text-2xl font-bold text-amber-400 mt-1 block font-mono">{unreadCount}</span>
        </div>
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-zinc-400 gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <span className="text-xs">Bildirishnomalar yuklanmoqda...</span>
        </div>
      ) : items.length === 0 ? (
        <div className="py-16 px-4 rounded bg-[#121214] border border-white/[0.08] text-center max-w-lg mx-auto">
          <div className="w-12 h-12 rounded-full bg-white/[0.04] flex items-center justify-center mx-auto mb-4 text-zinc-500">
            <Bell className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-white">Hozircha xabarlar yo&apos;q</h3>
          <p className="text-xs text-zinc-400 mt-1">
            {unreadOnly
              ? "Barcha bildirishnomalar o'qilgan. Barcha xabarlarni ko'rish uchun filtrni o'zgartiring."
              : "Yangi bildirishnomalar kelganda ular shu yerda ko'rinadi."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const isUnread = !item.is_read;

            return (
              <div
                key={item.id}
                className={`p-4 rounded bg-[#121214] border transition-colors ${
                  isUnread
                    ? "border-primary/40 bg-primary/[0.02]"
                    : "border-white/[0.08] hover:border-white/[0.16]"
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold font-mono bg-white/[0.06] text-zinc-300 border border-white/[0.08]">
                        {item.template_code}
                      </span>

                      {isUnread ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          O&apos;qilmagan
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-white/[0.04] text-zinc-500 border border-white/[0.08]">
                          O&apos;qilgan
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-400">
                      {item.created_at && (
                        <span className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-zinc-500" />
                          {new Date(item.created_at).toLocaleString("uz-UZ")}
                        </span>
                      )}

                      {item.application_id && (
                        <Link
                          href="/nomzod/arizalar"
                          className="flex items-center gap-1 text-primary hover:underline"
                        >
                          <FileText className="w-3 h-3" />
                          Ariza bo&apos;yicha
                        </Link>
                      )}

                      {item.placement_id && (
                        <Link
                          href="/nomzod/kundalik"
                          className="flex items-center gap-1 text-primary hover:underline"
                        >
                          <Calendar className="w-3 h-3" />
                          Amaliyot kundaligi
                        </Link>
                      )}

                      {item.ticket_id && (
                        <Link
                          href="/nomzod/yordam"
                          className="flex items-center gap-1 text-primary hover:underline"
                        >
                          <HelpCircle className="w-3 h-3" />
                          Yordam tiketi
                        </Link>
                      )}
                    </div>
                  </div>

                  {isUnread && (
                    <button
                      onClick={() => handleMarkRead(item.id)}
                      disabled={markingId === item.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 text-xs font-medium transition-colors shrink-0 self-end md:self-center disabled:opacity-50"
                    >
                      {markingId === item.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Check className="w-3.5 h-3.5" />
                      )}
                      O&apos;qilgan deb belgilash
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
