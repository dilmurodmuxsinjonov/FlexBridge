"use client";
import { enumLabel } from "@/lib/labels";

import { useEffect, useState, useCallback, useMemo } from "react";
import ResumeBuilder from "@/components/resume/ResumeBuilder";
import {
  User,
  Sparkles,
  Calendar,
  Clock,
  Save,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  LogIn,
  ShieldCheck,
  FileText,
  Search,
  Check,
  GraduationCap,
  Building2,
  BookOpen,
  CalendarDays,
  XCircle,
  Award,
  ExternalLink,
  FolderGit2,
  Download,
  Edit3,
  Globe,
  Github,
} from "lucide-react";
import {
  fetchAuthMe,
  fetchCandidateProfile,
  fetchCatalogSkills,
  updateCandidateSkills,
  fetchCandidateAvailability,
  saveCandidateAvailability,
  saveCandidateAvailabilityExceptions,
  fetchCandidateEnrollments,
  createCandidateEnrollment,
  endCandidateEnrollment,
  fetchVerifiedInstitutions,
  fetchCandidatePortfolios,
  createCandidatePortfolio,
  updateCandidatePortfolio,
  deleteCandidatePortfolio,
  fetchCandidateCertificates,
  createCandidateCertificate,
  deleteCandidateCertificate,
  exportCandidateResume,
  fetchCandidateResumeDetails,
  fetchCandidateApplicationsSummary,
  uploadCandidatePdfFile,
  AuthUser,
  CandidateProfileSkill,
  CatalogSkillItem,
  AvailabilityRuleItem,
  AvailabilityExceptionItem,
  CandidateEnrollmentItem,
  VerifiedInstitutionItem,
  PortfolioItem,
  CertificateItem,
  CandidateWorkExperienceItem,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";
import { SkeuoSegmented } from "@/components/skeuo/SkeuoPrimitives";
import ProfileOverview from "@/components/profile/ProfileOverview";
import EnrollmentResubmitModal from "@/components/nomzod/EnrollmentResubmitModal";
import { useAsyncData } from "@/lib/useAsyncData";
import { fetchMyTimetable } from "@/lib/timetable";


const WEEKDAY_NAMES = [
  { id: 1, name: "Dushanba" },
  { id: 2, name: "Seshanba" },
  { id: 3, name: "Chorshanba" },
  { id: 4, name: "Payshanba" },
  { id: 5, name: "Juma" },
  { id: 6, name: "Shanba" },
  { id: 7, name: "Yakshanba" },
];

function minutesToTimeString(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function timeStringToMinutes(timeStr: string): number {
  const [h, m] = timeStr.split(":").map(Number);
  return (h || 0) * 60 + (m || 0);
}

export default function CandidateProfileHub() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const applicationsQuery = useAsyncData(
    currentUser ? `applications-summary:${currentUser.user_id}` : null,
    fetchCandidateApplicationsSummary
  );
  const timetableQuery = useAsyncData(currentUser ? `my-timetable:${currentUser.user_id}` : null, () =>
    fetchMyTimetable().catch(() => null)
  );
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Active Tab: PROFILE, FULL_RESUME, SKILLS, AVAILABILITY, ENROLLMENTS, PORTFOLIO, CERTIFICATES
  const [activeTab, setActiveTab] = useState<"PROFILE" | "SKILLS" | "AVAILABILITY" | "ENROLLMENTS" | "PORTFOLIO" | "CERTIFICATES">("PROFILE");

  // Tab 1: Profile state

  // Tab 2: Skills state
  const [catalogSkills, setCatalogSkills] = useState<CatalogSkillItem[]>([]);
  const [skillSearchQuery, setSkillSearchQuery] = useState("");
  const [selectedCatalogSkillId, setSelectedCatalogSkillId] = useState("");
  const [selectedSkillLevel, setSelectedSkillLevel] = useState("INTERMEDIATE");
  const [mySkills, setMySkills] = useState<CandidateProfileSkill[]>([]);
  const [isSavingSkills, setIsSavingSkills] = useState(false);
  const [skillsSuccessMsg, setSkillsSuccessMsg] = useState<string | null>(null);
  const [skillsErrorMsg, setSkillsErrorMsg] = useState<string | null>(null);

  // Tab 3: Availability state
  const [rules, setRules] = useState<AvailabilityRuleItem[]>([]);
  const [isLoadingAvailability, setIsLoadingAvailability] = useState(false);
  const [isSavingAvailability, setIsSavingAvailability] = useState(false);
  const [availSuccessMsg, setAvailSuccessMsg] = useState<string | null>(null);
  const [availErrorMsg, setAvailErrorMsg] = useState<string | null>(null);

  // Tab 3: Availability Exceptions state (API-036)
  const [exceptions, setExceptions] = useState<AvailabilityExceptionItem[]>([]);
  const [newExcDate, setNewExcDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [newExcKind, setNewExcKind] = useState<"AVAILABLE" | "UNAVAILABLE">("UNAVAILABLE");
  const [newExcStart, setNewExcStart] = useState<string>("09:00");
  const [newExcEnd, setNewExcEnd] = useState<string>("18:00");
  const [isSavingExceptions, setIsSavingExceptions] = useState(false);
  const [excSuccessMsg, setExcSuccessMsg] = useState<string | null>(null);
  const [excErrorMsg, setExcErrorMsg] = useState<string | null>(null);

  // Tab 4: Enrollments state (API-027, API-034)
  const [enrollments, setEnrollments] = useState<CandidateEnrollmentItem[]>([]);
  const [isLoadingEnrollments, setIsLoadingEnrollments] = useState(false);
  const [institutions, setInstitutions] = useState<VerifiedInstitutionItem[]>([]);
  const [selectedInstId, setSelectedInstId] = useState<string>("");
  const [customInstId, setCustomInstId] = useState<string>("");
  const [enrProgram, setEnrProgram] = useState<string>("");
  const [enrStartDate, setEnrStartDate] = useState<string>("2023-09-01");
  const [enrEndDate, setEnrEndDate] = useState<string>("2027-06-30");
  const [enrStudentRef, setEnrStudentRef] = useState<string>("");
  const [enrEvidenceNote, setEnrEvidenceNote] = useState<string>("");
  // Proof of studies (dean-office reference PDF) - without it the request never reaches the university.
  const [enrEvidenceFile, setEnrEvidenceFile] = useState<File | null>(null);
  const [isSubmittingEnrollment, setIsSubmittingEnrollment] = useState(false);
  const [enrSuccessMsg, setEnrSuccessMsg] = useState<string | null>(null);
  const [enrErrorMsg, setEnrErrorMsg] = useState<string | null>(null);

  // End Enrollment Modal state
  const [endingEnrollment, setEndingEnrollment] = useState<CandidateEnrollmentItem | null>(null);
  const [resubmittingEnrollment, setResubmittingEnrollment] = useState<CandidateEnrollmentItem | null>(null);
  const [endReason, setEndReason] = useState<string>("");
  const [endEffectiveDate, setEndEffectiveDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [isSubmittingEnd, setIsSubmittingEnd] = useState(false);
  const [endErrorMsg, setEndErrorMsg] = useState<string | null>(null);

  // Tab 5: Portfolio state (API-026-PORTFOLIO)
  const [portfolios, setPortfolios] = useState<PortfolioItem[]>([]);
  const [isLoadingPortfolios, setIsLoadingPortfolios] = useState(false);
  const [isPortfolioModalOpen, setIsPortfolioModalOpen] = useState(false);
  const [editingPortfolioId, setEditingPortfolioId] = useState<string | null>(null);
  const [portTitle, setPortTitle] = useState("");
  const [portDesc, setPortDesc] = useState("");
  const [portProjUrl, setPortProjUrl] = useState("");
  const [portGithubUrl, setPortGithubUrl] = useState("");
  const [portSkillsInput, setPortSkillsInput] = useState("");
  const [portStartDate, setPortStartDate] = useState("");
  const [portEndDate, setPortEndDate] = useState("");
  const [isSavingPortfolio, setIsSavingPortfolio] = useState(false);
  const [portfolioSuccessMsg, setPortfolioSuccessMsg] = useState<string | null>(null);
  const [portfolioErrorMsg, setPortfolioErrorMsg] = useState<string | null>(null);

  // Tab 6: Certificates state (API-026-CERT)
  const [certificates, setCertificates] = useState<CertificateItem[]>([]);
  const [isLoadingCertificates, setIsLoadingCertificates] = useState(false);
  const [isCertModalOpen, setIsCertModalOpen] = useState(false);
  const [certTitle, setCertTitle] = useState("");
  const [certIssuer, setCertIssuer] = useState("");
  const [certIssueDate, setCertIssueDate] = useState("");
  const [certExpiryDate, setCertExpiryDate] = useState("");
  const [certCredId, setCertCredId] = useState("");
  const [certCredUrl, setCertCredUrl] = useState("");
  const [certFileId, setCertFileId] = useState("");
  const [isSavingCert, setIsSavingCert] = useState(false);
  const [certSuccessMsg, setCertSuccessMsg] = useState<string | null>(null);
  const [certErrorMsg, setCertErrorMsg] = useState<string | null>(null);

  // Header Action: Resume PDF Export state (API-026-RESUME)
  const [isExportingResume, setIsExportingResume] = useState(false);
  const [exportSuccessMsg, setExportSuccessMsg] = useState<string | null>(null);
  const [exportErrorMsg, setExportErrorMsg] = useState<string | null>(null);

  // Full Resume Details state (API-026-RESUME-DETAILS & API-026-DIRECT-UPLOAD)
  // Consent to appear in employer search (PRIVATE by default).
  const [workExperiences, setWorkExperiences] = useState<CandidateWorkExperienceItem[]>([]);
  const [profileHeadline, setProfileHeadline] = useState<string | null>(null);
  const [profileRegion, setProfileRegion] = useState<string | null>(null);
  const [resumeUpdatedAt, setResumeUpdatedAt] = useState<string | null>(null);

  // Direct PDF Upload state
  const [isUploadingCertPdf, setIsUploadingCertPdf] = useState(false);
  const [uploadedCertFilename, setUploadedCertFilename] = useState<string | null>(null);

  // Load Profile & Skills
  const loadProfileData = useCallback(async () => {
    try {
      const data = await fetchCandidateProfile();
      setMySkills(data.skills || []);
      setProfileHeadline(data.headline ?? null);
      setProfileRegion(data.region ?? null);
    } catch {
      // The resume tab loads and reports its own errors; these only feed the summary cards.
    }
  }, []);

  // Load Catalog Skills
  const loadCatalog = useCallback(async (q = "") => {
    try {
      const items = await fetchCatalogSkills(q);
      setCatalogSkills(items);
      if (items.length > 0 && !selectedCatalogSkillId) {
        setSelectedCatalogSkillId(items[0].id);
      }
    } catch {
      // Non-blocking
    }
  }, [selectedCatalogSkillId]);

  // Load Availability Rules
  const loadAvailabilityData = useCallback(async () => {
    setIsLoadingAvailability(true);
    setAvailErrorMsg(null);
    try {
      const data = await fetchCandidateAvailability();
      setRules(data.rules || []);
    } catch (err: unknown) {
      setAvailErrorMsg(err instanceof Error ? err.message : "Jadval ma'lumotlarini yuklashda xatolik");
    } finally {
      setIsLoadingAvailability(false);
    }
  }, []);

  // Load Enrollments & Institutions
  const loadEnrollmentsData = useCallback(async () => {
    setIsLoadingEnrollments(true);
    setEnrErrorMsg(null);
    try {
      const [enrs, insts] = await Promise.all([
        fetchCandidateEnrollments(),
        fetchVerifiedInstitutions().catch(() => []),
      ]);
      setEnrollments(enrs);
      setInstitutions(insts);
      if (insts.length > 0 && !selectedInstId) {
        setSelectedInstId(insts[0].id);
      }
    } catch (err: unknown) {
      setEnrErrorMsg(err instanceof Error ? err.message : "Talabalik ma'lumotlarini yuklashda xatolik");
    } finally {
      setIsLoadingEnrollments(false);
    }
  }, [selectedInstId]);

  // Load Portfolios (API-026-PORTFOLIO)
  const loadPortfoliosData = useCallback(async () => {
    setIsLoadingPortfolios(true);
    setPortfolioErrorMsg(null);
    try {
      const items = await fetchCandidatePortfolios();
      setPortfolios(items);
    } catch (err: unknown) {
      setPortfolioErrorMsg(err instanceof Error ? err.message : "Portfolio loyihalarini yuklashda xatolik");
    } finally {
      setIsLoadingPortfolios(false);
    }
  }, []);

  // Load Certificates (API-026-CERT)
  const loadCertificatesData = useCallback(async () => {
    setIsLoadingCertificates(true);
    setCertErrorMsg(null);
    try {
      const items = await fetchCandidateCertificates();
      setCertificates(items);
    } catch (err: unknown) {
      setCertErrorMsg(err instanceof Error ? err.message : "Sertifikatlarni yuklashda xatolik");
    } finally {
      setIsLoadingCertificates(false);
    }
  }, []);

  // Load Full Resume Details (API-026-RESUME-DETAILS)
  const loadResumeDetailsData = useCallback(async () => {
    try {
      const res = await fetchCandidateResumeDetails();
      setWorkExperiences(res.work_experiences || []);
      setResumeUpdatedAt(res.updated_at ?? null);
    } catch {
      // Summary cards only; the resume builder shows load errors.
    }
  }, []);

  // Auth Initialization
  useEffect(() => {
    let isMounted = true;
    async function initAuth() {
      try {
        const user = await fetchAuthMe();
        if (isMounted) {
          setCurrentUser(user);
          if (user) {
            loadProfileData();
            loadCatalog();
            loadAvailabilityData();
            loadEnrollmentsData();
            loadPortfoliosData();
            loadCertificatesData();
            loadResumeDetailsData();
          }
        }
      } catch {
        if (isMounted) setCurrentUser(null);
      } finally {
        if (isMounted) setIsAuthLoading(false);
      }
    }
    initAuth();
    return () => {
      isMounted = false;
    };
  }, [loadProfileData, loadCatalog, loadAvailabilityData, loadEnrollmentsData, loadPortfoliosData, loadCertificatesData, loadResumeDetailsData]);

  // Debounced skill search
  useEffect(() => {
    const timer = setTimeout(() => {
      loadCatalog(skillSearchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [skillSearchQuery, loadCatalog]);

  // Save Profile (API-026)
  // Add Skill (API-032)
  const handleAddSkill = async () => {
    if (!selectedCatalogSkillId) return;
    setIsSavingSkills(true);
    setSkillsSuccessMsg(null);
    setSkillsErrorMsg(null);
    try {
      await updateCandidateSkills({
        skills: [{ skill_id: selectedCatalogSkillId, level: selectedSkillLevel }],
        remove_skill_ids: [],
      });
      await loadProfileData();
      setSkillsSuccessMsg("Ko‘nikma ro‘yxatga muvaffaqiyatli qo‘shildi!");
      setTimeout(() => setSkillsSuccessMsg(null), 4000);
    } catch (err: unknown) {
      setSkillsErrorMsg(err instanceof Error ? err.message : "Ko‘nikma qo‘shishda xatolik");
    } finally {
      setIsSavingSkills(false);
    }
  };

  // Remove Skill (API-032)
  const handleRemoveSkill = async (skillId: string) => {
    setIsSavingSkills(true);
    setSkillsSuccessMsg(null);
    setSkillsErrorMsg(null);
    try {
      await updateCandidateSkills({
        skills: [],
        remove_skill_ids: [skillId],
      });
      await loadProfileData();
      setSkillsSuccessMsg("Ko‘nikma olib tashlandi.");
      setTimeout(() => setSkillsSuccessMsg(null), 3000);
    } catch (err: unknown) {
      setSkillsErrorMsg(err instanceof Error ? err.message : "O‘chirishda xatolik");
    } finally {
      setIsSavingSkills(false);
    }
  };

  // Availability Rule Manipulation (API-028)
  const addAvailabilityRule = (weekday: number) => {
    setRules((prev) => [
      ...prev,
      {
        weekday,
        start_minute: 540, // 09:00
        end_minute: 1080, // 18:00
      },
    ]);
  };

  const removeAvailabilityRule = (idx: number) => {
    setRules((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateRuleTimes = (idx: number, startStr: string, endStr: string) => {
    const s = timeStringToMinutes(startStr);
    const e = timeStringToMinutes(endStr);
    if (s >= e) return;
    setRules((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, start_minute: s, end_minute: e } : r))
    );
  };

  // Save Availability (API-028)
  const handleSaveAvailability = async () => {
    setIsSavingAvailability(true);
    setAvailSuccessMsg(null);
    setAvailErrorMsg(null);
    try {
      await saveCandidateAvailability(rules);
      setAvailSuccessMsg("Haftalik bo‘sh vaqt jadvali muvaffaqiyatli saqlandi!");
      setTimeout(() => setAvailSuccessMsg(null), 4000);
    } catch (err: unknown) {
      setAvailErrorMsg(err instanceof Error ? err.message : "Jadvalni saqlashda xatolik");
    } finally {
      setIsSavingAvailability(false);
    }
  };

  // Add Exception Item locally
  const handleAddException = () => {
    const s = timeStringToMinutes(newExcStart);
    const e = timeStringToMinutes(newExcEnd);
    if (!newExcDate || s >= e) {
      setExcErrorMsg("Noto'g'ri sana yoki vaqt oralig'i (Boshlanish tugashdan oldin bo'lishi shart)");
      return;
    }
    setExcErrorMsg(null);
    setExceptions((prev) => [
      ...prev,
      {
        local_date: newExcDate,
        kind: newExcKind,
        start_minute: s,
        end_minute: e,
      },
    ]);
  };

  const handleRemoveException = (index: number) => {
    setExceptions((prev) => prev.filter((_, i) => i !== index));
  };

  // Save Exceptions (API-036)
  const handleSaveExceptions = async () => {
    if (exceptions.length === 0) {
      setExcErrorMsg("Saqlash uchun kamida bitta sana istisnosi kiritilishi kerak.");
      return;
    }
    setIsSavingExceptions(true);
    setExcSuccessMsg(null);
    setExcErrorMsg(null);

    try {
      const dates = exceptions.map((e) => e.local_date).sort();
      const fromDate = dates[0];
      const toDate = dates[dates.length - 1];

      await saveCandidateAvailabilityExceptions({
        from_date: fromDate,
        to_date: toDate,
        exceptions,
      });

      setExcSuccessMsg("Taqvim istisnolari muvaffaqiyatli yangilandi!");
      setTimeout(() => setExcSuccessMsg(null), 4000);
    } catch (err: unknown) {
      setExcErrorMsg(err instanceof Error ? err.message : "Istisnolarni saqlashda xatolik");
    } finally {
      setIsSavingExceptions(false);
    }
  };

  // Submit Enrollment (API-027)
  const handleSubmitEnrollment = async (e: React.FormEvent) => {
    e.preventDefault();
    const instId = selectedInstId === "CUSTOM" ? customInstId.trim() : selectedInstId;
    if (!instId || !enrProgram.trim() || !enrStartDate) {
      setEnrErrorMsg("OTM, mutaxassislik/yo‘nalish va boshlanish sanasi to‘ldirilishi shart.");
      return;
    }
    if (!enrEvidenceFile) {
      setEnrErrorMsg("Talabalik ma’lumotnomasini (PDF) biriktiring — OTM xodimi shu hujjat bo‘yicha tasdiqlaydi.");
      return;
    }
    if (enrEvidenceFile.size > 10 * 1024 * 1024) {
      setEnrErrorMsg("PDF hajmi 10 MB dan oshmasligi kerak.");
      return;
    }

    setIsSubmittingEnrollment(true);
    setEnrSuccessMsg(null);
    setEnrErrorMsg(null);

    try {
      const contentBase64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ""));
        reader.onerror = () => reject(new Error("Faylni o‘qib bo‘lmadi."));
        reader.readAsDataURL(enrEvidenceFile);
      });
      const uploaded = await uploadCandidatePdfFile({
        filename: enrEvidenceFile.name,
        purpose: "CERTIFICATE",
        title: "Talabalik ma’lumotnomasi",
        content_base64: contentBase64,
      });
      const note = enrEvidenceNote.trim();
      await createCandidateEnrollment({
        institution_id: instId,
        program: enrProgram.trim(),
        start_date: enrStartDate,
        end_date: enrEndDate || null,
        student_ref: enrStudentRef.trim() || null,
        evidence_note: note.length >= 15 ? note : "Talabalik ma’lumotnomasi ilova qilindi (dekanat tomonidan berilgan).",
        file_ids: [uploaded.file_id],
      });

      setEnrSuccessMsg("Ariza yuborildi. OTM xodimi ma’lumotnomangizni tekshirib, talabaligingizni tasdiqlaydi.");
      setEnrProgram("");
      setEnrStudentRef("");
      setEnrEvidenceNote("");
      setEnrEvidenceFile(null);
      await loadEnrollmentsData();
      setTimeout(() => setEnrSuccessMsg(null), 5000);
    } catch (err: unknown) {
      setEnrErrorMsg(err instanceof Error ? err.message : "Arizani topshirishda xatolik");
    } finally {
      setIsSubmittingEnrollment(false);
    }
  };

  // End Enrollment (API-027 lifecycle)
  const handleConfirmEndEnrollment = async () => {
    if (!endingEnrollment) return;
    if (!endReason || endReason.trim().length < 15) {
      setEndErrorMsg("O'qishni yakunlash sababi kamida 15 ta belgidan iborat bo'lishi shart.");
      return;
    }

    setIsSubmittingEnd(true);
    setEndErrorMsg(null);

    try {
      await endCandidateEnrollment(endingEnrollment.id, {
        reason: endReason.trim(),
        effective_end_date: endEffectiveDate || null,
      });

      setEndingEnrollment(null);
      setEndReason("");
      await loadEnrollmentsData();
    } catch (err: unknown) {
      setEndErrorMsg(err instanceof Error ? err.message : "Talabalikni yakunlashda xatolik yuz berdi.");
    } finally {
      setIsSubmittingEnd(false);
    }
  };

  // Telemetry computation for Enrollments
  const activeEnrollment = useMemo(() => {
    return enrollments.find((e) => e.current_student && e.status !== "ENDED") || enrollments[0] || null;
  }, [enrollments]);

  // Portfolio Action Handlers (API-026-PORTFOLIO)
  const handleOpenAddPortfolio = () => {
    setEditingPortfolioId(null);
    setPortTitle("");
    setPortDesc("");
    setPortProjUrl("");
    setPortGithubUrl("");
    setPortSkillsInput("");
    setPortStartDate("");
    setPortEndDate("");
    setPortfolioErrorMsg(null);
    setIsPortfolioModalOpen(true);
  };

  const handleOpenEditPortfolio = (item: PortfolioItem) => {
    setEditingPortfolioId(item.id);
    setPortTitle(item.title);
    setPortDesc(item.description);
    setPortProjUrl(item.project_url || "");
    setPortGithubUrl(item.github_url || "");
    setPortSkillsInput((item.skills || []).join(", "));
    setPortStartDate(item.start_date || "");
    setPortEndDate(item.end_date || "");
    setPortfolioErrorMsg(null);
    setIsPortfolioModalOpen(true);
  };

  const handleSavePortfolio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (portTitle.trim().length < 2 || portDesc.trim().length < 2) {
      setPortfolioErrorMsg("Loyiha nomi va tavsifi kamida 2 ta belgidan iborat bo'lishi shart.");
      return;
    }

    if (portStartDate && portEndDate && portEndDate < portStartDate) {
      setPortfolioErrorMsg("Yakunlanish sanasi boshlanish sanasidan keyin yoki teng bo'lishi shart.");
      return;
    }

    setIsSavingPortfolio(true);
    setPortfolioErrorMsg(null);

    const skillsArray = portSkillsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      if (editingPortfolioId) {
        await updateCandidatePortfolio(editingPortfolioId, {
          title: portTitle.trim(),
          description: portDesc.trim(),
          project_url: portProjUrl.trim() || null,
          github_url: portGithubUrl.trim() || null,
          skills: skillsArray,
          start_date: portStartDate || null,
          end_date: portEndDate || null,
        });
        setPortfolioSuccessMsg("Loyiha muvaffaqiyatli yangilandi!");
      } else {
        await createCandidatePortfolio({
          title: portTitle.trim(),
          description: portDesc.trim(),
          project_url: portProjUrl.trim() || null,
          github_url: portGithubUrl.trim() || null,
          skills: skillsArray,
          start_date: portStartDate || null,
          end_date: portEndDate || null,
        });
        setPortfolioSuccessMsg("Yangi loyiha muvaffaqiyatli qo'shildi!");
      }
      setIsPortfolioModalOpen(false);
      await loadPortfoliosData();
      setTimeout(() => setPortfolioSuccessMsg(null), 4000);
    } catch (err: unknown) {
      setPortfolioErrorMsg(err instanceof Error ? err.message : "Loyihani saqlashda xatolik");
    } finally {
      setIsSavingPortfolio(false);
    }
  };

  const handleDeletePortfolio = async (id: string) => {
    if (!confirm("Haqiqatan ham bu loyihani o'chirmoqchimisiz?")) return;
    try {
      await deleteCandidatePortfolio(id);
      await loadPortfoliosData();
      setPortfolioSuccessMsg("Loyiha muvaffaqiyatli o'chirildi.");
      setTimeout(() => setPortfolioSuccessMsg(null), 3000);
    } catch (err: unknown) {
      setPortfolioErrorMsg(err instanceof Error ? err.message : "Loyihani o'chirishda xatolik");
    }
  };

  // Certificate Action Handlers (API-026-CERT)
  const handleOpenAddCert = () => {
    setCertTitle("");
    setCertIssuer("");
    setCertIssueDate(new Date().toISOString().split("T")[0]);
    setCertExpiryDate("");
    setCertCredId("");
    setCertCredUrl("");
    setCertFileId("");
    setCertErrorMsg(null);
    setIsCertModalOpen(true);
  };

  const handleSaveCert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (certTitle.trim().length < 2 || certIssuer.trim().length < 2 || !certIssueDate) {
      setCertErrorMsg("Sertifikat nomi, beruvchi tashkilot va berilgan sana kiritilishi shart.");
      return;
    }

    if (certExpiryDate && certExpiryDate < certIssueDate) {
      setCertErrorMsg("Amal qilish muddati berilgan sanadan keyin bo'lishi shart.");
      return;
    }

    setIsSavingCert(true);
    setCertErrorMsg(null);

    try {
      await createCandidateCertificate({
        title: certTitle.trim(),
        issuer: certIssuer.trim(),
        issue_date: certIssueDate,
        expiry_date: certExpiryDate || null,
        credential_id: certCredId.trim() || null,
        credential_url: certCredUrl.trim() || null,
        file_id: certFileId.trim() || null,
      });
      setIsCertModalOpen(false);
      setCertSuccessMsg("Sertifikat muvaffaqiyatli biriktirildi!");
      await loadCertificatesData();
      setTimeout(() => setCertSuccessMsg(null), 4000);
    } catch (err: unknown) {
      setCertErrorMsg(err instanceof Error ? err.message : "Sertifikatni saqlashda xatolik");
    } finally {
      setIsSavingCert(false);
    }
  };

  const handleDeleteCert = async (id: string) => {
    if (!confirm("Haqiqatan ham bu sertifikatni o'chirmoqchimisiz?")) return;
    try {
      await deleteCandidateCertificate(id);
      await loadCertificatesData();
      setCertSuccessMsg("Sertifikat muvaffaqiyatli o'chirildi.");
      setTimeout(() => setCertSuccessMsg(null), 3000);
    } catch (err: unknown) {
      setCertErrorMsg(err instanceof Error ? err.message : "Sertifikatni o'chirishda xatolik");
    }
  };

  // Resume Export Handler (API-026-RESUME)
  const handleExportResume = async () => {
    setIsExportingResume(true);
    setExportSuccessMsg(null);
    setExportErrorMsg(null);

    try {
      const res = await exportCandidateResume("PDF");
      setExportSuccessMsg(`Rezyume PDF shakllantirildi! (${res.summary?.skills_count || 0} ta ko'nikma, ${res.summary?.portfolios_count || 0} ta loyiha, ${res.summary?.certificates_count || 0} ta sertifikat).`);
      if (res.download_url) {
        window.open(res.download_url, "_blank");
      }
      setTimeout(() => setExportSuccessMsg(null), 6000);
    } catch (err: unknown) {
      setExportErrorMsg(err instanceof Error ? err.message : "Rezyume PDF shakllantirishda xatolik");
    } finally {
      setIsExportingResume(false);
    }
  };

  // Full Resume Builder Handlers (API-026-RESUME-DETAILS)
  // Direct PDF Upload for Certificates or CV (API-026-DIRECT-UPLOAD)
  const fileToBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = typeof reader.result === "string" ? reader.result : "";
        const base64 = result.includes(",") ? result.split(",")[1] : result;
        resolve(base64);
      };
      reader.onerror = () => reject(new Error("Faylni o'qishda xatolik"));
      reader.readAsDataURL(file);
    });

  const handleUploadCertificatePdf = async (file: File) => {
    setIsUploadingCertPdf(true);
    setCertErrorMsg(null);
    try {
      const fname = file.name.endsWith(".pdf") ? file.name : `${file.name}.pdf`;
      const b64 = await fileToBase64(file);
      const res = await uploadCandidatePdfFile({
        filename: fname,
        purpose: "CERTIFICATE",
        title: certTitle || "Nomzod Sertifikati",
        content_base64: b64,
      });
      setCertFileId(res.file_id);
      setUploadedCertFilename(`${res.filename} — viruslarga tekshirildi`);
    } catch (err: unknown) {
      setCertErrorMsg(err instanceof Error ? err.message : "PDF faylni yuklashda xatolik");
    } finally {
      setIsUploadingCertPdf(false);
    }
  };

  return (
    <main className="w-full flex flex-col gap-6">
      {/* HEADER SECTION (guests and loading; signed-in users get the profile overview) */}
      {!currentUser && (
      <section className="w-full skeuo-card rounded-[28px] p-5 sm:p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-sky-500/12 text-sky-700 dark:text-sky-300 border border-sky-500/25">
                Talaba kabineti
              </span>
              {currentUser ? (
                <span className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-500/12 px-2.5 py-0.5 rounded-full border border-emerald-500/25">
                  Talaba hisobi faol
                </span>
              ) : (
                <span className="text-[11px] font-semibold text-amber-800 dark:text-amber-300 bg-amber-500/12 px-2.5 py-0.5 rounded-full border border-amber-500/25">
                  Avtorizatsiyadan o‘tilmagan
                </span>
              )}
            </div>
            <h1 className="font-display text-lg md:text-xl font-bold text-[var(--fb-ink)] tracking-tight">
              Mening profilim va rezyumem
            </h1>
            <p className="text-xs text-[var(--fb-ink-muted)]">
              Rezyume, ko‘nikmalar va dars jadvalingizni shu yerda to‘ldiring — ish beruvchilar sizni aynan shu ma’lumotlar orqali topadi.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {isAuthLoading ? (
              <div className="flex items-center gap-2 text-xs text-[var(--fb-ink-muted)]">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Yuklanmoqda...</span>
              </div>
            ) : currentUser ? (
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleExportResume}
                  disabled={isExportingResume}
                  className="px-4 py-2 rounded-full skeuo-btn-obsidian text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                >
                  {isExportingResume ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Download className="w-3.5 h-3.5" />
                  )}
                  <span>Rezyumeni PDF formatida yuklab olish</span>
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setIsLoginModalOpen(true)}
                className="px-4 py-2 rounded-full skeuo-btn-obsidian text-xs font-semibold flex items-center gap-1.5"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Nomzod sifatida kirish</span>
              </button>
            )}
          </div>
        </div>
      </section>
      )}

      {currentUser && (
        <ProfileOverview
          name={currentUser.display_name}
          headline={profileHeadline}
          region={profileRegion}
          skills={mySkills}
          rules={rules}
          classes={timetableQuery.data?.status === "OK" ? timetableQuery.data.slots : undefined}
          enrollments={enrollments}
          portfolios={portfolios}
          certificates={certificates}
          experiences={workExperiences}
          resumeUpdatedAt={resumeUpdatedAt}
          applications={applicationsQuery.data ?? null}
          applicationsError={Boolean(applicationsQuery.error)}
          isExporting={isExportingResume}
          onExport={handleExportResume}
          onOpenTab={(tab) => {
            setActiveTab(tab);
            if (typeof document !== "undefined") {
              document.getElementById("fb-profile-editor")?.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          }}
        />
      )}

      {exportSuccessMsg && (
        <div className="p-3.5 rounded-2xl skeuo-card border border-emerald-500/25 text-emerald-700 dark:text-emerald-300 text-xs flex items-center gap-2 font-medium">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
          <span>{exportSuccessMsg}</span>
        </div>
      )}
      {exportErrorMsg && (
        <div className="p-3.5 rounded-2xl skeuo-card border border-rose-500/25 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2 font-medium">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
          <span>{exportErrorMsg}</span>
        </div>
      )}

      {/* LOGIN REQUIRED GATE */}
      {!currentUser && !isAuthLoading && (
        <section className="w-full skeuo-card rounded-[28px] p-10 sm:p-12 flex flex-col items-center justify-center text-center gap-3">
          <div className="w-14 h-14 rounded-2xl skeuo-well flex items-center justify-center text-[#D95F2B] mb-1">
            <User className="w-7 h-7" />
          </div>
          <h2 className="font-display text-lg font-bold text-[var(--fb-ink)]">Profilni boshqarish uchun tizimga kiring</h2>
          <p className="text-xs text-[var(--fb-ink-muted)] max-w-md leading-relaxed">
            Shaxsiy rezyume, ko‘nikmalar, OTM talabalik holati (HEMIS) va haftalik bo‘sh vaqt jadvalini sozlash uchun hisobingizga kiring.
          </p>
          <button
            type="button"
            onClick={() => setIsLoginModalOpen(true)}
            className="mt-2 px-5 py-2.5 rounded-full skeuo-btn-obsidian text-xs font-semibold"
          >
            Kirish oynasini ochish
          </button>
        </section>
      )}

      {/* AUTHENTICATED TABS & PANELS */}
      {currentUser && (() => {
        return (
        <div className="flex flex-col gap-6">
          {/* EDITOR: the overview cards above open these tabs */}
          <div id="fb-profile-editor" className="flex flex-wrap items-end justify-between gap-2 scroll-mt-24 pt-2">
            <div>
              <h2 className="font-display text-2xl font-bold tracking-tight text-[var(--fb-ink)]">Profilni tahrirlash</h2>
              <p className="text-xs text-[var(--fb-ink-muted)]">Har bir bo‘lim alohida saqlanadi.</p>
            </div>
          </div>

          {/* SKEUOMORPHIC SLIDING SEGMENTED TABS */}
          <SkeuoSegmented
            layoutName="candidateWorkspaceTabs"
            value={activeTab}
            onChange={(next) =>
              setActiveTab(
                next as
                  | "PROFILE"
                  | "SKILLS"
                  | "AVAILABILITY"
                  | "ENROLLMENTS"
                  | "PORTFOLIO"
                  | "CERTIFICATES"
              )
            }
            options={[
              { id: "PROFILE", label: "Rezyume", icon: User },
              { id: "SKILLS", label: "Ko‘nikmalar", icon: Sparkles, badge: mySkills.length || undefined },
              { id: "AVAILABILITY", label: "Jadval", icon: Calendar, badge: rules.length || undefined },
              { id: "ENROLLMENTS", label: "HEMIS", icon: GraduationCap, badge: enrollments.length || undefined },
              { id: "PORTFOLIO", label: "Portfolio", icon: FolderGit2, badge: portfolios.length || undefined },
              { id: "CERTIFICATES", label: "Sertifikatlar", icon: Award, badge: certificates.length || undefined },
            ]}
          />

          {/* LEGACY HIDDEN ACCESSIBLE BUTTONS ANCHOR END */}
          <div className="hidden" aria-hidden="true">
            <button
              type="button"
              onClick={() => setActiveTab("PROFILE")}
              className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "PROFILE"
                  ? "border-primary text-white bg-primary/5"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <User className="w-4 h-4 text-primary" />
              <span>Kasbiy Profil</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("SKILLS")}
              className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "SKILLS"
                  ? "border-primary text-white bg-primary/5"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <span>Ko‘nikmalar Katalogi</span>
              {mySkills.length > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-400">
                  {mySkills.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("AVAILABILITY")}
              className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "AVAILABILITY"
                  ? "border-primary text-white bg-primary/5"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Calendar className="w-4 h-4 text-amber-400" />
              <span>Dars & Ish Jadvali</span>
              {rules.length > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-400">
                  {rules.length} ta qoida
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("ENROLLMENTS")}
              className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "ENROLLMENTS"
                  ? "border-primary text-white bg-primary/5"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <GraduationCap className="w-4 h-4 text-blue-400" />
              <span>Talabalik & Oliy Ta’lim / HEMIS</span>
              {enrollments.length > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-blue-500/20 text-blue-400">
                  {enrollments.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("PORTFOLIO")}
              className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "PORTFOLIO"
                  ? "border-primary text-white bg-primary/5"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <FolderGit2 className="w-4 h-4 text-purple-400" />
              <span>Portfolio & Loyihalar</span>
              {portfolios.length > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-purple-500/20 text-purple-400">
                  {portfolios.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("CERTIFICATES")}
              className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                activeTab === "CERTIFICATES"
                  ? "border-primary text-white bg-primary/5"
                  : "border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Award className="w-4 h-4 text-yellow-400" />
              <span>Sertifikatlar</span>
              {certificates.length > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-yellow-500/20 text-yellow-400">
                  {certificates.length}
                </span>
              )}
            </button>
          </div>

          {/* TAB 1: RESUME BUILDER (Issue #241) */}
          {activeTab === "PROFILE" && <ResumeBuilder />}

          {/* TAB 2: SKILLS TAB */}
          {activeTab === "SKILLS" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* CURRENT SKILLS LIST */}
              <div className="lg:col-span-2 bg-[#121214] border border-white/[0.08] rounded-xl p-6 flex flex-col gap-5 shadow-sm">
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    <span>Mening Tasdiqlangan va E&apos;lon Qilingan Ko‘nikmalarim</span>
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    O‘zingiz ko‘rsatgan va tasdiqlangan ko‘nikmalar alohida belgilanadi. Vakansiyalarga moslik shu ro‘yxat asosida hisoblanadi.
                  </p>
                </div>

                {skillsSuccessMsg && (
                  <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    <span>{skillsSuccessMsg}</span>
                  </div>
                )}

                {skillsErrorMsg && (
                  <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{skillsErrorMsg}</span>
                  </div>
                )}

                {mySkills.length === 0 ? (
                  <div className="py-12 border border-dashed border-white/[0.08] rounded-xl flex flex-col items-center justify-center text-center p-6 gap-2 text-zinc-500">
                    <Sparkles className="w-6 h-6 stroke-1 text-zinc-600" />
                    <p className="text-xs">Hozircha birorta ham ko‘nikma biriktirilmagan.</p>
                    <p className="text-[11px] text-zinc-600">
                      O‘ng tomondagi qidiruv orqali katalogdan o‘zingizga mos texnologiyalarni qo‘shing.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {mySkills.map((s) => (
                      <div
                        key={s.skill_id}
                        className="p-3.5 rounded-xl bg-surface border border-white/[0.06] flex items-center justify-between gap-3 group hover:border-white/[0.12] transition-colors"
                      >
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-white">
                              {s.name_uz || s.name_ru || s.code || s.skill_id.slice(0, 8)}
                            </span>
                            {s.verified ? (
                              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                                <ShieldCheck className="w-3 h-3" />
                                <span>Tasdiqlangan</span>
                              </span>
                            ) : (
                              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400">
                                O‘zi ko‘rsatgan
                              </span>
                            )}
                          </div>
                          <span className="text-[11px] text-zinc-400 font-mono">
                            Daraja: {enumLabel(s.level)}
                          </span>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleRemoveSkill(s.skill_id)}
                          disabled={isSavingSkills}
                          className="p-1.5 rounded-lg text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                          title="O‘chirish"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* ADD SKILL FORM */}
              <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-6 flex flex-col gap-4 shadow-sm h-fit">
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Plus className="w-4 h-4 text-primary" />
                    <span>Yangi Ko‘nikma Qo‘shish</span>
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">Katalogdagi standart ko‘nikmalar bazasidan qidiring.</p>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-zinc-300 flex items-center gap-1.5">
                    <Search className="w-3.5 h-3.5 text-zinc-400" />
                    <span>Ko‘nikma Nomi bo‘yicha qidiruv</span>
                  </label>
                  <input
                    type="text"
                    value={skillSearchQuery}
                    onChange={(e) => setSkillSearchQuery(e.target.value)}
                    placeholder="Qidiruv: Python, React, SQL..."
                    className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-zinc-300">Katalogdan tanlang</label>
                  <select
                    value={selectedCatalogSkillId}
                    onChange={(e) => setSelectedCatalogSkillId(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none focus:border-primary/50"
                  >
                    {catalogSkills.length === 0 ? (
                      <option value="">Ko‘nikmalar topilmadi</option>
                    ) : (
                      catalogSkills.map((sk) => (
                        <option key={sk.id} value={sk.id} className="bg-surface text-white">
                          {sk.name_uz || sk.code}{sk.category && !/^[A-Z]{2}_[0-9a-f]+$/i.test(sk.category) ? ` (${sk.category})` : ""}
                        </option>
                      ))
                    )}
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-zinc-300">Bilim Darajangiz</label>
                  <select
                    value={selectedSkillLevel}
                    onChange={(e) => setSelectedSkillLevel(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none focus:border-primary/50"
                  >
                    <option value="BEGINNER" className="bg-surface text-white">
                      Boshlang‘ich
                    </option>
                    <option value="INTERMEDIATE" className="bg-surface text-white">
                      O‘rta (mustaqil ishlay oladi)
                    </option>
                    <option value="ADVANCED" className="bg-surface text-white">
                      Yuqori (katta amaliy tajriba)
                    </option>
                  </select>
                </div>

                <button
                  type="button"
                  onClick={handleAddSkill}
                  className="w-full mt-2 px-3.5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center justify-center gap-2 shadow-md shadow-primary/20"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Ro‘yxatga qo‘shish</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: AVAILABILITY & EXCEPTIONS TAB */}
          {activeTab === "AVAILABILITY" && (
            <div className="flex flex-col gap-6 max-w-4xl">
              {/* RECURRING WEEKLY SCHEDULE */}
              <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-6 flex flex-col gap-5 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-amber-400" />
                      <span>Haftalik Dars va Ish Oralig‘i Grafigi (Takrorlanuvchi)</span>
                    </h3>
                    <p className="text-xs text-zinc-400 mt-0.5">
                      O‘zR MK 118-moddasi talabi: dars vaqti bilan amaliyot/ish soatlari to‘qnashmasligi shart (kuniga 8 soatdan oshmasin).
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleSaveAvailability}
                    disabled={isSavingAvailability}
                    className="px-4 py-2 rounded-xl skeuo-btn-accent disabled:opacity-50 text-xs font-semibold text-white flex items-center gap-1.5 self-start sm:self-auto"
                  >
                    {isSavingAvailability ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Save className="w-3.5 h-3.5" />
                    )}
                    <span>Jadvalni Saqlash</span>
                  </button>
                </div>

                {availSuccessMsg && (
                  <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    <span>{availSuccessMsg}</span>
                  </div>
                )}

                {availErrorMsg && (
                  <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{availErrorMsg}</span>
                  </div>
                )}

                {isLoadingAvailability ? (
                  <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                    <span className="text-xs">Jadval ma&apos;lumotlari yuklanmoqda...</span>
                  </div>
                ) : (
                  <div className="flex flex-col gap-4">
                    {WEEKDAY_NAMES.map((day) => {
                      const dayRules = rules.map((r, idx) => ({ ...r, originalIndex: idx })).filter((r) => r.weekday === day.id);
                      const totalDayMinutes = dayRules.reduce((sum, r) => sum + (r.end_minute - r.start_minute), 0);
                      const isLimitExceeded = totalDayMinutes > 480;

                      return (
                        <div
                          key={day.id}
                          className="p-4 rounded-xl bg-surface border border-white/[0.06] flex flex-col gap-3"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-white">{day.name}</span>
                              <span
                                className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                                  totalDayMinutes === 0
                                    ? "bg-zinc-800 text-zinc-400"
                                    : isLimitExceeded
                                    ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                                    : "bg-primary/20 text-blue-300 border border-primary/30"
                                }`}
                              >
                                {totalDayMinutes > 0
                                  ? `${Math.floor(totalDayMinutes / 60)} soat ${totalDayMinutes % 60} daqiqa`
                                  : "Dam olish kuni"}
                              </span>
                            </div>

                            <button
                              type="button"
                              onClick={() => addAvailabilityRule(day.id)}
                              className="px-2.5 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08] text-[11px] font-semibold text-primary flex items-center gap-1 transition-all"
                            >
                              <Plus className="w-3 h-3" />
                              <span>Vaqt oralig‘i qo‘shish</span>
                            </button>
                          </div>

                          {dayRules.length === 0 ? (
                            <span className="text-[11px] text-zinc-500 italic">
                              Ushbu kunda ishlash rejalashtirilmagan.
                            </span>
                          ) : (
                            <div className="flex flex-col gap-2">
                              {dayRules.map((r) => (
                                <div
                                  key={r.originalIndex}
                                  className="flex flex-wrap items-center gap-3 p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                                >
                                  <div className="flex items-center gap-1.5 text-xs text-zinc-300">
                                    <Clock className="w-3.5 h-3.5 text-primary" />
                                    <span>Boshlanish:</span>
                                    <input
                                      type="time"
                                      value={minutesToTimeString(r.start_minute)}
                                      onChange={(e) =>
                                        updateRuleTimes(
                                          r.originalIndex,
                                          e.target.value,
                                          minutesToTimeString(r.end_minute)
                                        )
                                      }
                                      className="px-2 py-1 rounded bg-surface border border-white/[0.08] text-xs text-white font-mono focus:outline-none"
                                    />
                                  </div>

                                  <div className="flex items-center gap-1.5 text-xs text-zinc-300">
                                    <span>Tugash:</span>
                                    <input
                                      type="time"
                                      value={minutesToTimeString(r.end_minute)}
                                      onChange={(e) =>
                                        updateRuleTimes(
                                          r.originalIndex,
                                          minutesToTimeString(r.start_minute),
                                          e.target.value
                                        )
                                      }
                                      className="px-2 py-1 rounded bg-surface border border-white/[0.08] text-xs text-white font-mono focus:outline-none"
                                    />
                                  </div>

                                  <span className="text-[11px] font-mono text-zinc-400">
                                    ({r.end_minute - r.start_minute} daqiqa)
                                  </span>

                                  <button
                                    type="button"
                                    onClick={() => removeAvailabilityRule(r.originalIndex)}
                                    className="ml-auto text-zinc-500 hover:text-rose-400 transition-colors"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* CALENDAR DATE EXCEPTIONS & EXAMS (API-036) */}
              <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-6 flex flex-col gap-5 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <CalendarDays className="w-4 h-4 text-sky-400" />
                      <span>Sana Bo‘yicha Maxsus Kunlar & Imtihon Istisnolari</span>
                    </h3>
                    <p className="text-xs text-zinc-400 mt-0.5">
                      Muayyan sanalar uchun maxsus bo‘sh yoki band (imtihon, ta’til, dam olish) soatlaringizni belgilang.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleSaveExceptions}
                    disabled={isSavingExceptions || exceptions.length === 0}
                    className="px-4 py-2 rounded-xl skeuo-btn-obsidian disabled:opacity-50 text-xs font-semibold text-white flex items-center gap-1.5 self-start sm:self-auto"
                  >
                    {isSavingExceptions ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Save className="w-3.5 h-3.5" />
                    )}
                    <span>Istisnolarni Saqlash</span>
                  </button>
                </div>

                {excSuccessMsg && (
                  <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    <span>{excSuccessMsg}</span>
                  </div>
                )}

                {excErrorMsg && (
                  <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{excErrorMsg}</span>
                  </div>
                )}

                {/* ADD NEW EXCEPTION FORM */}
                <div className="p-4 rounded-xl bg-surface border border-white/[0.06] flex flex-col gap-3">
                  <span className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                    <Plus className="w-3.5 h-3.5 text-sky-400" />
                    <span>Yangi Sana Istisnosi Kiritish</span>
                  </span>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    <div className="flex flex-col gap-1">
                      <label className="text-[11px] text-zinc-400">Sana</label>
                      <input
                        type="date"
                        value={newExcDate}
                        onChange={(e) => setNewExcDate(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-[#121214] border border-white/[0.08] text-xs text-white focus:outline-none"
                      />
                    </div>

                    <div className="flex flex-col gap-1">
                      <label className="text-[11px] text-zinc-400">Holat turi</label>
                      <select
                        value={newExcKind}
                        onChange={(e) => setNewExcKind(e.target.value as "AVAILABLE" | "UNAVAILABLE")}
                        className="px-3 py-1.5 rounded-lg bg-[#121214] border border-white/[0.08] text-xs text-white focus:outline-none"
                      >
                        <option value="UNAVAILABLE">Band (imtihon / tadbir)</option>
                        <option value="AVAILABLE">Bo&apos;sh (qo&apos;shimcha smena)</option>
                      </select>
                    </div>

                    <div className="flex flex-col gap-1">
                      <label className="text-[11px] text-zinc-400">Boshlanish</label>
                      <input
                        type="time"
                        value={newExcStart}
                        onChange={(e) => setNewExcStart(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-[#121214] border border-white/[0.08] text-xs text-white font-mono focus:outline-none"
                      />
                    </div>

                    <div className="flex flex-col gap-1">
                      <label className="text-[11px] text-zinc-400">Tugash</label>
                      <input
                        type="time"
                        value={newExcEnd}
                        onChange={(e) => setNewExcEnd(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-[#121214] border border-white/[0.08] text-xs text-white font-mono focus:outline-none"
                      />
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleAddException}
                    className="self-end px-3 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-xs font-semibold text-white flex items-center gap-1.5 transition-all mt-1"
                  >
                    <Plus className="w-3.5 h-3.5 text-sky-400" />
                    <span>Ro&apos;yxatga qo&apos;shish</span>
                  </button>
                </div>

                {/* CURRENT EXCEPTIONS LIST */}
                {exceptions.length === 0 ? (
                  <div className="py-6 border border-dashed border-white/[0.08] rounded-xl flex items-center justify-center text-zinc-500 text-xs">
                    Hozircha birorta sana istisnosi kiritilmagan.
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-medium text-zinc-400">Kiritilgan istisnolar ({exceptions.length} ta):</span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {exceptions.map((exc, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-surface border border-white/[0.06] flex items-center justify-between gap-3"
                        >
                          <div className="flex flex-col gap-0.5">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-white font-mono">{exc.local_date}</span>
                              <span
                                className={`text-[10px] font-mono px-1.5 py-0.2 rounded font-semibold ${
                                  exc.kind === "UNAVAILABLE"
                                    ? "bg-rose-500/10 text-rose-300 border border-rose-500/20"
                                    : "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                                }`}
                              >
                                {enumLabel(exc.kind)}
                              </span>
                            </div>
                            <span className="text-[11px] text-zinc-400 font-mono">
                              {minutesToTimeString(exc.start_minute)} - {minutesToTimeString(exc.end_minute)} ({exc.end_minute - exc.start_minute} daqiqa)
                            </span>
                          </div>

                          <button
                            type="button"
                            onClick={() => handleRemoveException(idx)}
                            className="text-zinc-500 hover:text-rose-400 p-1 rounded transition-colors"
                            title="O'chirish"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: ENROLLMENTS & HEMIS TAB (API-027, API-034) */}
          {activeTab === "ENROLLMENTS" && (
            <div className="flex flex-col gap-6 max-w-5xl">
              {/* TELEMETRY 4 METRICS CARDS */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] flex flex-col gap-1.5">
                  <span className="text-[11px] font-medium text-zinc-400 flex items-center gap-1.5">
                    <GraduationCap className="w-3.5 h-3.5 text-blue-400" />
                    <span>Talabalik Holati</span>
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-white font-mono">
                      {activeEnrollment ? activeEnrollment.status : "Ro'yxatda yo'q"}
                    </span>
                    {activeEnrollment?.current_student && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Faol
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-zinc-500">
                    {activeEnrollment ? "Davlat ro'yxatidan o'tgan" : "Talaba emasmisiz? Bo'sh qoldiring"}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] flex flex-col gap-1.5">
                  <span className="text-[11px] font-medium text-zinc-400 flex items-center gap-1.5">
                    <Building2 className="w-3.5 h-3.5 text-sky-400" />
                    <span>Biriktirilgan OTM</span>
                  </span>
                  <span className="text-sm font-bold text-white truncate" title={activeEnrollment?.institution_name || "Mavjud emas"}>
                    {activeEnrollment?.institution_name || "Mavjud emas"}
                  </span>
                  <span className="text-[10px] text-zinc-500 truncate">
                    {activeEnrollment ? enumLabel(activeEnrollment.status) : "Talabalik qo‘shilmagan"}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] flex flex-col gap-1.5">
                  <span className="text-[11px] font-medium text-zinc-400 flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
                    <span>HEMIS ID / Talaba Kodi</span>
                  </span>
                  <span className="text-base font-bold text-white font-mono">
                    {activeEnrollment?.student_ref || "Kiritilmagan"}
                  </span>
                  <span className="text-[10px] text-zinc-500">
                    {activeEnrollment?.student_ref ? "HEMIS v3.2 integratsiyasi" : "Talaba ID kiritilishi mumkin"}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] flex flex-col gap-1.5">
                  <span className="text-[11px] font-medium text-zinc-400 flex items-center gap-1.5">
                    <Award className="w-3.5 h-3.5 text-amber-400" />
                    <span>Ta&apos;lim Dasturi</span>
                  </span>
                  <span className="text-sm font-bold text-white truncate" title={activeEnrollment?.program || "N/A"}>
                    {activeEnrollment?.program || "Tanlanmagan"}
                  </span>
                  <span className="text-[10px] text-zinc-500">
                    {activeEnrollment ? `${activeEnrollment.start_date} dan` : "Dastur kiritilmagan"}
                  </span>
                </div>
              </div>

              {enrSuccessMsg && (
                <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                  <span>{enrSuccessMsg}</span>
                </div>
              )}

              {enrErrorMsg && (
                <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{enrErrorMsg}</span>
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* ENROLLMENTS HISTORY LIST (API-034) */}
                <div className="lg:col-span-2 bg-[#121214] border border-white/[0.08] rounded-xl p-6 flex flex-col gap-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                        <GraduationCap className="w-4 h-4 text-blue-400" />
                        <span>Mening Talabalik Hujjatlarim & OTM Birikishlari</span>
                      </h3>
                      <p className="text-xs text-zinc-400 mt-0.5">
                        Oliygoh yoki texnikum bilan tasdiqlangan akademik munosabatlar tarixi.
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={loadEnrollmentsData}
                      disabled={isLoadingEnrollments}
                      className="px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-xs text-zinc-300 flex items-center gap-1.5 transition-all"
                    >
                      <Loader2 className={`w-3.5 h-3.5 ${isLoadingEnrollments ? "animate-spin text-primary" : ""}`} />
                      <span>Yangilash</span>
                    </button>
                  </div>

                  {isLoadingEnrollments ? (
                    <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
                      <Loader2 className="w-6 h-6 animate-spin text-primary" />
                      <span className="text-xs">Ma&apos;lumotlar yuklanmoqda...</span>
                    </div>
                  ) : enrollments.length === 0 ? (
                    <div className="py-12 border border-dashed border-white/[0.08] rounded-xl flex flex-col items-center justify-center text-center p-6 gap-2 text-zinc-500">
                      <GraduationCap className="w-8 h-8 stroke-1 text-zinc-600" />
                      <p className="text-xs">Hozircha birorta ham talabalik arizasi yoki OTM birikishi mavjud emas.</p>
                      <p className="text-[11px] text-zinc-600">
                        O&apos;ng tomondagi shakl orqali o&apos;z oliygohingizni tanlab, HEMIS ma&apos;lumotlaringizni kiriting.
                      </p>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3">
                      {enrollments.map((enr) => {
                        const isVerified = enr.status === "VERIFIED";
                        const isEnded = enr.status === "ENDED";
                        const isPending = enr.status === "PENDING" || enr.status === "IN_REVIEW";

                        return (
                          <div
                            key={enr.id}
                            className="p-4 rounded-xl bg-surface border border-white/[0.06] flex flex-col gap-3 hover:border-white/[0.12] transition-colors"
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                              <div className="flex flex-col gap-0.5">
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-bold text-white">
                                    {enr.institution_name || `Muassasa: ${enr.institution_id.slice(0, 8)}...`}
                                  </span>
                                  <span
                                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                                      isVerified
                                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                        : isEnded
                                        ? "bg-zinc-800 text-zinc-400"
                                        : isPending
                                        ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                        : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                                    }`}
                                  >
                                    {enumLabel(enr.status)}
                                  </span>
                                  {enr.case_status && (
                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.06] text-zinc-300 border border-white/10">
                                      {enumLabel(enr.case_status)}
                                    </span>
                                  )}
                                </div>
                                <span className="text-xs text-zinc-300 font-medium">
                                  {enr.program}
                                </span>
                              </div>

                              <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
                                {!isVerified &&
                                  !isEnded &&
                                  (!enr.case_status ||
                                    ["DRAFT", "NEEDS_INFO", "REJECTED"].includes(enr.case_status)) && (
                                    <button
                                      type="button"
                                      onClick={() => setResubmittingEnrollment(enr)}
                                      className="px-3 py-1.5 rounded-lg bg-blue-500/15 hover:bg-blue-500/25 text-xs font-semibold text-blue-300 border border-blue-500/25 transition-all"
                                    >
                                      Hujjatni qayta yuborish
                                    </button>
                                  )}
                                {!isEnded && (
                                  <button
                                    type="button"
                                    onClick={() => setEndingEnrollment(enr)}
                                    className="px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-xs font-semibold text-rose-300 border border-rose-500/20 transition-all"
                                  >
                                    O&apos;qishni yakunlash
                                  </button>
                                )}
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center gap-y-1 gap-x-4 text-[11px] text-zinc-400 pt-1 border-t border-white/[0.04]">
                              {enr.student_ref && (
                                <span>
                                  HEMIS ID: <strong className="text-white font-mono">{enr.student_ref}</strong>
                                </span>
                              )}
                              <span>
                                Davr: <strong className="text-zinc-200">{enr.start_date}</strong> dan {enr.end_date || "Hozirgacha"}
                              </span>
                              <span>
                                Tekshiruv: <strong className={enr.reviewed ? "text-emerald-400" : "text-amber-400"}>
                                  {enr.reviewed ? "Tasdiqlangan" : "Kutilmoqda"}
                                </strong>
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* CREATE ENROLLMENT FORM (API-027) */}
                <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-6 flex flex-col gap-4 shadow-sm h-fit">
                  <div>
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Plus className="w-4 h-4 text-blue-400" />
                      <span>OTMga Birikish (Yangi Ariza)</span>
                    </h3>
                    <p className="text-xs text-zinc-400 mt-0.5">
                      Davlat akkreditatsiyasidan o‘tgan OTMni tanlab talabalik hisobingizni tasdiqlang.
                    </p>
                  </div>

                  <form onSubmit={handleSubmitEnrollment} className="flex flex-col gap-3.5">
                    <div className="flex flex-col gap-1">
                      <label className="text-xs font-medium text-zinc-300">Oliygoh / Muassasa</label>
                      <select
                        value={selectedInstId}
                        onChange={(e) => setSelectedInstId(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none focus:border-primary/50"
                      >
                        {institutions.map((inst) => (
                          <option key={inst.id} value={inst.id} className="bg-surface text-white">
                            {inst.name} ({inst.region})
                          </option>
                        ))}
                        <option value="CUSTOM" className="bg-surface text-amber-300">
                          + Boshqa OTM (Maxsus UUID kiritish)
                        </option>
                      </select>
                    </div>

                    {selectedInstId === "CUSTOM" && (
                      <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium text-zinc-300">Muassasa UUID kodi</label>
                        <input
                          type="text"
                          value={customInstId}
                          onChange={(e) => setCustomInstId(e.target.value)}
                          placeholder="masalan: e75f28ed-446e-4d0a-a538-..."
                          className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white font-mono placeholder-zinc-500 focus:outline-none focus:border-primary/50"
                        />
                      </div>
                    )}

                    <div className="flex flex-col gap-1">
                      <label className="text-xs font-medium text-zinc-300">Mutaxassislik / Yo&apos;nalish</label>
                      <input
                        type="text"
                        value={enrProgram}
                        onChange={(e) => setEnrProgram(e.target.value)}
                        placeholder="Masalan: Dasturiy Injiniring (Bakalavr)"
                        className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2.5">
                      <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium text-zinc-300">Boshlanish</label>
                        <input
                          type="date"
                          value={enrStartDate}
                          onChange={(e) => setEnrStartDate(e.target.value)}
                          className="px-2.5 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none"
                        />
                      </div>

                      <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium text-zinc-300">Kutilayotgan tugash</label>
                        <input
                          type="date"
                          value={enrEndDate}
                          onChange={(e) => setEnrEndDate(e.target.value)}
                          className="px-2.5 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none"
                        />
                      </div>
                    </div>

                    <div className="flex flex-col gap-1">
                      <label className="text-xs font-medium text-zinc-300">HEMIS ID / Talaba raqami (Ixtiyoriy)</label>
                      <input
                        type="text"
                        value={enrStudentRef}
                        onChange={(e) => setEnrStudentRef(e.target.value)}
                        placeholder="Masalan: 3912011005"
                        className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white font-mono placeholder-zinc-500 focus:outline-none focus:border-primary/50"
                      />
                    </div>

                    <div className="flex flex-col gap-1">
                      <label htmlFor="enr-evidence" className="text-xs font-medium text-zinc-300">
                        Talabalik ma’lumotnomasi (PDF, majburiy)
                      </label>
                      <input
                        id="enr-evidence"
                        type="file"
                        accept=".pdf,application/pdf"
                        onChange={(e) => setEnrEvidenceFile(e.target.files?.[0] ?? null)}
                        className="text-xs text-zinc-300 file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border-0 file:bg-white/[0.08] file:text-zinc-200"
                      />
                      <span className="text-[11px] text-zinc-500">
                        Dekanatdan olingan ma’lumotnoma yoki talaba guvohnomasi nusxasi. OTM xodimi shu hujjat bo‘yicha tasdiqlaydi.
                      </span>
                    </div>

                    <div className="flex flex-col gap-1">
                      <label className="text-xs font-medium text-zinc-300">Izoh va Asos</label>
                      <textarea
                        rows={2}
                        value={enrEvidenceNote}
                        onChange={(e) => setEnrEvidenceNote(e.target.value)}
                        placeholder="Talabalik hujjati yoki ma'lumotnoma izohi..."
                        className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50 resize-y"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={isSubmittingEnrollment}
                      className="w-full mt-2 px-4 py-2.5 rounded-xl skeuo-btn-accent disabled:opacity-50 text-xs font-semibold text-white flex items-center justify-center gap-2"
                    >
                      {isSubmittingEnrollment ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Plus className="w-3.5 h-3.5" />
                      )}
                      <span>Arizani Yuborish</span>
                    </button>
                  </form>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: PORTFOLIO SHOWCASE (API-026-PORTFOLIO) */}
          {activeTab === "PORTFOLIO" && (
            <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-6 flex flex-col gap-6 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <FolderGit2 className="w-4 h-4 text-purple-400" />
                    <span>Portfolio & Loyihalar Namoyishi</span>
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Amalga oshirgan loyihalaringiz, havola va ko&apos;nikmalaringizni ish beruvchilarga taqdim eting.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleOpenAddPortfolio}
                  className="px-3.5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-purple-600/20 shrink-0"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Yangi loyiha qo&apos;shish</span>
                </button>
              </div>

              {portfolioSuccessMsg && (
                <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                  <span>{portfolioSuccessMsg}</span>
                </div>
              )}

              {portfolioErrorMsg && (
                <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{portfolioErrorMsg}</span>
                </div>
              )}

              {isLoadingPortfolios ? (
                <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
                  <Loader2 className="w-6 h-6 animate-spin text-purple-400" />
                  <span className="text-xs">Portfolio loyihalari yuklanmoqda...</span>
                </div>
              ) : portfolios.length === 0 ? (
                <div className="py-12 px-4 rounded-xl border border-dashed border-white/[0.08] flex flex-col items-center justify-center text-center gap-2">
                  <FolderGit2 className="w-8 h-8 text-zinc-500" />
                  <span className="text-xs font-semibold text-zinc-300">Hozircha loyihalar mavjud emas</span>
                  <p className="text-xs text-zinc-500 max-w-sm">
                    Rezyumengizni boyitish uchun bajargan amaliy ishlaringiz yoki mustaqil loyihalaringizni qo&apos;shing.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {portfolios.map((item) => (
                    <div
                      key={item.id}
                      className="bg-surface border border-white/[0.06] hover:border-purple-500/30 rounded-xl p-4 flex flex-col justify-between gap-3 transition-colors"
                    >
                      <div className="flex flex-col gap-2">
                        <div className="flex items-start justify-between gap-2">
                          <h4 className="text-xs font-bold text-white line-clamp-1">{item.title}</h4>
                          <span className="text-[10px] text-zinc-500 font-mono shrink-0">
                            {item.start_date || "—"} {item.end_date ? `— ${item.end_date}` : "— Hozir"}
                          </span>
                        </div>
                        <p className="text-xs text-zinc-400 line-clamp-3 whitespace-pre-line">{item.description}</p>
                        {item.skills && item.skills.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {item.skills.map((s, idx) => (
                              <span
                                key={idx}
                                className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20"
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="flex items-center justify-between pt-2 border-t border-white/[0.04] text-xs">
                        <div className="flex items-center gap-2">
                          {item.project_url && (
                            <a
                              href={item.project_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-primary hover:underline text-[11px] flex items-center gap-1"
                            >
                              <Globe className="w-3 h-3" />
                              <span>Demo</span>
                              <ExternalLink className="w-2.5 h-2.5 opacity-70" />
                            </a>
                          )}
                          {item.github_url && (
                            <a
                              href={item.github_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-zinc-300 hover:text-white text-[11px] flex items-center gap-1"
                            >
                              <Github className="w-3 h-3" />
                              <span>Kod</span>
                              <ExternalLink className="w-2.5 h-2.5 opacity-70" />
                            </a>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => handleOpenEditPortfolio(item)}
                            className="p-1.5 rounded hover:bg-white/[0.06] text-zinc-400 hover:text-zinc-200 transition-colors"
                            title="Tahrirlash"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeletePortfolio(item.id)}
                            className="p-1.5 rounded hover:bg-rose-500/10 text-zinc-400 hover:text-rose-400 transition-colors"
                            title="O'chirish"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 6: CERTIFICATES (API-026-CERT) */}
          {activeTab === "CERTIFICATES" && (
            <div className="bg-[#121214] border border-white/[0.08] rounded-xl p-6 flex flex-col gap-6 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Award className="w-4 h-4 text-yellow-400" />
                    <span>Sertifikatlar & Malaka Hujjatlari</span>
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Kasbiy sertifikatlar, litsenziyalar va xalqaro imtihon natijalari.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleOpenAddCert}
                  className="px-3.5 py-2 rounded-lg bg-yellow-600 hover:bg-yellow-500 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-yellow-600/20 shrink-0"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Sertifikat qo&apos;shish</span>
                </button>
              </div>

              {certSuccessMsg && (
                <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                  <span>{certSuccessMsg}</span>
                </div>
              )}

              {certErrorMsg && (
                <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{certErrorMsg}</span>
                </div>
              )}

              {isLoadingCertificates ? (
                <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
                  <Loader2 className="w-6 h-6 animate-spin text-yellow-400" />
                  <span className="text-xs">Sertifikatlar yuklanmoqda...</span>
                </div>
              ) : certificates.length === 0 ? (
                <div className="py-12 px-4 rounded-xl border border-dashed border-white/[0.08] flex flex-col items-center justify-center text-center gap-2">
                  <Award className="w-8 h-8 text-zinc-500" />
                  <span className="text-xs font-semibold text-zinc-300">Hozircha sertifikatlar mavjud emas</span>
                  <p className="text-xs text-zinc-500 max-w-sm">
                    Kasbiy malaka yoki til sertifikatlaringizni yuklab, profilda aks ettiring.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {certificates.map((cert) => (
                    <div
                      key={cert.id}
                      className="bg-surface border border-white/[0.06] hover:border-yellow-500/30 rounded-xl p-4 flex flex-col justify-between gap-3 transition-colors"
                    >
                      <div className="flex flex-col gap-2">
                        <div className="flex items-start justify-between gap-2">
                          <h4 className="text-xs font-bold text-white line-clamp-1">{cert.title}</h4>
                          <span className="text-[10px] text-zinc-500 font-mono shrink-0">
                            {cert.issue_date} {cert.expiry_date ? `(Amal qiladi: ${cert.expiry_date})` : "(Muddatsiz)"}
                          </span>
                        </div>
                        <div className="text-xs text-zinc-400 flex items-center gap-1.5">
                          <Building2 className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                          <span>Beruvchi: {cert.issuer}</span>
                        </div>
                        {cert.credential_id && (
                          <div className="text-[11px] text-zinc-500 font-mono">
                            ID: {cert.credential_id}
                          </div>
                        )}
                        {cert.file_id && (
                          <div className="pt-1">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <ShieldCheck className="w-3 h-3" />
                              <span>Toza hujjat biriktirilgan {cert.file_name ? `(${cert.file_name})` : ""}</span>
                            </span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center justify-between pt-2 border-t border-white/[0.04] text-xs">
                        <div>
                          {cert.credential_url ? (
                            <a
                              href={cert.credential_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-yellow-400 hover:underline text-[11px] flex items-center gap-1"
                            >
                              <span>Tekshirish havolasi</span>
                              <ExternalLink className="w-2.5 h-2.5 opacity-70" />
                            </a>
                          ) : (
                            <span className="text-[11px] text-zinc-600">Tekshiruv havolasi yo&apos;q</span>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => handleDeleteCert(cert.id)}
                          className="p-1.5 rounded hover:bg-rose-500/10 text-zinc-400 hover:text-rose-400 transition-colors"
                          title="O'chirish"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        );
      })()}

      {/* PORTFOLIO MODAL */}
      {isPortfolioModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#121214] border border-white/[0.1] rounded-2xl max-w-lg w-full p-6 shadow-2xl flex flex-col gap-5">
            <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <FolderGit2 className="w-4 h-4 text-purple-400" />
                <span>{editingPortfolioId ? "Portfolio Loyihasini Tahrirlash" : "Yangi Portfolio Loyihasi"}</span>
              </h3>
              <button
                type="button"
                onClick={() => setIsPortfolioModalOpen(false)}
                className="text-zinc-500 hover:text-zinc-300 text-sm"
              >
                ✕
              </button>
            </div>

            {portfolioErrorMsg && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{portfolioErrorMsg}</span>
              </div>
            )}

            <form onSubmit={handleSavePortfolio} className="flex flex-col gap-3.5">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium text-zinc-300">Loyiha Nomi *</label>
                <input
                  type="text"
                  value={portTitle}
                  onChange={(e) => setPortTitle(e.target.value)}
                  placeholder="Masalan: FlexBridge Talent Exchange"
                  className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/50"
                  required
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium text-zinc-300">Loyiha Tavsifi *</label>
                <textarea
                  rows={3}
                  value={portDesc}
                  onChange={(e) => setPortDesc(e.target.value)}
                  placeholder="Loyiha maqsadi, arxitekturasi va sizning hissangiz..."
                  className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/50 resize-y"
                  required
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-zinc-300">Demo Havolasi (Ixtiyoriy)</label>
                  <input
                    type="url"
                    value={portProjUrl}
                    onChange={(e) => setPortProjUrl(e.target.value)}
                    placeholder="https://demo.example.com"
                    className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/50"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-zinc-300">GitHub Havolasi (Ixtiyoriy)</label>
                  <input
                    type="url"
                    value={portGithubUrl}
                    onChange={(e) => setPortGithubUrl(e.target.value)}
                    placeholder="https://github.com/..."
                    className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/50"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium text-zinc-300">Ko&apos;nikmalar (Vergul bilan ajrating)</label>
                <input
                  type="text"
                  value={portSkillsInput}
                  onChange={(e) => setPortSkillsInput(e.target.value)}
                  placeholder="Masalan: Python, FastAPI, Next.js, PostgreSQL"
                  className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/50"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-zinc-300">Boshlanish Sanasi</label>
                  <input
                    type="date"
                    value={portStartDate}
                    onChange={(e) => setPortStartDate(e.target.value)}
                    className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-zinc-300">Yakunlanish Sanasi</label>
                  <input
                    type="date"
                    value={portEndDate}
                    onChange={(e) => setPortEndDate(e.target.value)}
                    className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.06]">
                <button
                  type="button"
                  onClick={() => setIsPortfolioModalOpen(false)}
                  disabled={isSavingPortfolio}
                  className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300 transition-all"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSavingPortfolio}
                  className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-purple-600/20"
                >
                  {isSavingPortfolio ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Save className="w-3.5 h-3.5" />
                  )}
                  <span>{editingPortfolioId ? "Saqlash" : "Qo'shish"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CERTIFICATE MODAL */}
      {isCertModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#121214] border border-white/[0.1] rounded-2xl max-w-lg w-full p-6 shadow-2xl flex flex-col gap-5">
            <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Award className="w-4 h-4 text-yellow-400" />
                <span>Yangi Sertifikat Qo&apos;shish</span>
              </h3>
              <button
                type="button"
                onClick={() => setIsCertModalOpen(false)}
                className="text-zinc-500 hover:text-zinc-300 text-sm"
              >
                ✕
              </button>
            </div>

            {certErrorMsg && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{certErrorMsg}</span>
              </div>
            )}

            <form onSubmit={handleSaveCert} className="flex flex-col gap-3.5">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium text-zinc-300">Sertifikat Nomi *</label>
                <input
                  type="text"
                  value={certTitle}
                  onChange={(e) => setCertTitle(e.target.value)}
                  placeholder="Masalan: AWS Certified Solutions Architect"
                  className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-yellow-500/50"
                  required
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium text-zinc-300">Beruvchi Tashkilot / Muassasa *</label>
                <input
                  type="text"
                  value={certIssuer}
                  onChange={(e) => setCertIssuer(e.target.value)}
                  placeholder="Masalan: Amazon Web Services, Coursera, IELTS"
                  className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-yellow-500/50"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-zinc-300">Berilgan Sana *</label>
                  <input
                    type="date"
                    value={certIssueDate}
                    onChange={(e) => setCertIssueDate(e.target.value)}
                    className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none"
                    required
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-zinc-300">Amal Qilish Muddati (Ixtiyoriy)</label>
                  <input
                    type="date"
                    value={certExpiryDate}
                    onChange={(e) => setCertExpiryDate(e.target.value)}
                    className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-zinc-300">Sertifikat ID / Litsenziya raqami</label>
                  <input
                    type="text"
                    value={certCredId}
                    onChange={(e) => setCertCredId(e.target.value)}
                    placeholder="Masalan: AWS-0098124"
                    className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white font-mono placeholder-zinc-500 focus:outline-none focus:border-yellow-500/50"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-zinc-300">Onlayn Tekshiruv Havolasi</label>
                  <input
                    type="url"
                    value={certCredUrl}
                    onChange={(e) => setCertCredUrl(e.target.value)}
                    placeholder="https://..."
                    className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-yellow-500/50"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-zinc-300">Sertifikat fayli (PDF)</label>
                <div className="flex flex-wrap items-center gap-2">
                  <label className="px-3 py-2 rounded-lg bg-yellow-500/15 hover:bg-yellow-500/25 border border-yellow-500/30 text-yellow-300 text-xs font-semibold cursor-pointer transition-all flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5" />
                    <span>{isUploadingCertPdf ? "Yuklanmoqda..." : "Kompyuterdan PDF tanlash"}</span>
                    <input
                      type="file"
                      accept=".pdf,application/pdf"
                      className="hidden"
                      disabled={isUploadingCertPdf}
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleUploadCertificatePdf(f);
                      }}
                    />
                  </label>
                  <span className="text-[11px] text-zinc-400">
                    Sertifikatning asl PDF nusxasi — antivirus tekshiruvidan o‘tadi.
                  </span>
                </div>
                {uploadedCertFilename && (
                  <span className="text-[11px] font-mono text-emerald-400">
                    ✓ Yuklandi: {uploadedCertFilename}
                  </span>
                )}
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.06]">
                <button
                  type="button"
                  onClick={() => setIsCertModalOpen(false)}
                  disabled={isSavingCert}
                  className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300 transition-all"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSavingCert}
                  className="px-4 py-2 rounded-lg bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-yellow-600/20"
                >
                  {isSavingCert ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Save className="w-3.5 h-3.5" />
                  )}
                  <span>Biriktirish</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* END ENROLLMENT MODAL */}
      {endingEnrollment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#121214] border border-white/[0.1] rounded-2xl max-w-md w-full p-6 shadow-2xl flex flex-col gap-5">
            <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <XCircle className="w-4 h-4 text-rose-400" />
                <span>Talabalikni Yakunlash / Ko&apos;chirish</span>
              </h3>
              <button
                type="button"
                onClick={() => setEndingEnrollment(null)}
                className="text-zinc-500 hover:text-zinc-300 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="p-3 rounded-lg bg-surface border border-white/[0.06] flex flex-col gap-1 text-xs">
              <span className="font-semibold text-white">
                {endingEnrollment.institution_name || `Muassasa: ${endingEnrollment.institution_id.slice(0, 8)}...`}
              </span>
              <span className="text-zinc-400">{endingEnrollment.program}</span>
              <span className="text-zinc-500 font-mono text-[11px]">Boshlangan sana: {endingEnrollment.start_date}</span>
            </div>

            {endErrorMsg && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{endErrorMsg}</span>
              </div>
            )}

            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium text-zinc-300">
                  Yakunlash Sanasi
                </label>
                <input
                  type="date"
                  value={endEffectiveDate}
                  onChange={(e) => setEndEffectiveDate(e.target.value)}
                  className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:outline-none"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium text-zinc-300">
                  Yakunlash Sababi (Kamida 15 ta belgi) *
                </label>
                <textarea
                  rows={3}
                  value={endReason}
                  onChange={(e) => setEndReason(e.target.value)}
                  placeholder="Masalan: O'qishni muvaffaqiyatli tamomlaganligi va diplom olganligi sababli..."
                  className="px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-rose-500/50 resize-y"
                />
                <span className="text-[10px] text-zinc-500 font-mono">
                  Belgilar soni: {endReason.trim().length} / 15
                </span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-white/[0.06]">
              <button
                type="button"
                onClick={() => setEndingEnrollment(null)}
                disabled={isSubmittingEnd}
                className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300 transition-all"
              >
                Bekor qilish
              </button>
              <button
                type="button"
                onClick={handleConfirmEndEnrollment}
                disabled={isSubmittingEnd || endReason.trim().length < 15}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-rose-600/20"
              >
                {isSubmittingEnd ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Check className="w-3.5 h-3.5" />
                )}
                <span>Yakunlashni Tasdiqlash</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {resubmittingEnrollment && (
        <EnrollmentResubmitModal
          key={resubmittingEnrollment.id}
          enrollment={resubmittingEnrollment}
          onClose={() => setResubmittingEnrollment(null)}
          onSaved={() => void loadEnrollmentsData()}
        />
      )}

      {/* AUTH MODAL */}
      <AuthModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        requiredPortal="CANDIDATE"
        title="Talaba / Nomzod kirishi"
        subtitle="Faqat talaba kabineti va funksiyalari uchun hisobingizga kiring"
        onSuccess={(user) => {
          setCurrentUser(user);
          loadProfileData();
          loadCatalog();
          loadAvailabilityData();
          loadEnrollmentsData();
          loadPortfoliosData();
          loadCertificatesData();
        }}
      />
    </main>
  );
}
