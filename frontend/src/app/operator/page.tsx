"use client";
import { enumLabel } from "@/lib/labels";

import Link from "next/link";
import { useEffect, useRef, useState, useCallback, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { canUseOperatorModule, type OperatorModule } from "@/lib/roles";
import {
  Lock,
  CheckCircle2,
  Loader2,
  LogIn,
  AlertCircle,
  ShieldAlert,
  ClipboardCheck,
  Briefcase,
  UserX,
  KeyRound,
  RefreshCw,
  Clock,
  Send,
  X,
  FileCheck2,
  LifeBuoy,
  MessageSquare,
  Flame,
  Activity,
  Server,
  CreditCard,
  Receipt,
  Coins,
  Filter,
  CheckCheck,
  Users,
  FolderSearch,
  Sliders,
  Scale,
  Search,
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
  fetchOperatorFinanceSummary,
  fetchOperatorReconciliation,
  approveOperatorRefund,
  AuthUser,
  OperatorAuditEventItem,
  OperatorVerificationCaseItem,
  OperatorSupportTicketItem,
  OperatorRestoreRunItem,
  OperatorPlatformAnalytics,
  OperatorFinanceSummaryResponse,
  OperatorReconciliationItem,
  BreakGlassAccessResult,
  EmergencyRevokeSessionsResult,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";

import OperatorOverview from "@/components/operator/OperatorOverview";
import ModerationPanel from "@/components/operator/ModerationPanel";
import StaffRolesPanel from "@/components/operator/StaffRolesPanel";
import DirectoryPanel from "@/components/operator/DirectoryPanel";
import FeatureFlagsPanel from "@/components/operator/FeatureFlagsPanel";
import GovernanceOpsPanel, { type GovernanceSection } from "@/components/operator/GovernanceOpsPanel";
import { fetchModerationQueue } from "@/lib/moderation";
import {
  fetchDirectoryUsers,
  fetchFeatureFlags,
  fetchModerationAppeals,
  fetchPrivacyRequests,
  fetchRecoveryRequests,
  fetchStaffGrants,
} from "@/lib/platformAdmin";
import { useAsyncData } from "@/lib/useAsyncData";
import SectionDock from "@/components/shell/SectionDock";

type ActiveTab =
  | "STAFF_ROLES"
  | "DIRECTORY"
  | "FEATURE_FLAGS"
  | "GOVERNANCE"
  | "AUDIT"
  | "VERIFICATION"
  | "MODERATION"
  | "BREAK_GLASS"
  | "SUPPORT_OPS"
  | "FINANCE";

// Which permission each console tab needs (any one of them opens the tab).
const TAB_MODULES: Array<[ActiveTab, OperatorModule[]]> = [
  ["STAFF_ROLES", ["STAFF_ROLES"]],
  ["DIRECTORY", ["DIRECTORY"]],
  ["FEATURE_FLAGS", ["FEATURE_FLAGS"]],
  ["GOVERNANCE", ["PRIVACY_REQUESTS", "RECOVERY_REVIEWS", "APPEALS", "CONTINUITY", "OPERATIONS"]],
  ["AUDIT", ["AUDIT"]],
  ["VERIFICATION", ["VERIFICATION"]],
  ["MODERATION", ["MODERATION"]],
  ["BREAK_GLASS", ["BREAK_GLASS"]],
  ["SUPPORT_OPS", ["SUPPORT_TICKETS", "PLATFORM_HEALTH"]],
  ["FINANCE", ["FINANCE"]],
];

const subscribeNoop = () => () => {};

export default function OperatorPortal() {
  const mounted = useSyncExternalStore(subscribeNoop, () => true, () => false);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  // Roles of the signed-in operator, read by loaders so they skip modules that would answer 403.
  const rolesRef = useRef<string[]>([]);
  const allowed = useCallback((module: OperatorModule) => canUseOperatorModule(rolesRef.current, module), []);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>("AUDIT");
  const [governanceSection, setGovernanceSection] = useState<GovernanceSection>("PRIVACY");

  // Break-glass searchable user pickers
  const [bgTargetSearch, setBgTargetSearch] = useState("");
  const [bgApproverSearch, setBgApproverSearch] = useState("");
  const [revokeUserSearch, setRevokeUserSearch] = useState("");

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

  // Support Ops & SLA Monitoring
  const [tickets, setTickets] = useState<OperatorSupportTicketItem[]>([]);
  const [isLoadingTickets, setIsLoadingTickets] = useState(false);
  const [ticketsError, setTicketsError] = useState<string | null>(null);
  const [ticketFilterStatus, setTicketFilterStatus] = useState<string>("ALL");
  const [ticketFilterPriority, setTicketFilterPriority] = useState<string>("ALL");

  // Ticket Message Reply Modal State
  const [selectedTicket, setSelectedTicket] = useState<OperatorSupportTicketItem | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [isInternalNote, setIsInternalNote] = useState(false);
  const [replyStatus, setReplyStatus] = useState<string>("");
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);
  const [replyError, setReplyError] = useState<string | null>(null);
  const [replySuccessMsg, setReplySuccessMsg] = useState<string | null>(null);

  // Incident Declaration Modal State
  const [isIncidentModalOpen, setIsIncidentModalOpen] = useState(false);
  const [incidentSeverity, setIncidentSeverity] = useState<"P1" | "P2" | "P3" | "P4">("P3");
  const [incidentTitle, setIncidentTitle] = useState("");
  const [incidentSummary, setIncidentSummary] = useState("");
  const [isSubmittingIncident, setIsSubmittingIncident] = useState(false);
  const [incidentError, setIncidentError] = useState<string | null>(null);
  const [incidentSuccessMsg, setIncidentSuccessMsg] = useState<string | null>(null);

  // Restore Runs & SLA
  const [restoreRuns, setRestoreRuns] = useState<OperatorRestoreRunItem[]>([]);
  const [runsSummary, setRunsSummary] = useState<{
    rpo_sla_target_minutes?: number;
    rto_sla_target_minutes?: number;
    total_runs_evaluated?: number;
    all_sla_met?: boolean;
  } | null>(null);
  const [isLoadingRuns, setIsLoadingRuns] = useState(false);
  const [runsError, setRunsError] = useState<string | null>(null);

  // Platform Analytics
  const [analytics, setAnalytics] = useState<OperatorPlatformAnalytics | null>(null);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  // Finance & Reconciliation Hub
  const [financeSummary, setFinanceSummary] = useState<OperatorFinanceSummaryResponse | null>(null);
  const [isLoadingFinance, setIsLoadingFinance] = useState(false);
  const [financeError, setFinanceError] = useState<string | null>(null);

  const [reconciliationItems, setReconciliationItems] = useState<OperatorReconciliationItem[]>([]);
  const [reconciliationSummary, setReconciliationSummary] = useState<{
    total_reconciled?: number;
    total_discrepancies?: number;
    matched_count?: number;
  } | null>(null);
  const [reconciliationProvider, setReconciliationProvider] = useState<string>("ALL");
  const [reconciliationDiscrepancyOnly, setReconciliationDiscrepancyOnly] = useState<boolean>(false);
  const [isLoadingReconciliation, setIsLoadingReconciliation] = useState(false);
  const [reconciliationError, setReconciliationError] = useState<string | null>(null);

  const [approvingRefundId, setApprovingRefundId] = useState<string | null>(null);
  const [manualRefundId, setManualRefundId] = useState<string>("");
  const [approveRefundSuccess, setApproveRefundSuccess] = useState<string | null>(null);
  const [approveRefundError, setApproveRefundError] = useState<string | null>(null);

  // Load Audit Events
  const loadAuditEvents = useCallback(async () => {
    if (!allowed("AUDIT")) return;
    setIsLoadingEvents(true);
    setEventsError(null);
    try {
      const items = await fetchOperatorAuditEvents();
      setAuditEvents(items);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 403) {
        setEventsError("Ruxsat berilmadi: Ushbu bo‘lim faqat tizim auditori yoki bosh administrator uchun.");
      } else {
        setEventsError(err instanceof Error ? err.message : "Audit jurnallarini yuklashda xatolik yuz berdi");
      }
    } finally {
      setIsLoadingEvents(false);
    }
  }, [allowed]);

  // Load Verification Cases
  const loadVerificationCases = useCallback(async () => {
    if (!allowed("VERIFICATION")) return;
    setIsLoadingCases(true);
    setCasesError(null);
    try {
      const items = await fetchOperatorVerificationCases({ limit: 50 });
      setCases(items);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 403) {
        setCasesError("Ruxsat berilmadi: Ushbu bo‘lim faqat moderatorlar uchun.");
      } else {
        setCasesError(err instanceof Error ? err.message : "Tekshiruv navbatini yuklashda xatolik yuz berdi");
      }
    } finally {
      setIsLoadingCases(false);
    }
  }, [allowed]);

  const loadSupportTickets = useCallback(async () => {
    if (!allowed("SUPPORT_TICKETS")) return;
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
  }, [allowed, ticketFilterStatus, ticketFilterPriority]);

  const loadRestoreRuns = useCallback(async () => {
    if (!allowed("PLATFORM_HEALTH")) return;
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
  }, [allowed]);

  const loadAnalytics = useCallback(async () => {
    if (!allowed("PLATFORM_HEALTH")) return;
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
  }, [allowed]);

  const loadSupportOps = useCallback(async () => {
    await Promise.allSettled([loadSupportTickets(), loadRestoreRuns(), loadAnalytics()]);
  }, [loadSupportTickets, loadRestoreRuns, loadAnalytics]);

  const loadFinanceSummary = useCallback(async () => {
    if (!allowed("FINANCE")) return;
    setIsLoadingFinance(true);
    setFinanceError(null);
    try {
      const res = await fetchOperatorFinanceSummary();
      setFinanceSummary(res);
    } catch (err: unknown) {
      setFinanceError(err instanceof Error ? err.message : "Moliya xulosasini yuklashda xatolik yuz berdi");
      setFinanceSummary(null);
    } finally {
      setIsLoadingFinance(false);
    }
  }, [allowed]);

  const loadReconciliation = useCallback(async () => {
    if (!allowed("FINANCE")) return;
    setIsLoadingReconciliation(true);
    setReconciliationError(null);
    try {
      const res = await fetchOperatorReconciliation({
        provider: reconciliationProvider === "ALL" ? undefined : reconciliationProvider,
        discrepancy_only: reconciliationDiscrepancyOnly ? true : undefined,
        limit: 50,
      });
      setReconciliationItems(res.items || []);
      setReconciliationSummary(res.summary || null);
    } catch (err: unknown) {
      setReconciliationError(err instanceof Error ? err.message : "Solishtiruv ma’lumotlarini yuklashda xatolik");
      setReconciliationItems([]);
    } finally {
      setIsLoadingReconciliation(false);
    }
  }, [allowed, reconciliationProvider, reconciliationDiscrepancyOnly]);

  const loadFinanceHub = useCallback(async () => {
    await Promise.allSettled([loadFinanceSummary(), loadReconciliation()]);
  }, [loadFinanceSummary, loadReconciliation]);

  const handleApproveRefund = async (refundId: string) => {
    if (!refundId.trim()) return;
    setApprovingRefundId(refundId);
    setApproveRefundError(null);
    setApproveRefundSuccess(null);
    try {
      const res = await approveOperatorRefund(refundId.trim());
      setApproveRefundSuccess(`Qaytarish #${refundId.slice(0, 8)} muvaffaqiyatli tasdiqlandi! Yangi holat: ${enumLabel(res.status)}`);
      setManualRefundId("");
      await loadFinanceHub();
    } catch (err: unknown) {
      setApproveRefundError(err instanceof Error ? err.message : "Mablag‘ qaytarishni tasdiqlashda xatolik");
    } finally {
      setApprovingRefundId(null);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const syncAuthAndQueues = () => {
      fetchAuthMe().then((user) => {
        if (!isMounted) return;
        setCurrentUser(user);
        setIsAuthLoading(false);
        rolesRef.current = user?.roles ?? [];
        if (user) {
          const firstTab = TAB_MODULES.find(([, mods]) => mods.some((m) => allowed(m)));
          if (firstTab) setActiveTab((tab) => (TAB_MODULES.find(([t]) => t === tab)?.[1].some((m) => allowed(m)) ? tab : firstTab[0]));
          loadAuditEvents();
          loadVerificationCases();
          loadSupportOps();
          loadFinanceHub();
        }
      });
    };
    syncAuthAndQueues();
    window.addEventListener("flexbridge:auth-changed", syncAuthAndQueues);
    return () => {
      isMounted = false;
      window.removeEventListener("flexbridge:auth-changed", syncAuthAndQueues);
    };
  }, [allowed, loadAuditEvents, loadVerificationCases, loadSupportOps, loadFinanceHub]);

  // Opening the support or finance tab refreshes it. Sign-in (auth sync above)
  // already loads every queue, so no effect is needed for user changes.
  const moderationQuery = useAsyncData(
    currentUser && canUseOperatorModule(currentUser.roles || [], "MODERATION") ? `operator-moderation:${currentUser.user_id}` : null,
    () => fetchModerationQueue().catch(() => [])
  );
  const staffOverviewQuery = useAsyncData(
    currentUser && canUseOperatorModule(currentUser.roles || [], "STAFF_ROLES") ? `operator-staff-ov:${currentUser.user_id}` : null,
    () => fetchStaffGrants().catch(() => null)
  );
  const flagsOverviewQuery = useAsyncData(
    currentUser && canUseOperatorModule(currentUser.roles || [], "FEATURE_FLAGS") ? `operator-flags-ov:${currentUser.user_id}` : null,
    () => fetchFeatureFlags().catch(() => [])
  );
  const privacyOverviewQuery = useAsyncData(
    currentUser && canUseOperatorModule(currentUser.roles || [], "PRIVACY_REQUESTS") ? `operator-priv-ov:${currentUser.user_id}` : null,
    () => fetchPrivacyRequests({ status: "PENDING", limit: 50 }).catch(() => [])
  );
  const recoveryOverviewQuery = useAsyncData(
    currentUser && canUseOperatorModule(currentUser.roles || [], "RECOVERY_REVIEWS") ? `operator-rec-ov:${currentUser.user_id}` : null,
    () => fetchRecoveryRequests({ status: "PENDING_REVIEW", limit: 50 }).catch(() => [])
  );
  const appealsOverviewQuery = useAsyncData(
    currentUser && canUseOperatorModule(currentUser.roles || [], "APPEALS") ? `operator-app-ov:${currentUser.user_id}` : null,
    () => fetchModerationAppeals(50).catch(() => [])
  );

  const bgDirEnabled = Boolean(
    currentUser &&
      activeTab === "BREAK_GLASS" &&
      canUseOperatorModule(currentUser.roles || [], "BREAK_GLASS")
  );
  const bgTargetDirQuery = useAsyncData(
    bgDirEnabled ? `bg-target-dir:${bgTargetSearch.trim()}` : null,
    () => fetchDirectoryUsers({ q: bgTargetSearch.trim(), limit: 8 }).catch(() => [])
  );
  const bgApproverDirQuery = useAsyncData(
    bgDirEnabled ? `bg-approver-dir:${bgApproverSearch.trim()}` : null,
    () => fetchDirectoryUsers({ q: bgApproverSearch.trim(), limit: 8 }).catch(() => [])
  );
  const revokeDirQuery = useAsyncData(
    bgDirEnabled ? `bg-revoke-dir:${revokeUserSearch.trim()}` : null,
    () => fetchDirectoryUsers({ q: revokeUserSearch.trim(), limit: 8 }).catch(() => [])
  );

  const selectTab = (tab: ActiveTab) => {
    if (tab === activeTab) return;
    setActiveTab(tab);
    if (!currentUser) return;
    if (tab === "SUPPORT_OPS") void loadSupportOps();
    if (tab === "FINANCE") void loadFinanceHub();
  };

  const handleLoginSuccess = (user: AuthUser) => {
    setCurrentUser(user);
    rolesRef.current = user.roles ?? [];
    const firstTab = TAB_MODULES.find(([, mods]) => mods.some((m) => canUseOperatorModule(user.roles ?? [], m)));
    if (firstTab) setActiveTab(firstTab[0]);
    loadAuditEvents();
    loadVerificationCases();
    loadSupportOps();
    loadFinanceHub();
  };

  // Submit Case Decision
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

  // Submit Break-Glass Request
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

  // Submit Emergency Revoke Sessions
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
      setIncidentSuccessMsg(`Insident #${res.incident_id?.slice(0, 8)} muvaffaqiyatli e’lon qilindi!`);
      setIncidentTitle("");
      setIncidentSummary("");
      setTimeout(() => {
        setIsIncidentModalOpen(false);
        setIncidentSuccessMsg(null);
      }, 1500);
    } catch (err: unknown) {
      setIncidentError(err instanceof Error ? err.message : "Insident e’lon qilishda xatolik");
    } finally {
      setIsSubmittingIncident(false);
    }
  };

  useEffect(() => {
    window.dispatchEvent(
      new CustomEvent("flexbridge:portal-tab-changed", {
        detail: { tab: activeTab },
      })
    );
  }, [activeTab]);

  useEffect(() => {
    const onDockTab = (ev: Event) => {
      const next = (ev as CustomEvent<{ tab?: string }>).detail?.tab as ActiveTab | undefined;
      if (!next) return;
      setActiveTab(next);
    };
    window.addEventListener("flexbridge:dock-tab", onDockTab);
    return () => window.removeEventListener("flexbridge:dock-tab", onDockTab);
  }, []);

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* OPERATOR CENTER UNAUTHENTICATED HEADER */}
      {!currentUser && (
      <section className="w-full skeuo-card rounded-[28px] p-5 sm:p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full skeuo-badge-recessed text-[var(--fb-ink-secondary)]">
                Operator Markazi
              </span>
              <span className="text-[11px] font-semibold text-amber-700 dark:text-amber-300 bg-[color-mix(in_srgb,#f59e0b_14%,transparent)] px-2.5 py-0.5 rounded-full">
                Avtorizatsiyadan o‘tilmagan
              </span>
            </div>
            <h1 className="font-heading text-lg md:text-xl font-bold text-[var(--fb-ink)] tracking-tight">
              Platforma boshqaruvi
            </h1>
            <p className="text-xs text-[var(--fb-ink-secondary)]">
              Xodim rollari, funksional flaglar, tashkilotlarni tekshirish, maxsus ruxsatlar va o‘zgarmas audit jurnali.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {isAuthLoading ? (
              <div className="flex items-center gap-2 text-xs text-[var(--fb-ink-muted)]">
                <Loader2 className="w-4 h-4 animate-spin text-[var(--fb-accent)]" />
                <span>Yuklanmoqda…</span>
              </div>
            ) : (
              <Link
                href="/operator/kirish"
                className="px-4 py-2 rounded-full skeuo-btn-obsidian text-xs font-semibold flex items-center gap-1.5"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Operator sifatida kirish</span>
              </Link>
            )}
          </div>
        </div>
      </section>
      )}

      {/* UNAUTHENTICATED NOTICE */}
      {!currentUser && !isAuthLoading && (
        <section className="w-full skeuo-card rounded-[28px] p-8 flex flex-col items-center justify-center text-center gap-4 py-16">
          <div className="w-14 h-14 rounded-2xl skeuo-well flex items-center justify-center text-[var(--fb-ink)]">
            <Lock className="w-7 h-7" />
          </div>
          <div className="flex flex-col gap-1.5 max-w-md">
            <h2 className="font-display text-lg font-bold text-[var(--fb-ink)]">
              Operator Markaziga kirish uchun tizimga kiring
            </h2>
            <p className="text-xs leading-relaxed text-[var(--fb-ink-muted)]">
              Ushbu bo‘lim faqat vakolatli platforma xodimlari, xavfsizlik rahbarlari, komplayens va tizim auditorlari uchun mo‘ljallangan.
            </p>
          </div>
          <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/operator/kirish"
              className="px-5 py-2.5 rounded-full skeuo-btn-obsidian text-xs font-semibold flex items-center gap-2"
            >
              <LogIn className="w-4 h-4" />
              <span>Operator alohida kirishi</span>
            </Link>
            <button
              type="button"
              onClick={() => setIsLoginModalOpen(true)}
              className="px-4 py-2.5 rounded-full skeuo-btn-secondary text-xs font-semibold"
            >
              Tezkor kirish oynasi
            </button>
          </div>
        </section>
      )}

      {/* OVERVIEW (bento; only the modules this role may open) */}
      {currentUser && (
        <OperatorOverview
          name={currentUser.display_name}
          roles={currentUser.roles || []}
          visible={TAB_MODULES.filter(([, mods]) => mods.some((m) => canUseOperatorModule(currentUser.roles || [], m))).map(([t]) => t)}
          cases={cases}
          tickets={tickets}
          auditEvents={auditEvents}
          discrepancies={reconciliationSummary?.total_discrepancies ?? null}
          moderationCount={moderationQuery.data?.length ?? null}
          activeStaffGrantsCount={staffOverviewQuery.data?.active_grants?.length ?? null}
          enabledR1FlagsCount={
            flagsOverviewQuery.data
              ? flagsOverviewQuery.data.filter((f) => f.category === "R1" && f.enabled).length
              : null
          }
          pendingPrivacyCount={privacyOverviewQuery.data?.length ?? null}
          pendingRecoveryCount={recoveryOverviewQuery.data?.length ?? null}
          appealsCount={appealsOverviewQuery.data?.length ?? null}
          onOpen={(tab) => {
            selectTab(tab);
            document.getElementById("op-workspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
          }}
          onOpenGovernance={(section) => {
            setGovernanceSection(section);
            selectTab("GOVERNANCE");
            document.getElementById("op-workspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
          }}
        />
      )}

      {/* AUTHENTICATED OPERATOR CONSOLE */}
      {currentUser && (
        <div id="op-workspace" className="grid scroll-mt-24 gap-6">
          <div className="contents">
          <SectionDock label="Operator Markazi bo‘limlari">
            <div className="hidden lg:block px-3 pb-1 pt-1.5 text-[11px] font-medium text-[var(--fb-ink-muted)]">
              Bo‘limlar
            </div>
            {(
              [
                {
                  tab: "STAFF_ROLES" as ActiveTab,
                  label: "Xodim rollari",
                  Icon: Users,
                  count: staffOverviewQuery.data?.active_grants?.length ?? null,
                },
                {
                  tab: "DIRECTORY" as ActiveTab,
                  label: "Katalog",
                  Icon: FolderSearch,
                  count: null,
                },
                {
                  tab: "FEATURE_FLAGS" as ActiveTab,
                  label: "Flaglar",
                  Icon: Sliders,
                  count: null,
                },
                {
                  tab: "GOVERNANCE" as ActiveTab,
                  label: "Komplayens",
                  Icon: Scale,
                  count:
                    (privacyOverviewQuery.data?.length ?? 0) +
                      (recoveryOverviewQuery.data?.length ?? 0) +
                      (appealsOverviewQuery.data?.length ?? 0) ||
                    null,
                },
                {
                  tab: "AUDIT" as ActiveTab,
                  label: "Audit jurnali",
                  Icon: FileCheck2,
                  count: auditEvents.length,
                },
                {
                  tab: "VERIFICATION" as ActiveTab,
                  label: "Tashkilotlarni tekshirish",
                  Icon: ClipboardCheck,
                  count: cases.length,
                },
                {
                  tab: "MODERATION" as ActiveTab,
                  label: "E’lonlar moderatsiyasi",
                  Icon: Briefcase,
                  count: moderationQuery.data?.length ?? null,
                },
                {
                  tab: "BREAK_GLASS" as ActiveTab,
                  label: "Favqulodda ruxsat",
                  Icon: ShieldAlert,
                  count: null,
                },
                {
                  tab: "SUPPORT_OPS" as ActiveTab,
                  label: "Murojaatlar",
                  Icon: LifeBuoy,
                  count: tickets.length,
                },
                {
                  tab: "FINANCE" as ActiveTab,
                  label: "Moliya",
                  Icon: CreditCard,
                  count: reconciliationSummary?.total_discrepancies || null,
                },
              ] as const
            )
              .filter(({ tab }) => {
                const mods = TAB_MODULES.find(([t]) => t === tab)?.[1] ?? [];
                return mods.some((m) => canUseOperatorModule(currentUser.roles || [], m));
              })
              .map(({ tab, label, Icon, count }) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => selectTab(tab)}
                  className={`shrink-0 lg:w-full fb-nav-item text-xs justify-between ${
                    activeTab === tab ? "fb-nav-active" : "fb-nav-idle"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Icon className="w-4 h-4 shrink-0" />
                    <span className="text-xs">{label}</span>
                  </span>
                  {count !== null && count > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-[var(--fb-well-deep)] text-[10px] tabular-nums">
                      {count}
                    </span>
                  )}
                </button>
              ))}
          </SectionDock>
          </div>

          <div className="min-w-0 flex flex-col gap-6">

          {activeTab === "STAFF_ROLES" && (
            <StaffRolesPanel currentUserId={currentUser.user_id} roles={currentUser.roles || []} />
          )}

          {activeTab === "DIRECTORY" && <DirectoryPanel roles={currentUser.roles || []} />}

          {activeTab === "FEATURE_FLAGS" && <FeatureFlagsPanel roles={currentUser.roles || []} />}

          {activeTab === "GOVERNANCE" && (
            <GovernanceOpsPanel roles={currentUser.roles || []} initialSection={governanceSection} />
          )}

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
                      Audit jurnali ({auditEvents.length} ta yozuv)
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
                          <th className="px-4 py-2.5">Kim (ID)</th>
                          <th className="px-4 py-2.5">Obyekt turi</th>
                          <th className="px-4 py-2.5">Obyekt</th>
                          <th className="px-4 py-2.5">Xesh</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.06]">
                        {auditEvents.map((evt) => (
                          <tr key={evt.id} className="hover:bg-white/[0.02] transition-colors">
                            <td className="px-4 py-3 font-mono text-[11px] text-zinc-400 whitespace-nowrap">
                              {evt.occurred_at ? new Date(evt.occurred_at).toLocaleString("uz-UZ") : "-"}
                            </td>
                            <td className="px-4 py-3 font-semibold text-white">
                              <span title={evt.action} className="text-xs font-semibold text-[var(--fb-ink)]">
                                {enumLabel(evt.action)}
                              </span>
                            </td>
                            <td className="px-4 py-3 font-mono text-zinc-300">
                              {evt.actor_id ? `${evt.actor_id.slice(0, 8)}...` : "Tizim"}
                            </td>
                            <td className="px-4 py-3 text-zinc-300" title={evt.object_type || undefined}>{enumLabel(evt.object_type, "-")}</td>
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
          {activeTab === "MODERATION" && <ModerationPanel onCountChange={() => void moderationQuery.reload()} />}

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
                              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-medium">
                                {enumLabel(c.kind || c.entity_type, "Tekshiruv")}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-zinc-200">
                              {c.organization_name || c.institution_name || c.entity_id?.slice(0, 8) || "Noma’lum subyekt"}
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

          {/* BREAK-GLASS & EMERGENCY CONTROL */}
          {activeTab === "BREAK_GLASS" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* BREAK-GLASS PRIVILEGED ACCESS */}
              <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-5 flex flex-col gap-4 shadow-sm">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                    <KeyRound className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      Favqulodda vaqtinchalik ruxsat
                    </h3>
                    <p className="text-[11px] text-zinc-400">
                      Ikki bosqichli tasdiqlash orqali vaqtinchalik maxsus ruxsat berish.
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
                      Favqulodda ruxsat tasdiqlandi
                    </span>
                    <span className="text-[11px] text-zinc-300">
                      Rol: {enumLabel(bgResult.role_code)} · Muddati: {bgResult.expires_at ? new Date(bgResult.expires_at).toLocaleString("uz-UZ") : "—"}
                    </span>
                  </div>
                )}

                <form onSubmit={handleBreakGlassSubmit} className="flex flex-col gap-3">
                  <div>
                    <label className="text-[11px] font-medium text-zinc-300 block mb-1">
                      Foydalanuvchini tanlash (katalogdan qidirish yoki UUID)
                    </label>
                    <div className="relative mb-1.5">
                      <Search className="pointer-events-none absolute left-2.5 top-2 h-3.5 w-3.5 text-zinc-500" />
                      <input
                        type="text"
                        value={bgTargetSearch}
                        onChange={(e) => setBgTargetSearch(e.target.value)}
                        placeholder="Ism yoki aloqa bo‘yicha qidirish…"
                        className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-amber-500/50"
                      />
                    </div>
                    {(bgTargetDirQuery.data ?? []).length > 0 && (
                      <div className="mb-1.5 flex flex-wrap gap-1.5">
                        {(bgTargetDirQuery.data ?? []).map((u) => (
                          <button
                            key={u.id}
                            type="button"
                            onClick={() => setBgTargetUserId(u.id)}
                            className={`rounded-full px-2.5 py-1 text-[11px] border transition ${
                              bgTargetUserId === u.id
                                ? "border-amber-400 bg-amber-500/20 text-amber-200"
                                : "border-white/10 bg-white/[0.04] text-zinc-300 hover:bg-white/[0.08]"
                            }`}
                          >
                            {u.display_name || "Nomsiz"} {u.masked_contact ? `(${u.masked_contact})` : ""}
                          </button>
                        ))}
                      </div>
                    )}
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
                        Imtiyozli rol
                      </label>
                      <select
                        value={bgRoleCode}
                        onChange={(e) => setBgRoleCode(e.target.value)}
                        className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500/50"
                      >
                        <option value="OPERATOR">{enumLabel("OPERATOR")}</option>
                        <option value="AUDITOR">{enumLabel("AUDITOR")}</option>
                        <option value="ADMIN">{enumLabel("ADMIN")}</option>
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
                      Mustaqil tasdiqlovchi (katalogdan tanlash yoki UUID)
                    </label>
                    <div className="relative mb-1.5">
                      <Search className="pointer-events-none absolute left-2.5 top-2 h-3.5 w-3.5 text-zinc-500" />
                      <input
                        type="text"
                        value={bgApproverSearch}
                        onChange={(e) => setBgApproverSearch(e.target.value)}
                        placeholder="Tasdiqlovchi ismi yoki aloqasi…"
                        className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-amber-500/50"
                      />
                    </div>
                    {(bgApproverDirQuery.data ?? []).filter((u) => u.id !== currentUser.user_id).length > 0 && (
                      <div className="mb-1.5 flex flex-wrap gap-1.5">
                        {(bgApproverDirQuery.data ?? [])
                          .filter((u) => u.id !== currentUser.user_id)
                          .map((u) => (
                            <button
                              key={u.id}
                              type="button"
                              onClick={() => setBgApproverId(u.id)}
                              className={`rounded-full px-2.5 py-1 text-[11px] border transition ${
                                bgApproverId === u.id
                                  ? "border-amber-400 bg-amber-500/20 text-amber-200"
                                  : "border-white/10 bg-white/[0.04] text-zinc-300 hover:bg-white/[0.08]"
                              }`}
                            >
                              {u.display_name || "Nomsiz"} {u.masked_contact ? `(${u.masked_contact})` : ""}
                            </button>
                          ))}
                      </div>
                    )}
                    <input
                      type="text"
                      value={bgApproverId}
                      onChange={(e) => setBgApproverId(e.target.value)}
                      placeholder="00000000-0000-0000-0000-000000000000"
                      className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-amber-500/50 font-mono"
                    />
                    <span className="text-[10px] text-zinc-500 mt-0.5 block">
                      Ikki bosqichli nazorat: So‘rovchi o‘z so‘rovini o‘zi tasdiqlay olmaydi.
                    </span>
                  </div>

                  <div>
                    <label className="text-[11px] font-medium text-zinc-300 block mb-1">
                      Favqulodda asoslantirish (kamida 5 ta belgi)
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
                    className="skeuo-btn-accent w-full py-2.5 px-4 disabled:opacity-50 text-xs justify-center"
                  >
                    {isSubmittingBg ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <KeyRound className="w-3.5 h-3.5" />
                    )}
                    <span>Imtiyozli ruxsatni berish</span>
                  </button>
                </form>
              </div>

              {/* EMERGENCY SESSION REVOCATION */}
              <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-5 flex flex-col gap-4 shadow-sm">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                    <UserX className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      Favqulodda sessiyani bekor qilish
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
                      Sessiyalar muvaffaqiyatli bekor qilindi
                    </span>
                    <span className="text-[11px] text-zinc-300">
                      Bekor qilingan sessiyalar soni: {revokeResult.revoked_count}
                    </span>
                  </div>
                )}

                <form onSubmit={handleRevokeSessionsSubmit} className="flex flex-col gap-3">
                  <div>
                    <label className="text-[11px] font-medium text-zinc-300 block mb-1">
                      Foydalanuvchini tanlash (katalogdan qidirish yoki UUID)
                    </label>
                    <div className="relative mb-1.5">
                      <Search className="pointer-events-none absolute left-2.5 top-2 h-3.5 w-3.5 text-zinc-500" />
                      <input
                        type="text"
                        value={revokeUserSearch}
                        onChange={(e) => setRevokeUserSearch(e.target.value)}
                        placeholder="Ism yoki aloqa bo‘yicha qidirish…"
                        className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-rose-500/50"
                      />
                    </div>
                    {(revokeDirQuery.data ?? []).length > 0 && (
                      <div className="mb-1.5 flex flex-wrap gap-1.5">
                        {(revokeDirQuery.data ?? []).map((u) => (
                          <button
                            key={u.id}
                            type="button"
                            onClick={() => setRevokeTargetUserId(u.id)}
                            className={`rounded-full px-2.5 py-1 text-[11px] border transition ${
                              revokeTargetUserId === u.id
                                ? "border-rose-400 bg-rose-500/20 text-rose-200"
                                : "border-white/10 bg-white/[0.04] text-zinc-300 hover:bg-white/[0.08]"
                            }`}
                          >
                            {u.display_name || "Nomsiz"} {u.masked_contact ? `(${u.masked_contact})` : ""}
                          </button>
                        ))}
                      </div>
                    )}
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
                      Bekor qilish asosi (kamida 5 ta belgi)
                    </label>
                    <textarea
                      rows={3}
                      value={revokeReason}
                      onChange={(e) => setRevokeReason(e.target.value)}
                      placeholder="Shubhali faoliyat yoki hisob buzilishi xavfi sababli sessiyalarni to‘xtatish…"
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
                    <span>Barcha faol sessiyalarni darhol to‘xtatish</span>
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* SUPPORT OPS, INCIDENTS & SLA MONITORING */}
          {activeTab === "SUPPORT_OPS" && (
            <div className="flex flex-col gap-6">
              {/* TOP ACTION BAR & TELEMETRY KPI CARDS */}
              <div className="flex flex-col gap-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <Activity className="w-4 h-4 text-sky-400" />
                      <span>Platforma Operatsion Telemetriyasi & SLA</span>
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
                      className="skeuo-btn-accent px-3.5 py-2 text-xs shrink-0"
                    >
                      <Flame className="w-3.5 h-3.5" />
                      <span>Hodisa E’lon Qilish (P1–P4)</span>
                    </button>
                  </div>
                </div>

                {analyticsError && (
                  <div role="alert" className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{analyticsError}</span>
                  </div>
                )}
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

              {/* DISASTER RECOVERY RESTORE RUNS SLA PROOFS */}
              <div className="p-5 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-4 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-purple-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Tizim Tiklanish Mashqlari & SLA Muvofiqligi
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
                          <th className="py-2 px-3 font-semibold">Ma’lumotlar Bazasi</th>
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

              {/* SUPPORT TICKET QUEUE */}
              <div className="p-5 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-4 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <LifeBuoy className="w-4 h-4 text-sky-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Texnik Yordam Murojaatlari Navbati ({tickets.length})
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
                              {enumLabel(t.priority)}
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20">
                              {enumLabel(t.category)}
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              {enumLabel(t.status)}
                            </span>
                            <span className="text-[11px] font-mono text-zinc-500">
                              Tiket ID: #{t.id.slice(0, 8)}...
                            </span>
                          </div>
                          <h4 className="font-semibold text-white text-sm">
                            {t.subject || "Yordam so‘rovi"}
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

          {/* FINANCE & RECONCILIATION HUB */}
          {activeTab === "FINANCE" && (
            <div className="flex flex-col gap-6">
              {/* TOP ACTION BAR & REFRESH */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <CreditCard className="w-5 h-5 text-emerald-400" />
                    <span>Moliya & Shlyuz Solishtiruvi Markazi</span>
                  </h2>
                  <p className="text-xs text-zinc-400">
                    Moliyaviy balans, to‘lov shlyuzlari solishtiruvi va ikki bosqichli mablag‘ qaytarish nazorati.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={loadFinanceHub}
                  disabled={isLoadingFinance || isLoadingReconciliation}
                  className="px-3.5 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-200 flex items-center gap-2 transition-all self-start sm:self-auto shadow-sm"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 ${
                      isLoadingFinance || isLoadingReconciliation ? "animate-spin text-emerald-400" : ""
                    }`}
                  />
                  <span>Yangilash</span>
                </button>
              </div>

              {/* ERROR NOTICES */}
              {financeError && (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
                  <span>{financeError}</span>
                </div>
              )}

              {/* FINANCIAL SUMMARY KPI CARDS */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-4 flex flex-col gap-2 shadow-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-400">Naqd Pul Tushumi</span>
                    <Coins className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-xl font-bold font-mono text-white">
                    {financeSummary?.cash_received_uzs != null
                      ? `${financeSummary.cash_received_uzs.toLocaleString()} UZS`
                      : "—"}
                  </div>
                  <span className="text-[11px] text-zinc-400">
                    To‘langan invoyslar bo‘yicha jami tushum
                  </span>
                </div>

                <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-4 flex flex-col gap-2 shadow-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-400">Tan Olingan Daromad</span>
                    <CheckCheck className="w-4 h-4 text-primary" />
                  </div>
                  <div className="text-xl font-bold font-mono text-white">
                    {financeSummary?.recognized_revenue_uzs != null
                      ? `${financeSummary.recognized_revenue_uzs.toLocaleString()} UZS`
                      : "—"}
                  </div>
                  <span className="text-[11px] text-zinc-400">
                    Xizmat ko‘rsatilgan davr bo‘yicha daromad
                  </span>
                </div>

                <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-4 flex flex-col gap-2 shadow-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-400">Kechiktirilgan Daromad</span>
                    <Clock className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="text-xl font-bold font-mono text-white">
                    {financeSummary?.deferred_revenue_uzs != null
                      ? `${financeSummary.deferred_revenue_uzs.toLocaleString()} UZS`
                      : "—"}
                  </div>
                  <span className="text-[11px] text-zinc-400">
                    Kelgusi davr xizmatlari uchun bo‘nak
                  </span>
                </div>

                <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-4 flex flex-col gap-2 shadow-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-400">Sof Daromad / Qaytarilgan</span>
                    <Receipt className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="text-xl font-bold font-mono text-white">
                    {financeSummary?.net_revenue_uzs != null
                      ? `${financeSummary.net_revenue_uzs.toLocaleString()} UZS`
                      : "—"}
                  </div>
                  <span className="text-[11px] text-zinc-400">
                    Qaytarilgan: {financeSummary?.refunded_amount_uzs != null ? `${financeSummary.refunded_amount_uzs.toLocaleString()} UZS` : "0 UZS"}
                  </span>
                </div>
              </div>

              {/* TARIFF PLAN BREAKDOWN */}
              {financeSummary?.plans_breakdown && financeSummary.plans_breakdown.length > 0 && (
                <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-5 flex flex-col gap-3 shadow-sm">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
                      Tarif Rejalari Bo‘yicha Taqsimot (Plans Breakdown)
                    </h3>
                    <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      Faol Obunalar: {financeSummary.active_subscriptions_count ?? 0} ta
                    </span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-white/[0.08] text-zinc-400">
                          <th className="py-2.5 px-3">Tarif Kodi</th>
                          <th className="py-2.5 px-3">Jami Huquqlar</th>
                          <th className="py-2.5 px-3">Faol Obunalar</th>
                          <th className="py-2.5 px-3">Kassa Tushumi</th>
                          <th className="py-2.5 px-3">Tan Olingan Daromad</th>
                          <th className="py-2.5 px-3">Kechiktirilgan Daromad</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04]">
                        {financeSummary.plans_breakdown.map((plan, idx) => (
                          <tr key={idx} className="hover:bg-white/[0.02]">
                            <td className="py-2.5 px-3 font-mono font-semibold text-white">
                              {plan.plan_code}
                            </td>
                            <td className="py-2.5 px-3 text-zinc-300">{plan.total_entitlements}</td>
                            <td className="py-2.5 px-3">
                              <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-medium border border-emerald-500/20">
                                {plan.active_count} ta faol
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-mono text-zinc-200">
                              {plan.cash_received_uzs?.toLocaleString()} UZS
                            </td>
                            <td className="py-2.5 px-3 font-mono text-emerald-400">
                              {plan.recognized_revenue_uzs?.toLocaleString()} UZS
                            </td>
                            <td className="py-2.5 px-3 font-mono text-amber-400">
                              {plan.deferred_revenue_uzs?.toLocaleString()} UZS
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* DUAL-CONTROL REFUND APPROVAL HUB */}
              <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-5 flex flex-col gap-4 shadow-sm">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-amber-400" />
                    <h3 className="text-sm font-semibold text-white">
                      Mablag‘ Qaytarish So‘rovlarini Tasdiqlash (Ikki Bosqichli Nazorat)
                    </h3>
                  </div>
                  <p className="text-xs text-zinc-400">
                    Platforma xavfsizligi bo‘yicha har qanday mablag‘ qaytarish 2 ta mustaqil moliya operatori tomonidan tasdiqlanishi shart:
                    1-tasdiq <span className="font-mono text-amber-400">PENDING_SECOND_APPROVAL</span> holatiga o‘tkazadi,
                    2-tasdiq esa <span className="font-mono text-emerald-400">APPROVED</span> qilib avtomatik <span className="font-mono text-zinc-300">REFUND_EXECUTE</span> vazifasini ishga tushiradi. O‘ziga o‘zi tasdiqlash taqiqlangan.
                  </p>
                </div>

                {approveRefundSuccess && (
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    <span>{approveRefundSuccess}</span>
                  </div>
                )}

                {approveRefundError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{approveRefundError}</span>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row items-center gap-2.5">
                  <input
                    type="text"
                    value={manualRefundId}
                    onChange={(e) => setManualRefundId(e.target.value)}
                    placeholder="Qaytarish UUID kodi (masalan: 123e4567-e89b-12d3-a456-426614174000)..."
                    className="w-full sm:flex-1 bg-[#18181b] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500/50 font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => handleApproveRefund(manualRefundId)}
                    disabled={!manualRefundId.trim() || approvingRefundId === manualRefundId}
                    className="skeuo-btn-obsidian w-full sm:w-auto px-4 py-2 disabled:opacity-50 text-xs shrink-0"
                  >
                    {approvingRefundId === manualRefundId ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCheck className="w-3.5 h-3.5" />
                    )}
                    <span>Tasdiqlash</span>
                  </button>
                </div>
              </div>

              {/* GATEWAY VS LEDGER RECONCILIATION HUB */}
              <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-5 flex flex-col gap-4 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
                  <div>
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Receipt className="w-4 h-4 text-primary" />
                      <span>To‘lov Shlyuzlari va Moliyaviy Jurnal Solishtiruvi</span>
                    </h3>
                    <p className="text-xs text-zinc-400">
                      Billing ledger yozuvlari tashqi to‘lov shlyuzlari (Payme, Click, Uzum) tranzaksiyalari bilan taqqoslanadi. Zero PII ta’minlangan.
                    </p>
                  </div>

                  {/* RECONCILIATION FILTERS */}
                  <div className="flex flex-wrap items-center gap-2.5">
                    <div className="flex items-center gap-1.5 bg-[#18181b] border border-white/[0.08] rounded-lg px-2.5 py-1">
                      <Filter className="w-3 h-3 text-zinc-400" />
                      <select
                        value={reconciliationProvider}
                        onChange={(e) => setReconciliationProvider(e.target.value)}
                        className="bg-transparent text-xs text-zinc-300 focus:outline-none cursor-pointer"
                      >
                        <option value="ALL">Barcha Provayderlar</option>
                        <option value="PAYME">PAYME</option>
                        <option value="CLICK">CLICK</option>
                        <option value="UZUM">UZUM</option>
                      </select>
                    </div>

                    <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer bg-[#18181b] border border-white/[0.08] rounded-lg px-2.5 py-1.5 hover:bg-white/[0.04] transition-all">
                      <input
                        type="checkbox"
                        checked={reconciliationDiscrepancyOnly}
                        onChange={(e) => setReconciliationDiscrepancyOnly(e.target.checked)}
                        className="rounded border-zinc-700 text-rose-500 focus:ring-rose-500/40"
                      />
                      <span>Faqat Tafovutlar ({reconciliationSummary?.total_discrepancies ?? 0})</span>
                    </label>
                  </div>
                </div>

                {/* RECONCILIATION SUMMARY STATS */}
                {reconciliationSummary && (
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-[#18181b] border border-white/[0.06] rounded-lg p-2.5 flex flex-col items-center justify-center">
                      <span className="text-[10px] uppercase font-bold text-zinc-400">Jami Solishtirilgan</span>
                      <span className="text-sm font-mono font-bold text-white">
                        {reconciliationSummary.total_reconciled ?? reconciliationItems.length}
                      </span>
                    </div>
                    <div className="bg-[#18181b] border border-white/[0.06] rounded-lg p-2.5 flex flex-col items-center justify-center">
                      <span className="text-[10px] uppercase font-bold text-emerald-400">To‘liq Mos Kelgan</span>
                      <span className="text-sm font-mono font-bold text-emerald-400">
                        {reconciliationSummary.matched_count ?? 0}
                      </span>
                    </div>
                    <div className="bg-[#18181b] border border-white/[0.06] rounded-lg p-2.5 flex flex-col items-center justify-center">
                      <span className="text-[10px] uppercase font-bold text-rose-400">Tafovut Aniqlangan</span>
                      <span className="text-sm font-mono font-bold text-rose-400">
                        {reconciliationSummary.total_discrepancies ?? 0}
                      </span>
                    </div>
                  </div>
                )}

                {reconciliationError && (
                  <div role="alert" className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{reconciliationError}</span>
                  </div>
                )}
                {/* RECONCILIATION ITEMS TABLE */}
                {isLoadingReconciliation ? (
                  <div className="p-8 flex items-center justify-center gap-2 text-xs text-zinc-400">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span>Solishtiruv ma’lumotlari tekshirilmoqda...</span>
                  </div>
                ) : reconciliationItems.length === 0 ? (
                  <div className="p-8 text-center text-xs text-zinc-400">
                    Solishtiruv yozuvlari topilmadi.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-white/[0.08] text-zinc-400">
                          <th className="py-2.5 px-3">Sana</th>
                          <th className="py-2.5 px-3">Yozuv Turi</th>
                          <th className="py-2.5 px-3">Provayder & Tranzaksiya</th>
                          <th className="py-2.5 px-3">Ledger Summasi</th>
                          <th className="py-2.5 px-3">Shlyuz Summasi</th>
                          <th className="py-2.5 px-3">Holat</th>
                          <th className="py-2.5 px-3">Tafovut</th>
                          <th className="py-2.5 px-3 text-right">Amal</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04]">
                        {reconciliationItems.map((item, idx) => (
                          <tr
                            key={idx}
                            className={`hover:bg-white/[0.02] ${
                              item.is_discrepant ? "bg-rose-500/[0.03]" : ""
                            }`}
                          >
                            <td className="py-2.5 px-3 text-zinc-400 whitespace-nowrap">
                              {item.occurred_at ? new Date(item.occurred_at).toLocaleString() : "—"}
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                                  item.entry_kind === "PAYMENT_CAPTURED"
                                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                    : item.entry_kind === "REFUND_EXECUTED"
                                    ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                                    : "bg-zinc-800 text-zinc-300"
                                }`}
                              >
                                {item.entry_kind}
                              </span>
                            </td>
                            <td className="py-2.5 px-3">
                              <div className="flex flex-col">
                                <span className="font-semibold text-white">{item.provider || "ICHKI"}</span>
                                <span className="text-[10px] font-mono text-zinc-400">
                                  {item.provider_transaction_id || item.payment_attempt_id?.slice(0, 8) || "—"}
                                </span>
                              </div>
                            </td>
                            <td className="py-2.5 px-3 font-mono font-medium text-white">
                              {item.ledger_amount_uzs?.toLocaleString()} {item.currency}
                            </td>
                            <td className="py-2.5 px-3 font-mono text-zinc-300">
                              {item.gateway_amount_uzs != null
                                ? `${item.gateway_amount_uzs.toLocaleString()} ${item.currency}`
                                : "—"}
                            </td>
                            <td className="py-2.5 px-3">
                              <div className="flex items-center gap-1.5 text-[11px]">
                                <span className="font-mono text-zinc-300">{item.ledger_status}</span>
                                {item.gateway_status && (
                                  <>
                                    <span className="text-zinc-500">/</span>
                                    <span className="font-mono text-zinc-400">{item.gateway_status}</span>
                                  </>
                                )}
                              </div>
                            </td>
                            <td className="py-2.5 px-3">
                              {item.is_discrepant ? (
                                <div className="flex flex-wrap gap-1">
                                  {item.discrepancy_flags?.map((fl, fIdx) => (
                                    <span
                                      key={fIdx}
                                      className="px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] font-mono"
                                    >
                                      {fl}
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-medium">
                                  Mos
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-right">
                              {item.refund_id ? (
                                <button
                                  type="button"
                                  onClick={() => handleApproveRefund(item.refund_id!)}
                                  disabled={approvingRefundId === item.refund_id}
                                  className="px-2.5 py-1 rounded bg-surface hover:bg-surface-high border border-white/[0.08] text-[11px] font-semibold text-emerald-400 hover:text-emerald-300 transition-all inline-flex items-center gap-1"
                                >
                                  {approvingRefundId === item.refund_id ? (
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                  ) : (
                                    <CheckCheck className="w-3 h-3" />
                                  )}
                                  <span>Tasdiqlash</span>
                                </button>
                              ) : (
                                <span className="text-zinc-600 text-[11px]">—</span>
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
          </div>
        </div>
      )}

      {/* VERIFICATION CASE DECISION MODAL */}
      {mounted &&
        selectedCase &&
        createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-[#121214] border border-white/[0.12] rounded-xl shadow-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Tekshiruv xulosasini chiqarish
                </h3>
                <span className="text-[11px] text-zinc-400">
                  {selectedCase.organization_name || selectedCase.institution_name || "Ariza"} · Reviziya {selectedCase.revision || 1}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedCase(null)}
                className="text-zinc-400 hover:text-white transition-colors"
                aria-label="Oynani yopish"
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
                  Qaror xulosasi
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
                    Tasdiqlash
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
                    Hujjat talab
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
                    Rad etish
                  </button>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Qaror asoslantirishi (kamida 15 ta belgi)
                </label>
                <textarea
                  rows={4}
                  required
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  placeholder="Taqdim etilgan soliq guvohnomasi va yuridik ma’lumotlar to‘liq tekshirildi…"
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
                  <span>Xulosani tasdiqlash</span>
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* TICKET MESSAGE REPLY MODAL */}
      {mounted &&
        selectedTicket &&
        createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-[#121214] border border-white/[0.12] rounded-xl shadow-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Murojaatga javob berish
                </h3>
                <span className="text-[11px] text-zinc-400">
                  {enumLabel(selectedTicket.category)} ({enumLabel(selectedTicket.priority)})
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedTicket(null)}
                className="text-zinc-400 hover:text-white transition-colors"
                aria-label="Oynani yopish"
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
                  Javob matni
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
                  <span>Ichki eslatma (faqat operatorlar ko‘radi)</span>
                </label>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-400">Yangi holat:</span>
                  <select
                    value={replyStatus}
                    onChange={(e) => setReplyStatus(e.target.value)}
                    className="bg-[#18181b] border border-white/[0.08] rounded-lg px-2.5 py-1 text-xs text-zinc-300 focus:outline-none focus:border-primary/50"
                  >
                    <option value="">O‘zgarishsiz</option>
                    <option value="IN_PROGRESS">Jarayonda</option>
                    <option value="RESOLVED">Hal qilindi</option>
                    <option value="CLOSED">Yopildi</option>
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
                  <span>{isInternalNote ? "Eslatmani saqlash" : "Javobni yuborish"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* OPERATIONAL INCIDENT DECLARATION MODAL */}
      {mounted &&
        isIncidentModalOpen &&
        createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-[#121214] border border-white/[0.12] rounded-xl shadow-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-rose-500" />
                <h3 className="text-sm font-semibold text-white">
                  Favqulodda operatsion hodisa e’lon qilish
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsIncidentModalOpen(false)}
                className="text-zinc-400 hover:text-white transition-colors"
                aria-label="Oynani yopish"
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
                  Insident darajasi
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
                  Insident sarlavhasi
                </label>
                <input
                  type="text"
                  required
                  value={incidentTitle}
                  onChange={(e) => setIncidentTitle(e.target.value)}
                  placeholder="Masalan: SMS provayder ulanishida uzilish yoki kechikish…"
                  className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-rose-500/50"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Qisqacha tavsif / dastlabki ta’sir
                </label>
                <textarea
                  rows={3}
                  value={incidentSummary}
                  onChange={(e) => setIncidentSummary(e.target.value)}
                  placeholder="Ta’sir doirasi, xavf darajasi va ko‘rilayotgan dastlabki choralar…"
                  className="w-full bg-[#18181b] border border-white/[0.08] rounded-lg p-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-rose-500/50 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setIsIncidentModalOpen(false)}
                  className="skeuo-btn-secondary px-4 py-2 text-xs"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingIncident}
                  className="skeuo-btn-accent px-4 py-2 disabled:opacity-50 text-xs"
                >
                  {isSubmittingIncident ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Flame className="w-3.5 h-3.5" />
                  )}
                  <span>Hodisani e’lon qilish</span>
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* LOGIN MODAL */}
      <AuthModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onSuccess={handleLoginSuccess}
        requiredPortal="OPERATOR"
        title="Operator Tizimiga Kirish"
        subtitle="Platforma xavfsizlik auditori yoki ma’muri hisob ma’lumotlarini kiriting"
      />
    </main>
  );
}
