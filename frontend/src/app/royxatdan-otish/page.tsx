"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { errorText } from "@/lib/errorText";
import Link from "next/link";
import TelegramVerification, { type TelegramMode } from "@/components/TelegramVerification";
import { useRouter, useSearchParams } from "next/navigation";
import {
  GraduationCap,
  Building2,
  School,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  ArrowLeft,
  Smartphone,
  Eye,
  EyeOff,
  Shield,
  KeyRound,
  User,
  Send,
  MessageSquare,
} from "lucide-react";
import {
  fetchAuthOptions,
  issueAuthChallenge,
  fetchAuthChallengeStatus,
  consumeAuthChallenge,
  registerCandidateUser,
  fetchAuthMe,
} from "@/lib/api";
import { isOperatorRoles, resolvePortalDashboard } from "@/lib/roles";

type RoleOption = "CANDIDATE" | "EMPLOYER" | "ACADEMIC" | "OPERATOR";
type DeliveryMethodOption = "SMS" | "TELEGRAM";

interface InvitePreview {
  organization_id: string;
  organization_name?: string;
  role_code: string;
  channel: string;
  masked_destination: string;
  expires_at: string;
  status: string;
}

interface PendingAppointmentItem {
  id: string;
  institution_id: string;
  status: string;
  case_status: string;
  current_revision: number;
}

interface VerifiedContactItem {
  id: string;
  channel: string;
  masked_destination: string;
  is_primary: boolean;
}

function normalizeRoleParam(param: string | null): RoleOption {
  if (!param) return "CANDIDATE";
  const upper = param.trim().toUpperCase();
  if (upper === "EMPLOYER" || upper === "ORGANIZATION" || upper === "HR") return "EMPLOYER";
  if (upper === "ACADEMIC" || upper === "UNIVERSITY" || upper === "TEACHER" || upper === "COORDINATOR") {
    return "ACADEMIC";
  }
  if (upper === "OPERATOR" || upper === "MODERATOR" || upper === "AUDITOR" || upper === "SOC") {
    return "OPERATOR";
  }
  return "CANDIDATE";
}

