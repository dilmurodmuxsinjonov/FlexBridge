"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Building2,
  Phone,
  ShieldCheck,
  UserCheck,
  Lock,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  ArrowLeft,
  Send,
  KeyRound,
  Briefcase,
} from "lucide-react";
import {
  issueAuthChallenge,
  fetchAuthChallengeStatus,
  sendTelegramBotUpdate,
  consumeAuthChallenge,
  registerCandidateUser,
  fetchAuthOptions,
  fetchAuthMe,
  logoutUser,
} from "@/lib/api";
import { isEmployerRoles } from "@/lib/roles";

interface InvitationPreview {
  organization_name?: string;
  organization_id?: string;
  role_code?: string;
  status?: string;
  expires_at?: string;
}

function KorxonaRegistrationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialToken = searchParams.get("token") || "";

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

  const [inviteToken, setInviteToken] = useState(initialToken);
  const [invitePreview, setInvitePreview] = useState<InvitationPreview | null>(null);
  const [inviteAccepted, setInviteAccepted] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

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
      if (isEmployerRoles(user.roles)) {
        router.push("/employer");
      } else {
        setStep(3);
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
        // Ignore transient polling error
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
            ? "Telegram tasdiqlash so‘rovi yaratildi. Botni ishga tushirib (/start), raqamni ulashing."
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
          from: { id: telegramUserId, first_name: displayName || "Korxona vakili" },
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
          from: { id: telegramUserId, first_name: displayName || "Korxona vakili" },
          chat: { id: telegramUserId, type: "private" },
          contact: {
            phone_number: botContactPhone.trim() || phone.trim(),
            first_name: displayName || "Korxona vakili",
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
        setSuccessMessage("Vakil hisobi yaratildi! Endi tashkilotga ulanish bosqichiga o‘ting.");
        setStep(3);
      } else {
        setErrorMessage("Hisob yaratishda xatolik yuz berdi.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Ro‘yxatdan o‘tishda xatolik.");
    } finally {
      setIsLoading(false);
    }
  };

  const handlePreviewInvitation = async () => {
    const token = inviteToken.trim();
    if (!token) {
      setErrorMessage("Taklif tokenini kiriting.");
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    setInvitePreview(null);
    try {
      const res = await fetch(`/api/bff/invitations/${encodeURIComponent(token)}`, {
        method: "GET",
        cache: "no-store",
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        setErrorMessage(data.message || data.error || "Taklif topilmadi.");
        return;
      }
      setInvitePreview(data);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Taklifni tekshirishda xatolik.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAcceptInvitation = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = inviteToken.trim();
    if (!token) {
      setErrorMessage("Taklif tokenini kiriting.");
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const res = await fetch(`/api/bff/invitations/${encodeURIComponent(token)}/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        setErrorMessage(data.message || data.error || "Taklifni qabul qilib bo‘lmadi.");
        return;
      }
      window.dispatchEvent(new Event("flexbridge:auth-changed"));
      setInviteAccepted(true);
      setSuccessMessage("Korxona jamoasiga muvaffaqiyatli qo‘shildingiz! HR kabinetga yo‘naltirilmoqda...");
      setTimeout(() => {
        router.push("/employer");
        router.refresh();
      }, 600);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Taklifni tasdiqlashda xatolik.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen text-[var(--fb-ink)] py-10 px-4 sm:px-6 lg:px-8 flex items-center justify-center">
      <div className="w-full max-w-2xl space-y-6">
        <div className="flex items-center justify-between gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Bosh sahifa</span>
          </Link>
          <span className="text-[11px] font-mono text-emerald-400">
            KORXONA VAKILI RO‘YXATDAN O‘TISHI
          </span>
        </div>

        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-300">
            <Building2 className="w-4 h-4 text-emerald-400" />
            <span>Korxona / HR & Mentor Ro‘yxatdan O‘tishi</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">
            Korxona Jamoasiga Ulanish
          </h1>
          <p className="text-xs text-zinc-400">
            Vakil hisobini yarating va tashkilot taklif tokeni orqali Korxona kabinetiga ulaning.
          </p>
        </div>

        {/* 3-Step Indicator */}
        <div className="flex items-center justify-center gap-2">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all border ${
                  step === s
                    ? "bg-emerald-600 text-white border-emerald-500 shadow-lg shadow-emerald-600/25"
                    : step > s
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                    : "bg-zinc-900 text-zinc-500 border-zinc-800"
                }`}
              >
                {step > s ? <CheckCircle2 className="w-4 h-4" /> : s}
              </div>
              <span
                className={`text-xs font-medium hidden sm:inline ${
                  step === s ? "text-zinc-100" : "text-zinc-500"
                }`}
              >
                {s === 1
                  ? "1. Telefon Tasdiqlash"
                  : s === 2
                  ? "2. Vakil Profili"
                  : "3. Korxona Taklifi"}
              </span>
              {s < 3 && <div className="w-8 h-px bg-zinc-800" />}
            </div>
          ))}
        </div>

        <div className="bg-[#121214] border border-emerald-500/20 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
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

          {step === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-zinc-100">
                  Vakil telefon raqamini tasdiqlang
                </h2>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Kodni SMS yoki Telegram bot orqali oling.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setDeliveryMethod("SMS");
                    setChallengeId(null);
                    setErrorMessage(null);
                  }}
                  className={`p-3 rounded-xl border text-left transition flex items-center gap-2.5 ${
                    deliveryMethod === "SMS"
                      ? "border-emerald-500 bg-emerald-500/10 text-zinc-100"
                      : "border-zinc-800 bg-[#09090b] text-zinc-400 hover:border-zinc-700"
                  }`}
                >
                  <Phone className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div>
                    <div className="text-xs font-semibold">SMS xabar orqali</div>
                    <div className="text-[10px] text-zinc-500">Telefon raqamga</div>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setDeliveryMethod("TELEGRAM");
                    setChallengeId(null);
                    setErrorMessage(null);
                  }}
                  className={`p-3 rounded-xl border text-left transition flex items-center gap-2.5 ${
                    deliveryMethod === "TELEGRAM"
                      ? "border-emerald-500 bg-emerald-500/10 text-zinc-100"
                      : "border-zinc-800 bg-[#09090b] text-zinc-400 hover:border-zinc-700"
                  }`}
                >
                  <Send className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div>
                    <div className="text-xs font-semibold">Telegram Bot</div>
                    <div className="text-[10px] text-zinc-500">@{telegramBotUsername}</div>
                  </div>
                </button>
              </div>

              <form onSubmit={handleSendChallenge} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                    Telefon raqamingiz
                  </label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Phone className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="tel"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        placeholder="+998901234567"
                        required
                        className="w-full bg-[#09090b] border border-zinc-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={isLoading || resendTimer > 0}
                      className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white text-xs font-semibold rounded-xl transition shrink-0"
                    >
                      {resendTimer > 0
                        ? `${resendTimer}s`
                        : challengeId
                        ? "Qayta yuborish"
                        : "Kod yuborish"}
                    </button>
                  </div>
                </div>
              </form>

              {challengeId && deliveryMethod === "TELEGRAM" && (
                <div className="p-4 rounded-xl border border-emerald-500/25 bg-[#09090b] space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-emerald-300">
                      Telegram Bot (@{telegramBotUsername})
                    </span>
                    {telegramVerified && (
                      <span className="text-emerald-400 font-semibold">Tasdiqlandi</span>
                    )}
                  </div>
                  {telegramDeepLink && (
                    <a
                      href={telegramDeepLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs text-emerald-400 hover:underline"
                    >
                      <span>Telegram botni ochish</span>
                      <ArrowRight className="w-3 h-3" />
                    </a>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={handleBotStart}
                      disabled={isLoading || botStarted}
                      className="px-3 py-1.5 rounded-lg border border-zinc-700 text-xs text-zinc-200 hover:bg-zinc-800 disabled:opacity-50"
                    >
                      1. Bot /start
                    </button>
                    <button
                      type="button"
                      onClick={handleBotShareContact}
                      disabled={isLoading || !botStarted || telegramVerified}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white disabled:opacity-50"
                    >
                      2. Raqamni ulashish
                    </button>
                  </div>
                  {botMessage && <p className="text-[11px] text-zinc-400">{botMessage}</p>}
                  {botDeliveredOtp && (
                    <p className="text-xs font-mono text-emerald-300">
                      Bot kodi: {botDeliveredOtp}
                    </p>
                  )}
                </div>
              )}

              {challengeId && (
                <form
                  onSubmit={handleVerifyOtp}
                  className="pt-4 border-t border-zinc-800/80 space-y-4"
                >
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                      Tasdiqlash kodi
                    </label>
                    <div className="relative">
                      <KeyRound className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        inputMode="numeric"
                        maxLength={8}
                        value={otpCode}
                        onChange={(e) => setOtpCode(e.target.value)}
                        placeholder="123456"
                        required
                        className="w-full bg-[#09090b] border border-zinc-800 rounded-xl pl-10 pr-4 py-2.5 text-center font-mono text-lg tracking-widest text-zinc-100 placeholder:text-zinc-700 focus:outline-none focus:border-emerald-500 transition"
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 text-white font-semibold py-2.5 px-4 rounded-xl text-sm transition flex items-center justify-center gap-2"
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

          {step === 2 && (
            <form onSubmit={handleCreateAccount} className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-zinc-100">
                  Vakil ma’lumotlari va xavfsiz parol
                </h2>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Hisob yaratilgach, tashkilot taklif tokeni orqali HR/Mentor rolini faollashtirasiz.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  To‘liq ismingiz (F.I.Sh.)
                </label>
                <div className="relative">
                  <UserCheck className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="Masalan: Dilshod Karimov"
                    required
                    className="w-full bg-[#09090b] border border-zinc-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  Kuchli parol (kamida 12 ta belgi)
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Kamida 12 ta belgi"
                    minLength={12}
                    required
                    className="w-full bg-[#09090b] border border-zinc-800 rounded-xl pl-10 pr-10 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                    aria-label="Parolni ko‘rsatish"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-2.5 pt-2">
                <label className="flex items-start gap-2.5 text-xs text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={adultConfirmed}
                    onChange={(e) => setAdultConfirmed(e.target.checked)}
                    className="mt-0.5 rounded border-zinc-700 bg-zinc-900 text-emerald-500 focus:ring-emerald-500"
                  />
                  <span>18 yoshdan oshganman va korxona vakili sifatida harakat qilaman.</span>
                </label>
                <label className="flex items-start gap-2.5 text-xs text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={termsAgreed}
                    onChange={(e) => setTermsAgreed(e.target.checked)}
                    className="mt-0.5 rounded border-zinc-700 bg-zinc-900 text-emerald-500 focus:ring-emerald-500"
                  />
                  <span>
                    <Link href="/shartlar" className="text-emerald-400 hover:underline">
                      Foydalanish shartlari ({termsVersion})
                    </Link>{" "}
                    va{" "}
                    <Link href="/maxfiylik" className="text-emerald-400 hover:underline">
                      Maxfiylik siyosati ({privacyVersion})
                    </Link>
                    ga roziman.
                  </span>
                </label>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 text-white font-semibold py-2.5 px-4 rounded-xl text-sm transition flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Saqlanmoqda...</span>
                  </>
                ) : (
                  <>
                    <span>Hisob Yaratish va Keyingi Bosqich</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {step === 3 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-lg font-semibold text-zinc-100">
                  Korxona Taklif Tokenini Faollashtirish
                </h2>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Tashkilot rahbari yoki administrator tomonidan yuborilgan 43 belgili taklif tokenini kiriting.
                </p>
              </div>

              <form onSubmit={handleAcceptInvitation} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                    Taklif tokeni (43 belgi)
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={inviteToken}
                      onChange={(e) => setInviteToken(e.target.value)}
                      placeholder="Taklif tokenini kiriting"
                      className="flex-1 bg-[#09090b] border border-zinc-800 rounded-xl px-3.5 py-2.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition"
                    />
                    <button
                      type="button"
                      onClick={handlePreviewInvitation}
                      disabled={isLoading || !inviteToken.trim()}
                      className="px-3.5 py-2.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-50"
                    >
                      Tekshirish
                    </button>
                  </div>
                </div>

                {invitePreview && (
                  <div className="rounded-xl border border-emerald-500/25 bg-[#09090b] p-3.5 text-xs space-y-1">
                    <p className="font-semibold text-emerald-300">
                      Tashkilot: {invitePreview.organization_name || invitePreview.organization_id || "Tasdiqlangan"}
                    </p>
                    <p className="text-zinc-400">
                      Beriladigan rol:{" "}
                      <span className="font-mono text-zinc-200">{invitePreview.role_code || "HR"}</span>
                    </p>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isLoading || inviteAccepted || !inviteToken.trim()}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/40 text-white font-semibold py-2.5 px-4 rounded-xl text-sm transition flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Faollashtirilmoqda...</span>
                    </>
                  ) : (
                    <>
                      <Briefcase className="w-4 h-4" />
                      <span>Korxona Jamoasiga Qo‘shilish</span>
                    </>
                  )}
                </button>
              </form>

              <div className="rounded-xl border border-white/[0.08] bg-[#09090b]/70 p-4 space-y-2 text-xs text-zinc-400">
                <p className="font-semibold text-zinc-200">
                  Agar yangi korxona ochmoqchi bo‘lsangiz:
                </p>
                <p className="text-[11px] leading-relaxed">
                  Yangi korxonani ro‘yxatdan o‘tkazish uchun STIR va davlat ro‘yxatidan o‘tganlik guvohnomasi (<span className="font-mono text-zinc-300">API-065</span>) platforma moderatori tomonidan tasdiqlanishi talab etiladi. Tasdiqdan so‘ng korxona nomidan e’lon berish huquqi avtomatik ochiladi.
                </p>
                <div className="pt-1 flex flex-wrap gap-3">
                  <Link
                    href="/korxona/kirish"
                    className="font-semibold text-emerald-400 hover:text-emerald-300 transition"
                  >
                    Korxona kirishiga o‘tish &rarr;
                  </Link>
                  <button
                    type="button"
                    onClick={async () => {
                      await logoutUser();
                      setStep(1);
                    }}
                    className="text-zinc-500 hover:text-zinc-300 transition"
                  >
                    Sessiyadan chiqish
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="pt-4 border-t border-zinc-800/80 flex items-center justify-between text-xs text-zinc-400">
            <span>Allaqachon korxona hisobingiz bormi?</span>
            <Link
              href="/korxona/kirish"
              className="text-emerald-400 hover:text-emerald-300 font-semibold transition"
            >
              Korxona kirishi &rarr;
            </Link>
          </div>
        </div>

        <div className="flex items-center justify-center gap-6 text-[11px] text-zinc-500">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            Korxona Rollari Nazorati
          </span>
        </div>
      </div>
    </div>
  );
}

export default function KorxonaRoyxatdanOtishPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#09090b] flex items-center justify-center text-xs text-zinc-400 gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Yuklanmoqda...</span>
        </div>
      }
    >
      <KorxonaRegistrationContent />
    </Suspense>
  );
}
