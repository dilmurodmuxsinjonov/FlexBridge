"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Briefcase,
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
  Users,
  ClipboardCheck,
  CreditCard,
  Building2,
  LogOut,
} from "lucide-react";
import { loginUser, verifyMfa, fetchAuthMe, logoutUser, AuthUser } from "@/lib/api";
import { isEmployerRoles, resolvePortalDashboard } from "@/lib/roles";

const EMPLOYER_PERMITTED_FEATURES = [
  {
    icon: Briefcase,
    title: "Vakansiyalar & Shartnoma E’lonlari",
    desc: "Smenali ish va amaliyot o‘rinlari yaratish, nashr qilish va muddatli boshqarish.",
  },
  {
    icon: Users,
    title: "Nomzod Kanban & Aqlli Qidiruv",
    desc: "Arizalarni bosqichma-bosqich saralash, suhbat belgilash va ish taklifi yuborish.",
  },
  {
    icon: ClipboardCheck,
    title: "Amaliyot Mentorligi & E-Imzo",
    desc: "Kundaliklarni tasdiqlash, 1- va 2-hujjat bo‘yicha korxona e-imzosi qo‘yish.",
  },
  {
    icon: CreditCard,
    title: "Korxona Rekvizitlari, Jamoa & Kvotalar",
    desc: "HR/Mentor taklif qilish, tashkilot ma’lumotnomasi va tarif to‘lovlari.",
  },
];

