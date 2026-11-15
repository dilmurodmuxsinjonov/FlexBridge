"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
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
} from "lucide-react";
import { loginUser, verifyMfa, fetchAuthMe } from "@/lib/api";
import { isRoleAllowedForPortal, type PortalScope, resolvePortalDashboard } from "@/lib/roles";

function KirishForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get("redirect");

  const [destination, setDestination] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // MFA Challenge State
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaTicket, setMfaTicket] = useState<string | null>(null);
  const [totpCode, setTotpCode] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleRedirectAfterLogin = useCallback(
    (roles: string[]) => {
      const targetDashboard = resolvePortalDashboard(roles);
      if (redirectParam && redirectParam.startsWith("/") && !redirectParam.startsWith("//")) {
        const portalScopeMap: Array<[string, PortalScope]> = [
          ["/operator", "OPERATOR"],
          ["/employer", "EMPLOYER"],
          ["/university", "ACADEMIC"],
          ["/nomzod", "CANDIDATE"],
        ];
        const matched = portalScopeMap.find(([prefix]) => redirectParam.startsWith(prefix));
        if (!matched || isRoleAllowedForPortal(roles, matched[1])) {
          router.push(redirectParam);
          router.refresh();
          return;
        }
      }
      router.push(targetDashboard.href);
      router.refresh();
    },
    [redirectParam, router]
  );

  // Auto-redirect if already logged in
  useEffect(() => {
    let isMounted = true;
    fetchAuthMe().then((user) => {
      if (isMounted && user) {
        handleRedirectAfterLogin(user.roles);
      }
    });
    return () => {
      isMounted = false;
    };
  }, [handleRedirectAfterLogin]);

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!destination.trim() || !password) {
      setErrorMessage("Telefon/pochta va parolni kiriting.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await loginUser(destination.trim(), password);
      if (res.ok) {
        if (res.mfa_required && res.mfa_ticket) {
          setMfaRequired(true);
          setMfaTicket(res.mfa_ticket);
          setSuccessMessage("Ikki bosqichli autentifikatsiya kodi talab etiladi.");
        } else {
          window.dispatchEvent(new Event("flexbridge:auth-changed"));
          const userRoles = "roles" in res ? (res.roles as string[]) : [];
          const dash = resolvePortalDashboard(userRoles);
          setSuccessMessage(`Muvaffaqiyatli kirildi! ${dash.label} sahifasiga yo‘naltirilmoqda...`);
          setTimeout(() => {
            handleRedirectAfterLogin(userRoles);
          }, 400);
        }
      } else {
        setErrorMessage(res.error || "Kirish ma'lumotlari noto‘g‘ri.");
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
      const res = await verifyMfa(mfaTicket, totpCode.trim());
      if (res.ok) {
        window.dispatchEvent(new Event("flexbridge:auth-changed"));
        const userRoles = "roles" in res ? (res.roles as string[]) : [];
        const dash = resolvePortalDashboard(userRoles);
        setSuccessMessage(`MFA tasdiqlandi! ${dash.label} sahifasiga yo‘naltirilmoqda...`);
        setTimeout(() => {
          handleRedirectAfterLogin(userRoles);
        }, 400);
      } else {
        setErrorMessage(res.error || "Kiritilgan 2FA kodi yaroqsiz yoki eskirgan.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "MFA tasdiqlashda xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md space-y-6">
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
          {mfaRequired ? "Ikki Bosqichli Tasdiqlash" : "Tizimga Kirish"}
        </h1>
        <p className="text-xs text-[var(--fb-ink-muted)]">
          {mfaRequired
            ? "Ilovangizdagi (Google Authenticator) 6 xonali kodni kiriting"
            : "Talabalar, korxonalar, OTMlar va operatorlar uchun yagona kirish — rolingizga mos kabinetga avtomatik yo‘naltirilasiz"}
        </p>
      </div>

      {/* Main Card */}
      <div className="skeuo-card rounded-[28px] p-6 sm:p-8 space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          <Link
            href="/talaba/kirish"
            className="flex items-center justify-between gap-2 rounded-2xl skeuo-well-sm border border-sky-500/25 px-3.5 py-2.5 text-xs hover:border-sky-500/50 transition-colors"
          >
            <div>
              <p className="font-bold text-sky-700 dark:text-sky-300">Talaba / Nomzod</p>
              <p className="text-[11px] text-[var(--fb-ink-muted)]">Talaba kirishi</p>
            </div>
            <span className="shrink-0 font-bold text-sky-700 dark:text-sky-400">Kirish &rarr;</span>
          </Link>
          <Link
            href="/korxona/kirish"
            className="flex items-center justify-between gap-2 rounded-2xl skeuo-well-sm border border-emerald-500/25 px-3.5 py-2.5 text-xs hover:border-emerald-500/50 transition-colors"
          >
            <div>
              <p className="font-bold text-emerald-700 dark:text-emerald-300">Korxona / HR</p>
              <p className="text-[11px] text-[var(--fb-ink-muted)]">Korxona kirishi</p>
            </div>
            <span className="shrink-0 font-bold text-emerald-700 dark:text-emerald-400">Kirish &rarr;</span>
          </Link>
          <Link
            href="/universitet/kirish"
            className="flex items-center justify-between gap-2 rounded-2xl skeuo-well-sm border border-indigo-500/25 px-3.5 py-2.5 text-xs hover:border-indigo-500/50 transition-colors"
          >
            <div>
              <p className="font-bold text-indigo-700 dark:text-indigo-300">Universitet / OTM</p>
              <p className="text-[11px] text-[var(--fb-ink-muted)]">OTM kirishi</p>
            </div>
            <span className="shrink-0 font-bold text-indigo-700 dark:text-indigo-400">Kirish &rarr;</span>
          </Link>
          <Link
            href="/operator/kirish"
            className="flex items-center justify-between gap-2 rounded-2xl skeuo-well-sm border border-amber-500/25 px-3.5 py-2.5 text-xs hover:border-amber-500/50 transition-colors"
          >
            <div>
              <p className="font-bold text-amber-800 dark:text-amber-300">Operator / SOC</p>
              <p className="text-[11px] text-[var(--fb-ink-muted)]">Operator kirishi</p>
            </div>
            <span className="shrink-0 font-bold text-amber-800 dark:text-amber-400">Kirish &rarr;</span>
          </Link>
        </div>

        {/* Status Alerts */}
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
          /* Step 1: Destination & Password Form */
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[var(--fb-ink)] mb-1.5">
                Telefon raqam yoki Elektron pochta
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  placeholder="+998901234567 yoki pochta@misol.uz"
                  className="w-full skeuo-input rounded-2xl px-4 py-2.5 text-sm pr-10"
                />
                <Smartphone className="w-4 h-4 text-[var(--fb-ink-muted)] absolute right-3.5 top-3" />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-[var(--fb-ink)]">
                  Parol
                </label>
                <Link
                  href="/haqida"
                  className="text-[11px] font-medium text-[var(--fb-ink-muted)] hover:text-[#D95F2B] transition"
                >
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
                  className="w-full skeuo-input rounded-2xl px-4 py-2.5 text-sm pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-3 text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)] transition"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 skeuo-btn-obsidian rounded-2xl text-sm font-semibold flex items-center justify-center gap-2 mt-2 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Tekshirilmoqda...</span>
                </>
              ) : (
                <>
                  <span>Tizimga Kirish</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        ) : (
          /* Step 2: 2FA / TOTP Verification Form */
          <form onSubmit={handleMfaSubmit} className="space-y-4">
            <div className="p-3 bg-zinc-900/60 border border-zinc-800 rounded-xl flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0" />
              <div className="text-xs text-zinc-300">
                Hisobingizda 2FA faollashtirilgan. Authenticator ilovasidagi 6 xonali kodni kiriting.
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
                  className="w-full bg-[#18181b] border border-zinc-700/80 rounded-xl px-4 py-3 text-center text-xl tracking-widest font-mono text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-indigo-500 transition"
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
                className="flex-1 py-3 bg-primary hover:bg-primary-hover disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 shadow-sm"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Tasdiqlanmoqda...</span>
                  </>
                ) : (
                  <>
                    <span>Tasdiqlash & Kirish</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        )}

        {/* Registration CTA Divider */}
        <div className="pt-4 border-t border-zinc-800/80 text-center space-y-3">
          <p className="text-xs text-zinc-400">
            Hali hisobingiz yo‘qmi?{" "}
            <Link
              href="/royxatdan-otish"
              className="text-indigo-400 hover:text-indigo-300 font-semibold underline underline-offset-2 transition"
            >
              Ro‘yxatdan o‘tish
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

      {/* Security Disclaimer */}
      <div className="flex items-center justify-center gap-2 text-[11px] text-zinc-500">
        <Lock className="w-3.5 h-3.5 text-zinc-600" />
        <span>256-bit shifrlangan xavfsiz ulanish (RFC 6238 / AC-023)</span>
      </div>
    </div>
  );
}

export default function KirishPage() {
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

        <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] items-start">
          {/* Left Architectural Context Panel */}
          <aside className="hidden lg:flex flex-col gap-5 rounded-[28px] skeuo-card p-7">
            <div className="inline-flex w-fit items-center gap-2 rounded-full skeuo-well-sm px-3 py-1 text-[11px] font-bold uppercase tracking-[0.14em] text-[#D95F2B]">
              Yagona autentifikatsiya
            </div>
            <div>
              <h2 className="font-display text-2xl font-bold tracking-tight text-[var(--fb-ink)]">
                Har bir rol uchun alohida xavfsiz ish muhiti
              </h2>
              <p className="mt-2 text-xs leading-relaxed text-[var(--fb-ink-muted)]">
                Kirishingiz bilan tizim sizni tegishli kabinetga yo‘naltiradi: Talaba, Korxona HR, OTM Dekanat yoki Operator SOC.
              </p>
            </div>
            <div className="space-y-2.5 pt-2 border-t border-[var(--fb-border)] text-xs">
              <Link
                href="/talaba/kirish"
                className="block rounded-2xl skeuo-well p-3.5 border border-sky-500/25 hover:border-sky-500/50 transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="font-bold text-sky-700 dark:text-sky-300">Talaba / Nomzod</p>
                  <span className="text-[10px] font-bold text-sky-700 dark:text-sky-400">Alohida kirish &rarr;</span>
                </div>
                <p className="text-[var(--fb-ink-muted)] text-[11px] mt-0.5">HEMIS jadvali, rezyume, arizalar va ikki tomonlama e-imzoli kundalik.</p>
              </Link>
              <Link
                href="/korxona/kirish"
                className="block rounded-2xl skeuo-well p-3.5 border border-emerald-500/25 hover:border-emerald-500/50 transition-colors"
              >
                <p className="font-bold text-emerald-700 dark:text-emerald-300">Ish Beruvchi / Korxona →</p>
                <p className="text-[var(--fb-ink-muted)] text-[11px] mt-0.5">Nomzod Kanban, mentorlik tasdig‘i, jamoa va kvota boshqaruvi.</p>
              </Link>
              <Link
                href="/universitet/kirish"
                className="block rounded-2xl skeuo-well p-3.5 border border-indigo-500/25 hover:border-indigo-500/50 transition-colors"
              >
                <p className="font-bold text-indigo-700 dark:text-indigo-300">Universitet / OTM &rarr;</p>
                <p className="text-[var(--fb-ink-muted)] text-[11px] mt-0.5">Kafedra taqsimoti, dars jadvali integratsiyasi va yakuniy xulosalar.</p>
              </Link>
              <Link
                href="/operator/kirish"
                className="block rounded-2xl skeuo-well p-3.5 border border-amber-500/25 hover:border-amber-500/50 transition-colors"
              >
                <p className="font-bold text-amber-800 dark:text-amber-300">Platforma Operatori (SOC) &rarr;</p>
                <p className="text-[var(--fb-ink-muted)] text-[11px] mt-0.5">Hash-chain audit, KYB/OTM moderatsiyasi, moliya va xavfsizlik nazorati.</p>
              </Link>
            </div>
          </aside>

          {/* Right Auth Form Card */}
          <div className="flex justify-center">
            <Suspense
              fallback={
                <div className="p-8 text-center text-zinc-400 flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Yuklanmoqda...</span>
                </div>
              }
            >
              <KirishForm />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  );
}
