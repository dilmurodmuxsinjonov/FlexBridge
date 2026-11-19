"use client";

import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { describeRequestError } from "@/lib/errors";
import { useAsyncData } from "@/lib/useAsyncData";
import {
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
  AuthUser,
  fetchAuthMe,
  fetchUserSecurityOverview,
  requestTotpEnrollment,
  confirmTotpEnrollment,
  disableTotp,
  generateRecoveryCodes,
  revokeUserSession,
  UserSecurityOverview,
  ActiveSessionItem,
} from "@/lib/api";
import { resolvePortalDashboard } from "@/lib/roles";
import { SkeuoStatCard } from "@/components/skeuo/SkeuoPrimitives";
import AccountProfileAndPasswordPanel from "@/components/security/AccountProfileAndPasswordPanel";
import PasskeysPanel from "@/components/security/PasskeysPanel";
import ContactsPanel from "@/components/security/ContactsPanel";

export interface AccountSecurityWorkspaceProps {
  mode: "universal" | "candidate";
}

export default function AccountSecurityWorkspace({ mode }: AccountSecurityWorkspaceProps) {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authLoaded, setAuthLoaded] = useState(false);
  const [displayNameOverride, setDisplayNameOverride] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const syncAuth = () => {
      void fetchAuthMe().then((user) => {
        if (!active) return;
        setCurrentUser(user);
        setDisplayNameOverride(null);
        setAuthLoaded(true);
      });
    };
    syncAuth();
    window.addEventListener("flexbridge:auth-changed", syncAuth);
    return () => {
      active = false;
      window.removeEventListener("flexbridge:auth-changed", syncAuth);
    };
  }, []);

  const overview = useAsyncData<UserSecurityOverview>("security-overview", fetchUserSecurityOverview);
  const securityData = overview.data ?? null;
  const isLoading = overview.isLoading;
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const displayedError =
    errorMessage ??
    (overview.error
      ? describeRequestError(overview.error, "Xavfsizlik ma'lumotlarini yuklashda xatolik yuz berdi.")
      : null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // TOTP Enrollment Modal State
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [enrollPassword, setEnrollPassword] = useState("");
  const [enrollStepUpTotp, setEnrollStepUpTotp] = useState("");
  const [isEnrolling, setIsEnrolling] = useState(false);
  const [enrollSecret, setEnrollSecret] = useState<string | null>(null);
  const [confirmationCode, setConfirmationCode] = useState("");
  const [isConfirming, setIsConfirming] = useState(false);
  const [copiedSecret, setCopiedSecret] = useState(false);

  // TOTP Disable Modal State
  const [isDisableModalOpen, setIsDisableModalOpen] = useState(false);
  const [disablePassword, setDisablePassword] = useState("");
  const [disableTotpCode, setDisableTotpCode] = useState("");
  const [isDisabling, setIsDisabling] = useState(false);

  // Recovery Codes Modal State
  const [isRecoveryModalOpen, setIsRecoveryModalOpen] = useState(false);
  const [recoveryPassword, setRecoveryPassword] = useState("");
  const [recoveryTotpCode, setRecoveryTotpCode] = useState("");
  const [isGeneratingRecovery, setIsGeneratingRecovery] = useState(false);
  const [generatedCodes, setGeneratedCodes] = useState<string[] | null>(null);
  const [copiedCodes, setCopiedCodes] = useState(false);

  // Session Revocation State
  const [revokingSessionId, setRevokingSessionId] = useState<string | null>(null);

  const reloadOverview = overview.reload;
  const loadSecurityOverview = useCallback(async () => {
    setErrorMessage(null);
    await reloadOverview();
  }, [reloadOverview]);

  const dashboard = currentUser ? resolvePortalDashboard(currentUser.roles) : { href: "/nomzod", label: "Kabinet" };
  const resolvedDisplayName = displayNameOverride ?? currentUser?.display_name ?? "";

  if (mode === "universal" && authLoaded && !currentUser) {
    return (
      <div className="skeuo-card rounded-2xl p-6 md:p-8 space-y-5 text-center max-w-xl mx-auto my-8">
        <div className="w-12 h-12 rounded-2xl skeuo-well mx-auto flex items-center justify-center">
          <Lock className="w-6 h-6 text-[var(--fb-accent)]" aria-hidden="true" />
        </div>
        <div className="space-y-1.5">
          <h1 className="text-xl font-bold text-[var(--fb-ink)]">Hisobingizga kiring</h1>
          <p className="text-xs text-[var(--fb-ink-secondary)]">
            Ism, parol, kirish kontaktlari (telefon/e-pochta), 2FA va faol qurilmalarni boshqarish uchun avval tizimga kiring.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
          <Link href="/talaba/kirish" className="skeuo-btn-obsidian rounded-xl px-4 py-2.5 font-semibold">
            Talaba / Nomzod kirishi
          </Link>
          <Link href="/korxona/kirish" className="skeuo-btn-secondary rounded-xl px-4 py-2.5 font-semibold">
            Korxona HR kirishi
          </Link>
          <Link href="/universitet/kirish" className="skeuo-btn-secondary rounded-xl px-4 py-2.5 font-semibold">
            OTM Dekanat kirishi
          </Link>
          <Link href="/operator/kirish" className="skeuo-btn-secondary rounded-xl px-4 py-2.5 font-semibold">
            Operator SOC kirishi
          </Link>
        </div>
      </div>
    );
  }

  // TOTP Handlers
  const handleStartTotpEnrollment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!enrollPassword.trim()) {
      setErrorMessage("Joriy maxfiy so‘zni kiritishingiz shart.");
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
        err instanceof Error ? err.message : "TOTP kodini tasdiqlashda xatolik yuz berdi. Kod to‘g‘riligini tekshiring."
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
      setSuccessMessage("Ikki bosqichli autentifikatsiya muvaffaqiyatli o‘chirildi.");
      setIsDisableModalOpen(false);
      setDisablePassword("");
      setDisableTotpCode("");
      await loadSecurityOverview();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "TOTP ni o‘chirishda xatolik yuz berdi.");
    } finally {
      setIsDisabling(false);
    }
  };

  // Recovery Codes Handlers
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
      setErrorMessage(err instanceof Error ? err.message : "Zaxira kodlarini yaratishda xatolik yuz berdi.");
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
    const content = `FLEXBRIDGE FAVQULODDA ZAXIRA KODLARI\nYaratilgan vaqt: ${new Date().toISOString()}\n\nHar bir kod faqat bir marta ishlatiladi:\n\n${generatedCodes
      .map((c, i) => `${i + 1}. ${c}`)
      .join("\n")}\n\nEslatma: Ushbu kodlarni xavfsiz joyda saqlang.`;
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `flexbridge-recovery-codes-${new Date().toISOString().slice(0, 10)}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

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
        window.dispatchEvent(new Event("flexbridge:auth-changed"));
        router.push("/");
        router.refresh();
        return;
      }
      setSuccessMessage("Sessiya muvaffaqiyatli yakunlandi.");
      await loadSecurityOverview();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Sessiyani yakunlashda xatolik yuz berdi.");
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
    <div className="w-full text-[var(--fb-ink)]">
      <div className="w-full space-y-6">
        {/* Breadcrumb */}
        <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--fb-ink-muted)]">
          <Link
            href={mode === "candidate" ? "/nomzod" : dashboard.href}
            className="hover:text-[var(--fb-ink)] transition flex items-center gap-1"
          >
            <User className="w-3.5 h-3.5" aria-hidden="true" />
            <span>{mode === "candidate" ? "Nomzod Kabineti" : dashboard.label}</span>
          </Link>
          <span>/</span>
          <span className="text-[var(--fb-ink)] font-medium">Hisob &amp; Xavfsizlik</span>
        </div>

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="fb-display">Hisob va xavfsizlik</h1>
            <p className="text-xs text-[var(--fb-ink-secondary)] mt-1">
              Akkaunt nomi, kirish paroli, asosiy telefon/e-pochta, ikki bosqichli autentifikatsiya (2FA), Passkey va faol qurilmalarni boshqarish.
            </p>
          </div>
          <button
            type="button"
            onClick={loadSecurityOverview}
            disabled={isLoading}
            className="px-3.5 py-2 text-xs font-semibold rounded-xl skeuo-btn-secondary flex items-center gap-2 self-start md:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[var(--fb-ink-muted)] ${isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
            Yangilash
          </button>
        </div>

        {displayedError && (
          <div
            role="alert"
            className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/25 text-rose-700 dark:text-rose-300 text-xs flex items-center justify-between gap-2"
          >
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{displayedError}</span>
            </div>
            <button type="button" onClick={() => setErrorMessage(null)} aria-label="Xatoni yopish">
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        )}

        {successMessage && (
          <div
            role="status"
            className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-700 dark:text-emerald-300 text-xs flex items-center justify-between gap-2"
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{successMessage}</span>
            </div>
            <button type="button" onClick={() => setSuccessMessage(null)} aria-label="Xabarni yopish">
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        )}

        {/* Section 0: Name, Roles & Password */}
        <AccountProfileAndPasswordPanel
          displayName={resolvedDisplayName}
          roles={currentUser?.roles ?? []}
          totpEnabled={Boolean(securityData?.totp_enabled)}
          onDisplayNameUpdated={(nextName) => {
            setDisplayNameOverride(nextName);
            setCurrentUser((prev) => (prev ? { ...prev, display_name: nextName } : prev));
          }}
          onPasswordChanged={loadSecurityOverview}
        />

        {/* Telemetry Cards */}
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
            value={securityData?.totp_enabled ? "Yuqori" : "Oddiy"}
            subtitle={securityData?.totp_enabled ? "Parol + bir martalik kod" : "Faqat parol"}
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

        {/* Verified Contacts (phone/email, primary switch, safe delete) */}
        <ContactsPanel totpEnabled={Boolean(securityData?.totp_enabled)} />

        {/* TOTP Two-Factor Authentication */}
        <div className="skeuo-card p-5 md:p-6 rounded-2xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--fb-border)] pb-4">
            <div>
              <h2 className="text-base font-semibold text-[var(--fb-ink)] flex items-center gap-2">
                <Smartphone className="w-5 h-5 text-[var(--fb-accent)]" aria-hidden="true" />
                Ikki Bosqichli Autentifikatsiya (2FA / TOTP)
              </h2>
              <p className="text-xs text-[var(--fb-ink-secondary)] mt-1">
                Google Authenticator, Microsoft Authenticator yoki 1Password orqali bir martalik 6 xonali dinamik xavfsizlik kodlari.
              </p>
            </div>
            {securityData?.totp_enabled ? (
              <button
                type="button"
                onClick={() => setIsDisableModalOpen(true)}
                className="px-3.5 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-700 dark:text-rose-300 border border-rose-500/25 text-xs font-semibold flex items-center gap-1.5 transition self-start sm:self-auto"
              >
                <LogOut className="w-3.5 h-3.5" aria-hidden="true" />
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
                <ShieldCheck className="w-4 h-4" aria-hidden="true" />
                <span>2FA Himoyasini Yoqish</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
            <div className="skeuo-well p-4 rounded-xl space-y-1">
              <span className="text-[11px] font-semibold text-[var(--fb-ink-muted)] uppercase tracking-wider">Holat</span>
              <p className="text-sm font-medium text-[var(--fb-ink)] flex items-center gap-2">
                {securityData?.totp_enabled ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" aria-hidden="true" />
                    <span className="text-emerald-700 dark:text-emerald-300">Hisobingiz 2FA bilan himoyalangan</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" aria-hidden="true" />
                    <span className="text-amber-700 dark:text-amber-300">Faqat oddiy parol bilan himoyalangan</span>
                  </>
                )}
              </p>
            </div>
            <div className="skeuo-well p-4 rounded-xl space-y-1">
              <span className="text-[11px] font-semibold text-[var(--fb-ink-muted)]">Qaysi ilova</span>
              <p className="text-sm font-medium text-[var(--fb-ink)]">
                Google Authenticator, Microsoft Authenticator va shu kabi ilovalar (kod har 30 soniyada yangilanadi)
              </p>
            </div>
            <div className="skeuo-well p-4 rounded-xl space-y-1">
              <span className="text-[11px] font-semibold text-[var(--fb-ink-muted)]">Nimani himoya qiladi</span>
              <p className="text-sm font-medium text-[var(--fb-ink)]">Kirish, parolni tiklash va muhim amallar</p>
            </div>
          </div>
        </div>

        {/* Recovery Codes */}
        <div className="skeuo-card p-5 md:p-6 rounded-2xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--fb-border)] pb-4">
            <div>
              <h2 className="text-base font-semibold text-[var(--fb-ink)] flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-amber-500" aria-hidden="true" />
                Zaxira tiklash kodlari
              </h2>
              <p className="text-xs text-[var(--fb-ink-secondary)] mt-1">
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
              className="skeuo-btn-secondary px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 self-start sm:self-auto"
            >
              <RefreshCw className="w-3.5 h-3.5 text-amber-500" aria-hidden="true" />
              <span>Yangi Zaxira Kodlari Yaratish</span>
            </button>
          </div>

          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-800 dark:text-amber-200 flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-500" aria-hidden="true" />
            <p className="leading-relaxed">
              Zaxira kodlari har safar qayta yaratilganda, avvalgi barcha faol kodlar avtomatik ravishda bekor qilinadi.
              Har bir kod faqat bir marta ishlatilishi mumkin. Kodlarni chop etib yoki shifrlangan faylda xavfsiz saqlang.
            </p>
          </div>
        </div>

        {/* Passkeys */}
        <PasskeysPanel
          passkeys={securityData?.passkeys ?? []}
          totpEnabled={Boolean(securityData?.totp_enabled)}
          onUpdated={loadSecurityOverview}
        />

        {/* Active Sessions & Devices */}
        <div className="skeuo-card p-5 md:p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--fb-border)] pb-4">
            <div>
              <h2 className="text-base font-semibold text-[var(--fb-ink)] flex items-center gap-2">
                <Laptop className="w-5 h-5 text-violet-500" aria-hidden="true" />
                Faol Qurilmalar &amp; Sessiyalar Boshqaruvi
              </h2>
              <p className="text-xs text-[var(--fb-ink-secondary)] mt-1">
                Hisobingizga kirilgan barcha faol sessiyalar ro‘yxati. Notanish yoki eski qurilmalarni istalgan vaqtda bekor qilishingiz mumkin.
              </p>
            </div>
          </div>

          {isLoading ? (
            <div className="p-12 text-center text-xs text-[var(--fb-ink-secondary)] flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-[var(--fb-accent)]" aria-hidden="true" />
              <span>Sessiyalar yuklanmoqda...</span>
            </div>
          ) : !securityData?.sessions || securityData.sessions.length === 0 ? (
            <div className="p-8 text-center text-xs text-[var(--fb-ink-muted)]">Faol sessiyalar topilmadi.</div>
          ) : (
            <div className="divide-y divide-[var(--fb-border)]">
              {securityData.sessions.map((session: ActiveSessionItem) => {
                const isCurrent = session.is_current;
                const isRevoking = revokingSessionId === session.id;

                return (
                  <div
                    key={session.id}
                    className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`p-2.5 rounded-xl border mt-0.5 ${
                          isCurrent
                            ? "bg-[var(--fb-accent)]/12 border-[var(--fb-accent)]/30 text-[var(--fb-accent)]"
                            : "skeuo-well text-[var(--fb-ink-muted)]"
                        }`}
                      >
                        <Laptop className="w-4 h-4" aria-hidden="true" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-[var(--fb-ink)] font-semibold text-[11px]">{session.id}</span>
                          {isCurrent && (
                            <span className="px-2 py-0.5 rounded-full bg-[var(--fb-accent)]/15 text-[var(--fb-accent)] border border-[var(--fb-accent)]/30 text-[10px] font-semibold">
                              Joriy Qurilma
                            </span>
                          )}
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                              session.assurance === "MFA"
                                ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300 border-emerald-500/25"
                                : "bg-amber-500/12 text-amber-700 dark:text-amber-300 border-amber-500/25"
                            }`}
                          >
                            {session.assurance === "MFA" ? "MFA bilan tasdiqlangan" : "Parol orqali kirilgan"}
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-3 text-[var(--fb-ink-muted)] text-[11px] mt-1 font-mono">
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
                      className="px-3 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-700 dark:text-rose-300 border border-rose-500/25 text-xs font-semibold flex items-center gap-1.5 transition self-start sm:self-auto shrink-0"
                    >
                      {isRevoking ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                      ) : (
                        <LogOut className="w-3.5 h-3.5" aria-hidden="true" />
                      )}
                      <span>{isCurrent ? "Chiqish (Logout)" : "Sessiyani Yakunlash"}</span>
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* MODAL 1: TOTP ENROLLMENT */}
        {isEnrollModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div role="dialog" aria-modal="true" className="skeuo-card w-full max-w-lg rounded-2xl p-6 space-y-5 text-xs">
              <div className="flex items-center justify-between border-b border-[var(--fb-border)] pb-3">
                <h3 className="text-sm font-semibold text-[var(--fb-ink)] flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-[var(--fb-accent)]" aria-hidden="true" />
                  Ikki Bosqichli Autentifikatsiyani Yoqish (TOTP)
                </h3>
                <button
                  type="button"
                  onClick={() => setIsEnrollModalOpen(false)}
                  aria-label="Modalni yopish"
                  className="text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)]"
                >
                  <X className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>

              {!enrollSecret ? (
                <form onSubmit={handleStartTotpEnrollment} className="space-y-4">
                  <p className="text-[var(--fb-ink-secondary)]">
                    Xavfsizlik yuzasidan ikki bosqichli autentifikatsiyani yoqishdan avval joriy maxfiy so‘zingizni (parol) tasdiqlashingiz shart:
                  </p>
                  <div>
                    <label className="block text-[11px] font-semibold text-[var(--fb-ink-secondary)] mb-1">
                      Joriy Parol *
                    </label>
                    <input
                      type="password"
                      required
                      value={enrollPassword}
                      onChange={(e) => setEnrollPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="skeuo-input w-full px-3.5 py-2 rounded-xl text-xs"
                    />
                  </div>
                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--fb-border)]">
                    <button
                      type="button"
                      onClick={() => setIsEnrollModalOpen(false)}
                      className="skeuo-btn-secondary px-3 py-2 rounded-xl font-semibold"
                    >
                      Bekor qilish
                    </button>
                    <button
                      type="submit"
                      disabled={isEnrolling}
                      className="skeuo-btn-obsidian px-4 py-2 rounded-xl font-semibold flex items-center gap-1.5"
                    >
                      {isEnrolling ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />}
                      <span>Davom etish</span>
                    </button>
                  </div>
                </form>
              ) : (
                <form onSubmit={handleConfirmTotp} className="space-y-4">
                  <div className="space-y-2 text-[var(--fb-ink-secondary)]">
                    <p>1. Authenticator ilovangizni (Google Authenticator, Microsoft Authenticator yoki 1Password) oching.</p>
                    <p>2. Yangi hisob qo‘shishni tanlang va quyidagi maxfiy kalitni kiriting:</p>
                  </div>

                  <div className="skeuo-well p-3 rounded-xl flex items-center justify-between gap-2">
                    <span className="font-mono text-[var(--fb-accent)] font-bold tracking-wider text-sm select-all">
                      {enrollSecret}
                    </span>
                    <button
                      type="button"
                      onClick={() => copySecretToClipboard(enrollSecret)}
                      className="skeuo-btn-secondary px-2.5 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1 shrink-0"
                    >
                      {copiedSecret ? <Check className="w-3 h-3 text-emerald-500" aria-hidden="true" /> : <Copy className="w-3 h-3" aria-hidden="true" />}
                      <span>{copiedSecret ? "Nusxalandi" : "Nusxa olish"}</span>
                    </button>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-[var(--fb-ink-secondary)] mb-1">
                      3. Ilovadagi 6 xonali tasdiqlash kodini kiriting *
                    </label>
                    <input
                      type="text"
                      required
                      maxLength={6}
                      value={confirmationCode}
                      onChange={(e) => setConfirmationCode(e.target.value.replace(/\D/g, ""))}
                      placeholder="123456"
                      className="skeuo-input w-full px-3.5 py-2 rounded-xl text-base font-mono tracking-widest text-center"
                    />
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--fb-border)]">
                    <button
                      type="button"
                      onClick={() => setIsEnrollModalOpen(false)}
                      className="skeuo-btn-secondary px-3 py-2 rounded-xl font-semibold"
                    >
                      Bekor qilish
                    </button>
                    <button
                      type="submit"
                      disabled={isConfirming || confirmationCode.length !== 6}
                      className="skeuo-btn-accent px-4 py-2 rounded-xl font-semibold flex items-center gap-1.5 disabled:opacity-50"
                    >
                      {isConfirming ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />}
                      <span>Tasdiqlash &amp; Yoqish</span>
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

        {/* MODAL 2: TOTP DISABLE */}
        {isDisableModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div role="dialog" aria-modal="true" className="skeuo-card w-full max-w-md rounded-2xl p-6 space-y-4 text-xs">
              <div className="flex items-center justify-between border-b border-[var(--fb-border)] pb-3">
                <h3 className="text-sm font-semibold text-rose-600 dark:text-rose-400 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" aria-hidden="true" />
                  MFA Himoyasini O‘chirish
                </h3>
                <button
                  type="button"
                  onClick={() => setIsDisableModalOpen(false)}
                  aria-label="Modalni yopish"
                  className="text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)]"
                >
                  <X className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>

              <p className="text-[var(--fb-ink-secondary)]">
                Ikki bosqichli himoyani o‘chirish hisobingiz xavfsizlik darajasini pasaytiradi. Amalni tasdiqlash uchun parolingizni kiriting:
              </p>

              <form onSubmit={handleDisableTotp} className="space-y-4">
                <div>
                  <label className="block text-[11px] font-semibold text-[var(--fb-ink-secondary)] mb-1">
                    Joriy Parol *
                  </label>
                  <input
                    type="password"
                    required
                    value={disablePassword}
                    onChange={(e) => setDisablePassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="skeuo-input w-full px-3.5 py-2 rounded-xl text-xs"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-[var(--fb-ink-secondary)] mb-1">
                    Joriy 6 xonali TOTP kodi (agar faol bo‘lsa)
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    value={disableTotpCode}
                    onChange={(e) => setDisableTotpCode(e.target.value.replace(/\D/g, ""))}
                    placeholder="123456"
                    className="skeuo-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
                  />
                </div>
                <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--fb-border)]">
                  <button
                    type="button"
                    onClick={() => setIsDisableModalOpen(false)}
                    className="skeuo-btn-secondary px-3 py-2 rounded-xl font-semibold"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="submit"
                    disabled={isDisabling}
                    className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold flex items-center gap-1.5"
                  >
                    {isDisabling ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <LogOut className="w-3.5 h-3.5" aria-hidden="true" />}
                    <span>O‘chirishni Tasdiqlash</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL 3: RECOVERY CODES */}
        {isRecoveryModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div role="dialog" aria-modal="true" className="skeuo-card w-full max-w-lg rounded-2xl p-6 space-y-4 text-xs">
              <div className="flex items-center justify-between border-b border-[var(--fb-border)] pb-3">
                <h3 className="text-sm font-semibold text-[var(--fb-ink)] flex items-center gap-2">
                  <KeyRound className="w-4 h-4 text-amber-500" aria-hidden="true" />
                  Favqulodda Zaxira Tiklash Kodlari
                </h3>
                <button
                  type="button"
                  onClick={() => setIsRecoveryModalOpen(false)}
                  aria-label="Modalni yopish"
                  className="text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)]"
                >
                  <X className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>

              {!generatedCodes ? (
                <form onSubmit={handleGenerateRecoveryCodes} className="space-y-4">
                  <p className="text-[var(--fb-ink-secondary)]">Zaxira kodlarini yaratish uchun hisob parolingizni tasdiqlang:</p>
                  <div>
                    <label className="block text-[11px] font-semibold text-[var(--fb-ink-secondary)] mb-1">
                      Joriy Parol *
                    </label>
                    <input
                      type="password"
                      required
                      value={recoveryPassword}
                      onChange={(e) => setRecoveryPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="skeuo-input w-full px-3.5 py-2 rounded-xl text-xs"
                    />
                  </div>
                  {securityData?.totp_enabled && (
                    <div>
                      <label className="block text-[11px] font-semibold text-[var(--fb-ink-secondary)] mb-1">
                        Joriy 6 xonali TOTP kodi
                      </label>
                      <input
                        type="text"
                        maxLength={6}
                        value={recoveryTotpCode}
                        onChange={(e) => setRecoveryTotpCode(e.target.value.replace(/\D/g, ""))}
                        placeholder="123456"
                        className="skeuo-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
                      />
                    </div>
                  )}
                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--fb-border)]">
                    <button
                      type="button"
                      onClick={() => setIsRecoveryModalOpen(false)}
                      className="skeuo-btn-secondary px-3 py-2 rounded-xl font-semibold"
                    >
                      Bekor qilish
                    </button>
                    <button
                      type="submit"
                      disabled={isGeneratingRecovery}
                      className="skeuo-btn-obsidian px-4 py-2 rounded-xl font-semibold flex items-center gap-1.5"
                    >
                      {isGeneratingRecovery ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />}
                      <span>Kodlarni Yaratish</span>
                    </button>
                  </div>
                </form>
              ) : (
                <div className="space-y-4">
                  <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-200 text-[11px]">
                    Diqqat! Ushbu kodlar faqat bitta marta ko‘rsatiladi. Kodlarni nusxalab oling yoki fayl sifatida yuklab oling.
                  </div>
                  <div className="skeuo-well grid grid-cols-2 gap-2 p-3 rounded-xl">
                    {generatedCodes.map((code, index) => (
                      <div
                        key={index}
                        className="font-mono text-[11px] text-[var(--fb-ink)] px-2.5 py-1.5 rounded-lg border border-[var(--fb-border)] text-center select-all"
                      >
                        {code}
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[var(--fb-border)]">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleCopyCodes}
                        className="skeuo-btn-secondary px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5"
                      >
                        {copiedCodes ? <Check className="w-3.5 h-3.5 text-emerald-500" aria-hidden="true" /> : <Copy className="w-3.5 h-3.5" aria-hidden="true" />}
                        <span>{copiedCodes ? "Nusxalandi" : "Nusxa Olish"}</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleDownloadCodes}
                        className="skeuo-btn-secondary px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5"
                      >
                        <Download className="w-3.5 h-3.5" aria-hidden="true" />
                        <span>Fayl sifatida yuklash</span>
                      </button>
                    </div>
                    <button
                      type="button"
                      onClick={() => setIsRecoveryModalOpen(false)}
                      className="skeuo-btn-obsidian px-4 py-1.5 rounded-xl font-semibold"
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
