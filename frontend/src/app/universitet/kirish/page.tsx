"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Eye,
  EyeOff,
  FileSignature,
  GraduationCap,
  KeyRound,
  Loader2,
  Lock,
  LogOut,
  ShieldAlert,
  ShieldCheck,
  Users,
} from "lucide-react";
import { fetchAuthMe, loginUser, logoutUser, verifyMfa, type AuthUser } from "@/lib/api";
import { isAcademicRoles, resolvePortalDashboard } from "@/lib/roles";

function UniversitetKirishForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = searchParams.get("next") || "/university";

  const [destination, setDestination] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

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
      if (isAcademicRoles(user.roles)) {
        router.push("/university");
      } else {
        setWrongRoleUser(user);
      }
    });
    return () => {
      active = false;
    };
  }, [router]);

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!destination.trim() || !password) {
      setErrorMessage("Telefon raqam/email va parolni kiriting.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await loginUser(destination.trim(), password, undefined, "ACADEMIC");

      if (res.ok) {
        if (res.mfa_required) {
          setMfaRequired(true);
          setMfaTicket(res.mfa_ticket);
          setSuccessMessage("Ikki bosqichli tasdiqlash kodi (TOTP) talab etiladi.");
        } else {
          window.dispatchEvent(new Event("flexbridge:auth-changed"));
          setSuccessMessage("Universitet kabinetiga muvaffaqiyatli kirdingiz!");
          const target = nextUrl.startsWith("/university") ? nextUrl : "/university";
          router.push(target);
          router.refresh();
        }
      } else {
        setErrorMessage(res.error || "Kirishda xatolik yuz berdi.");
      }
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Ma’lumotlar noto‘g‘ri yoki hisob akademik rolda emas."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!totpCode.trim() || totpCode.trim().length !== 6) {
      setErrorMessage("6 xonali tasdiqlash kodini to‘liq kiriting.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await verifyMfa(mfaTicket, totpCode.trim(), "ACADEMIC");
      if (res.ok) {
        window.dispatchEvent(new Event("flexbridge:auth-changed"));
        setSuccessMessage("Tasdiqlandi! Universitet kabinetiga yo‘naltirilmoqda...");
        const target = nextUrl.startsWith("/university") ? nextUrl : "/university";
        router.push(target);
        router.refresh();
      } else {
        setErrorMessage("Tasdiqlash kodi noto‘g‘ri.");
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
  };

  if (wrongRoleUser) {
    const dash = resolvePortalDashboard(wrongRoleUser.roles);
    return (
      <div className="w-full max-w-md bg-[#121214] border border-amber-500/25 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-5">
        <div className="inline-flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-300">
          <ShieldAlert className="w-4 h-4" />
          <span>Rol chegarasi</span>
        </div>
        <div className="space-y-2">
          <h2 className="font-heading text-lg font-bold text-white">
            Siz hozir boshqa rol hisobi bilan kirgansiz
          </h2>
          <p className="text-xs leading-relaxed text-zinc-400">
            Faol sessiya:{" "}
            <span className="font-mono text-zinc-200">{wrongRoleUser.roles.join(", ")}</span>.
            Bu sahifa faqat Universitet / OTM koordinatori (`COORDINATOR`) va amaliyot rahbarlari (`TEACHER`) uchun mo‘ljallangan.
          </p>
        </div>
        <div className="flex flex-col gap-2.5">
          <Link
            href={dash.href}
            className="w-full py-2.5 px-4 rounded-xl bg-white/10 border border-white/15 hover:bg-white/15 text-xs font-semibold text-white flex items-center justify-center gap-2 transition-colors"
          >
            <span>{dash.label} sahifasiga o‘tish</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
          <button
            type="button"
            onClick={handleSwitchLogout}
            className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white flex items-center justify-center gap-2 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Chiqish va OTM hisobi bilan kirish</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md space-y-6">
      <div className="space-y-1.5">
        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-[11px] font-semibold text-indigo-300">
          <GraduationCap className="w-3.5 h-3.5" />
          <span>Universitet / OTM Kirishi</span>
        </div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-white">
          {mfaRequired ? "2FA Tasdiqlash" : "OTM Kabinetiga Kirish"}
        </h1>
        <p className="text-xs text-zinc-400">
          {mfaRequired
            ? "Authenticator ilovangizdagi 6 xonali tasdiqlash kodini kiriting"
            : "Faqat OTM koordinatori va kafedra o‘qituvchilari uchun ajratilgan kirish"}
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
          <div className="p-3.5 bg-indigo-500/10 border border-indigo-500/25 rounded-xl flex items-start gap-3 text-xs text-indigo-300">
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-indigo-400" />
            <span className="leading-relaxed">{successMessage}</span>
          </div>
        )}

        {!mfaRequired ? (
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Telefon raqam yoki Xizmat emaili
              </label>
              <input
                type="text"
                required
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="+998901234567 yoki dekanat@otm.uz"
                disabled={isLoading}
                className="w-full px-3.5 py-2.5 bg-zinc-900/90 border border-zinc-800 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Parol
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  disabled={isLoading}
                  className="w-full px-3.5 py-2.5 pr-10 bg-zinc-900/90 border border-zinc-800 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-500/20 transition-all flex items-center justify-center gap-2 mt-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Tekshirilmoqda...</span>
                </>
              ) : (
                <>
                  <span>OTM kabinetiga kirish</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleMfaSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                6 Xonali Tasdiqlash Kodi (Authenticator)
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-indigo-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  required
                  maxLength={6}
                  pattern="[0-9]{6}"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/[^0-9]/g, ""))}
                  placeholder="000000"
                  disabled={isLoading}
                  className="w-full pl-10 pr-4 py-2.5 bg-zinc-900/90 border border-zinc-800 rounded-xl text-sm font-mono tracking-widest text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>

            <div className="flex items-center gap-3 pt-1">
              <button
                type="button"
                onClick={() => {
                  setMfaRequired(false);
                  setMfaTicket("");
                  setTotpCode("");
                  setErrorMessage(null);
                  setSuccessMessage(null);
                }}
                disabled={isLoading}
                className="px-4 py-2.5 bg-zinc-800/80 hover:bg-zinc-800 text-zinc-300 text-xs font-semibold rounded-xl transition-colors"
              >
                Orqaga
              </button>
              <button
                type="submit"
                disabled={isLoading || totpCode.length !== 6}
                className="flex-1 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-500/20 transition-all flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Tasdiqlanmoqda...</span>
                  </>
                ) : (
                  <span>Kodni tasdiqlash</span>
                )}
              </button>
            </div>
          </form>
        )}

        <div className="pt-4 border-t border-zinc-800/80 space-y-2.5 text-center">
          <p className="text-xs text-zinc-400">
            OTM tayinlovingiz bormi yoki yangi vakilmisiz?{" "}
            <Link
              href="/universitet/royxatdan-otish"
              className="font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              OTM vakili ro‘yxatdan o‘tish →
            </Link>
          </p>
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 text-[11px] text-zinc-500">
        <span className="flex items-center gap-1">
          <Lock className="w-3.5 h-3.5 text-zinc-600" />
          OTM Rol Nazorati
        </span>
        <span>•</span>
        <span className="flex items-center gap-1">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          Akademik E-Imzo
        </span>
      </div>
    </div>
  );
}

