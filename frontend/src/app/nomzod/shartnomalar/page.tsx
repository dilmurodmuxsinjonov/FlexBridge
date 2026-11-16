"use client";

import React, { useEffect, useEffectEvent, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Briefcase,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Calendar,
  Clock,
  FileText,
  ChevronRight,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  Search,
  Check,
  Building2,
  BookOpen,
} from "lucide-react";
import {
  fetchAuthMe,
  AuthUser,
  fetchCandidatePlacementsList,
  fetchPlacementPlanDetail,
  acceptCandidatePlacementTerms,
  fetchCandidateEngagement,
  submitEngagementConfirmation,
  CandidatePlacementItem,
  PlacementPlanDetail,
  JobEngagementDetail,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";

function ShartnomalarHubContent() {
  const searchParams = useSearchParams();
  const initialEngagementId = searchParams.get("engagement_id") || "";

  // Auth State
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Top-Level Tabs: "PLACEMENTS" (Amaliyot) vs "ENGAGEMENTS" (Ish Munosabatlari)
  const [activeTab, setActiveTab] = useState<"PLACEMENTS" | "ENGAGEMENTS">(
    initialEngagementId ? "ENGAGEMENTS" : "PLACEMENTS"
  );

  // --- PLACEMENTS TAB STATE ---
  const [placements, setPlacements] = useState<CandidatePlacementItem[]>([]);
  const [isLoadingPlacements, setIsLoadingPlacements] = useState(false);
  const [placementsError, setPlacementsError] = useState<string | null>(null);

  // Placement Plan Modal
  const [selectedPlacementId, setSelectedPlacementId] = useState<string | null>(null);
  const [placementPlan, setPlacementPlan] = useState<PlacementPlanDetail | null>(null);
  const [isLoadingPlan, setIsLoadingPlan] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [isAcceptingTerms, setIsAcceptingTerms] = useState(false);
  const [acceptTermsSuccess, setAcceptTermsSuccess] = useState<string | null>(null);

  // --- ENGAGEMENTS TAB STATE ---
  const [engagementIdInput, setEngagementIdInput] = useState(initialEngagementId);
  const [activeEngagement, setActiveEngagement] = useState<JobEngagementDetail | null>(null);
  const [isLoadingEngagement, setIsLoadingEngagement] = useState(false);
  const [engagementError, setEngagementError] = useState<string | null>(null);
  const [isSubmittingConfirmation, setIsSubmittingConfirmation] = useState(false);
  const [confirmationFeedback, setConfirmationFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Check Auth on Mount
  useEffect(() => {
    async function checkAuth() {
      try {
        const user = await fetchAuthMe();
        setCurrentUser(user);
      } catch {
        setCurrentUser(null);
      } finally {
        setIsAuthLoading(false);
      }
    }
    checkAuth();
  }, []);

  // Load Placements when user is authenticated and tab is PLACEMENTS
  useEffect(() => {
    if (currentUser && activeTab === "PLACEMENTS") {
      loadPlacements();
    }
  }, [currentUser, activeTab]);

  // Load Initial Engagement if query param provided
  const onInitialEngagement = useEffectEvent((engagementId: string) => {
    loadEngagement(engagementId);
  });
  useEffect(() => {
    if (currentUser && initialEngagementId) {
      onInitialEngagement(initialEngagementId);
    }
  }, [currentUser, initialEngagementId]);

  async function loadPlacements() {
    setIsLoadingPlacements(true);
    setPlacementsError(null);
    try {
      const res = await fetchCandidatePlacementsList(50);
      setPlacements(res.items || []);
    } catch (err: unknown) {
      setPlacementsError(
        err instanceof Error ? err.message : "Amaliyotlar ro'yxatini yuklashda xatolik yuz berdi"
      );
    } finally {
      setIsLoadingPlacements(false);
    }
  }

  async function handleOpenPlanModal(placementId: string) {
    setSelectedPlacementId(placementId);
    setPlacementPlan(null);
    setPlanError(null);
    setAcceptTermsSuccess(null);
    setIsLoadingPlan(true);

    try {
      const plan = await fetchPlacementPlanDetail(placementId);
      setPlacementPlan(plan);
    } catch (err: unknown) {
      setPlanError(
        err instanceof Error ? err.message : "Amaliyot rejasini yuklashda xatolik yuz berdi"
      );
    } finally {
      setIsLoadingPlan(false);
    }
  }

  async function handleAcceptTerms() {
    if (!selectedPlacementId || !placementPlan) return;
    setIsAcceptingTerms(true);
    setPlanError(null);
    setAcceptTermsSuccess(null);

    try {
      await acceptCandidatePlacementTerms(selectedPlacementId, {
        terms_id: placementPlan.terms_id,
        version: placementPlan.version,
      });
      setAcceptTermsSuccess("Amaliyot shartlari muvaffaqiyatli qabul qilindi va tasdiqlandi!");
      // Reload placements list to reflect state updates
      loadPlacements();
    } catch (err: unknown) {
      setPlanError(
        err instanceof Error ? err.message : "Shartlarni qabul qilishda xatolik yuz berdi"
      );
    } finally {
      setIsAcceptingTerms(false);
    }
  }

  async function loadEngagement(idToLoad?: string) {
    const id = idToLoad || engagementIdInput.trim();
    if (!id) return;
    setIsLoadingEngagement(true);
    setEngagementError(null);
    setConfirmationFeedback(null);

    try {
      const eng = await fetchCandidateEngagement(id);
      setActiveEngagement(eng);
      setEngagementIdInput(id);
    } catch (err: unknown) {
      setActiveEngagement(null);
      setEngagementError(
        err instanceof Error ? err.message : "Ish munosabati topilmadi yoki yuklashda xatolik yuz berdi"
      );
    } finally {
      setIsLoadingEngagement(false);
    }
  }

  async function handleConfirmEngagement(
    action: "CONFIRM_START" | "CONFIRM_END" | "DISPUTE_START" | "DISPUTE_END"
  ) {
    if (!activeEngagement) return;
    setIsSubmittingConfirmation(true);
    setConfirmationFeedback(null);

    try {
      await submitEngagementConfirmation(activeEngagement.id, { action });
      setConfirmationFeedback({
        type: "success",
        message: `Amal muvaffaqiyatli bajarildi: ${action}`,
      });
      // Refresh engagement
      await loadEngagement(activeEngagement.id);
    } catch (err: unknown) {
      setConfirmationFeedback({
        type: "error",
        message: err instanceof Error ? err.message : "Tasdiqlashda xatolik yuz berdi",
      });
    } finally {
      setIsSubmittingConfirmation(false);
    }
  }

  function getPlacementStatusBadge(status: string) {
    switch (status) {
      case "ACTIVE":
        return { label: "Faol amaliyot", cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" };
      case "PLANNED":
        return { label: "Rejalashtirilgan", cls: "bg-sky-500/10 text-sky-400 border-sky-500/20" };
      case "PENDING_START_CONFIRMATION":
        return { label: "Boshlanish kutilmoqda", cls: "bg-amber-500/10 text-amber-400 border-amber-500/20" };
      case "COMPLETED":
        return { label: "Yakunlangan", cls: "bg-purple-500/10 text-purple-400 border-purple-500/20" };
      case "CANCELLED":
        return { label: "Bekor qilingan", cls: "bg-rose-500/10 text-rose-400 border-rose-500/20" };
      default:
        return { label: status, cls: "bg-zinc-800 text-zinc-400 border-zinc-700" };
    }
  }

  function getEngagementStatusBadge(status: string) {
    switch (status) {
      case "ACTIVE":
        return { label: "Faol ish munosabati", cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" };
      case "PENDING_START_CONFIRMATION":
        return { label: "Boshlanish tasdig'i kutilmoqda", cls: "bg-amber-500/10 text-amber-400 border-amber-500/20" };
      case "COMPLETED":
        return { label: "Yakunlangan", cls: "bg-purple-500/10 text-purple-400 border-purple-500/20" };
      case "DISPUTED":
        return { label: "E'tiroz bildirilgan (Nizoli)", cls: "bg-rose-500/10 text-rose-400 border-rose-500/20" };
      default:
        return { label: status, cls: "bg-zinc-800 text-zinc-400 border-zinc-700" };
    }
  }

  return (
    <main className="w-full flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-sky-500/15 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Link href="/" className="text-xs text-zinc-400 hover:text-primary transition-colors">
              Bosh sahifa
            </Link>
            <ChevronRight className="h-3 w-3 text-zinc-600" />
            <Link href="/nomzod" className="text-xs text-zinc-400 hover:text-primary transition-colors">
              Nomzod portali
            </Link>
            <ChevronRight className="h-3 w-3 text-zinc-600" />
            <span className="text-xs font-medium text-primary">Shartnomalar & Amaliyot</span>
          </div>
          <h1 className="fb-display">Shartnomalar</h1>
          <p className="mt-1 text-sm text-[var(--fb-ink-secondary)]">
            Amaliyot o‘quv rejalari, shartnomalarni qabul qilish va ikki tomonlama ish boshlanishini tasdiqlash markazi.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {currentUser ? (
            <div className="flex items-center gap-3">
              <button
                onClick={() => (activeTab === "PLACEMENTS" ? loadPlacements() : loadEngagement())}
                disabled={isLoadingPlacements || isLoadingEngagement}
                title="Yangilash"
                className="p-2 rounded-lg border border-white/[0.08] bg-surface-card text-zinc-300 hover:text-white hover:border-primary/40 transition-colors"
              >
                <RefreshCw
                  className={`h-4 w-4 ${
                    isLoadingPlacements || isLoadingEngagement ? "animate-spin text-primary" : ""
                  }`}
                />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl skeuo-btn-accent px-4 py-2 text-xs font-semibold text-white"
            >
              <span>Tizimga kirish</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Unauthenticated View */}
      {!currentUser && !isAuthLoading && (
        <section className="rounded-[26px] skeuo-card p-8 md:p-12 text-center flex flex-col items-center max-w-xl mx-auto my-8">
          <div className="h-12 w-12 rounded-2xl skeuo-well-sm flex items-center justify-center text-[#D95F2B] mb-4">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h2 className="font-heading text-lg font-bold text-[var(--fb-ink)] mb-2">
            Shartnomalarni ko‘rish uchun tizimga kiring
          </h2>
          <p className="text-xs text-[var(--fb-ink-secondary)] max-w-md mb-6 leading-relaxed">
            Tasdiqlangan amaliyot o‘quv rejalari, korxona bilan kelishilgan vazifalar va ish boshlanishini ikki tomonlama tasdiqlash uchun talaba hisobingizga kiring.
          </p>
          <button
            onClick={() => setIsAuthModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl skeuo-btn-accent px-5 py-2.5 text-xs font-semibold text-white"
          >
            <span>Talaba sifatida kirish</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </section>
      )}

      {/* Authenticated Workspace */}
      {currentUser && (
        <div className="flex flex-col gap-6">
          {/* Main Module Tabs Switcher */}
          <div className="flex items-center gap-2 border-b border-[var(--fb-hairline)] pb-px">
            <button
              onClick={() => setActiveTab("PLACEMENTS")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === "PLACEMENTS"
                  ? "border-primary text-[var(--fb-ink)] bg-primary/5"
                  : "border-transparent text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)]"
              }`}
            >
              <BookOpen className="h-4 w-4 text-primary" />
              <span>Amaliyot Shartnomalari & O‘quv Rejasi</span>
              {placements.length > 0 && (
                <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-full bg-primary/20 text-primary">
                  {placements.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("ENGAGEMENTS")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === "ENGAGEMENTS"
                  ? "border-primary text-[var(--fb-ink)] bg-primary/5"
                  : "border-transparent text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)]"
              }`}
            >
              <Briefcase className="h-4 w-4 text-emerald-500" />
              <span>Ish Munosabatlari & Boshlanishni Tasdiqlash</span>
            </button>
          </div>

          {/* ================================================================ */}
          {/* TAB 1: PLACEMENTS (AMALIYOT SHARTNOMALARI & O'QUV REJASI)        */}
          {/* ================================================================ */}
          {activeTab === "PLACEMENTS" && (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                    Faol va Rejalashtirilgan Amaliyotlar
                  </h2>
                  <p className="text-xs text-zinc-400">
                    Oliy ta’lim muassasasi yoki korxona bilan bog‘langan barcha amaliyot o‘rinlari ro‘yxati.
                  </p>
                </div>
                <button
                  onClick={loadPlacements}
                  disabled={isLoadingPlacements}
                  className="skeuo-btn-secondary px-3 py-1.5 text-xs"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${isLoadingPlacements ? "animate-spin text-primary" : ""}`} />
                  <span>Yangilash</span>
                </button>
              </div>

              {placementsError && (
                <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{placementsError}</span>
                </div>
              )}

              {isLoadingPlacements ? (
                <div className="py-12 text-center text-xs text-zinc-400">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-primary" />
                  Amaliyotlar ro‘yxati yuklanmoqda...
                </div>
              ) : placements.length === 0 ? (
                <div className="rounded-xl border border-white/[0.08] bg-[#121214] p-8 text-center text-xs text-zinc-400">
                  <BookOpen className="h-8 w-8 mx-auto mb-2 text-zinc-600" />
                  <p className="text-zinc-300 font-semibold mb-1">Hozircha amaliyot shartnomalari mavjud emas</p>
                  <p className="text-zinc-500">
                    Tashkilotlar tomonidan e’lon qilingan vakansiyalarga ariza topshiring va taklifni qabul qiling.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {placements.map((plc) => {
                    const badge = getPlacementStatusBadge(plc.status);
                    return (
                      <div
                        key={plc.id}
                        className="rounded-xl border border-white/[0.08] bg-[#121214] p-5 flex flex-col justify-between hover:border-white/[0.15] transition-colors"
                      >
                        <div>
                          <div className="flex items-center justify-between mb-3">
                            <span className="min-w-0 truncate text-sm font-semibold text-[var(--fb-ink)]">
                              {plc.opportunity_title || "Amaliyot"}
                            </span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${badge.cls}`}>
                              {badge.label}
                            </span>
                          </div>

                          <div className="space-y-2 mb-4 text-xs text-zinc-300">
                            <div className="flex items-center gap-2 text-zinc-400">
                              <Building2 className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
                              <span className="truncate">{plc.organization_name || "Korxona"}</span>
                            </div>
                            <div className="flex items-center gap-2 text-zinc-400">
                              <Calendar className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
                              <span>Muddati: {plc.start_date || "—"} dan {plc.end_date || "—"} gacha</span>
                            </div>
                            <div className="flex items-center gap-2 text-zinc-400">
                              <FileText className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
                              <span>{plc.current_terms_id ? "Shartlar kelishilgan" : "Shartlar hali kelishilmagan"}</span>
                            </div>
                          </div>
                        </div>

                        <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between">
                          <Link
                            href="/nomzod/kundalik"
                            className="text-[11px] text-zinc-400 hover:text-primary transition-colors flex items-center gap-1"
                          >
                            <span>Kundalik</span>
                            <ChevronRight className="h-3 w-3" />
                          </Link>

                          <button
                            onClick={() => handleOpenPlanModal(plc.id)}
                            className="py-1.5 px-3 rounded-xl skeuo-btn-obsidian text-white text-xs font-semibold flex items-center gap-1.5"
                          >
                            <BookOpen className="h-3.5 w-3.5" />
                            <span>Rejani ko‘rish</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ================================================================ */}
          {/* TAB 2: ENGAGEMENTS (ISH MUNOSABATLARI & DUAL-CONFIRMATION)        */}
          {/* ================================================================ */}
          {activeTab === "ENGAGEMENTS" && (
            <div className="flex flex-col gap-6">
              {/* Engagement Lookup Input */}
              <div className="rounded-2xl skeuo-card p-5">
                <h2 className="text-xs font-bold text-[var(--fb-ink)] uppercase tracking-wider mb-2">
                  Ish Munosabatini Qidirish & Tekshirish
                </h2>
                <p className="text-xs text-[var(--fb-ink-secondary)] mb-4">
                  Ish beruvchi tomonidan berilgan taklif qabul qilingandan so‘ng shakllangan ish munosabati identifikatorini kiriting.
                </p>

                <div className="flex flex-col sm:flex-row items-center gap-2.5">
                  <div className="relative flex-1 w-full">
                    <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                    <input
                      type="text"
                      placeholder="Munosabat ID (masalan: 123e4567-e89b-12d3-a456-426614174000)..."
                      value={engagementIdInput}
                      onChange={(e) => setEngagementIdInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && loadEngagement()}
                      className="w-full pl-9 pr-3 py-2 rounded-xl skeuo-input text-xs font-mono"
                    />
                  </div>
                  <button
                    onClick={() => loadEngagement()}
                    disabled={isLoadingEngagement || !engagementIdInput.trim()}
                    className="w-full sm:w-auto py-2 px-4 rounded-xl skeuo-btn-accent text-white text-xs font-semibold flex items-center justify-center gap-1.5 disabled:opacity-50"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${isLoadingEngagement ? "animate-spin" : ""}`} />
                    <span>Yuklash</span>
                  </button>
                </div>

                {engagementError && (
                  <div className="mt-3 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span>{engagementError}</span>
                  </div>
                )}
              </div>

              {/* Engagement Workspace Card */}
              {isLoadingEngagement ? (
                <div className="py-12 text-center text-xs text-zinc-400">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-primary" />
                  Ish munosabati ma’lumotlari tekshirilmoqda...
                </div>
              ) : activeEngagement ? (
                <div className="rounded-xl border border-white/[0.08] bg-[#121214] p-6 space-y-6">
                  {/* Top Bar */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-zinc-400">Ish munosabati:</span>
                        <span className="font-mono text-xs font-bold text-white">{activeEngagement.id}</span>
                      </div>
                      <p className="text-xs text-zinc-400">
                        Vakansiya turi: <span className="font-semibold text-primary">{activeEngagement.opportunity?.kind}</span> | 
                        Tomoningiz: <span className="font-semibold text-emerald-400">{activeEngagement.my_side}</span>
                      </p>
                    </div>

                    <span
                      className={`px-3 py-1 rounded-md text-xs font-mono font-bold border ${
                        getEngagementStatusBadge(activeEngagement.status).cls
                      }`}
                    >
                      {getEngagementStatusBadge(activeEngagement.status).label}
                    </span>
                  </div>

                  {/* Dual-Party Confirmation Visualizer */}
                  <div className="rounded-xl skeuo-well p-4">
                    <h3 className="text-xs font-bold text-[var(--fb-ink)] uppercase tracking-wider mb-2 flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-primary" />
                      <span>Ikki Tomonlama Ish Boshlanishini Tasdiqlash</span>
                    </h3>
                    <p className="text-[11px] text-[var(--fb-ink-secondary)] mb-4 leading-relaxed">
                      O‘zbekiston Respublikasi Mehnat Kodeksi va FlexBridge reglamentiga ko‘ra, faol ish holati faqat ikkala tomon — ham talaba, ham ish beruvchi tasdiqlaganidan so‘ng kuchga kiradi.
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Candidate Box */}
                      <div className="rounded-lg border border-white/[0.08] bg-[#18181b] p-3.5">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-semibold text-zinc-200">Nomzod (Siz)</span>
                          {activeEngagement.confirmations.some((c) => c.side === "CANDIDATE" && c.action === "CONFIRM_START") ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 flex items-center gap-1">
                              <Check className="h-3 w-3" />
                              <span>Tasdiqlangan</span>
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              <span>Tasdiq kutilmoqda</span>
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-zinc-400">
                          {activeEngagement.confirmations.some((c) => c.side === "CANDIDATE" && c.action === "CONFIRM_START")
                            ? "Siz ish boshlanganini tasdiqlagansiz."
                            : "Ishga kirishganingizni tasdiqlashingiz kerak."}
                        </p>
                      </div>

                      {/* Employer Box */}
                      <div className="rounded-lg border border-white/[0.08] bg-[#18181b] p-3.5">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-semibold text-zinc-200">Ish Beruvchi (Tashkilot)</span>
                          {activeEngagement.confirmations.some((c) => c.side === "EMPLOYER" && c.action === "CONFIRM_START") ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 flex items-center gap-1">
                              <Check className="h-3 w-3" />
                              <span>Tasdiqlangan</span>
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              <span>Tasdiq kutilmoqda</span>
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-zinc-400">
                          {activeEngagement.confirmations.some((c) => c.side === "EMPLOYER" && c.action === "CONFIRM_START")
                            ? "Ish beruvchi ish boshlanishini tasdiqlagan."
                            : "Ish beruvchining yakuniy tasdig'i kutilmoqda."}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Confirmation Feedback Banner */}
                  {confirmationFeedback && (
                    <div
                      className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
                        confirmationFeedback.type === "success"
                          ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-300"
                          : "bg-rose-500/10 border border-rose-500/30 text-rose-300"
                      }`}
                    >
                      {confirmationFeedback.type === "success" ? (
                        <CheckCircle2 className="h-4 w-4 shrink-0" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                      )}
                      <span>{confirmationFeedback.message}</span>
                    </div>
                  )}

                  {/* Actions Bar (API-046) */}
                  <div className="border-t border-white/[0.06] pt-4 flex flex-wrap items-center justify-between gap-3">
                    <div className="text-xs text-zinc-400">
                      Boshlanish sanasi: <span className="font-mono text-zinc-200">{activeEngagement.start_date || "—"}</span>
                      {activeEngagement.confirmed_started_at && (
                        <span className="ml-3 text-emerald-400">
                          Tasdiqlangan vaqt: {new Date(activeEngagement.confirmed_started_at).toLocaleString("uz-UZ")}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {activeEngagement.status === "PENDING_START_CONFIRMATION" && (
                        <>
                          <button
                            onClick={() => handleConfirmEngagement("CONFIRM_START")}
                            disabled={isSubmittingConfirmation}
                            className="py-2 px-3.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                          >
                            <CheckCircle2 className="h-4 w-4" />
                            <span>Ish boshlanganini tasdiqlash</span>
                          </button>
                          <button
                            onClick={() => handleConfirmEngagement("DISPUTE_START")}
                            disabled={isSubmittingConfirmation}
                            className="py-2 px-3.5 rounded-lg border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                          >
                            <AlertTriangle className="h-4 w-4" />
                            <span>E’tiroz bildirish</span>
                          </button>
                        </>
                      )}

                      {activeEngagement.status === "ACTIVE" && (
                        <>
                          <button
                            onClick={() => handleConfirmEngagement("CONFIRM_END")}
                            disabled={isSubmittingConfirmation}
                            className="skeuo-btn-obsidian py-2 px-3.5 text-xs disabled:opacity-50"
                          >
                            <CheckCircle2 className="h-4 w-4" />
                            <span>Ish yakunlanganini tasdiqlash</span>
                          </button>
                          <button
                            onClick={() => handleConfirmEngagement("DISPUTE_END")}
                            disabled={isSubmittingConfirmation}
                            className="py-2 px-3.5 rounded-lg border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                          >
                            <AlertTriangle className="h-4 w-4" />
                            <span>Yakunlanishga e’tiroz bildirish</span>
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Confirmation History Timeline */}
                  {activeEngagement.confirmations.length > 0 && (
                    <div className="border-t border-white/[0.06] pt-4">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-3">
                        Tasdiqlar Tarixi
                      </h4>
                      <div className="space-y-2">
                        {activeEngagement.confirmations.map((conf) => (
                          <div
                            key={conf.id}
                            className="rounded-lg border border-white/[0.04] bg-black/20 p-3 text-xs flex items-center justify-between"
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-zinc-200">
                                {conf.side === "CANDIDATE" ? "Nomzod" : "Ish beruvchi"}
                              </span>
                              <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-zinc-800 text-primary">
                                {conf.action}
                              </span>
                            </div>
                            <span className="text-[11px] text-zinc-400 font-mono">
                              {new Date(conf.occurred_at).toLocaleString("uz-UZ")}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="rounded-xl border border-white/[0.08] bg-[#121214] p-8 text-center text-xs text-zinc-500">
                  Shartnoma kodini kiriting va «Yuklash» tugmasini bosing.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ================================================================ */}
      {/* PLACEMENT PLAN & ACCEPTANCE MODAL (API-050 / API-048)            */}
      {/* ================================================================ */}
      {selectedPlacementId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-3xl rounded-xl border border-white/[0.1] bg-[#121214] p-6 max-h-[90vh] overflow-y-auto shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4 mb-4">
              <div>
                <h3 className="text-base font-bold text-[var(--fb-ink)] flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-primary" />
                  <span>Amaliyot O‘quv Rejasi & Shartlari</span>
                </h3>
                <p className="text-xs text-zinc-400 mt-0.5">
                  {(() => {
                    const p = placements.find((x) => x.id === selectedPlacementId);
                    return p ? [p.opportunity_title, p.organization_name].filter(Boolean).join(" · ") : "Amaliyot";
                  })()}
                </p>
              </div>
              <button
                onClick={() => setSelectedPlacementId(null)}
                className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/[0.06] hover:text-white transition-colors"
              >
                <XCircle className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            {isLoadingPlan ? (
              <div className="py-12 text-center text-xs text-zinc-400">
                <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-primary" />
                Amaliyot rejasi va vazifalari yuklanmoqda...
              </div>
            ) : planError ? (
              <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300">
                {planError}
              </div>
            ) : placementPlan ? (
              <div className="space-y-5">
                {/* General Info */}
                <div className="rounded-lg border border-white/[0.06] bg-black/30 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold text-white">
                      {placementPlan.title || "Amaliyot O'quv Rejasi"}
                    </h4>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-primary/20 text-primary border border-primary/30">
                      Versiya: {placementPlan.version}
                    </span>
                  </div>

                  {placementPlan.objectives && (
                    <p className="text-xs text-zinc-300 leading-relaxed">
                      {placementPlan.objectives}
                    </p>
                  )}

                  {/* Time Limits Table */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 border-t border-white/[0.04] text-[11px]">
                    <div className="p-2 rounded bg-[#18181b]">
                      <span className="text-zinc-500 block">Kunlik limit:</span>
                      <span className="font-mono font-bold text-zinc-200">
                        {placementPlan.daily_limit_minutes} daqiqa ({Math.floor(placementPlan.daily_limit_minutes / 60)}s)
                      </span>
                    </div>
                    <div className="p-2 rounded bg-[#18181b]">
                      <span className="text-zinc-500 block">Haftalik limit:</span>
                      <span className="font-mono font-bold text-zinc-200">
                        {placementPlan.weekly_limit_minutes} daqiqa ({Math.floor(placementPlan.weekly_limit_minutes / 60)}s)
                      </span>
                    </div>
                    <div className="p-2 rounded bg-[#18181b]">
                      <span className="text-zinc-500 block">Talab etilgan umumiy:</span>
                      <span className="font-mono font-bold text-emerald-400">
                        {placementPlan.required_minutes} daqiqa ({Math.floor(placementPlan.required_minutes / 60)}s)
                      </span>
                    </div>
                  </div>
                </div>

                {/* Tasks List */}
                <div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-2">
                    Amaliyot Vazifalari ({placementPlan.tasks.length})
                  </h4>
                  <div className="space-y-2">
                    {placementPlan.tasks.map((task) => (
                      <div
                        key={task.code}
                        className="rounded-lg border border-white/[0.06] bg-black/20 p-3 text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[11px] font-bold text-primary">
                            [{task.code}] {task.title}
                          </span>
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-mono ${
                              task.required
                                ? "bg-amber-500/20 text-amber-300"
                                : "bg-zinc-800 text-zinc-400"
                            }`}
                          >
                            {task.required ? "Majburiy" : "Ixtiyoriy"}
                          </span>
                        </div>
                        <p className="text-zinc-400 text-[11px] leading-relaxed">
                          Kutilayotgan natija: {task.expected_result}
                        </p>
                        {task.target_minutes && (
                          <p className="text-zinc-500 text-[10px] font-mono">
                            Rejalashtirilgan vaqt: {task.target_minutes} daqiqa
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Accept Terms Banner & Action (API-048) */}
                {acceptTermsSuccess ? (
                  <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs text-emerald-300 flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 shrink-0" />
                    <span>{acceptTermsSuccess}</span>
                  </div>
                ) : (
                  <div className="rounded-lg border border-primary/30 bg-primary/10 p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
                    <div>
                      <h5 className="text-xs font-bold text-white mb-0.5">
                        Amaliyot shartlari va o‘quv rejasiga rozimisiz?
                      </h5>
                      <p className="text-[11px] text-zinc-300">
                        Shartlarni qabul qilish orqali siz belgilangan vazifalarni bajarish va kundalik yuritish majburiyatini olasiz.
                      </p>
                    </div>

                    <button
                      onClick={handleAcceptTerms}
                      disabled={isAcceptingTerms}
                      className="w-full sm:w-auto py-2 px-4 rounded-xl skeuo-btn-accent text-white text-xs font-semibold flex items-center justify-center gap-1.5 disabled:opacity-50 shrink-0"
                    >
                      {isAcceptingTerms ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        <Check className="h-4 w-4" />
                      )}
                      <span>Shartlarni Qabul Qilish</span>
                    </button>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        requiredPortal="CANDIDATE"
        title="Talaba / Nomzod kirishi"
        subtitle="Amaliyot shartnomalarini ko‘rish va tasdiqlash uchun talaba hisobingizga kiring"
        onSuccess={async () => {
          setIsAuthModalOpen(false);
          const user = await fetchAuthMe().catch(() => null);
          setCurrentUser(user);
        }}
      />
    </main>
  );
}

export default function CandidateShartnomalarHub() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-zinc-400">Yuklanmoqda...</div>}>
      <ShartnomalarHubContent />
    </Suspense>
  );
}
