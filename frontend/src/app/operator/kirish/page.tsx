"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  KeyRound,
  Lock,
  LogOut,
  ShieldAlert,
  ShieldCheck,
  Terminal,
} from "lucide-react";
import { AuthUser, fetchAuthMe, loginUser, logoutUser, verifyMfa } from "@/lib/api";
import { isOperatorRoles, resolvePortalDashboard } from "@/lib/roles";

function OperatorKirishForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = searchParams.get("next") || "/operator";

  const [destination, setDestination] = useState("");
  const [password, setPassword] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaTicket, setMfaTicket] = useState("");
  const [totpCode, setTotpCode] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [wrongRoleUser, setWrongRoleUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let active = true;
    fetchAuthMe().then((user) => {
      if (!active || !user) return;
      if (isOperatorRoles(user.roles)) {
        const target = nextUrl.startsWith("/operator") ? nextUrl : "/operator";
        router.replace(target);
      } else {
        setWrongRoleUser(user);
      }
    });
    return () => {
      active = false;
    };
  }, [nextUrl, router]);

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!destination.trim() || !password) {
      setErrorMessage("Operator telefon raqami (yoki email) va parolni kiriting.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await loginUser(destination.trim(), password, undefined, "OPERATOR");

      if (res.ok) {
        if (res.mfa_required) {
          setMfaRequired(true);
          setMfaTicket(res.mfa_ticket);
          setSuccessMessage("SOC terminal kirishi uchun 2FA TOTP kodini kiriting.");
        } else {
          window.dispatchEvent(new Event("flexbridge:auth-changed"));
          setSuccessMessage("SOC terminaliga muvaffaqiyatli kirdingiz!");
          const target = nextUrl.startsWith("/operator") ? nextUrl : "/operator";
          router.push(target);
          router.refresh();
        }
      } else {
        setErrorMessage(res.error || "Kirish rad etildi yoki operator vakolati mavjud emas.");
      }
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Ma’lumotlar noto‘g‘ri yoki platforma roli tasdiqlanmagan."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!totpCode.trim() || totpCode.trim().length !== 6) {
      setErrorMessage("6 xonali TOTP tasdiqlash kodini to‘liq kiriting.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await verifyMfa(mfaTicket, totpCode.trim(), "OPERATOR");
      if (res.ok) {
        window.dispatchEvent(new Event("flexbridge:auth-changed"));
        setSuccessMessage("2FA tasdiqlandi! Operator SOC terminaliga yo‘naltirilmoqda...");
        const target = nextUrl.startsWith("/operator") ? nextUrl : "/operator";
        router.push(target);
        router.refresh();
      } else {
        setErrorMessage(res.error || "Tasdiqlash kodi noto‘g‘ri.");
      }
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "2FA kodini tekshirishda xatolik yuz berdi."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleSwitchLogout = async () => {
    await logoutUser();
    setWrongRoleUser(null);
    window.dispatchEvent(new Event("flexbridge:auth-changed"));
    router.refresh();
  };

  if (wrongRoleUser) {
    const dash = resolvePortalDashboard(wrongRoleUser.roles);
    return (
      <div className="w-full max-w-md mx-auto">
        <div className="bg-[#121214] border border-amber-500/35 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-5">
          <div className="inline-flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-[11px] font-mono font-semibold text-amber-300">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>SOC Rol Chegarasi</span>
          </div>
          <div className="space-y-2">
            <h2 className="text-lg font-heading font-bold text-white">
              Joriy sessiya Operator roliga ega emas
            </h2>
            <p className="text-xs leading-relaxed text-zinc-400">
              Siz hozir{" "}
              <span className="font-mono text-zinc-200">
                {wrongRoleUser.user_id}
              </span>{" "}
              (<span className="font-mono text-amber-300">{wrongRoleUser.roles.join(", ")}</span>)
              hisobidasiz. SOC terminaliga kirish uchun ushbu sessiyadan chiqib, Operator hisobi bilan kiring.
            </p>
          </div>
          <div className="flex flex-col gap-2.5 pt-2 border-t border-white/[0.06]">
            <button
              type="button"
              onClick={handleSwitchLogout}
              className="w-full rounded-xl bg-amber-600 hover:bg-amber-500 text-zinc-950 font-semibold text-xs py-3 transition-colors flex items-center justify-center gap-2"
            >
              <LogOut className="w-4 h-4" />
              <span>Chiqish va Operator sifatida kirish</span>
            </button>
            <Link
              href={dash.href}
              className="w-full rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] text-zinc-300 font-semibold text-xs py-2.5 text-center transition-colors"
            >
              {dash.label}ga qaytish
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="text-center mb-6 space-y-2">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/25 text-amber-300 text-[11px] font-mono font-semibold">
          <Terminal className="w-3.5 h-3.5" />
          <span>SOC SECURITY PORTAL</span>
        </div>
        <h1 className="text-2xl font-heading font-bold tracking-tight text-white">
          Platforma Operatori Kirishi
        </h1>
        <p className="text-xs text-zinc-400">
          OPERATOR, MODERATOR, AUDITOR, SUPPORT va FINANCE xavfsizlik terminali
        </p>
      </div>

      <div className="skeuo-card rounded-[28px] p-6 sm:p-8 space-y-6">
        {errorMessage && (
          <div className="p-3.5 bg-rose-500/10 border border-rose-500/25 rounded-xl flex items-start gap-3 text-xs text-rose-400">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <span className="leading-relaxed">{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div className="p-3.5 bg-amber-500/10 border border-amber-500/25 rounded-xl flex items-start gap-3 text-xs text-amber-300">
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-amber-300" />
            <span className="leading-relaxed">{successMessage}</span>
          </div>
        )}

        {!mfaRequired ? (
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300 block">
                Operator telefon raqami yoki email
              </label>
              <input
                type="text"
                required
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="+998901234567"
                disabled={isLoading}
                className="w-full px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-xs font-mono text-white placeholder:text-zinc-600 focus:outline-none focus:border-amber-500 transition-colors"
                autoComplete="username"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300 block">Parol</label>
              <div className="relative">
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  disabled={isLoading}
                  className="w-full px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white placeholder:text-zinc-600 focus:outline-none focus:border-amber-500 transition-colors pr-10"
                  autoComplete="current-password"
                />
                <Lock className="w-4 h-4 text-zinc-500 absolute right-3.5 top-2.5" />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-amber-600 hover:bg-amber-500 text-zinc-950 text-xs font-semibold rounded-xl transition-colors shadow-lg shadow-amber-500/10 flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {isLoading ? (
                <>
                  <Activity className="w-4 h-4 animate-spin" />
                  <span>SOC tekshiruvi...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>SOC terminaliga kirish</span>
                </>
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleMfaSubmit} className="space-y-4">
            <div className="p-3 bg-amber-500/10 border border-amber-500/25 rounded-xl flex items-start gap-2.5 text-[11px] text-amber-300">
              <KeyRound className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
              <span>
                Autentifikator ilovasidagi (TOTP) 6 xonali xavfsizlik kodini kiriting.
              </span>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300 block">
                Tasdiqlash kodi (6 xonali)
              </label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                required
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                placeholder="000000"
                disabled={isLoading}
                className="w-full px-3.5 py-3 bg-zinc-950 border border-amber-500/35 rounded-xl text-center text-base font-mono font-bold tracking-[0.4em] text-amber-300 focus:outline-none focus:border-amber-400"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-amber-600 hover:bg-amber-500 text-zinc-950 text-xs font-semibold rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {isLoading ? "Tasdiqlanmoqda..." : "2FA kodini tasdiqlash"}
            </button>
          </form>
        )}

        <div className="pt-4 border-t border-white/[0.06] space-y-2 text-[11px] text-zinc-400">
          <div className="rounded-lg border border-amber-500/15 bg-amber-500/[0.04] p-2.5">
            <p className="font-mono text-amber-300 font-semibold">Dual-Control Platform Access</p>
            <p className="text-zinc-400 mt-0.5">
              Platforma xodimlari rollari (<code className="text-zinc-300">platform_role_grants</code>) mustaqil tasdiq va majburiy TOTP 2FA orqali beriladi; ochiq ro‘yxatdan o‘tish mavjud emas.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function OperatorKirishPage() {
  return (
    <div className="min-h-[calc(100vh-4rem)] text-[var(--fb-ink)] py-10 px-4">
      <div className="max-w-5xl mx-auto">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--fb-ink-muted)] hover:text-amber-600 dark:hover:text-amber-300 transition-colors mb-8"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Bosh sahifaga qaytish</span>
        </Link>

        <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] items-start">
          <aside className="hidden lg:flex flex-col gap-5 rounded-[28px] skeuo-card p-7">
            <div className="inline-flex w-fit items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[11px] font-mono font-semibold uppercase tracking-wider text-amber-300">
              SOC Xavfsizlik Terminal
            </div>
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight text-white">
                Platforma nazorati, audit va moderatsiya markazi
              </h2>
              <p className="mt-2 text-xs leading-relaxed text-zinc-400">
                Ushbu kirish sahifasi faqat platforma darajasidagi maxsus rollar (<code className="text-amber-300">OPERATOR</code>, <code className="text-amber-300">MODERATOR</code>, <code className="text-amber-300">AUDITOR</code>, <code className="text-amber-300">SUPPORT</code>, <code className="text-amber-300">FINANCE</code>) uchun ajratilgan.
              </p>
            </div>
            <div className="space-y-2.5 pt-2 border-t border-white/[0.06] text-xs">
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-3">
                <p className="font-mono font-semibold text-amber-300">01 // Hash-Chain Audit & Replay</p>
                <p className="text-zinc-400 text-[11px] mt-0.5">
                  Shubhali xatti-harakatlar, autentifikatsiya hodisalari va tiklash jurnallari nazorati.
                </p>
              </div>
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-3">
                <p className="font-mono font-semibold text-amber-300">02 // KYB & OTM Moderatsiyasi</p>
                <p className="text-zinc-400 text-[11px] mt-0.5">
                  Korxonalar, OTM tayinlovlari va talaba ro‘yxatga olish hujjatlarini mustaqil tasdiqlash.
                </p>
              </div>
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-3">
                <p className="font-mono font-semibold text-amber-300">03 // Moliya, Support & Xavfsizlik</p>
                <p className="text-zinc-400 text-[11px] mt-0.5">
                  Dual-control ledger tekshiruvi, shikoyat tiklash va rollarni boshqarish.
                </p>
              </div>
            </div>
          </aside>

          <div className="flex justify-center">
            <Suspense
              fallback={
                <div className="p-8 text-center text-zinc-400 flex items-center justify-center gap-2 text-xs">
                  <Activity className="w-4 h-4 animate-spin text-amber-400" />
                  <span>SOC terminal yuklanmoqda...</span>
                </div>
              }
            >
              <OperatorKirishForm />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  );
}