export default function UniversitetKirishPage() {
  return (
    <div className="min-h-[calc(100vh-3.5rem)] text-[var(--fb-ink)] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-4xl grid gap-8 lg:grid-cols-[1.05fr_1fr] items-center">
        <aside className="hidden lg:flex flex-col gap-5 rounded-[28px] skeuo-card p-7">
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-indigo-500/25 bg-indigo-500/10 px-3 py-1 text-[11px] font-semibold text-indigo-300">
            <GraduationCap className="h-3.5 w-3.5" />
            <span>OTM Akademik Ekotizimi</span>
          </div>
          <div>
            <h2 className="font-heading text-2xl font-bold tracking-tight text-white">
              Universitetlar va kafedralar uchun yagona nazorat markazi
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-zinc-400">
              Faqat OTM vakolatli xodimlariga ochiq bo‘lgan akademik amaliyotlar, dars jadvali va yakuniy tasdiqlar muhiti.
            </p>
          </div>
          <div className="space-y-3 pt-2 border-t border-white/[0.06] text-xs">
            <div className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <Users className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-zinc-100">Kafedra & O‘qituvchi Tayinlash</p>
                <p className="text-zinc-400 text-[11px] mt-0.5">
                  Talabalarga ilmiy rahbar biriktirish, yo‘llanma berish va nazorat ro‘yxati.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <Calendar className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-zinc-100">OTM Dars Jadvali & Yuklash</p>
                <p className="text-zinc-400 text-[11px] mt-0.5">
                  Guruh dars jadvallarini qo‘lda kiritish yoki tayyor jadval shablonidan yuklash.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <FileSignature className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-zinc-100">Yakuniy Xulosa, E-Imzo & Eksport</p>
                <p className="text-zinc-400 text-[11px] mt-0.5">
                  Kundaliklar bahosi, yakuniy xulosa E-Imzo va rasmiy PDF hisobot yaratish.
                </p>
              </div>
            </div>
          </div>
        </aside>

        <div className="flex justify-center">
          <Suspense
            fallback={
              <div className="p-8 text-center text-zinc-400 flex items-center justify-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                <span>Yuklanmoqda...</span>
              </div>
            }
          >
            <UniversitetKirishForm />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
