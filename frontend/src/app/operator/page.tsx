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
} from "lucide-react";
import {
  fetchAuthMe,
  fetchOperatorAuditEvents,
  fetchOperatorVerificationCases,
  claimVerificationCase,
  decideVerificationCase,
  requestBreakGlassAccess,
  emergencyRevokeUserSessions,
  logoutUser,
  AuthUser,
  OperatorAuditEventItem,
  OperatorVerificationCaseItem,
  BreakGlassAccessResult,
  EmergencyRevokeSessionsResult,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";

type ActiveTab = "AUDIT" | "VERIFICATION" | "BREAK_GLASS";

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

  useEffect(() => {
    let isMounted = true;
    fetchAuthMe().then((user) => {
      if (isMounted) {
        setCurrentUser(user);
        setIsAuthLoading(false);
        if (user) {
          loadAuditEvents();
          loadVerificationCases();
        }
      }
    });
    return () => {
      isMounted = false;
    };
  }, [loadAuditEvents, loadVerificationCases]);

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setAuditEvents([]);
    setCases([]);
    setEventsError(null);
    setCasesError(null);
  };

  const handleLoginSuccess = (user: AuthUser) => {
    setCurrentUser(user);
    loadAuditEvents();
    loadVerificationCases();
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
