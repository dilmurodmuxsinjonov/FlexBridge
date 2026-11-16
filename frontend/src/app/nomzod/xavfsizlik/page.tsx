"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { describeRequestError } from "@/lib/errors";
import { useAsyncData } from "@/lib/useAsyncData";
import {
  Shield,
  ShieldCheck,
  KeyRound,
  Smartphone,
  Laptop,
  Lock,
  LogOut,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Copy,
  Check,
  Download,
  AlertTriangle,
  X,
  User,
  ArrowRight,
} from "lucide-react";
import {
  fetchUserSecurityOverview,
  requestTotpEnrollment,
  confirmTotpEnrollment,
  disableTotp,
  generateRecoveryCodes,
  revokeUserSession,
  UserSecurityOverview,
  ActiveSessionItem,
} from "@/lib/api";
import { SkeuoStatCard } from "@/components/skeuo/SkeuoPrimitives";

export default function CandidateSecurityPage() {
  const router = useRouter();
  const overview = useAsyncData<UserSecurityOverview>("security-overview", fetchUserSecurityOverview);
  const securityData = overview.data ?? null;
  const isLoading = overview.isLoading;
  // Errors from user actions; load errors come from `overview.error`.
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const displayedError =
    errorMessage ??
    (overview.error ? describeRequestError(overview.error, "Xavfsizlik ma'lumotlarini yuklashda xatolik yuz berdi.") : null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // TOTP Enrollment Modal State
  // ---------------------------------------------------------------------------
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [enrollPassword, setEnrollPassword] = useState("");
  const [enrollStepUpTotp, setEnrollStepUpTotp] = useState("");
  const [isEnrolling, setIsEnrolling] = useState(false);
  const [enrollSecret, setEnrollSecret] = useState<string | null>(null);
  const [confirmationCode, setConfirmationCode] = useState("");
  const [isConfirming, setIsConfirming] = useState(false);
  const [copiedSecret, setCopiedSecret] = useState(false);

  // ---------------------------------------------------------------------------
  // TOTP Disable Modal State
  // ---------------------------------------------------------------------------
  const [isDisableModalOpen, setIsDisableModalOpen] = useState(false);
  const [disablePassword, setDisablePassword] = useState("");
  const [disableTotpCode, setDisableTotpCode] = useState("");
  const [isDisabling, setIsDisabling] = useState(false);

  // ---------------------------------------------------------------------------
  // Recovery Codes Modal State
  // ---------------------------------------------------------------------------
  const [isRecoveryModalOpen, setIsRecoveryModalOpen] = useState(false);
  const [recoveryPassword, setRecoveryPassword] = useState("");
  const [recoveryTotpCode, setRecoveryTotpCode] = useState("");
  const [isGeneratingRecovery, setIsGeneratingRecovery] = useState(false);
  const [generatedCodes, setGeneratedCodes] = useState<string[] | null>(null);
  const [copiedCodes, setCopiedCodes] = useState(false);

  // ---------------------------------------------------------------------------
  // Session Revocation State
  // ---------------------------------------------------------------------------
  const [revokingSessionId, setRevokingSessionId] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Data Loading
  // ---------------------------------------------------------------------------
  const reloadOverview = overview.reload;
  const loadSecurityOverview = useCallback(async () => {
    setErrorMessage(null);
    await reloadOverview();
  }, [reloadOverview]);

  // ---------------------------------------------------------------------------
  // TOTP Handlers
  // ---------------------------------------------------------------------------
  const handleStartTotpEnrollment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!enrollPassword.trim()) {
      setErrorMessage("Joriy maxfiy so'zni kiritishingiz shart.");
      return;
    }
    setIsEnrolling(true);
    setErrorMessage(null);
    try {
      const res = await requestTotpEnrollment(enrollPassword.trim(), enrollStepUpTotp.trim() || undefined);
      if (res.secret) {
        setEnrollSecret(res.secret);
      } else {
        setErrorMessage("TOTP maxfiy kalitini olishda xatolik yuz berdi.");
      }
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Ikki bosqichli autentifikatsiyani boshlashda xatolik yuz berdi."
      );
    } finally {
      setIsEnrolling(false);
    }
  };

  const handleConfirmTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!confirmationCode.trim() || !/^[0-9]{6}$/.test(confirmationCode.trim())) {
      setErrorMessage("Iltimos, ilovangizdagi 6 xonali raqamli kodni kiriting.");
      return;
    }
    setIsConfirming(true);
    setErrorMessage(null);
    try {
      await confirmTotpEnrollment(confirmationCode.trim());
      setSuccessMessage("Ikki bosqichli autentifikatsiya (TOTP) muvaffaqiyatli yoqildi!");
      setIsEnrollModalOpen(false);
      setEnrollSecret(null);
      setEnrollPassword("");
      setEnrollStepUpTotp("");
      setConfirmationCode("");
      await loadSecurityOverview();
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "TOTP kodini tasdiqlashda xatolik yuz berdi. Kod to'g'riligini tekshiring."
      );
    } finally {
      setIsConfirming(false);
    }
  };

  const handleDisableTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!disablePassword.trim()) {
      setErrorMessage("Parolni kiritishingiz shart.");
      return;
    }
    setIsDisabling(true);
    setErrorMessage(null);
    try {
      await disableTotp(disablePassword.trim(), disableTotpCode.trim() || undefined);
      setSuccessMessage("Ikki bosqichli autentifikatsiya muvaffaqiyatli o'chirildi.");
      setIsDisableModalOpen(false);
      setDisablePassword("");
      setDisableTotpCode("");
      await loadSecurityOverview();
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "TOTP ni o'chirishda xatolik yuz berdi."
      );
    } finally {
      setIsDisabling(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Recovery Codes Handlers
  // ---------------------------------------------------------------------------
  const handleGenerateRecoveryCodes = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recoveryPassword.trim()) {
      setErrorMessage("Parolni kiritishingiz shart.");
      return;
    }
    setIsGeneratingRecovery(true);
    setErrorMessage(null);
    try {
      const res = await generateRecoveryCodes(recoveryPassword.trim(), recoveryTotpCode.trim() || undefined);
      if (res.recovery_codes && res.recovery_codes.length > 0) {
        setGeneratedCodes(res.recovery_codes);
        setSuccessMessage("Yangi zaxira tiklash kodlari muvaffaqiyatli yaratildi!");
        await loadSecurityOverview();
      }
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Zaxira kodlarini yaratishda xatolik yuz berdi."
      );
    } finally {
      setIsGeneratingRecovery(false);
    }
  };

  const handleCopyCodes = () => {
    if (!generatedCodes) return;
    navigator.clipboard.writeText(generatedCodes.join("\n"));
    setCopiedCodes(true);
    setTimeout(() => setCopiedCodes(false), 2500);
  };

  const handleDownloadCodes = () => {
    if (!generatedCodes) return;
    const content = `FLEXBRIDGE FAVQULODDA ZAXIRA KODLARI\nYaratilgan vaqt: ${new Date().toISOString()}\n\nHar bir kod faqat bir marta ishlatiladi:\n\n${generatedCodes.map((c, i) => `${i + 1}. ${c}`).join("\n")}\n\nEslatma: Ushbu kodlarni xavfsiz joyda saqlang.`;
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `flexbridge-recovery-codes-${new Date().toISOString().slice(0, 10)}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // ---------------------------------------------------------------------------
  // Session Revoke Handler
  // ---------------------------------------------------------------------------
  const handleRevokeSession = async (sessionId: string, isCurrent: boolean) => {
    const confirmText = isCurrent
      ? "Haqiqatan ham joriy qurilmadagi sessiyani yakunlamoqchimisiz? Tizimdan chiqib ketasiz."
      : "Ushbu qurilmadagi faol sessiyani bekor qilmoqchimisiz?";
    if (!window.confirm(confirmText)) return;

    setRevokingSessionId(sessionId);
    setErrorMessage(null);
    try {
      await revokeUserSession(sessionId);
      if (isCurrent) {
        // BFF cleared the session cookie; resync shared chrome like the Navbar logout does.
        window.dispatchEvent(new Event("flexbridge:auth-changed"));
        router.push("/");
        router.refresh();
        return;
      }
      setSuccessMessage("Sessiya muvaffaqiyatli yakunlandi.");
      await loadSecurityOverview();
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Sessiyani yakunlashda xatolik yuz berdi."
      );
    } finally {
      setRevokingSessionId(null);
    }
  };

  const copySecretToClipboard = (secret: string) => {
    navigator.clipboard.writeText(secret);
    setCopiedSecret(true);
    setTimeout(() => setCopiedSecret(false), 2500);
  };

  return (
    <div className="w-full text-zinc-100">
      <div className="w-full space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
          <Link href="/nomzod" className="hover:text-white transition flex items-center gap-1">
            <User className="w-3.5 h-3.5" />
            <span>Nomzod Kabineti</span>
          </Link>
          <span>/</span>
          <span className="text-zinc-200 font-medium">Xavfsizlik & Sessiyalar</span>
        </div>

        {/* Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Shield className="w-6 h-6 text-primary" />
              Xavfsizlik, Ikki Bosqichli Autentifikatsiya (MFA) & Sessiyalar
            </h1>
            <p className="text-xs text-[var(--fb-ink-secondary)] mt-1">
              Parol bilan qo‘shimcha tasdiqlash, ikki bosqichli autentifikatsiya, zaxira kodlari va faol qurilmalarni boshqarish.
            </p>
          </div>
          <button
            onClick={loadSecurityOverview}
            disabled={isLoading}
            className="px-3.5 py-2 text-xs font-semibold rounded-xl skeuo-btn-secondary flex items-center gap-2 self-start md:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[var(--fb-ink-muted)] ${isLoading ? "animate-spin" : ""}`} />
            Yangilash
          </button>
        </div>

        {/* Alert Notifications */}
        {displayedError && (
          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{displayedError}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-rose-200">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {successMessage && (
          <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              <span>{successMessage}</span>
            </div>
            <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:text-emerald-200">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ------------------------------------------------------------------- */}
        {/* TELEMETRY CARDS */}
        {/* ------------------------------------------------------------------- */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <SkeuoStatCard
            title="Ikki bosqichli himoya (MFA)"
            value={securityData?.totp_enabled ? "FAOL" : "YOQILMAGAN"}
            subtitle="TOTP autentifikator holati"
            icon={ShieldCheck}
            tone={securityData?.totp_enabled ? "emerald" : "amber"}
          />
          <SkeuoStatCard
            title="Ishonch darajasi"
            value={securityData?.totp_enabled ? "A2" : "A1"}
            subtitle={securityData?.totp_enabled ? "MFA-LEVEL himoya" : "Faqat parol darajasi"}
            icon={Lock}
            tone="sky"
          />
          <SkeuoStatCard
            title="Zaxira tiklash kodlari"
            value={securityData?.recovery_codes_count ?? 0}
            subtitle="Faol tiklash kalitlari"
            icon={KeyRound}
            tone="amber"
          />
          <SkeuoStatCard
            title="Faol sessiyalar"
            value={securityData?.sessions?.length ?? 0}
            subtitle="Ulangan qurilmalar"
            icon={Laptop}
            tone="indigo"
          />
        </div>

        {/* ------------------------------------------------------------------- */}
        {/* SECTION 1: TOTP TWO-FACTOR AUTHENTICATION (API-060) */}
        {/* ------------------------------------------------------------------- */}
        <div className="p-5 md:p-6 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Smartphone className="w-5 h-5 text-primary" />
                Ikki Bosqichli Autentifikatsiya (2FA / TOTP)
              </h2>
              <p className="text-xs text-zinc-400 mt-1">
                Google Authenticator, Microsoft Authenticator yoki 1Password orqali bir martalik 6 xonali dinamik xavfsizlik kodlari.
              </p>
            </div>
            {securityData?.totp_enabled ? (
              <button
                type="button"
                onClick={() => setIsDisableModalOpen(true)}
                className="px-3.5 py-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-xs font-semibold flex items-center gap-1.5 transition self-start sm:self-auto"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>MFA ni O‘chirish</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setIsEnrollModalOpen(true);
                  setEnrollSecret(null);
                  setErrorMessage(null);
                }}
                className="px-4 py-2 rounded-xl skeuo-btn-accent text-white text-xs font-semibold flex items-center gap-1.5 self-start sm:self-auto"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>2FA Himoyasini Yoqish</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04] space-y-1">
              <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Holat</span>
              <p className="text-sm font-medium text-white flex items-center gap-2">
                {securityData?.totp_enabled ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-emerald-400">Hisobingiz 2FA bilan himoyalangan</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span className="text-amber-400">Faqat oddiy parol bilan himoyalangan</span>
                  </>
                )}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04] space-y-1">
              <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Standart</span>
              <p className="text-sm font-medium text-white">RFC 6238 TOTP (SHA-1 / 30 soniya)</p>
            </div>
            <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04] space-y-1">
              <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Himoya Qamrovi</span>
              <p className="text-sm font-medium text-white">Barcha portal sessiyalari & API amallari</p>
            </div>
          </div>
        </div>

        {/* ------------------------------------------------------------------- */}
        {/* SECTION 2: EMERGENCY RECOVERY CODES */}
        {/* ------------------------------------------------------------------- */}
        <div className="p-5 md:p-6 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-amber-400" />
                Favqulodda Zaxira Tiklash Kodlari (Recovery Codes)
              </h2>
              <p className="text-xs text-zinc-400 mt-1">
                Telefoningiz yoki authenticator ilovangizga kirish imkoni bo‘lmaganda hisobni tiklash uchun bir martalik zaxira kodlari.
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setIsRecoveryModalOpen(true);
                setGeneratedCodes(null);
                setErrorMessage(null);
              }}
              className="px-3.5 py-2 rounded-lg bg-[#18181b] hover:bg-white/[0.06] border border-white/[0.08] text-zinc-200 text-xs font-semibold flex items-center gap-1.5 transition self-start sm:self-auto"
            >
              <RefreshCw className="w-3.5 h-3.5 text-amber-400" />
              <span>Yangi Zaxira Kodlari Yaratish</span>
            </button>
          </div>

          <div className="p-4 rounded-lg bg-amber-500/5 border border-amber-500/10 text-xs text-amber-300/90 flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
            <p className="leading-relaxed">
              Zaxira kodlari har safar qayta yaratilganda, avvalgi barcha faol kodlar avtomatik ravishda bekor qilinadi.
              Har bir kod faqat bir marta ishlatilishi mumkin. Kodlarni chop etib yoki shifrlangan faylda xavfsiz saqlang.
            </p>
          </div>
        </div>

        {/* ------------------------------------------------------------------- */}
        {/* SECTION 3: ACTIVE SESSIONS & DEVICES (API-061) */}
        {/* ------------------------------------------------------------------- */}
        <div className="p-5 md:p-6 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Laptop className="w-5 h-5 text-violet-400" />
                Faol Qurilmalar & Sessiyalar Boshqaruvi
              </h2>
              <p className="text-xs text-zinc-400 mt-1">
                Hisobingizga kirilgan barcha faol sessiyalar ro‘yxati. Notanish yoki eski qurilmalarni istalgan vaqtda bekor qilishingiz mumkin.
              </p>
            </div>
          </div>

          {isLoading ? (
            <div className="p-12 text-center text-xs text-zinc-400 flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              <span>Sessiyalar yuklanmoqda...</span>
            </div>
          ) : !securityData?.sessions || securityData.sessions.length === 0 ? (
            <div className="p-8 text-center text-xs text-zinc-400">
              Faol sessiyalar topilmadi.
            </div>
          ) : (
            <div className="divide-y divide-white/[0.06]">
              {securityData.sessions.map((session: ActiveSessionItem) => {
                const isCurrent = session.is_current;
                const isRevoking = revokingSessionId === session.id;

                return (
                  <div
                    key={session.id}
                    className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-2.5 rounded-lg border mt-0.5 ${
                        isCurrent
                          ? "bg-primary/10 border-primary/20 text-primary"
                          : "bg-white/[0.04] border-white/[0.08] text-zinc-400"
                      }`}>
                        <Laptop className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-zinc-200 font-semibold text-[11px]">
                            {session.id}
                          </span>
                          {isCurrent && (
                            <span className="px-2 py-0.5 rounded bg-primary/20 text-primary border border-primary/30 text-[10px] font-semibold">
                              Joriy Qurilma
                            </span>
                          )}
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                            session.assurance === "MFA"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                          }`}>
                            {session.assurance === "MFA" ? "MFA bilan tasdiqlangan" : "Parol orqali kirilgan"}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-zinc-400 text-[11px] mt-1 font-mono">
                          <span>Yaratilgan: {session.created_at ? new Date(session.created_at).toLocaleString("uz-UZ") : "—"}</span>
                          <span>•</span>
                          <span>Muddati: {session.expires_at ? new Date(session.expires_at).toLocaleString("uz-UZ") : "—"}</span>
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      disabled={isRevoking}
                      onClick={() => handleRevokeSession(session.id, isCurrent)}
                      className="px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-xs font-semibold flex items-center gap-1.5 transition self-start sm:self-auto shrink-0"
                    >
                      {isRevoking ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <LogOut className="w-3.5 h-3.5" />
                      )}
                      <span>{isCurrent ? "Chiqish (Logout)" : "Sessiyani Yakunlash"}</span>
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ------------------------------------------------------------------- */}
        {/* MODAL 1: TOTP ENROLLMENT (API-060) */}
        {/* ------------------------------------------------------------------- */}
        {isEnrollModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="w-full max-w-lg rounded-2xl bg-[#121214] border border-white/[0.1] shadow-2xl p-6 space-y-5 text-xs">
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-primary" />
                  Ikki Bosqichli Autentifikatsiyani Yoqish (TOTP)
                </h3>
                <button
                  onClick={() => setIsEnrollModalOpen(false)}
                  className="text-zinc-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {!enrollSecret ? (
                /* Step 1: Password step-up verification */
                <form onSubmit={handleStartTotpEnrollment} className="space-y-4">
                  <p className="text-zinc-300">
                    Xavfsizlik yuzasidan ikki bosqichli autentifikatsiyani yoqishdan avval joriy maxfiy so‘zingizni (parol) tasdiqlashingiz shart:
                  </p>
                  <div>
                    <label className="block text-[11px] font-semibold text-zinc-400 mb-1">
                      Joriy Parol *
                    </label>
                    <input
                      type="password"
                      required
                      value={enrollPassword}
                      onChange={(e) => setEnrollPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-white text-xs focus:outline-none focus:border-primary"
                    />
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
                    <button
                      type="button"
                      onClick={() => setIsEnrollModalOpen(false)}
                      className="px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-semibold"
                    >
                      Bekor qilish
                    </button>
                    <button
                      type="submit"
                      disabled={isEnrolling}
                      className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-white font-semibold flex items-center gap-1.5 shadow-md shadow-primary/20"
                    >
                      {isEnrolling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowRight className="w-3.5 h-3.5" />}
                      <span>Davom etish</span>
                    </button>
                  </div>
                </form>
              ) : (
                /* Step 2: Show Secret Key & Enter 6-digit confirmation code */
                <form onSubmit={handleConfirmTotp} className="space-y-4">
                  <div className="space-y-2">
                    <p className="text-zinc-300">
                      1. Authenticator ilovangizni (Google Authenticator, Microsoft Authenticator yoki 1Password) oching.
                    </p>
                    <p className="text-zinc-300">
                      2. Yangi hisob qo‘shishni tanlang va quyidagi maxfiy kalitni kiriting:
                    </p>
                  </div>

                  <div className="p-3 rounded-lg bg-[#18181b] border border-white/[0.1] flex items-center justify-between gap-2">
                    <span className="font-mono text-primary font-bold tracking-wider text-sm select-all">
                      {enrollSecret}
                    </span>
                    <button
                      type="button"
                      onClick={() => copySecretToClipboard(enrollSecret)}
                      className="px-2.5 py-1 rounded bg-white/[0.06] hover:bg-white/[0.1] text-zinc-200 text-[11px] font-semibold flex items-center gap-1 transition shrink-0"
                    >
                      {copiedSecret ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedSecret ? "Nusxalandi" : "Nusxa olish"}</span>
                    </button>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-zinc-400 mb-1">
                      3. Ilovadagi 6 xonali tasdiqlash kodini kiriting *
                    </label>
                    <input
                      type="text"
                      required
                      maxLength={6}
                      value={confirmationCode}
                      onChange={(e) => setConfirmationCode(e.target.value.replace(/\D/g, ""))}
                      placeholder="123456"
                      className="w-full px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-white text-base font-mono tracking-widest text-center focus:outline-none focus:border-primary"
                    />
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
                    <button
                      type="button"
                      onClick={() => setIsEnrollModalOpen(false)}
                      className="px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-semibold"
                    >
                      Bekor qilish
                    </button>
                    <button
                      type="submit"
                      disabled={isConfirming || confirmationCode.length !== 6}
                      className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold flex items-center gap-1.5 shadow-md shadow-emerald-600/20 disabled:opacity-50"
                    >
                      {isConfirming ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                      <span>Tasdiqlash & Yoqish</span>
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------- */}
        {/* MODAL 2: TOTP DISABLE MODAL */}
        {/* ------------------------------------------------------------------- */}
        {isDisableModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="w-full max-w-md rounded-2xl bg-[#121214] border border-white/[0.1] shadow-2xl p-6 space-y-4 text-xs">
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                <h3 className="text-sm font-semibold text-rose-400 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                  MFA Himoyasini O‘chirish
                </h3>
                <button
                  onClick={() => setIsDisableModalOpen(false)}
                  className="text-zinc-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <p className="text-zinc-300">
                Ikki bosqichli himoyani o‘chirish hisobingiz xavfsizlik darajasini pasaytiradi.
                Amalni tasdiqlash uchun parolingizni kiriting:
              </p>

              <form onSubmit={handleDisableTotp} className="space-y-4">
                <div>
                  <label className="block text-[11px] font-semibold text-zinc-400 mb-1">
                    Joriy Parol *
                  </label>
                  <input
                    type="password"
                    required
                    value={disablePassword}
                    onChange={(e) => setDisablePassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-white text-xs focus:outline-none focus:border-rose-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-zinc-400 mb-1">
                    Joriy 6 xonali TOTP kodi (agar faol bo‘lsa)
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    value={disableTotpCode}
                    onChange={(e) => setDisableTotpCode(e.target.value.replace(/\D/g, ""))}
                    placeholder="123456"
                    className="w-full px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-white text-xs font-mono focus:outline-none focus:border-rose-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
                  <button
                    type="button"
                    onClick={() => setIsDisableModalOpen(false)}
                    className="px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-semibold"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="submit"
                    disabled={isDisabling}
                    className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold flex items-center gap-1.5 shadow-md shadow-rose-600/20"
                  >
                    {isDisabling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <LogOut className="w-3.5 h-3.5" />}
                    <span>O‘chirishni Tasdiqlash</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------- */}
        {/* MODAL 3: EMERGENCY RECOVERY CODES GENERATION */}
        {/* ------------------------------------------------------------------- */}
        {isRecoveryModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="w-full max-w-lg rounded-2xl bg-[#121214] border border-white/[0.1] shadow-2xl p-6 space-y-4 text-xs">
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <KeyRound className="w-4 h-4 text-amber-400" />
                  Favqulodda Zaxira Tiklash Kodlari
                </h3>
                <button
                  onClick={() => setIsRecoveryModalOpen(false)}
                  className="text-zinc-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {!generatedCodes ? (
                <form onSubmit={handleGenerateRecoveryCodes} className="space-y-4">
                  <p className="text-zinc-300">
                    Zaxira kodlarini yaratish uchun hisob parolingizni tasdiqlang:
                  </p>
                  <div>
                    <label className="block text-[11px] font-semibold text-zinc-400 mb-1">
                      Joriy Parol *
                    </label>
                    <input
                      type="password"
                      required
                      value={recoveryPassword}
                      onChange={(e) => setRecoveryPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-white text-xs focus:outline-none focus:border-amber-500"
                    />
                  </div>

                  {securityData?.totp_enabled && (
                    <div>
                      <label className="block text-[11px] font-semibold text-zinc-400 mb-1">
                        Joriy 6 xonali TOTP kodi
                      </label>
                      <input
                        type="text"
                        maxLength={6}
                        value={recoveryTotpCode}
                        onChange={(e) => setRecoveryTotpCode(e.target.value.replace(/\D/g, ""))}
                        placeholder="123456"
                        className="w-full px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-white text-xs font-mono focus:outline-none focus:border-amber-500"
                      />
                    </div>
                  )}

                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
                    <button
                      type="button"
                      onClick={() => setIsRecoveryModalOpen(false)}
                      className="px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-semibold"
                    >
                      Bekor qilish
                    </button>
                    <button
                      type="submit"
                      disabled={isGeneratingRecovery}
                      className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold flex items-center gap-1.5 shadow-md shadow-amber-600/20"
                    >
                      {isGeneratingRecovery ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                      <span>Kodlarni Yaratish</span>
                    </button>
                  </div>
                </form>
              ) : (
                <div className="space-y-4">
                  <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px]">
                    Diqqat! Ushbu kodlar faqat bitta marta ko‘rsatiladi. Kodlarni nusxalab oling yoki fayl sifatida yuklab oling.
                  </div>

                  <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-[#18181b] border border-white/[0.08]">
                    {generatedCodes.map((code, index) => (
                      <div
                        key={index}
                        className="font-mono text-[11px] text-zinc-200 bg-black/40 px-2.5 py-1.5 rounded border border-white/[0.04] text-center select-all"
                      >
                        {code}
                      </div>
                    ))}
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/[0.08]">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleCopyCodes}
                        className="px-3 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-zinc-200 text-xs font-semibold flex items-center gap-1.5 transition"
                      >
                        {copiedCodes ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedCodes ? "Nusxalandi" : "Nusxa Olish"}</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleDownloadCodes}
                        className="px-3 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-zinc-200 text-xs font-semibold flex items-center gap-1.5 transition"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Fayl sifatida yuklash</span>
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={() => setIsRecoveryModalOpen(false)}
                      className="px-4 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-white font-semibold"
                    >
                      Tayyor
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
