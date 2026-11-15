"use client";

import { useEffect, useState, useCallback } from "react";
import {
  CheckCircle2,
  AlertCircle,
  GraduationCap,
  Loader2,
  LogIn,
  LogOut,
  FileCheck,
  BookOpen,
  Award,
  Users,
  RefreshCw,
  ShieldCheck,
  Send,
  UserCheck,
  X,
  Download,
  FileSpreadsheet,
  Building2,
  BarChart3,
  TrendingUp,
  Clock,
  Activity,
  Filter,
  Search,
  AlertTriangle,
} from "lucide-react";
import {
  fetchAuthMe,
  fetchUniversityReviewQueue,
  fetchTeacherAcademicAssignments,
  fetchPlacementDecisionContext,
  submitAcademicPlacementConclusion,
  fetchCoordinatorAssignmentQueue,
  assignTeacherToPlacement,
  generateInstitutionExport,
  fetchInstitutionSupervisions,
  fetchInstitutionAcademicAgreements,
  fetchUniversityAnalytics,
  logoutUser,
  AuthUser,
  AcademicReviewQueueItem,
  TeacherAcademicAssignmentItem,
  AcademicDecisionContext,
  CoordinatorAssignmentQueueItem,
  AcademicTeacherOption,
  InstitutionExportReceipt,
  StudentSupervisionItem,
  AcademicAgreementItem,
  UniversityAnalyticsResponse,
  StudentAttendanceItem,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";
import AcademicReviewModal from "@/components/AcademicReviewModal";

export default function UniversityPortal() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Active Tab: "queue" | "assignments" | "coordinator" | "exports" | "analytics"
  const [activeTab, setActiveTab] = useState<"queue" | "assignments" | "coordinator" | "exports" | "analytics">("queue");

  // TAB 1: Daily Log Review Queue (API-105)
  const [queueItems, setQueueItems] = useState<AcademicReviewQueueItem[]>([]);
  const [isLoadingQueue, setIsLoadingQueue] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [selectedReviewItem, setSelectedReviewItem] = useState<AcademicReviewQueueItem | null>(null);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);

  // TAB 2: Teacher Assigned Placements & Conclusions (API-104 / API-108)
  const [assignments, setAssignments] = useState<TeacherAcademicAssignmentItem[]>([]);
  const [isLoadingAssignments, setIsLoadingAssignments] = useState(false);
  const [assignmentsError, setAssignmentsError] = useState<string | null>(null);

  // Placement Conclusion Modal State
  const [selectedPlacementId, setSelectedPlacementId] = useState<string | null>(null);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<string | null>(null);
  const [isConclusionModalOpen, setIsConclusionModalOpen] = useState(false);
  const [conclusionContext, setConclusionContext] = useState<AcademicDecisionContext | null>(null);
  const [isLoadingContext, setIsLoadingContext] = useState(false);
  const [conclusionDecision, setConclusionDecision] = useState<"ACADEMIC_REVIEW_COMPLETE" | "ACADEMIC_REVISION_REQUIRED">("ACADEMIC_REVIEW_COMPLETE");
  const [conclusionReason, setConclusionReason] = useState("");
  const [isSubmittingConclusion, setIsSubmittingConclusion] = useState(false);
  const [conclusionStatusMsg, setConclusionStatusMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // TAB 3: Coordinator Assignment Queue & Teacher Nomination (API-103 / API-102)
  const [coordinatorQueue, setCoordinatorQueue] = useState<CoordinatorAssignmentQueueItem[]>([]);
  const [teachersList, setTeachersList] = useState<AcademicTeacherOption[]>([]);
  const [institutionId, setInstitutionId] = useState<string | null>(null);
  const [isLoadingCoord, setIsLoadingCoord] = useState(false);
  const [coordError, setCoordError] = useState<string | null>(null);

  // Nomination Modal State
  const [nominatePlacement, setNominatePlacement] = useState<CoordinatorAssignmentQueueItem | null>(null);
  const [selectedTeacherId, setSelectedTeacherId] = useState<string>("");
  const [isNominateModalOpen, setIsNominateModalOpen] = useState(false);
  const [isSubmittingNominate, setIsSubmittingNominate] = useState(false);
  const [nominateStatusMsg, setNominateStatusMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // TAB 4: Reports & Academic Agreements (API-100, API-098, API-101)
  const [exportFormat, setExportFormat] = useState<"PDF" | "JSON">("PDF");
  const [includeDetails, setIncludeDetails] = useState(true);
  const [isGeneratingExport, setIsGeneratingExport] = useState(false);
  const [exportReceipt, setExportReceipt] = useState<InstitutionExportReceipt | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const [supervisions, setSupervisions] = useState<StudentSupervisionItem[]>([]);
  const [isLoadingSupervisions, setIsLoadingSupervisions] = useState(false);
  const [supervisionsError, setSupervisionsError] = useState<string | null>(null);

  const [academicAgreements, setAcademicAgreements] = useState<AcademicAgreementItem[]>([]);
  const [isLoadingAgreements, setIsLoadingAgreements] = useState(false);
  const [agreementsError, setAgreementsError] = useState<string | null>(null);

  // TAB 5: Analytics & Monitoring (API-125)
  const [analyticsData, setAnalyticsData] = useState<UniversityAnalyticsResponse | null>(null);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [analyticsFilters, setAnalyticsFilters] = useState<{
    program: string;
    status: string;
    fromDate: string;
    toDate: string;
  }>({
    program: "",
    status: "",
    fromDate: "",
    toDate: "",
  });
  const [studentSearchTerm, setStudentSearchTerm] = useState("");

  const loadQueue = useCallback(async () => {
    setIsLoadingQueue(true);
    setQueueError(null);
    try {
      const items = await fetchUniversityReviewQueue();
      setQueueItems(items);
    } catch (err: unknown) {
      setQueueError(err instanceof Error ? err.message : "Navbatni yuklashda xatolik yuz berdi");
    } finally {
      setIsLoadingQueue(false);
    }
  }, []);

  const loadAssignments = useCallback(async () => {
    setIsLoadingAssignments(true);
    setAssignmentsError(null);
    try {
      const items = await fetchTeacherAcademicAssignments();
      setAssignments(items);
    } catch (err: unknown) {
      setAssignmentsError(err instanceof Error ? err.message : "Biriktirilgan amaliyotlarni yuklashda xatolik yuz berdi");
    } finally {
      setIsLoadingAssignments(false);
    }
  }, []);

  const loadCoordinatorQueue = useCallback(async () => {
    setIsLoadingCoord(true);
    setCoordError(null);
    try {
      const data = await fetchCoordinatorAssignmentQueue();
      setCoordinatorQueue(data.items);
      setTeachersList(data.teachers);
      if (data.institution_id) setInstitutionId(data.institution_id);
    } catch (err: unknown) {
      setCoordError(err instanceof Error ? err.message : "Kafedra navbatini yuklashda xatolik yuz berdi");
    } finally {
      setIsLoadingCoord(false);
    }
  }, []);

  const loadReportsAndAgreements = useCallback(async (targetInstId: string) => {
    if (!targetInstId) return;
    setIsLoadingSupervisions(true);
    setSupervisionsError(null);
    setIsLoadingAgreements(true);
    setAgreementsError(null);

    try {
      const sups = await fetchInstitutionSupervisions(targetInstId);
      setSupervisions(sups);
    } catch (err: unknown) {
      setSupervisionsError(err instanceof Error ? err.message : "Superviziyalarni yuklashda xatolik.");
      setSupervisions([]);
    } finally {
      setIsLoadingSupervisions(false);
    }

    try {
      const agrs = await fetchInstitutionAcademicAgreements(targetInstId);
      setAcademicAgreements(agrs);
    } catch (err: unknown) {
      setAgreementsError(err instanceof Error ? err.message : "Shartnomalarni yuklashda xatolik.");
      setAcademicAgreements([]);
    } finally {
      setIsLoadingAgreements(false);
    }
  }, []);

  const loadAnalytics = useCallback(
    async (targetInstId?: string, customFilters?: typeof analyticsFilters) => {
      const inst = targetInstId || institutionId;
      if (!inst) return;
      setIsLoadingAnalytics(true);
      setAnalyticsError(null);
      try {
        const f = customFilters || analyticsFilters;
        const res = await fetchUniversityAnalytics(inst, {
          program: f.program || undefined,
          status: f.status || undefined,
          from_date: f.fromDate || undefined,
          to_date: f.toDate || undefined,
        });
        setAnalyticsData(res);
      } catch (err: unknown) {
        setAnalyticsError(
          err instanceof Error ? err.message : "Analitika ma'lumotlarini yuklashda xatolik yuz berdi"
        );
      } finally {
        setIsLoadingAnalytics(false);
      }
    },
    [institutionId, analyticsFilters]
  );

  const handleGenerateExport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institutionId) {
      setExportError("Muassasa ID aniqlanmadi.");
      return;
    }
    setIsGeneratingExport(true);
    setExportError(null);
    try {
      const receipt = await generateInstitutionExport(institutionId, {
        format: exportFormat,
        include_details: includeDetails,
      });
      setExportReceipt(receipt);
      // reload supervisions & agreements
      await loadReportsAndAgreements(institutionId);
    } catch (err: unknown) {
      setExportError(err instanceof Error ? err.message : "Hisobotni yaratishda xatolik yuz berdi.");
    } finally {
      setIsGeneratingExport(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    fetchAuthMe().then((user) => {
      if (isMounted) {
        setCurrentUser(user);
        setIsAuthLoading(false);
        if (user) {
          loadQueue();
          loadAssignments();
          loadCoordinatorQueue();
        }
      }
    });
    return () => {
      isMounted = false;
    };
  }, [loadQueue, loadAssignments, loadCoordinatorQueue]);

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setQueueItems([]);
    setAssignments([]);
    setCoordinatorQueue([]);
    setQueueError(null);
    setAssignmentsError(null);
    setCoordError(null);
    setIsReviewModalOpen(false);
    setSelectedReviewItem(null);
    setIsConclusionModalOpen(false);
    setIsNominateModalOpen(false);
  };

  const handleOpenReview = (item: AcademicReviewQueueItem) => {
    setSelectedReviewItem(item);
    setIsReviewModalOpen(true);
  };

  const handleOpenConclusionModal = async (placementId: string, assignmentId: string) => {
    setSelectedPlacementId(placementId);
    setSelectedAssignmentId(assignmentId);
    setConclusionStatusMsg(null);
    setConclusionReason("");
    setConclusionDecision("ACADEMIC_REVIEW_COMPLETE");
    setIsConclusionModalOpen(true);
    setIsLoadingContext(true);

    try {
      const ctx = await fetchPlacementDecisionContext(placementId, assignmentId);
      setConclusionContext(ctx);
    } catch (err: unknown) {
      setConclusionStatusMsg({
        type: "error",
        text: err instanceof Error ? err.message : "Kontekstni yuklashda xatolik yuz berdi",
      });
    } finally {
      setIsLoadingContext(false);
    }
  };

  const handleSubmitConclusion = async () => {
    if (!selectedPlacementId) return;
    if (conclusionReason.trim().length < 1) {
      setConclusionStatusMsg({ type: "error", text: "Xulosa asosi kamida 1 belgidan iborat bo'lishi shart." });
      return;
    }

    setIsSubmittingConclusion(true);
    setConclusionStatusMsg(null);

    try {
      await submitAcademicPlacementConclusion(selectedPlacementId, {
        decision: conclusionDecision,
        reason: conclusionReason.trim(),
        academic_assignment_id: selectedAssignmentId || undefined,
        terms_id: conclusionContext?.terms_id,
        version: conclusionContext?.version,
        expected_basis_digest: conclusionContext?.basis_digest,
      });

      setConclusionStatusMsg({
        type: "success",
        text: "Yakuniy akademik xulosa muvaffaqiyatli topshirildi va qayd etildi.",
      });

      // Refresh context and assignments
      loadAssignments();
      const updatedCtx = await fetchPlacementDecisionContext(selectedPlacementId, selectedAssignmentId || undefined);
      setConclusionContext(updatedCtx);
    } catch (err: unknown) {
      setConclusionStatusMsg({
        type: "error",
        text: err instanceof Error ? err.message : "Xulosa topshirishda xatolik yuz berdi",
      });
    } finally {
      setIsSubmittingConclusion(false);
    }
  };

  const handleOpenNominateModal = (item: CoordinatorAssignmentQueueItem) => {
    setNominatePlacement(item);
    setSelectedTeacherId("");
    setNominateStatusMsg(null);
    setIsNominateModalOpen(true);
  };

  const handleSubmitNomination = async () => {
    if (!nominatePlacement || !selectedTeacherId || !institutionId) {
      setNominateStatusMsg({ type: "error", text: "O'qituvchi va muassasa tanlanishi shart." });
      return;
    }

    setIsSubmittingNominate(true);
    setNominateStatusMsg(null);

    try {
      await assignTeacherToPlacement(nominatePlacement.placement_id, {
        institution_id: institutionId,
        supervisor_id: selectedTeacherId,
        supervision_id: nominatePlacement.id,
      });

      setNominateStatusMsg({
        type: "success",
        text: "O'qituvchi ushbu amaliyotga muvaffaqiyatli biriktirildi.",
      });

      loadCoordinatorQueue();
      setTimeout(() => {
        setIsNominateModalOpen(false);
      }, 1200);
    } catch (err: unknown) {
      setNominateStatusMsg({
        type: "error",
        text: err instanceof Error ? err.message : "Biriktirishda xatolik yuz berdi",
      });
    } finally {
      setIsSubmittingNominate(false);
    }
  };

  const handleLoginSuccess = (user: AuthUser) => {
    setCurrentUser(user);
    loadQueue();
    loadAssignments();
    loadCoordinatorQueue();
  };

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* HEADER BAR */}
      <section className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                Universitet Portali
              </span>
              <span className="text-zinc-500 text-xs font-mono">• API-105 / API-108 / API-103</span>
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
            <h1 className="font-heading text-lg md:text-xl font-bold text-zinc-100">
              Akademik Nazorat, Amaliyotlar & Xulosalar Markazi
            </h1>
            <p className="text-xs text-zinc-400">
              Kafedra o‘qituvchilari va mas’ul koordinatorlar uchun talabalar amaliyotini to‘liq ilmiy-akademik boshqarish.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {isAuthLoading ? (
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span>Yuklanmoqda...</span>
              </div>
            ) : currentUser ? (
              <button
                type="button"
                onClick={handleLogout}
                className="px-3.5 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-rose-300 hover:text-rose-200 transition-all flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 active:scale-[0.98]"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Chiqish</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIsLoginModalOpen(true)}
                className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>O‘qituvchi sifatida kirish</span>
              </button>
            )}
          </div>
        </div>

        {/* NAVIGATION TABS */}
        {currentUser && (
          <div className="mt-6 flex border-b border-white/[0.08] gap-1 overflow-x-auto">
            <button
              type="button"
              onClick={() => setActiveTab("queue")}
              className={`pb-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "queue"
                  ? "border-primary text-primary"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <FileCheck className="w-4 h-4" />
              <span>Kundaliklar Navbati</span>
              <span className="ml-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">
                {queueItems.length}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("assignments")}
              className={`pb-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "assignments"
                  ? "border-primary text-primary"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <BookOpen className="w-4 h-4" />
              <span>Biriktirilgan Amaliyotlar & Xulosalar</span>
              <span className="ml-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">
                {assignments.length}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("coordinator")}
              className={`pb-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "coordinator"
                  ? "border-primary text-primary"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Users className="w-4 h-4" />
              <span>Kafedra Taqsimot Navbati</span>
              <span className="ml-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">
                {coordinatorQueue.length}
              </span>
            </button>

            <button
              type="button"
              onClick={() => {
                setActiveTab("exports");
                if (institutionId) {
                  loadReportsAndAgreements(institutionId);
                }
              }}
              className={`pb-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "exports"
                  ? "border-primary text-primary"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>Yig&apos;ma Hisobotlar & Shartnomalar</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setActiveTab("analytics");
                if (institutionId) {
                  loadAnalytics(institutionId);
                } else {
                  loadCoordinatorQueue();
                }
              }}
              className={`pb-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "analytics"
                  ? "border-primary text-primary"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span>Analitika & Monitoring</span>
            </button>
          </div>
        )}
      </section>

      {/* UNAUTHENTICATED STATE */}
      {!currentUser && !isAuthLoading && (
        <section className="w-full bg-surface-card/60 border border-white/[0.08] rounded-xl p-8 flex flex-col items-center justify-center text-center gap-4 py-16">
          <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <GraduationCap className="w-7 h-7" />
          </div>
          <div className="flex flex-col gap-1 max-w-md">
            <h2 className="text-base md:text-lg font-heading font-semibold text-white">
              Akademik portalga kirish talab etiladi
            </h2>
            <p className="text-xs text-zinc-400">
              Talabalarning amaliyot kundaliklarini baholash, yakuniy akademik xulosalarni rasmiylashtirish yoki o‘qituvchilarni biriktirish uchun tizimga kiring.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsLoginModalOpen(true)}
            className="mt-2 px-5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-2 shadow-lg shadow-primary/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
          >
            <LogIn className="w-4 h-4" />
            <span>Tizimga kirish</span>
          </button>
        </section>
      )}

      {/* TAB 1: DAILY LOGS REVIEW QUEUE */}
      {currentUser && activeTab === "queue" && (
        <div className="flex flex-col gap-6">
          {queueError && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{queueError}</span>
            </div>
          )}

          {isLoadingQueue ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-3 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span className="text-xs">Akademik ko‘rib chiqish navbati yuklanmoqda...</span>
            </div>
          ) : queueItems.length === 0 ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-2 text-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mb-1" />
              <h3 className="text-sm font-semibold text-white">Ko‘rib chiqish navbati bo‘sh</h3>
              <p className="text-xs text-zinc-400 max-w-md">
                Sizga biriktirilgan talabalarning barcha topshirilgan amaliyot kundaliklari to‘liq ko‘rib chiqilgan.
              </p>
            </div>
          ) : (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl overflow-hidden shadow-sm">
              <div className="px-5 py-3.5 border-b border-white/[0.08] flex items-center justify-between">
                <span className="text-xs font-semibold text-white">
                  Kutilayotgan kundaliklar ({queueItems.length} ta)
                </span>
                <button
                  type="button"
                  onClick={loadQueue}
                  className="text-xs text-primary hover:underline flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Yangilash</span>
                </button>
              </div>

              <div className="divide-y divide-white/[0.06]">
                {queueItems.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 hover:bg-white/[0.02] transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">
                          {item.student_name || "Talaba"}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                          Rev #{item.revision}
                        </span>
                        <span className="text-xs text-zinc-400">• Sana: {item.local_date}</span>
                      </div>
                      <div className="text-xs text-zinc-400 flex flex-wrap items-center gap-2">
                        <span>Maqsad: {item.purpose}</span>
                        <span>•</span>
                        <span className="font-mono text-[11px]">
                          Amaliyot ID: {item.placement_id.slice(0, 8)}...
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <span className="text-[11px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                        Ko‘rib chiqish kutilmoqda
                      </span>
                      <button
                        type="button"
                        onClick={() => handleOpenReview(item)}
                        className="px-3.5 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-sm shadow-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
                      >
                        <FileCheck className="w-3.5 h-3.5" />
                        <span>Ko‘rib chiqish</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: REPORTS & ACADEMIC AGREEMENTS (API-100, API-098, API-101) */}
      {currentUser && activeTab === "exports" && (
        <div className="flex flex-col gap-6">
          {/* Header Card */}
          <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Hisobot & Shartnomalar Hub
                </span>
                <span className="text-zinc-500 text-xs font-mono">• API-100, API-098, API-101</span>
              </div>
              <h2 className="font-heading text-base md:text-lg font-bold text-white">
                Muassasa Yig&apos;ma Hisoboti va Hamkorlik Shartnomalari
              </h2>
              <p className="text-xs text-zinc-400">
                Talabalar amaliyoti, o&apos;quv rejalari va soatlar sarfi bo&apos;yicha rasmiy PDF va JSON hisobotlarini shakllantirish (CAP-026 / API-100) hamda faol hamkorlik shartnomalari nazorati.
              </p>
            </div>

            {institutionId && (
              <button
                type="button"
                disabled={isLoadingSupervisions || isLoadingAgreements}
                onClick={() => loadReportsAndAgreements(institutionId)}
                className="px-3.5 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300 hover:text-white transition-all flex items-center gap-1.5 self-start md:self-center disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingSupervisions || isLoadingAgreements ? "animate-spin" : ""}`} />
                <span>Yangilash</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Columns: Report Generator & Generated Receipt */}
            <div className="lg:col-span-2 flex flex-col gap-5">
              {/* Generator Form */}
              <div className="p-5 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-4 shadow-sm">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="w-4 h-4 text-primary" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Rasmiy Yig&apos;ma Hisobot Yaratish (API-100)
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500">CAP-026 / REPORT_EXPORT</span>
                </div>

                <form onSubmit={handleGenerateExport} className="flex flex-col gap-4">
                  {exportError && (
                    <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <span>{exportError}</span>
                    </div>
                  )}

                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-semibold text-zinc-300">
                      Hujjat formati:
                    </label>
                    <div className="grid grid-cols-2 gap-3 max-w-xs">
                      <button
                        type="button"
                        onClick={() => setExportFormat("PDF")}
                        className={`py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 border transition-all ${
                          exportFormat === "PDF"
                            ? "bg-primary text-white border-primary shadow-sm shadow-primary/20"
                            : "bg-surface-lowest text-zinc-400 border-white/[0.08] hover:text-white"
                        }`}
                      >
                        <FileCheck className="w-3.5 h-3.5" />
                        <span>PDF Format</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setExportFormat("JSON")}
                        className={`py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 border transition-all ${
                          exportFormat === "JSON"
                            ? "bg-primary text-white border-primary shadow-sm shadow-primary/20"
                            : "bg-surface-lowest text-zinc-400 border-white/[0.08] hover:text-white"
                        }`}
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        <span>JSON Ma&apos;lumot</span>
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <input
                      id="include-details"
                      type="checkbox"
                      checked={includeDetails}
                      onChange={(e) => setIncludeDetails(e.target.checked)}
                      className="w-4 h-4 rounded border-white/[0.1] bg-surface text-primary focus:ring-primary"
                    />
                    <label htmlFor="include-details" className="text-xs text-zinc-300 cursor-pointer">
                      Barcha talabalar amaliyot va kundalik detallarini hisobotga qo&apos;shish
                    </label>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-container border border-white/[0.06] text-[11px] text-zinc-400 leading-relaxed">
                    * Rasmiy ogohlantirish: Axborot amaliyot hisoboti; davlat diplomi, rasmiy baho yoki malaka attestatsiyasi hisoblanmaydi.
                  </div>

                  <button
                    type="submit"
                    disabled={isGeneratingExport}
                    className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-primary/25"
                  >
                    {isGeneratingExport ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Hisobot shakllantirilmoqda...</span>
                      </>
                    ) : (
                      <>
                        <Download className="w-3.5 h-3.5" />
                        <span>Rasmiy Hisobotni Shakllantirish ({exportFormat})</span>
                      </>
                    )}
                  </button>
                </form>
              </div>

              {/* Export Receipt Preview (when available) */}
              {exportReceipt && (
                <div className="p-5 rounded-xl bg-surface-card border border-emerald-500/20 flex flex-col gap-4 shadow-sm animate-in fade-in duration-200">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      <div>
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                          Hisobot Tayyor (Kvitansiya #{exportReceipt.export_id.slice(0, 8)})
                        </h4>
                        <span className="text-[11px] text-zinc-400">
                          Yaratilgan: {new Date(exportReceipt.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>

                    <a
                      href={exportReceipt.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition-all flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Yuklab Olish ({exportReceipt.export_format})</span>
                    </a>
                  </div>

                  {/* Summary KPI Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-surface p-4 rounded-xl border border-white/[0.06]">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Biriktirilgan Talabalar</span>
                      <span className="text-xl font-bold font-mono text-white tabular-nums">
                        {exportReceipt.summary.total_students_enrolled}
                      </span>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Superviziyalar</span>
                      <span className="text-xl font-bold font-mono text-emerald-400 tabular-nums">
                        {exportReceipt.summary.total_supervisions}
                      </span>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Jami Amaliyotlar</span>
                      <span className="text-xl font-bold font-mono text-blue-400 tabular-nums">
                        {exportReceipt.summary.total_placements}
                      </span>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Jami Ish Soatlari</span>
                      <span className="text-xl font-bold font-mono text-amber-300 tabular-nums">
                        {exportReceipt.summary.total_logged_hours} soat
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right 1 Column: Supervisions & Academic Agreements */}
            <div className="flex flex-col gap-5">
              {/* Student Supervisions Card (API-098) */}
              <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-3 shadow-sm">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <GraduationCap className="w-4 h-4 text-purple-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Superviziyalar ({supervisions.length})
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500">API-098</span>
                </div>

                {supervisionsError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                    {supervisionsError}
                  </div>
                )}

                {isLoadingSupervisions ? (
                  <div className="py-6 flex items-center justify-center text-zinc-400 gap-2 text-xs">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span>Yuklanmoqda...</span>
                  </div>
                ) : supervisions.length === 0 ? (
                  <div className="p-4 rounded-lg bg-surface text-center text-zinc-400 text-xs">
                    Superviziyalar mavjud emas.
                  </div>
                ) : (
                  <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                    {supervisions.map((sup) => (
                      <div
                        key={sup.id}
                        className="p-3 rounded-lg bg-surface border border-white/[0.04] flex flex-col gap-1 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">{sup.purpose}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
                            {sup.status || "ACTIVE"}
                          </span>
                        </div>
                        <span className="text-[11px] font-mono text-zinc-500">
                          Enrollment: #{sup.enrollment_id.slice(0, 8)}...
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Academic Agreements Card (API-101) */}
              <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-3 shadow-sm">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Hamkorlik Shartnomalari ({academicAgreements.length})
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500">API-101</span>
                </div>

                {agreementsError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                    {agreementsError}
                  </div>
                )}

                {isLoadingAgreements ? (
                  <div className="py-6 flex items-center justify-center text-zinc-400 gap-2 text-xs">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span>Yuklanmoqda...</span>
                  </div>
                ) : academicAgreements.length === 0 ? (
                  <div className="p-4 rounded-lg bg-surface text-center text-zinc-400 text-xs">
                    Faol shartnomalar topilmadi.
                  </div>
                ) : (
                  <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                    {academicAgreements.map((agr) => (
                      <div
                        key={agr.id}
                        className="p-3 rounded-lg bg-surface border border-white/[0.04] flex flex-col gap-1 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">Tashkilot #{agr.organization_id.slice(0, 8)}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            {agr.status}
                          </span>
                        </div>
                        <span className="text-[11px] font-mono text-zinc-500">
                          Shartnoma ID: #{agr.id.slice(0, 8)}...
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: TEACHER ASSIGNED PLACEMENTS & CONCLUSIONS */}
      {currentUser && activeTab === "assignments" && (
        <div className="flex flex-col gap-6">
          {assignmentsError && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{assignmentsError}</span>
            </div>
          )}

          {isLoadingAssignments ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-3 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span className="text-xs">Biriktirilgan amaliyotlar yuklanmoqda...</span>
            </div>
          ) : assignments.length === 0 ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-2 text-center">
              <BookOpen className="w-8 h-8 text-zinc-500 mb-1" />
              <h3 className="text-sm font-semibold text-white">Biriktirilgan amaliyotlar mavjud emas</h3>
              <p className="text-xs text-zinc-400 max-w-md">
                Hozirda sizga biriktirilgan talaba amaliyotlari topilmadi. Kafedra koordinatori tomonidan talaba biriktirilishi kutilmoqda.
              </p>
            </div>
          ) : (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl overflow-hidden shadow-sm">
              <div className="px-5 py-3.5 border-b border-white/[0.08] flex items-center justify-between">
                <span className="text-xs font-semibold text-white">
                  Biriktirilgan amaliyotlar ({assignments.length} ta)
                </span>
                <button
                  type="button"
                  onClick={loadAssignments}
                  className="text-xs text-primary hover:underline flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Yangilash</span>
                </button>
              </div>

              <div className="divide-y divide-white/[0.06]">
                {assignments.map((assignment) => (
                  <div
                    key={assignment.id}
                    className="p-4 hover:bg-white/[0.02] transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div className="flex flex-col gap-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium text-white">
                          Amaliyot ID: {assignment.placement_id.slice(0, 8)}...
                        </span>
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {assignment.accepted_at ? "Qabul qilingan" : "Biriktirilgan"}
                        </span>
                        <span className="text-xs text-zinc-400 font-mono">
                          Biriktirilgan sana: {new Date(assignment.assigned_at).toLocaleDateString("uz-UZ")}
                        </span>
                      </div>
                      <div className="text-xs text-zinc-400 flex flex-wrap items-center gap-3">
                        <span>Biriktiruv ID: {assignment.id.slice(0, 8)}...</span>
                        <span>•</span>
                        <span>Muassasa ID: {assignment.institution_id.slice(0, 8)}...</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <button
                        type="button"
                        onClick={() => handleOpenConclusionModal(assignment.placement_id, assignment.id)}
                        className="px-3.5 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-sm shadow-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
                      >
                        <Award className="w-3.5 h-3.5" />
                        <span>Akademik Xulosa (API-108)</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: REPORTS & ACADEMIC AGREEMENTS (API-100, API-098, API-101) */}
      {currentUser && activeTab === "exports" && (
        <div className="flex flex-col gap-6">
          {/* Header Card */}
          <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Hisobot & Shartnomalar Hub
                </span>
                <span className="text-zinc-500 text-xs font-mono">• API-100, API-098, API-101</span>
              </div>
              <h2 className="font-heading text-base md:text-lg font-bold text-white">
                Muassasa Yig&apos;ma Hisoboti va Hamkorlik Shartnomalari
              </h2>
              <p className="text-xs text-zinc-400">
                Talabalar amaliyoti, o&apos;quv rejalari va soatlar sarfi bo&apos;yicha rasmiy PDF va JSON hisobotlarini shakllantirish (CAP-026 / API-100) hamda faol hamkorlik shartnomalari nazorati.
              </p>
            </div>

            {institutionId && (
              <button
                type="button"
                disabled={isLoadingSupervisions || isLoadingAgreements}
                onClick={() => loadReportsAndAgreements(institutionId)}
                className="px-3.5 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300 hover:text-white transition-all flex items-center gap-1.5 self-start md:self-center disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingSupervisions || isLoadingAgreements ? "animate-spin" : ""}`} />
                <span>Yangilash</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Columns: Report Generator & Generated Receipt */}
            <div className="lg:col-span-2 flex flex-col gap-5">
              {/* Generator Form */}
              <div className="p-5 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-4 shadow-sm">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="w-4 h-4 text-primary" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Rasmiy Yig&apos;ma Hisobot Yaratish (API-100)
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500">CAP-026 / REPORT_EXPORT</span>
                </div>

                <form onSubmit={handleGenerateExport} className="flex flex-col gap-4">
                  {exportError && (
                    <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <span>{exportError}</span>
                    </div>
                  )}

                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-semibold text-zinc-300">
                      Hujjat formati:
                    </label>
                    <div className="grid grid-cols-2 gap-3 max-w-xs">
                      <button
                        type="button"
                        onClick={() => setExportFormat("PDF")}
                        className={`py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 border transition-all ${
                          exportFormat === "PDF"
                            ? "bg-primary text-white border-primary shadow-sm shadow-primary/20"
                            : "bg-surface-lowest text-zinc-400 border-white/[0.08] hover:text-white"
                        }`}
                      >
                        <FileCheck className="w-3.5 h-3.5" />
                        <span>PDF Format</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setExportFormat("JSON")}
                        className={`py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 border transition-all ${
                          exportFormat === "JSON"
                            ? "bg-primary text-white border-primary shadow-sm shadow-primary/20"
                            : "bg-surface-lowest text-zinc-400 border-white/[0.08] hover:text-white"
                        }`}
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        <span>JSON Ma&apos;lumot</span>
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <input
                      id="include-details"
                      type="checkbox"
                      checked={includeDetails}
                      onChange={(e) => setIncludeDetails(e.target.checked)}
                      className="w-4 h-4 rounded border-white/[0.1] bg-surface text-primary focus:ring-primary"
                    />
                    <label htmlFor="include-details" className="text-xs text-zinc-300 cursor-pointer">
                      Barcha talabalar amaliyot va kundalik detallarini hisobotga qo&apos;shish
                    </label>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-container border border-white/[0.06] text-[11px] text-zinc-400 leading-relaxed">
                    * Rasmiy ogohlantirish: Axborot amaliyot hisoboti; davlat diplomi, rasmiy baho yoki malaka attestatsiyasi hisoblanmaydi.
                  </div>

                  <button
                    type="submit"
                    disabled={isGeneratingExport}
                    className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-primary/25"
                  >
                    {isGeneratingExport ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Hisobot shakllantirilmoqda...</span>
                      </>
                    ) : (
                      <>
                        <Download className="w-3.5 h-3.5" />
                        <span>Rasmiy Hisobotni Shakllantirish ({exportFormat})</span>
                      </>
                    )}
                  </button>
                </form>
              </div>

              {/* Export Receipt Preview (when available) */}
              {exportReceipt && (
                <div className="p-5 rounded-xl bg-surface-card border border-emerald-500/20 flex flex-col gap-4 shadow-sm animate-in fade-in duration-200">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      <div>
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                          Hisobot Tayyor (Kvitansiya #{exportReceipt.export_id.slice(0, 8)})
                        </h4>
                        <span className="text-[11px] text-zinc-400">
                          Yaratilgan: {new Date(exportReceipt.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>

                    <a
                      href={exportReceipt.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition-all flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Yuklab Olish ({exportReceipt.export_format})</span>
                    </a>
                  </div>

                  {/* Summary KPI Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-surface p-4 rounded-xl border border-white/[0.06]">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Biriktirilgan Talabalar</span>
                      <span className="text-xl font-bold font-mono text-white tabular-nums">
                        {exportReceipt.summary.total_students_enrolled}
                      </span>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Superviziyalar</span>
                      <span className="text-xl font-bold font-mono text-emerald-400 tabular-nums">
                        {exportReceipt.summary.total_supervisions}
                      </span>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Jami Amaliyotlar</span>
                      <span className="text-xl font-bold font-mono text-blue-400 tabular-nums">
                        {exportReceipt.summary.total_placements}
                      </span>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Jami Ish Soatlari</span>
                      <span className="text-xl font-bold font-mono text-amber-300 tabular-nums">
                        {exportReceipt.summary.total_logged_hours} soat
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right 1 Column: Supervisions & Academic Agreements */}
            <div className="flex flex-col gap-5">
              {/* Student Supervisions Card (API-098) */}
              <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-3 shadow-sm">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <GraduationCap className="w-4 h-4 text-purple-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Superviziyalar ({supervisions.length})
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500">API-098</span>
                </div>

                {supervisionsError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                    {supervisionsError}
                  </div>
                )}

                {isLoadingSupervisions ? (
                  <div className="py-6 flex items-center justify-center text-zinc-400 gap-2 text-xs">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span>Yuklanmoqda...</span>
                  </div>
                ) : supervisions.length === 0 ? (
                  <div className="p-4 rounded-lg bg-surface text-center text-zinc-400 text-xs">
                    Superviziyalar mavjud emas.
                  </div>
                ) : (
                  <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                    {supervisions.map((sup) => (
                      <div
                        key={sup.id}
                        className="p-3 rounded-lg bg-surface border border-white/[0.04] flex flex-col gap-1 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">{sup.purpose}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
                            {sup.status || "ACTIVE"}
                          </span>
                        </div>
                        <span className="text-[11px] font-mono text-zinc-500">
                          Enrollment: #{sup.enrollment_id.slice(0, 8)}...
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Academic Agreements Card (API-101) */}
              <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-3 shadow-sm">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Hamkorlik Shartnomalari ({academicAgreements.length})
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500">API-101</span>
                </div>

                {agreementsError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                    {agreementsError}
                  </div>
                )}

                {isLoadingAgreements ? (
                  <div className="py-6 flex items-center justify-center text-zinc-400 gap-2 text-xs">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span>Yuklanmoqda...</span>
                  </div>
                ) : academicAgreements.length === 0 ? (
                  <div className="p-4 rounded-lg bg-surface text-center text-zinc-400 text-xs">
                    Faol shartnomalar topilmadi.
                  </div>
                ) : (
                  <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                    {academicAgreements.map((agr) => (
                      <div
                        key={agr.id}
                        className="p-3 rounded-lg bg-surface border border-white/[0.04] flex flex-col gap-1 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">Tashkilot #{agr.organization_id.slice(0, 8)}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            {agr.status}
                          </span>
                        </div>
                        <span className="text-[11px] font-mono text-zinc-500">
                          Shartnoma ID: #{agr.id.slice(0, 8)}...
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: COORDINATOR ASSIGNMENT QUEUE & TEACHER NOMINATION */}
      {currentUser && activeTab === "coordinator" && (
        <div className="flex flex-col gap-6">
          {coordError && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{coordError}</span>
            </div>
          )}

          {isLoadingCoord ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-3 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span className="text-xs">Kafedra taqsimot navbati yuklanmoqda...</span>
            </div>
          ) : coordinatorQueue.length === 0 ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-2 text-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mb-1" />
              <h3 className="text-sm font-semibold text-white">Taqsimot navbati bo‘sh</h3>
              <p className="text-xs text-zinc-400 max-w-md">
                Barcha talabalar amaliyotlariga o‘qituvchi tayinlangan yoki hozirda yangi kutilayotgan so‘rovlar yo‘q.
              </p>
            </div>
          ) : (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl overflow-hidden shadow-sm">
              <div className="px-5 py-3.5 border-b border-white/[0.08] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-white">
                    Biriktirish kutilayotgan talabalar ({coordinatorQueue.length} ta)
                  </span>
                  {institutionId && (
                    <span className="text-[11px] font-mono text-zinc-500">
                      (Muassasa: {institutionId.slice(0, 8)}...)
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={loadCoordinatorQueue}
                  className="text-xs text-primary hover:underline flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Yangilash</span>
                </button>
              </div>

              <div className="divide-y divide-white/[0.06]">
                {coordinatorQueue.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 hover:bg-white/[0.02] transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">
                          {item.student_name || "Talaba"}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                          Taqsimot kutilmoqda
                        </span>
                      </div>
                      <div className="text-xs text-zinc-400 flex flex-wrap items-center gap-2">
                        <span>Amaliyot ID: {item.placement_id.slice(0, 8)}...</span>
                        <span>•</span>
                        <span>Enrollment ID: {item.enrollment_id.slice(0, 8)}...</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <button
                        type="button"
                        onClick={() => handleOpenNominateModal(item)}
                        className="px-3.5 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-sm shadow-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
                      >
                        <UserCheck className="w-3.5 h-3.5" />
                        <span>O‘qituvchi tayinlash</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: REPORTS & ACADEMIC AGREEMENTS (API-100, API-098, API-101) */}
      {currentUser && activeTab === "exports" && (
        <div className="flex flex-col gap-6">
          {/* Header Card */}
          <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Hisobot & Shartnomalar Hub
                </span>
                <span className="text-zinc-500 text-xs font-mono">• API-100, API-098, API-101</span>
              </div>
              <h2 className="font-heading text-base md:text-lg font-bold text-white">
                Muassasa Yig&apos;ma Hisoboti va Hamkorlik Shartnomalari
              </h2>
              <p className="text-xs text-zinc-400">
                Talabalar amaliyoti, o&apos;quv rejalari va soatlar sarfi bo&apos;yicha rasmiy PDF va JSON hisobotlarini shakllantirish (CAP-026 / API-100) hamda faol hamkorlik shartnomalari nazorati.
              </p>
            </div>

            {institutionId && (
              <button
                type="button"
                disabled={isLoadingSupervisions || isLoadingAgreements}
                onClick={() => loadReportsAndAgreements(institutionId)}
                className="px-3.5 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300 hover:text-white transition-all flex items-center gap-1.5 self-start md:self-center disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingSupervisions || isLoadingAgreements ? "animate-spin" : ""}`} />
                <span>Yangilash</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Columns: Report Generator & Generated Receipt */}
            <div className="lg:col-span-2 flex flex-col gap-5">
              {/* Generator Form */}
              <div className="p-5 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-4 shadow-sm">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="w-4 h-4 text-primary" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Rasmiy Yig&apos;ma Hisobot Yaratish (API-100)
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500">CAP-026 / REPORT_EXPORT</span>
                </div>

                <form onSubmit={handleGenerateExport} className="flex flex-col gap-4">
                  {exportError && (
                    <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <span>{exportError}</span>
                    </div>
                  )}

                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-semibold text-zinc-300">
                      Hujjat formati:
                    </label>
                    <div className="grid grid-cols-2 gap-3 max-w-xs">
                      <button
                        type="button"
                        onClick={() => setExportFormat("PDF")}
                        className={`py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 border transition-all ${
                          exportFormat === "PDF"
                            ? "bg-primary text-white border-primary shadow-sm shadow-primary/20"
                            : "bg-surface-lowest text-zinc-400 border-white/[0.08] hover:text-white"
                        }`}
                      >
                        <FileCheck className="w-3.5 h-3.5" />
                        <span>PDF Format</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setExportFormat("JSON")}
                        className={`py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 border transition-all ${
                          exportFormat === "JSON"
                            ? "bg-primary text-white border-primary shadow-sm shadow-primary/20"
                            : "bg-surface-lowest text-zinc-400 border-white/[0.08] hover:text-white"
                        }`}
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        <span>JSON Ma&apos;lumot</span>
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <input
                      id="include-details"
                      type="checkbox"
                      checked={includeDetails}
                      onChange={(e) => setIncludeDetails(e.target.checked)}
                      className="w-4 h-4 rounded border-white/[0.1] bg-surface text-primary focus:ring-primary"
                    />
                    <label htmlFor="include-details" className="text-xs text-zinc-300 cursor-pointer">
                      Barcha talabalar amaliyot va kundalik detallarini hisobotga qo&apos;shish
                    </label>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-container border border-white/[0.06] text-[11px] text-zinc-400 leading-relaxed">
                    * Rasmiy ogohlantirish: Axborot amaliyot hisoboti; davlat diplomi, rasmiy baho yoki malaka attestatsiyasi hisoblanmaydi.
                  </div>

                  <button
                    type="submit"
                    disabled={isGeneratingExport}
                    className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-primary/25"
                  >
                    {isGeneratingExport ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Hisobot shakllantirilmoqda...</span>
                      </>
                    ) : (
                      <>
                        <Download className="w-3.5 h-3.5" />
                        <span>Rasmiy Hisobotni Shakllantirish ({exportFormat})</span>
                      </>
                    )}
                  </button>
                </form>
              </div>

              {/* Export Receipt Preview (when available) */}
              {exportReceipt && (
                <div className="p-5 rounded-xl bg-surface-card border border-emerald-500/20 flex flex-col gap-4 shadow-sm animate-in fade-in duration-200">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      <div>
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                          Hisobot Tayyor (Kvitansiya #{exportReceipt.export_id.slice(0, 8)})
                        </h4>
                        <span className="text-[11px] text-zinc-400">
                          Yaratilgan: {new Date(exportReceipt.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>

                    <a
                      href={exportReceipt.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition-all flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Yuklab Olish ({exportReceipt.export_format})</span>
                    </a>
                  </div>

                  {/* Summary KPI Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-surface p-4 rounded-xl border border-white/[0.06]">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Biriktirilgan Talabalar</span>
                      <span className="text-xl font-bold font-mono text-white tabular-nums">
                        {exportReceipt.summary.total_students_enrolled}
                      </span>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Superviziyalar</span>
                      <span className="text-xl font-bold font-mono text-emerald-400 tabular-nums">
                        {exportReceipt.summary.total_supervisions}
                      </span>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Jami Amaliyotlar</span>
                      <span className="text-xl font-bold font-mono text-blue-400 tabular-nums">
                        {exportReceipt.summary.total_placements}
                      </span>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500">Jami Ish Soatlari</span>
                      <span className="text-xl font-bold font-mono text-amber-300 tabular-nums">
                        {exportReceipt.summary.total_logged_hours} soat
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right 1 Column: Supervisions & Academic Agreements */}
            <div className="flex flex-col gap-5">
              {/* Student Supervisions Card (API-098) */}
              <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-3 shadow-sm">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <GraduationCap className="w-4 h-4 text-purple-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Superviziyalar ({supervisions.length})
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500">API-098</span>
                </div>

                {supervisionsError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                    {supervisionsError}
                  </div>
                )}

                {isLoadingSupervisions ? (
                  <div className="py-6 flex items-center justify-center text-zinc-400 gap-2 text-xs">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span>Yuklanmoqda...</span>
                  </div>
                ) : supervisions.length === 0 ? (
                  <div className="p-4 rounded-lg bg-surface text-center text-zinc-400 text-xs">
                    Superviziyalar mavjud emas.
                  </div>
                ) : (
                  <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                    {supervisions.map((sup) => (
                      <div
                        key={sup.id}
                        className="p-3 rounded-lg bg-surface border border-white/[0.04] flex flex-col gap-1 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">{sup.purpose}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
                            {sup.status || "ACTIVE"}
                          </span>
                        </div>
                        <span className="text-[11px] font-mono text-zinc-500">
                          Enrollment: #{sup.enrollment_id.slice(0, 8)}...
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Academic Agreements Card (API-101) */}
              <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-3 shadow-sm">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Hamkorlik Shartnomalari ({academicAgreements.length})
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500">API-101</span>
                </div>

                {agreementsError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                    {agreementsError}
                  </div>
                )}

                {isLoadingAgreements ? (
                  <div className="py-6 flex items-center justify-center text-zinc-400 gap-2 text-xs">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span>Yuklanmoqda...</span>
                  </div>
                ) : academicAgreements.length === 0 ? (
                  <div className="p-4 rounded-lg bg-surface text-center text-zinc-400 text-xs">
                    Faol shartnomalar topilmadi.
                  </div>
                ) : (
                  <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                    {academicAgreements.map((agr) => (
                      <div
                        key={agr.id}
                        className="p-3 rounded-lg bg-surface border border-white/[0.04] flex flex-col gap-1 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">Tashkilot #{agr.organization_id.slice(0, 8)}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            {agr.status}
                          </span>
                        </div>
                        <span className="text-[11px] font-mono text-zinc-500">
                          Shartnoma ID: #{agr.id.slice(0, 8)}...
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: UNIVERSITY ANALYTICS & MONITORING (API-125) */}
      {currentUser && activeTab === "analytics" && (
        <div className="flex flex-col gap-6">
          {/* FILTER BAR & CONTROLS */}
          <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-4 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5 text-zinc-400">
                <Filter className="w-3.5 h-3.5 text-primary" />
                <span className="font-semibold text-zinc-300">Filtrlash:</span>
              </div>

              {/* Program Filter */}
              <input
                type="text"
                placeholder="Dastur / Fakultet (masalan: Kompyuter)"
                value={analyticsFilters.program}
                onChange={(e) =>
                  setAnalyticsFilters((prev) => ({ ...prev, program: e.target.value }))
                }
                className="px-3 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-white placeholder-zinc-500 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary w-48"
              />

              {/* Status Filter */}
              <select
                value={analyticsFilters.status}
                onChange={(e) =>
                  setAnalyticsFilters((prev) => ({ ...prev, status: e.target.value }))
                }
                className="px-3 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-white text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
              >
                <option value="">Barcha holatlar</option>
                <option value="ACTIVE">Faol (ACTIVE)</option>
                <option value="COMPLETED">Yakunlangan (COMPLETED)</option>
                <option value="CANCELLED">Bekor qilingan (CANCELLED)</option>
              </select>

              {/* Date Range */}
              <div className="flex items-center gap-1.5 text-zinc-400">
                <span className="text-[11px]">Sanadan:</span>
                <input
                  type="date"
                  value={analyticsFilters.fromDate}
                  onChange={(e) =>
                    setAnalyticsFilters((prev) => ({ ...prev, fromDate: e.target.value }))
                  }
                  className="px-2 py-1 rounded bg-surface border border-white/[0.08] text-white text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                />
                <span className="text-[11px]">gacha:</span>
                <input
                  type="date"
                  value={analyticsFilters.toDate}
                  onChange={(e) =>
                    setAnalyticsFilters((prev) => ({ ...prev, toDate: e.target.value }))
                  }
                  className="px-2 py-1 rounded bg-surface border border-white/[0.08] text-white text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={() => {
                  setAnalyticsFilters({ program: "", status: "", fromDate: "", toDate: "" });
                  if (institutionId) {
                    loadAnalytics(institutionId, { program: "", status: "", fromDate: "", toDate: "" });
                  }
                }}
                className="px-3 py-1.5 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-zinc-300 text-xs font-medium transition-all"
              >
                Tozalash
              </button>
              <button
                type="button"
                onClick={() => {
                  if (institutionId) loadAnalytics(institutionId);
                }}
                disabled={isLoadingAnalytics}
                className="px-3.5 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-primary/20 transition-all active:scale-[0.98] disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingAnalytics ? "animate-spin" : ""}`} />
                <span>Yangilash</span>
              </button>
            </div>
          </div>

          {analyticsError && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{analyticsError}</span>
            </div>
          )}

          {isLoadingAnalytics ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-3 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span className="text-xs">Universitet analitika ma&apos;lumotlari hisoblanmoqda...</span>
            </div>
          ) : !analyticsData ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-2 text-center">
              <BarChart3 className="w-8 h-8 text-zinc-500 mb-1" />
              <p className="text-sm font-semibold text-white">Analitika yuklanmadi</p>
              <p className="text-xs text-zinc-400 max-w-sm">
                Universitet ID si topilmadi yoki analitika ma&apos;lumotlari mavjud emas. Yuqoridagi &quot;Yangilash&quot; tugmasini bosing.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              {/* 4 EXECUTIVE SUMMARY KPI CARDS */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* KPI 1 */}
                <div className="bg-surface-card border border-white/[0.08] rounded-xl p-4 flex flex-col justify-between gap-3">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs font-medium">Talabalar & Amaliyotlar</span>
                    <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                      <Users className="w-4 h-4" />
                    </div>
                  </div>
                  <div>
                    <span className="text-2xl font-bold font-mono text-white">
                      {analyticsData.summary.total_students}
                    </span>
                    <p className="text-[11px] text-zinc-400 mt-0.5">
                      Faol: <span className="font-mono text-emerald-400">{analyticsData.summary.active_interns}</span> • Yakunlangan: <span className="font-mono text-zinc-300">{analyticsData.summary.completed_interns}</span>
                    </p>
                  </div>
                </div>

                {/* KPI 2 */}
                <div className="bg-surface-card border border-white/[0.08] rounded-xl p-4 flex flex-col justify-between gap-3">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs font-medium">Umumiy Davomat</span>
                    <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                      <Activity className="w-4 h-4" />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl font-bold font-mono text-white">
                        {analyticsData.summary.overall_attendance_rate}%
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                          analyticsData.summary.overall_attendance_rate >= 85
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : analyticsData.summary.overall_attendance_rate >= 70
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                        }`}
                      >
                        {analyticsData.summary.overall_attendance_rate >= 85
                          ? "Yaxshi"
                          : analyticsData.summary.overall_attendance_rate >= 70
                          ? "Ogohlantirish"
                          : "Xavfli"}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-400 mt-0.5">
                      Kutilgan ish kunlari hisobiga ko&apos;ra
                    </p>
                  </div>
                </div>

                {/* KPI 3 */}
                <div className="bg-surface-card border border-white/[0.08] rounded-xl p-4 flex flex-col justify-between gap-3">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs font-medium">Jami Ishlangan Soatlar</span>
                    <div className="w-8 h-8 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
                      <Clock className="w-4 h-4" />
                    </div>
                  </div>
                  <div>
                    <span className="text-2xl font-bold font-mono text-white">
                      {analyticsData.summary.total_logged_hours}{" "}
                      <span className="text-xs font-normal text-zinc-400">soat</span>
                    </span>
                    <p className="text-[11px] text-zinc-400 mt-0.5">
                      Joriy hafta: <span className="font-mono text-white">{analyticsData.weekly_hours_monitoring.current_week_hours} s</span> (O&apos;rt: <span className="font-mono text-zinc-300">{analyticsData.summary.avg_weekly_hours_per_student} s/talaba</span>)
                    </p>
                  </div>
                </div>

                {/* KPI 4 */}
                <div className="bg-surface-card border border-white/[0.08] rounded-xl p-4 flex flex-col justify-between gap-3">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs font-medium">Muvaffaqiyatli Yakunlash</span>
                    <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                      <Award className="w-4 h-4" />
                    </div>
                  </div>
                  <div>
                    <span className="text-2xl font-bold font-mono text-white">
                      {analyticsData.summary.completion_rate}%
                    </span>
                    <p className="text-[11px] text-zinc-400 mt-0.5">
                      Xulosalar: <span className="font-mono text-emerald-400">{analyticsData.summary.academic_conclusions_count}</span> • Ko&apos;rib chiqilmoqda: <span className="font-mono text-zinc-300">{analyticsData.summary.pending_teacher_reviews}</span>
                    </p>
                  </div>
                </div>
              </div>

              {/* PILLAR 1: TALABALAR DAVOMATI MONITORINGI */}
              <div className="bg-surface-card border border-white/[0.08] rounded-xl p-6 flex flex-col gap-5">
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
                  <div>
                    <h3 className="text-sm font-heading font-semibold text-white flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span>Talabalar Davomati Monitoringi</span>
                    </h3>
                    <p className="text-xs text-zinc-400 mt-0.5">
                      Dushanba–Shanba kunlari doirasidagi kutilgan va amaldagi kundaliklar hisobi
                    </p>
                  </div>

                  {/* Day Type Breakdown Pills */}
                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                    <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20">
                      Ish joyida: <strong className="font-mono">{analyticsData.attendance_metrics.by_day_type.work}</strong>
                    </span>
                    <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                      Masofaviy: <strong className="font-mono">{analyticsData.attendance_metrics.by_day_type.remote_work}</strong>
                    </span>
                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                      Kasallik: <strong className="font-mono">{analyticsData.attendance_metrics.by_day_type.sick_leave}</strong>
                    </span>
                    <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20">
                      Sababsiz: <strong className="font-mono">{analyticsData.attendance_metrics.by_day_type.absence}</strong>
                    </span>
                    <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                      Dam olish: <strong className="font-mono">{analyticsData.attendance_metrics.by_day_type.holiday}</strong>
                    </span>
                    {analyticsData.attendance_metrics.late_submissions_count > 0 && (
                      <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1 font-semibold">
                        <AlertTriangle className="w-3 h-3 text-amber-400" />
                        <span>Kech topshirilgan: {analyticsData.attendance_metrics.late_submissions_count} ta</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Risk Distribution Summary */}
                <div className="flex items-center gap-4 text-xs text-zinc-400 bg-surface/40 p-3 rounded-lg border border-white/[0.04]">
                  <span className="font-semibold text-zinc-300">Xavf toifalari taqsimoti:</span>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                    <span>Yaxshi (&ge;85%):</span>
                    <strong className="font-mono text-white">
                      {analyticsData.attendance_metrics.by_status_distribution.good}
                    </strong>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                    <span>Ogohlantirish (70–84%):</span>
                    <strong className="font-mono text-white">
                      {analyticsData.attendance_metrics.by_status_distribution.warning}
                    </strong>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-400" />
                    <span>Xavfli (&lt;70%):</span>
                    <strong className="font-mono text-white">
                      {analyticsData.attendance_metrics.by_status_distribution.critical}
                    </strong>
                  </div>
                </div>

                {/* Student Attendance Table with Search */}
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="relative flex-1 max-w-xs">
                      <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                      <input
                        type="text"
                        placeholder="Talaba yoki dastur bo'yicha qidirish..."
                        value={studentSearchTerm}
                        onChange={(e) => setStudentSearchTerm(e.target.value)}
                        className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-white placeholder-zinc-500 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                      />
                    </div>
                    <span className="text-xs text-zinc-500">
                      Jami: {analyticsData.attendance_metrics.students.length} ta talaba
                    </span>
                  </div>

                  <div className="overflow-x-auto border border-white/[0.08] rounded-lg">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-surface/80 text-zinc-400 border-b border-white/[0.06] text-[11px] uppercase tracking-wider">
                        <tr>
                          <th className="py-2.5 px-3 font-semibold">Talaba</th>
                          <th className="py-2.5 px-3 font-semibold">Dastur / Fakultet</th>
                          <th className="py-2.5 px-3 font-semibold">Tashkilot</th>
                          <th className="py-2.5 px-3 font-semibold text-center">Kutilgan</th>
                          <th className="py-2.5 px-3 font-semibold text-center">Qatnashgan</th>
                          <th className="py-2.5 px-3 font-semibold text-center">Qoldirilgan</th>
                          <th className="py-2.5 px-3 font-semibold">Davomat %</th>
                          <th className="py-2.5 px-3 font-semibold text-center">Holat</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04] text-zinc-300">
                        {analyticsData.attendance_metrics.students
                          .filter(
                            (s) =>
                              !studentSearchTerm ||
                              s.student_name.toLowerCase().includes(studentSearchTerm.toLowerCase()) ||
                              s.program.toLowerCase().includes(studentSearchTerm.toLowerCase()) ||
                              s.organization_name.toLowerCase().includes(studentSearchTerm.toLowerCase())
                          )
                          .map((student) => (
                            <tr key={student.placement_id} className="hover:bg-white/[0.02] transition-colors">
                              <td className="py-2.5 px-3">
                                <div className="font-semibold text-white">{student.student_name}</div>
                                <div className="text-[10px] font-mono text-zinc-500">
                                  ID: {student.student_id.slice(0, 8)}...
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-zinc-400">{student.program}</td>
                              <td className="py-2.5 px-3 text-zinc-300">{student.organization_name}</td>
                              <td className="py-2.5 px-3 font-mono text-center text-zinc-400">
                                {student.expected_days}
                              </td>
                              <td className="py-2.5 px-3 font-mono text-center text-emerald-400 font-semibold">
                                {student.attended_days}
                              </td>
                              <td className="py-2.5 px-3 font-mono text-center text-zinc-400">
                                {student.absent_days}{" "}
                                {student.sick_days > 0 && (
                                  <span className="text-amber-400 text-[10px]">(+kasal {student.sick_days})</span>
                                )}
                              </td>
                              <td className="py-2.5 px-3">
                                <div className="flex items-center gap-2">
                                  <div className="w-16 h-2 rounded-full bg-zinc-800 overflow-hidden">
                                    <div
                                      className={`h-full rounded-full ${
                                        student.attendance_rate >= 85
                                          ? "bg-emerald-400"
                                          : student.attendance_rate >= 70
                                          ? "bg-amber-400"
                                          : "bg-rose-400"
                                      }`}
                                      style={{ width: `${Math.min(100, Math.max(0, student.attendance_rate))}%` }}
                                    />
                                  </div>
                                  <span className="font-mono text-xs font-semibold">
                                    {student.attendance_rate}%
                                  </span>
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-center">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                    student.attendance_status === "GOOD"
                                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                      : student.attendance_status === "WARNING"
                                      ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                                      : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                                  }`}
                                >
                                  {student.attendance_status === "GOOD"
                                    ? "Yaxshi"
                                    : student.attendance_status === "WARNING"
                                    ? "Ogohlantirish"
                                    : "Xavfli"}
                                </span>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* PILLAR 2: HAFTALIK SOATLAR MONITORINGI */}
              <div className="bg-surface-card border border-white/[0.08] rounded-xl p-6 flex flex-col gap-5">
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
                  <div>
                    <h3 className="text-sm font-heading font-semibold text-white flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-primary" />
                      <span>Haftalik Soatlar Monitoringi & O&apos;zR MK 118 Muvofiqligi</span>
                    </h3>
                    <p className="text-xs text-zinc-400 mt-0.5">
                      Kalendar haftalari bo&apos;yicha kiritilgan soatlar dinamikasi va qonuniy me&apos;yorlar nazorati
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-zinc-400">
                      Joriy hafta: <strong className="font-mono text-white">{analyticsData.weekly_hours_monitoring.current_week_hours} s</strong>
                    </span>
                    <span className="text-zinc-400">
                      O&apos;rtacha: <strong className="font-mono text-white">{analyticsData.weekly_hours_monitoring.avg_weekly_hours} s/talaba</strong>
                    </span>
                  </div>
                </div>

                {/* Compliance Alert Banner */}
                {(analyticsData.weekly_hours_monitoring.compliance_alerts.overtime_students > 0 ||
                  analyticsData.weekly_hours_monitoring.compliance_alerts.zero_hours_this_week > 0) && (
                  <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                      <span>
                        <strong>O&apos;zbekiston Respublikasi Mehnat Kodeksi 118-moddasi ogohlantirishi:</strong>
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      {analyticsData.weekly_hours_monitoring.compliance_alerts.overtime_students > 0 && (
                        <span className="font-semibold text-rose-300">
                          {analyticsData.weekly_hours_monitoring.compliance_alerts.overtime_students} ta talaba kunlik/haftalik limitdan oshgan
                        </span>
                      )}
                      {analyticsData.weekly_hours_monitoring.compliance_alerts.zero_hours_this_week > 0 && (
                        <span className="font-semibold text-amber-400">
                          {analyticsData.weekly_hours_monitoring.compliance_alerts.zero_hours_this_week} ta faol talaba joriy haftada soat kiritmagan
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Visual Weekly Hours Bar Chart */}
                <div className="flex flex-col gap-2">
                  <span className="text-xs font-semibold text-zinc-300">Haftalik Ish Soatlari Trendi</span>
                  {analyticsData.weekly_hours_monitoring.weekly_trend.length === 0 ? (
                    <div className="p-6 rounded-lg bg-surface text-center text-zinc-500 text-xs">
                      Haftalik soatlar yozuvi mavjud emas.
                    </div>
                  ) : (
                    <div className="p-4 rounded-lg bg-surface border border-white/[0.04] flex items-end gap-3 h-44 overflow-x-auto pt-6">
                      {analyticsData.weekly_hours_monitoring.weekly_trend.map((item) => {
                        const maxH = Math.max(
                          ...analyticsData.weekly_hours_monitoring.weekly_trend.map((w) => w.logged_hours),
                          1
                        );
                        const barHeight = Math.max((item.logged_hours / maxH) * 100, 6);
                        return (
                          <div
                            key={item.week}
                            className="flex-1 min-w-[56px] flex flex-col items-center gap-1.5 h-full justify-end group"
                          >
                            <span className="text-[10px] font-mono text-zinc-400 opacity-80 group-hover:opacity-100 transition-opacity">
                              {item.logged_hours}s
                            </span>
                            <div className="w-full bg-zinc-800 rounded-t overflow-hidden flex items-end h-full">
                              <div
                                className="w-full bg-primary/80 hover:bg-primary transition-all rounded-t"
                                style={{ height: `${barHeight}%` }}
                              />
                            </div>
                            <span className="text-[10px] font-mono text-zinc-400 whitespace-nowrap">
                              {item.week.replace(/^.*-W/, "H")}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Breakdowns Grid: Program & Organization */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* By Program */}
                  <div className="bg-surface/60 border border-white/[0.04] rounded-lg p-4 flex flex-col gap-3">
                    <span className="text-xs font-semibold text-white">Dasturlar Kesimida Soatlar</span>
                    {analyticsData.weekly_hours_monitoring.by_program.length === 0 ? (
                      <span className="text-xs text-zinc-500">Ma&apos;lumot mavjud emas</span>
                    ) : (
                      <div className="space-y-2 text-xs">
                        {analyticsData.weekly_hours_monitoring.by_program.map((p) => (
                          <div
                            key={p.program}
                            className="flex items-center justify-between p-2 rounded bg-surface border border-white/[0.04]"
                          >
                            <div>
                              <div className="font-semibold text-white">{p.program}</div>
                              <div className="text-[10px] text-zinc-400">
                                {p.student_count} ta talaba • O&apos;rt: {p.avg_hours} s
                              </div>
                            </div>
                            <span className="font-mono font-bold text-white text-xs">{p.total_hours} s</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* By Organization */}
                  <div className="bg-surface/60 border border-white/[0.04] rounded-lg p-4 flex flex-col gap-3">
                    <span className="text-xs font-semibold text-white">Ish Beruvchilar Kesimida Soatlar</span>
                    {analyticsData.weekly_hours_monitoring.by_organization.length === 0 ? (
                      <span className="text-xs text-zinc-500">Ma&apos;lumot mavjud emas</span>
                    ) : (
                      <div className="space-y-2 text-xs">
                        {analyticsData.weekly_hours_monitoring.by_organization.map((o) => (
                          <div
                            key={o.organization_name}
                            className="flex items-center justify-between p-2 rounded bg-surface border border-white/[0.04]"
                          >
                            <div>
                              <div className="font-semibold text-white">{o.organization_name}</div>
                              <div className="text-[10px] text-zinc-400">{o.intern_count} ta amaliyotchi</div>
                            </div>
                            <span className="font-mono font-bold text-primary text-xs">{o.total_hours} s</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* PILLAR 3: AMALIYOT NATIJALARI TAHLILI */}
              <div className="bg-surface-card border border-white/[0.08] rounded-xl p-6 flex flex-col gap-5">
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
                  <div>
                    <h3 className="text-sm font-heading font-semibold text-white flex items-center gap-2">
                      <Award className="w-4 h-4 text-amber-400" />
                      <span>Amaliyot Natijalari & Baholash Tahlili</span>
                    </h3>
                    <p className="text-xs text-zinc-400 mt-0.5">
                      Yakuniy xulosalar, mentor baholari va dasturlar bo&apos;yicha natijalar
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                      Yakunlash: {analyticsData.internship_results.completion_rate}%
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Academic Conclusions */}
                  <div className="bg-surface/60 border border-white/[0.04] rounded-lg p-4 flex flex-col gap-3">
                    <span className="text-xs font-semibold text-white">Akademik Xulosalar (O&apos;qituvchilar)</span>
                    <div className="space-y-2 text-xs">
                      <div className="flex items-center justify-between p-2 rounded bg-surface">
                        <span className="text-zinc-300">To&apos;liq Ma&apos;qullangan:</span>
                        <strong className="font-mono text-emerald-400">
                          {analyticsData.internship_results.academic_conclusions.complete}
                        </strong>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded bg-surface">
                        <span className="text-zinc-300">Qayta Ko&apos;rish Talab:</span>
                        <strong className="font-mono text-amber-400">
                          {analyticsData.internship_results.academic_conclusions.revision_required}
                        </strong>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded bg-surface">
                        <span className="text-zinc-300">Xulosa Kutilmoqda:</span>
                        <strong className="font-mono text-zinc-400">
                          {analyticsData.internship_results.academic_conclusions.pending}
                        </strong>
                      </div>
                    </div>
                  </div>

                  {/* Workplace Evaluations */}
                  <div className="bg-surface/60 border border-white/[0.04] rounded-lg p-4 flex flex-col gap-3">
                    <span className="text-xs font-semibold text-white">Ish Beruvchi Baholari (Mentorlar)</span>
                    <div className="space-y-2 text-xs">
                      <div className="flex items-center justify-between p-2 rounded bg-surface">
                        <span className="text-zinc-300">Ma&apos;qullash Darajasi:</span>
                        <strong className="font-mono text-emerald-400">
                          {analyticsData.internship_results.workplace_evaluations.approved_rate}%
                        </strong>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded bg-surface">
                        <span className="text-zinc-300">Ma&apos;qullangan Kundaliklar:</span>
                        <strong className="font-mono text-white">
                          {analyticsData.internship_results.workplace_evaluations.approved_count}
                        </strong>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded bg-surface">
                        <span className="text-zinc-300">O&apos;zgartirish So&apos;ralgan:</span>
                        <strong className="font-mono text-amber-400">
                          {analyticsData.internship_results.workplace_evaluations.changes_requested_count}
                        </strong>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded bg-surface">
                        <span className="text-zinc-300">Rad Etilgan:</span>
                        <strong className="font-mono text-rose-400">
                          {analyticsData.internship_results.workplace_evaluations.rejected_count}
                        </strong>
                      </div>
                    </div>
                  </div>

                  {/* Program Performance */}
                  <div className="bg-surface/60 border border-white/[0.04] rounded-lg p-4 flex flex-col gap-3">
                    <span className="text-xs font-semibold text-white">Dasturlar Bo&apos;yicha Natija</span>
                    <div className="space-y-2 text-xs overflow-y-auto max-h-48 pr-1">
                      {analyticsData.internship_results.program_performance.map((prog) => (
                        <div key={prog.program} className="p-2 rounded bg-surface border border-white/[0.04] flex flex-col gap-1">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-white">{prog.program}</span>
                            <span className="font-mono text-emerald-400">{prog.completion_rate}%</span>
                          </div>
                          <div className="text-[10px] text-zinc-400">
                            Jami: {prog.enrolled} • Faol: {prog.active} • Yakunlangan: {prog.completed}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Quick Link to Tab 4 for Export */}
                <div className="p-4 rounded-lg bg-surface/50 border border-white/[0.06] flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 text-zinc-300">
                    <FileSpreadsheet className="w-4 h-4 text-primary" />
                    <span>Rasmiy hisobot hujjati (PDF yoki JSON) yaratish talab etiladimi?</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setActiveTab("exports");
                      if (institutionId) loadReportsAndAgreements(institutionId);
                    }}
                    className="px-3 py-1.5 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-primary font-semibold text-xs transition-all"
                  >
                    Yig&apos;ma Hisobotlar Bo&apos;limiga O&apos;tish &rarr;
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* PLACEMENT CONCLUSION MODAL (API-108) */}
      {isConclusionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-surface-card border border-white/[0.1] rounded-xl shadow-2xl p-6 flex flex-col gap-5">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2 text-white font-heading font-semibold text-base">
                <Award className="w-5 h-5 text-primary" />
                <span>Yakuniy Akademik Xulosa (API-108)</span>
              </div>
              <button
                type="button"
                onClick={() => setIsConclusionModalOpen(false)}
                aria-label="Yopish"
                className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {isLoadingContext ? (
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
                <span className="text-xs">Amaliyot akademik konteksti hisoblanmoqda...</span>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {conclusionStatusMsg && (
                  <div
                    className={`p-3 rounded-lg text-xs flex items-center gap-2 border ${
                      conclusionStatusMsg.type === "success"
                        ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
                        : "bg-rose-500/10 border-rose-500/20 text-rose-300"
                    }`}
                  >
                    {conclusionStatusMsg.type === "success" ? (
                      <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    ) : (
                      <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    )}
                    <span>{conclusionStatusMsg.text}</span>
                  </div>
                )}

                {/* Metrics Context Summary */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-surface-container p-3 rounded-lg border border-white/[0.06] text-center">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-zinc-400">Jami hisobotlar</span>
                    <span className="text-sm font-semibold font-mono tabular-nums text-zinc-200">
                      {conclusionContext?.log_count ?? 0}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-zinc-400">Topshirilgan</span>
                    <span className="text-sm font-semibold font-mono tabular-nums text-amber-300">
                      {conclusionContext?.submitted_count ?? 0}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-zinc-400">Ko‘rib chiqilgan</span>
                    <span className="text-sm font-semibold font-mono tabular-nums text-emerald-400">
                      {conclusionContext?.reviewed_count ?? 0}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-zinc-400">Qaytarilgan</span>
                    <span className="text-sm font-semibold font-mono tabular-nums text-rose-400">
                      {conclusionContext?.needs_revision_count ?? 0}
                    </span>
                  </div>
                </div>

                {conclusionContext?.current_conclusion ? (
                  <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg flex items-start gap-2.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                    <div className="flex flex-col text-xs text-emerald-200">
                      <span className="font-semibold">Ushbu amaliyot bo‘yicha xulosa berilgan:</span>
                      <span className="font-mono text-[11px] text-emerald-300 mt-0.5">
                        {conclusionContext.current_conclusion.decision || "ACADEMIC_REVIEW_COMPLETE"}
                      </span>
                    </div>
                  </div>
                ) : null}

                {/* Decision Selector */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-zinc-300">Akademik Qaror:</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setConclusionDecision("ACADEMIC_REVIEW_COMPLETE")}
                      className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 active:scale-[0.98] ${
                        conclusionDecision === "ACADEMIC_REVIEW_COMPLETE"
                          ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300"
                          : "bg-surface border-white/[0.08] text-zinc-400 hover:text-white"
                      }`}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>To‘liq Tasdiqlash</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setConclusionDecision("ACADEMIC_REVISION_REQUIRED")}
                      className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 active:scale-[0.98] ${
                        conclusionDecision === "ACADEMIC_REVISION_REQUIRED"
                          ? "bg-amber-500/20 border-amber-500/40 text-amber-300"
                          : "bg-surface border-white/[0.08] text-zinc-400 hover:text-white"
                      }`}
                    >
                      <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                      <span>Qayta ko‘rib chiqish</span>
                    </button>
                  </div>
                </div>

                {/* Reason Textarea */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-zinc-300">
                    Xulosa Asosi va Izoh (Majburiy):
                  </label>
                  <textarea
                    rows={4}
                    value={conclusionReason}
                    onChange={(e) => setConclusionReason(e.target.value)}
                    placeholder="Talabaning amaliyot davomidagi faoliyati, kundaliklar sifati va o‘zlashtirish darajasi bo‘yicha yakuniy xulosa..."
                    className="w-full bg-surface-container border border-white/[0.08] focus:border-primary rounded-lg p-3 text-xs text-white placeholder-zinc-500 focus:outline-none focus-visible:ring-1 focus-visible:ring-primary transition-all resize-none"
                  />
                  <div className="flex justify-between text-[10px] text-zinc-500">
                    <span>Minimal 1 ta belgi</span>
                    <span className="font-mono tabular-nums">{conclusionReason.length} / 2000</span>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2.5 mt-2">
                  <button
                    type="button"
                    onClick={() => setIsConclusionModalOpen(false)}
                    className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="button"
                    disabled={isSubmittingConclusion || conclusionReason.trim().length < 1}
                    onClick={handleSubmitConclusion}
                    className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 disabled:opacity-50 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
                  >
                    {isSubmittingConclusion ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Send className="w-3.5 h-3.5" />
                    )}
                    <span>Xulosani Tasdiqlash</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TEACHER NOMINATION MODAL (API-102) */}
      {isNominateModalOpen && nominatePlacement && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-surface-card border border-white/[0.1] rounded-xl shadow-2xl p-6 flex flex-col gap-5">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2 text-white font-heading font-semibold text-base">
                <UserCheck className="w-5 h-5 text-primary" />
                <span>O‘qituvchi Biriktirish (API-102)</span>
              </div>
              <button
                type="button"
                onClick={() => setIsNominateModalOpen(false)}
                aria-label="Yopish"
                className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-col gap-4">
              {nominateStatusMsg && (
                <div
                  className={`p-3 rounded-lg text-xs flex items-center gap-2 border ${
                    nominateStatusMsg.type === "success"
                      ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
                      : "bg-rose-500/10 border-rose-500/20 text-rose-300"
                  }`}
                >
                  {nominateStatusMsg.type === "success" ? (
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                  ) : (
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  )}
                  <span>{nominateStatusMsg.text}</span>
                </div>
              )}

              <div className="p-3 bg-surface-container rounded-lg border border-white/[0.06] flex flex-col gap-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Talaba:</span>
                  <span className="font-semibold text-white">{nominatePlacement.student_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Amaliyot ID:</span>
                  <span className="font-mono text-zinc-300">{nominatePlacement.placement_id.slice(0, 8)}...</span>
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-zinc-300">
                  Mas’ul O‘qituvchini Tanlang:
                </label>
                <select
                  value={selectedTeacherId}
                  onChange={(e) => setSelectedTeacherId(e.target.value)}
                  className="w-full bg-surface-container border border-white/[0.08] focus:border-primary rounded-lg p-2.5 text-xs text-white focus:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                >
                  <option value="">O‘qituvchini tanlang...</option>
                  {teachersList.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.display_name}
                    </option>
                  ))}
                </select>
                {teachersList.length === 0 && (
                  <span className="text-[11px] text-amber-400">
                    Kafedrada faol akademik o‘qituvchilar topilmadi.
                  </span>
                )}
              </div>

              <div className="flex items-center justify-end gap-2.5 mt-2">
                <button
                  type="button"
                  onClick={() => setIsNominateModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
                >
                  Bekor qilish
                </button>
                <button
                  type="button"
                  disabled={isSubmittingNominate || !selectedTeacherId}
                  onClick={handleSubmitNomination}
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 disabled:opacity-50 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary active:scale-[0.98]"
                >
                  {isSubmittingNominate ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <UserCheck className="w-3.5 h-3.5" />
                  )}
                  <span>Biriktirish</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DAILY LOG ACADEMIC REVIEW MODAL */}
      <AcademicReviewModal
        key={selectedReviewItem?.id || "empty-review-modal"}
        isOpen={isReviewModalOpen}
        onClose={() => {
          setIsReviewModalOpen(false);
          setSelectedReviewItem(null);
        }}
        revisionId={selectedReviewItem?.id || null}
        studentName={selectedReviewItem?.student_name}
        onSuccess={() => {
          loadQueue();
        }}
      />

      {/* AUTH LOGIN MODAL */}
      <AuthModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onSuccess={handleLoginSuccess}
        title="Universitet O‘qituvchisi Kirishi"
        subtitle="Kafedra o‘qituvchisi yoki koordinator hisob ma’lumotlaringizni kiriting"
      />
    </main>
  );
}
