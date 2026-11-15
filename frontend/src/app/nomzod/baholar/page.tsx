"use client";

import React, { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import {
  Star,
  ShieldCheck,
  Scale,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Lock,
  MessageSquare,
  Send,
  FileText,
  ChevronRight,
  X,
  Building2,
  Award,
  HelpCircle,
} from "lucide-react";
import {
  fetchCandidateRatings,
  submitEngagementRating,
  submitRatingAppeal,
  CandidateRatingsResponse,
  RubricVersion,
  EligibleRelationItem,
  ReceivedRatingItem,
  GivenRatingItem,
} from "@/lib/api";

export default function CandidateRatingsPage() {
  const [data, setData] = useState<CandidateRatingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  // Active view tab: "received" | "given" | "evaluate"
  const [activeTab, setActiveTab] = useState<"received" | "given" | "evaluate">("received");

  // Rating submission form state
  const [selectedRelation, setSelectedRelation] = useState<EligibleRelationItem | null>(null);
  const [selectedRubric, setSelectedRubric] = useState<RubricVersion | null>(null);
  const [criterionScores, setCriterionScores] = useState<Record<string, number>>({});
  const [ratingComment, setRatingComment] = useState("");
  const [submitSuccessMsg, setSubmitSuccessMsg] = useState<string | null>(null);
  const [submitErrorMsg, setSubmitErrorMsg] = useState<string | null>(null);

  // Appeal modal state
  const [appealTarget, setAppealTarget] = useState<ReceivedRatingItem | null>(null);
  const [appealCategory, setAppealCategory] = useState("FACTUAL_DISPUTE");
  const [appealReason, setAppealReason] = useState("");
  const [appealEvidence, setAppealEvidence] = useState("");
  const [appealSuccessMsg, setAppealSuccessMsg] = useState<string | null>(null);
  const [appealErrorMsg, setAppealErrorMsg] = useState<string | null>(null);

  const loadRatings = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchCandidateRatings();
      setData(res);
      if (res.available_rubrics && res.available_rubrics.length > 0) {
        setSelectedRubric(res.available_rubrics[0]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Baholarni yuklashda xatolik";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRatings();
  }, []);

  // Handle score change for a criterion
  const handleScoreChange = (criterionId: string, score: number) => {
    setCriterionScores((prev) => ({
      ...prev,
      [criterionId]: score,
    }));
  };

  // Submit mutual engagement rating (API-047)
  const handleSubmitRating = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRelation) {
      setSubmitErrorMsg("Iltimos, baholanadigan yakunlangan munosabatni tanlang.");
      return;
    }
    if (!selectedRubric) {
      setSubmitErrorMsg("Baholash rubrikasi topilmadi.");
      return;
    }

    const missingRequired = selectedRubric.criteria
      .filter((c) => c.required)
      .some((c) => !criterionScores[c.id]);

    if (missingRequired) {
      setSubmitErrorMsg("Barcha majburiy mezonlar bo'yicha ball qo'yilishi shart (1 dan 5 gacha).");
      return;
    }

    setSubmitErrorMsg(null);
    setSubmitSuccessMsg(null);

    const scoresPayload = Object.entries(criterionScores).map(([cid, sc]) => ({
      criterion_id: cid,
      score: sc,
    }));

    startTransition(async () => {
      try {
        await submitEngagementRating(selectedRelation.relation_id, {
          rubric_id: selectedRubric.id,
          scores: scoresPayload,
          comment: ratingComment.trim() || undefined,
          idempotency_key: `rate-${selectedRelation.relation_id}-${Date.now()}`,
        });
        setSubmitSuccessMsg("Baholash muvaffaqiyatli yuborildi! AC-024 bo'yicha 14 kunlik Double-Blind himoya davriga kiritildi.");
        setCriterionScores({});
        setRatingComment("");
        await loadRatings();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Baholashni yuborishda xatolik";
        setSubmitErrorMsg(msg);
      }
    });
  };

  // Submit appeal (API-058)
  const handleSubmitAppeal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!appealTarget) return;

    if (appealReason.trim().length < 10) {
      setAppealErrorMsg("E'tiroz sababi kamida 10 ta belgidan iborat bo'lishi shart.");
      return;
    }

    setAppealErrorMsg(null);
    setAppealSuccessMsg(null);

    startTransition(async () => {
      try {
        await submitRatingAppeal(appealTarget.id, {
          category: appealCategory,
          reason: appealReason.trim(),
          evidence_notes: appealEvidence.trim() || undefined,
        });
        setAppealSuccessMsg("E'tiroz qabul qilindi va mustaqil ko'rib chiqish navbatiga qo'shildi (AC-025).");
        setTimeout(() => {
          setAppealTarget(null);
          setAppealReason("");
          setAppealEvidence("");
          setAppealSuccessMsg(null);
        }, 2000);
        await loadRatings();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "E'tirozni yuborishda xatolik";
        setAppealErrorMsg(msg);
      }
    });
  };

  const agg = data?.aggregate;

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
          className="px-3 py-1.5 rounded-lg border border-zinc-700 bg-zinc-800/80 text-zinc-100 font-medium transition-colors whitespace-nowrap"
        >
          Baholar & Sharhlar
        </Link>
        <Link
          href="/nomzod/saqlanganlar"
          className="px-3 py-1.5 rounded-lg border border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors whitespace-nowrap"
        >
          Saqlangan E&apos;lonlar
        </Link>
      </div>

      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-100 flex items-center gap-2">
              <Award className="w-6 h-6 text-amber-400" />
              Baholar, Ko&apos;rib Chiqish & E&apos;tirozlar Markazi
            </h1>
            <p className="text-sm text-zinc-400 mt-1">
              Bilateral Double-Blind himoyasi (AC-024) va Rubrika mezonlari asosida mustaqil baholash tizimi (API-057 / API-047 / API-058)
            </p>
          </div>
          <button
            onClick={loadRatings}
            disabled={loading}
            className="px-4 py-2 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition flex items-center gap-2 self-start md:self-auto"
          >
            <Clock className="w-4 h-4 text-zinc-400" />
            Yangilash
          </button>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-200 text-sm flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Xatolik yuz berdi</p>
              <p className="text-xs text-red-300 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Section 1: Candidate Aggregated Score & Privacy Badge (AC-023) */}
        {agg && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 p-6 rounded-2xl bg-[#121214] border border-zinc-800 shadow-xl relative overflow-hidden">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                    Umumiy Baholash Ko&apos;rsatkichi
                  </span>
                  <div className="flex items-baseline gap-3 mt-2">
                    {agg.score !== null ? (
                      <>
                        <span className="text-4xl font-bold tracking-tight text-zinc-100 tabular-nums">
                          {agg.score.toFixed(1)}
                        </span>
                        <span className="text-sm text-zinc-500 font-medium">/ 5.0</span>
                      </>
                    ) : (
                      <span className="text-2xl font-bold tracking-tight text-zinc-400">
                        Baholanmagan
                      </span>
                    )}
                  </div>
                </div>

                {/* Score Status Badge */}
                <div>
                  {agg.score_status === "PUBLISHED" && (
                    <span className="px-3 py-1 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/50 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Tasdiqlangan (Published)
                    </span>
                  )}
                  {agg.score_status === "WITHHELD_INSUFFICIENT_SAMPLE" && (
                    <span className="px-3 py-1 rounded-full text-xs font-medium bg-amber-950/60 text-amber-400 border border-amber-800/50 flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5" /> Yashirilgan (n &lt; 5)
                    </span>
                  )}
                  {agg.score_status === "UNRATED" && (
                    <span className="px-3 py-1 rounded-full text-xs font-medium bg-zinc-800 text-zinc-400 border border-zinc-700 flex items-center gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5" /> Yangi Profil (Unrated)
                    </span>
                  )}
                </div>
              </div>

              {/* Explanatory Note (AC-023) */}
              <p className="text-xs text-zinc-400 mt-4 leading-relaxed bg-black/30 p-3.5 rounded-xl border border-zinc-800/60">
                {agg.explanation}
              </p>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-6 pt-5 border-t border-zinc-800/70 text-xs">
                <div>
                  <span className="text-zinc-500">Baholashlar soni (n):</span>
                  <p className="font-semibold text-zinc-200 mt-0.5 tabular-nums">
                    {agg.sample_size} ta mustaqil baho
                  </p>
                </div>
                <div>
                  <span className="text-zinc-500">Minimal chegara:</span>
                  <p className="font-semibold text-zinc-200 mt-0.5 tabular-nums">
                    n &ge; 5 (AC-023 Maxfiylik)
                  </p>
                </div>
                <div>
                  <span className="text-zinc-500">So&apos;nggi hisoblash:</span>
                  <p className="font-semibold text-zinc-200 mt-0.5 tabular-nums">
                    {agg.computed_at ? new Date(agg.computed_at).toLocaleDateString() : "Hali hisoblanmagan"}
                  </p>
                </div>
              </div>
            </div>

            {/* Double-Blind Protection Card (AC-024) */}
            <div className="p-6 rounded-2xl bg-[#121214] border border-zinc-800 shadow-xl flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-zinc-300 font-semibold text-sm">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  Bilateral Double-Blind (AC-024)
                </div>
                <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
                  Ish beruvchi va nomzod baholashlari bir-biriga ta&apos;sir qilmasligi uchun 14 kunlik maxfiylik oynasi qo&apos;llaniladi.
                </p>
                <div className="mt-4 space-y-2 text-xs">
                  <div className="flex items-center gap-2 text-zinc-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <span>Ikkala tomon topshirmaguncha baholar yopiq qoladi</span>
                  </div>
                  <div className="flex items-center gap-2 text-zinc-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <span>Qasoskorlik (retaliation) xavfi bartaraf etiladi</span>
                  </div>
                  <div className="flex items-center gap-2 text-zinc-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <span>14 kundan so&apos;ng baholar avtomatik e&apos;lon qilinadi</span>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-zinc-800 text-[11px] text-zinc-500">
                E&apos;tiroz bildirish oynasi: nashr etilgan kundan boshlab 14 kun (AC-025).
              </div>
            </div>
          </div>
        )}

        {/* Section 2: Tab Navigation for Reviews and Mutual Evaluation */}
        <div className="flex items-center space-x-2 border-b border-zinc-800 pb-3">
          <button
            onClick={() => setActiveTab("received")}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-colors flex items-center gap-2 ${
              activeTab === "received"
                ? "bg-zinc-800 text-zinc-100 border border-zinc-700 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
            }`}
          >
            <Star className="w-3.5 h-3.5 text-amber-400" />
            Menga Berilgan Baholar ({data?.submissions_received.length || 0})
          </button>
          <button
            onClick={() => setActiveTab("given")}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-colors flex items-center gap-2 ${
              activeTab === "given"
                ? "bg-zinc-800 text-zinc-100 border border-zinc-700 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
            }`}
          >
            <Send className="w-3.5 h-3.5 text-blue-400" />
            Men Bergan Baholar ({data?.submissions_given.length || 0})
          </button>
          <button
            onClick={() => setActiveTab("evaluate")}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-colors flex items-center gap-2 ${
              activeTab === "evaluate"
                ? "bg-zinc-800 text-zinc-100 border border-zinc-700 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
            }`}
          >
            <Scale className="w-3.5 h-3.5 text-emerald-400" />
            Ish Beruvchini Baholash ({data?.eligible_relations.length || 0})
          </button>
        </div>

        {/* TAB 1: Received Ratings */}
        {activeTab === "received" && (
          <div className="space-y-4">
            {data?.submissions_received.length === 0 ? (
              <div className="p-8 rounded-2xl bg-[#121214] border border-zinc-800 text-center text-zinc-400 text-sm">
                Sizga hali hech kim baho qoldirmagan.
              </div>
            ) : (
              data?.submissions_received.map((sub) => (
                <div
                  key={sub.id}
                  className="p-5 rounded-2xl bg-[#121214] border border-zinc-800 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      {sub.blind_window_active ? (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-amber-950/60 text-amber-400 border border-amber-800/50 flex items-center gap-1">
                          <Lock className="w-3 h-3" /> Double-Blind Himoya Davri (AC-024)
                        </span>
                      ) : (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/50 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Nashr etilgan (Published)
                        </span>
                      )}
                      <span className="text-xs text-zinc-500 font-mono">ID: {sub.id.slice(0, 8)}...</span>
                    </div>

                    {sub.blind_window_active ? (
                      <p className="text-xs text-zinc-400 leading-relaxed max-w-xl">
                        {sub.message || "14-kunlik himoya davrida baholovchi shaxsi va sharh tafsilotlari maxfiy saqlanadi."}
                      </p>
                    ) : (
                      <p className="text-xs text-zinc-300 leading-relaxed max-w-xl italic">
                        &ldquo;{sub.comment || "Izoh bildirilmagan"}&rdquo;
                      </p>
                    )}

                    <div className="text-[11px] text-zinc-500 flex items-center gap-4">
                      {sub.publish_after && (
                        <span>
                          Nashr muddati: {new Date(sub.publish_after).toLocaleDateString()}
                        </span>
                      )}
                      {sub.submitted_at && (
                        <span>
                          Yuborilgan sana: {new Date(sub.submitted_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {!sub.blind_window_active && sub.status === "PUBLISHED" && (
                      <button
                        onClick={() => setAppealTarget(sub)}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-950/40 hover:bg-red-900/50 text-red-300 border border-red-800/50 transition flex items-center gap-1.5"
                      >
                        <Scale className="w-3.5 h-3.5 text-red-400" />
                        E&apos;tiroz bildirish (AC-025)
                      </button>
                    )}
                    {sub.status === "UNDER_APPEAL" && (
                      <span className="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-950/50 text-amber-300 border border-amber-800/50">
                        E&apos;tiroz ko&apos;rib chiqilmoqda
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 2: Given Ratings */}
        {activeTab === "given" && (
          <div className="space-y-4">
            {data?.submissions_given.length === 0 ? (
              <div className="p-8 rounded-2xl bg-[#121214] border border-zinc-800 text-center text-zinc-400 text-sm">
                Siz hali hech bir tashkilot yoki ish munosabatini baholamadingiz.
              </div>
            ) : (
              data?.submissions_given.map((sub) => (
                <div
                  key={sub.id}
                  className="p-5 rounded-2xl bg-[#121214] border border-zinc-800 shadow-md space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-blue-950/60 text-blue-400 border border-blue-800/50">
                      Holat: {sub.status}
                    </span>
                    <span className="text-xs text-zinc-500 font-mono">
                      {sub.submitted_at ? new Date(sub.submitted_at).toLocaleDateString() : ""}
                    </span>
                  </div>
                  {sub.comment && (
                    <p className="text-xs text-zinc-300 italic">&ldquo;{sub.comment}&rdquo;</p>
                  )}
                  <div className="text-[11px] text-zinc-500">
                    <span>Bog&apos;liq munosabat ID: {sub.engagement_id || sub.placement_id || "—"}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 3: Evaluate Completed Relations (API-047) */}
        {activeTab === "evaluate" && (
          <div className="space-y-6">
            {data?.eligible_relations.length === 0 ? (
              <div className="p-8 rounded-2xl bg-[#121214] border border-zinc-800 text-center text-zinc-400 text-sm">
                Baholash uchun mos yakunlangan munosabatlar mavjud emas (AC-022 bo&apos;yicha faqat yakunlangan amaliyot yoki ish munosabatlari baholanadi).
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data?.eligible_relations.map((rel) => (
                  <div
                    key={rel.relation_id}
                    onClick={() => {
                      setSelectedRelation(rel);
                      setCriterionScores({});
                      setSubmitSuccessMsg(null);
                      setSubmitErrorMsg(null);
                    }}
                    className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                      selectedRelation?.relation_id === rel.relation_id
                        ? "bg-zinc-800/70 border-emerald-500 shadow-lg"
                        : "bg-[#121214] border-zinc-800 hover:border-zinc-700"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-zinc-400" />
                        <span className="font-semibold text-zinc-200 text-sm">
                          {rel.relation_type === "PLACEMENT" ? "Amaliyot Munosabati" : "Ish Munosabati"}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-zinc-800 text-zinc-300">
                        {rel.status}
                      </span>
                    </div>

                    <div className="mt-3 text-xs text-zinc-400 space-y-1">
                      <p>Munosabat ID: <span className="font-mono text-zinc-300">{rel.relation_id.slice(0, 12)}...</span></p>
                      {rel.start_date && (
                        <p>Davr: {rel.start_date} &rarr; {rel.end_date || "Hozirga qadar"}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Rubric Evaluation Form */}
            {selectedRelation && selectedRubric && (
              <form
                onSubmit={handleSubmitRating}
                className="p-6 rounded-2xl bg-[#121214] border border-zinc-800 shadow-2xl space-y-6"
              >
                <div>
                  <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                    <Scale className="w-5 h-5 text-emerald-400" />
                    Rubrika Mezonlari Bo&apos;yicha Baholash (API-047)
                  </h3>
                  <p className="text-xs text-zinc-400 mt-1">
                    Rubrika oilasi: <span className="font-semibold text-zinc-300">{selectedRubric.family} (v{selectedRubric.version})</span> | 1 dan 5 gacha ball bering.
                  </p>
                </div>

                {submitSuccessMsg && (
                  <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/50 text-emerald-200 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>{submitSuccessMsg}</span>
                  </div>
                )}

                {submitErrorMsg && (
                  <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-200 text-xs flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                    <span>{submitErrorMsg}</span>
                  </div>
                )}

                {/* Criteria Scoring */}
                <div className="space-y-4">
                  {selectedRubric.criteria.map((crit) => (
                    <div
                      key={crit.id}
                      className="p-4 rounded-xl bg-black/30 border border-zinc-800 flex flex-col md:flex-row md:items-center justify-between gap-3"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-zinc-200 text-xs">
                            {crit.title}
                          </span>
                          {crit.required && (
                            <span className="text-[10px] text-red-400 font-medium">*majburiy</span>
                          )}
                        </div>
                        <span className="text-[11px] text-zinc-500 font-mono mt-0.5 block">
                          Kod: {crit.code} | Salmoq: {crit.weight}x
                        </span>
                      </div>

                      {/* 1..5 Star / Numeric Selection */}
                      <div className="flex items-center gap-1.5">
                        {[1, 2, 3, 4, 5].map((star) => {
                          const currentVal = criterionScores[crit.id] || 0;
                          return (
                            <button
                              key={star}
                              type="button"
                              onClick={() => handleScoreChange(crit.id, star)}
                              className={`w-9 h-9 rounded-lg font-semibold text-xs transition flex items-center justify-center ${
                                currentVal >= star
                                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/50 shadow-sm"
                                  : "bg-zinc-800/60 text-zinc-400 hover:bg-zinc-800 border border-zinc-700/60"
                              }`}
                            >
                              <Star className={`w-3.5 h-3.5 ${currentVal >= star ? "fill-amber-400 text-amber-400" : ""}`} />
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Optional Comment */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-300 flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-zinc-400" />
                    Qo&apos;shimcha Konstruktiv Sharh (ixtiyoriy, max 2000 belgi)
                  </label>
                  <textarea
                    value={ratingComment}
                    onChange={(e) => setRatingComment(e.target.value)}
                    rows={3}
                    maxLength={2000}
                    placeholder="Ish muhiti, ustozlik ko'magi va munosabat bo'yicha fikringizni bildiring..."
                    className="w-full bg-black/40 border border-zinc-800 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isPending}
                  className="w-full md:w-auto px-6 py-2.5 rounded-xl font-medium text-xs bg-emerald-600 hover:bg-emerald-500 text-white transition flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
                >
                  <Send className="w-4 h-4" />
                  {isPending ? "Yuborilmoqda..." : "Baholashni Tasdiqlash & Yuborish (API-047)"}
                </button>
              </form>
            )}
          </div>
        )}
      </div>

      {/* Appeal Modal (API-058 / AC-025) */}
      {appealTarget && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#121214] border border-zinc-800 rounded-2xl p-6 max-w-lg w-full space-y-5 shadow-2xl relative">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                <Scale className="w-4 h-4 text-red-400" />
                Bahoga E&apos;tiroz Bildirish (API-058 / AC-025)
              </h3>
              <button
                onClick={() => setAppealTarget(null)}
                className="text-zinc-500 hover:text-zinc-300 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {appealSuccessMsg && (
              <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/50 text-emerald-200 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{appealSuccessMsg}</span>
              </div>
            )}

            {appealErrorMsg && (
              <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/50 text-red-200 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                <span>{appealErrorMsg}</span>
              </div>
            )}

            <form onSubmit={handleSubmitAppeal} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">
                  E&apos;tiroz Toifasi
                </label>
                <select
                  value={appealCategory}
                  onChange={(e) => setAppealCategory(e.target.value)}
                  className="w-full bg-black/40 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600"
                >
                  <option value="FACTUAL_DISPUTE">Faktik Noaniqlik (Factual Dispute)</option>
                  <option value="RETALIATION">Qasoskor Baho (Retaliation)</option>
                  <option value="HARASSMENT">Kamsitish / Haqorat (Harassment)</option>
                  <option value="OTHER">Boshqa Asos</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">
                  E&apos;tiroz Sababi (kamida 10 ta belgi) *
                </label>
                <textarea
                  required
                  minLength={10}
                  maxLength={4000}
                  value={appealReason}
                  onChange={(e) => setAppealReason(e.target.value)}
                  rows={4}
                  placeholder="Baho nima uchun adolatsiz yoki faktlarga zid ekanligini batafsil yoritib bering..."
                  className="w-full bg-black/40 border border-zinc-800 rounded-xl px-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">
                  Dalillar / Yozishmalar Havolasi (ixtiyoriy)
                </label>
                <input
                  type="text"
                  maxLength={4000}
                  value={appealEvidence}
                  onChange={(e) => setAppealEvidence(e.target.value)}
                  placeholder="Masalan: Kundalik loglari yoki buyruq hujjatlari raqami"
                  className="w-full bg-black/40 border border-zinc-800 rounded-xl px-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setAppealTarget(null)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-zinc-400 hover:text-zinc-200 bg-zinc-900 border border-zinc-800"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isPending}
                  className="px-4 py-2 rounded-xl text-xs font-medium bg-red-600 hover:bg-red-500 text-white disabled:opacity-50 flex items-center gap-1.5 shadow-md"
                >
                  <Scale className="w-3.5 h-3.5" />
                  {isPending ? "Yuborilmoqda..." : "E'tirozni Yuborish (API-058)"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
