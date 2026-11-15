"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  GraduationCap,
  Lock,
  ArrowRight,
  Eye,
  EyeOff,
  ShieldCheck,
  AlertCircle,
  Loader2,
  CheckCircle2,
  KeyRound,
  ArrowLeft,
  Smartphone,
  FileText,
  BookOpen,
  Award,
  Search,
  LogOut,
} from "lucide-react";
import { loginUser, verifyMfa, fetchAuthMe, logoutUser, AuthUser } from "@/lib/api";
import { isStudentOnlyRoles, resolvePortalDashboard } from "@/lib/roles";

const STUDENT_PERMITTED_FEATURES = [
  {
    icon: FileText,
    title: "Kasbiy Profil, Rezyume & HEMIS",
    desc: "Shaxsiy rezyume, sertifikatlar, portfel va PDF CV eksporti.",
  },
  {
    icon: Search,
    title: "Dars Jadvaliga Mos Vakansiyalar",
    desc: "HEMIS jadvali bilan ziddiyatsiz smenali ishlar, ariza va saqlash.",
  },
  {
    icon: BookOpen,
    title: "Amaliyot Shartnomalari & Kundalik",
    desc: "Standart kundalik (1-hujjat), yakuniy xulosa (2-hujjat) va E-Imzo.",
  },
  {
    icon: Award,
    title: "Baholar, Apellyatsiya & 2FA Himoya",
    desc: "Reytinglar, bildirishnomalar, TOTP 2FA va texnik yordam.",
  },
];

function resolveNonCandidateHome(roles: string[]): { href: string; label: string } {
  const dash = resolvePortalDashboard(roles);
  return { href: dash.href, label: `${dash.label}ga o‘tish` };
}

function TalabaKirishForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get("redirect");

  const [destination, setDestination] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaTicket, setMfaTicket] = useState<string | null>(null);
  const [totpCode, setTotpCode] = useState("");

  const [existingWrongRoleUser, setExistingWrongRoleUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const goToStudentCabinet = useCallback(() => {
    if (redirectParam && (redirectParam.startsWith("/nomzod") || redirectParam === "/")) {
      router.push(redirectParam);
      return;
    }
    router.push("/nomzod");
  }, [redirectParam, router]);

  useEffect(() => {
    let active = true;
    fetchAuthMe().then((user) => {
      if (!active || !user) return;
      if (isStudentOnlyRoles(user.roles)) {
        goToStudentCabinet();
      } else {
        setExistingWrongRoleUser(user);
      }
    });
    return () => {
      active = false;
    };
  }, [goToStudentCabinet]);

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!destination.trim() || !password) {
      setErrorMessage("Telefon raqam/pochta va parolni kiriting.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await loginUser(destination.trim(), password, undefined, "CANDIDATE");
      if (res.ok) {
        if (res.mfa_required && res.mfa_ticket) {
          setMfaRequired(true);
          setMfaTicket(res.mfa_ticket);
          setSuccessMessage("Ikki bosqichli tasdiqlash (2FA) kodi talab etiladi.");
        } else {
          setSuccessMessage("Talaba kabinetiga muvaffaqiyatli kirildi! Yo‘naltirilmoqda...");
          setTimeout(() => {
            goToStudentCabinet();
          }, 500);
        }
      } else {
        setErrorMessage(res.error || "Kirish ma’lumotlari noto‘g‘ri.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Tizimga kirishda xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mfaTicket || totpCode.trim().length !== 6) {
      setErrorMessage("6 xonali 2FA kodini to‘liq kiriting.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await verifyMfa(mfaTicket, totpCode.trim(), "CANDIDATE");
      if (res.ok) {
        setSuccessMessage("MFA tasdiqlandi! Talaba kabinetiga yo‘naltirilmoqda...");
        setTimeout(() => {
          goToStudentCabinet();
        }, 500);
      } else {
        setErrorMessage(res.error || "Kiritilgan 2FA kodi yaroqsiz yoki eskirgan.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "MFA tasdiqlashda xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSwitchAccount = async () => {
    await logoutUser();
    setExistingWrongRoleUser(null);
    setErrorMessage(null);
  };

  if (existingWrongRoleUser) {
    const ownPortal = resolveNonCandidateHome(existingWrongRoleUser.roles);
    return (
      <div className="w-full max-w-md rounded-2xl border border-amber-500/25 bg-[#121214] p-7 space-y-5 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-amber-500/25 bg-amber-500/10 text-amber-400">
            <AlertCircle className="h-5 w-5" />
          </div>
          <div>
            <h1 className="font-heading text-lg font-bold text-white">
              Faqat Talaba hisoblari uchun
            </h1>
            <p className="text-xs text-zinc-400 font-mono">
              Faol rol: {existingWrongRoleUser.roles.join(", ")}
            </p>
          </div>
        </div>
        <p className="text-xs leading-relaxed text-zinc-300">
          Siz hozir boshqa rol bilan tizimga kirgansiz. Talaba kirishi va imkoniyatlari faqat{" "}
          <span className="font-mono text-sky-400">CANDIDATE</span> hisobi uchun ajratilgan.
        </p>
        <div className="flex flex-col gap-2.5 pt-2">
          <Link
            href={ownPortal.href}
            className="w-full rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.1] px-4 py-2.5 text-center text-xs font-semibold text-white transition-colors"
          >
            {ownPortal.label}
          </Link>
          <button
            type="button"
            onClick={handleSwitchAccount}
            className="w-full rounded-xl bg-sky-600 hover:bg-sky-500 px-4 py-2.5 text-xs font-semibold text-white flex items-center justify-center gap-2 transition-colors"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>Chiqish va Talaba hisobiga kirish</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md space-y-5">
      {/* Student Brand Header */}
      <div className="space-y-2 text-center lg:text-left">
        <div className="inline-flex items-center gap-2 rounded-full border border-sky-500/25 bg-sky-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-sky-400">
          <GraduationCap className="h-3.5 w-3.5" />
          <span>Talaba &amp; Nomzod Kirishi</span>
        </div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-white">
          {mfaRequired ? "Talaba 2FA Tasdiqlash" : "Talaba Kabinetiga Kirish"}
        </h1>
        <p className="text-xs text-zinc-400">
          {mfaRequired
            ? "Authenticator ilovangizdagi 6 xonali kodni kiriting"
            : "Faqat talaba va nomzod hisoblari uchun ajratilgan xavfsiz kirish oynasi"}
        </p>
      </div>

      {/* Form Card */}
      <div className="rounded-[28px] skeuo-card p-6 sm:p-7 space-y-5">
        {errorMessage && (
          <div className="p-3.5 bg-rose-500/10 border border-rose-500/25 rounded-xl flex items-start gap-3 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <span className="leading-relaxed">{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/25 rounded-xl flex items-start gap-3 text-xs text-emerald-300">
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-400" />
            <span className="leading-relaxed">{successMessage}</span>
          </div>
        )}

        {!mfaRequired ? (
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Telefon raqam yoki Elektron pochta
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  placeholder="+998901234567 yoki talaba@otm.uz"
                  className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-sky-500 transition pr-10"
                />
                <Smartphone className="w-4 h-4 text-zinc-500 absolute right-3.5 top-3" />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-zinc-300">Parol</label>
                <Link href="/haqida" className="text-[11px] text-zinc-400 hover:text-sky-400 transition">
                  Yordam kerakmi?
                </Link>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
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
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 shadow-sm mt-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Tekshirilmoqda...</span>
                </>
              ) : (
                <>
                  <span>Talaba sifatida kirish</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleMfaSubmit} className="space-y-4">
            <div className="p-3 bg-zinc-900/60 border border-zinc-800 rounded-xl flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-sky-400 shrink-0" />
              <div className="text-xs text-zinc-300">
                2FA faollashtirilgan. Authenticator ilovasidagi 6 xonali kodni kiriting.
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                6 xonali TOTP kodi
              </label>
              <div className="relative">
                <input
                  type="text"
                  maxLength={6}
                  required
                  autoFocus
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                  placeholder="000000"
                  className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-3 text-center text-xl tracking-widest font-mono text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-sky-500 transition"
                />
                <KeyRound className="w-4 h-4 text-zinc-500 absolute left-3.5 top-3.5" />
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setMfaRequired(false);
                  setMfaTicket(null);
                  setTotpCode("");
                  setErrorMessage(null);
                }}
                className="px-4 py-3 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-xs font-medium transition"
              >
                Ortga
              </button>
              <button
                type="submit"
                disabled={isLoading || totpCode.length !== 6}
                className="flex-1 py-3 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 shadow-sm"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Tasdiqlanmoqda...</span>
                  </>
                ) : (
                  <>
                    <span>Tasdiqlash &amp; Kirish</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        )}

        <div className="pt-4 border-t border-zinc-800/80 text-center space-y-2.5">
          <p className="text-xs text-zinc-400">
            Talaba hisobingiz yo‘qmi?{" "}
            <Link
              href="/talaba/royxatdan-otish"
              className="text-sky-400 hover:text-sky-300 font-semibold underline underline-offset-2 transition"
            >
              Talaba ro‘yxatdan o‘tishi
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
              Qo‘llanma
            </Link>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center gap-2 text-[11px] text-zinc-500">
        <Lock className="w-3.5 h-3.5 text-zinc-600" />
        <span>Rol chegarasi himoyalangan: faqat CANDIDATE hisoblari</span>
      </div>
    </div>
  );
}

export default function TalabaKirishPage() {
  return (
    <div className="min-h-screen text-[var(--fb-ink)] py-10 px-4 sm:px-6 lg:px-8 flex items-center justify-center">
      <div className="w-full max-w-5xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)] transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>E’lonlar katalogiga qaytish</span>
          </Link>
          <Link
            href="/kirish"
            className="text-xs font-medium text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)] transition"
          >
            Korxona yoki OTM xodimi? Umumiy kirish →
          </Link>
        </div>

        <div className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr] items-start">
          {/* Left Panel: Strictly Student-Permitted Capabilities */}
          <aside className="rounded-[28px] skeuo-card p-6 sm:p-7 space-y-5">
            <div>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-sky-500/25 bg-sky-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-sky-400">
                Talabaga ruxsat etilgan modullar
              </span>
              <h2 className="mt-3 font-heading text-xl font-bold tracking-tight text-white">
                Talaba va Nomzod uchun ajratilgan muhit
              </h2>
              <p className="mt-1.5 text-xs leading-relaxed text-zinc-400">
                Ushbu hisob orqali faqat talabalarga tegishli rezyume, ish qidirish, amaliyot shartnomalari va e-imzoli kundalik funksiyalaridan foydalanasiz.
              </p>
            </div>

            <div className="grid gap-3">
              {STUDENT_PERMITTED_FEATURES.map((item) => {
                const Icon = item.icon;
                return (
                  <div
                    key={item.title}
                    className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-surface-lowest/60 p-3.5"
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-sky-500/25 bg-sky-500/10 text-sky-400">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-white">{item.title}</p>
                      <p className="mt-0.5 text-[11px] leading-relaxed text-zinc-400">
                        {item.desc}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </aside>

          {/* Right Panel: Student Scoped Login Form */}
          <div className="flex justify-center">
            <Suspense
              fallback={
                <div className="p-8 text-center text-zinc-400 flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin text-sky-400" />
                  <span>Yuklanmoqda...</span>
                </div>
              }
            >
              <TalabaKirishForm />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  );
}
