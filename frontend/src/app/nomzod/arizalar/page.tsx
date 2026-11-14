"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  Building2,
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  XCircle,
  RotateCcw,
  ArrowRight,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Briefcase,
  Video,
  Award,
  Layers,
  X,
  Loader2,
  LogOut,
  RefreshCw,
} from "lucide-react";
import {
  CandidateApplicationsSummary,
  CandidateApplicationItem,
  CandidateApplicationDetail,
  fetchCandidateApplicationsSummary,
  fetchCandidateApplications,
  fetchCandidateApplicationDetail,
  withdrawCandidateApplication,
  reapplyCandidateApplication,
  fetchAuthMe,
  logoutUser,
  AuthUser,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";

type FilterTab = "ALL" | "SUBMITTED" | "UNDER_REVIEW" | "INTERVIEW_SCHEDULED" | "OFFERED" | "ACCEPTED" | "REJECTED" | "WITHDRAWN";

function getStatusBadge(status: string) {
  switch (status) {
    case "SUBMITTED":
      return {
        label: "Topshirildi",
        className: "bg-sky-500/10 text-sky-400 border-sky-500/20",
        icon: Clock,
      };
    case "UNDER_REVIEW":
      return {
        label: "Ko‘rib chiqilmoqda",
        className: "bg-amber-500/10 text-amber-400 border-amber-500/20",
        icon: Layers,
      };
    case "INTERVIEW_SCHEDULED":
      return {
        label: "Suhbat belgilangan",
        className: "bg-violet-500/10 text-violet-400 border-violet-500/20",
        icon: Video,
      };
    case "OFFERED":
      return {
        label: "Taklif berildi",
        className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
        icon: Award,
      };
    case "ACCEPTED":
      return {
        label: "Qabul qilindi",
        className: "bg-emerald-600 text-white border-emerald-500",
        icon: CheckCircle2,
      };
    case "REJECTED":
      return {
        label: "Rad etildi",
        className: "bg-rose-500/10 text-rose-400 border-rose-500/20",
        icon: XCircle,
      };
    case "WITHDRAWN":
      return {
        label: "Qaytarib olingan",
        className: "bg-zinc-800/80 text-zinc-400 border-zinc-700/50",
        icon: RotateCcw,
      };
    default:
      return {
        label: status,
        className: "bg-zinc-800 text-zinc-300 border-zinc-700",
        icon: Clock,
      };
  }
}

export default function CandidateApplicationsPage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);

  const [summary, setSummary] = useState<CandidateApplicationsSummary | null>(null);
  const [applications, setApplications] = useState<CandidateApplicationItem[]>([]);
  const [activeTab, setActiveTab] = useState<FilterTab>("ALL");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Detail Modal State
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CandidateApplicationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Withdraw Modal State
  const [withdrawAppId, setWithdrawAppId] = useState<string | null>(null);
  const [withdrawReason, setWithdrawReason] = useState("");
  const [isWithdrawing, setIsWithdrawing] = useState(false);
  const [withdrawError, setWithdrawError] = useState<string | null>(null);

  // Reapply Modal State
  const [reapplyAppId, setReapplyAppId] = useState<string | null>(null);
  const [reapplyReason, setReapplyReason] = useState("");
  const [isReapplying, setIsReapplying] = useState(false);
  const [reapplyError, setReapplyError] = useState<string | null>(null);

  // Synchronize authentication and application data
  useEffect(() => {
    let active = true;

    async function init() {
      try {
        const curr = await fetchAuthMe();
        if (!active) return;
        setUser(curr);
        setAuthChecked(true);

        if (curr) {
          try {
            const [sumData, listData] = await Promise.all([
              fetchCandidateApplicationsSummary(),
              fetchCandidateApplications(activeTab !== "ALL" ? { status: activeTab } : undefined),
            ]);
            if (active) {
              setSummary(sumData);
              setApplications(listData.items || []);
            }
          } catch (err: unknown) {
            if (active) {
              setError(err instanceof Error ? err.message : "Ma'lumotlarni yuklashda xatolik");
            }
          }
        }
      } catch {
        if (!active) return;
        setUser(null);
        setAuthChecked(true);
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    init();

    return () => {
      active = false;
    };
  }, [activeTab]);

  const loadData = async (filterStatus?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const [sumData, listData] = await Promise.all([
        fetchCandidateApplicationsSummary(),
        fetchCandidateApplications(filterStatus && filterStatus !== "ALL" ? { status: filterStatus } : undefined),
      ]);
      setSummary(sumData);
      setApplications(listData.items || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Ma'lumotlarni yuklashda xatolik";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTabChange = (tab: FilterTab) => {
    setActiveTab(tab);
  };

  const openDetail = async (id: string) => {
    setSelectedAppId(id);
    setDetailLoading(true);
    try {
      const data = await fetchCandidateApplicationDetail(id);
      setDetail(data);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Tafsilotlarni yuklab bo'lmadi");
      setSelectedAppId(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleWithdraw = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!withdrawAppId) return;
    setIsWithdrawing(true);
    setWithdrawError(null);
    try {
      await withdrawCandidateApplication(withdrawAppId, withdrawReason.trim() || undefined);
      setWithdrawAppId(null);
      setWithdrawReason("");
      // Refresh list & summary
      await loadData(activeTab);
      if (selectedAppId === withdrawAppId) {
        setSelectedAppId(null);
        setDetail(null);
      }
    } catch (err: unknown) {
      setWithdrawError(err instanceof Error ? err.message : "Arizani qaytarib olishda xatolik");
    } finally {
      setIsWithdrawing(false);
    }
  };

  const handleReapply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reapplyAppId) return;
    setIsReapplying(true);
    setReapplyError(null);
    try {
      await reapplyCandidateApplication(reapplyAppId, {
        reason: reapplyReason.trim() || undefined,
      });
      setReapplyAppId(null);
      setReapplyReason("");
      await loadData(activeTab);
    } catch (err: unknown) {
      setReapplyError(err instanceof Error ? err.message : "Qayta topshirishda xatolik");
    } finally {
      setIsReapplying(false);
    }
  };

  const handleLogout = async () => {
    await logoutUser();
    setUser(null);
    setSummary(null);
    setApplications([]);
  };

  return (
    <main className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-4 py-8 md:px-8">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/[0.08] pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Link href="/" className="text-xs text-zinc-400 hover:text-primary transition-colors">
              Bosh sahifa
            </Link>
            <ChevronRight className="h-3 w-3 text-zinc-600" />
            <span className="text-xs font-medium text-primary">Nomzod arizalari</span>
          </div>
          <h1 className="font-heading text-2xl md:text-3xl font-bold text-white tracking-tight">
            Mening arizalarim va tanlov holati
          </h1>
          <p className="mt-1 text-sm text-zinc-400">
            Topshirilgan arizalarning real vaqt holati, suhbatlar jadvali va takliflarni boshqarish.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-semibold text-zinc-200">Faol hisob</span>
                <span className="text-[11px] text-zinc-400">{user.user_id.slice(0, 8)}...</span>
              </div>
              <button
                onClick={() => loadData(activeTab)}
                disabled={isLoading}
                title="Yangilash"
                className="p-2 rounded-lg border border-white/[0.08] bg-surface-card text-zinc-300 hover:text-white hover:border-primary/40 transition-colors"
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin text-primary" : ""}`} />
              </button>
              <button
                onClick={handleLogout}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-surface-card px-3 py-2 text-xs font-medium text-zinc-300 hover:bg-white/[0.04] hover:text-rose-400 transition-colors"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Chiqish</span>
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuthModal(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-primary-hover transition-colors"
            >
              <span>Tizimga kirish</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Unauthenticated View */}
      {!user && authChecked && (
        <section className="rounded-xl border border-white/[0.08] bg-surface-card p-8 md:p-12 text-center flex flex-col items-center max-w-xl mx-auto my-8">
          <div className="h-12 w-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mb-4">
            <FileText className="h-6 w-6" />
          </div>
          <h2 className="font-heading text-lg font-bold text-white mb-2">Arizalarni ko‘rish uchun tizimga kiring</h2>
          <p className="text-xs text-zinc-400 max-w-md mb-6 leading-relaxed">
            Siz topshirgan barcha arizalar, ularning ko‘rib chiqilish bosqichlari va tashkilotlar tomonidan taklif etilgan suhbatlarni kuzatib borish uchun nomzod hisobingizga kiring.
          </p>
          <button
            onClick={() => setShowAuthModal(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-xs font-semibold text-white hover:bg-primary-hover transition-colors"
          >
            <span>Nomzod sifatida kirish</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </section>
      )}

      {/* Authenticated Dashboard View */}
      {user && (
        <>
          {/* Metrics Bar (Single Source of Metric Truth) */}
          <section className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:gap-4">
            <div className="rounded-xl border border-white/[0.08] bg-surface-card p-4 transition-colors hover:border-primary/30">
              <div className="flex items-center justify-between text-zinc-400 mb-2">
                <span className="text-xs font-medium">Jami arizalar</span>
                <FileText className="h-4 w-4 text-primary" />
              </div>
              <div className="font-heading text-2xl font-bold text-white">
                {summary ? summary.total_applications : "—"}
              </div>
              <p className="mt-1 text-[11px] text-zinc-500">Topshirilgan arizalar</p>
            </div>

            <div className="rounded-xl border border-white/[0.08] bg-surface-card p-4 transition-colors hover:border-amber-500/30">
              <div className="flex items-center justify-between text-zinc-400 mb-2">
                <span className="text-xs font-medium">Ko‘rib chiqilmoqda</span>
                <Clock className="h-4 w-4 text-amber-400" />
              </div>
              <div className="font-heading text-2xl font-bold text-amber-400">
                {summary ? summary.submitted + summary.under_review : "—"}
              </div>
              <p className="mt-1 text-[11px] text-zinc-500">HR tahlil jarayonida</p>
            </div>

            <div className="rounded-xl border border-white/[0.08] bg-surface-card p-4 transition-colors hover:border-violet-500/30">
              <div className="flex items-center justify-between text-zinc-400 mb-2">
                <span className="text-xs font-medium">Suhbat belgilangan</span>
                <Video className="h-4 w-4 text-violet-400" />
              </div>
              <div className="font-heading text-2xl font-bold text-violet-400">
                {summary ? summary.interview_scheduled : "—"}
              </div>
              <p className="mt-1 text-[11px] text-zinc-500">Rejalashtirilgan intervyular</p>
            </div>

            <div className="rounded-xl border border-white/[0.08] bg-surface-card p-4 transition-colors hover:border-emerald-500/30">
              <div className="flex items-center justify-between text-zinc-400 mb-2">
                <span className="text-xs font-medium">Taklif / Qabul</span>
                <Award className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="font-heading text-2xl font-bold text-emerald-400">
                {summary ? summary.offered + summary.accepted : "—"}
              </div>
              <p className="mt-1 text-[11px] text-zinc-500">Ish takliflari va boshlanish</p>
            </div>
          </section>

          {/* Page-Level Filter Control Bar */}
          <section className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-white/[0.08]">
            {(
              [
                { id: "ALL", label: "Barchasi", count: summary?.total_applications },
                { id: "UNDER_REVIEW", label: "Ko‘rib chiqilmoqda", count: summary ? summary.submitted + summary.under_review : undefined },
                { id: "INTERVIEW_SCHEDULED", label: "Suhbat", count: summary?.interview_scheduled },
                { id: "OFFERED", label: "Taklif berilgan", count: summary?.offered },
                { id: "ACCEPTED", label: "Qabul qilingan", count: summary?.accepted },
                { id: "REJECTED", label: "Rad etilgan", count: summary?.rejected },
                { id: "WITHDRAWN", label: "Qaytarib olingan", count: summary?.withdrawn },
              ] as const
            ).map((tab) => {
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    active
                      ? "border border-primary/30 bg-primary/10 text-primary"
                      : "text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200"
                  }`}
                >
                  <span>{tab.label}</span>
                  {typeof tab.count === "number" && (
                    <span
                      className={`rounded px-1.5 py-0.2 text-[10px] font-mono ${
                        active ? "bg-primary/20 text-primary font-bold" : "bg-white/[0.06] text-zinc-400"
                      }`}
                    >
                      {tab.count}
                    </span>
                  )}
                </button>
              );
            })}
          </section>

          {/* Applications List */}
          <section className="flex flex-col gap-3">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                <span className="text-xs text-zinc-400">Arizalar yuklanmoqda...</span>
              </div>
            ) : error ? (
              <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-5 text-center">
                <AlertCircle className="h-5 w-5 text-rose-400 mx-auto mb-2" />
                <p className="text-xs text-rose-300 mb-3">{error}</p>
                <button
                  onClick={() => loadData(activeTab)}
                  className="rounded bg-rose-600/30 px-3 py-1 text-xs text-rose-200 hover:bg-rose-600/50"
                >
                  Qayta urinish
                </button>
              </div>
            ) : applications.length === 0 ? (
              <div className="rounded-xl border border-white/[0.08] bg-surface-card p-12 text-center flex flex-col items-center">
                <FileText className="h-10 w-10 text-zinc-600 mb-3" />
                <h3 className="text-sm font-semibold text-zinc-200 mb-1">
                  Ushbu toifada arizalar topilmadi
                </h3>
                <p className="text-xs text-zinc-400 max-w-sm mb-4">
                  Katalogdan vakansiyalarni ko‘zdan kechiring va o‘z ta’lim dasturingizga mos imkoniyatlarga ariza topshiring.
                </p>
                <Link
                  href="/"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3.5 py-2 text-xs font-semibold text-primary hover:bg-primary/20 transition-colors"
                >
                  <span>E’lonlar katalogiga o‘tish</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            ) : (
              applications.map((app) => {
                const badge = getStatusBadge(app.status);
                const BadgeIcon = badge.icon;
                const submittedDate = app.created_at
                  ? new Date(app.created_at).toLocaleDateString("uz-UZ", {
                      day: "2-digit",
                      month: "2-digit",
                      year: "numeric",
                    })
                  : null;

                const canWithdraw = !["ACCEPTED", "WITHDRAWN"].includes(app.status);
                const canReapply = app.status === "REJECTED";

                return (
                  <article
                    key={app.id}
                    className="rounded-xl border border-white/[0.08] bg-surface-card p-5 transition-colors hover:border-white/[0.15]"
                  >
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                      <div className="flex min-w-0 gap-3.5">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
                          <Building2 className="h-5 w-5" aria-hidden="true" />
                        </div>
                        <div className="min-w-0">
                          <div className="mb-1 flex flex-wrap items-center gap-2">
                            <span className="text-xs font-semibold text-zinc-200">
                              {app.opportunity?.organization_name || "Tashkilot"}
                            </span>
                            <span className="inline-flex items-center gap-1 rounded border border-emerald-500/20 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-300">
                              <ShieldCheck className="h-3 w-3" />
                              Tasdiqlangan
                            </span>
                          </div>

                          <h2 className="font-heading text-base font-bold text-white">
                            <Link
                              href={`/ishlar/${app.opportunity_id}`}
                              className="hover:text-primary transition-colors inline-flex items-center gap-1.5"
                            >
                              <span>{app.opportunity?.title || "Lavozim"}</span>
                              <ExternalLink className="h-3.5 w-3.5 opacity-60" />
                            </Link>
                          </h2>

                          <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-400">
                            {submittedDate && (
                              <span className="inline-flex items-center gap-1">
                                <Calendar className="h-3.5 w-3.5 text-zinc-500" />
                                Topshirildi: {submittedDate}
                              </span>
                            )}
                            {app.current_attempt && (
                              <span className="inline-flex items-center gap-1">
                                <RotateCcw className="h-3.5 w-3.5 text-zinc-500" />
                                {app.current_attempt.attempt_no}-urinish
                              </span>
                            )}
                            {app.opportunity?.work_mode && (
                              <span className="inline-flex items-center gap-1">
                                <Briefcase className="h-3.5 w-3.5 text-zinc-500" />
                                {app.opportunity.work_mode}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Right Action & Status Area */}
                      <div className="flex flex-row sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-2.5 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-white/[0.06]">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium ${badge.className}`}
                        >
                          <BadgeIcon className="h-3.5 w-3.5" />
                          <span>{badge.label}</span>
                        </span>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => openDetail(app.id)}
                            className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-white/[0.07] hover:border-primary/40 transition-colors"
                          >
                            Tafsilotlar
                          </button>

                          {canWithdraw && (
                            <button
                              onClick={() => {
                                setWithdrawAppId(app.id);
                                setWithdrawReason("");
                                setWithdrawError(null);
                              }}
                              className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-2.5 py-1.5 text-xs font-medium text-rose-300 hover:bg-rose-500/20 transition-colors"
                            >
                              Qaytarib olish
                            </button>
                          )}

                          {canReapply && (
                            <button
                              onClick={() => {
                                setReapplyAppId(app.id);
                                setReapplyReason("");
                                setReapplyError(null);
                              }}
                              className="rounded-lg border border-primary/30 bg-primary/10 px-2.5 py-1.5 text-xs font-medium text-primary hover:bg-primary/20 transition-colors"
                            >
                              Qayta topshirish
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })
            )}
          </section>
        </>
      )}

      {/* Application Detail Modal */}
      {selectedAppId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-2xl bg-surface-card border border-white/[0.1] rounded-xl shadow-2xl p-6 sm:p-7 max-h-[90vh] flex flex-col gap-5 overflow-hidden">
            <button
              onClick={() => {
                setSelectedAppId(null);
                setDetail(null);
              }}
              type="button"
              className="absolute top-4 right-4 p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            {detailLoading || !detail ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                <span className="text-xs text-zinc-400">Tafsilotlar yuklanmoqda...</span>
              </div>
            ) : (
              <>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-zinc-400">
                      {detail.opportunity?.organization_name}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] font-medium ${
                        getStatusBadge(detail.status).className
                      }`}
                    >
                      {getStatusBadge(detail.status).label}
                    </span>
                  </div>
                  <h2 className="font-heading text-lg font-bold text-white">
                    {detail.opportunity?.title || "Lavozim tafsiloti"}
                  </h2>
                </div>

                <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-5">
                  {/* Active Interview Notice if scheduled */}
                  {detail.interview && (
                    <div className="rounded-lg border border-violet-500/30 bg-violet-500/10 p-4">
                      <div className="flex items-center gap-2 text-violet-400 font-semibold text-xs mb-2">
                        <Video className="h-4 w-4" />
                        <span>Suhbat taklifi belgilangan</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs text-zinc-300">
                        <div>
                          <span className="text-zinc-500 block">Boshlanish vaqti:</span>
                          {new Date(detail.interview.starts_at).toLocaleString("uz-UZ")}
                        </div>
                        <div>
                          <span className="text-zinc-500 block">Formati:</span>
                          {detail.interview.mode || "Online"}
                        </div>
                        {detail.interview.location_or_link && (
                          <div className="col-span-2 mt-1">
                            <span className="text-zinc-500 block">Havola / Joylashuv:</span>
                            <span className="font-mono text-[11px] text-violet-300 break-all">
                              {detail.interview.location_or_link}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Active Offer Notice if offered */}
                  {detail.offer && (
                    <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4">
                      <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs mb-2">
                        <Award className="h-4 w-4" />
                        <span>Ish taklifi (Offer)</span>
                      </div>
                      <div className="text-xs text-zinc-300">
                        <p>Holat: <span className="font-bold text-emerald-300">{detail.offer.status}</span></p>
                        {detail.offer.expires_at && (
                          <p className="mt-1 text-zinc-400 text-[11px]">
                            Amal qilish muddati: {new Date(detail.offer.expires_at).toLocaleString("uz-UZ")}
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Attempts Summary */}
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                      Topshirish urinishlari ({detail.attempts.length})
                    </h3>
                    <div className="flex flex-col gap-2">
                      {detail.attempts.map((att) => (
                        <div
                          key={att.id}
                          className="rounded-lg border border-white/[0.06] bg-surface-lowest p-3 text-xs"
                        >
                          <div className="flex items-center justify-between text-zinc-300 font-medium mb-1">
                            <span>{att.attempt_no}-urinish</span>
                            <span className="text-zinc-500 text-[11px]">
                              {new Date(att.submitted_at).toLocaleString("uz-UZ")}
                            </span>
                          </div>
                          {att.schedule_result && (
                            <span className="text-[11px] text-zinc-400">
                              Dars jadvali muvofiqligi: <span className="font-semibold text-primary">{att.schedule_result}</span>
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Status Timeline */}
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                      Holat xronologiyasi (Audit Trail)
                    </h3>
                    <div className="relative pl-5 border-l border-white/[0.1] flex flex-col gap-4">
                      {detail.timeline.map((ev) => (
                        <div key={ev.id} className="relative">
                          <div className="absolute -left-[25px] top-1 h-2.5 w-2.5 rounded-full bg-primary border-2 border-surface-card" />
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-zinc-200">
                              {getStatusBadge(ev.to_status).label}
                            </span>
                            <span className="text-[10px] text-zinc-500">
                              {new Date(ev.occurred_at).toLocaleString("uz-UZ")}
                            </span>
                          </div>
                          {ev.reason && (
                            <p className="text-[11px] text-zinc-400 mt-0.5">Sabab: {ev.reason}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-white/[0.08] flex justify-end">
                  <button
                    onClick={() => {
                      setSelectedAppId(null);
                      setDetail(null);
                    }}
                    className="rounded-lg border border-white/[0.1] px-4 py-2 text-xs font-semibold text-zinc-300 hover:text-white hover:bg-white/[0.06]"
                  >
                    Yopish
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Withdraw Modal */}
      {withdrawAppId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md bg-surface-card border border-white/[0.1] rounded-xl shadow-2xl p-6 flex flex-col gap-4">
            <button
              onClick={() => setWithdrawAppId(null)}
              type="button"
              className="absolute top-4 right-4 p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06]"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                <RotateCcw className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-heading text-base font-bold text-white">Arizani qaytarib olasizmi?</h3>
                <p className="text-xs text-zinc-400">Ushbu amal tanlov jarayonini to‘xtatadi.</p>
              </div>
            </div>

            <p className="text-xs text-zinc-300 leading-relaxed">
              Arizani qaytarib olganingizda tashkilot tanlov ro‘yxatidan chiqasiz va band qilingan o‘rin bo‘shatiladi.
            </p>

            <form onSubmit={handleWithdraw} className="flex flex-col gap-3">
              <label className="flex flex-col gap-1.5">
                <span className="text-xs text-zinc-400">Qaytarib olish sababi (ixtiyoriy):</span>
                <input
                  type="text"
                  value={withdrawReason}
                  onChange={(e) => setWithdrawReason(e.target.value)}
                  placeholder="Masalan: Boshqa taklifni qabul qildim yoki vaqtim to‘g‘ri kelmadi"
                  className="rounded-lg border border-white/[0.1] bg-surface-lowest px-3 py-2 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-rose-400 focus:outline-none"
                />
              </label>

              {withdrawError && (
                <p className="text-xs text-rose-400 bg-rose-500/10 p-2 rounded border border-rose-500/20">
                  {withdrawError}
                </p>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setWithdrawAppId(null)}
                  disabled={isWithdrawing}
                  className="rounded-lg border border-white/[0.1] px-3.5 py-2 text-xs font-semibold text-zinc-300 hover:text-white"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isWithdrawing}
                  className="rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {isWithdrawing && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  <span>Qaytarib olishni tasdiqlash</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reapply Modal */}
      {reapplyAppId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md bg-surface-card border border-white/[0.1] rounded-xl shadow-2xl p-6 flex flex-col gap-4">
            <button
              onClick={() => setReapplyAppId(null)}
              type="button"
              className="absolute top-4 right-4 p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06]"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                <RotateCcw className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-heading text-base font-bold text-white">Arizani qayta topshirish</h3>
                <p className="text-xs text-zinc-400">Yangi urinish bilan yangilash (24 soatlik tanaffus qoidasi).</p>
              </div>
            </div>

            <form onSubmit={handleReapply} className="flex flex-col gap-3">
              <label className="flex flex-col gap-1.5">
                <span className="text-xs text-zinc-400">Qayta topshirish sababi yoki izoh:</span>
                <input
                  type="text"
                  value={reapplyReason}
                  onChange={(e) => setReapplyReason(e.target.value)}
                  placeholder="Ko‘nikmalarimni yangiladim yoki dars jadvalim o‘zgardi"
                  className="rounded-lg border border-white/[0.1] bg-surface-lowest px-3 py-2 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none"
                />
              </label>

              {reapplyError && (
                <p className="text-xs text-rose-400 bg-rose-500/10 p-2 rounded border border-rose-500/20">
                  {reapplyError}
                </p>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setReapplyAppId(null)}
                  disabled={isReapplying}
                  className="rounded-lg border border-white/[0.1] px-3.5 py-2 text-xs font-semibold text-zinc-300 hover:text-white"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isReapplying}
                  className="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary-hover transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {isReapplying && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  <span>Qayta topshirish</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Auth Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onSuccess={(newUser) => {
          setUser(newUser);
          setShowAuthModal(false);
          loadData(activeTab);
        }}
        title="Nomzod hisobiga kirish"
        subtitle="Topshirilgan arizalaringiz va suhbatlarni boshqarish uchun kiring"
      />
    </main>
  );
}
