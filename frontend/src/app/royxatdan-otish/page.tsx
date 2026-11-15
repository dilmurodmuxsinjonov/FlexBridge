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
} from "lucide-react";
import {
  fetchAuthOptions,
  issueAuthChallenge,
  consumeAuthChallenge,
  registerCandidateUser,
  fetchAuthMe,
} from "@/lib/api";

type RoleOption = "CANDIDATE" | "EMPLOYER" | "ACADEMIC";

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
  const [phone, setPhone] = useState("+998");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [verificationToken, setVerificationToken] = useState<string | null>(null);
  const [resendTimer, setResendTimer] = useState(0);

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

    try {
      const res = await issueAuthChallenge(channel, phone.trim(), "REGISTER");
      if (res.ok && res.challenge_id) {
        setChallengeId(res.challenge_id);
        setResendTimer(res.resend_after || 60);
        setSuccessMessage("Tasdiqlash kodi ko'rsatilgan manzilga yuborildi.");
      } else {
        setErrorMessage("Tasdiqlash kodini yuborishda xatolik yuz berdi.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: Verify OTP Code
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!challengeId || otpCode.trim().length !== 6) {
      setErrorMessage("6 xonali SMS kodini to‘liq kiriting.");
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
                  Xavfsizlik va kirish uchun shaxsiy telefon raqamingizni tasdiqlang
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
                  <p className="text-[11px] text-zinc-500 mt-1">
                    Ushbu raqamga bir martalik 6 xonali SMS tasdiqlash kodi yuboriladi
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-3 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Yuborilmoqda...</span>
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
                  <div className="text-zinc-300 font-mono">{phone}</div>
                  <button
                    type="button"
                    onClick={() => {
                      setChallengeId(null);
                      setOtpCode("");
                    }}
                    className="text-indigo-400 hover:text-indigo-300 text-[11px] transition"
                  >
                    O‘zgartirish
                  </button>
                </div>

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
                  disabled={isLoading || otpCode.length !== 6}
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