function KorxonaKirishForm() {
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

  const goToEmployerCabinet = useCallback(() => {
    if (redirectParam && (redirectParam.startsWith("/employer") || redirectParam === "/")) {
      router.push(redirectParam);
      return;
    }
    router.push("/employer");
  }, [redirectParam, router]);

  useEffect(() => {
    let active = true;
    fetchAuthMe().then((user) => {
      if (!active || !user) return;
      if (isEmployerRoles(user.roles)) {
        goToEmployerCabinet();
      } else {
        setExistingWrongRoleUser(user);
      }
    });
    return () => {
      active = false;
    };
  }, [goToEmployerCabinet]);

  const handleLogoutWrongRole = async () => {
    await logoutUser();
    setExistingWrongRoleUser(null);
    setErrorMessage(null);
    router.refresh();
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!destination.trim() || !password) {
      setErrorMessage("Telefon raqam (yoki email) hamda parolni kiriting.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await loginUser(destination.trim(), password, undefined, "EMPLOYER");
      if (res.ok) {
        if (res.mfa_required) {
          setMfaRequired(true);
          setMfaTicket(res.mfa_ticket);
          setSuccessMessage("2FA himoyasi faol. Autentifikator ilovasidagi 6 xonali kodni kiriting.");
        } else {
          setSuccessMessage("Korxona hisobingiz tasdiqlandi! HR kabinetga yo‘naltirilmoqda...");
          setTimeout(() => {
            goToEmployerCabinet();
            router.refresh();
          }, 350);
        }
      } else {
        setErrorMessage(res.error || "Kirish ma’lumotlari noto‘g‘ri.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Tizim xatosi yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mfaTicket || !totpCode.trim() || totpCode.trim().length < 6) {
      setErrorMessage("6 xonali tasdiqlash kodini kiriting.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await verifyMfa(mfaTicket, totpCode.trim(), "EMPLOYER");
      if (res.ok && !res.mfa_required) {
        setSuccessMessage("Korxona 2FA tasdiqlandi! Yo‘naltirilmoqda...");
        setTimeout(() => {
          goToEmployerCabinet();
          router.refresh();
        }, 350);
      } else if (!res.ok) {
        setErrorMessage(res.error || "Tasdiqlash kodi noto‘g‘ri yoki ushbu hisob korxona rolida emas.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Tasdiqlashda xatolik.");
    } finally {
      setIsLoading(false);
    }
  };

  if (existingWrongRoleUser) {
    const dash = resolvePortalDashboard(existingWrongRoleUser.roles);
    return (
      <div className="w-full max-w-md rounded-2xl border border-amber-500/25 bg-[#121214] p-7 shadow-2xl space-y-5">
        <div className="inline-flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-amber-300">
          Rol chegarasi
        </div>
        <div className="space-y-2">
          <h1 className="font-heading text-xl font-bold text-white">
            Siz boshqa rol bilan tizimga kirgansiz
          </h1>
          <p className="text-xs leading-relaxed text-zinc-400">
            Ushbu sahifa faqat Korxona / Ish beruvchi (`OWNER`, `HR`, `MENTOR`, `HOST_COORDINATOR`, `BILLING`) hisoblari uchun ajratilgan. Hozirgi faol rolingiz:{" "}
            <span className="font-mono text-zinc-200">{existingWrongRoleUser.roles.join(", ")}</span>.
          </p>
        </div>
        <div className="flex flex-col gap-2.5">
          <Link
            href={dash.href}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-white/10 hover:bg-white/15 border border-white/10 py-2.5 px-4 text-xs font-semibold text-white transition"
          >
            <span>{dash.label}ga o‘tish</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
          <button
            type="button"
            onClick={handleLogoutWrongRole}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 py-2.5 px-4 text-xs font-semibold text-white transition"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Chiqish va korxona sifatida kirish</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md space-y-6">
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-300">
          <Building2 className="w-4 h-4 text-emerald-400" />
          <span>Korxona & Ish Beruvchi Portali</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-100">
          {mfaRequired ? "Korxona 2FA Tasdiqlash" : "Korxona Kabinetiga Kirish"}
        </h1>
        <p className="text-xs text-zinc-400">
          {mfaRequired
            ? "Autentifikator ilovasidagi 6 xonali xavfsizlik kodini kiriting"
            : "Tashkilot rahbari, HR menejer, mentor yoki muvofiqlashtiruvchi hisobi bilan kiring"}
        </p>
      </div>

      <div className="skeuo-card rounded-[28px] p-6 sm:p-8 space-y-6">
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

        {!mfaRequired ? (
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Telefon raqam yoki korporativ email
              </label>
              <div className="relative">
                <Smartphone className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  placeholder="+998901234567 yoki hr@korxona.uz"
                  autoComplete="username"
                  required
                  className="w-full bg-[#09090b] border border-zinc-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">Parol</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  autoComplete="current-password"
                  required
                  className="w-full bg-[#09090b] border border-zinc-800 rounded-xl pl-10 pr-10 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition"
                  aria-label="Parolni ko‘rsatish"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 text-white font-semibold py-2.5 px-4 rounded-xl text-sm transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Tekshirilmoqda...</span>
                </>
              ) : (
                <>
                  <span>Korxona Kabinetiga Kirish</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleMfaSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                TOTP Tasdiqlash Kodi (6 xonali)
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={8}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value)}
                  placeholder="123456"
                  autoFocus
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
                  <span>Tasdiqlanmoqda...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Tasdiqlash va Kirish</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => {
                setMfaRequired(false);
                setMfaTicket(null);
                setErrorMessage(null);
              }}
              className="w-full text-xs text-zinc-500 hover:text-zinc-300 py-1.5 transition"
            >
              &larr; Ortga qaytish
            </button>
          </form>
        )}

        <div className="pt-4 border-t border-zinc-800/80 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-zinc-400">
          <span>Yangi korxona vakilimisiz?</span>
          <Link
            href="/korxona/royxatdan-otish"
            className="text-emerald-400 hover:text-emerald-300 font-semibold transition"
          >
            Korxona vakili sifatida ulanish &rarr;
          </Link>
        </div>
      </div>

      <div className="flex items-center justify-center gap-6 text-[11px] text-zinc-500">
        <span className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
          Faqat Korxona Rollari (403 Chegaralangan)
        </span>
        <span className="flex items-center gap-1.5">
          <Lock className="w-3.5 h-3.5 text-emerald-400" />
          HttpOnly + 2FA Himoya
        </span>
      </div>
    </div>
  );
}

export default function KorxonaKirishPage() {
  return (
    <div className="min-h-screen text-[var(--fb-ink)] py-10 px-4 sm:px-6 lg:px-8 flex items-center justify-center">
      <div className="w-full max-w-5xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)] transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Bosh sahifaga qaytish</span>
          </Link>
          <span className="text-[11px] font-mono rounded-full skeuo-badge-recessed px-3 py-0.5 text-emerald-700 dark:text-emerald-400">
            Korxona HR Portali • Tashkilot rollari
          </span>
        </div>

        <div className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr] items-start">
          <aside className="rounded-[28px] skeuo-card p-6 sm:p-7 space-y-5">
            <div className="inline-flex items-center gap-2 rounded-lg skeuo-badge-recessed px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
              Ish Beruvchi & HR Ruxsatlari
            </div>
            <div>
              <h2 className="font-heading text-xl sm:text-2xl font-bold tracking-tight text-[var(--fb-ink)]">
                Korxona vakillari uchun alohida himoyalangan kirish
              </h2>
              <p className="mt-2 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
                Ushbu kirish faqat tashkilotga biriktirilgan rahbar, HR mutaxassis, amaliyot mentori, koordinator va hisobchi hisoblari uchun ochiq. Talaba va OTM hisoblari bu sahifadan kirmaydi.
              </p>
            </div>

            <div className="grid gap-2.5 pt-2 border-t border-white/[0.06]">
              {EMPLOYER_PERMITTED_FEATURES.map((feat) => {
                const Icon = feat.icon;
                return (
                  <div
                    key={feat.title}
                    className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-[#09090b]/60 p-3"
                  >
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-emerald-400">
                      <Icon className="h-3.5 w-3.5" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-zinc-100">{feat.title}</p>
                      <p className="text-[11px] text-zinc-400 mt-0.5">{feat.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </aside>

          <div className="flex justify-center">
            <Suspense
              fallback={
                <div className="p-8 text-center text-zinc-400 flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Yuklanmoqda...</span>
                </div>
              }
            >
              <KorxonaKirishForm />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  );
}
