"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  GraduationCap,
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
  ExternalLink,
  Check,
} from "lucide-react";
import {
  fetchAuthOptions,
  issueAuthChallenge,
  fetchAuthChallengeStatus,
  sendTelegramBotUpdate,
  consumeAuthChallenge,
  registerCandidateUser,
  fetchAuthMe,
} from "@/lib/api";

type DeliveryMethodOption = "SMS" | "TELEGRAM";

function TalabaRoyxatdanOtishWizard() {
  const router = useRouter();

  // Streamlined 2-Step Student Wizard (1 = Telefon & OTP, 2 = Talaba Profili & Parol)
  const [step, setStep] = useState<1 | 2>(1);

  // Step 1 State
  const [deliveryMethod, setDeliveryMethod] = useState<DeliveryMethodOption>("SMS");
  const [phone, setPhone] = useState("+998");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [verificationToken, setVerificationToken] = useState<string | null>(null);
  const [resendTimer, setResendTimer] = useState(0);

  // Telegram Bot State
  const [telegramBotUsername, setTelegramBotUsername] = useState("FlexBridgeAuthBot");
  const [telegramDeepLink, setTelegramDeepLink] = useState<string | null>(null);
  const [telegramVerified, setTelegramVerified] = useState(false);
  const [botStarted, setBotStarted] = useState(false);
  const [botContactPhone, setBotContactPhone] = useState("");
  const [botMessage, setBotMessage] = useState<string | null>(null);
  const [botDeliveredOtp, setBotDeliveredOtp] = useState<string | null>(null);
  const [isBotBusy, setIsBotBusy] = useState(false);
  const [telegramUserId] = useState(() => Math.floor(100000000 + Math.random() * 899999999));

  // Step 2 State
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [adultConfirmed, setAdultConfirmed] = useState(false);
  const [termsAgreed, setTermsAgreed] = useState(false);

  const [termsVersion, setTermsVersion] = useState("2026.1");
  const [privacyVersion, setPrivacyVersion] = useState("2026.1");

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
      if (user.roles.includes("CANDIDATE")) {
        router.push("/nomzod");
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
        // Ignore transient status polling error
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
            ? "Telegram tasdiqlash so‘rovi yaratildi! Botni ishga tushirib (/start), telefon raqamingizni yuboring."
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

  const handleTelegramStart = async () => {
    if (!challengeId) return;
    setIsBotBusy(true);
    setErrorMessage(null);
    try {
      const res = await sendTelegramBotUpdate({
        challenge_id: challengeId,
        message: {
          from: { id: telegramUserId, first_name: displayName || "Talaba" },
          chat: { id: telegramUserId, type: "private" },
          text: `/start ${challengeId}`,
        },
      });
      setBotStarted(true);
      setBotMessage(res.bot_message);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Botni ishga tushirishda xatolik.");
    } finally {
      setIsBotBusy(false);
    }
  };

  const handleTelegramShareContact = async () => {
    if (!challengeId) return;
    if (!botContactPhone.trim()) {
      setErrorMessage("Telegram botda yuboriladigan telefon raqamni kiriting.");
      return;
    }
    setIsBotBusy(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const res = await sendTelegramBotUpdate({
        challenge_id: challengeId,
        message: {
          from: { id: telegramUserId, first_name: displayName || "Talaba" },
          chat: { id: telegramUserId, type: "private" },
          contact: {
            phone_number: botContactPhone.trim(),
            first_name: displayName || "Talaba",
            user_id: telegramUserId,
          },
        },
      });
      setBotMessage(res.bot_message);
      if (res.telegram_verified) {
        setTelegramVerified(true);
        if (res.otp_code) {
          setBotDeliveredOtp(res.otp_code);
        }
        setSuccessMessage(
          "Saytda kiritilgan raqam va Telegram raqamingiz mos keldi! 6 xonali kod botga yuborildi."
        );
      }
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Telegram raqamni tekshirishda xatolik yuz berdi."
      );
    } finally {
      setIsBotBusy(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!challengeId || otpCode.trim().length !== 6) {
      setErrorMessage("6 xonali tasdiqlash kodini to‘liq kiriting.");
      return;
    }

    if (deliveryMethod === "TELEGRAM" && !telegramVerified) {
      setErrorMessage(
        "Avval Telegram bot orqali telefon raqamingizni yuborib, mosligini tasdiqlang."
      );
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await consumeAuthChallenge(challengeId, "REGISTER", otpCode.trim());
      if (res.ok && res.verification_token) {
        setVerificationToken(res.verification_token);
        setSuccessMessage("Telefon raqamingiz tasdiqlandi!");
        setTimeout(() => {
          setSuccessMessage(null);
          setStep(2);
        }, 400);
      } else {
        setErrorMessage("Kiritilgan tasdiqlash kodi noto‘g‘ri yoki muddati o‘tgan.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Kodni tasdiqlashda xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompleteRegistration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verificationToken) {
      setErrorMessage("Telefon raqam tasdiqlanishi shart.");
      setStep(1);
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
        password,
        adult_confirmed: adultConfirmed,
        terms_version: termsVersion,
        privacy_version: privacyVersion,
        roles: ["CANDIDATE"],
      });

      if (res.ok) {
        setSuccessMessage("Talaba hisobingiz yaratildi! Kabinetga yo‘naltirilmoqda...");
        setTimeout(() => {
          router.push("/nomzod");
        }, 700);
      } else {
        setErrorMessage("Ro‘yxatdan o‘tishda xatolik yuz berdi.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Ro‘yxatdan o‘tishda xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  const strength =
    password.length === 0
      ? { label: "", score: 0, color: "bg-zinc-700" }
      : password.length < 8
      ? { label: "Juda zaif", score: 1, color: "bg-rose-500" }
      : password.length < 12
      ? { label: "Kamida 12 belgi", score: 2, color: "bg-amber-500" }
      : /\d/.test(password) && /[^A-Za-z0-9]/.test(password)
      ? { label: "Mustahkam", score: 4, color: "bg-emerald-500" }
      : { label: "Yaxshi", score: 3, color: "bg-sky-500" };

  return (
    <div className="w-full max-w-lg space-y-5">
      <div className="space-y-2 text-center lg:text-left">
        <div className="inline-flex items-center gap-2 rounded-full border border-sky-500/25 bg-sky-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-sky-400">
          <GraduationCap className="h-3.5 w-3.5" />
          <span>Talaba Ro‘yxatdan O‘tishi</span>
        </div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-white">
          Talaba Hisobini Yaratish
        </h1>
        <p className="text-xs text-zinc-400">
          Faqat Talaba / Nomzod funksiyalari uchun ajratilgan ro‘yxatdan o‘tish jarayoni
        </p>
      </div>

      {/* 2-Step Indicator */}
      <div className="flex items-center gap-3 px-1 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-sky-600 text-white flex items-center justify-center font-semibold text-[11px]">
            1
          </div>
          <span className={step === 1 ? "font-semibold text-white" : "text-zinc-400"}>
            Telefon tasdig‘i
          </span>
        </div>
        <div className="flex-1 h-px bg-zinc-800" />
        <div className="flex items-center gap-2">
          <div
            className={`w-6 h-6 rounded-full flex items-center justify-center font-semibold text-[11px] ${
              step === 2 ? "bg-sky-600 text-white" : "bg-zinc-800 text-zinc-500"
            }`}
          >
            2
          </div>
          <span className={step === 2 ? "font-semibold text-white" : "text-zinc-500"}>
            Talaba profili &amp; Parol
          </span>
        </div>
      </div>

      <div className="rounded-2xl border border-sky-500/20 bg-[#121214] p-6 sm:p-7 shadow-2xl space-y-5">
        {errorMessage && (
          <div className="p-3.5 bg-rose-500/10 border border-rose-500/25 rounded-xl flex items-start gap-3 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
        )}
        {successMessage && (
          <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/25 rounded-xl flex items-start gap-3 text-xs text-emerald-300">
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-400" />
            <span>{successMessage}</span>
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
                  setOtpCode("");
                  setTelegramVerified(false);
                }}
                className={`p-3 rounded-xl border text-left transition ${
                  deliveryMethod === "SMS"
                    ? "bg-sky-500/10 border-sky-500/40 text-white"
                    : "bg-[#18181b] border-zinc-800 text-zinc-400 hover:border-zinc-700"
                }`}
              >
                <div className="flex items-center gap-2 text-xs font-semibold">
                  <MessageSquare className="w-4 h-4 text-sky-400" />
                  <span>SMS orqali</span>
                </div>
                <p className="text-[11px] text-zinc-400 mt-1">6 xonali SMS kod</p>
              </button>

              <button
                type="button"
                onClick={() => {
                  setDeliveryMethod("TELEGRAM");
                  setChallengeId(null);
                  setOtpCode("");
                  setTelegramVerified(false);
                }}
                className={`p-3 rounded-xl border text-left transition ${
                  deliveryMethod === "TELEGRAM"
                    ? "bg-sky-500/10 border-sky-500/40 text-white"
                    : "bg-[#18181b] border-zinc-800 text-zinc-400 hover:border-zinc-700"
                }`}
              >
                <div className="flex items-center gap-2 text-xs font-semibold">
                  <Send className="w-4 h-4 text-sky-400" />
                  <span>Telegram orqali</span>
                </div>
                <p className="text-[11px] text-zinc-400 mt-1">@{telegramBotUsername} orqali</p>
              </button>
            </div>

            <form onSubmit={handleSendChallenge} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  Telefon raqamingiz
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <input
                      type="tel"
                      required
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+998901234567"
                      className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-2.5 text-sm font-mono text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-sky-500 transition"
                    />
                    <Smartphone className="w-4 h-4 text-zinc-500 absolute right-3.5 top-3" />
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading || resendTimer > 0}
                    className="px-4 py-2.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-zinc-200 rounded-xl text-xs font-semibold whitespace-nowrap transition"
                  >
                    {resendTimer > 0
                      ? `${resendTimer}s`
                      : deliveryMethod === "TELEGRAM"
                      ? challengeId
                        ? "Qayta yaratish"
                        : "Bot kod olish"
                      : challengeId
                      ? "Qayta yuborish"
                      : "SMS kod olish"}
                  </button>
                </div>
              </div>
            </form>

            {challengeId && deliveryMethod === "TELEGRAM" && (
              <div className="p-4 rounded-xl bg-sky-950/30 border border-sky-500/30 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-sky-300">
                    <Send className="w-4 h-4" />
                    <span>Telegram Bot: @{telegramBotUsername}</span>
                  </div>
                  {telegramDeepLink && (
                    <a
                      href={telegramDeepLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 underline"
                    >
                      <span>Telegramda ochish</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>

                {!botStarted ? (
                  <button
                    type="button"
                    disabled={isBotBusy}
                    onClick={handleTelegramStart}
                    className="w-full py-2.5 px-3 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>1-qadam: Botni ishga tushirish (/start)</span>
                  </button>
                ) : !telegramVerified ? (
                  <div className="space-y-2.5">
                    {botMessage && (
                      <div className="p-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800 text-[11px] text-zinc-300 whitespace-pre-line">
                        {botMessage}
                      </div>
                    )}
                    <div className="flex gap-2">
                      <input
                        type="tel"
                        value={botContactPhone}
                        onChange={(e) => setBotContactPhone(e.target.value)}
                        placeholder="+998901234567"
                        className="flex-1 bg-[#18181b] border border-zinc-700 rounded-lg px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-sky-500"
                      />
                      <button
                        type="button"
                        disabled={isBotBusy}
                        onClick={handleTelegramShareContact}
                        className="px-3.5 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold whitespace-nowrap transition"
                      >
                        Raqamni yuborish
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/25 space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-semibold text-emerald-300">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Raqamlar mos keldi va tasdiqlandi!</span>
                    </div>
                    {botDeliveredOtp && (
                      <div className="flex items-center justify-between pt-1 border-t border-emerald-500/20">
                        <span className="text-[11px] text-zinc-300">
                          Bot yuborgan kod:{" "}
                          <strong className="font-mono text-white">{botDeliveredOtp}</strong>
                        </span>
                        <button
                          type="button"
                          onClick={() => setOtpCode(botDeliveredOtp)}
                          className="text-[11px] font-semibold text-sky-400 hover:text-sky-300 underline"
                        >
                          Maydonga kiritish
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {challengeId && (
              <form onSubmit={handleVerifyOtp} className="space-y-3 pt-2 border-t border-zinc-800/80">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                    6 xonali tasdiqlash kodi
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      maxLength={6}
                      required
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                      placeholder="123456"
                      className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-2.5 text-center text-lg tracking-widest font-mono text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-sky-500 transition"
                    />
                    <KeyRound className="w-4 h-4 text-zinc-500 absolute left-3.5 top-3" />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={
                    isLoading ||
                    otpCode.length !== 6 ||
                    (deliveryMethod === "TELEGRAM" && !telegramVerified)
                  }
                  className="w-full py-3 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2"
                >
                  <span>Tasdiqlash &amp; Davom etish</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </form>
            )}
          </div>
        )}

        {step === 2 && (
          <form onSubmit={handleCompleteRegistration} className="space-y-4">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-center gap-2">
              <Check className="w-4 h-4 shrink-0" />
              <span>Telefon tasdiqlandi: {phone}</span>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                To‘liq Ismingiz (F.I.Sh.)
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Masalan: Jasurbek Alimov"
                  className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-sky-500 transition"
                />
                <User className="w-4 h-4 text-zinc-500 absolute right-3.5 top-3" />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-zinc-300">
                  Parol (kamida 12 ta belgi)
                </label>
                {strength.label && (
                  <span className="text-[11px] font-medium text-zinc-400">{strength.label}</span>
                )}
              </div>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={12}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Kamida 12 ta belgi"
                  className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-sky-500 transition pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-3 text-zinc-400 hover:text-zinc-200 transition"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {password.length > 0 && (
                <div className="flex gap-1 mt-1.5 h-1">
                  {[1, 2, 3, 4].map((lvl) => (
                    <div
                      key={lvl}
                      className={`flex-1 rounded-full ${
                        lvl <= strength.score ? strength.color : "bg-zinc-800"
                      }`}
                    />
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Parolni tasdiqlang
              </label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Parolni qayta kiriting"
                className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-sky-500 transition"
              />
            </div>

            <div className="space-y-2.5 pt-2 border-t border-zinc-800/80 text-xs text-zinc-300">
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={adultConfirmed}
                  onChange={(e) => setAdultConfirmed(e.target.checked)}
                  className="mt-0.5 rounded border-zinc-700 bg-zinc-900 text-sky-600 focus:ring-sky-500"
                />
                <span>18 yoshga to‘lganman va qonuniy mehnat layoqatiga egaman</span>
              </label>
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={termsAgreed}
                  onChange={(e) => setTermsAgreed(e.target.checked)}
                  className="mt-0.5 rounded border-zinc-700 bg-zinc-900 text-sky-600 focus:ring-sky-500"
                />
                <span>
                  <Link href="/shartlar" className="text-sky-400 underline">
                    Foydalanish shartlari
                  </Link>{" "}
                  va{" "}
                  <Link href="/maxfiylik" className="text-sky-400 underline">
                    Maxfiylik siyosati
                  </Link>{" "}
                  bilan tanishdim
                </span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Hisob yaratilmoqda...</span>
                </>
              ) : (
                <>
                  <span>Talaba hisobini yaratish</span>
                  <CheckCircle2 className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        )}

        <div className="pt-4 border-t border-zinc-800/80 text-center">
          <p className="text-xs text-zinc-400">
            Allaqachon talaba hisobingiz bormi?{" "}
            <Link
              href="/talaba/kirish"
              className="text-sky-400 hover:text-sky-300 font-semibold underline underline-offset-2 transition"
            >
              Talaba kirishiga o‘tish
            </Link>
          </p>
        </div>
      </div>

      <div className="flex items-center justify-center gap-2 text-[11px] text-zinc-500">
        <Shield className="w-3.5 h-3.5 text-zinc-600" />
        <span>Hisob turi: faqat Talaba / Nomzod (CANDIDATE)</span>
      </div>
    </div>
  );
}

export default function TalabaRoyxatdanOtishPage() {
  return (
    <div className="min-h-screen text-[var(--fb-ink)] py-10 px-4 sm:px-6 lg:px-8 flex items-center justify-center">
      <div className="w-full max-w-2xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link
            href="/talaba/kirish"
            className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Talaba kirishiga qaytish</span>
          </Link>
          <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-300 transition">
            E’lonlar katalogi →
          </Link>
        </div>

        <div className="flex justify-center">
          <Suspense
            fallback={
              <div className="p-8 text-center text-zinc-400 flex items-center justify-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-sky-400" />
                <span>Yuklanmoqda...</span>
              </div>
            }
          >
            <TalabaRoyxatdanOtishWizard />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
