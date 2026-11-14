"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import {
  Users,
  Briefcase,
  Calendar,
  Search,
  Building,
  GraduationCap,
  Loader2,
  LogIn,
  LogOut,
  AlertCircle,
  Plus,
  CheckCircle2,
  Clock,
  Eye,
  UserCheck,
  Video,
  Send,
  XCircle,
  RefreshCw,
  FileText,
  MapPin,
  ArrowRight,
} from "lucide-react";
import {
  fetchAuthMe,
  fetchEmployerDashboard,
  logoutUser,
  createEmployerOpportunity,
  fetchEmployerOpportunityApplications,
  transitionApplicationStatus,
  fetchApplicationHRDetail,
  scheduleApplicationInterview,
  issueApplicationOffer,
  AuthUser,
  EmployerDashboardMetrics,
  EmployerOpportunityApplicationItem,
  ApplicationHRDetailResponse,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";

export default function EmployerPortal() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Organization selection & dashboard data
  const [orgId, setOrgId] = useState("");
  const [dashboard, setDashboard] = useState<EmployerDashboardMetrics | null>(null);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  // New opportunity creation state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createTitle, setCreateTitle] = useState("");
  const [createKind, setCreateKind] = useState("PART_TIME_JOB");
  const [createContract, setCreateContract] = useState("LABOR_PART_TIME");
  const [createCompensation, setCreateCompensation] = useState("HOURLY");
  const [createPay, setCreatePay] = useState("35000");
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // FB-150: Employer Candidate Kanban & Application Workflow State
  // -------------------------------------------------------------------------
  const [targetOppId, setTargetOppId] = useState("");
  const [applications, setApplications] = useState<EmployerOpportunityApplicationItem[]>([]);
  const [isLoadingApps, setIsLoadingApps] = useState(false);
  const [appsError, setAppsError] = useState<string | null>(null);
  const [activeActionAppId, setActiveActionAppId] = useState<string | null>(null);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  // Modals for candidate actions
  const [interviewModalApp, setInterviewModalApp] = useState<EmployerOpportunityApplicationItem | null>(null);
  const [interviewStartsAt, setInterviewStartsAt] = useState("");
  const [interviewEndsAt, setInterviewEndsAt] = useState("");
  const [interviewMode, setInterviewMode] = useState<"ONLINE" | "IN_PERSON">("ONLINE");
  const [interviewLink, setInterviewLink] = useState("https://meet.google.com/flx-interview");
  const [isSubmittingInterview, setIsSubmittingInterview] = useState(false);
  const [interviewError, setInterviewError] = useState<string | null>(null);

  const [offerModalApp, setOfferModalApp] = useState<EmployerOpportunityApplicationItem | null>(null);
  const [offerExpiresAt, setOfferExpiresAt] = useState("");
  const [offerTermsSalary, setOfferTermsSalary] = useState("4500000");
  const [offerTermsNotes, setOfferTermsNotes] = useState("3 oylik sinov muddati bilan to‘liq stavka");
  const [isSubmittingOffer, setIsSubmittingOffer] = useState(false);
  const [offerError, setOfferError] = useState<string | null>(null);

  const [rejectModalApp, setRejectModalApp] = useState<EmployerOpportunityApplicationItem | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [isSubmittingReject, setIsSubmittingReject] = useState(false);
  const [rejectError, setRejectError] = useState<string | null>(null);

  const [detailModalAppId, setDetailModalAppId] = useState<string | null>(null);
  const [hrDetail, setHrDetail] = useState<ApplicationHRDetailResponse | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const loadDashboard = useCallback(async (targetOrgIdInput: string) => {
    if (!targetOrgIdInput.trim()) return;
    setIsLoadingDashboard(true);
    setDashboardError(null);

    try {
      const data = await fetchEmployerDashboard(targetOrgIdInput.trim());
      setDashboard(data);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 404) {
        setDashboardError("Tashkilot topilmadi yoki unga kirish huquqingiz yo'q (IDOR himoyasi).");
      } else if (status === 401) {
        setDashboardError("Sessiya muddati tugagan. Iltimos, qayta tizimga kiring.");
        setCurrentUser(null);
      } else {
        setDashboardError(err instanceof Error ? err.message : "Ma'lumotlarni yuklashda xatolik yuz berdi.");
      }
      setDashboard(null);
    } finally {
      setIsLoadingDashboard(false);
    }
  }, []);

  const loadApplications = useCallback(async (oppIdInput: string) => {
    if (!oppIdInput.trim()) return;
    setIsLoadingApps(true);
    setAppsError(null);
    setActionSuccessMsg(null);

    try {
      const res = await fetchEmployerOpportunityApplications(oppIdInput.trim());
      setApplications(res.items || []);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 404) {
        setAppsError("Vakansiya / e'lon topilmadi yoki tashkilotingizga tegishli emas.");
      } else if (status === 401) {
        setAppsError("Sessiya muddati tugagan. Iltimos, tizimga qayta kiring.");
      } else {
        setAppsError(err instanceof Error ? err.message : "Arizalarni yuklashda xatolik yuz berdi.");
      }
      setApplications([]);
    } finally {
      setIsLoadingApps(false);
    }
  }, []);

  // Load session on mount
  useEffect(() => {
    let isMounted = true;
    fetchAuthMe().then((user) => {
      if (isMounted) {
        setCurrentUser(user);
        setIsAuthLoading(false);
      }
    });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setDashboard(null);
    setDashboardError(null);
    setApplications([]);
    setTargetOppId("");
  };

  const handleLoginSuccess = (user: AuthUser) => {
    setCurrentUser(user);
    if (orgId) {
      loadDashboard(orgId);
    }
  };

  const handleCreateOpportunity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgId.trim()) {
      setCreateError("Tashkilot ID (UUID) kiritilishi shart.");
      return;
    }
    setIsCreating(true);
    setCreateError(null);
    setCreateSuccess(null);
    try {
      const payNum = Number(createPay) || 0;
      await createEmployerOpportunity({
        organization_id: orgId.trim(),
        title: createTitle.trim(),
        opportunity_kind: createKind,
        contract_type: createContract,
        compensation_type: createCompensation,
        hourly_pay: createCompensation === "HOURLY" ? payNum : undefined,
        stipend_amount: createCompensation === "STIPEND" ? payNum : undefined,
      });
      setCreateSuccess("E'lon muvaffaqiyatli qoralama (DRAFT) sifatida yaratildi!");
      setCreateTitle("");
      loadDashboard(orgId.trim());
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Yaratishda xatolik yuz berdi");
    } finally {
      setIsCreating(false);
    }
  };

  // Quick State Transition Handler (API-083)
  const handleQuickTransition = async (appId: string, toStatus: string) => {
    setActiveActionAppId(appId);
    setAppsError(null);
    try {
      await transitionApplicationStatus(appId, { to_status: toStatus });
      setActionSuccessMsg(`Ariza holati "${toStatus}" bosqichiga muvaffaqiyatli o'tkazildi.`);
      if (targetOppId) {
        await loadApplications(targetOppId);
      }
    } catch (err: unknown) {
      setAppsError(err instanceof Error ? err.message : "Bosqichni o'zgartirishda xatolik");
    } finally {
      setActiveActionAppId(null);
    }
  };

  // Submit Schedule Interview (API-085)
  const handleSubmitInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!interviewModalApp) return;
    setIsSubmittingInterview(true);
    setInterviewError(null);

    try {
      // Validate dates
      const s = new Date(interviewStartsAt);
      const end = new Date(interviewEndsAt);
      if (isNaN(s.getTime()) || isNaN(end.getTime()) || end <= s) {
        throw new Error("Suhbat tugash vaqti boshlanish vaqtidan keyin bo'lishi shart.");
      }

      await scheduleApplicationInterview(interviewModalApp.application_id, {
        starts_at: s.toISOString(),
        ends_at: end.toISOString(),
        mode: interviewMode,
        location_or_link: interviewLink.trim() || undefined,
        timezone: "Asia/Tashkent",
      });

      setActionSuccessMsg("Suhbat muvaffaqiyatli belgilandi va nomzodga bildirishnoma yuborildi!");
      setInterviewModalApp(null);
      if (targetOppId) {
        await loadApplications(targetOppId);
      }
    } catch (err: unknown) {
      setInterviewError(err instanceof Error ? err.message : "Suhbatni rejalashtirishda xatolik.");
    } finally {
      setIsSubmittingInterview(false);
    }
  };

  // Submit Issue Offer (API-086)
  const handleSubmitOffer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!offerModalApp) return;
    setIsSubmittingOffer(true);
    setOfferError(null);

    try {
      let isoExpires: string | undefined = undefined;
      if (offerExpiresAt.trim()) {
        const exp = new Date(offerExpiresAt);
        if (!isNaN(exp.getTime())) {
          isoExpires = exp.toISOString();
        }
      }

      await issueApplicationOffer(offerModalApp.application_id, {
        expires_at: isoExpires,
        terms_snapshot: {
          salary_or_stipend: offerTermsSalary,
          notes: offerTermsNotes,
          currency: "UZS",
        },
      });

      setActionSuccessMsg("Rasmiy ish taklifi (OFFER) muvaffaqiyatli yuborildi!");
      setOfferModalApp(null);
      if (targetOppId) {
        await loadApplications(targetOppId);
      }
    } catch (err: unknown) {
      setOfferError(err instanceof Error ? err.message : "Taklif yuborishda xatolik.");
    } finally {
      setIsSubmittingOffer(false);
    }
  };

  // Submit Rejection (API-083)
  const handleSubmitReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectModalApp) return;
    setIsSubmittingReject(true);
    setRejectError(null);

    try {
      await transitionApplicationStatus(rejectModalApp.application_id, {
        to_status: "REJECTED",
        reason: rejectReason.trim() || undefined,
      });

      setActionSuccessMsg("Ariza rad etildi va tegishli audit yozuvi qayd etildi.");
      setRejectModalApp(null);
      setRejectReason("");
      if (targetOppId) {
        await loadApplications(targetOppId);
      }
    } catch (err: unknown) {
      setRejectError(err instanceof Error ? err.message : "Arizani rad etishda xatolik.");
    } finally {
      setIsSubmittingReject(false);
    }
  };

  // Open HR Snapshot & History Modal (API-084)
  const handleOpenHRDetail = async (appId: string) => {
    setDetailModalAppId(appId);
    setIsLoadingDetail(true);
    setDetailError(null);
    setHrDetail(null);

    try {
      const data = await fetchApplicationHRDetail(appId);
      setHrDetail(data);
    } catch (err: unknown) {
      setDetailError(err instanceof Error ? err.message : "HR snapshot ma'lumotlarini yuklashda xatolik.");
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // Group applications into Kanban columns
  const kanbanColumns = useMemo(() => {
    const submitted: EmployerOpportunityApplicationItem[] = [];
    const reviewing: EmployerOpportunityApplicationItem[] = [];
    const shortlisted: EmployerOpportunityApplicationItem[] = [];
    const interview: EmployerOpportunityApplicationItem[] = [];
    const offered: EmployerOpportunityApplicationItem[] = [];
    const rejected: EmployerOpportunityApplicationItem[] = [];

    applications.forEach((app) => {
      switch (app.status) {
        case "SUBMITTED":
          submitted.push(app);
          break;
        case "REVIEWING":
          reviewing.push(app);
          break;
        case "SHORTLISTED":
          shortlisted.push(app);
          break;
        case "INVITED_TO_INTERVIEW":
          interview.push(app);
          break;
        case "OFFER_PENDING":
        case "OFFERED":
        case "ACCEPTED":
          offered.push(app);
          break;
        case "REJECTED":
        case "WITHDRAWN":
          rejected.push(app);
          break;
        default:
          submitted.push(app);
          break;
      }
    });

    return [
      {
        id: "SUBMITTED",
        title: "Yangi arizalar",
        statusBadge: "bg-blue-500/10 text-blue-400 border-blue-500/20",
        icon: Clock,
        items: submitted,
      },
      {
        id: "REVIEWING",
        title: "Ko‘rib chiqilmoqda",
        statusBadge: "bg-amber-500/10 text-amber-400 border-amber-500/20",
        icon: Eye,
        items: reviewing,
      },
      {
        id: "SHORTLISTED",
        title: "Saralangan",
        statusBadge: "bg-purple-500/10 text-purple-400 border-purple-500/20",
        icon: UserCheck,
        items: shortlisted,
      },
      {
        id: "INTERVIEW",
        title: "Suhbat belgilangan",
        statusBadge: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
        icon: Video,
        items: interview,
      },
      {
        id: "OFFER",
        title: "Taklif yuborilgan",
        statusBadge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
        icon: Send,
        items: offered,
      },
      {
        id: "REJECTED",
        title: "Rad etilgan",
        statusBadge: "bg-rose-500/10 text-rose-400 border-rose-500/20",
        icon: XCircle,
        items: rejected,
      },
    ];
  }, [applications]);

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* AUTH STATUS & HEADER BAR */}
      <section className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-5 shadow-lg">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                Ish Beruvchi Portali
              </span>
              <span className="text-zinc-500 text-xs">• API-068 / API-082-086 / CAP-015</span>
              {currentUser ? (
                <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                  <span>Kirilgan: {currentUser.user_id.slice(0, 8)}...</span>
                  <span className="text-zinc-500">({currentUser.roles.join(", ")})</span>
                </span>
              ) : (
                <span className="text-[11px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                  Avtorizatsiyadan o‘tilmagan
                </span>
              )}
            </div>
            <h1 className="font-heading text-lg md:text-xl font-bold text-zinc-100">
              Tashkilot HR va Vakansiyalar Boshqaruvi
            </h1>
            <p className="text-xs text-zinc-400">
              Haqiqiy backend orqali tashkilot statistikasi, vakansiyalar va nomzodlar bosqichlari (Kanban) monitoringi.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {isAuthLoading ? (
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Yuklanmoqda...</span>
              </div>
            ) : currentUser ? (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setIsCreateModalOpen(true);
                    setCreateSuccess(null);
                    setCreateError(null);
                  }}
                  className="px-3.5 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-primary/20"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Yangi e’lon joylash</span>
                </button>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="px-3.5 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-rose-300 hover:text-rose-200 transition-all flex items-center gap-1.5"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Chiqish</span>
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setIsLoginModalOpen(true)}
                className="px-3.5 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-primary/20"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Tizimga kirish</span>
              </button>
            )}
          </div>
        </div>
      </section>

      {/* UNAUTHENTICATED STATE */}
      {!currentUser && !isAuthLoading && (
        <section className="w-full bg-surface-card/60 border border-white/[0.08] rounded-xl p-8 flex flex-col items-center justify-center text-center gap-4 py-16">
          <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <Building className="w-7 h-7" />
          </div>
          <div className="flex flex-col gap-1 max-w-md">
            <h2 className="text-base md:text-lg font-heading font-semibold text-white">
              Tashkilot ma’lumotlariga kirish uchun tizimga kiring
            </h2>
            <p className="text-xs text-zinc-400">
              Ushbu bo‘lim tashkilot HR vakillari va rahbarlari uchun mo‘ljallangan. Tashkilotingiz tahlillari va nomzodlarini boshqarish uchun tizimga kiring.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsLoginModalOpen(true)}
            className="mt-2 px-5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-2 shadow-lg shadow-primary/25"
          >
            <LogIn className="w-4 h-4" />
            <span>HR hisobi bilan kirish</span>
          </button>
        </section>
      )}

      {/* AUTHENTICATED WORKSPACE */}
      {currentUser && (
        <div className="flex flex-col gap-6">
          {/* ORG ID SELECTOR */}
          <section className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 shadow-md">
            <div className="flex flex-1 items-center gap-2">
              <label htmlFor="orgIdInput" className="text-xs font-medium text-zinc-300 shrink-0">
                Tashkilot ID (UUID):
              </label>
              <input
                id="orgIdInput"
                type="text"
                value={orgId}
                onChange={(e) => setOrgId(e.target.value)}
                placeholder="masalan: e1a54054-0eb7-4eb2-a7d1-e63013d39ea3"
                className="w-full max-w-md px-3 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-xs font-mono text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50"
              />
            </div>
            <button
              type="button"
              disabled={isLoadingDashboard || !orgId.trim()}
              onClick={() => loadDashboard(orgId)}
              className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center justify-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed shadow"
            >
              {isLoadingDashboard ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Yuklanmoqda...</span>
                </>
              ) : (
                <>
                  <Search className="w-3.5 h-3.5" />
                  <span>Tahlillarni yuklash</span>
                </>
              )}
            </button>
          </section>

          {/* DASHBOARD ERROR MESSAGE */}
          {dashboardError && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <div className="flex flex-col gap-0.5">
                <span className="font-semibold">Kirish rad etildi / Xatolik:</span>
                <span>{dashboardError}</span>
              </div>
            </div>
          )}

          {/* METRICS DISPLAY */}
          {dashboard?.metrics && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* VACANCIES / OPPORTUNITIES */}
              <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-2">
                <div className="flex items-center justify-between text-zinc-400">
                  <span className="text-xs font-medium">Vakansiyalar</span>
                  <Briefcase className="w-4 h-4 text-primary" />
                </div>
                <div className="text-2xl font-bold font-mono text-white">
                  {dashboard.metrics.opportunities.total}
                </div>
                <div className="text-[11px] text-zinc-400 flex flex-wrap gap-2">
                  <span className="text-emerald-400 font-medium">
                    {dashboard.metrics.opportunities.published} faol
                  </span>
                  <span>•</span>
                  <span>{dashboard.metrics.opportunities.draft} qoralama</span>
                </div>
              </div>

              {/* APPLICATIONS */}
              <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-2">
                <div className="flex items-center justify-between text-zinc-400">
                  <span className="text-xs font-medium">Nomzodlar arizalari</span>
                  <Users className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold font-mono text-white">
                  {dashboard.metrics.applications.total}
                </div>
                <div className="text-[11px] text-zinc-400 flex flex-wrap gap-2">
                  <span className="text-amber-400 font-medium">
                    {dashboard.metrics.applications.pending} kutilmoqda
                  </span>
                  <span>•</span>
                  <span className="text-emerald-400 font-medium">
                    {dashboard.metrics.applications.offered} taklif qilingan
                  </span>
                </div>
              </div>

              {/* INTERVIEWS */}
              <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-2">
                <div className="flex items-center justify-between text-zinc-400">
                  <span className="text-xs font-medium">Suhbatlar</span>
                  <Calendar className="w-4 h-4 text-amber-400" />
                </div>
                <div className="text-2xl font-bold font-mono text-white">
                  {dashboard.metrics.interviews.total}
                </div>
                <div className="text-[11px] text-zinc-400 flex flex-wrap gap-2">
                  <span className="text-blue-400 font-medium">
                    {dashboard.metrics.interviews.scheduled} rejalashtirilgan
                  </span>
                  <span>•</span>
                  <span>{dashboard.metrics.interviews.completed} yakunlangan</span>
                </div>
              </div>

              {/* ENGAGEMENTS */}
              <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-2">
                <div className="flex items-center justify-between text-zinc-400">
                  <span className="text-xs font-medium">Stajirovkalar (Dual ta&apos;lim)</span>
                  <GraduationCap className="w-4 h-4 text-purple-400" />
                </div>
                <div className="text-2xl font-bold font-mono text-white">
                  {dashboard.metrics.engagements.total}
                </div>
                <div className="text-[11px] text-zinc-400 flex flex-wrap gap-2">
                  <span className="text-emerald-400 font-medium">
                    {dashboard.metrics.engagements.active} faol
                  </span>
                  <span>•</span>
                  <span>{dashboard.metrics.engagements.completed} yakunlangan</span>
                </div>
              </div>
            </div>
          )}

          {/* ----------------------------------------------------------------- */}
          {/* FB-150: NOMZODLAR BOSQICHLARI VA KANBAN BOSHQARUVI */}
          {/* ----------------------------------------------------------------- */}
          <section className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-5 flex flex-col gap-4 shadow-lg">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Nomzodlar Kanbani
                  </span>
                  <span className="text-zinc-500 text-xs">• API-082, 083, 084, 085, 086</span>
                </div>
                <h2 className="font-heading text-base md:text-lg font-bold text-white">
                  Arizalarni Bosqichma-bosqich Boshqarish va Suhbat Belgilash
                </h2>
                <p className="text-xs text-zinc-400">
                  Vakansiyaga topshirilgan barcha nomzodlarni saralash, suhbat tayinlash va rasmiy takliflar (Offer) yuborish.
                </p>
              </div>

              {/* Opportunity Selector */}
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <input
                    type="text"
                    value={targetOppId}
                    onChange={(e) => setTargetOppId(e.target.value)}
                    placeholder="Vakansiya ID (UUID)"
                    className="w-64 px-3 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-xs font-mono text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50"
                  />
                </div>
                <button
                  type="button"
                  disabled={isLoadingApps || !targetOppId.trim()}
                  onClick={() => loadApplications(targetOppId)}
                  className="px-3.5 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed shadow"
                >
                  {isLoadingApps ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Yuklanmoqda...</span>
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Nomzodlarni yuklash</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Action success message */}
            {actionSuccessMsg && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{actionSuccessMsg}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setActionSuccessMsg(null)}
                  className="text-emerald-400 hover:text-white text-xs font-bold p-1"
                >
                  ✕
                </button>
              </div>
            )}

            {/* Kanban Error Message */}
            {appsError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div className="flex flex-col gap-0.5">
                  <span className="font-semibold">Xatolik yuz berdi:</span>
                  <span>{appsError}</span>
                </div>
              </div>
            )}

            {/* Empty or Loaded Kanban Board */}
            {!targetOppId.trim() ? (
              <div className="p-8 text-center text-zinc-400 text-xs flex flex-col items-center justify-center gap-2 border border-dashed border-white/[0.08] rounded-xl my-4">
                <Users className="w-8 h-8 text-zinc-500" />
                <span>Nomzodlar jadvalini ko‘rish uchun yuqoriga Vakansiya ID (UUID) kiriting va &quot;Nomzodlarni yuklash&quot; tugmasini bosing.</span>
              </div>
            ) : isLoadingApps ? (
              <div className="p-12 flex flex-col items-center justify-center gap-2 text-zinc-400 text-xs">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
                <span>Nomzodlar arizalari yuklanmoqda...</span>
              </div>
            ) : applications.length === 0 ? (
              <div className="p-8 text-center text-zinc-400 text-xs flex flex-col items-center justify-center gap-2 border border-dashed border-white/[0.08] rounded-xl my-4">
                <Briefcase className="w-8 h-8 text-zinc-500" />
                <span>Ushbu vakansiyaga hozircha hech qanday nomzod ariza topshirmagan.</span>
              </div>
            ) : (
              /* KANBAN BOARD COLUMNS */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5 overflow-x-auto pb-4 pt-2">
                {kanbanColumns.map((col) => {
                  const Icon = col.icon;
                  return (
                    <div
                      key={col.id}
                      className="flex flex-col bg-[#0f0f11] border border-white/[0.06] rounded-xl p-3 min-w-[220px]"
                    >
                      {/* Column Header */}
                      <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-white/[0.06]">
                        <div className="flex items-center gap-1.5">
                          <Icon className="w-3.5 h-3.5 text-zinc-400" />
                          <span className="text-xs font-semibold text-zinc-200">{col.title}</span>
                        </div>
                        <span className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded-full border ${col.statusBadge}`}>
                          {col.items.length}
                        </span>
                      </div>

                      {/* Card Items */}
                      <div className="flex flex-col gap-2.5 flex-1">
                        {col.items.length === 0 ? (
                          <div className="py-6 text-center text-zinc-600 text-[11px]">
                            Arizalar yo‘q
                          </div>
                        ) : (
                          col.items.map((app) => (
                            <div
                              key={app.application_id}
                              className="bg-[#141416] hover:bg-[#18181b] border border-white/[0.08] rounded-lg p-3 flex flex-col gap-2 transition-all shadow-sm"
                            >
                              {/* Candidate header info */}
                              <div className="flex items-center justify-between gap-1">
                                <span className="text-[11px] font-mono text-zinc-300 font-medium">
                                  #{app.candidate_id.slice(0, 8)}
                                </span>
                                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-white/[0.04]">
                                  #{app.attempt_no}-urinish
                                </span>
                              </div>

                              {/* Headline / Region */}
                              {app.headline && (
                                <p className="text-xs font-medium text-zinc-100 line-clamp-1">
                                  {app.headline}
                                </p>
                              )}
                              {app.region && (
                                <div className="flex items-center gap-1 text-[11px] text-zinc-400">
                                  <MapPin className="w-3 h-3 text-zinc-500" />
                                  <span>{app.region}</span>
                                </div>
                              )}

                              {/* Date & Schedule result */}
                              <div className="text-[10px] text-zinc-500 font-mono flex items-center justify-between pt-1 border-t border-white/[0.04]">
                                <span>{new Date(app.submitted_at || app.created_at).toLocaleDateString()}</span>
                                {app.schedule_result && (
                                  <span className="text-[10px] font-mono text-emerald-400">
                                    {app.schedule_result}
                                  </span>
                                )}
                              </div>

                              {/* Action Buttons */}
                              <div className="flex flex-col gap-1.5 pt-2 border-t border-white/[0.06]">
                                {/* Status-dependent buttons */}
                                {app.status === "SUBMITTED" && (
                                  <div className="grid grid-cols-2 gap-1.5">
                                    <button
                                      type="button"
                                      disabled={activeActionAppId === app.application_id}
                                      onClick={() => handleQuickTransition(app.application_id, "REVIEWING")}
                                      className="px-2 py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 text-amber-300 text-[11px] font-medium flex items-center justify-center gap-1 transition-all"
                                    >
                                      <Eye className="w-3 h-3" />
                                      <span>Ko‘rish</span>
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setRejectModalApp(app);
                                        setRejectReason("");
                                        setRejectError(null);
                                      }}
                                      className="px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-300 text-[11px] font-medium flex items-center justify-center gap-1 transition-all"
                                    >
                                      <XCircle className="w-3 h-3" />
                                      <span>Rad</span>
                                    </button>
                                  </div>
                                )}

                                {app.status === "REVIEWING" && (
                                  <div className="flex flex-col gap-1.5">
                                    <div className="grid grid-cols-2 gap-1.5">
                                      <button
                                        type="button"
                                        disabled={activeActionAppId === app.application_id}
                                        onClick={() => handleQuickTransition(app.application_id, "SHORTLISTED")}
                                        className="px-2 py-1 rounded bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 text-purple-300 text-[11px] font-medium flex items-center justify-center gap-1 transition-all"
                                      >
                                        <UserCheck className="w-3 h-3" />
                                        <span>Saralash</span>
                                      </button>
                                      <button
                                        type="button"
                                        onClick={() => {
                                          setRejectModalApp(app);
                                          setRejectReason("");
                                          setRejectError(null);
                                        }}
                                        className="px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-300 text-[11px] font-medium flex items-center justify-center gap-1 transition-all"
                                      >
                                        <XCircle className="w-3 h-3" />
                                        <span>Rad</span>
                                      </button>
                                    </div>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setInterviewModalApp(app);
                                        setInterviewStartsAt("");
                                        setInterviewEndsAt("");
                                        setInterviewError(null);
                                      }}
                                      className="w-full px-2 py-1 rounded bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 text-indigo-300 text-[11px] font-medium flex items-center justify-center gap-1 transition-all"
                                    >
                                      <Video className="w-3 h-3" />
                                      <span>Suhbat belgilash</span>
                                    </button>
                                  </div>
                                )}

                                {app.status === "SHORTLISTED" && (
                                  <div className="flex flex-col gap-1.5">
                                    <div className="grid grid-cols-2 gap-1.5">
                                      <button
                                        type="button"
                                        onClick={() => {
                                          setInterviewModalApp(app);
                                          setInterviewStartsAt("");
                                          setInterviewEndsAt("");
                                          setInterviewError(null);
                                        }}
                                        className="px-2 py-1 rounded bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 text-indigo-300 text-[11px] font-medium flex items-center justify-center gap-1 transition-all"
                                      >
                                        <Video className="w-3 h-3" />
                                        <span>Suhbat</span>
                                      </button>
                                      <button
                                        type="button"
                                        onClick={() => {
                                          setOfferModalApp(app);
                                          setOfferExpiresAt("");
                                          setOfferError(null);
                                        }}
                                        className="px-2 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 text-emerald-300 text-[11px] font-medium flex items-center justify-center gap-1 transition-all"
                                      >
                                        <Send className="w-3 h-3" />
                                        <span>Offer</span>
                                      </button>
                                    </div>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setRejectModalApp(app);
                                        setRejectReason("");
                                        setRejectError(null);
                                      }}
                                      className="w-full px-2 py-0.5 rounded bg-surface hover:bg-surface-high border border-white/[0.06] text-rose-400 text-[10px] font-medium"
                                    >
                                      Rad etish
                                    </button>
                                  </div>
                                )}

                                {(app.status === "INVITED_TO_INTERVIEW" || (app.status as string) === "INTERVIEW_SCHEDULED") && (
                                  <div className="grid grid-cols-2 gap-1.5">
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setOfferModalApp(app);
                                        setOfferExpiresAt("");
                                        setOfferError(null);
                                      }}
                                      className="px-2 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 text-emerald-300 text-[11px] font-medium flex items-center justify-center gap-1 transition-all"
                                    >
                                      <Send className="w-3 h-3" />
                                      <span>Offer</span>
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setRejectModalApp(app);
                                        setRejectReason("");
                                        setRejectError(null);
                                      }}
                                      className="px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-300 text-[11px] font-medium flex items-center justify-center gap-1 transition-all"
                                    >
                                      <XCircle className="w-3 h-3" />
                                      <span>Rad</span>
                                    </button>
                                  </div>
                                )}

                                {/* Always visible: HR Snapshot & Audit trail */}
                                <button
                                  type="button"
                                  onClick={() => handleOpenHRDetail(app.application_id)}
                                  className="w-full mt-0.5 px-2 py-1 rounded bg-surface hover:bg-surface-high border border-white/[0.06] text-zinc-300 text-[11px] font-medium flex items-center justify-center gap-1 transition-all"
                                >
                                  <FileText className="w-3 h-3 text-zinc-400" />
                                  <span>Tafsilotlar</span>
                                </button>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      )}

      {/* LOGIN MODAL */}
      <AuthModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onSuccess={handleLoginSuccess}
        title="Ish Beruvchi Tizimiga Kirish"
        subtitle="Tashkilot HR yoki Rahbar hisob ma’lumotlaringizni kiriting"
      />

      {/* CREATE OPPORTUNITY MODAL */}
      {isCreateModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-opportunity-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-lg rounded-2xl border border-white/[0.1] bg-[#121214] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <h2
                id="create-opportunity-title"
                className="font-heading text-lg font-bold text-white"
              >
                Yangi Vakansiya / E’lon Yaratish
              </h2>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className="rounded-lg p-1 text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {createSuccess ? (
              <div className="py-6 text-center">
                <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-400" />
                <h3 className="mt-4 text-base font-bold text-white">{createSuccess}</h3>
                <p className="mt-2 text-xs text-zinc-400">
                  E’lon qoralama (DRAFT) holatida saqlandi. Moderatsiyadan so‘ng e’lon qilinadi.
                </p>
                <div className="mt-6">
                  <button
                    type="button"
                    onClick={() => {
                      setIsCreateModalOpen(false);
                      setCreateSuccess(null);
                    }}
                    className="rounded-lg bg-primary px-5 py-2 text-xs font-semibold text-white hover:bg-primary-hover"
                  >
                    Tushunarli
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCreateOpportunity} className="mt-4 space-y-4">
                <div>
                  <label htmlFor="create-title" className="block text-xs font-semibold text-zinc-300">
                    Vakansiya / Lavozim nomi
                  </label>
                  <input
                    id="create-title"
                    type="text"
                    required
                    value={createTitle}
                    onChange={(e) => setCreateTitle(e.target.value)}
                    placeholder="masalan: Junior Backend Dasturchi"
                    className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-3 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="create-kind" className="block text-xs font-semibold text-zinc-300">
                      Imkoniyat turi
                    </label>
                    <select
                      id="create-kind"
                      value={createKind}
                      onChange={(e) => {
                        const val = e.target.value;
                        setCreateKind(val);
                        if (val === "PART_TIME_JOB") {
                          setCreateContract("LABOR_PART_TIME");
                        } else {
                          setCreateContract("INTERNSHIP_AGREEMENT");
                        }
                      }}
                      className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-2.5 text-xs text-zinc-200 focus:border-primary focus:outline-none"
                    >
                      <option value="PART_TIME_JOB">Yarim stavka ish</option>
                      <option value="GENERAL_INTERNSHIP">Amaliyot / Stajirovka</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor="create-comp" className="block text-xs font-semibold text-zinc-300">
                      To‘lov formati
                    </label>
                    <select
                      id="create-comp"
                      value={createCompensation}
                      onChange={(e) => setCreateCompensation(e.target.value)}
                      className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-2.5 text-xs text-zinc-200 focus:border-primary focus:outline-none"
                    >
                      <option value="HOURLY">Soatbay to‘lov</option>
                      <option value="STIPEND">Oylik stipendiya</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label htmlFor="create-pay" className="block text-xs font-semibold text-zinc-300">
                    {createCompensation === "HOURLY" ? "Soatbay stavka (UZS / soat)" : "Oylik miqdor (UZS)"}
                  </label>
                  <input
                    id="create-pay"
                    type="number"
                    min="1"
                    required
                    value={createPay}
                    onChange={(e) => setCreatePay(e.target.value)}
                    placeholder="35000"
                    className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-3 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none"
                  />
                </div>

                {createError && (
                  <div
                    role="alert"
                    className="rounded-xl border border-rose-500/20 bg-rose-500/[0.05] p-3 text-xs text-rose-300"
                  >
                    {createError}
                  </div>
                )}

                <div className="flex items-center justify-end gap-3 pt-3">
                  <button
                    type="button"
                    onClick={() => setIsCreateModalOpen(false)}
                    className="rounded-lg border border-white/[0.1] px-4 py-2 text-xs font-semibold text-zinc-300 hover:border-zinc-500"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="submit"
                    disabled={isCreating || !createTitle.trim()}
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-xs font-semibold text-white hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isCreating ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Yaratilmoqda...
                      </>
                    ) : (
                      <>
                        <Plus className="h-3.5 w-3.5" /> E’lonni yaratish
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* INTERVIEW SCHEDULING MODAL (API-085) */}
      {/* ----------------------------------------------------------------- */}
      {interviewModalApp && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-lg rounded-2xl border border-white/[0.1] bg-[#121214] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center gap-2">
                <Video className="w-5 h-5 text-indigo-400" />
                <h3 className="font-heading text-base font-bold text-white">
                  Suhbat Belgilash (API-085)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setInterviewModalApp(null)}
                className="rounded-lg p-1 text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitInterview} className="mt-4 space-y-4">
              <div className="text-xs text-zinc-400">
                Nomzod: <span className="font-mono text-zinc-200">#{interviewModalApp.candidate_id.slice(0, 12)}...</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-300">
                    Boshlanish vaqti
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={interviewStartsAt}
                    onChange={(e) => setInterviewStartsAt(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-2.5 text-xs text-zinc-100 focus:border-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-300">
                    Tugash vaqti
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={interviewEndsAt}
                    onChange={(e) => setInterviewEndsAt(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-2.5 text-xs text-zinc-100 focus:border-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-300">
                    Suhbat formati
                  </label>
                  <select
                    value={interviewMode}
                    onChange={(e) => setInterviewMode(e.target.value as "ONLINE" | "IN_PERSON")}
                    className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-2.5 text-xs text-zinc-200 focus:border-primary focus:outline-none"
                  >
                    <option value="ONLINE">Masofaviy (Online)</option>
                    <option value="IN_PERSON">Ofisda (Yuzma-yuz)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-300">
                    Vaqt mintaqasi
                  </label>
                  <input
                    type="text"
                    disabled
                    value="Asia/Tashkent (UTC+5)"
                    className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest/50 p-2.5 text-xs text-zinc-400 cursor-not-allowed"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300">
                  {interviewMode === "ONLINE" ? "Havola (Google Meet / Zoom)" : "Ofis manzili / Xona"}
                </label>
                <input
                  type="text"
                  value={interviewLink}
                  onChange={(e) => setInterviewLink(e.target.value)}
                  placeholder="https://meet.google.com/..."
                  className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-2.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none"
                />
              </div>

              {interviewError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                  {interviewError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setInterviewModalApp(null)}
                  className="rounded-lg border border-white/[0.1] px-4 py-2 text-xs font-semibold text-zinc-300 hover:border-zinc-500"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingInterview || !interviewStartsAt || !interviewEndsAt}
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 px-5 py-2 text-xs font-semibold text-white disabled:opacity-50"
                >
                  {isSubmittingInterview ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Belgilanmoqda...</span>
                    </>
                  ) : (
                    <>
                      <Video className="w-3.5 h-3.5" />
                      <span>Suhbatni tasdiqlash</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* ISSUE OFFER MODAL (API-086) */}
      {/* ----------------------------------------------------------------- */}
      {offerModalApp && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-lg rounded-2xl border border-white/[0.1] bg-[#121214] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center gap-2">
                <Send className="w-5 h-5 text-emerald-400" />
                <h3 className="font-heading text-base font-bold text-white">
                  Rasmiy Ish Taklifi (Offer) Yuborish (API-086)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setOfferModalApp(null)}
                className="rounded-lg p-1 text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitOffer} className="mt-4 space-y-4">
              <div className="text-xs text-zinc-400">
                Nomzod: <span className="font-mono text-zinc-200">#{offerModalApp.candidate_id.slice(0, 12)}...</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300">
                  Taklif qilingan oylik ish haqi / stipendiya (UZS)
                </label>
                <input
                  type="text"
                  required
                  value={offerTermsSalary}
                  onChange={(e) => setOfferTermsSalary(e.target.value)}
                  placeholder="4500000"
                  className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-2.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300">
                  Taklif amal qilish muddati (ixtiyoriy)
                </label>
                <input
                  type="datetime-local"
                  value={offerExpiresAt}
                  onChange={(e) => setOfferExpiresAt(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-2.5 text-xs text-zinc-100 focus:border-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300">
                  Qo‘shimcha shartlar va izohlar
                </label>
                <textarea
                  rows={3}
                  value={offerTermsNotes}
                  onChange={(e) => setOfferTermsNotes(e.target.value)}
                  placeholder="Masalan: 3 oylik sinov muddati bilan to‘liq stavka..."
                  className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-2.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none resize-none"
                />
              </div>

              {offerError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                  {offerError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setOfferModalApp(null)}
                  className="rounded-lg border border-white/[0.1] px-4 py-2 text-xs font-semibold text-zinc-300 hover:border-zinc-500"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingOffer}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 px-5 py-2 text-xs font-semibold text-white disabled:opacity-50"
                >
                  {isSubmittingOffer ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Yuborilmoqda...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Taklifni yuborish</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* REJECT MODAL (API-083) */}
      {/* ----------------------------------------------------------------- */}
      {rejectModalApp && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-md rounded-2xl border border-white/[0.1] bg-[#121214] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center gap-2">
                <XCircle className="w-5 h-5 text-rose-400" />
                <h3 className="font-heading text-base font-bold text-white">
                  Arizani Rad Etish (API-083)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setRejectModalApp(null)}
                className="rounded-lg p-1 text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitReject} className="mt-4 space-y-4">
              <div className="text-xs text-zinc-400">
                Arizachi: <span className="font-mono text-zinc-200">#{rejectModalApp.candidate_id.slice(0, 12)}...</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300">
                  Rad etish sababi (ixtiyoriy)
                </label>
                <textarea
                  rows={3}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="masalan: Malaka talablari to‘liq mos kelmadi..."
                  className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-2.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none resize-none"
                />
              </div>

              {rejectError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                  {rejectError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setRejectModalApp(null)}
                  className="rounded-lg border border-white/[0.1] px-4 py-2 text-xs font-semibold text-zinc-300 hover:border-zinc-500"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingReject}
                  className="inline-flex items-center gap-2 rounded-lg bg-rose-600 hover:bg-rose-500 px-5 py-2 text-xs font-semibold text-white disabled:opacity-50"
                >
                  {isSubmittingReject ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Rad etilmoqda...</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Rad etishni tasdiqlash</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* HR SNAPSHOT & AUDIT LOG MODAL (API-084) */}
      {/* ----------------------------------------------------------------- */}
      {detailModalAppId && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-xl max-h-[85vh] overflow-y-auto rounded-2xl border border-white/[0.1] bg-[#121214] p-6 shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary" />
                <h3 className="font-heading text-base font-bold text-white">
                  Nomzod HR Snapshot & Audit Tarixi (API-084)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setDetailModalAppId(null)}
                className="rounded-lg p-1 text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {isLoadingDetail ? (
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-xs text-zinc-400">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
                <span>Ma&apos;lumotlar yuklanmoqda...</span>
              </div>
            ) : detailError ? (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                {detailError}
              </div>
            ) : hrDetail ? (
              <div className="flex flex-col gap-4">
                {/* Status overview */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs bg-surface p-3 rounded-xl border border-white/[0.06]">
                  <div>
                    <span className="text-zinc-500 block text-[10px]">Holat:</span>
                    <span className="font-semibold text-emerald-400">{hrDetail.status}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block text-[10px]">Versiya:</span>
                    <span className="font-mono text-zinc-300">v{hrDetail.version}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block text-[10px]">Urinish:</span>
                    <span className="font-mono text-zinc-300">#{hrDetail.attempt?.attempt_no ?? 1}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block text-[10px]">Topshirilgan:</span>
                    <span className="font-mono text-zinc-300">
                      {hrDetail.attempt?.submitted_at ? new Date(hrDetail.attempt.submitted_at).toLocaleDateString() : "—"}
                    </span>
                  </div>
                </div>

                {/* Candidate snapshot */}
                <div className="flex flex-col gap-1.5">
                  <h4 className="text-xs font-semibold text-zinc-300">Ariza topshirilgan vaqtdagi Snapshot:</h4>
                  <pre className="p-3 rounded-xl bg-surface-lowest border border-white/[0.06] text-[11px] font-mono text-zinc-300 overflow-x-auto max-h-48">
                    {JSON.stringify(hrDetail.attempt?.profile_snapshot || hrDetail.snapshot || {}, null, 2)}
                  </pre>
                </div>

                {/* Audit events trail */}
                <div className="flex flex-col gap-2">
                  <h4 className="text-xs font-semibold text-zinc-300">O&apos;zgarishlar Tarixi (Audit Log):</h4>
                  <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
                    {hrDetail.events.length === 0 ? (
                      <span className="text-zinc-500 text-xs">Hodisalar mavjud emas</span>
                    ) : (
                      hrDetail.events.map((ev) => (
                        <div
                          key={ev.id}
                          className="flex items-center justify-between text-xs p-2 rounded-lg bg-surface border border-white/[0.04]"
                        >
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono text-zinc-400">{ev.from_status || "START"}</span>
                            <ArrowRight className="w-3 h-3 text-zinc-600" />
                            <span className="font-semibold text-primary">{ev.to_status}</span>
                            {ev.reason && (
                              <span className="text-[11px] text-zinc-400 italic">({ev.reason})</span>
                            )}
                          </div>
                          <span className="text-[10px] font-mono text-zinc-500">
                            {new Date(ev.occurred_at).toLocaleString()}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            ) : null}

            <div className="flex justify-end pt-2 border-t border-white/[0.08]">
              <button
                type="button"
                onClick={() => setDetailModalAppId(null)}
                className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300"
              >
                Yopish
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
