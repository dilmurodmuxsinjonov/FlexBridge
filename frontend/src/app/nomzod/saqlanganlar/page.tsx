"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bookmark,
  Trash2,
  ExternalLink,
  Briefcase,
  MapPin,
  Calendar,
  AlertCircle,
  Clock,
  CheckCircle2,
  Loader2,
  RefreshCw,
} from "lucide-react";
import {
  fetchMySavedOpportunities,
  deleteSavedOpportunity,
  SavedOpportunityItem,
} from "@/lib/api";

export default function SavedOpportunitiesPage() {
  const [items, setItems] = useState<SavedOpportunityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const loadSaved = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchMySavedOpportunities(1, 50);
      setItems(res.items || []);
    } catch (err: any) {
      if (err.status === 401) {
        setError("Tizimga kirish talab etiladi. Iltimos, profilingizga kiring.");
      } else {
        setError(err.message || "Saqlangan e'lonlarni yuklashda xatolik yuz berdi");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSaved();
  }, []);

  const handleRemove = async (savedId: string, title: string) => {
    try {
      setRemovingId(savedId);
      await deleteSavedOpportunity(savedId);
      setItems((prev) => prev.filter((i) => i.id !== savedId));
      setActionSuccess(`"${title}" muvaffaqiyatli saqlanganlardan olib tashlandi.`);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setError(err.message || "E'lonni o'chirishda xatolik yuz berdi");
    } finally {
      setRemovingId(null);
    }
  };

  const activeCount = items.filter((i) => !i.opportunity.is_closed).length;
  const closedCount = items.filter((i) => i.opportunity.is_closed).length;

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 px-4 py-8 md:px-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.08] pb-6 mb-8">
        <div>
          <div className="flex items-center gap-2 text-primary text-xs font-semibold uppercase tracking-wider mb-1">
            <Bookmark className="w-4 h-4" />
            <span>Nomzod Markazi</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold font-heading text-white">
            Saqlangan Vakansiyalar va E'lonlar
          </h1>
          <p className="text-zinc-400 text-sm mt-1">
            Siz saqlab qo'ygan qiziqarli amaliyot va ish o'rinlari to'plami.
          </p>
        </div>

        <button
          onClick={loadSaved}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-2 text-xs font-medium bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] rounded transition-colors disabled:opacity-50 self-start md:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Yangilash
        </button>
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
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="p-4 rounded bg-[#121214] border border-white/[0.08]">
          <span className="text-xs text-zinc-400 uppercase tracking-wider block">Jami Saqlangan</span>
          <span className="text-2xl font-bold text-white mt-1 block font-mono">{items.length}</span>
        </div>
        <div className="p-4 rounded bg-[#121214] border border-white/[0.08]">
          <span className="text-xs text-zinc-400 uppercase tracking-wider block">Faol E'lonlar</span>
          <span className="text-2xl font-bold text-emerald-400 mt-1 block font-mono">{activeCount}</span>
        </div>
        <div className="p-4 rounded bg-[#121214] border border-white/[0.08]">
          <span className="text-xs text-zinc-400 uppercase tracking-wider block">Yopilgan / Arxiv</span>
          <span className="text-2xl font-bold text-zinc-500 mt-1 block font-mono">{closedCount}</span>
        </div>
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-zinc-400 gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <span className="text-xs">Saqlangan vakansiyalar yuklanmoqda...</span>
        </div>
      ) : items.length === 0 ? (
        <div className="py-16 px-4 rounded bg-[#121214] border border-white/[0.08] text-center max-w-lg mx-auto">
          <div className="w-12 h-12 rounded-full bg-white/[0.04] flex items-center justify-center mx-auto mb-4 text-zinc-500">
            <Bookmark className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-white">Hozircha saqlangan e'lonlar yo'q</h3>
          <p className="text-xs text-zinc-400 mt-1 mb-6">
            Bo'sh ish o'rinlari sahifasidan o'zingizga yoqqan vakansiyalarni saqlab qo'yishingiz mumkin.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded text-xs font-medium transition-colors"
          >
            <Briefcase className="w-3.5 h-3.5" />
            E'lonlarni ko'rish
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => {
            const opp = item.opportunity;
            const isClosed = opp.is_closed;

            return (
              <div
                key={item.id}
                className={`p-5 rounded bg-[#121214] border transition-colors ${
                  isClosed ? "border-white/[0.04] opacity-75" : "border-white/[0.08] hover:border-white/[0.16]"
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-base font-semibold text-white">
                        {opp.title || "Vakansiya nomi ko'rsatilmagan"}
                      </h2>
                      {isClosed ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                          Yopilgan
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          Faol
                        </span>
                      )}
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-white/[0.04] text-zinc-400 border border-white/[0.08]">
                        {opp.work_mode || "Gibrid"}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-white/[0.04] text-zinc-400 border border-white/[0.08]">
                        {opp.contract_type || "LABOR_PART_TIME"}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-400">
                      <span className="flex items-center gap-1.5">
                        <Briefcase className="w-3.5 h-3.5 text-zinc-500" />
                        Tashkilot ID: <span className="font-mono text-zinc-300">{opp.organization_id ? `${opp.organization_id.slice(0, 8)}...` : "N/A"}</span>
                      </span>
                      {item.created_at && (
                        <span className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-zinc-500" />
                          Saqlangan: {new Date(item.created_at).toLocaleDateString("uz-UZ")}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                    {!isClosed && (
                      <Link
                        href={`/ishlar/${opp.id}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 text-xs font-medium transition-colors"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        Batafsil
                      </Link>
                    )}
                    <button
                      onClick={() => handleRemove(item.id, opp.title || "Vakansiya")}
                      disabled={removingId === item.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-xs font-medium transition-colors disabled:opacity-50"
                    >
                      {removingId === item.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="w-3.5 h-3.5" />
                      )}
                      O'chirish
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
