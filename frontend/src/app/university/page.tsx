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
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";
import AcademicReviewModal from "@/components/AcademicReviewModal";

export default function UniversityPortal() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Active Tab: "queue" | "assignments" | "coordinator" | "exports"
  const [activeTab, setActiveTab] = useState<"queue" | "assignments" | "coordinator" | "exports">("queue");

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
