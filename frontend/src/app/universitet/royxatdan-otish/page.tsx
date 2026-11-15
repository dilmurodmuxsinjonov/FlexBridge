"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Building2,
  CheckCircle2,
  Eye,
  EyeOff,
  GraduationCap,
  KeyRound,
  Loader2,
  Lock,
  Phone,
  RefreshCw,
  Send,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import {
  consumeAuthChallenge,
  fetchAuthChallengeStatus,
  fetchAuthMe,
  fetchAuthOptions,
  issueAuthChallenge,
  registerCandidateUser,
  sendTelegramBotUpdate,
} from "@/lib/api";
import { isAcademicRoles } from "@/lib/roles";

interface AppointmentInboxItem {
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

function UniversitetRegistrationContent() {
  const router = useRouter();

  const [step, setStep] = useState<1 | 2 | 3>(1);

  const [phone, setPhone] = useState("");
  const [deliveryMethod, setDeliveryMethod] = useState<"SMS" | "TELEGRAM">("SMS");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [verificationToken, setVerificationToken] = useState<string | null>(null);
  const [resendTimer, setResendTimer] = useState(0);

  const [telegramBotUsername, setTelegramBotUsername] = useState("FlexBridgeAuthBot");
  const [telegramDeepLink, setTelegramDeepLink] = useState<string | null>(null);
  const [telegramVerified, setTelegramVerified] = useState(false);
  const [botStarted, setBotStarted] = useState(false);
  const [botContactPhone, setBotContactPhone] = useState("");
  const [botDeliveredOtp, setBotDeliveredOtp] = useState<string | null>(null);
  const [botMessage, setBotMessage] = useState<string | null>(null);
  const [telegramUserId] = useState(() => Math.floor(100000000 + Math.random() * 899999999));

  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [adultConfirmed, setAdultConfirmed] = useState(false);
  const [termsAgreed, setTermsAgreed] = useState(false);

  const [termsVersion, setTermsVersion] = useState("2026.1");
  const [privacyVersion, setPrivacyVersion] = useState("2026.1");

  const [appointments, setAppointments] = useState<AppointmentInboxItem[]>([]);
  const [contacts, setContacts] = useState<VerifiedContactItem[]>([]);
  const [selectedContactId, setSelectedContactId] = useState("");
  const [isLoadingInbox, setIsLoadingInbox] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadAppointmentInbox = async () => {
    setIsLoadingInbox(true);
    try {
      const res = await fetch("/api/bff/university/appointments", { cache: "no-store" });
      const data = await res.json();
      if (res.ok && data.ok) {
        setAppointments(Array.isArray(data.items) ? data.items : []);
        const contactList = Array.isArray(data.contacts) ? data.contacts : [];
        setContacts(contactList);
        if (contactList.length > 0 && !selectedContactId) {
          setSelectedContactId(contactList[0].id);
        }
      }
    } catch {
      // Non-blocking if inbox fetch fails before sign-in
    } finally {
      setIsLoadingInbox(false);
    }
  };

  useEffect(() => {
    let active = true;
    fetchAuthOptions()
      .then((opts) => {
        if (!active || !opts) return;
        if (opts.terms_version) setTermsVersion(opts.terms_version);
        if (opts.privacy_version) setPrivacyVersion(opts.privacy_version);
        if (opts.telegram_bot_username) setTelegramBotUsername(opts.telegram_bot_username);
      })
      .catch(() => {});

    fetchAuthMe().then((user) => {
      if (!active || !user) return;
      if (isAcademicRoles(user.roles)) {
        router.push("/university");
      } else {
        setStep(3);
        loadAppointmentInbox();
      }
    });

    return () => {
      active = false;
    };
  }, [router]);

  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer(resendTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendTimer]);

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
        // Ignore polling blip
      }
    }, 3000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [challengeId, deliveryMethod, telegramVerified]);

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
    setBotStarted(false);
    setBotMessage(null);
    setBotDeliveredOtp(null);
    setBotContactPhone(phone.trim());

    try {
      const res = await issueAuthChallenge("PHONE", phone.trim(), "REGISTER", deliveryMethod);
      if (res.ok && res.challenge_id) {
        setChallengeId(res.challenge_id);
        setResendTimer(res.resend_after || 60);
        if (res.telegram_bot_username) setTelegramBotUsername(res.telegram_bot_username);
        if (res.telegram_deep_link) setTelegramDeepLink(res.telegram_deep_link);

        setSuccessMessage(
          deliveryMethod === "TELEGRAM"
            ? "Telegram tasdiqlash so‘rovi yaratildi. Botni ishga tushirib (/start), raqamingizni yuboring."
            : "Tasdiqlash kodi SMS orqali telefon raqamingizga yuborildi."
        );
      } else {
        setErrorMessage("Tasdiqlash kodini yuborishda xatolik yuz berdi.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleBotStart = async () => {
    if (!challengeId) return;
    setIsLoading(true);
    setErrorMessage(null);
    setBotMessage(null);
    try {
      const res = await sendTelegramBotUpdate({
        challenge_id: challengeId,
        message: {
          from: { id: telegramUserId, first_name: displayName || "OTM vakili" },
          chat: { id: telegramUserId, type: "private" },
          text: `/start ${challengeId}`,
        },
      });
      setBotStarted(true);
      setBotMessage(res.bot_message || "Bot ishga tushdi. Endi telefon raqamingizni yuboring.");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Botni ishga tushirishda xatolik.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleBotShareContact = async () => {
    if (!challengeId) return;
    setIsLoading(true);
    setErrorMessage(null);
    setBotMessage(null);
    try {
      const res = await sendTelegramBotUpdate({
        challenge_id: challengeId,
        message: {
          from: { id: telegramUserId, first_name: displayName || "OTM vakili" },
          chat: { id: telegramUserId, type: "private" },
          contact: {
            phone_number: botContactPhone.trim() || phone.trim(),
            first_name: displayName || "OTM vakili",
            user_id: telegramUserId,
          },
        },
      });
      if (res.telegram_verified) {
        setTelegramVerified(true);
      }
      if (res.otp_code) {
        setBotDeliveredOtp(res.otp_code);
        setOtpCode(res.otp_code);
      }
      setBotMessage(
        res.bot_message || "Raqam mos keldi va tasdiqlandi! Endi quyidagi tasdiqlash kodini kiriting."
      );
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Telegram raqamini tasdiqlashda xatolik."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!challengeId || !otpCode.trim()) {
      setErrorMessage("Tasdiqlash kodini kiriting.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await consumeAuthChallenge(challengeId, "REGISTER", otpCode.trim());
      if (res.ok && res.verification_token) {
        setVerificationToken(res.verification_token);
        setSuccessMessage("Telefon raqamingiz tasdiqlandi!");
        setStep(2);
      } else {
        setErrorMessage("Tasdiqlash kodi noto‘g‘ri.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Kodni tekshirishda xatolik.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verificationToken) {
      setErrorMessage("Avval telefon raqamini tasdiqlang.");
      return;
    }
    if (!displayName.trim() || displayName.trim().length < 2) {
      setErrorMessage("F.I.Sh. (kamida 2 ta belgi) kiritilishi shart.");
      return;
    }
    if (!password || password.length < 12) {
      setErrorMessage("Parol kamida 12 ta belgidan iborat bo‘lishi shart.");
      return;
    }
    if (!adultConfirmed) {
      setErrorMessage("18 yoshdan oshganligingizni tasdiqlang.");
      return;
    }
    if (!termsAgreed) {
      setErrorMessage("Foydalanish shartlari va maxfiylik siyosatiga rozilik bildiring.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await registerCandidateUser({
        verification_token: verificationToken,
        display_name: displayName.trim(),
        password,
        adult_confirmed: true,
        terms_version: termsVersion,
        privacy_version: privacyVersion,
        roles: ["CANDIDATE"],
      });

      if (res.ok && res.user) {
        window.dispatchEvent(new Event("flexbridge:auth-changed"));
        setSuccessMessage("OTM vakili hisobi yaratildi! Endi tayinlovni tasdiqlang.");
        setStep(3);
        await loadAppointmentInbox();
      } else {
        setErrorMessage("Hisob yaratishda xatolik yuz berdi.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Ro‘yxatdan o‘tishda xatolik.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleConsentDecision = async (
    item: AppointmentInboxItem,
    decision: "ACCEPT" | "DECLINE"
  ) => {
    if (decision === "ACCEPT" && !selectedContactId) {
      setErrorMessage("Rozilik uchun tasdiqlangan telefon kontaktini tanlang.");
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const res = await fetch(
        `/api/bff/university/appointments/${encodeURIComponent(item.id)}/consent`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({
            expected_revision: item.current_revision,
            decision,
            contact_id: decision === "ACCEPT" ? selectedContactId : undefined,
          }),
        }
      );
      const data = await res.json();
      if (!res.ok || !data.ok) {
        setErrorMessage(data.message || data.error || "Tayinlov qarorini saqlab bo‘lmadi.");
        return;
      }

      window.dispatchEvent(new Event("flexbridge:auth-changed"));
      const updatedRoles = Array.isArray(data.roles) ? data.roles : [];
      if (isAcademicRoles(updatedRoles)) {
        setSuccessMessage("OTM akademik roli faollashtirildi! Universitet kabinetiga o‘tilmoqda...");
        setTimeout(() => {
          router.push("/university");
          router.refresh();
        }, 600);
      } else {
        setSuccessMessage(
          decision === "ACCEPT"
            ? "Roziligingiz qayd etildi! Moderator tasdiqlashi yakunlangach akademik rol faollashadi."
            : "Tayinlov rad etildi."
        );
        await loadAppointmentInbox();
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Tayinlovni tasdiqlashda xatolik.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-lg space-y-6">
      <div className="space-y-1.5 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-[11px] font-semibold text-indigo-300">
          <GraduationCap className="w-3.5 h-3.5" />
          <span>OTM Vakili Ulanishi (Koordinator / O‘qituvchi)</span>
        </div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-white">
          Universitet Vakili Ro‘yxatdan O‘tishi
        </h1>
        <p className="text-xs text-zinc-400">
          Dekanat koordinatori yoki kafedra o‘qituvchisi hisobini yarating va rasmiy tayinlovni tasdiqlang
        </p>
      </div>

      {/* Stepper */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { num: 1, title: "1. Telefon OTP", icon: Phone },
          { num: 2, title: "2. Vakil Profili", icon: UserCheck },
          { num: 3, title: "3. OTM Tayinlovi", icon: Building2 },
        ].map((item) => {
          const Icon = item.icon;
          const active = step === item.num;
          const done = step > item.num;
          return (
            <div
              key={item.num}
              className={`rounded-xl border px-3 py-2.5 flex items-center gap-2 text-xs transition-colors ${
                active
                  ? "border-indigo-500/50 bg-indigo-500/15 text-indigo-200 font-semibold"
                  : done
                    ? "border-indigo-500/25 bg-indigo-500/[0.06] text-indigo-400"
                    : "border-white/[0.08] bg-[#121214] text-zinc-500"
              }`}
            >
              <Icon className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">{item.title}</span>
            </div>
          );
        })}
      </div>

      <div className="bg-[#121214] border border-indigo-500/20 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-5">
        {errorMessage && (
          <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-3 text-xs text-rose-400">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <span className="leading-relaxed">{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div className="p-3.5 bg-indigo-500/10 border border-indigo-500/25 rounded-xl flex items-start gap-3 text-xs text-indigo-300">
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-indigo-400" />
            <span className="leading-relaxed">{successMessage}</span>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => {
                  setDeliveryMethod("SMS");
                  setChallengeId(null);
                  setErrorMessage(null);
                }}
                className={`rounded-xl border px-3 py-2.5 text-xs font-semibold text-left transition-colors ${
                  deliveryMethod === "SMS"
                    ? "border-indigo-500/50 bg-indigo-500/15 text-indigo-200"
                    : "border-zinc-800 bg-zinc-900/70 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                SMS orqali kod olish
              </button>
              <button
                type="button"
                onClick={() => {
                  setDeliveryMethod("TELEGRAM");
                  setChallengeId(null);
                  setErrorMessage(null);
                }}
                className={`rounded-xl border px-3 py-2.5 text-xs font-semibold text-left transition-colors ${
                  deliveryMethod === "TELEGRAM"
                    ? "border-indigo-500/50 bg-indigo-500/15 text-indigo-200"
                    : "border-zinc-800 bg-zinc-900/70 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Telegram Bot (@{telegramBotUsername})
              </button>
            </div>

            {!challengeId ? (
              <form onSubmit={handleSendChallenge} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                    Xizmat Telefon Raqamingiz
                  </label>
                  <input
                    type="tel"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+998901234567"
                    disabled={isLoading}
                    className="w-full px-3.5 py-2.5 bg-zinc-900/90 border border-zinc-800 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <span>Tasdiqlash so‘rovini yuborish</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            ) : (
              <div className="space-y-4">
                {deliveryMethod === "TELEGRAM" && !telegramVerified && (
                  <div className="rounded-xl border border-indigo-500/25 bg-indigo-500/[0.06] p-4 space-y-3 text-xs">
                    <p className="font-semibold text-indigo-300">
                      Telegram Bot orqali raqam mosligini tasdiqlash
                    </p>
                    {telegramDeepLink && (
                      <a
                        href={telegramDeepLink}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-indigo-400 hover:underline font-medium"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>Botni ochish (@{telegramBotUsername})</span>
                      </a>
                    )}
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={handleBotStart}
                        disabled={isLoading || botStarted}
                        className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium disabled:opacity-50"
                      >
                        {botStarted ? "Bot ishga tushgan" : "1. Botni ishga tushirish (/start)"}
                      </button>
                      <button
                        type="button"
                        onClick={handleBotShareContact}
                        disabled={isLoading || !botStarted}
                        className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold disabled:opacity-50"
                      >
                        2. Telegram raqamini ulashish
                      </button>
                    </div>
                    {botMessage && <p className="text-[11px] text-zinc-300">{botMessage}</p>}
                  </div>
                )}

                {botDeliveredOtp && (
                  <div className="rounded-lg border border-indigo-500/25 bg-indigo-500/10 px-3 py-2 text-xs text-indigo-300">
                    Bot kodi: <span className="font-mono font-bold">{botDeliveredOtp}</span>
                  </div>
                )}

                <form onSubmit={handleVerifyOtp} className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                      6 Xonali Tasdiqlash Kodi
                    </label>
                    <input
                      type="text"
                      required
                      maxLength={6}
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/[^0-9]/g, ""))}
                      placeholder="000000"
                      className="w-full px-3.5 py-2.5 bg-zinc-900/90 border border-zinc-800 rounded-xl text-sm font-mono tracking-widest text-zinc-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading || otpCode.length !== 6}
                    className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2"
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <span>Kodni tasdiqlash va davom etish</span>
                    )}
                  </button>
                </form>
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <form onSubmit={handleCreateAccount} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                F.I.Sh. (O‘qituvchi yoki Koordinator)
              </label>
              <input
                type="text"
                required
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Karimova Dilfuza"
                className="w-full px-3.5 py-2.5 bg-zinc-900/90 border border-zinc-800 rounded-xl text-xs text-zinc-100 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Parol (kamida 12 ta belgi)
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={12}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Kamida 12 belgi"
                  className="w-full px-3.5 py-2.5 pr-10 bg-zinc-900/90 border border-zinc-800 rounded-xl text-xs text-zinc-100 focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="space-y-2.5 text-xs text-zinc-300 pt-1">
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={adultConfirmed}
                  onChange={(e) => setAdultConfirmed(e.target.checked)}
                  className="mt-0.5 rounded border-zinc-700 bg-zinc-900 text-indigo-500"
                />
                <span>18 yoshdan katta ekanligimni va OTM vakili ekanligimni tasdiqlayman.</span>
              </label>
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={termsAgreed}
                  onChange={(e) => setTermsAgreed(e.target.checked)}
                  className="mt-0.5 rounded border-zinc-700 bg-zinc-900 text-indigo-500"
                />
                <span>
                  <Link href="/shartlar" className="text-indigo-400 hover:underline">
                    Foydalanish shartlari
                  </Link>{" "}
                  va{" "}
                  <Link href="/maxfiylik" className="text-indigo-400 hover:underline">
                    Maxfiylik siyosati
                  </Link>{" "}
                  bilan tanishdim va roziman.
                </span>
              </label>
            </div>

            <div className="flex items-center gap-3 pt-1">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="px-4 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold rounded-xl flex items-center gap-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Orqaga</span>
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <span>Hisobni yaratish</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-bold text-[var(--fb-ink)] flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-indigo-400" />
                <span>OTM Tayinlovlar Ro‘yxati</span>
              </h2>
              <button
                type="button"
                onClick={loadAppointmentInbox}
                disabled={isLoadingInbox}
                className="px-2.5 py-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 text-[11px] font-semibold text-indigo-300 hover:bg-indigo-500/20 inline-flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${isLoadingInbox ? "animate-spin" : ""}`} />
                <span>Yangilash</span>
              </button>
            </div>

            {contacts.length > 0 && (
              <div>
                <label className="block text-[11px] font-medium text-zinc-400 mb-1">
                  Tasdiqlangan kontakt (rozilik uchun)
                </label>
                <select
                  value={selectedContactId}
                  onChange={(e) => setSelectedContactId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-indigo-500"
                >
                  {contacts.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.channel}: {c.masked_destination}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {isLoadingInbox ? (
              <div className="py-6 flex items-center justify-center gap-2 text-xs text-zinc-400">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                <span>Tayinlovlar yuklanmoqda...</span>
              </div>
            ) : appointments.length > 0 ? (
              <div className="space-y-3">
                {appointments.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-xl border border-indigo-500/25 bg-indigo-500/[0.06] p-4 space-y-3 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-[11px] text-indigo-300">
                        #{item.id.slice(0, 8)} • Rev {item.current_revision}
                      </span>
                      <span className="rounded-full border border-indigo-500/30 bg-indigo-500/15 px-2.5 py-0.5 text-[10px] font-semibold text-indigo-300">
                        {item.status} / {item.case_status}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleConsentDecision(item, "ACCEPT")}
                        disabled={isLoading || item.status === "ACTIVE" || item.status === "REVOKED"}
                        className="flex-1 py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold transition-colors"
                      >
                        Tayinlovni tasdiqlash
                      </button>
                      <button
                        type="button"
                        onClick={() => handleConsentDecision(item, "DECLINE")}
                        disabled={isLoading || item.status === "ACTIVE" || item.status === "REVOKED"}
                        className="py-2 px-3 rounded-lg border border-zinc-700 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-50 text-zinc-300 font-semibold transition-colors"
                      >
                        Rad etish
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-white/[0.08] bg-zinc-900/70 p-4 space-y-2 text-xs text-zinc-400">
                <p className="font-semibold text-zinc-200">
                  Hisobingizga hali tayinlov yuborilmagan
                </p>
                <p className="leading-relaxed">
                  Universitet dekanati koordinatori yoki platforma moderatori sizning tasdiqlangan telefon raqamingizga rasmiy tayinlov yuborgach, shu sahifada bir marta bosish bilan tasdiqlab `/university` kabinetiga o‘tasiz.
                </p>
              </div>
            )}
          </div>
        )}

        <div className="pt-4 border-t border-zinc-800/80 text-center">
          <Link
            href="/universitet/kirish"
            className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            ← OTM kirish sahifasiga qaytish
          </Link>
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 text-[11px] text-zinc-500">
        <span className="flex items-center gap-1">
          <Lock className="w-3.5 h-3.5 text-zinc-600" />
          Nomzodlarsiz OTM Registratsiyasi
        </span>
        <span>•</span>
        <span className="flex items-center gap-1">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          SMS & Telegram Tasdiqlash
        </span>
      </div>
    </div>
  );
}

export default function UniversitetRoyxatdanOtishPage() {
  return (
    <div className="min-h-[calc(100vh-3.5rem)] text-[var(--fb-ink)] flex items-center justify-center px-4 py-10">
      <Suspense
        fallback={
          <div className="p-8 text-center text-zinc-400 flex items-center justify-center gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
            <span>Yuklanmoqda...</span>
          </div>
        }
      >
        <UniversitetRegistrationContent />
      </Suspense>
    </div>
  );
}
