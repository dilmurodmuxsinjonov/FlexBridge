"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  GraduationCap,
  Building2,
  School,
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

type RoleOption = "CANDIDATE" | "EMPLOYER" | "ACADEMIC";
type DeliveryMethodOption = "SMS" | "TELEGRAM";

function RoyxatdanOtishWizard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const roleParam = searchParams.get("role");

  // Wizard Step: 1 = Role, 2 = Contact & OTP, 3 = Profile & Password
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [selectedRole, setSelectedRole] = useState<RoleOption>("CANDIDATE");

  useEffect(() => {
    if (roleParam) {
      const upper = roleParam.toUpperCase();
      if (upper === "EMPLOYER" || upper === "ORGANIZATION") {
        setSelectedRole("EMPLOYER");
      } else if (upper === "ACADEMIC" || upper === "UNIVERSITY" || upper === "TEACHER") {
        setSelectedRole("ACADEMIC");
      } else if (upper === "CANDIDATE" || upper === "NOMZOD") {
        setSelectedRole("CANDIDATE");
      }
    }
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
  const [telegramDeepLink, setTelegramDeepLink] = useState<string | null>(null);
  const [telegramVerified, setTelegramVerified] = useState(false);
  const [botStarted, setBotStarted] = useState(false);
  const [botContactPhone, setBotContactPhone] = useState("");
  const [botMessage, setBotMessage] = useState<string | null>(null);
  const [botDeliveredOtp, setBotDeliveredOtp] = useState<string | null>(null);
  const [isBotBusy, setIsBotBusy] = useState(false);
  const [telegramUserId] = useState(() => Math.floor(100000000 + Math.random() * 899999999));

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
        }
      })
      .catch(() => {});

    fetchAuthMe().then((user) => {
      if (isMounted && user) {
        if (user.roles.includes("EMPLOYER")) router.push("/employer");
        else if (user.roles.includes("ACADEMIC")) router.push("/university");
        else router.push("/nomzod");
      }
    });

    return () => {
      isMounted = false;
    };
  }, [router]);

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
    setBotStarted(false);
    setBotMessage(null);
    setBotDeliveredOtp(null);
    setBotContactPhone(phone.trim());

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
  const handleTelegramStart = async () => {
    if (!challengeId) return;
    setIsBotBusy(true);
    setErrorMessage(null);
    try {
      const res = await sendTelegramBotUpdate({
        challenge_id: challengeId,
        message: {
          from: { id: telegramUserId, first_name: displayName || "Nomzod" },
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

  // Step 2 (Telegram Bot): Share native Telegram contact (request_contact=True)
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
          from: { id: telegramUserId, first_name: displayName || "Nomzod" },
          chat: { id: telegramUserId, type: "private" },
          contact: {
            phone_number: botContactPhone.trim(),
            first_name: displayName || "Nomzod",
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
        roles: [selectedRole],
      });

      if (res.ok) {
        setSuccessMessage("Hisobingiz muvaffaqiyatli yaratildi! Kabinetga yo‘naltirilmoqda...");
        setTimeout(() => {
          if (selectedRole === "EMPLOYER") router.push("/employer");
          else if (selectedRole === "ACADEMIC") router.push("/university");
          else router.push("/nomzod");
        }, 800);
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
        <Link href="/" className="inline-flex items-center gap-2 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition">
            FB
          </div>
          <span className="text-xl font-bold tracking-tight text-white">FlexBridge</span>
        </Link>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-100">
          Ro‘yxatdan O‘tish
        </h1>
        <p className="text-xs text-zinc-400">
          Dars jadvaliga mos smenali ishlar va rasmiy amaliyot platformasi
        </p>
      </div>

      {/* Stepper Indicator */}
      <div className="flex items-center justify-between px-2">
        <div className="flex items-center gap-2">
          <div
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${
              step >= 1 ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-500"
            }`}
          >
            1
          </div>
          <span className={`text-xs ${step >= 1 ? "text-zinc-200 font-medium" : "text-zinc-500"}`}>
            Rolni tanlash
          </span>
        </div>
        <div className="w-8 h-[1px] bg-zinc-800" />
        <div className="flex items-center gap-2">
          <div
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${
              step >= 2 ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-500"
            }`}
          >
            2
          </div>
          <span className={`text-xs ${step >= 2 ? "text-zinc-200 font-medium" : "text-zinc-500"}`}>
            Telefon
          </span>
        </div>
        <div className="w-8 h-[1px] bg-zinc-800" />
        <div className="flex items-center gap-2">
          <div
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${
              step >= 3 ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-500"
            }`}
          >
            3
          </div>
          <span className={`text-xs ${step >= 3 ? "text-zinc-200 font-medium" : "text-zinc-500"}`}>
            Profil
          </span>
        </div>
      </div>

      {/* Main Wizard Card */}
      <div className="bg-[#121214] border border-zinc-800/80 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
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
              <h2 className="text-sm font-semibold text-zinc-200">
                Platformadagi faoliyat turini tanlang
              </h2>
              <p className="text-xs text-zinc-400">
                Har bir rol uchun moslashtirilgan xizmatlar va vositalar taqdim etiladi
              </p>
            </div>

            <div className="space-y-3">
              {/* Option 1: Candidate */}
              <div
                onClick={() => setSelectedRole("CANDIDATE")}
                className={`p-4 rounded-xl border cursor-pointer transition flex items-start gap-3.5 ${
                  selectedRole === "CANDIDATE"
                    ? "bg-indigo-950/20 border-indigo-500/80 ring-1 ring-indigo-500/40"
                    : "bg-[#18181b] border-zinc-800 hover:border-zinc-700"
                }`}
              >
                <div
                  className={`p-2.5 rounded-lg shrink-0 ${
                    selectedRole === "CANDIDATE" ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-400"
                  }`}
                >
                  <GraduationCap className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-zinc-100">
                      Talaba / Ish Izlovchi (Nomzod)
                    </span>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Faol
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                    Dars jadvaliga mos amaliyot, smenali ishlar va rasmiy shartnomalar
                  </p>
                </div>
              </div>

              {/* Option 2: Employer */}
              <div
                onClick={() => setSelectedRole("EMPLOYER")}
                className={`p-4 rounded-xl border cursor-pointer transition flex items-start gap-3.5 ${
                  selectedRole === "EMPLOYER"
                    ? "bg-indigo-950/20 border-indigo-500/80 ring-1 ring-indigo-500/40"
                    : "bg-[#18181b] border-zinc-800 hover:border-zinc-700"
                }`}
              >
                <div
                  className={`p-2.5 rounded-lg shrink-0 ${
                    selectedRole === "EMPLOYER" ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-400"
                  }`}
                >
                  <Building2 className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-zinc-100">
                      Ish Beruvchi / Tashkilot
                    </span>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      Korxona
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                    Vakansiya e’lon berish, talaba-amaliyotchilar va jamoa mentorligi
                  </p>
                </div>
              </div>

              {/* Option 3: Academic */}
              <div
                onClick={() => setSelectedRole("ACADEMIC")}
                className={`p-4 rounded-xl border cursor-pointer transition flex items-start gap-3.5 ${
                  selectedRole === "ACADEMIC"
                    ? "bg-indigo-950/20 border-indigo-500/80 ring-1 ring-indigo-500/40"
                    : "bg-[#18181b] border-zinc-800 hover:border-zinc-700"
                }`}
              >
                <div
                  className={`p-2.5 rounded-lg shrink-0 ${
                    selectedRole === "ACADEMIC" ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-400"
                  }`}
                >
                  <School className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-zinc-100">
                      OTM / Ta'lim Muassasasi
                    </span>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      Akademik
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                    Kafedra o‘qituvchilari biriktiruvi va raqamli amaliyot xulosalari
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
              className="w-full py-3 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 mt-4"
            >
              <span>Davom etish</span>
              <ArrowRight className="w-4 h-4" />
            </button>
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
                      setBotStarted(false);
                      setBotMessage(null);
                      setBotDeliveredOtp(null);
                    }}
                    className="text-indigo-400 hover:text-indigo-300 text-[11px] transition"
                  >
                    O‘zgartirish
                  </button>
                </div>

                {/* Telegram Bot Interactive Verification Box */}
                {deliveryMethod === "TELEGRAM" && (
                  <div className="p-4 rounded-xl bg-[#16181d] border border-sky-500/30 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-lg bg-sky-500/20 border border-sky-500/40 flex items-center justify-center text-sky-400">
                          <Send className="w-3.5 h-3.5" />
                        </div>
                        <div>
                          <div className="text-xs font-semibold text-zinc-100">
                            @{telegramBotUsername}
                          </div>
                          <div className="text-[10px] text-zinc-400">
                            Rasmiy telefon raqam tekshiruv boti
                          </div>
                        </div>
                      </div>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                          telegramVerified
                            ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                            : "bg-amber-500/15 text-amber-300 border-amber-500/30"
                        }`}
                      >
                        {telegramVerified ? "✓ Raqam mosligi tasdiqlandi" : "Kontakt kutilmoqda"}
                      </span>
                    </div>

                    {telegramDeepLink && (
                      <div className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-zinc-900/80 border border-zinc-800 text-[11px]">
                        <span className="text-zinc-300 truncate">
                          Telegram ilovasida ochish:{" "}
                          <strong className="text-sky-400">@{telegramBotUsername}</strong>
                        </span>
                        <a
                          href={telegramDeepLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 font-medium transition"
                        >
                          <span>Telegramda ochish</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    )}

                    {/* Bot Step 1: /start */}
                    <div className="space-y-2.5 pt-1 border-t border-zinc-800/80">
                      <div className="text-[11px] text-zinc-400 leading-relaxed">
                        <strong className="text-zinc-200">1-qadam:</strong> Botni ishga tushiring (
                        <code className="text-sky-400">/start</code>) — bot sizdan telefon
                        raqamingizni yuborishni so‘raydi:
                      </div>

                      {!botStarted ? (
                        <button
                          type="button"
                          disabled={isBotBusy}
                          onClick={handleTelegramStart}
                          className="w-full py-2 px-3 rounded-lg bg-sky-600/20 hover:bg-sky-600/30 border border-sky-500/40 text-sky-200 text-xs font-medium transition flex items-center justify-center gap-2"
                        >
                          {isBotBusy ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Send className="w-3.5 h-3.5" />
                          )}
                          <span>Botni ishga tushirish (/start)</span>
                        </button>
                      ) : (
                        <div className="space-y-2.5">
                          {botMessage && (
                            <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 text-[11px] text-zinc-200 whitespace-pre-line leading-relaxed">
                              {botMessage}
                            </div>
                          )}

                          {!telegramVerified ? (
                            <div className="space-y-2">
                              <div className="text-[11px] text-zinc-400">
                                <strong className="text-zinc-200">2-qadam:</strong> Telegram
                                hisobingizdagi telefon raqamni kontakt sifatida yuboring (saytda
                                kiritilgan <code className="text-sky-300">{phone}</code> raqamiga mos
                                kelishi tekshiriladi):
                              </div>
                              <div className="flex gap-2">
                                <input
                                  type="tel"
                                  value={botContactPhone}
                                  onChange={(e) => setBotContactPhone(e.target.value)}
                                  placeholder="+998901234567"
                                  className="flex-1 bg-[#18181b] border border-zinc-700/80 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:outline-none focus:border-sky-500"
                                />
                                <button
                                  type="button"
                                  disabled={isBotBusy}
                                  onClick={handleTelegramShareContact}
                                  className="px-3.5 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:opacity-50 text-white text-xs font-semibold transition flex items-center gap-1.5 shrink-0"
                                >
                                  {isBotBusy ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  ) : (
                                    <Smartphone className="w-3.5 h-3.5" />
                                  )}
                                  <span>📱 Telefon raqamni yuborish</span>
                                </button>
                              </div>
                            </div>
                          ) : (
                            botDeliveredOtp && (
                              <div className="flex items-center justify-between p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs">
                                <span className="text-emerald-300">
                                  Bot kodi: <strong className="font-mono text-sm">{botDeliveredOtp}</strong>
                                </span>
                                <button
                                  type="button"
                                  onClick={() => setOtpCode(botDeliveredOtp)}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-200 text-[11px] font-medium transition"
                                >
                                  <Check className="w-3 h-3" />
                                  <span>Kodni kiritish</span>
                                </button>
                              </div>
                            )
                          )}
                        </div>
                      )}
                    </div>
                  </div>
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
                  Profil va xavfsizlik ma'lumotlari
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
        <span>Shaxsiy ma'lumotlar O'zR qonunchiligi bo'yicha himoyalangan</span>
      </div>
    </div>
  );
}

export default function RoyxatdanOtishPage() {
  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 flex flex-col justify-center items-center py-12 px-4 sm:px-6 lg:px-8">
      {/* Back button */}
      <div className="w-full max-w-lg mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Bosh sahifaga qaytish</span>
        </Link>
      </div>

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
  );
}