function RoyxatdanOtishWizard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const roleParam = searchParams.get("role");
  const inviteParam = searchParams.get("invite") || "";

  // Wizard Step: 1 = Role, 2 = Contact & OTP, 3 = Profile & Password, 4 = Role Activation
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [selectedRole, setSelectedRole] = useState<RoleOption>(() => normalizeRoleParam(roleParam));
  const [inviteToken, setInviteToken] = useState(inviteParam);
  const [invitePreview, setInvitePreview] = useState<InvitePreview | null>(null);
  const [pendingAppointments, setPendingAppointments] = useState<PendingAppointmentItem[]>([]);
  const [verifiedContacts, setVerifiedContacts] = useState<VerifiedContactItem[]>([]);
  const [activationBusy, setActivationBusy] = useState(false);

  useEffect(() => {
    if (!roleParam) return;
    const mapped = normalizeRoleParam(roleParam);
    const id = setTimeout(() => setSelectedRole(mapped), 0);
    return () => clearTimeout(id);
  }, [roleParam]);

  // Step 2 State
  const [channel] = useState<"PHONE" | "EMAIL">("PHONE");
  const [deliveryMethod, setDeliveryMethod] = useState<DeliveryMethodOption>("SMS");
  const [phone, setPhone] = useState("+998");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [verificationToken, setVerificationToken] = useState<string | null>(null);
  const [resendTimer, setResendTimer] = useState(0);

  // Telegram Bot Verification State
  const [telegramBotUsername, setTelegramBotUsername] = useState("FlexBridgeAuthBot");
  const [telegramMode, setTelegramMode] = useState<TelegramMode>("LIVE");
  const [telegramDeepLink, setTelegramDeepLink] = useState<string | null>(null);
  const [telegramVerified, setTelegramVerified] = useState(false);

  // Step 3 State
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [adultConfirmed, setAdultConfirmed] = useState(false);
  const [termsAgreed, setTermsAgreed] = useState(false);

  // Policy versions from backend
  const [termsVersion, setTermsVersion] = useState("2026.1");
  const [privacyVersion, setPrivacyVersion] = useState("2026.1");

  // General Status State
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load auth options & check existing session
  useEffect(() => {
    let isMounted = true;
    fetchAuthOptions()
      .then((opts) => {
        if (isMounted && opts) {
          if (opts.terms_version) setTermsVersion(opts.terms_version);
          if (opts.privacy_version) setPrivacyVersion(opts.privacy_version);
          if (opts.telegram_bot_username) setTelegramBotUsername(opts.telegram_bot_username);
        if (opts.telegram_mode) setTelegramMode(opts.telegram_mode);
        }
      })
      .catch(() => {});

    fetchAuthMe().then((user) => {
      if (isMounted && user) {
        const dash = resolvePortalDashboard(user.roles);
        router.push(dash.href);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [router]);

  const loadAppointmentInbox = useCallback(async () => {
    setActivationBusy(true);
    try {
      const res = await fetch("/api/bff/university/appointments", { cache: "no-store" });
      const data = await res.json();
      if (res.ok && data.ok) {
        setPendingAppointments(Array.isArray(data.items) ? data.items : []);
        setVerifiedContacts(Array.isArray(data.contacts) ? data.contacts : []);
      }
    } catch {
      // Non-fatal while polling/loading appointment inbox
    } finally {
      setActivationBusy(false);
    }
  }, []);

  const handlePreviewInvite = async () => {
    if (!inviteToken.trim()) {
      setErrorMessage("Korxona taklif tokenini kiriting.");
      return;
    }
    setActivationBusy(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`/api/bff/invitations/${encodeURIComponent(inviteToken.trim())}`, {
        cache: "no-store",
      });
      const data = await res.json();
      if (!res.ok) {
        setInvitePreview(null);
        setErrorMessage(errorText(data, "Taklif tokeni topilmadi yoki muddati o‘tgan."));
      } else {
        setInvitePreview(data as InvitePreview);
      }
    } catch {
      setErrorMessage("Taklifni tekshirishda tarmoq xatosi yuz berdi.");
    } finally {
      setActivationBusy(false);
    }
  };

  const handleAcceptInvite = async () => {
    if (!inviteToken.trim()) return;
    setActivationBusy(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const res = await fetch(`/api/bff/invitations/${encodeURIComponent(inviteToken.trim())}/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        if (data.error === "MFA_REQUIRED" || data.detail?.code === "MFA_REQUIRED") {
          setErrorMessage(
            "Korxona taklifini qabul qilish uchun avval 2FA (TOTP) ni yoqing va qayta tizimga kiring (/nomzod/xavfsizlik)."
          );
        } else {
          setErrorMessage(errorText(data, "Taklifni qabul qilib bo‘lmadi."));
        }
      } else {
        window.dispatchEvent(new Event("flexbridge:auth-changed"));
        const dash = resolvePortalDashboard(Array.isArray(data.roles) ? data.roles : ["HR"]);
        setSuccessMessage(`Korxona vakolati faollashtirildi! ${dash.label}ga yo‘naltirilmoqda...`);
        setTimeout(() => {
          router.push(dash.href);
          router.refresh();
        }, 450);
      }
    } catch {
      setErrorMessage("Taklifni qabul qilishda tarmoq xatosi yuz berdi.");
    } finally {
      setActivationBusy(false);
    }
  };

  const handleAppointmentConsent = async (appt: PendingAppointmentItem, decision: "ACCEPT" | "DECLINE") => {
    const contactId = verifiedContacts[0]?.id;
    if (decision === "ACCEPT" && !contactId) {
      setErrorMessage("Rozilik berish uchun tasdiqlangan telefon/email kontaktingiz topilmadi.");
      return;
    }
    setActivationBusy(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const res = await fetch(`/api/bff/university/appointments/${encodeURIComponent(appt.id)}/consent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expected_revision: appt.current_revision,
          decision,
          ...(decision === "ACCEPT" && contactId ? { contact_id: contactId } : {}),
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        setErrorMessage(errorText(data, "Tayinlov qarorini yuborib bo‘lmadi."));
        await loadAppointmentInbox();
      } else if (decision === "ACCEPT") {
        window.dispatchEvent(new Event("flexbridge:auth-changed"));
        const dash = resolvePortalDashboard(Array.isArray(data.roles) ? data.roles : ["TEACHER"]);
        setSuccessMessage(`OTM vakolatingiz faollashtirildi! ${dash.label}ga yo‘naltirilmoqda...`);
        setTimeout(() => {
          router.push(dash.href);
          router.refresh();
        }, 450);
      } else {
        setSuccessMessage("Tayinlov rad etildi.");
        await loadAppointmentInbox();
      }
    } catch {
      setErrorMessage("Tayinlov roziligini yuborishda tarmoq xatosi yuz berdi.");
    } finally {
      setActivationBusy(false);
    }
  };

  const handleRecheckOperatorRoles = async () => {
    setActivationBusy(true);
    setErrorMessage(null);
    try {
      const user = await fetchAuthMe();
      if (user && isOperatorRoles(user.roles)) {
        window.dispatchEvent(new Event("flexbridge:auth-changed"));
        router.push("/operator");
        router.refresh();
      } else {
        setErrorMessage(
          "Hozircha platforma granti (OPERATOR/MODERATOR/AUDITOR) faollashmagan. Vakolat tasdiqlangach /operator/kirish orqali kiring."
        );
      }
    } finally {
      setActivationBusy(false);
    }
  };

  // Resend Countdown
  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer(resendTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendTimer]);

  // Poll Telegram verification status while waiting for contact verification
  useEffect(() => {
    if (!challengeId || deliveryMethod !== "TELEGRAM" || telegramVerified) return;
    let active = true;
    const interval = setInterval(async () => {
      try {
        const status = await fetchAuthChallengeStatus(challengeId);
        if (active && status.telegram_verified) {
          setTelegramVerified(true);
        }
      } catch {
        // Ignore transient status polling error
      }
    }, 3000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [challengeId, deliveryMethod, telegramVerified]);

  // Step 2: Send OTP Challenge
  const handleSendChallenge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim() || phone.trim().length < 9) {
      setErrorMessage("To‘g‘ri telefon raqam kiriting (masalan: +998901234567)");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    setTelegramVerified(false);

    try {
      const res = await issueAuthChallenge(channel, phone.trim(), "REGISTER", deliveryMethod);
      if (res.ok && res.challenge_id) {
        setChallengeId(res.challenge_id);
        setResendTimer(res.resend_after || 60);
        if (res.telegram_bot_username) setTelegramBotUsername(res.telegram_bot_username);
        if (res.telegram_deep_link) setTelegramDeepLink(res.telegram_deep_link);

        if (deliveryMethod === "TELEGRAM") {
          setSuccessMessage(
            "Telegram tasdiqlash so‘rovi yaratildi! Endi botni ishga tushirib (/start), telefon raqamingizni yuboring."
          );
        } else {
          setSuccessMessage("Tasdiqlash kodi SMS orqali ko‘rsatilgan telefon raqamga yuborildi.");
        }
      } else {
        setErrorMessage("Tasdiqlash kodini yuborishda xatolik yuz berdi.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2 (Telegram Bot): Start bot (/start <challengeId>)
  // Step 2 (Telegram Bot): Share native Telegram contact (request_contact=True)
  // Step 2: Verify OTP Code
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!challengeId || otpCode.trim().length !== 6) {
      setErrorMessage("6 xonali tasdiqlash kodini to‘liq kiriting.");
      return;
    }

    if (deliveryMethod === "TELEGRAM" && !telegramVerified) {
      setErrorMessage(
        "Avval Telegram bot orqali telefon raqamingizni yuborib, saytda kiritilgan raqam bilan mosligini tasdiqlang."
      );
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await consumeAuthChallenge(challengeId, "REGISTER", otpCode.trim());
      if (res.ok && res.verification_token) {
        setVerificationToken(res.verification_token);
        setSuccessMessage("Telefon raqamingiz muvaffaqiyatli tasdiqlandi!");
        setTimeout(() => {
          setSuccessMessage(null);
          setStep(3);
        }, 500);
      } else {
        setErrorMessage("Kiritilgan tasdiqlash kodi noto‘g‘ri yoki muddati o‘tgan.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Kodni tasdiqlashda xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  // Step 3: Complete Registration
  const handleCompleteRegistration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verificationToken) {
      setErrorMessage("Telefon raqam tasdiqlanishi shart.");
      setStep(2);
      return;
    }

    if (!displayName.trim() || displayName.trim().length < 2) {
      setErrorMessage("Ism va familiyangizni to‘liq kiriting.");
      return;
    }

    if (password.length < 12) {
      setErrorMessage("Parol kamida 12 ta belgidan iborat bo‘lishi shart.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage("Kiritilgan parollar bir-biriga mos kelmadi.");
      return;
    }

    if (!adultConfirmed) {
      setErrorMessage("18 yoshga to‘lganligingizni tasdiqlashingiz shart.");
      return;
    }

    if (!termsAgreed) {
      setErrorMessage("Foydalanish shartlari va Maxfiylik siyosatiga rozilik berilishi shart.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await registerCandidateUser({
        verification_token: verificationToken,
        display_name: displayName.trim(),
        password: password,
        adult_confirmed: adultConfirmed,
        terms_version: termsVersion,
        privacy_version: privacyVersion,
        roles: ["CANDIDATE"],
      });

      if (res.ok) {
        window.dispatchEvent(new Event("flexbridge:auth-changed"));
        const me = await fetchAuthMe();
        const userRoles = me?.roles || ["CANDIDATE"];
        const dash = resolvePortalDashboard(userRoles);

        if (selectedRole === "CANDIDATE" || dash.portal === selectedRole) {
          setSuccessMessage(`Hisobingiz yaratildi! ${dash.label}ga yo‘naltirilmoqda...`);
          setTimeout(() => {
            router.push(dash.href);
            router.refresh();
          }, 600);
          return;
        }

        if (selectedRole === "EMPLOYER") {
          setSuccessMessage("Hisob yaratildi! Korxona taklif tokeni bo‘lsa quyida faollashtiring.");
          if (inviteToken.trim()) {
            await handlePreviewInvite();
          }
          setStep(4);
          return;
        }

        if (selectedRole === "ACADEMIC") {
          setSuccessMessage("Hisob yaratildi! OTM tayinlov roziligingizni quyida tasdiqlang.");
          await loadAppointmentInbox();
          setStep(4);
          return;
        }

        setSuccessMessage("Bazaviy hisob yaratildi! Operator SOC vakolati protokolini ko‘ring.");
        setStep(4);
      } else {
        setErrorMessage("Ro‘yxatdan o‘tishda xatolik yuz berdi.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Ro‘yxatdan o‘tishda xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  // Password Strength Calculation
  const getPasswordStrength = () => {
    if (password.length === 0) return { label: "", score: 0, color: "bg-zinc-700" };
    if (password.length < 8) return { label: "Juda zaif", score: 1, color: "bg-rose-500" };
    if (password.length < 12) return { label: "Yetarli emas (kamida 12 belgi)", score: 2, color: "bg-amber-500" };
    const hasNum = /\d/.test(password);
    const hasSpecial = /[^A-Za-z0-9]/.test(password);
    if (hasNum && hasSpecial) return { label: "Mustahkam", score: 4, color: "bg-emerald-500" };
    return { label: "Yaxshi", score: 3, color: "bg-blue-500" };
  };

  const strength = getPasswordStrength();

  return (
    <div className="w-full max-w-lg space-y-6">
      {/* Brand Header */}
      <div className="text-center space-y-2">
        <Link href="/" className="inline-flex items-center gap-2.5 group">
          <div
            data-skeuo-dark="true"
            className="relative w-11 h-11 rounded-2xl skeuo-obsidian flex items-center justify-center font-display font-bold text-white shadow-lg group-hover:scale-105 transition"
          >
            FB
            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-[#D95F2B] ring-2 ring-[var(--fb-bg)]" />
          </div>
          <span className="font-display text-xl font-bold tracking-tight text-[var(--fb-ink)]">FlexBridge</span>
        </Link>
        <h1 className="font-display text-2xl font-bold tracking-tight text-[var(--fb-ink)]">
          Ro‘yxatdan O‘tish
        </h1>
        <p className="text-xs text-[var(--fb-ink-muted)]">
          Talaba, Korxona, Universitet va Operator uchun yagona ro‘yxatdan o‘tish va rolga yo‘naltirish
        </p>
      </div>

      {/* Stepper Indicator */}
      <div className="flex items-center justify-between px-2">
        <div className="flex items-center gap-2">
          <div
            data-skeuo-dark={step >= 1 ? "true" : undefined}
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
              step >= 1 ? "skeuo-obsidian text-white" : "skeuo-well text-[var(--fb-ink-muted)]"
            }`}
          >
            1
          </div>
          <span className={`text-xs ${step >= 1 ? "text-[var(--fb-ink)] font-semibold" : "text-[var(--fb-ink-muted)]"}`}>
            Rol
          </span>
        </div>
        <div className="w-6 h-[1px] bg-[var(--fb-border)]" />
        <div className="flex items-center gap-2">
          <div
            data-skeuo-dark={step >= 2 ? "true" : undefined}
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
              step >= 2 ? "skeuo-obsidian text-white" : "skeuo-well text-[var(--fb-ink-muted)]"
            }`}
          >
            2
          </div>
          <span className={`text-xs ${step >= 2 ? "text-[var(--fb-ink)] font-semibold" : "text-[var(--fb-ink-muted)]"}`}>
            Telefon
          </span>
        </div>
        <div className="w-6 h-[1px] bg-[var(--fb-border)]" />
        <div className="flex items-center gap-2">
          <div
            data-skeuo-dark={step >= 3 ? "true" : undefined}
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
              step >= 3 ? "skeuo-obsidian text-white" : "skeuo-well text-[var(--fb-ink-muted)]"
            }`}
          >
            3
          </div>
          <span className={`text-xs ${step >= 3 ? "text-[var(--fb-ink)] font-semibold" : "text-[var(--fb-ink-muted)]"}`}>
            Profil
          </span>
        </div>
        <div className="w-6 h-[1px] bg-[var(--fb-border)]" />
        <div className="flex items-center gap-2">
          <div
            data-skeuo-dark={step >= 4 ? "true" : undefined}
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
              step >= 4 ? "skeuo-obsidian text-white" : "skeuo-well text-[var(--fb-ink-muted)]"
            }`}
          >
            4
          </div>
          <span className={`text-xs ${step >= 4 ? "text-[var(--fb-ink)] font-semibold" : "text-[var(--fb-ink-muted)]"}`}>
            Kabinet
          </span>
        </div>
      </div>

      {/* Main Wizard Card */}
      <div className="skeuo-card rounded-[28px] p-6 sm:p-8 space-y-6">
        {/* Error / Success Alerts */}
        {errorMessage && (
          <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-3 text-xs text-rose-400">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <span className="leading-relaxed">{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-start gap-3 text-xs text-emerald-400">
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-400" />
            <span className="leading-relaxed">{successMessage}</span>
          </div>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* STEP 1: Select Role */}
        {/* ------------------------------------------------------------------ */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="space-y-1">
              <h2 className="text-sm font-bold text-[var(--fb-ink)]">
                Platformadagi faoliyat turini tanlang (4 portal)
              </h2>
              <p className="text-xs text-[var(--fb-ink-muted)]">
                Ro‘yxatdan o‘tgach hisobingiz roliga qarab avtomatik o‘z kabinetingizga o‘tkazilasiz
              </p>
            </div>

            <div className="space-y-3">
              {/* Option 1: Candidate */}
              <div
                onClick={() => setSelectedRole("CANDIDATE")}
                className={`p-4 rounded-2xl cursor-pointer transition-all flex items-start gap-3.5 ${
                  selectedRole === "CANDIDATE"
                    ? "skeuo-card border border-sky-500/70 ring-1 ring-sky-500/35"
                    : "skeuo-well hover:-translate-y-0.5"
                }`}
              >
                <div
                  className={`p-2.5 rounded-xl shrink-0 ${
                    selectedRole === "CANDIDATE"
                      ? "bg-sky-600 text-white shadow-sm"
                      : "skeuo-well-sm text-sky-700 dark:text-sky-300"
                  }`}
                >
                  <GraduationCap className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-[var(--fb-ink)]">
                      1. Talaba / Nomzod
                    </span>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-sky-500/12 text-sky-700 dark:text-sky-300 border border-sky-500/25">
                      Talaba
                    </span>
                  </div>
                  <p className="text-xs text-[var(--fb-ink-muted)] mt-1 leading-relaxed">
                    Dars jadvaliga mos amaliyot, rezyume, smenali ishlar va e-imzoli kundalik
                  </p>
                </div>
              </div>

              {/* Option 2: Employer */}
              <div
                onClick={() => setSelectedRole("EMPLOYER")}
                className={`p-4 rounded-2xl cursor-pointer transition-all flex items-start gap-3.5 ${
                  selectedRole === "EMPLOYER"
                    ? "skeuo-card border border-emerald-500/70 ring-1 ring-emerald-500/35"
                    : "skeuo-well hover:-translate-y-0.5"
                }`}
              >
                <div
                  className={`p-2.5 rounded-xl shrink-0 ${
                    selectedRole === "EMPLOYER"
                      ? "bg-emerald-600 text-white shadow-sm"
                      : "skeuo-well-sm text-emerald-700 dark:text-emerald-300"
                  }`}
                >
                  <Building2 className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-[var(--fb-ink)]">
                      2. Korxona / HR Vakili
                    </span>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/12 text-emerald-700 dark:text-emerald-300 border border-emerald-500/25">
                      Korxona
                    </span>
                  </div>
                  <p className="text-xs text-[var(--fb-ink-muted)] mt-1 leading-relaxed">
                    Tashkilot taklifini qabul qilish, vakansiyalar, nomzod Kanban va mentorlik
                  </p>
                </div>
              </div>

              {/* Option 3: Academic */}
              <div
                onClick={() => setSelectedRole("ACADEMIC")}
                className={`p-4 rounded-2xl cursor-pointer transition-all flex items-start gap-3.5 ${
                  selectedRole === "ACADEMIC"
                    ? "skeuo-card border border-indigo-500/70 ring-1 ring-indigo-500/35"
                    : "skeuo-well hover:-translate-y-0.5"
                }`}
              >
                <div
                  className={`p-2.5 rounded-xl shrink-0 ${
                    selectedRole === "ACADEMIC"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "skeuo-well-sm text-indigo-700 dark:text-indigo-300"
                  }`}
                >
                  <School className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-[var(--fb-ink)]">
                      3. OTM / Universitet Vakili
                    </span>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/12 text-indigo-700 dark:text-indigo-300 border border-indigo-500/25">
                      Universitet
                    </span>
                  </div>
                  <p className="text-xs text-[var(--fb-ink-muted)] mt-1 leading-relaxed">
                    Kafedra tayinlovini tasdiqlash, dars jadvali va yakuniy akademik xulosalar
                  </p>
                </div>
              </div>

              {/* Option 4: Platform Operator */}
              <div
                onClick={() => setSelectedRole("OPERATOR")}
                className={`p-4 rounded-2xl cursor-pointer transition-all flex items-start gap-3.5 ${
                  selectedRole === "OPERATOR"
                    ? "skeuo-card border border-amber-500/70 ring-1 ring-amber-500/35"
                    : "skeuo-well hover:-translate-y-0.5"
                }`}
              >
                <div
                  className={`p-2.5 rounded-xl shrink-0 ${
                    selectedRole === "OPERATOR"
                      ? "bg-amber-600 text-white shadow-sm"
                      : "skeuo-well-sm text-amber-700 dark:text-amber-300"
                  }`}
                >
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-[var(--fb-ink)]">
                      4. Platforma Operatori
                    </span>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-500/12 text-amber-800 dark:text-amber-300 border border-amber-500/25">
                      Operator
                    </span>
                  </div>
                  <p className="text-xs text-[var(--fb-ink-muted)] mt-1 leading-relaxed">
                    Ikki bosqichli platforma vakolati tayyorlash, moderatsiya va tizim audit nazorati
                  </p>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => {
                setErrorMessage(null);
                setStep(2);
              }}
              className="w-full py-3 skeuo-btn-obsidian rounded-2xl text-sm font-semibold flex items-center justify-center gap-2 mt-4"
            >
              <span>Davom etish</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <div className="grid grid-cols-2 gap-2 pt-3 border-t border-[var(--fb-border)] text-[11px]">
              <Link
                href="/talaba/royxatdan-otish"
                className="rounded-xl skeuo-well-sm border border-sky-500/25 px-2.5 py-2 text-sky-700 dark:text-sky-300 hover:border-sky-500/50 text-center font-semibold transition-colors"
              >
                Alohida Talaba ulanishi
              </Link>
              <Link
                href="/korxona/royxatdan-otish"
                className="rounded-xl skeuo-well-sm border border-emerald-500/25 px-2.5 py-2 text-emerald-700 dark:text-emerald-300 hover:border-emerald-500/50 text-center font-semibold transition-colors"
              >
                Alohida Korxona ulanishi
              </Link>
              <Link
                href="/universitet/royxatdan-otish"
                className="rounded-xl skeuo-well-sm border border-indigo-500/25 px-2.5 py-2 text-indigo-700 dark:text-indigo-300 hover:border-indigo-500/50 text-center font-semibold transition-colors"
              >
                Alohida OTM ulanishi
              </Link>
              <Link
                href="/operator/kirish"
                className="rounded-xl skeuo-well-sm border border-amber-500/25 px-2.5 py-2 text-amber-800 dark:text-amber-300 hover:border-amber-500/50 text-center font-semibold transition-colors"
              >
                Operator SOC kirishi
              </Link>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* STEP 2: Phone Challenge & OTP Verification */}
        {/* ------------------------------------------------------------------ */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <h2 className="text-sm font-semibold text-zinc-200">
                  Telefon raqamni tasdiqlash
                </h2>
                <p className="text-xs text-zinc-400">
                  Kodni qabul qilish usulini tanlang (SMS yoki Telegram Bot)
                </p>
              </div>
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1 transition"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Rolni o‘zgartirish</span>
              </button>
            </div>

            {!challengeId ? (
              <form onSubmit={handleSendChallenge} className="space-y-4">
                {/* Delivery Method Choice: SMS vs TELEGRAM */}
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-2">
                    Tasdiqlash kodini olish usulini tanlang
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    <button
                      type="button"
                      onClick={() => {
                        setDeliveryMethod("SMS");
                        setErrorMessage(null);
                      }}
                      className={`p-3 rounded-xl border text-left transition flex items-start gap-2.5 ${
                        deliveryMethod === "SMS"
                          ? "bg-indigo-950/30 border-indigo-500/80 ring-1 ring-indigo-500/40"
                          : "bg-[#18181b] border-zinc-800 hover:border-zinc-700"
                      }`}
                    >
                      <div
                        className={`p-2 rounded-lg shrink-0 ${
                          deliveryMethod === "SMS"
                            ? "bg-indigo-600 text-white"
                            : "bg-zinc-800 text-zinc-400"
                        }`}
                      >
                        <MessageSquare className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-zinc-100">
                          SMS xabar orqali
                        </div>
                        <p className="text-[11px] text-zinc-400 mt-0.5 leading-snug">
                          Raqamingizga 6 xonali SMS kod yuboriladi
                        </p>
                      </div>
                    </button>

                    <button
                      type="button"
                      disabled={telegramMode === "DISABLED"}
                      title={telegramMode === "DISABLED" ? "Telegram bot hozircha ulanmagan — SMS orqali davom eting" : undefined}
                      onClick={() => {
                        setDeliveryMethod("TELEGRAM");
                        setErrorMessage(null);
                      }}
                      className={`p-3 rounded-xl border text-left transition flex items-start gap-2.5 ${
                        deliveryMethod === "TELEGRAM"
                          ? "bg-sky-950/30 border-sky-500/80 ring-1 ring-sky-500/40"
                          : "bg-[#18181b] border-zinc-800 hover:border-zinc-700"
                      }`}
                    >
                      <div
                        className={`p-2 rounded-lg shrink-0 ${
                          deliveryMethod === "TELEGRAM"
                            ? "bg-sky-500 text-white"
                            : "bg-zinc-800 text-zinc-400"
                        }`}
                      >
                        <Send className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-semibold text-zinc-100">
                            Telegram Bot orqali
                          </span>
                          <span className="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-sky-500/15 text-sky-400 border border-sky-500/30">
                            Bot
                          </span>
                        </div>
                        <p className="text-[11px] text-zinc-400 mt-0.5 leading-snug">
                          Botda telefon raqam mosligi tekshirilib kod beriladi
                        </p>
                      </div>
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                    Telefon raqam
                  </label>
                  <div className="relative">
                    <input
                      type="tel"
                      required
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+998901234567"
                      className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition font-mono"
                    />
                    <Smartphone className="w-4 h-4 text-zinc-500 absolute right-3.5 top-3" />
                  </div>
                  {deliveryMethod === "TELEGRAM" ? (
                    <div className="mt-2 p-3 rounded-xl bg-sky-500/10 border border-sky-500/25 space-y-1">
                      <div className="text-[11px] font-semibold text-sky-300 flex items-center gap-1.5">
                        <Shield className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                        <span>Telegram orqali tasdiqlash sharti:</span>
                      </div>
                      <p className="text-[11px] text-sky-200/80 leading-relaxed">
                        Saytda kiritilgan telefon raqami Telegram botda yuborilgan raqamingizga{" "}
                        <strong className="text-white">to‘liq mos kelishi shart</strong>. Bot ishga
                        tushganda (<code className="text-sky-300">/start</code>) maxsus tugma orqali
                        telefon raqamingizni yuborish so‘raladi va bot tizimi raqam haqiqiyligini
                        tekshiradi.
                      </p>
                    </div>
                  ) : (
                    <p className="text-[11px] text-zinc-500 mt-1">
                      Ushbu raqamga bir martalik 6 xonali SMS tasdiqlash kodi yuboriladi
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className={`w-full py-3 ${
                    deliveryMethod === "TELEGRAM"
                      ? "bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 shadow-sky-600/25"
                      : "bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 shadow-indigo-600/25"
                  } disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 shadow-lg`}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Tayyorlanmoqda...</span>
                    </>
                  ) : deliveryMethod === "TELEGRAM" ? (
                    <>
                      <Send className="w-4 h-4" />
                      <span>Telegram Bot orqali Kod Olish</span>
                    </>
                  ) : (
                    <>
                      <span>SMS Kod Yuborish</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            ) : (
              <form onSubmit={handleVerifyOtp} className="space-y-4">
                <div className="p-3 bg-zinc-900/60 border border-zinc-800 rounded-xl flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-300 font-mono">{phone}</span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                        deliveryMethod === "TELEGRAM"
                          ? "bg-sky-500/15 text-sky-400 border border-sky-500/30"
                          : "bg-indigo-500/15 text-indigo-400 border border-indigo-500/30"
                      }`}
                    >
                      {deliveryMethod === "TELEGRAM" ? "Telegram Bot" : "SMS"}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setChallengeId(null);
                      setOtpCode("");
                      setTelegramVerified(false);
                    }}
                    className="text-indigo-400 hover:text-indigo-300 text-[11px] transition"
                  >
                    O‘zgartirish
                  </button>
                </div>

                {/* Telegram Bot Interactive Verification Box */}
                {challengeId && deliveryMethod === "TELEGRAM" && (
                  <TelegramVerification
                    mode={telegramMode}
                    challengeId={challengeId}
                    phone={phone}
                    botUsername={telegramBotUsername}
                    deepLink={telegramDeepLink}
                    verified={telegramVerified}
                    onSimulatedCode={(code) => {
                      setOtpCode(code);
                      setTelegramVerified(true);
                    }}
                  />
                )}

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                    6 xonali tasdiqlash kodi
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      maxLength={6}
                      required
                      autoFocus
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                      placeholder="000000"
                      className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-3 text-center text-xl tracking-widest font-mono text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-indigo-500 transition"
                    />
                    <KeyRound className="w-4 h-4 text-zinc-500 absolute left-3.5 top-3.5" />
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-500">Kodni olmadingizmi?</span>
                  {resendTimer > 0 ? (
                    <span className="text-zinc-500 font-mono">{resendTimer} soniya kutish</span>
                  ) : (
                    <button
                      type="button"
                      onClick={handleSendChallenge}
                      className="text-indigo-400 hover:text-indigo-300 font-medium transition"
                    >
                      Kodni qayta yuborish
                    </button>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={
                    isLoading ||
                    otpCode.length !== 6 ||
                    (deliveryMethod === "TELEGRAM" && !telegramVerified)
                  }
                  className="w-full py-3 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Tekshirilmoqda...</span>
                    </>
                  ) : (
                    <>
                      <span>Kodni Tasdiqlash</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* STEP 3: Profile Info, Password & Legal Consent */}
        {/* ------------------------------------------------------------------ */}
        {step === 3 && (
          <form onSubmit={handleCompleteRegistration} className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <h2 className="text-sm font-semibold text-zinc-200">
                  Profil va xavfsizlik ma&apos;lumotlari
                </h2>
                <p className="text-xs text-zinc-400">
                  Ismingiz va kamida 12 belgidan iborat kuchli parol kiriting
                </p>
              </div>
            </div>

            {/* Display Name */}
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Ism va Familiyangiz
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Aziz Rahimov"
                  className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition"
                />
                <User className="w-4 h-4 text-zinc-500 absolute right-3.5 top-3" />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Yangi Parol (kamida 12 ta belgi)
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-3 text-zinc-400 hover:text-zinc-200 transition"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {/* Strength Meter */}
              {password.length > 0 && (
                <div className="mt-1.5 space-y-1">
                  <div className="h-1 w-full bg-zinc-800 rounded-full overflow-hidden flex gap-1">
                    <div className={`h-full flex-1 transition-all ${strength.score >= 1 ? strength.color : "bg-transparent"}`} />
                    <div className={`h-full flex-1 transition-all ${strength.score >= 2 ? strength.color : "bg-transparent"}`} />
                    <div className={`h-full flex-1 transition-all ${strength.score >= 3 ? strength.color : "bg-transparent"}`} />
                    <div className={`h-full flex-1 transition-all ${strength.score >= 4 ? strength.color : "bg-transparent"}`} />
                  </div>
                  <span className="text-[10px] text-zinc-400">{strength.label}</span>
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Parolni Takrorlang
              </label>
              <input
                type={showPassword ? "text" : "password"}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition"
              />
            </div>

            {/* Adult Confirmation Checkbox */}
            <div className="pt-2 space-y-2.5">
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  required
                  checked={adultConfirmed}
                  onChange={(e) => setAdultConfirmed(e.target.checked)}
                  className="mt-0.5 rounded border-zinc-700 bg-zinc-800 text-indigo-600 focus:ring-0 focus:ring-offset-0"
                />
                <span className="text-xs text-zinc-300 leading-relaxed">
                  Men 18 yoshga to‘lganligimni (yoki qonuniy vakil roziligi bilan ishtirok etayotganimni) tasdiqlayman.
                </span>
              </label>

              {/* Policy Consent Checkbox */}
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  required
                  checked={termsAgreed}
                  onChange={(e) => setTermsAgreed(e.target.checked)}
                  className="mt-0.5 rounded border-zinc-700 bg-zinc-800 text-indigo-600 focus:ring-0 focus:ring-offset-0"
                />
                <span className="text-xs text-zinc-300 leading-relaxed">
                  Platformaning{" "}
                  <Link href="/shartlar" target="_blank" className="text-indigo-400 underline hover:text-indigo-300">
                    Foydalanish shartlari
                  </Link>{" "}
                  va{" "}
                  <Link href="/maxfiylik" target="_blank" className="text-indigo-400 underline hover:text-indigo-300">
                    Maxfiylik siyosatiga
                  </Link>{" "}
                  to‘liq roziman.
                </span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading || !adultConfirmed || !termsAgreed}
              className="w-full py-3 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 mt-4"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Hisob yaratilmoqda...</span>
                </>
              ) : (
                <>
                  <span>Ro‘yxatdan O‘tishni Yakunlash</span>
                  <CheckCircle2 className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        )}

        {/* Step 4: Role Activation (Employer Invite / Academic Consent / Operator 2FA & Dual-Control) */}
        {step === 4 && (
          <div className="space-y-5 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 p-3.5 text-xs text-emerald-200 space-y-1">
              <div className="font-semibold text-emerald-100">
                Asosiy hisob yaratildi va tizimga ulandi
              </div>
              <p className="text-emerald-200/80 leading-relaxed">
                Endi tanlangan rol bo‘yicha kabinet vakolatini shu yerning o‘zida faollashtiring yoki asosiy nomzod kabinetiga o‘ting.
              </p>
            </div>

            {selectedRole === "EMPLOYER" && (
              <div className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4">
                <div className="space-y-1">
                  <h3 className="text-sm font-semibold text-white">
                    Korxona / HR taklif tokenini faollashtirish
                  </h3>
                  <p className="text-xs text-zinc-400 leading-relaxed">
                    Korxona rahbari (Owner) yoki HR administratoridan olingan taklif tokenini kiriting. Tekshiruvdan so‘ng bevosita /employer kabinetiga o‘tasiz.
                  </p>
                </div>

                <div className="space-y-2">
                  <label htmlFor="invite-token-input" className="block text-xs font-medium text-zinc-300">
                    Taklif tokeni
                  </label>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <input
                      id="invite-token-input"
                      type="text"
                      value={inviteToken}
                      onChange={(e) => setInviteToken(e.target.value)}
                      placeholder="Masalan: fb_inv_..."
                      className="flex-1 rounded-xl border border-zinc-800 bg-zinc-900/80 px-3.5 py-2.5 text-xs text-white placeholder:text-zinc-500 focus:border-indigo-500 focus:outline-none"
                    />
                    <button
                      type="button"
                      disabled={activationBusy || !inviteToken.trim()}
                      onClick={() => void handlePreviewInvite()}
                      className="rounded-xl border border-indigo-500/40 bg-indigo-500/15 px-4 py-2.5 text-xs font-semibold text-indigo-200 hover:bg-indigo-500/25 disabled:opacity-50 transition"
                    >
                      {activationBusy ? "Tekshirilmoqda..." : "Tokenni tekshirish"}
                    </button>
                  </div>
                </div>

                {invitePreview && (
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 space-y-3 text-xs">
                    <div className="grid grid-cols-2 gap-2 text-zinc-300">
                      <div>
                        <span className="block text-[11px] text-zinc-400">Korxona</span>
                        <span className="font-semibold text-white">{invitePreview.organization_name}</span>
                      </div>
                      <div>
                        <span className="block text-[11px] text-zinc-400">Rol</span>
                        <span className="font-semibold text-emerald-300">{invitePreview.role_code}</span>
                      </div>
                      <div>
                        <span className="block text-[11px] text-zinc-400">Manzil</span>
                        <span className="text-zinc-200">{invitePreview.masked_destination}</span>
                      </div>
                      <div>
                        <span className="block text-[11px] text-zinc-400">Holat</span>
                        <span className="text-zinc-200">{invitePreview.status}</span>
                      </div>
                    </div>
                    <button
                      type="button"
                      disabled={activationBusy}
                      onClick={() => void handleAcceptInvite()}
                      className="w-full rounded-xl bg-emerald-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition"
                    >
                      {activationBusy ? "Faollashtirilmoqda..." : "Taklifni qabul qilish va /employer kabinetiga o‘tish"}
                    </button>
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-zinc-800/80 text-xs">
                  <Link href="/nomzod/xavfsizlik" className="text-amber-300 hover:text-amber-200 transition">
                    2FA (TOTP) ni sozlash
                  </Link>
                  <Link href="/korxona/kirish" className="text-indigo-400 hover:text-indigo-300 transition">
                    Korxona kirish sahifasi
                  </Link>
                  <Link href="/nomzod" className="text-zinc-400 hover:text-white transition">
                    /nomzod kabinetiga o‘tish
                  </Link>
                </div>
              </div>
            )}

            {selectedRole === "ACADEMIC" && (
              <div className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <h3 className="text-sm font-semibold text-white">
                      Universitet / OTM tayinlovini tasdiqlash
                    </h3>
                    <p className="text-xs text-zinc-400 leading-relaxed">
                      OTM koordinatori yoki rektorati tomonidan yuborilgan tayinlovga rozilik bildiring. Tasdiqlangach /university kabineti ochiladi.
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled={activationBusy}
                    onClick={() => void loadAppointmentInbox()}
                    className="shrink-0 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-[11px] font-medium text-zinc-200 hover:border-zinc-500 disabled:opacity-50 transition"
                  >
                    {activationBusy ? "Yuklanmoqda..." : "Yangilash"}
                  </button>
                </div>

                {verifiedContacts.length > 0 && (
                  <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-2.5 text-[11px] text-zinc-300">
                    Tasdiqlangan aloqa:{" "}
                    {verifiedContacts.map((c) => `${c.channel}: ${c.masked_destination}`).join(", ")}
                  </div>
                )}

                {pendingAppointments.length === 0 ? (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-3.5 text-xs text-zinc-400 space-y-2">
                    <p>
                      Hozircha sizning tasdiqlangan telefoningiz yoki Telegram hisobingizga biriktirilgan faol OTM tayinlovi topilmadi.
                    </p>
                    <p>
                      OTM mas’ul xodimi tayinlov yaratgach «Yangilash» tugmasini bosing.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {pendingAppointments.map((appt) => (
                      <div
                        key={appt.id}
                        className="rounded-xl border border-indigo-500/25 bg-indigo-500/5 p-3.5 space-y-3 text-xs"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div>
                            <div className="font-semibold text-white">OTM ID: {appt.institution_id}</div>
                            <div className="text-[11px] text-zinc-400">
                              Holat: {appt.status} ({appt.case_status}) • rev {appt.current_revision}
                            </div>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={activationBusy}
                            onClick={() => void handleAppointmentConsent(appt, "ACCEPT")}
                            className="flex-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition"
                          >
                            Qabul qilish va /university ga o‘tish
                          </button>
                          <button
                            type="button"
                            disabled={activationBusy}
                            onClick={() => void handleAppointmentConsent(appt, "DECLINE")}
                            className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-medium text-zinc-300 hover:border-red-500/40 hover:text-red-300 disabled:opacity-50 transition"
                          >
                            Rad etish
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-zinc-800/80 text-xs">
                  <Link href="/universitet/kirish" className="text-indigo-400 hover:text-indigo-300 transition">
                    OTM kirish sahifasi
                  </Link>
                  <Link href="/nomzod" className="text-zinc-400 hover:text-white transition">
                    Hozircha /nomzod kabinetiga o‘tish
                  </Link>
                </div>
              </div>
            )}

            {selectedRole === "OPERATOR" && (
              <div className="space-y-4 rounded-xl border border-amber-500/25 bg-amber-500/5 p-4">
                <div className="space-y-1">
                  <h3 className="text-sm font-semibold text-amber-200">
                    Platforma Operatori / SOC faollashtiruvi
                  </h3>
                  <p className="text-xs text-zinc-300 leading-relaxed">
                    Xavfsizlik siyosatiga ko‘ra operator rollari (OPERATOR, MODERATOR, AUDITOR, SECURITY_LEAD, ADMIN) ikki tomonlama tasdiq (dual-control) va majburiy 2FA (TOTP) orqali beriladi.
                  </p>
                </div>

                <div className="flex flex-col gap-2">
                  <button
                    type="button"
                    disabled={activationBusy}
                    onClick={() => void handleRecheckOperatorRoles()}
                    className="w-full rounded-xl bg-amber-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-amber-500 disabled:opacity-50 transition"
                  >
                    {activationBusy ? "Tekshirilmoqda..." : "Operator ruxsatini qayta tekshirish"}
                  </button>
                  <Link
                    href="/nomzod/xavfsizlik"
                    className="w-full text-center rounded-xl border border-amber-500/35 bg-zinc-900/80 px-4 py-2.5 text-xs font-semibold text-amber-200 hover:bg-zinc-900 transition"
                  >
                    2FA (TOTP) ni sozlash (/nomzod/xavfsizlik)
                  </Link>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-amber-500/20 text-xs">
                  <Link href="/operator/kirish" className="text-amber-300 hover:text-amber-200 transition">
                    SOC kirish sahifasi (/operator/kirish)
                  </Link>
                  <Link href="/nomzod" className="text-zinc-400 hover:text-white transition">
                    Hozircha /nomzod kabinetiga o‘tish
                  </Link>
                </div>
              </div>
            )}

            {selectedRole === "CANDIDATE" && (
              <div className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 text-xs">
                <p className="text-zinc-300">Talaba / Nomzod kabinetingiz tayyor.</p>
                <Link
                  href="/nomzod"
                  className="inline-flex w-full items-center justify-center rounded-xl bg-indigo-600 px-4 py-2.5 font-semibold text-white hover:bg-indigo-500 transition"
                >
                  /nomzod kabinetiga o‘tish
                </Link>
              </div>
            )}
          </div>
        )}

        {/* Existing User Login Divider */}
        <div className="pt-4 border-t border-zinc-800/80 text-center space-y-3">
          <p className="text-xs text-zinc-400">
            Allaqachon hisobingiz bormi?{" "}
            <Link
              href="/kirish"
              className="text-indigo-400 hover:text-indigo-300 font-semibold underline underline-offset-2 transition"
            >
              Tizimga kirish
            </Link>
          </p>

          <div className="flex items-center justify-center gap-4 text-[11px] text-zinc-500">
            <Link href="/shartlar" className="hover:text-zinc-300 transition">
              Shartlar
            </Link>
            <span>•</span>
            <Link href="/maxfiylik" className="hover:text-zinc-300 transition">
              Maxfiylik
            </Link>
            <span>•</span>
            <Link href="/haqida" className="hover:text-zinc-300 transition">
              Platforma haqida
            </Link>
          </div>
        </div>
      </div>

      {/* Security Footer Note */}
      <div className="flex items-center justify-center gap-2 text-[11px] text-zinc-500">
        <Shield className="w-3.5 h-3.5 text-zinc-600" />
        <span>Shaxsiy ma&apos;lumotlar O&apos;zR qonunchiligi bo&apos;yicha himoyalangan</span>
      </div>
    </div>
  );
}

export default function RoyxatdanOtishPage() {
  return (
    <div className="min-h-screen text-[var(--fb-ink)] py-10 px-4 sm:px-6 lg:px-8 flex items-center justify-center">
      <div className="w-full max-w-5xl space-y-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)] transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Bosh sahifaga qaytish</span>
        </Link>

        <div className="grid gap-8 lg:grid-cols-[0.85fr_1.15fr] items-start">
          {/* Left Onboarding Guide Column */}
          <aside className="hidden lg:flex flex-col gap-5 rounded-[28px] skeuo-card p-7">
            <div className="inline-flex w-fit items-center gap-2 rounded-lg skeuo-badge-recessed px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
              4 bosqichli tezkor ulanish
            </div>
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight text-[var(--fb-ink)]">
                Mos hisob turini tanlang va kabinetga kiring
              </h2>
              <p className="mt-2 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
                SMS yoki rasmiy Telegram bot orqali xavfsiz hisob yarating va rol bo‘yicha kabinetni (taklif kodi, OTM tayinlovi yoki operator 2FA) shu yerning o‘zida faollashtiring.
              </p>
            </div>
            <ol className="space-y-3 pt-2 border-t border-[var(--fb-hairline)] text-xs text-[var(--fb-ink-secondary)]">
              <li className="flex items-start gap-2.5">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full skeuo-well-sm text-[10px] font-bold text-[var(--fb-ink)]">1</span>
                <span><strong className="text-[var(--fb-ink)]">Rolni tanlash:</strong> Talaba, Korxona HR, Universitet yoki Operator sifatida ro‘yxatdan o‘tish.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full skeuo-well-sm text-[10px] font-bold text-[var(--fb-ink)]">2</span>
                <span><strong className="text-[var(--fb-ink)]">Kontakt tasdig‘i:</strong> SMS yoki Telegram botda raqam mosligini tasdiqlash.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full skeuo-well-sm text-[10px] font-bold text-[var(--fb-ink)]">3</span>
                <span><strong className="text-[var(--fb-ink)]">Shaxsiy kabinet:</strong> Rolingizga mos alohida boshqaruv paneliga o‘tish.</span>
              </li>
            </ol>
          </aside>

          {/* Right Registration Wizard */}
          <div className="flex justify-center">
            <Suspense
              fallback={
                <div className="p-8 text-center text-zinc-400 flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Yuklanmoqda...</span>
                </div>
              }
            >
              <RoyxatdanOtishWizard />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  );
}
