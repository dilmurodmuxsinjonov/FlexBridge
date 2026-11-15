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
  Award,
  CheckSquare,
  ExternalLink,
  ShieldAlert,
  FileCheck,
  ShieldCheck,
  UserPlus,
  UserMinus,
  Mail,
  Phone,
  Trash2,
  CreditCard,
  Receipt,
  Coins,
  TrendingUp,
  Sparkles,
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
  fetchMentorReviewQueue,
  fetchWorkplaceRevisionDetail,
  submitWorkplaceReview,
  fetchMentorAssignments,
  fetchOrganizationPlacements,
  fetchOrgCapabilities,
  fetchOrgMemberships,
  inviteOrgMember,
  revokeOrgMembership,
  fetchOrgVerificationStatus,
  fetchOrgEntitlements,
  fetchOrgBillingOverview,
  createOrgOrder,
  requestOrderRefund,
  publishEmployerOpportunity,
  transitionOpportunityStatus,
  AuthUser,
  EmployerDashboardMetrics,
  EmployerOpportunityApplicationItem,
  ApplicationHRDetailResponse,
  MentorReviewQueueItem,
  MentorLogRevisionDetail,
  MentorAssignmentItem,
  OrganizationPlacementItem,
  OrgCapabilityItem,
  OrgMembershipItem,
  OrgVerificationStatusResponse,
  OrgEntitlementsResponse,
  OrgBillingOverviewResponse,
  OrgOrderItem,
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

  // FB-180: Opportunity Lifecycle State (API-081 & API-082)
  const [isPublishingOpp, setIsPublishingOpp] = useState(false);
  const [isTransitioningOpp, setIsTransitioningOpp] = useState(false);
  const [oppLifecycleMsg, setOppLifecycleMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

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

  // -------------------------------------------------------------------------
  // FB-162, FB-168 & FB-174: Workspace Tabs & Hub States
  // -------------------------------------------------------------------------
  const [activeMainTab, setActiveMainTab] = useState<"KANBAN" | "MENTOR_HUB" | "ORG_HUB" | "BILLING_HUB">("KANBAN");
  const [mentorSubTab, setMentorSubTab] = useState<"QUEUE" | "PLACEMENTS">("QUEUE");

  // -------------------------------------------------------------------------
  // FB-174: Billing Overview, Entitlements, Orders & Refunds (API-070, 093, 094, 095)
  // -------------------------------------------------------------------------
  const [entitlements, setEntitlements] = useState<OrgEntitlementsResponse | null>(null);
  const [billingOverview, setBillingOverview] = useState<OrgBillingOverviewResponse | null>(null);
  const [isLoadingBilling, setIsLoadingBilling] = useState(false);
  const [billingError, setBillingError] = useState<string | null>(null);

  // New Subscription Order State (API-094)
  const [selectedPlanCode, setSelectedPlanCode] = useState<"ORG_PLAN_30D" | "SINGLE_POST_30D">("ORG_PLAN_30D");
  const [isOrdering, setIsOrdering] = useState(false);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [orderSuccess, setOrderSuccess] = useState<string | null>(null);

  // Refund Request Modal State (API-095)
  const [refundModalOrder, setRefundModalOrder] = useState<OrgOrderItem | null>(null);
  const [refundAmountUzs, setRefundAmountUzs] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [isSubmittingRefund, setIsSubmittingRefund] = useState(false);
  const [refundError, setRefundError] = useState<string | null>(null);
  const [refundSuccess, setRefundSuccess] = useState<string | null>(null);

  // Review Queue State (API-090)
  const [reviewQueue, setReviewQueue] = useState<MentorReviewQueueItem[]>([]);
  const [isLoadingQueue, setIsLoadingQueue] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);

  // Review Modal State (API-091 & API-092)
  const [reviewModalRevisionId, setReviewModalRevisionId] = useState<string | null>(null);
  const [revisionDetail, setRevisionDetail] = useState<MentorLogRevisionDetail | null>(null);
  const [isLoadingRevisionDetail, setIsLoadingRevisionDetail] = useState(false);
  const [revisionDetailError, setRevisionDetailError] = useState<string | null>(null);
  const [reviewDecision, setReviewDecision] = useState<"APPROVED" | "CHANGES_REQUESTED" | "REJECTED">("APPROVED");
  const [reviewComment, setReviewComment] = useState("");
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [reviewSubmitError, setReviewSubmitError] = useState<string | null>(null);
  const [reviewSubmitSuccess, setReviewSubmitSuccess] = useState<string | null>(null);

  // Placements & Assignments State (API-089 & API-069)
  const [placementsTab, setPlacementsTab] = useState<"MY_MENTEES" | "ORG_PLACEMENTS">("MY_MENTEES");
  const [mentorAssignments, setMentorAssignments] = useState<MentorAssignmentItem[]>([]);
  const [orgPlacements, setOrgPlacements] = useState<OrganizationPlacementItem[]>([]);
  const [isLoadingPlacements, setIsLoadingPlacements] = useState(false);
  const [placementsError, setPlacementsError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // FB-168: Organization Settings, Team Management, Capabilities & Verification (API-072..075, 067)
  // -------------------------------------------------------------------------
  const [orgCapabilities, setOrgCapabilities] = useState<OrgCapabilityItem[]>([]);
  const [isLoadingCapabilities, setIsLoadingCapabilities] = useState(false);
  const [capabilitiesError, setCapabilitiesError] = useState<string | null>(null);

  const [orgMemberships, setOrgMemberships] = useState<OrgMembershipItem[]>([]);
  const [isLoadingMemberships, setIsLoadingMemberships] = useState(false);
  const [membershipsError, setMembershipsError] = useState<string | null>(null);

  const [orgVerification, setOrgVerification] = useState<OrgVerificationStatusResponse | null>(null);
  const [isLoadingVerification, setIsLoadingVerification] = useState(false);
  const [verificationError, setVerificationError] = useState<string | null>(null);

  // Invite Member Form State (API-074)
  const [inviteChannel, setInviteChannel] = useState<"EMAIL" | "PHONE">("EMAIL");
  const [inviteDestination, setInviteDestination] = useState("");
  const [inviteRoleCode, setInviteRoleCode] = useState<"HR" | "HOST_COORDINATOR" | "MENTOR" | "BILLING">("HR");
  const [isSubmittingInvite, setIsSubmittingInvite] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null);

  // Revoke Member Modal State (API-075)
  const [revokeModalMembership, setRevokeModalMembership] = useState<OrgMembershipItem | null>(null);
  const [revokeReason, setRevokeReason] = useState("");
  const [isSubmittingRevoke, setIsSubmittingRevoke] = useState(false);
  const [revokeError, setRevokeError] = useState<string | null>(null);
  const [revokeSuccess, setRevokeSuccess] = useState<string | null>(null);

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

  // FB-180: Publish Opportunity (API-081)
  const handlePublishOpportunity = async (oppId: string) => {
    if (!oppId.trim()) return;
    setIsPublishingOpp(true);
    setOppLifecycleMsg(null);
    try {
      const res = await publishEmployerOpportunity(oppId.trim());
      setOppLifecycleMsg({
        type: "success",
        text: `Vakansiya (${oppId.slice(0, 8)}...) muvaffaqiyatli nashr qilindi (API-081)! Holat: ${res.status || 'PUBLISHED'}`,
      });
      if (orgId.trim()) {
        loadDashboard(orgId.trim());
      }
    } catch (err: unknown) {
      setOppLifecycleMsg({
        type: "error",
        text: err instanceof Error ? err.message : "Vakansiyani nashr qilishda xatolik yuz berdi",
      });
    } finally {
      setIsPublishingOpp(false);
    }
  };

  // FB-180: Transition Opportunity Status (API-082)
  const handleTransitionOpportunity = async (oppId: string, status: "PAUSED" | "CLOSED") => {
    if (!oppId.trim()) return;
    setIsTransitioningOpp(true);
    setOppLifecycleMsg(null);
    try {
      await transitionOpportunityStatus(oppId.trim(), status);
      setOppLifecycleMsg({
        type: "success",
        text: `Vakansiya holati '${status}' ga muvaffaqiyatli o'zgartirildi (API-082)!`,
      });
      if (orgId.trim()) {
        loadDashboard(orgId.trim());
      }
    } catch (err: unknown) {
      setOppLifecycleMsg({
        type: "error",
        text: err instanceof Error ? err.message : "Vakansiya holatini o'zgartirishda xatolik",
      });
    } finally {
      setIsTransitioningOpp(false);
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

  // -------------------------------------------------------------------------
  // FB-162: Mentor Callbacks & Handlers (API-090..092, 089, 069)
  // -------------------------------------------------------------------------
  const loadMentorQueue = useCallback(async () => {
    setIsLoadingQueue(true);
    setQueueError(null);
    try {
      const res = await fetchMentorReviewQueue(50);
      setReviewQueue(res.items || []);
    } catch (err: unknown) {
      setQueueError(err instanceof Error ? err.message : "Kundaliklar navbatini yuklashda xatolik.");
      setReviewQueue([]);
    } finally {
      setIsLoadingQueue(false);
    }
  }, []);

  const loadPlacements = useCallback(async () => {
    setIsLoadingPlacements(true);
    setPlacementsError(null);
    try {
      const [assignments, placements] = await Promise.all([
        fetchMentorAssignments(50).catch(() => []),
        orgId.trim() ? fetchOrganizationPlacements(orgId.trim(), 50).catch(() => []) : Promise.resolve([]),
      ]);
      setMentorAssignments(assignments);
      setOrgPlacements(placements);
    } catch (err: unknown) {
      setPlacementsError(err instanceof Error ? err.message : "Amaliyotchilar ro'yxatini yuklashda xatolik.");
    } finally {
      setIsLoadingPlacements(false);
    }
  }, [orgId]);

  const handleOpenReviewModal = async (revisionId: string) => {
    setReviewModalRevisionId(revisionId);
    setIsLoadingRevisionDetail(true);
    setRevisionDetailError(null);
    setRevisionDetail(null);
    setReviewDecision("APPROVED");
    setReviewComment("");
    setReviewSubmitError(null);
    setReviewSubmitSuccess(null);

    try {
      const detail = await fetchWorkplaceRevisionDetail(revisionId);
      setRevisionDetail(detail);
      if (detail.existing_review?.decision) {
        setReviewDecision(detail.existing_review.decision as "APPROVED" | "CHANGES_REQUESTED" | "REJECTED");
        setReviewComment(detail.existing_review.comment || "");
      }
    } catch (err: unknown) {
      setRevisionDetailError(err instanceof Error ? err.message : "Kundalik tafsilotlarini yuklashda xatolik.");
    } finally {
      setIsLoadingRevisionDetail(false);
    }
  };

  const handleSubmitReviewDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewModalRevisionId) return;
    setIsSubmittingReview(true);
    setReviewSubmitError(null);
    setReviewSubmitSuccess(null);

    try {
      await submitWorkplaceReview(reviewModalRevisionId, {
        decision: reviewDecision,
        comment: reviewComment.trim() || undefined,
      });
      setReviewSubmitSuccess("Kundalik muvaffaqiyatli baholandi va holati yangilandi!");
      await loadMentorQueue();
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      const msg = err instanceof Error ? err.message : "Bahoni saqlashda xatolik.";
      if (status === 403 || msg.includes("SELF_REVIEW_FORBIDDEN")) {
        setReviewSubmitError("O‘zingizning kundaligingizni baholash taqiqlanadi (Anti-self review xavfsizlik qoidasi).");
      } else {
        setReviewSubmitError(msg);
      }
    } finally {
      setIsSubmittingReview(false);
    }
  };

  // -------------------------------------------------------------------------
  // FB-168: Org Hub Data Loaders & Action Handlers (API-072..075, 067)
  // -------------------------------------------------------------------------
  const loadOrgHubData = useCallback(async (targetOrgId: string) => {
    if (!targetOrgId.trim()) return;
    const tid = targetOrgId.trim();

    setIsLoadingCapabilities(true);
    setCapabilitiesError(null);
    setIsLoadingMemberships(true);
    setMembershipsError(null);
    setIsLoadingVerification(true);
    setVerificationError(null);

    try {
      const caps = await fetchOrgCapabilities(tid);
      setOrgCapabilities(caps.items || []);
    } catch (err: unknown) {
      setCapabilitiesError(err instanceof Error ? err.message : "Imkoniyatlarni yuklashda xatolik.");
      setOrgCapabilities([]);
    } finally {
      setIsLoadingCapabilities(false);
    }

    try {
      const mems = await fetchOrgMemberships(tid);
      setOrgMemberships(mems.items || []);
    } catch (err: unknown) {
      setMembershipsError(err instanceof Error ? err.message : "Jamoa a'zolarini yuklashda xatolik.");
      setOrgMemberships([]);
    } finally {
      setIsLoadingMemberships(false);
    }

    try {
      const verif = await fetchOrgVerificationStatus(tid);
      setOrgVerification(verif);
    } catch (err: unknown) {
      setVerificationError(err instanceof Error ? err.message : "Verifikatsiya holatini yuklashda xatolik.");
      setOrgVerification(null);
    } finally {
      setIsLoadingVerification(false);
    }
  }, []);

  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgId.trim()) {
      setInviteError("Tashkilot ID tanlanmagan.");
      return;
    }
    if (!inviteDestination.trim()) {
      setInviteError("Email yoki telefon raqami kiritilishi shart.");
      return;
    }
    setIsSubmittingInvite(true);
    setInviteError(null);
    setInviteSuccess(null);

    try {
      await inviteOrgMember(orgId.trim(), {
        channel: inviteChannel,
        destination: inviteDestination.trim(),
        role_code: inviteRoleCode,
      });
      setInviteSuccess(`${inviteDestination.trim()} manziliga 24 soatlik taklifnoma muvaffaqiyatli yuborildi!`);
      setInviteDestination("");
      // reload memberships
      const mems = await fetchOrgMemberships(orgId.trim());
      setOrgMemberships(mems.items || []);
    } catch (err: unknown) {
      setInviteError(err instanceof Error ? err.message : "Taklifnoma yuborishda xatolik yuz berdi.");
    } finally {
      setIsSubmittingInvite(false);
    }
  };

  const handleRevokeMembership = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!revokeModalMembership || !orgId.trim()) return;
    if (revokeReason.trim().length < 15) {
      setRevokeError("Bekor qilish sababi kamida 15 ta belgidan iborat bo‘lishi shart (API-075 qat'iy talabi).");
      return;
    }

    setIsSubmittingRevoke(true);
    setRevokeError(null);
    setRevokeSuccess(null);

    try {
      await revokeOrgMembership(orgId.trim(), revokeModalMembership.id, {
        reason: revokeReason.trim(),
      });
      setRevokeSuccess("A'zolik muvaffaqiyatli bekor qilindi.");
      setRevokeReason("");
      setRevokeModalMembership(null);
      // reload memberships
      const mems = await fetchOrgMemberships(orgId.trim());
      setOrgMemberships(mems.items || []);
    } catch (err: unknown) {
      setRevokeError(err instanceof Error ? err.message : "A'zolikni bekor qilishda xatolik yuz berdi.");
    } finally {
      setIsSubmittingRevoke(false);
    }
  };

  // -------------------------------------------------------------------------
  // FB-174: Billing Hub Data Loaders & Action Handlers (API-070, 093, 094, 095)
  // -------------------------------------------------------------------------
  const loadBillingHubData = useCallback(async (targetOrgId: string) => {
    if (!targetOrgId.trim()) return;
    const tid = targetOrgId.trim();

    setIsLoadingBilling(true);
    setBillingError(null);

    try {
      const [entData, billData] = await Promise.all([
        fetchOrgEntitlements(tid),
        fetchOrgBillingOverview(tid),
      ]);
      setEntitlements(entData);
      setBillingOverview(billData);
    } catch (err: unknown) {
      setBillingError(err instanceof Error ? err.message : "To‘lov va kvota ma'lumotlarini yuklashda xatolik yuz berdi.");
    } finally {
      setIsLoadingBilling(false);
    }
  }, []);

  const handleCreateOrder = async (planCode: "ORG_PLAN_30D" | "SINGLE_POST_30D") => {
    if (!orgId.trim()) {
      setOrderError("Tashkilot ID tanlanmagan.");
      return;
    }
    setIsOrdering(true);
    setOrderError(null);
    setOrderSuccess(null);

    try {
      const res = await createOrgOrder(orgId.trim(), {
        plan_code: planCode,
        idempotency_key: `ord_${crypto.randomUUID()}`,
      });
      setOrderSuccess(`Buyurtma #${res.order.id.slice(0, 8)} muvaffaqiyatli yaratildi. Summa: ${res.order.amount.toLocaleString()} UZS.`);
      await loadBillingHubData(orgId.trim());
    } catch (err: unknown) {
      setOrderError(err instanceof Error ? err.message : "Buyurtma berishda xatolik yuz berdi.");
    } finally {
      setIsOrdering(false);
    }
  };

  const handleRequestRefund = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!refundModalOrder) return;
    const amt = Number(refundAmountUzs);
    if (!amt || isNaN(amt) || amt <= 0) {
      setRefundError("Qaytarish summasi 0 dan katta bo‘lishi shart.");
      return;
    }
    if (refundReason.trim().length < 15) {
      setRefundError("Qaytarish sababi kamida 15 ta belgidan iborat bo‘lishi shart (API-095 talabi).");
      return;
    }

    setIsSubmittingRefund(true);
    setRefundError(null);
    setRefundSuccess(null);

    try {
      const res = await requestOrderRefund(refundModalOrder.id, {
        amount_uzs: Math.round(amt),
        reason: refundReason.trim(),
      });
      setRefundSuccess(`Qaytarish so‘rovi #${res.refund_id.slice(0, 8)} muvaffaqiyatli qabul qilindi.`);
      await loadBillingHubData(orgId.trim());
      setTimeout(() => {
        setRefundModalOrder(null);
        setRefundAmountUzs("");
        setRefundReason("");
        setRefundSuccess(null);
      }, 2000);
    } catch (err: unknown) {
      setRefundError(err instanceof Error ? err.message : "Qaytarish so‘rovini yuborishda xatolik yuz berdi.");
    } finally {
      setIsSubmittingRefund(false);
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

          {/* PRIMARY WORKSPACE TABS */}
          <div className="flex items-center gap-2 border-b border-white/[0.08] pb-3">
            <button
              type="button"
              onClick={() => setActiveMainTab("KANBAN")}
              className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
                activeMainTab === "KANBAN"
                  ? "bg-primary text-white shadow-md shadow-primary/20"
                  : "bg-surface-card hover:bg-surface border border-white/[0.08] text-zinc-400 hover:text-white"
              }`}
            >
              <Users className="w-4 h-4" />
              <span>Nomzodlar Kanbani & Suhbatlar</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveMainTab("MENTOR_HUB");
                if (reviewQueue.length === 0 && !isLoadingQueue) {
                  loadMentorQueue();
                }
                if (mentorAssignments.length === 0 && !isLoadingPlacements) {
                  loadPlacements();
                }
              }}
              className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
                activeMainTab === "MENTOR_HUB"
                  ? "bg-primary text-white shadow-md shadow-primary/20"
                  : "bg-surface-card hover:bg-surface border border-white/[0.08] text-zinc-400 hover:text-white"
              }`}
            >
              <Award className="w-4 h-4" />
              <span>Mentorlik & Amaliyot Kundaliklari</span>
              {reviewQueue.filter((q) => q.is_escalated).length > 0 && (
                <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500 text-white animate-pulse">
                  {reviewQueue.filter((q) => q.is_escalated).length}
                </span>
              )}
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveMainTab("ORG_HUB");
                if (orgId.trim()) {
                  loadOrgHubData(orgId.trim());
                }
              }}
              className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
                activeMainTab === "ORG_HUB"
                  ? "bg-primary text-white shadow-md shadow-primary/20"
                  : "bg-surface-card hover:bg-surface border border-white/[0.08] text-zinc-400 hover:text-white"
              }`}
            >
              <Building className="w-4 h-4" />
              <span>Tashkilot & Jamoa Boshqaruvi</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveMainTab("BILLING_HUB");
                if (orgId.trim()) {
                  loadBillingHubData(orgId.trim());
                }
              }}
              className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
                activeMainTab === "BILLING_HUB"
                  ? "bg-primary text-white shadow-md shadow-primary/20"
                  : "bg-surface-card hover:bg-surface border border-white/[0.08] text-zinc-400 hover:text-white"
              }`}
            >
              <CreditCard className="w-4 h-4" />
              <span>To‘lovlar, Tariflar & Kvotalar</span>
            </button>
          </div>

          {/* ----------------------------------------------------------------- */}
          {/* FB-150: NOMZODLAR BOSQICHLARI VA KANBAN BOSHQARUVI */}
          {/* ----------------------------------------------------------------- */}
          {activeMainTab === "KANBAN" && (
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

                {/* FB-180: Lifecycle Action Buttons */}
                <button
                  type="button"
                  disabled={isPublishingOpp || !targetOppId.trim()}
                  onClick={() => handlePublishOpportunity(targetOppId)}
                  title="Qoralama vakansiyani nashr qilish (API-081)"
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed shadow"
                >
                  {isPublishingOpp ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                  <span>Nashr qilish</span>
                </button>

                <button
                  type="button"
                  disabled={isTransitioningOpp || !targetOppId.trim()}
                  onClick={() => handleTransitionOpportunity(targetOppId, "PAUSED")}
                  title="Vakansiyani vaqtincha to'xtatish (API-082)"
                  className="px-3 py-1.5 rounded-lg bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 text-xs font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span>To'xtatish</span>
                </button>

                <button
                  type="button"
                  disabled={isTransitioningOpp || !targetOppId.trim()}
                  onClick={() => handleTransitionOpportunity(targetOppId, "CLOSED")}
                  title="Vakansiyani yopish (API-082)"
                  className="px-3 py-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 text-xs font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span>Yopish</span>
                </button>
              </div>
            </div>

            {/* Opportunity Lifecycle feedback message */}
            {oppLifecycleMsg && (
              <div
                className={`p-3 rounded-lg text-xs flex items-center justify-between gap-2 border ${
                  oppLifecycleMsg.type === "success"
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
                    : "bg-rose-500/10 border-rose-500/20 text-rose-300"
                }`}
              >
                <div className="flex items-center gap-2">
                  {oppLifecycleMsg.type === "success" ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  )}
                  <span>{oppLifecycleMsg.text}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setOppLifecycleMsg(null)}
                  className="text-zinc-400 hover:text-white text-xs font-bold p-1"
                >
                  ✕
                </button>
              </div>
            )}

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
          )}

          {/* ----------------------------------------------------------------- */}
          {/* FB-162: WORKPLACE MENTOR HUB & INTERN EVALUATIONS (API-090..092) */}
          {/* ----------------------------------------------------------------- */}
          {activeMainTab === "MENTOR_HUB" && (
            <section className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-5 flex flex-col gap-5 shadow-lg">
              {/* Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      Workplace Mentor Hub
                    </span>
                    <span className="text-zinc-500 text-xs">• API-090, API-091, API-092, API-089, API-069</span>
                  </div>
                  <h2 className="font-heading text-base md:text-lg font-bold text-white">
                    Amaliyot Kundaliklarini Baholash va Mentorlik Boshqaruvi
                  </h2>
                  <p className="text-xs text-zinc-400">
                    Amaliyotchi talabalarning kunlik topshiriqlarini tekshirish, tasdiqlash yoki tuzatish talab qilish hamda biriktirilgan amaliyotchilarni kuzatish.
                  </p>
                </div>

                {/* Sub-tab navigation */}
                <div className="flex items-center gap-2 bg-surface p-1 rounded-xl border border-white/[0.08]">
                  <button
                    type="button"
                    onClick={() => {
                      setMentorSubTab("QUEUE");
                      loadMentorQueue();
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                      mentorSubTab === "QUEUE"
                        ? "bg-primary text-white shadow"
                        : "text-zinc-400 hover:text-white"
                    }`}
                  >
                    <Clock className="w-3.5 h-3.5" />
                    <span>Kundaliklar Navbati</span>
                    {reviewQueue.length > 0 && (
                      <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-white/20 text-white font-mono">
                        {reviewQueue.length}
                      </span>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMentorSubTab("PLACEMENTS");
                      loadPlacements();
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                      mentorSubTab === "PLACEMENTS"
                        ? "bg-primary text-white shadow"
                        : "text-zinc-400 hover:text-white"
                    }`}
                  >
                    <GraduationCap className="w-3.5 h-3.5" />
                    <span>Amaliyotchilar</span>
                  </button>
                </div>
              </div>

              {/* Sub-tab 1: QUEUE (API-090) */}
              {mentorSubTab === "QUEUE" && (
                <div className="flex flex-col gap-4">
                  {/* Urgent escalation warning if any */}
                  {reviewQueue.some((q) => q.is_escalated) && (
                    <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-3">
                      <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0" />
                      <div className="flex flex-col">
                        <span className="font-bold text-rose-200">
                          Diqqat: Muddati o&apos;tgan (Escalated) kundaliklar mavjud!
                        </span>
                        <span className="text-[11px] text-rose-300/80">
                          Ushbu kundaliklar 3 kunlik muddatdan oshgan. Iltimos, ularni birinchi navbatda ko&apos;rib chiqing.
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Queue error message */}
                  {queueError && (
                    <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <span>{queueError}</span>
                    </div>
                  )}

                  {/* Loading or Content */}
                  {isLoadingQueue ? (
                    <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400 text-xs">
                      <Loader2 className="w-6 h-6 animate-spin text-primary" />
                      <span>Tekshiruv navbati yuklanmoqda...</span>
                    </div>
                  ) : reviewQueue.length === 0 ? (
                    <div className="py-12 text-center text-zinc-400 text-xs flex flex-col items-center justify-center gap-3 border border-dashed border-white/[0.08] rounded-xl">
                      <CheckCircle2 className="w-8 h-8 text-emerald-400/60" />
                      <div className="flex flex-col gap-1">
                        <span className="font-semibold text-zinc-200">Navbat bo&apos;sh!</span>
                        <span>Hozircha tekshiruvni kutayotgan amaliyot kundaliklari mavjud emas.</span>
                      </div>
                      <button
                        type="button"
                        onClick={loadMentorQueue}
                        className="mt-2 px-3 py-1.5 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300 flex items-center gap-1.5"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>Yangilash</span>
                      </button>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center justify-between text-xs text-zinc-400 px-1">
                        <span>Jami navbatda: <strong className="text-white font-mono">{reviewQueue.length}</strong> ta topshiriq</span>
                        <button
                          type="button"
                          onClick={loadMentorQueue}
                          className="px-2.5 py-1 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs text-zinc-300 flex items-center gap-1"
                        >
                          <RefreshCw className="w-3 h-3" />
                          <span>Yangilash</span>
                        </button>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {reviewQueue.map((item) => (
                          <div
                            key={item.revision_id}
                            className={`p-4 rounded-xl border flex flex-col justify-between gap-3 transition-all ${
                              item.is_escalated
                                ? "bg-rose-500/[0.03] border-rose-500/30 hover:border-rose-500/50"
                                : "bg-surface border-white/[0.08] hover:border-white/[0.15]"
                            }`}
                          >
                            <div className="flex flex-col gap-2">
                              {/* Header & badges */}
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex flex-col">
                                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                                    <GraduationCap className="w-3.5 h-3.5 text-primary" />
                                    {item.candidate?.full_name || "Amaliyotchi talaba"}
                                  </span>
                                  {item.candidate?.headline && (
                                    <span className="text-[11px] text-zinc-400 line-clamp-1">
                                      {item.candidate.headline}
                                    </span>
                                  )}
                                </div>
                                {item.is_escalated ? (
                                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 shrink-0">
                                    ESCALATED
                                  </span>
                                ) : (
                                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">
                                    Kutilmoqda
                                  </span>
                                )}
                              </div>

                              {/* Details */}
                              <div className="grid grid-cols-2 gap-2 text-xs py-2 border-y border-white/[0.04]">
                                <div>
                                  <span className="text-zinc-500 text-[10px] block">Sana:</span>
                                  <span className="font-mono text-zinc-200">
                                    {item.log_date || "—"} ({item.day_type})
                                  </span>
                                </div>
                                <div>
                                  <span className="text-zinc-500 text-[10px] block">Bajarilgan vaqt:</span>
                                  <span className="font-mono text-emerald-400 font-semibold">
                                    {item.total_minutes} daqiqa ({(item.total_minutes / 60).toFixed(1)} soat)
                                  </span>
                                </div>
                              </div>

                              {/* Summary */}
                              <p className="text-xs text-zinc-300 line-clamp-2 bg-surface-lowest p-2 rounded-lg border border-white/[0.04]">
                                {item.summary || "Bajarilgan vazifalar tavsifi ko‘rsatilmagan."}
                              </p>

                              {/* Deadline */}
                              {item.due_at && (
                                <div className="text-[11px] text-zinc-500 flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  <span>Muddati: {new Date(item.due_at).toLocaleDateString()}</span>
                                </div>
                              )}
                            </div>

                            {/* Action */}
                            <button
                              type="button"
                              onClick={() => handleOpenReviewModal(item.revision_id)}
                              className="w-full mt-1 py-2 px-3 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center justify-center gap-1.5 shadow"
                            >
                              <FileCheck className="w-3.5 h-3.5" />
                              <span>Baholash va Tekshirish</span>
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Sub-tab 2: PLACEMENTS (API-089 & API-069) */}
              {mentorSubTab === "PLACEMENTS" && (
                <div className="flex flex-col gap-4">
                  {/* Selector between My Mentees and All Org Placements */}
                  <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setPlacementsTab("MY_MENTEES")}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                          placementsTab === "MY_MENTEES"
                            ? "bg-surface-high text-white border border-white/[0.1]"
                            : "text-zinc-400 hover:text-white"
                        }`}
                      >
                        Menga biriktirilganlar (API-089)
                      </button>
                      <button
                        type="button"
                        onClick={() => setPlacementsTab("ORG_PLACEMENTS")}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                          placementsTab === "ORG_PLACEMENTS"
                            ? "bg-surface-high text-white border border-white/[0.1]"
                            : "text-zinc-400 hover:text-white"
                        }`}
                      >
                        Tashkilot amaliyotlari (API-069)
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={loadPlacements}
                      className="px-2.5 py-1 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs text-zinc-300 flex items-center gap-1"
                    >
                      <RefreshCw className="w-3 h-3" />
                      <span>Yangilash</span>
                    </button>
                  </div>

                  {placementsError && (
                    <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                      {placementsError}
                    </div>
                  )}

                  {isLoadingPlacements ? (
                    <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400 text-xs">
                      <Loader2 className="w-6 h-6 animate-spin text-primary" />
                      <span>Amaliyot ma&apos;lumotlari yuklanmoqda...</span>
                    </div>
                  ) : placementsTab === "MY_MENTEES" ? (
                    mentorAssignments.length === 0 ? (
                      <div className="py-8 text-center text-zinc-400 text-xs border border-dashed border-white/[0.08] rounded-xl">
                        Sizga biriktirilgan faol amaliyotchi talabalar topilmadi.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {mentorAssignments.map((asg) => (
                          <div
                            key={asg.id}
                            className="p-4 rounded-xl bg-surface border border-white/[0.08] flex flex-col gap-2"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-semibold text-white">Amaliyot #{asg.placement_id.slice(0, 8)}</span>
                              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                {asg.revoked_at ? "Tugallangan" : asg.accepted_at ? "Faol Mentorlik" : "Kutilmoqda"}
                              </span>
                            </div>
                            <div className="text-xs text-zinc-400 flex flex-col gap-1 mt-1">
                              <div>Biriktirilgan: <span className="font-mono text-zinc-300">{new Date(asg.assigned_at).toLocaleDateString()}</span></div>
                              {asg.accepted_at && (
                                <div>Qabul qilingan: <span className="font-mono text-zinc-300">{new Date(asg.accepted_at).toLocaleDateString()}</span></div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )
                  ) : (
                    orgPlacements.length === 0 ? (
                      <div className="py-8 text-center text-zinc-400 text-xs border border-dashed border-white/[0.08] rounded-xl">
                        Tashkilot bo&apos;yicha amaliyotlar topilmadi. Yuqorida to&apos;g&apos;ri Tashkilot ID tanlanganligini tekshiring.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {orgPlacements.map((plc) => (
                          <div
                            key={plc.id}
                            className="p-4 rounded-xl bg-surface border border-white/[0.08] flex flex-col gap-2"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-semibold text-white font-mono">#{plc.id.slice(0, 8)}</span>
                              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                                {plc.status}
                              </span>
                            </div>
                            <div className="text-xs text-zinc-400 flex flex-col gap-1 mt-1">
                              <div>Nomzod ID: <span className="font-mono text-zinc-300">#{plc.candidate_id.slice(0, 8)}...</span></div>
                              <div>Davomiyligi: <span className="font-mono text-zinc-300">{plc.start_date} ~ {plc.end_date}</span></div>
                              <div>Akademik trek: <span className="font-semibold text-zinc-200">{plc.academic_track ? "Mavjud (Dual ta'lim)" : "Yo'q"}</span></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )
                  )}
                </div>
              )}
            </section>
          )}

          {/* ----------------------------------------------------------------- */}
          {/* FB-168: TASHKILOT SOZLAMALARI VA JAMOA BOSHQARUVI (API-072..075, 067) */}
          {/* ----------------------------------------------------------------- */}
          {activeMainTab === "ORG_HUB" && (
            <section className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-5 flex flex-col gap-6 shadow-lg">
              {/* Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Tashkilot & Jamoa Hub
                    </span>
                    <span className="text-zinc-500 text-xs font-mono">• API-072, API-073, API-074, API-075, API-067</span>
                  </div>
                  <h2 className="font-heading text-base md:text-lg font-bold text-white">
                    Tashkilot Huquqlari, Verifikatsiya va Jamoa Boshqaruvi
                  </h2>
                  <p className="text-xs text-zinc-400">
                    Tashkilot faoliyat imkoniyatlari (Capabilities), davlat tekshiruvi holati, a&apos;zolar ro&apos;yxati va 24 soatlik taklifnomalar yuborish.
                  </p>
                </div>

                <button
                  type="button"
                  disabled={isLoadingCapabilities || isLoadingMemberships || !orgId.trim()}
                  onClick={() => loadOrgHubData(orgId.trim())}
                  className="px-3 py-1.5 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300 hover:text-white transition-all flex items-center gap-1.5 disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingCapabilities || isLoadingMemberships ? "animate-spin" : ""}`} />
                  <span>Yangilash</span>
                </button>
              </div>

              {/* CARD 1: Organization Capabilities & Verification Status (API-072 & API-067) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Capabilities Card */}
                <div className="p-4 rounded-xl bg-surface border border-white/[0.08] flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                        Faoliyat Imkoniyatlari (Capabilities)
                      </h3>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-500">API-072</span>
                  </div>

                  {isLoadingCapabilities ? (
                    <div className="py-6 flex items-center justify-center text-zinc-400 gap-2 text-xs">
                      <Loader2 className="w-4 h-4 animate-spin text-primary" />
                      <span>Imkoniyatlar yuklanmoqda...</span>
                    </div>
                  ) : capabilitiesError ? (
                    <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                      {capabilitiesError}
                    </div>
                  ) : orgCapabilities.length === 0 ? (
                    <div className="p-4 rounded-lg bg-surface-lowest text-center text-zinc-400 text-xs">
                      Tashkilot uchun biriktirilgan faol huquqlar topilmadi.
                    </div>
                  ) : (
                    <div className="flex flex-col gap-2">
                      {orgCapabilities.map((cap) => (
                        <div
                          key={cap.id || cap.capability}
                          className="p-3 rounded-lg bg-surface-lowest border border-white/[0.04] flex items-center justify-between"
                        >
                          <div className="flex flex-col gap-0.5">
                            <span className="text-xs font-bold text-white font-mono">{cap.capability}</span>
                            <span className="text-[11px] text-zinc-400">
                              {cap.created_at ? `Berilgan: ${new Date(cap.created_at).toLocaleDateString()}` : "Faoliyat huquqi"}
                            </span>
                          </div>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                            cap.status === "ACTIVE" || cap.status === "VERIFIED"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                          }`}>
                            {cap.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Verification Status Card */}
                <div className="p-4 rounded-xl bg-surface border border-white/[0.08] flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Building className="w-4 h-4 text-primary" />
                      <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                        Tashkilot Verifikatsiyasi (STIR / Soliq)
                      </h3>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-500">API-067</span>
                  </div>

                  {isLoadingVerification ? (
                    <div className="py-6 flex items-center justify-center text-zinc-400 gap-2 text-xs">
                      <Loader2 className="w-4 h-4 animate-spin text-primary" />
                      <span>Verifikatsiya ma&apos;lumotlari yuklanmoqda...</span>
                    </div>
                  ) : verificationError ? (
                    <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                      {verificationError}
                    </div>
                  ) : orgVerification ? (
                    <div className="flex flex-col gap-2.5">
                      <div className="p-3 rounded-lg bg-surface-lowest border border-white/[0.04] flex items-center justify-between">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-[11px] text-zinc-400">A&apos;zolik / Tashkilot holati:</span>
                          <span className="text-xs font-bold text-white font-mono">
                            {orgVerification.membership_status || orgVerification.status || "VERIFIED"}
                          </span>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                          (orgVerification.membership_status || orgVerification.status) === "ACTIVE" || (orgVerification.membership_status || orgVerification.status) === "VERIFIED"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : (orgVerification.membership_status || orgVerification.status) === "PENDING" || (orgVerification.membership_status || orgVerification.status) === "PENDING_APPROVAL"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                        }`}>
                          {orgVerification.membership_status || orgVerification.status || "VERIFIED"}
                        </span>
                      </div>

                      {orgVerification.cases && orgVerification.cases.length > 0 && (
                        <div className="flex flex-col gap-1.5 mt-1">
                          <span className="text-[11px] font-semibold text-zinc-400">Tekshiruv tarixi:</span>
                          <div className="max-h-28 overflow-y-auto space-y-1.5 pr-1">
                            {orgVerification.cases.map((c) => (
                              <div
                                key={c.id}
                                className="p-2 rounded bg-surface-lowest/60 border border-white/[0.04] text-[11px] flex items-center justify-between"
                              >
                                <span className="font-mono text-zinc-300">{c.kind}</span>
                                <span className="text-zinc-500 font-mono">
                                  {c.created_at ? new Date(c.created_at).toLocaleDateString() : ""}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-4 rounded-lg bg-surface-lowest text-center text-zinc-400 text-xs">
                      Verifikatsiya holati topilmadi.
                    </div>
                  )}
                </div>
              </div>

              {/* SECTION 2: TEAM MEMBERS & INVITE FORM (API-073 & API-074) */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Team Members List (2 Columns on Desktop) */}
                <div className="lg:col-span-2 flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4 text-primary" />
                      <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                        Jamoa A&apos;zolari va Rollar ({orgMemberships.length})
                      </h3>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-500">API-073</span>
                  </div>

                  {membershipsError && (
                    <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                      {membershipsError}
                    </div>
                  )}

                  {revokeSuccess && (
                    <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>{revokeSuccess}</span>
                    </div>
                  )}

                  {isLoadingMemberships ? (
                    <div className="py-12 flex items-center justify-center text-zinc-400 gap-2 text-xs">
                      <Loader2 className="w-4 h-4 animate-spin text-primary" />
                      <span>Jamoa a&apos;zolari yuklanmoqda...</span>
                    </div>
                  ) : orgMemberships.length === 0 ? (
                    <div className="p-8 rounded-xl bg-surface border border-white/[0.08] text-center text-zinc-400 text-xs flex flex-col items-center gap-2">
                      <Users className="w-8 h-8 text-zinc-600" />
                      <span>Ushbu tashkilotda biriktirilgan a&apos;zolar mavjud emas.</span>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-2.5">
                      {orgMemberships.map((mem) => {
                        const isOwner = mem.role === "OWNER";
                        const isRevoked = mem.status === "REVOKED";

                        return (
                          <div
                            key={mem.id}
                            className="p-3.5 rounded-xl bg-surface border border-white/[0.08] hover:border-white/[0.15] transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                          >
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-bold text-xs uppercase">
                                {mem.user_id.slice(0, 2)}
                              </div>
                              <div className="flex flex-col gap-0.5">
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-semibold text-white">
                                    Foydalanuvchi #{mem.user_id.slice(0, 8)}
                                  </span>
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                                    isOwner
                                      ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                                      : mem.role === "HR"
                                      ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
                                      : mem.role === "MENTOR"
                                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                      : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                                  }`}>
                                    {mem.role}
                                  </span>
                                </div>
                                <span className="text-[11px] text-zinc-500 font-mono">
                                  Qo&apos;shilgan: {mem.created_at ? new Date(mem.created_at).toLocaleDateString() : (mem.accepted_at ? new Date(mem.accepted_at).toLocaleDateString() : "Yaqinda")}
                                </span>
                              </div>
                            </div>

                            <div className="flex items-center gap-2 self-end sm:self-center">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                mem.status === "ACTIVE"
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                  : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                              }`}>
                                {mem.status}
                              </span>

                              {!isOwner && !isRevoked && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setRevokeModalMembership(mem);
                                    setRevokeReason("");
                                    setRevokeError(null);
                                    setRevokeSuccess(null);
                                  }}
                                  className="px-2.5 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-[11px] font-semibold text-rose-300 hover:text-rose-200 transition-all flex items-center gap-1"
                                >
                                  <UserMinus className="w-3 h-3" />
                                  <span>Bekor qilish</span>
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Send Invitation Form (1 Column on Desktop) */}
                <div className="p-4 rounded-xl bg-surface border border-white/[0.08] flex flex-col gap-4">
                  <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                    <div className="flex items-center gap-2">
                      <UserPlus className="w-4 h-4 text-emerald-400" />
                      <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                        Yangi A&apos;zo Taklif Qilish
                      </h3>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-500">API-074</span>
                  </div>

                  <form onSubmit={handleInviteMember} className="flex flex-col gap-3">
                    {inviteSuccess && (
                      <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs">
                        {inviteSuccess}
                      </div>
                    )}

                    {inviteError && (
                      <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                        {inviteError}
                      </div>
                    )}

                    {/* Channel Selector */}
                    <div className="flex flex-col gap-1">
                      <label className="text-[11px] font-semibold text-zinc-300">
                        Yuborish kanali:
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          type="button"
                          onClick={() => setInviteChannel("EMAIL")}
                          className={`py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 border transition-all ${
                            inviteChannel === "EMAIL"
                              ? "bg-primary text-white border-primary"
                              : "bg-surface-lowest text-zinc-400 border-white/[0.08] hover:text-white"
                          }`}
                        >
                          <Mail className="w-3 h-3" />
                          <span>Email</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setInviteChannel("PHONE")}
                          className={`py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 border transition-all ${
                            inviteChannel === "PHONE"
                              ? "bg-primary text-white border-primary"
                              : "bg-surface-lowest text-zinc-400 border-white/[0.08] hover:text-white"
                          }`}
                        >
                          <Phone className="w-3 h-3" />
                          <span>SMS</span>
                        </button>
                      </div>
                    </div>

                    {/* Destination Input */}
                    <div className="flex flex-col gap-1">
                      <label htmlFor="invite-destination" className="text-[11px] font-semibold text-zinc-300">
                        {inviteChannel === "EMAIL" ? "Elektron pochta manzili:" : "Telefon raqami:"}
                      </label>
                      <input
                        id="invite-destination"
                        type={inviteChannel === "EMAIL" ? "email" : "text"}
                        required
                        value={inviteDestination}
                        onChange={(e) => setInviteDestination(e.target.value)}
                        placeholder={inviteChannel === "EMAIL" ? "hr.manager@example.com" : "+998901234567"}
                        className="w-full rounded-lg border border-white/[0.1] bg-surface-lowest px-3 py-2 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none"
                      />
                    </div>

                    {/* Role Selector */}
                    <div className="flex flex-col gap-1">
                      <label htmlFor="invite-role" className="text-[11px] font-semibold text-zinc-300">
                        Tayinlanadigan rol:
                      </label>
                      <select
                        id="invite-role"
                        value={inviteRoleCode}
                        onChange={(e) => setInviteRoleCode(e.target.value as "HR" | "HOST_COORDINATOR" | "MENTOR" | "BILLING")}
                        className="w-full rounded-lg border border-white/[0.1] bg-surface-lowest px-3 py-2 text-xs text-zinc-200 focus:border-primary focus:outline-none"
                      >
                        <option value="HR">HR (Kadrlar boshqaruvi)</option>
                        <option value="HOST_COORDINATOR">HOST_COORDINATOR (Amaliyot koordinatori)</option>
                        <option value="MENTOR">MENTOR (Amaliyot mentori)</option>
                        <option value="BILLING">BILLING (Moliya boshqaruvi)</option>
                      </select>
                    </div>

                    <div className="text-[11px] text-zinc-500 leading-relaxed pt-1">
                      * Taklifnoma xavfsiz va bir martalik bo&apos;lib, yuborilgan vaqtdan boshlab 24 soat amal qiladi.
                    </div>

                    <button
                      type="submit"
                      disabled={isSubmittingInvite || !inviteDestination.trim()}
                      className="mt-2 w-full py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-primary/20"
                    >
                      {isSubmittingInvite ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Yuborilmoqda...</span>
                        </>
                      ) : (
                        <>
                          <Send className="w-3.5 h-3.5" />
                          <span>Taklifnomani yuborish</span>
                        </>
                      )}
                    </button>
                  </form>
                </div>
              </div>
            </section>
          )}

          {/* ----------------------------------------------------------------- */}
          {/* FB-174: TO‘LOVLAR, TARIFLAR & KVOTALAR HUBI (API-070, 093, 094, 095) */}
          {/* ----------------------------------------------------------------- */}
          {activeMainTab === "BILLING_HUB" && (
            <section className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-5 flex flex-col gap-6 shadow-lg">
              {/* Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      To‘lovlar & Obuna Hub
                    </span>
                    <span className="text-zinc-500 text-xs font-mono">• API-070, API-093, API-094, API-095</span>
                  </div>
                  <h3 className="text-base font-semibold text-zinc-100">
                    Tarif Rejalari, Xizmat Huquqlari & Tranzaksiyalar
                  </h3>
                  <p className="text-xs text-zinc-400">
                    Tashkilot faol obunasi, e&apos;lon kvotalari, hisob-fakturalar va to‘lov qaytarish (refund) boshqaruvi.
                  </p>
                </div>

                <button
                  type="button"
                  disabled={isLoadingBilling || !orgId.trim()}
                  onClick={() => loadBillingHubData(orgId.trim())}
                  className="px-3 py-1.5 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300 hover:text-white transition-all flex items-center gap-1.5 disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingBilling ? "animate-spin" : ""}`} />
                  <span>Yangilash</span>
                </button>
              </div>

              {/* Billing Error / Success */}
              {billingError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-400 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{billingError}</span>
                </div>
              )}
              {orderSuccess && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-400 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{orderSuccess}</span>
                </div>
              )}
              {orderError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-400 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{orderError}</span>
                </div>
              )}

              {/* 4 Telemetry Metrics Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3.5 bg-surface-lowest rounded-xl border border-white/[0.05] flex flex-col gap-1">
                  <span className="text-[11px] font-medium text-zinc-400 flex items-center gap-1.5">
                    <CreditCard className="w-3.5 h-3.5 text-amber-400" />
                    <span>Joriy Obuna Tarifi</span>
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-zinc-100">
                      {billingOverview?.plan?.code || "BEPUL"}
                    </span>
                    <span
                      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${
                        billingOverview?.plan?.status === "ACTIVE"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                      }`}
                    >
                      {billingOverview?.plan?.status === "ACTIVE" ? "FAOL" : "NOFAOL"}
                    </span>
                  </div>
                </div>

                <div className="p-3.5 bg-surface-lowest rounded-xl border border-white/[0.05] flex flex-col gap-1">
                  <span className="text-[11px] font-medium text-zinc-400 flex items-center gap-1.5">
                    <Coins className="w-3.5 h-3.5 text-blue-400" />
                    <span>Post E&apos;lon Kvotasi</span>
                  </span>
                  <span className="text-base font-bold text-zinc-100 tabular-nums">
                    {entitlements?.active_entitlement?.quota !== null && entitlements?.active_entitlement?.quota !== undefined
                      ? `${entitlements.active_entitlement.quota} ta`
                      : (billingOverview?.plan?.quota !== null && billingOverview?.plan?.quota !== undefined
                          ? `${billingOverview.plan.quota} ta`
                          : "Cheksiz")}
                  </span>
                </div>

                <div className="p-3.5 bg-surface-lowest rounded-xl border border-white/[0.05] flex flex-col gap-1">
                  <span className="text-[11px] font-medium text-zinc-400 flex items-center gap-1.5">
                    <Briefcase className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Bo‘sh Vakansiya Slotlari</span>
                  </span>
                  <span className="text-base font-bold text-zinc-100 tabular-nums">
                    {entitlements?.usage?.concurrent_slots_available ?? 0} ta bo‘sh
                  </span>
                  <span className="text-[10px] text-zinc-500 tabular-nums">
                    Limit: {entitlements?.usage?.concurrent_active_limit ?? 0} ta bir vaqtda
                  </span>
                </div>

                <div className="p-3.5 bg-surface-lowest rounded-xl border border-white/[0.05] flex flex-col gap-1">
                  <span className="text-[11px] font-medium text-zinc-400 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-purple-400" />
                    <span>Amal Qilish Muddati</span>
                  </span>
                  <span className="text-base font-bold text-zinc-100 tabular-nums">
                    {entitlements?.usage?.days_remaining ?? 0} kun
                  </span>
                  <span className="text-[10px] text-zinc-500">
                    {entitlements?.active_entitlement?.ends_at
                      ? new Date(entitlements.active_entitlement.ends_at).toLocaleDateString()
                      : "Muddatsiz"}
                  </span>
                </div>
              </div>

              {/* GRID 2 COLUMNS: Plans on Left, Entitlements on Right */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Section A: Tarif Rejalari & Buyurtma Berish (API-094) */}
                <div className="bg-surface-lowest border border-white/[0.05] rounded-xl p-4 flex flex-col gap-4">
                  <div className="flex items-center justify-between border-b border-white/[0.05] pb-2.5">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-amber-400" />
                      <span className="text-xs font-semibold text-zinc-200">
                        Tarif Rejalari (API-094)
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-500">MFA + OWNER/BILLING</span>
                  </div>

                  {/* Plan Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {/* Plan 1: ORG_PLAN_30D */}
                    <div
                      onClick={() => setSelectedPlanCode("ORG_PLAN_30D")}
                      className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col gap-2.5 ${
                        selectedPlanCode === "ORG_PLAN_30D"
                          ? "bg-primary/10 border-primary text-white shadow-md shadow-primary/10"
                          : "bg-surface-card border-white/[0.08] hover:border-white/[0.2] text-zinc-300"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-zinc-100">Kompaniya Oylik</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/20 text-primary font-semibold">Tavsiya</span>
                      </div>
                      <div className="flex items-baseline gap-1">
                        <span className="text-lg font-bold text-zinc-100 tabular-nums">599,000</span>
                        <span className="text-[10px] text-zinc-400">UZS / oy</span>
                      </div>
                      <ul className="text-[11px] text-zinc-400 flex flex-col gap-1.5">
                        <li className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>5 ta bir vaqtda faol vakansiya</span>
                        </li>
                        <li className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>Cheksiz post e&apos;lon krediti</span>
                        </li>
                        <li className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>30 kunlik to‘liq amal muddati</span>
                        </li>
                      </ul>
                    </div>

                    {/* Plan 2: SINGLE_POST_30D */}
                    <div
                      onClick={() => setSelectedPlanCode("SINGLE_POST_30D")}
                      className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col gap-2.5 ${
                        selectedPlanCode === "SINGLE_POST_30D"
                          ? "bg-primary/10 border-primary text-white shadow-md shadow-primary/10"
                          : "bg-surface-card border-white/[0.08] hover:border-white/[0.2] text-zinc-300"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-zinc-100">Bittalik E&apos;lon</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 font-semibold">Start</span>
                      </div>
                      <div className="flex items-baseline gap-1">
                        <span className="text-lg font-bold text-zinc-100 tabular-nums">149,000</span>
                        <span className="text-[10px] text-zinc-400">UZS</span>
                      </div>
                      <ul className="text-[11px] text-zinc-400 flex flex-col gap-1.5">
                        <li className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>1 ta bir vaqtda faol e&apos;lon</span>
                        </li>
                        <li className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>1 ta post e&apos;lon qilish krediti</span>
                        </li>
                        <li className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>30 kunlik faollik muddati</span>
                        </li>
                      </ul>
                    </div>
                  </div>

                  <button
                    type="button"
                    disabled={isOrdering || !orgId.trim()}
                    onClick={() => handleCreateOrder(selectedPlanCode)}
                    className="w-full py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center justify-center gap-2 disabled:opacity-50 shadow-md shadow-primary/20"
                  >
                    {isOrdering ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Buyurtma rasmiylashtirilmoqda...</span>
                      </>
                    ) : (
                      <>
                        <CheckSquare className="w-4 h-4" />
                        <span>{selectedPlanCode === "ORG_PLAN_30D" ? "599,000 UZS lik Kompaniya Tarifini Olish" : "149,000 UZS lik Bittalik E'lonni Olish"}</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Section B: Xizmat Huquqlari & Kvota Telemetriyasi (API-070) */}
                <div className="bg-surface-lowest border border-white/[0.05] rounded-xl p-4 flex flex-col gap-4">
                  <div className="flex items-center justify-between border-b border-white/[0.05] pb-2.5">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs font-semibold text-zinc-200">
                        Xizmat Huquqlari & Kvotalar (API-070)
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-500">REALTIME USAGE</span>
                  </div>

                  {/* Slot Usage Progress Bar */}
                  <div className="flex flex-col gap-2 p-3 bg-surface-card rounded-lg border border-white/[0.05]">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-zinc-400">Faol E&apos;lonlar Slotidan Foydalanish:</span>
                      <span className="font-bold text-zinc-200 tabular-nums">
                        {entitlements?.usage?.concurrent_active_opportunities ?? 0} / {entitlements?.usage?.concurrent_active_limit ?? 0}
                      </span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-emerald-500 h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${Math.min(
                            100,
                            entitlements?.usage?.concurrent_active_limit
                              ? ((entitlements.usage.concurrent_active_opportunities / entitlements.usage.concurrent_active_limit) * 100)
                              : 0
                          )}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Entitlement Details List */}
                  <div className="flex flex-col gap-2 text-xs">
                    <div className="flex items-center justify-between py-1 border-b border-white/[0.05]">
                      <span className="text-zinc-400">Faol Xizmat Turi:</span>
                      <span className="font-mono text-zinc-200">{entitlements?.active_entitlement?.service_kind || "BEPUL_KIRISH"}</span>
                    </div>
                    <div className="flex items-center justify-between py-1 border-b border-white/[0.05]">
                      <span className="text-zinc-400">Boshlanish Sanasi:</span>
                      <span className="text-zinc-200">
                        {entitlements?.active_entitlement?.starts_at
                          ? new Date(entitlements.active_entitlement.starts_at).toLocaleString()
                          : "Ko'rsatilmagan"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-1 border-b border-white/[0.05]">
                      <span className="text-zinc-400">Tugash Sanasi:</span>
                      <span className="text-zinc-200">
                        {entitlements?.active_entitlement?.ends_at
                          ? new Date(entitlements.active_entitlement.ends_at).toLocaleString()
                          : "Muddatsiz"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-1">
                      <span className="text-zinc-400">Bog&apos;langan Buyurtma:</span>
                      <span className="font-mono text-zinc-400">
                        {entitlements?.active_entitlement?.order_id
                          ? `#${entitlements.active_entitlement.order_id.slice(0, 8)}`
                          : "To'g'ridan-to'g'ri"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Section C: Hisob-fakturalar & Buyurtmalar Tarixi (API-093) */}
              <div className="bg-surface-lowest border border-white/[0.05] rounded-xl p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between border-b border-white/[0.05] pb-2.5">
                  <div className="flex items-center gap-2">
                    <Receipt className="w-4 h-4 text-zinc-400" />
                    <span className="text-xs font-semibold text-zinc-200">
                      Buyurtmalar & Hisob-fakturalar Tarixi (API-093)
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500">
                    Jami: {billingOverview?.orders?.length ?? 0} ta buyurtma
                  </span>
                </div>

                {billingOverview?.orders && billingOverview.orders.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-white/[0.08] text-zinc-400 font-medium">
                          <th className="py-2 px-3">Buyurtma ID</th>
                          <th className="py-2 px-3">Tarif Rejasi</th>
                          <th className="py-2 px-3">Summa</th>
                          <th className="py-2 px-3">Holati</th>
                          <th className="py-2 px-3">Sana</th>
                          <th className="py-2 px-3 text-right">Harakat</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04]">
                        {billingOverview.orders.map((order) => (
                          <tr key={order.id} className="hover:bg-white/[0.02] transition-colors">
                            <td className="py-2.5 px-3 font-mono text-zinc-300">
                              #{order.id.slice(0, 8)}
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-zinc-200">
                              {order.plan_code || "XIZMAT_PAKETI"}
                            </td>
                            <td className="py-2.5 px-3 font-bold text-zinc-100 tabular-nums">
                              {order.amount.toLocaleString()} UZS
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                                  order.status === "PAID"
                                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                    : order.status === "PENDING_PAYMENT"
                                    ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                                    : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                                }`}
                              >
                                {order.status}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-zinc-400">
                              {order.created_at ? new Date(order.created_at).toLocaleDateString() : "—"}
                            </td>
                            <td className="py-2.5 px-3 text-right">
                              {order.status === "PAID" && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setRefundModalOrder(order);
                                    setRefundAmountUzs(String(order.amount));
                                    setRefundReason("");
                                    setRefundError(null);
                                    setRefundSuccess(null);
                                  }}
                                  className="px-2.5 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-[11px] font-semibold transition-all"
                                >
                                  Mablag‘ni Qaytarish (API-095)
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="py-8 text-center text-xs text-zinc-500">
                    Hozircha buyurtmalar mavjud emas. Yuqoridagi tariflardan birini tanlab buyurtma bering.
                  </div>
                )}
              </div>
            </section>
          )}
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

      {/* ----------------------------------------------------------------- */}
      {/* FB-162: WORKPLACE MENTOR LOG REVISION REVIEW MODAL (API-091 & 092) */}
      {/* ----------------------------------------------------------------- */}
      {reviewModalRevisionId && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-white/[0.1] bg-[#121214] p-6 shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center gap-2">
                <Award className="w-5 h-5 text-primary" />
                <h3 className="font-heading text-base font-bold text-white">
                  Kundalikni Tekshirish va Baholash (API-091 / API-092)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setReviewModalRevisionId(null)}
                className="rounded-lg p-1 text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {isLoadingRevisionDetail ? (
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400 text-xs">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
                <span>Kundalik tafsilotlari yuklanmoqda...</span>
              </div>
            ) : revisionDetailError ? (
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                {revisionDetailError}
              </div>
            ) : revisionDetail ? (
              <div className="flex flex-col gap-4">
                {/* Intern and Log Overview */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs bg-surface p-3.5 rounded-xl border border-white/[0.06]">
                  <div>
                    <span className="text-zinc-500 block text-[10px]">Talaba:</span>
                    <span className="font-semibold text-white">{revisionDetail.candidate?.full_name}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block text-[10px]">Sana & Tur:</span>
                    <span className="font-mono text-zinc-200">{revisionDetail.log_date} ({revisionDetail.day_type})</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block text-[10px]">Jami daqiqa:</span>
                    <span className="font-mono text-emerald-400 font-bold">
                      {revisionDetail.total_minutes} daqiqa ({(revisionDetail.total_minutes / 60).toFixed(1)} s.)
                    </span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block text-[10px]">Holat:</span>
                    <span className="font-semibold text-primary">{revisionDetail.status}</span>
                  </div>
                </div>

                {/* Summary */}
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-semibold text-zinc-300">Talaba xulosasi:</span>
                  <div className="p-3 rounded-xl bg-surface-lowest border border-white/[0.06] text-xs text-zinc-300">
                    {revisionDetail.summary || "Xulosa ko'rsatilmagan."}
                  </div>
                </div>

                {/* Task Breakdown */}
                <div className="flex flex-col gap-2">
                  <span className="text-xs font-semibold text-zinc-300">
                    Bajarilgan vazifalar ro&apos;yxati ({revisionDetail.tasks?.length || 0} ta):
                  </span>
                  <div className="flex flex-col gap-2 max-h-56 overflow-y-auto">
                    {!revisionDetail.tasks || revisionDetail.tasks.length === 0 ? (
                      <span className="text-zinc-500 text-xs italic">Vazifalar qayd etilmagan</span>
                    ) : (
                      revisionDetail.tasks.map((task, idx) => (
                        <div
                          key={task.task_id || idx}
                          className="p-3 rounded-xl bg-surface border border-white/[0.04] flex flex-col gap-1.5"
                        >
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-medium text-white">{task.title}</span>
                            <span className="font-mono text-emerald-400 font-semibold">{task.minutes} min</span>
                          </div>
                          {task.evidence && task.evidence.length > 0 && (
                            <div className="flex items-center gap-1.5 text-[11px] text-zinc-400">
                              <ExternalLink className="w-3 h-3 text-primary" />
                              <span>Biriktirilgan dalillar: {task.evidence.length} ta fayl</span>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Existing Review Notice if any */}
                {revisionDetail.existing_review && (
                  <div className="p-3 rounded-xl bg-surface-high border border-white/[0.08] text-xs flex flex-col gap-1">
                    <span className="text-zinc-400 text-[10px]">Avvalgi baholash natijasi:</span>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{revisionDetail.existing_review.decision}</span>
                      {revisionDetail.existing_review.decided_at && (
                        <span className="text-[10px] text-zinc-500 font-mono">
                          ({new Date(revisionDetail.existing_review.decided_at).toLocaleString()})
                        </span>
                      )}
                    </div>
                    {revisionDetail.existing_review.comment && (
                      <p className="text-zinc-300 italic">{revisionDetail.existing_review.comment}</p>
                    )}
                  </div>
                )}

                {/* Success Message */}
                {reviewSubmitSuccess && (
                  <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>{reviewSubmitSuccess}</span>
                  </div>
                )}

                {/* Error Message */}
                {reviewSubmitError && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <span>{reviewSubmitError}</span>
                  </div>
                )}

                {/* Evaluation Form */}
                <form onSubmit={handleSubmitReviewDecision} className="flex flex-col gap-3 pt-2 border-t border-white/[0.08]">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-zinc-300">Mentor Qarori (API-092):</label>
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        type="button"
                        onClick={() => setReviewDecision("APPROVED")}
                        className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all border ${
                          reviewDecision === "APPROVED"
                            ? "bg-emerald-500/20 border-emerald-500 text-emerald-300 shadow-md shadow-emerald-500/10"
                            : "bg-surface border-white/[0.08] text-zinc-400 hover:text-white"
                        }`}
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Tasdiqlash</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setReviewDecision("CHANGES_REQUESTED")}
                        className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all border ${
                          reviewDecision === "CHANGES_REQUESTED"
                            ? "bg-amber-500/20 border-amber-500 text-amber-300 shadow-md shadow-amber-500/10"
                            : "bg-surface border-white/[0.08] text-zinc-400 hover:text-white"
                        }`}
                      >
                        <Clock className="w-3.5 h-3.5" />
                        <span>Tuzatish so&apos;rash</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setReviewDecision("REJECTED")}
                        className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all border ${
                          reviewDecision === "REJECTED"
                            ? "bg-rose-500/20 border-rose-500 text-rose-300 shadow-md shadow-rose-500/10"
                            : "bg-surface border-white/[0.08] text-zinc-400 hover:text-white"
                        }`}
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Rad etish</span>
                      </button>
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="review-comment" className="text-xs font-semibold text-zinc-300">
                      Mentor Izohi / Tavsiyalari:
                    </label>
                    <textarea
                      id="review-comment"
                      rows={3}
                      value={reviewComment}
                      onChange={(e) => setReviewComment(e.target.value)}
                      placeholder="Talabaga vazifalar bo‘yicha ko‘rsatma yoki fikrlaringizni yozing..."
                      className="w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-3 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none"
                    />
                  </div>

                  <div className="flex items-center justify-end gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => setReviewModalRevisionId(null)}
                      className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300"
                    >
                      Yopish
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmittingReview}
                      className="px-5 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow"
                    >
                      {isSubmittingReview ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Saqlanmoqda...</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Qarorni tasdiqlash</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* REVOKE MEMBERSHIP MODAL (API-075) */}
      {revokeModalMembership && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-md rounded-2xl border border-white/[0.1] bg-[#121214] p-6 shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2 text-rose-400">
                <ShieldAlert className="w-5 h-5" />
                <h3 className="font-heading text-base font-bold text-white">
                  A&apos;zolikni Bekor Qilish
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setRevokeModalMembership(null)}
                className="rounded-lg p-1 text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-zinc-400">
              Siz <span className="font-semibold text-white">Foydalanuvchi #{revokeModalMembership.user_id.slice(0, 8)}</span> ({revokeModalMembership.role}) a&apos;zoligini bekor qilmoqchisiz. Ushbu amal foydalanuvchining tashkilotdagi barcha huquqlarini to&apos;xtatadi.
            </p>

            <form onSubmit={handleRevokeMembership} className="flex flex-col gap-3">
              {revokeError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                  {revokeError}
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="revoke-reason" className="text-xs font-semibold text-zinc-300">
                    Bekor qilish sababi (kamida 15 ta belgi):
                  </label>
                  <span className={`text-[10px] font-mono ${
                    revokeReason.trim().length >= 15 ? "text-emerald-400" : "text-amber-400"
                  }`}>
                    {revokeReason.trim().length} / 15
                  </span>
                </div>
                <textarea
                  id="revoke-reason"
                  rows={3}
                  required
                  value={revokeReason}
                  onChange={(e) => setRevokeReason(e.target.value)}
                  placeholder="Xodim bilan mehnat shartnomasi bekor qilinganligi sababli..."
                  className="w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-3 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-rose-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setRevokeModalMembership(null)}
                  className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingRevoke || revokeReason.trim().length < 15}
                  className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-rose-600/20"
                >
                  {isSubmittingRevoke ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Tasdiqlanmoqda...</span>
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>A&apos;zolikni to&apos;xtatish</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* FB-174: MABLAG‘NI QAYTARISH SO‘ROVI MODALI (API-095) */}
      {/* ----------------------------------------------------------------- */}
      {refundModalOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-white/[0.1] bg-surface-card p-6 shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  <CreditCard className="w-4 h-4" />
                </span>
                <div>
                  <h4 className="text-sm font-semibold text-zinc-100">To‘lovni Qaytarish So‘rovi</h4>
                  <p className="text-[11px] text-zinc-400 font-mono">
                    Buyurtma #{refundModalOrder.id.slice(0, 8)} • API-095
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setRefundModalOrder(null)}
                className="p-1 rounded-lg hover:bg-white/[0.05] text-zinc-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {refundError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-400 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{refundError}</span>
              </div>
            )}
            {refundSuccess && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-400 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{refundSuccess}</span>
              </div>
            )}

            <form onSubmit={handleRequestRefund} className="flex flex-col gap-3.5">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  Qaytarish Summasi (UZS)
                </label>
                <input
                  type="number"
                  min="1"
                  max={refundModalOrder.amount}
                  value={refundAmountUzs}
                  onChange={(e) => setRefundAmountUzs(e.target.value)}
                  className="w-full rounded-xl border border-white/[0.1] bg-surface-lowest px-3 py-2 text-xs text-zinc-100 tabular-nums focus:border-primary focus:outline-none"
                />
                <span className="text-[10px] text-zinc-500">Maksimal: {refundModalOrder.amount.toLocaleString()} UZS</span>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  Qaytarish Sababi (kamida 15 ta belgi) *
                </label>
                <textarea
                  rows={3}
                  value={refundReason}
                  onChange={(e) => setRefundReason(e.target.value)}
                  placeholder="Xizmat ko‘rsatish rejasini o‘zgartirish yoki xato to‘lov sababli..."
                  className="w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-3 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setRefundModalOrder(null)}
                  className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-300"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingRefund || refundReason.trim().length < 15}
                  className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-rose-600/20"
                >
                  {isSubmittingRefund ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Yuborilmoqda...</span>
                    </>
                  ) : (
                    <>
                      <CreditCard className="w-3.5 h-3.5" />
                      <span>So‘rovni Yuborish (API-095)</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
