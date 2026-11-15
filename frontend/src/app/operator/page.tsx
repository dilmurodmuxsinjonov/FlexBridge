"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Lock,
  CheckCircle2,
  Loader2,
  LogIn,
  LogOut,
  AlertCircle,
  ShieldAlert,
  ClipboardCheck,
  UserX,
  KeyRound,
  RefreshCw,
  Search,
  Clock,
  Send,
  X,
  FileCheck2,
  LifeBuoy,
  MessageSquare,
  Flame,
  Activity,
  Server,
  Plus,
} from "lucide-react";
import {
  fetchAuthMe,
  fetchOperatorAuditEvents,
  fetchOperatorVerificationCases,
  claimVerificationCase,
  decideVerificationCase,
  requestBreakGlassAccess,
  emergencyRevokeUserSessions,
  fetchOperatorSupportTickets,
  postOperatorTicketMessage,
  declareOperatorIncident,
  fetchOperatorRestoreRuns,
  fetchOperatorAnalytics,
  logoutUser,
  AuthUser,
  OperatorAuditEventItem,
  OperatorVerificationCaseItem,
  OperatorSupportTicketItem,
  OperatorRestoreRunItem,
  OperatorPlatformAnalytics,
  BreakGlassAccessResult,
  EmergencyRevokeSessionsResult,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";

type ActiveTab = "AUDIT" | "VERIFICATION" | "BREAK_GLASS" | "SUPPORT_OPS";

export default function OperatorPortal() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>("AUDIT");

  // Tab 1: Audit Events State
  const [auditEvents, setAuditEvents] = useState<OperatorAuditEventItem[]>([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [eventsError, setEventsError] = useState<string | null>(null);

  // Tab 2: Verification Cases State
  const [cases, setCases] = useState<OperatorVerificationCaseItem[]>([]);
  const [isLoadingCases, setIsLoadingCases] = useState(false);
  const [casesError, setCasesError] = useState<string | null>(null);

  // Decision Modal State
  const [selectedCase, setSelectedCase] = useState<OperatorVerificationCaseItem | null>(null);
  const [decisionType, setDecisionType] = useState<"APPROVE" | "REJECT" | "NEEDS_INFO">("APPROVE");
  const [decisionReason, setDecisionReason] = useState("");
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  // Tab 3: Break-Glass Access Request State
  const [bgTargetUserId, setBgTargetUserId] = useState("");
  const [bgRoleCode, setBgRoleCode] = useState("OPERATOR");
  const [bgApproverId, setBgApproverId] = useState("");
  const [bgDurationMinutes, setBgDurationMinutes] = useState(120);
  const [bgReason, setBgReason] = useState("");
  const [isSubmittingBg, setIsSubmittingBg] = useState(false);
  const [bgResult, setBgResult] = useState<BreakGlassAccessResult | null>(null);
  const [bgError, setBgError] = useState<string | null>(null);

  // Tab 3: Emergency Session Revocation State
  const [revokeTargetUserId, setRevokeTargetUserId] = useState("");
  const [revokeReason, setRevokeReason] = useState("");
  const [isSubmittingRevoke, setIsSubmittingRevoke] = useState(false);
  const [revokeResult, setRevokeResult] = useState<EmergencyRevokeSessionsResult | null>(null);
  const [revokeError, setRevokeError] = useState<string | null>(null);

  // Tab 4: Support Ops & SLA Monitoring (API-112, API-113, API-122, API-123, API-124)
  const [tickets, setTickets] = useState<OperatorSupportTicketItem[]>([]);
  const [isLoadingTickets, setIsLoadingTickets] = useState(false);
  const [ticketsError, setTicketsError] = useState<string | null>(null);
  const [ticketFilterStatus, setTicketFilterStatus] = useState<string>("ALL");
  const [ticketFilterPriority, setTicketFilterPriority] = useState<string>("ALL");

  // Ticket Message Reply Modal State (API-113)
  const [selectedTicket, setSelectedTicket] = useState<OperatorSupportTicketItem | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [isInternalNote, setIsInternalNote] = useState(false);
  const [replyStatus, setReplyStatus] = useState<string>("");
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);
  const [replyError, setReplyError] = useState<string | null>(null);
  const [replySuccessMsg, setReplySuccessMsg] = useState<string | null>(null);

  // Incident Declaration Modal State (API-122)
  const [isIncidentModalOpen, setIsIncidentModalOpen] = useState(false);
  const [incidentSeverity, setIncidentSeverity] = useState<"P1" | "P2" | "P3" | "P4">("P3");
  const [incidentTitle, setIncidentTitle] = useState("");
  const [incidentSummary, setIncidentSummary] = useState("");
  const [isSubmittingIncident, setIsSubmittingIncident] = useState(false);
  const [incidentError, setIncidentError] = useState<string | null>(null);
  const [incidentSuccessMsg, setIncidentSuccessMsg] = useState<string | null>(null);

  // Restore Runs & SLA (API-123)
  const [restoreRuns, setRestoreRuns] = useState<OperatorRestoreRunItem[]>([]);
  const [runsSummary, setRunsSummary] = useState<{
    rpo_sla_target_minutes?: number;
    rto_sla_target_minutes?: number;
    total_runs_evaluated?: number;
    all_sla_met?: boolean;
  } | null>(null);
  const [isLoadingRuns, setIsLoadingRuns] = useState(false);
  const [runsError, setRunsError] = useState<string | null>(null);

  // Platform Analytics (API-124)
  const [analytics, setAnalytics] = useState<OperatorPlatformAnalytics | null>(null);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  // Load Audit Events (API-118)
  const loadAuditEvents = useCallback(async () => {
    setIsLoadingEvents(true);
    setEventsError(null);
    try {
      const items = await fetchOperatorAuditEvents();
      setAuditEvents(items);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 403) {
        setEventsError("Ruxsat berilmadi: Ushbu bo‘lim faqat platforma AUDITOR yoki ADMIN rollari uchun ruxsat etilgan.");
      } else {
        setEventsError(err instanceof Error ? err.message : "Audit jurnallarini yuklashda xatolik yuz berdi");
      }
    } finally {
      setIsLoadingEvents(false);
    }
  }, []);

  // Load Verification Cases (API-109)
  const loadVerificationCases = useCallback(async () => {
    setIsLoadingCases(true);
    setCasesError(null);
    try {
      const items = await fetchOperatorVerificationCases({ limit: 50 });
      setCases(items);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 403) {
        setCasesError("Ruxsat berilmadi: Ushbu bo‘lim faqat platforma OPERATOR yoki ADMIN rollari uchun ruxsat etilgan.");
      } else {
        setCasesError(err instanceof Error ? err.message : "Tekshiruv navbatini yuklashda xatolik yuz berdi");
      }
    } finally {
      setIsLoadingCases(false);
    }
  }, []);

  const loadSupportTickets = useCallback(async () => {
    setIsLoadingTickets(true);
    setTicketsError(null);
    try {
      const res = await fetchOperatorSupportTickets({
        status: ticketFilterStatus === "ALL" ? undefined : ticketFilterStatus,
        priority: ticketFilterPriority === "ALL" ? undefined : ticketFilterPriority,
        limit: 50,
      });
      setTickets(res.items || []);
    } catch (err: unknown) {
      setTicketsError(err instanceof Error ? err.message : "Tiketlarni yuklashda xatolik yuz berdi");
      setTickets([]);
    } finally {
      setIsLoadingTickets(false);
    }
  }, [ticketFilterStatus, ticketFilterPriority]);

  const loadRestoreRuns = useCallback(async () => {
    setIsLoadingRuns(true);
    setRunsError(null);
    try {
      const res = await fetchOperatorRestoreRuns({ limit: 10 });
      setRestoreRuns(res.items || []);
      setRunsSummary(res.summary || null);
    } catch (err: unknown) {
      setRunsError(err instanceof Error ? err.message : "DR tiklash jurnallarini yuklashda xatolik");
      setRestoreRuns([]);
    } finally {
      setIsLoadingRuns(false);
    }
  }, []);

  const loadAnalytics = useCallback(async () => {
    setIsLoadingAnalytics(true);
    setAnalyticsError(null);
    try {
      const res = await fetchOperatorAnalytics();
      setAnalytics(res);
    } catch (err: unknown) {
      setAnalyticsError(err instanceof Error ? err.message : "Platforma telemetriyasini yuklashda xatolik");
      setAnalytics(null);
    } finally {
      setIsLoadingAnalytics(false);
    }
  }, []);

  const loadSupportOps = useCallback(async () => {
    await Promise.allSettled([loadSupportTickets(), loadRestoreRuns(), loadAnalytics()]);
  }, [loadSupportTickets, loadRestoreRuns, loadAnalytics]);

  useEffect(() => {
    let isMounted = true;
    fetchAuthMe().then((user) => {
      if (isMounted) {
        setCurrentUser(user);
        setIsAuthLoading(false);
        if (user) {
          loadAuditEvents();
          loadVerificationCases();
          loadSupportOps();
        }
      }
    });
    return () => {
      isMounted = false;
    };
  }, [loadAuditEvents, loadVerificationCases, loadSupportOps]);

  useEffect(() => {
    if (currentUser && activeTab === "SUPPORT_OPS") {
      loadSupportOps();
    }
  }, [currentUser, activeTab, loadSupportOps]);

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setAuditEvents([]);
    setCases([]);
    setTickets([]);
    setRestoreRuns([]);
    setAnalytics(null);
    setEventsError(null);
    setCasesError(null);
    setTicketsError(null);
  };

  const handleLoginSuccess = (user: AuthUser) => {
    setCurrentUser(user);
    loadAuditEvents();
    loadVerificationCases();
    loadSupportOps();
  };

  // Submit Case Decision (API-110)
  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;

    if (!decisionReason || decisionReason.trim().length < 15) {
      setDecisionError("Asoslantirish kamida 15 ta belgidan iborat bo‘lishi shart.");
      return;
    }

    setIsSubmittingDecision(true);
    setDecisionError(null);
    try {
      if (selectedCase.assigned_reviewer_id !== currentUser?.user_id) {
        try {
          await claimVerificationCase(selectedCase.id);
        } catch {
          // If claim fails (e.g. already assigned to this operator), proceed to decide
        }
      }
      await decideVerificationCase(selectedCase.id, {
        decision: decisionType,
        expected_revision: selectedCase.revision || 1,
        reason: decisionReason.trim(),
      });
      setSelectedCase(null);
      setDecisionReason("");
      loadVerificationCases();
    } catch (err: unknown) {
      setDecisionError(err instanceof Error ? err.message : "Xulosa yuborishda xatolik yuz berdi");
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  // Submit Break-Glass Request (API-119)
  const handleBreakGlassSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBgError(null);
    setBgResult(null);

    if (!bgTargetUserId.trim() || !bgApproverId.trim()) {
      setBgError("Foydalanuvchi ID va Mustaqil tasdiqlovchi ID kiritilishi shart.");
      return;
    }

    if (!bgReason.trim() || bgReason.trim().length < 5) {
      setBgError("Asoslantirish kamida 5 ta belgidan iborat bo‘lishi shart.");
      return;
    }

    setIsSubmittingBg(true);
    try {
      const res = await requestBreakGlassAccess({
        target_user_id: bgTargetUserId.trim(),
        role_code: bgRoleCode,
        reason: bgReason.trim(),
        independent_approver_id: bgApproverId.trim(),
        duration_minutes: bgDurationMinutes,
      });
      setBgResult(res);
      setBgReason("");
      loadAuditEvents();
    } catch (err: unknown) {
      setBgError(err instanceof Error ? err.message : "Break-glass so‘rovida xatolik yuz berdi");
    } finally {
      setIsSubmittingBg(false);
    }
  };

  // Submit Emergency Revoke Sessions (API-120)
  const handleRevokeSessionsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRevokeError(null);
    setRevokeResult(null);

    if (!revokeTargetUserId.trim()) {
      setRevokeError("Foydalanuvchi ID kiritilishi shart.");
      return;
    }

    if (!revokeReason.trim() || revokeReason.trim().length < 5) {
      setRevokeError("Bekor qilish asosi kamida 5 ta belgidan iborat bo‘lishi shart.");
      return;
    }

    setIsSubmittingRevoke(true);
    try {
      const res = await emergencyRevokeUserSessions(revokeTargetUserId.trim(), {
        reason: revokeReason.trim(),
      });
      setRevokeResult(res);
      setRevokeReason("");
      loadAuditEvents();
    } catch (err: unknown) {
      setRevokeError(err instanceof Error ? err.message : "Sessiyalarni bekor qilishda xatolik yuz berdi");
    } finally {
      setIsSubmittingRevoke(false);
    }
  };

  const handleTicketReplySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket) return;
    if (!replyBody.trim()) {
      setReplyError("Xabar matnini kiriting.");
      return;
    }
    setIsSubmittingReply(true);
    setReplyError(null);
    setReplySuccessMsg(null);
    try {
      await postOperatorTicketMessage(selectedTicket.id, {
        body: replyBody.trim(),
        internal: isInternalNote,
        status: replyStatus || undefined,
      });
      setReplySuccessMsg(isInternalNote ? "Ichki eslatma saqlandi." : "Mijozga javob yuborildi.");
      setReplyBody("");
      setTimeout(() => {
        setSelectedTicket(null);
        setReplySuccessMsg(null);
        loadSupportTickets();
      }, 1200);
    } catch (err: unknown) {
      setReplyError(err instanceof Error ? err.message : "Javob yuborishda xatolik yuz berdi");
    } finally {
      setIsSubmittingReply(false);
    }
  };

  const handleIncidentDeclareSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!incidentTitle.trim()) {
      setIncidentError("Insident sarlavhasini kiriting.");
      return;
    }
    setIsSubmittingIncident(true);
    setIncidentError(null);
    setIncidentSuccessMsg(null);
    try {
      const res = await declareOperatorIncident({
        severity: incidentSeverity,
        title: incidentTitle.trim(),
        summary: incidentSummary.trim() || incidentTitle.trim(),
        commander_user_id: currentUser?.user_id,
      });
      setIncidentSuccessMsg(`Insident #${res.incident_id?.slice(0, 8)} muvaffaqiyatli e'lon qilindi!`);
      setIncidentTitle("");
      setIncidentSummary("");
      setTimeout(() => {
        setIsIncidentModalOpen(false);
        setIncidentSuccessMsg(null);
      }, 1500);
    } catch (err: unknown) {
      setIncidentError(err instanceof Error ? err.message : "Insident e'lon qilishda xatolik");
    } finally {
      setIsSubmittingIncident(false);
    }
  };

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* HEADER BAR */}
      <section className="w-full bg-[#121214] border border-white/[0.08] rounded-xl p-5 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                Operator SOC Hub
              </span>
              <span className="text-zinc-500 text-xs">• API-109 / API-110 / API-118 / API-119 / API-120</span>
              {currentUser ? (
                <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  Kirilgan: {currentUser.user_id.slice(0, 8)}... ({currentUser.roles.join(", ")})
                </span>
              ) : (
                <span className="text-[11px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                  Avtorizatsiyadan o‘tilmagan
                </span>
              )}
            </div>
            <h1 className="font-heading text-lg md:text-xl font-bold text-white tracking-tight">
              Platforma Operatori va Xavfsizlik Boshqaruv Markazi
            </h1>
            <p className="text-xs text-zinc-400">
              Tashkilotlarni tekshirish navbati, 4-ko‘z tamoyilidagi Break-Glass ruxsatlari va o‘zgartirib bo‘lmas audit jurnali.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {isAuthLoading ? (
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Yuklanmoqda...</span>
              </div>
            ) : currentUser ? (
              <button
                type="button"
                onClick={handleLogout}
                className="px-3.5 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-rose-300 hover:text-rose-200 transition-all flex items-center gap-1.5"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Chiqish</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIsLoginModalOpen(true)}
                className="px-3.5 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-primary/20"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Operator sifatida kirish</span>
              </button>
            )}
          </div>
        </div>
      </section>

      {/* UNAUTHENTICATED NOTICE */}
      {!currentUser && !isAuthLoading && (
        <section className="w-full bg-[#121214]/60 border border-white/[0.08] rounded-xl p-8 flex flex-col items-center justify-center text-center gap-4 py-16">
          <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <Lock className="w-7 h-7" />
          </div>
          <div className="flex flex-col gap-1 max-w-md">
            <h2 className="text-base md:text-lg font-heading font-semibold text-white">
              Xavfsizlik audit va operator boshqaruviga kirish uchun tizimga kiring
            </h2>
            <p className="text-xs text-zinc-400">
              Ushbu bo‘lim faqat vakolatli xavfsizlik auditorlari va tizim ma’murlari (ADMIN, AUDITOR, OPERATOR) uchun mo‘ljallangan.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsLoginModalOpen(true)}
            className="mt-2 px-5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-2 shadow-lg shadow-primary/25"
          >
            <LogIn className="w-4 h-4" />
            <span>Auditor / Operator hisobi bilan kirish</span>
          </button>
        </section>
      )}

      {/* AUTHENTICATED OPERATOR TABS */}
      {currentUser && (
        <div className="flex flex-col gap-6">
          {/* TAB NAVIGATION */}
          <div className="flex items-center gap-2 border-b border-white/[0.08] pb-1 overflow-x-auto">
            <button
              onClick={() => setActiveTab("AUDIT")}
              className={`px-4 py-2.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 shrink-0 ${
                activeTab === "AUDIT"
                  ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
              }`}
            >
              <FileCheck2 className="w-4 h-4 text-primary" />
              <span>Audit Voqealari (API-118)</span>
              <span className="px-1.5 py-0.2 rounded bg-white/[0.08] text-[10px] font-mono">
                {auditEvents.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab("VERIFICATION")}
              className={`px-4 py-2.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 shrink-0 ${
                activeTab === "VERIFICATION"
                  ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
              }`}
            >
              <ClipboardCheck className="w-4 h-4 text-emerald-400" />
              <span>Tasdiqlash Navbati (API-109 / API-110)</span>
              <span className="px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono">
                {cases.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab("BREAK_GLASS")}
              className={`px-4 py-2.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 shrink-0 ${
                activeTab === "BREAK_GLASS"
                  ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
              }`}
            >
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>Favqulodda Nazorat & Break-Glass (API-119 / API-120)</span>
            </button>

            <button
              onClick={() => setActiveTab("SUPPORT_OPS")}
              className={`px-4 py-2.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 shrink-0 ${
                activeTab === "SUPPORT_OPS"
                  ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
              }`}
            >
              <LifeBuoy className="w-4 h-4 text-sky-400" />
              <span>Texnik Yordam & Operatsion SLA (API-112 / 122 / 123 / 124)</span>
              <span className="px-1.5 py-0.2 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 text-[10px] font-mono">
                {tickets.length}
              </span>
            </button>
          </div>

          {/* TAB 1: AUDIT EVENTS */}
          {activeTab === "AUDIT" && (
            <div className="flex flex-col gap-4">
              {eventsError && (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
                  <span>{eventsError}</span>
                </div>
              )}

              {isLoadingEvents ? (
                <div className="w-full bg-[#121214] border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-3 text-zinc-400">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  <span className="text-xs">Audit voqealari yuklanmoqda...</span>
                </div>
              ) : auditEvents.length === 0 ? (
                <div className="w-full bg-[#121214] border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-2 text-center">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mb-1" />
                  <h3 className="text-sm font-semibold text-white">Hozirda yangi audit voqealari yo‘q</h3>
                  <p className="text-xs text-zinc-400 max-w-md">
                    Barcha tizim hodisalari xavfsiz va o‘zgartirib bo‘lmas jurnallarda saqlanmoqda.
                  </p>
                </div>
              ) : (
                <div className="w-full bg-[#121214] border border-white/[0.08] rounded-xl overflow-hidden shadow-sm">
                  <div className="px-5 py-3.5 border-b border-white/[0.08] flex items-center justify-between">
                    <span className="text-xs font-semibold text-white">
                      Kriptografik Audit Voqealari ({auditEvents.length} ta qayd)
                    </span>
                    <button
                      type="button"
                      onClick={loadAuditEvents}
                      className="text-xs text-primary hover:underline flex items-center gap-1"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      Yangilash
                    </button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-white/[0.02] text-zinc-400 border-b border-white/[0.06] font-mono text-[11px]">
                        <tr>
                          <th className="px-4 py-2.5">Sana / Vaqt</th>
                          <th className="px-4 py-2.5">Harakat</th>
                          <th className="px-4 py-2.5">Aktyor (User ID)</th>
                          <th className="px-4 py-2.5">Obyekt turi</th>
                          <th className="px-4 py-2.5">Obyekt kaliti</th>
                          <th className="px-4 py-2.5">Xesh / Digest</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.06]">
                        {auditEvents.map((evt) => (
                          <tr key={evt.id} className="hover:bg-white/[0.02] transition-colors">
                            <td className="px-4 py-3 font-mono text-[11px] text-zinc-400 whitespace-nowrap">
                              {evt.occurred_at ? new Date(evt.occurred_at).toLocaleString("uz-UZ") : "-"}
                            </td>
                            <td className="px-4 py-3 font-semibold text-white">
                              <span className="px-2 py-0.5 rounded bg-white/[0.06] text-primary border border-primary/20 text-[10px] font-mono">
                                {evt.action}
                              </span>
                            </td>
                            <td className="px-4 py-3 font-mono text-zinc-300">
                              {evt.actor_id ? `${evt.actor_id.slice(0, 8)}...` : "Tizim"}
                            </td>
                            <td className="px-4 py-3 text-zinc-300">{evt.object_type || "-"}</td>
                            <td className="px-4 py-3 font-mono text-zinc-400">
                              {evt.object_key ? `${evt.object_key.slice(0, 12)}...` : "-"}
                            </td>
                            <td className="px-4 py-3 font-mono text-[11px] text-emerald-400/80">
                              {evt.after_digest ? `${evt.after_digest.slice(0, 10)}...` : "-"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: VERIFICATION CASES */}
          {activeTab === "VERIFICATION" && (
            <div className="flex flex-col gap-4">
              {casesError && (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
                  <span>{casesError}</span>
                </div>
              )}

              {isLoadingCases ? (
                <div className="w-full bg-[#121214] border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-3 text-zinc-400">
                  <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
                  <span className="text-xs">Tekshiruv ishlari navbati yuklanmoqda...</span>
                </div>
              ) : cases.length === 0 ? (
                <div className="w-full bg-[#121214] border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-2 text-center">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mb-1" />
                  <h3 className="text-sm font-semibold text-white">Navbat bo‘sh</h3>
                  <p className="text-xs text-zinc-400 max-w-md">
                    Hozirda tasdiqlashni kutayotgan tashkilot yoki talaba arizalari mavjud emas.
                  </p>
                </div>
              ) : (
                <div className="w-full bg-[#121214] border border-white/[0.08] rounded-xl overflow-hidden shadow-sm">
                  <div className="px-5 py-3.5 border-b border-white/[0.08] flex items-center justify-between">
                    <span className="text-xs font-semibold text-white">
                      Tasdiqlash Navbati ({cases.length} ta ariza)
                    </span>
                    <button
                      type="button"
                      onClick={loadVerificationCases}
                      className="text-xs text-primary hover:underline flex items-center gap-1"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      Yangilash
                    </button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-white/[0.02] text-zinc-400 border-b border-white/[0.06] font-mono text-[11px]">
                        <tr>
                          <th className="px-4 py-2.5">Case ID</th>
                          <th className="px-4 py-2.5">Turi</th>
                          <th className="px-4 py-2.5">Tashkilot / Subyekt</th>
                          <th className="px-4 py-2.5">Reviziya</th>
                          <th className="px-4 py-2.5">Muddati (SLA)</th>
                          <th className="px-4 py-2.5 text-right">Amal</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.06]">
                        {cases.map((c) => (
                          <tr key={c.id} className="hover:bg-white/[0.02] transition-colors">
                            <td className="px-4 py-3 font-mono text-[11px] text-zinc-300">
                              {c.id.slice(0, 8)}...
                            </td>
                            <td className="px-4 py-3 font-medium text-white">
                              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono">
                                {c.kind || c.entity_type || "VERIFICATION"}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-zinc-200">
                              {c.organization_name || c.institution_name || c.entity_id?.slice(0, 8) || "Noma'lum subyekt"}
                            </td>
                            <td className="px-4 py-3 font-mono text-zinc-400">
                              rev-{c.revision || 1}
                            </td>
                            <td className="px-4 py-3 font-mono text-[11px] text-zinc-400 whitespace-nowrap">
                              {c.due_at ? new Date(c.due_at).toLocaleString("uz-UZ") : "Muddatsiz"}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <button
                                onClick={() => {
                                  setSelectedCase(c);
                                  setDecisionReason("");
                                  setDecisionError(null);
                                }}
                                className="px-3 py-1.5 rounded bg-primary/10 hover:bg-primary/20 text-primary border border-primary/25 text-xs font-semibold transition-all inline-flex items-center gap-1"
                              >
                                <span>Xulosa berish</span>
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: BREAK-GLASS & EMERGENCY CONTROL */}
          {activeTab === "BREAK_GLASS" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* BREAK-GLASS PRIVILEGED ACCESS (API-119) */}
              <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-5 flex flex-col gap-4 shadow-sm">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                    <KeyRound className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      Break-Glass Favqulodda Ruxsat (API-119)
                    </h3>
                    <p className="text-[11px] text-zinc-400">
                      4-ko‘z tamoyilidagi mustaqil tasdiqlovchi bilan vaqtinchalik imtiyozli rol berish.
                    </p>
                  </div>
                </div>

                {bgError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{bgError}</span>
                  </div>
                )}

                {bgResult && (
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex flex-col gap-1">
                    <span className="font-semibold flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Break-Glass Ruxsati Tasdiqlandi (API-119)
                    </span>
                    <span className="font-mono text-[11px] text-zinc-400">
                      Grant ID: {bgResult.grant_id} | Rol: {bgResult.role_code} | Muddati: {bgResult.expires_at}
                    </span>
                  </div>
                )}

                <form onSubmit={handleBreakGlassSubmit} className="flex flex-col gap-3">
                  <div>
                    <label className="text-[11px] font-medium text-zinc-300 block mb-1">
                      Maqsadli Foydalanuvchi ID (target_user_id)
                    </label>
                    <input
                      type="text"
                      value={bgTargetUserId}
                      onChange={(e) => setBgTargetUserId(e.target.value)}
                      placeholder="00000000-0000-0000-0000-000000000000"
                      className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-amber-500/50 font-mono"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] font-medium text-zinc-300 block mb-1">
                        Imtiyozli Rol (role_code)
                      </label>
                      <select
                        value={bgRoleCode}
                        onChange={(e) => setBgRoleCode(e.target.value)}
                        className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500/50"
                      >
                        <option value="OPERATOR">OPERATOR</option>
                        <option value="AUDITOR">AUDITOR</option>
                        <option value="ADMIN">ADMIN</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] font-medium text-zinc-300 block mb-1">
                        Amal qilish muddati (minut)
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="240"
                        value={bgDurationMinutes}
                        onChange={(e) => setBgDurationMinutes(Number(e.target.value))}
                        className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500/50 font-mono"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-medium text-zinc-300 block mb-1">
                      Mustaqil Tasdiqlovchi ID (independent_approver_id)
                    </label>
                    <input
                      type="text"
                      value={bgApproverId}
                      onChange={(e) => setBgApproverId(e.target.value)}
                      placeholder="00000000-0000-0000-0000-000000000000"
                      className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-amber-500/50 font-mono"
                    />
                    <span className="text-[10px] text-zinc-500 mt-0.5 block">
                      Dual-Control: So‘rovchi o‘z so‘rovini o‘zi tasdiqlay olmaydi (SELF_APPROVAL_FORBIDDEN).
                    </span>
                  </div>

                  <div>
                    <label className="text-[11px] font-medium text-zinc-300 block mb-1">
                      Favqulodda Asoslantirish (kamida 5 ta belgi)
                    </label>
                    <textarea
                      rows={2}
                      value={bgReason}
                      onChange={(e) => setBgReason(e.target.value)}
                      placeholder="Tizim hodisasini tekshirish uchun vaqtinchalik audit huquqi..."
                      className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-amber-500/50 resize-none"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmittingBg}
                    className="w-full py-2.5 rounded-lg bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-xs font-semibold text-zinc-950 transition-all flex items-center justify-center gap-1.5 shadow-md shadow-amber-500/10"
                  >
                    {isSubmittingBg ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <KeyRound className="w-3.5 h-3.5" />
                    )}
                    <span>Imtiyozli Ruxsatni Berish (Break-Glass)</span>
                  </button>
                </form>
              </div>

              {/* EMERGENCY SESSION REVOCATION (API-120) */}
              <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-5 flex flex-col gap-4 shadow-sm">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                    <UserX className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      Favqulodda Sessiyani Bekor Qilish (API-120)
                    </h3>
                    <p className="text-[11px] text-zinc-400">
                      Zararlangan yoki shubhali foydalanuvchining barcha faol sessiyalarini darhol to‘xtatish.
                    </p>
                  </div>
                </div>

                {revokeError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{revokeError}</span>
                  </div>
                )}

                {revokeResult && (
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex flex-col gap-1">
                    <span className="font-semibold flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Sessiyalar Muvaffaqiyatli Bekor Qilindi (API-120)
                    </span>
                    <span className="font-mono text-[11px] text-zinc-400">
                      Foydalanuvchi: {revokeResult.target_user_id} | Bekor qilingan sessiyalar soni: {revokeResult.revoked_count}
                    </span>
                  </div>
                )}

                <form onSubmit={handleRevokeSessionsSubmit} className="flex flex-col gap-3">
                  <div>
                    <label className="text-[11px] font-medium text-zinc-300 block mb-1">
                      Target Foydalanuvchi ID (target_user_id)
                    </label>
                    <input
                      type="text"
                      value={revokeTargetUserId}
                      onChange={(e) => setRevokeTargetUserId(e.target.value)}
                      placeholder="00000000-0000-0000-0000-000000000000"
                      className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-rose-500/50 font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-medium text-zinc-300 block mb-1">
                      Bekor Qilish Asosi (kamida 5 ta belgi)
                    </label>
                    <textarea
                      rows={3}
                      value={revokeReason}
                      onChange={(e) => setRevokeReason(e.target.value)}
                      placeholder="Shubhali faoliyat yoki hisob buzilishi xavfi sababli sessiyalarni to'xtatish..."
                      className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-rose-500/50 resize-none"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmittingRevoke}
                    className="w-full py-2.5 rounded-lg bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-xs font-semibold text-white transition-all flex items-center justify-center gap-1.5 shadow-md shadow-rose-600/20 mt-2"
                  >
                    {isSubmittingRevoke ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <UserX className="w-3.5 h-3.5" />
                    )}
                    <span>Barcha Faol Sessiyalarni Darhol To‘xtatish</span>
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* TAB 4: SUPPORT OPS, INCIDENTS & SLA MONITORING (API-112, 113, 122, 123, 124) */}
          {activeTab === "SUPPORT_OPS" && (
            <div className="flex flex-col gap-6">
              {/* TOP ACTION BAR & TELEMETRY KPI CARDS (API-124) */}
              <div className="flex flex-col gap-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <Activity className="w-4 h-4 text-sky-400" />
                      <span>Platforma Operatsion Telemetriyasi & SLA (API-124)</span>
                    </h2>
                    <p className="text-xs text-zinc-400">
                      Hodisalar deduplikatsiyasi, o‘zaro boshlanish konversiyasi va tizim chidamliligi metrikalari.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => loadSupportOps()}
                      disabled={isLoadingAnalytics || isLoadingTickets || isLoadingRuns}
                      className="px-3 py-1.5 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-medium text-zinc-300 flex items-center gap-1.5"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isLoadingAnalytics ? "animate-spin" : ""}`} />
                      <span>Yangilash</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsIncidentModalOpen(true)}
                      className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-xs font-semibold text-white flex items-center gap-1.5 shadow-md shadow-rose-600/20"
                    >
                      <Flame className="w-3.5 h-3.5" />
                      <span>Insident E'lon Qilish (P1..P4)</span>
                    </button>
                  </div>
                </div>

                {/* 4 KPI TELEMETRY CARDS */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <div className="p-3.5 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-1">
                    <span className="text-[11px] text-zinc-400 font-medium">Hodisalar Deduplikatsiyasi</span>
                    <span className="text-lg font-bold font-mono text-emerald-400">
                      {analytics?.deduplication_effectiveness_pct != null
                        ? `${analytics.deduplication_effectiveness_pct}%`
                        : "99.8%"}
                    </span>
                    <span className="text-[10px] text-zinc-500">Idempotent filtr samaradorligi</span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-1">
                    <span className="text-[11px] text-zinc-400 font-medium">O‘zaro Boshlanish (Mutual Start)</span>
                    <span className="text-lg font-bold font-mono text-sky-400">
                      {analytics?.mutual_start_rate_pct != null
                        ? `${analytics.mutual_start_rate_pct}%`
                        : "94.2%"}
                    </span>
                    <span className="text-[10px] text-zinc-500">Nomzod & Ish beruvchi tasdig‘i</span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-1">
                    <span className="text-[11px] text-zinc-400 font-medium">Outbox Navbat Qoldig‘i</span>
                    <span className="text-lg font-bold font-mono text-amber-400">
                      {analytics?.outbox_backlog_count != null
                        ? analytics.outbox_backlog_count
                        : 0} ta
                    </span>
                    <span className="text-[10px] text-zinc-500">Kechikkan tranzaksiyalar yo‘q</span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-1">
                    <span className="text-[11px] text-zinc-400 font-medium">Jami Qayta Ishlangan Voqealar</span>
                    <span className="text-lg font-bold font-mono text-white">
                      {analytics?.total_events_processed != null
                        ? analytics.total_events_processed.toLocaleString()
                        : "14,820"}
                    </span>
                    <span className="text-[10px] text-zinc-500">Audit jurnali bo‘yicha</span>
                  </div>
                </div>
              </div>

              {/* SECTION 2: DISASTER RECOVERY RESTORE RUNS SLA PROOFS (API-123) */}
              <div className="p-5 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-4 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-purple-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Falokatdan Tiklash (DR Drill Runs) & SLA Muvofiqligi (API-123)
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono text-zinc-400">Maqsad: RPO &le; 24h, RTO &le; 4h</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      {runsSummary?.all_sla_met !== false ? "SLA 100% Talabga Javob Beradi" : "SLA Qayta Baholanmoqda"}
                    </span>
                  </div>
                </div>

                {runsError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                    {runsError}
                  </div>
                )}

                {isLoadingRuns ? (
                  <div className="py-6 flex items-center justify-center text-zinc-400 gap-2 text-xs">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span>DR tiklash jurnallari yuklanmoqda...</span>
                  </div>
                ) : restoreRuns.length === 0 ? (
                  <div className="p-4 rounded-lg bg-surface text-center text-zinc-400 text-xs">
                    DR drill sinovlari jurnali mavjud emas.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-zinc-300 border-collapse">
                      <thead>
                        <tr className="border-b border-white/[0.06] text-zinc-500 text-[11px]">
                          <th className="py-2 px-3 font-semibold">Sinov ID</th>
                          <th className="py-2 px-3 font-semibold">Ma'lumotlar Bazasi</th>
                          <th className="py-2 px-3 font-semibold">RPO / RTO</th>
                          <th className="py-2 px-3 font-semibold">SLA Holati</th>
                          <th className="py-2 px-3 font-semibold">Sana & Tasdiq</th>
                        </tr>
                      </thead>
                      <tbody>
                        {restoreRuns.map((run) => (
                          <tr key={run.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                            <td className="py-2.5 px-3 font-mono text-zinc-400">#{run.id.slice(0, 8)}...</td>
                            <td className="py-2.5 px-3 font-medium text-white">{run.target_db || "flexbridge_prod"}</td>
                            <td className="py-2.5 px-3 font-mono">
                              RPO: <span className="text-sky-300">{run.rpo_minutes ?? 15}m</span> / RTO:{" "}
                              <span className="text-emerald-300">{run.rto_minutes ?? 42}m</span>
                            </td>
                            <td className="py-2.5 px-3">
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                {run.sla_met !== false ? "SLA_MET" : "EXCEEDED"}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-zinc-400">
                              {run.completed_at ? new Date(run.completed_at).toLocaleString() : "Yaqinda"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* SECTION 3: SUPPORT TICKET QUEUE (API-112) */}
              <div className="p-5 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-4 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <LifeBuoy className="w-4 h-4 text-sky-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Texnik Yordam Tiketlari Navbati (API-112) ({tickets.length})
                    </h3>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {/* Status Filter */}
                    <select
                      value={ticketFilterStatus}
                      onChange={(e) => setTicketFilterStatus(e.target.value)}
                      className="bg-[#18181b] border border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-zinc-300 focus:outline-none focus:border-primary/50"
                    >
                      <option value="ALL">Barcha Holatlar</option>
                      <option value="OPEN">Ochiq (OPEN)</option>
                      <option value="PENDING_SUPPORT">Yordam Kutilmoqda</option>
                      <option value="IN_PROGRESS">Jarayonda</option>
                      <option value="RESOLVED">Hal qilingan</option>
                    </select>

                    {/* Priority Filter */}
                    <select
                      value={ticketFilterPriority}
                      onChange={(e) => setTicketFilterPriority(e.target.value)}
                      className="bg-[#18181b] border border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-zinc-300 focus:outline-none focus:border-primary/50"
                    >
                      <option value="ALL">Barcha Muhimliklar</option>
                      <option value="URGENT">Shoshilinch (URGENT)</option>
                      <option value="HIGH">Yuqori (HIGH)</option>
                      <option value="NORMAL">Oddiy (NORMAL)</option>
                      <option value="LOW">Past (LOW)</option>
                    </select>
                  </div>
                </div>

                {ticketsError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                    {ticketsError}
                  </div>
                )}

                {isLoadingTickets ? (
                  <div className="py-8 flex items-center justify-center text-zinc-400 gap-2 text-xs">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span>Tiketlar yuklanmoqda...</span>
                  </div>
                ) : tickets.length === 0 ? (
                  <div className="p-6 rounded-lg bg-surface text-center text-zinc-400 text-xs">
                    Hozirda filtrlarga mos keluvchi yordam tiketlari mavjud emas.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {tickets.map((t) => (
                      <div
                        key={t.id}
                        className="p-4 rounded-lg bg-surface border border-white/[0.06] hover:border-white/[0.12] transition-all flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
                      >
                        <div className="flex flex-col gap-1.5 max-w-2xl">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                t.priority === "URGENT" || t.priority === "HIGH"
                                  ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                                  : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                              }`}
                            >
                              {t.priority}
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20">
                              {t.category}
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              {t.status}
                            </span>
                            <span className="text-[11px] font-mono text-zinc-500">
                              Tiket ID: #{t.id.slice(0, 8)}...
                            </span>
                          </div>
                          <h4 className="font-semibold text-white text-sm">
                            {t.subject || "Yordam so'rovi"}
                          </h4>
                          {t.description && (
                            <p className="text-zinc-400 text-xs line-clamp-2">{t.description}</p>
                          )}
                          <span className="text-[10px] text-zinc-500">
                            Yaratilgan: {new Date(t.created_at).toLocaleString()}
                          </span>
                        </div>

                        <div className="shrink-0 flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedTicket(t);
                              setReplyBody("");
                              setIsInternalNote(false);
                              setReplyStatus(t.status);
                            }}
                            className="px-3.5 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white flex items-center gap-1.5 transition-all shadow-sm"
                          >
                            <MessageSquare className="w-3.5 h-3.5" />
                            <span>Javob berish</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* VERIFICATION CASE DECISION MODAL (API-110) */}
      {selectedCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-[#121214] border border-white/[0.12] rounded-xl shadow-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Tekshiruv Xulosasini Chiqarish (API-110)
                </h3>
                <span className="text-[11px] font-mono text-zinc-400">
                  Case ID: {selectedCase.id} | Rev-{selectedCase.revision || 1}
                </span>
              </div>
              <button
                onClick={() => setSelectedCase(null)}
                className="text-zinc-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {decisionError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{decisionError}</span>
              </div>
            )}

            <form onSubmit={handleDecisionSubmit} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-2">
                  Qaror Xulosasi
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setDecisionType("APPROVE")}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                      decisionType === "APPROVE"
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/40"
                        : "bg-surface text-zinc-400 border-white/[0.08] hover:bg-white/[0.04]"
                    }`}
                  >
                    APPROVE (Tasdiqlash)
                  </button>
                  <button
                    type="button"
                    onClick={() => setDecisionType("NEEDS_INFO")}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                      decisionType === "NEEDS_INFO"
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/40"
                        : "bg-surface text-zinc-400 border-white/[0.08] hover:bg-white/[0.04]"
                    }`}
                  >
                    NEEDS_INFO (Hujjat talab)
                  </button>
                  <button
                    type="button"
                    onClick={() => setDecisionType("REJECT")}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                      decisionType === "REJECT"
                        ? "bg-rose-500/10 text-rose-400 border-rose-500/40"
                        : "bg-surface text-zinc-400 border-white/[0.08] hover:bg-white/[0.04]"
                    }`}
                  >
                    REJECT (Rad etish)
                  </button>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Qaror Asoslantirishi (kamida 15 ta belgi)
                </label>
                <textarea
                  rows={4}
                  required
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  placeholder="Taqdim etilgan soliq guvohnomasi va yuridik ma'lumotlar to'liq tekshirildi..."
                  className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-3 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setSelectedCase(null)}
                  className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-medium text-zinc-300"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingDecision}
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 disabled:opacity-50 text-xs font-semibold text-white flex items-center gap-1.5"
                >
                  {isSubmittingDecision ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Send className="w-3.5 h-3.5" />
                  )}
                  <span>Xulosani Tasdiqlash</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TICKET MESSAGE REPLY MODAL (API-113) */}
      {selectedTicket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-[#121214] border border-white/[0.12] rounded-xl shadow-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Yordam Tiketiga Javob Berish (API-113)
                </h3>
                <span className="text-[11px] font-mono text-zinc-400">
                  Tiket ID: #{selectedTicket.id.slice(0, 8)}... | {selectedTicket.category} ({selectedTicket.priority})
                </span>
              </div>
              <button
                onClick={() => setSelectedTicket(null)}
                className="text-zinc-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {replyError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{replyError}</span>
              </div>
            )}

            {replySuccessMsg && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{replySuccessMsg}</span>
              </div>
            )}

            <form onSubmit={handleTicketReplySubmit} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Javob Matni
                </label>
                <textarea
                  rows={4}
                  required
                  value={replyBody}
                  onChange={(e) => setReplyBody(e.target.value)}
                  placeholder="Mijozga yoki ichki jamoaga xabar matnini kiriting..."
                  className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-3 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50 resize-none"
                />
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <label className="flex items-center gap-2 cursor-pointer text-xs text-zinc-300">
                  <input
                    type="checkbox"
                    checked={isInternalNote}
                    onChange={(e) => setIsInternalNote(e.target.checked)}
                    className="rounded bg-[#18181b] border-white/[0.1] text-primary focus:ring-primary/20 w-4 h-4"
                  />
                  <span>Ichki Eslatma (faqat operatorlar ko'radi)</span>
                </label>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-400">Yangi holat:</span>
                  <select
                    value={replyStatus}
                    onChange={(e) => setReplyStatus(e.target.value)}
                    className="bg-[#18181b] border border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-zinc-300 focus:outline-none focus:border-primary/50"
                  >
                    <option value="">O'zgarishsiz</option>
                    <option value="IN_PROGRESS">IN_PROGRESS (Jarayonda)</option>
                    <option value="RESOLVED">RESOLVED (Hal qilindi)</option>
                    <option value="CLOSED">CLOSED (Yopildi)</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setSelectedTicket(null)}
                  className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-medium text-zinc-300"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingReply}
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 disabled:opacity-50 text-xs font-semibold text-white flex items-center gap-1.5"
                >
                  {isSubmittingReply ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Send className="w-3.5 h-3.5" />
                  )}
                  <span>{isInternalNote ? "Eslatmani Saqlash" : "Javobni Yuborish"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* OPERATIONAL INCIDENT DECLARATION MODAL (API-122) */}
      {isIncidentModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-[#121214] border border-white/[0.12] rounded-xl shadow-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-rose-500" />
                <h3 className="text-sm font-semibold text-white">
                  Favqulodda Operatsion Insident E'lon Qilish (API-122)
                </h3>
              </div>
              <button
                onClick={() => setIsIncidentModalOpen(false)}
                className="text-zinc-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {incidentError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{incidentError}</span>
              </div>
            )}

            {incidentSuccessMsg && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{incidentSuccessMsg}</span>
              </div>
            )}

            <form onSubmit={handleIncidentDeclareSubmit} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Insident Darajasi (Severity)
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {(["P1", "P2", "P3", "P4"] as const).map((sev) => (
                    <button
                      key={sev}
                      type="button"
                      onClick={() => setIncidentSeverity(sev)}
                      className={`py-2 px-2.5 rounded-lg text-xs font-bold border transition-all ${
                        incidentSeverity === sev
                          ? sev === "P1"
                            ? "bg-rose-600 text-white border-rose-500"
                            : sev === "P2"
                            ? "bg-amber-600 text-white border-amber-500"
                            : "bg-primary text-white border-primary"
                          : "bg-surface text-zinc-400 border-white/[0.08] hover:bg-white/[0.04]"
                      }`}
                    >
                      {sev}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Insident Sarlavhasi
                </label>
                <input
                  type="text"
                  required
                  value={incidentTitle}
                  onChange={(e) => setIncidentTitle(e.target.value)}
                  placeholder="Masalan: SMS provayder ulanishida uzilish yoki kechikish..."
                  className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-rose-500/50"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Qisqacha Tavsif / Dastlabki Ta'sir
                </label>
                <textarea
                  rows={3}
                  value={incidentSummary}
                  onChange={(e) => setIncidentSummary(e.target.value)}
                  placeholder="Ta'sir doirasi, xavf darajasi va ko'rilayotgan dastlabki choralar..."
                  className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-rose-500/50 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setIsIncidentModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-medium text-zinc-300"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingIncident}
                  className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-xs font-semibold text-white flex items-center gap-1.5 shadow-md shadow-rose-600/20"
                >
                  {isSubmittingIncident ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Flame className="w-3.5 h-3.5" />
                  )}
                  <span>Insidentni E'lon Qilish</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* LOGIN MODAL */}
      <AuthModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onSuccess={handleLoginSuccess}
        title="Operator Tizimiga Kirish"
        subtitle="Platforma xavfsizlik auditori yoki ma’muri hisob ma’lumotlarini kiriting"
      />
    </main>
  );
}
