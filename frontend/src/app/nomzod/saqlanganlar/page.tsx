"use client";

import React, { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import {
  Bookmark,
  BookmarkCheck,
  Trash2,
  ArrowUpRight,
  Building2,
  Briefcase,
  MapPin,
  Calendar,
  Clock,
  AlertTriangle,
  CheckCircle2,
  DollarSign,
} from "lucide-react";
import {
  fetchSavedOpportunities,
  deleteSavedOpportunity,
  SavedOpportunityItem,
} from "@/lib/api";

export default function CandidateSavedOpportunitiesPage() {
  const [items, setItems] = useState<SavedOpportunityItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const loadSaved = async (pageNum: number = 1) => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchSavedOpportunities(pageNum, 20);
      setItems(res.items || []);
      setTotal(res.total || 0);
      setPage(res.page || 1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Saqlangan e'lonlarni yuklashda xatolik";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSaved(1);
  }, []);

  const handleUnsave = (savedId: string, oppTitle?: string) => {
    startTransition(async () => {
      try {
        await deleteSavedOpportunity(savedId);
        setItems((prev) => prev.filter((item) => item.id !== savedId));
        setTotal((prev) => Math.max(0, prev - 1));
        setActionSuccess(`"${oppTitle || 'E\'lon'}" saqlanganlar ro'yxatidan o'chirildi.`);
        setTimeout(() => setActionSuccess(null), 3000);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "E'lonni o'chirishda xatolik";
        setError(msg);
      }
    });
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 p-6 md:p-10 font-sans">
      {/* Sub-Navigation */}
      <div className="max-w-6xl mx-auto mb-8 flex items-center space-x-2 border-b border-zinc-800 pb-4 overflow-x-auto text-sm">
        <Link
          href="/nomzod"
          className="px-3 py-1.5 rounded-lg border border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors whitespace-nowrap"
        >
          Mening Profilim
        </Link>
        <Link
          href="/nomzod/arizalar"
          className="px-3 py-1.5 rounded-lg border border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors whitespace-nowrap"
        >
          Mening Arizalarim
        </Link>
        <Link
          href="/nomzod/shartnomalar"
          className="px-3 py-1.5 rounded-lg border border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors whitespace-nowrap"
        >
          Shartnomalar & Amaliyot
        </Link>
        <Link
          href="/nomzod/kundalik"
          className="px-3 py-1.5 rounded-lg border border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors whitespace-nowrap"
        >
          Amaliyot Kundaligi
        </Link>
        <Link
          href="/nomzod/baholar"
          className="px-3 py-1.5 rounded-lg border border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors whitespace-nowrap"
        >
          Baholar & Sharhlar
        </Link>
        <Link
          href="/nomzod/saqlanganlar"
          className="px-3 py-1.5 rounded-lg border border-zinc-700 bg-zinc-800/80 text-zinc-100 font-medium transition-colors whitespace-nowrap"
        >
          Saqlangan E&apos;lonlar
        </Link>
      </div>

      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-100 flex items-center gap-2">
              <Bookmark className="w-6 h-6 text-amber-400" />
              Saqlangan Vakansiyalar & Amaliyot E&apos;lonlari
            </h1>
            <p className="text-sm text-zinc-400 mt-1">
              Keyinroq ko&apos;rib chiqish va ariza topshirish uchun belgilangan imkoniyatlar (API-037 / API-004 / API-038)
            </p>
          </div>
          <button
            onClick={() => loadSaved(page)}
            disabled={loading}
            className="px-4 py-2 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition flex items-center gap-2 self-start md:self-auto"
          >
            <Clock className="w-4 h-4 text-zinc-400" />
            Yangilash
          </button>
        </div>

        {actionSuccess && (
          <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/50 text-emerald-200 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-200 text-sm flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Xatolik yuz berdi</p>
              <p className="text-xs text-red-300 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Counter Summary */}
        <div className="flex items-center justify-between text-xs text-zinc-400 px-1">
          <span>Jami saqlangan e&apos;lonlar: <strong className="text-zinc-200 tabular-nums">{total}</strong> ta</span>
          <span>Sahifa: {page}</span>
        </div>

        {/* Saved List */}
        {loading && items.length === 0 ? (
          <div className="p-12 rounded-2xl bg-[#121214] border border-zinc-800 text-center text-zinc-400 text-sm">
            Yuklanmoqda...
          </div>
        ) : items.length === 0 ? (
          <div className="p-12 rounded-2xl bg-[#121214] border border-zinc-800 text-center space-y-3">
            <BookmarkCheck className="w-10 h-10 text-zinc-600 mx-auto" />
            <h3 className="text-zinc-300 font-medium text-sm">Saqlangan e&apos;lonlar mavjud emas</h3>
            <p className="text-xs text-zinc-500 max-w-md mx-auto">
              Sizga yoqqan vakansiya yoki amaliyot o&apos;rnini keyinroq topshirish uchun saqlab qo&apos;yishingiz mumkin.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {items.map((item) => {
              const opp = item.opportunity;
              const isClosed = opp.is_closed || opp.status === "CLOSED" || opp.status === "ARCHIVED";

              return (
                <div
                  key={item.id}
                  className="p-5 rounded-2xl bg-[#121214] border border-zinc-800 hover:border-zinc-700 shadow-md transition flex flex-col justify-between gap-4"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-zinc-800 text-zinc-300 border border-zinc-700/60">
                          {opp.kind === "INTERNSHIP" ? "Amaliyot" : "Yarim Stavka (Part-time)"}
                        </span>
                        <h3 className="font-semibold text-zinc-100 text-sm mt-2 line-clamp-1">
                          {opp.title || "Nomlanmagan e'lon"}
                        </h3>
                      </div>

                      {/* Status Badge */}
                      {isClosed ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-950/50 text-red-400 border border-red-800/40">
                          Yopilgan
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950/50 text-emerald-400 border border-emerald-800/40">
                          Faol
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs text-zinc-400 pt-1">
                      <div className="flex items-center gap-1.5">
                        <Briefcase className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                        <span className="truncate">{opp.work_mode || "Aniqlanmagan"}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <DollarSign className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                        <span>{opp.is_paid ? "To'lanadigan" : "To'lovsiz"}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                        <span>Saqlangan: {item.created_at ? new Date(item.created_at).toLocaleDateString() : "—"}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                        <span className="truncate font-mono">{opp.organization_id ? opp.organization_id.slice(0, 8) : "Tashkilot"}</span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="pt-3 border-t border-zinc-800/80 flex items-center justify-between gap-3">
                    <button
                      onClick={() => handleUnsave(item.id, opp.title)}
                      disabled={isPending}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-400 hover:text-red-400 hover:bg-red-950/20 transition flex items-center gap-1.5"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      O&apos;chirish
                    </button>

                    {!isClosed ? (
                      <Link
                        href={`/nomzod/arizalar`}
                        className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition flex items-center gap-1.5 shadow-sm"
                      >
                        Ariza topshirish
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    ) : (
                      <span className="text-[11px] text-zinc-500 italic">E&apos;lon muddati tugagan</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
