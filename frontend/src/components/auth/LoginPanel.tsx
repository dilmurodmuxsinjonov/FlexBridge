"use client";

import { Suspense, useCallback, useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  Fingerprint,
  KeyRound,
  Loader2,
  LogOut,
  Mail,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { fetchAuthMe, loginUser, logoutUser, verifyMfa, type AuthUser } from "@/lib/api";
import { finishPasskeyLogin, startPasskeyLogin } from "@/lib/authSecurity";
import { humanizeMessage } from "@/lib/errorText";
import { describeLoginError } from "@/lib/errors";
import { getPasskeyAssertion } from "@/lib/webauthn";
import {
  isAcademicRoles,
  isEmployerRoles,
  isOperatorRoles,
  isRoleAllowedForPortal,
  isStudentOnlyRoles,
  resolvePortalDashboard,
  type PortalScope,
} from "@/lib/roles";

export type LoginTone = "orange" | "sky" | "emerald" | "indigo" | "amber";

export interface LoginFeature {
  icon: LucideIcon;
  title: string;
  desc: string;
}

export interface LoginPanelConfig {
  /** Portal boundary enforced by the BFF; omit for the unified sign-in. */
  portal?: PortalScope;
  tone: LoginTone;
  icon: LucideIcon;
  badge: string;
  /** Who this page is for, lower case ("talaba", "korxona"...). */
  audience?: string;
  title: string;
  subtitle: string;
  identifierPlaceholder: string;
  submitLabel: string;
  /** Where a signed-in user of this portal lands (scoped portals only). */
  home?: string;
  /** Redirect targets (?redirect= / ?next=) accepted for this portal. */
  redirectPrefixes?: string[];
  register?: { href: string; label: string } | null;
  registerNote?: string;
  asideTitle: string;
  asideText: string;
  features: LoginFeature[];
}

const TONE_TEXT: Record<LoginTone, string> = {
  orange: "text-[#c2410c] dark:text-orange-300",
  sky: "text-sky-700 dark:text-sky-300",
  emerald: "text-emerald-700 dark:text-emerald-300",
  indigo: "text-indigo-700 dark:text-indigo-300",
  amber: "text-amber-800 dark:text-amber-300",
};

const TONE_CHIP: Record<LoginTone, string> = {
  orange: "bg-orange-500/10 border-orange-500/25",
  sky: "bg-sky-500/10 border-sky-500/25",
  emerald: "bg-emerald-500/10 border-emerald-500/25",
  indigo: "bg-indigo-500/10 border-indigo-500/25",
  amber: "bg-amber-500/10 border-amber-500/25",
};

const OTHER_PORTALS: Array<{ portal: PortalScope | "ALL"; href: string; label: string }> = [
  { portal: "ALL", href: "/kirish", label: "Umumiy kirish" },
  { portal: "CANDIDATE", href: "/talaba/kirish", label: "Talaba" },
  { portal: "EMPLOYER", href: "/korxona/kirish", label: "Korxona" },
  { portal: "ACADEMIC", href: "/universitet/kirish", label: "Universitet" },
  { portal: "OPERATOR", href: "/operator/kirish", label: "Operator" },
];

function isAllowed(portal: PortalScope | undefined, roles: string[]): boolean {
  switch (portal) {
    case undefined:
      return true;
    case "CANDIDATE":
      return isStudentOnlyRoles(roles);
    case "EMPLOYER":
      return isEmployerRoles(roles);
    case "ACADEMIC":
      return isAcademicRoles(roles);
    case "OPERATOR":
      return isOperatorRoles(roles);
  }
}

const PORTAL_PREFIXES: Array<[string, PortalScope]> = [
  ["/operator", "OPERATOR"],
  ["/employer", "EMPLOYER"],
  ["/university", "ACADEMIC"],
  ["/nomzod", "CANDIDATE"],
];

function safeInternalPath(value: string | null): string | null {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : null;
}

function RedirectParamReader({ onChange }: { onChange: (path: string | null) => void }) {
  const searchParams = useSearchParams();
  const nextValue = safeInternalPath(searchParams.get("redirect") ?? searchParams.get("next"));
  useEffect(() => {
    onChange(nextValue);
  }, [nextValue, onChange]);
  return null;
}

/**
 * The one sign-in experience for every portal: identifier + password, then an
 * authenticator code when the account has 2FA. Scoped portals send their
 * boundary to the BFF (which refuses other roles) and explain wrong-role
 * sessions instead of silently redirecting.
 */
export default function LoginPanel({ config }: { config: LoginPanelConfig }) {
  const router = useRouter();
  const [requested, setRequested] = useState<string | null>(null);
  const prefersReduced = useReducedMotion();
  const ids = useId();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);

  const [mfaTicket, setMfaTicket] = useState<string | null>(null);
  const [code, setCode] = useState("");

  const [busy, setBusy] = useState(false);
  const [redirecting, setRedirecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wrongRoleUser, setWrongRoleUser] = useState<AuthUser | null>(null);

  const identifierRef = useRef<HTMLInputElement>(null);
  const codeRef = useRef<HTMLInputElement>(null);

  const goToDashboard = useCallback(
    (roles: string[]) => {
      setRedirecting(true);
      let target: string;
      if (config.portal) {
        const prefixes = config.redirectPrefixes ?? [config.home ?? "/"];
        target = requested && prefixes.some((p) => requested === p || requested.startsWith(p)) ? requested : config.home ?? "/";
      } else {
        target = resolvePortalDashboard(roles).href;
        if (requested) {
          const scope = PORTAL_PREFIXES.find(([prefix]) => requested.startsWith(prefix));
          if (!scope || isRoleAllowedForPortal(roles, scope[1])) target = requested;
        }
      }
      window.dispatchEvent(new Event("flexbridge:auth-changed"));
      router.replace(target);
      router.refresh();
    },
    [config.home, config.portal, config.redirectPrefixes, requested, router]
  );

  // Already signed in: go straight to the right place, or explain the mismatch.
  useEffect(() => {
    let active = true;
    fetchAuthMe().then((user) => {
      if (!active || !user) return;
      if (isAllowed(config.portal, user.roles)) goToDashboard(user.roles);
      else setWrongRoleUser(user);
    });
    return () => {
      active = false;
    };
  }, [config.portal, goToDashboard]);

  useEffect(() => {
    if (mfaTicket) codeRef.current?.focus();
  }, [mfaTicket]);

  const submitPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setError("Telefon/pochta va parolni kiriting.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await loginUser(identifier.trim(), password, undefined, config.portal);
      if (!res.ok) {
        setError(describeLoginError(res.error));
      } else if (res.mfa_required && res.mfa_ticket) {
        setMfaTicket(res.mfa_ticket);
        setCode("");
      } else {
        goToDashboard("roles" in res && Array.isArray(res.roles) ? res.roles : []);
      }
    } catch (err: unknown) {
      setError(describeLoginError(err instanceof Error ? err.message : null));
    } finally {
      setBusy(false);
    }
  };

  const submitCode = async (value: string) => {
    if (!mfaTicket || value.length !== 6 || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await verifyMfa(mfaTicket, value, config.portal);
      if (!res.ok) {
        setError(describeLoginError(res.error));
        setCode("");
        codeRef.current?.focus();
      } else {
        goToDashboard("roles" in res && Array.isArray(res.roles) ? res.roles : []);
      }
    } catch (err: unknown) {
      setError(describeLoginError(err instanceof Error ? err.message : null));
    } finally {
      setBusy(false);
    }
  };

  const submitPasskey = async (ticket?: string) => {
    setBusy(true);
    setError(null);
    try {
      const opts = await startPasskeyLogin(ticket);
      const assertion = await getPasskeyAssertion(opts.public_key);
      const verified = await finishPasskeyLogin(opts.ceremony_token, assertion, config.portal);
      goToDashboard(Array.isArray(verified.roles) ? verified.roles : []);
    } catch (err: unknown) {
      const raw = err instanceof Error ? err.message : null;
      const code = (err as { code?: string })?.code;
      setError(code ? describeLoginError(code) : humanizeMessage(raw));
    } finally {
      setBusy(false);
    }
  };

  const switchAccount = async () => {
    await logoutUser();
    setWrongRoleUser(null);
    setError(null);
    identifierRef.current?.focus();
  };

  const Icon = config.icon;
  const step = wrongRoleUser ? "wrong-role" : mfaTicket ? "mfa" : "password";
  const fade = prefersReduced
    ? {}
    : { initial: { opacity: 0, y: 6 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -6 }, transition: { duration: 0.2, ease: "easeOut" as const } };

  return (
    <div className="w-full max-w-5xl mx-auto grid gap-6 lg:grid-cols-[0.95fr_1.05fr] items-stretch">
      <Suspense fallback={null}>
        <RedirectParamReader onChange={setRequested} />
      </Suspense>
      {/* About this portal */}
      <aside className="order-2 lg:order-1 skeuo-card rounded-[28px] p-6 sm:p-8 flex flex-col gap-5">
        <div className="space-y-2">
          <h2 className="font-heading text-xl sm:text-2xl font-bold tracking-tight text-[var(--fb-ink)]">{config.asideTitle}</h2>
          <p className="text-sm leading-relaxed text-[var(--fb-ink-secondary)]">{config.asideText}</p>
        </div>
        <ul className="flex flex-col gap-2.5">
          {config.features.map((f) => {
            const FIcon = f.icon;
            return (
              <li key={f.title} className="flex items-start gap-3 rounded-2xl skeuo-well p-3.5">
                <span className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border ${TONE_CHIP[config.tone]} ${TONE_TEXT[config.tone]}`}>
                  <FIcon className="h-4 w-4" aria-hidden="true" />
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-[var(--fb-ink)]">{f.title}</span>
                  <span className="block text-xs leading-relaxed text-[var(--fb-ink-secondary)]">{f.desc}</span>
                </span>
              </li>
            );
          })}
        </ul>
        <nav aria-label="Boshqa kirish sahifalari" className="mt-auto pt-4 border-t border-[var(--fb-hairline)]">
          <p className="text-xs text-[var(--fb-ink-muted)] mb-2">Boshqa turdagi hisob bilan kirasizmi?</p>
          <div className="flex flex-wrap gap-1.5">
            {(config.portal
              ? OTHER_PORTALS.filter((p) => p.portal === "ALL")
              : OTHER_PORTALS.filter((p) => p.portal !== "ALL")
            ).map((p) => (
              <Link key={p.href} href={p.href} className="rounded-full skeuo-btn-secondary px-3 py-1.5 text-xs">
                {p.label}
              </Link>
            ))}
          </div>
        </nav>
      </aside>

      {/* Sign-in card */}
      <section className="order-1 lg:order-2 skeuo-card rounded-[28px] p-6 sm:p-9 flex flex-col gap-6" aria-labelledby={`${ids}-title`}>
        <div className="space-y-2.5">
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${TONE_CHIP[config.tone]} ${TONE_TEXT[config.tone]}`}>
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
            {config.badge}
          </span>
          <h1 id={`${ids}-title`} className="font-heading text-2xl sm:text-[28px] font-bold tracking-tight text-[var(--fb-ink)]">
            {step === "mfa" ? "Tasdiqlash kodi" : step === "wrong-role" ? "Siz boshqa hisob bilan kirgansiz" : config.title}
          </h1>
          <p className="text-sm leading-relaxed text-[var(--fb-ink-secondary)]">
            {step === "mfa"
              ? "Authenticator ilovangizni (Google Authenticator, Authy va h.k.) oching va FlexBridge uchun ko‘rsatilgan 6 xonali kodni kiriting."
              : step === "wrong-role" && wrongRoleUser
                ? `Hozirgi hisobingiz «${resolvePortalDashboard(wrongRoleUser.roles).label}» uchun, bu sahifa esa ${config.audience ?? "boshqa"} hisoblari uchun.`
                : config.subtitle}
          </p>
        </div>

        <div aria-live="polite" aria-atomic="true" className="empty:hidden">
          {error && (
            <div role="alert" className="flex items-start gap-2.5 rounded-2xl border border-rose-500/25 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}
          {redirecting && !error && (
            <div className="flex items-center gap-2.5 rounded-2xl border border-emerald-500/25 bg-emerald-500/10 p-3.5 text-sm text-emerald-700 dark:text-emerald-300">
              <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>Kirildi. Kabinetingiz ochilmoqda…</span>
            </div>
          )}
        </div>

        <AnimatePresence mode="wait" initial={false}>
          {step === "wrong-role" && wrongRoleUser ? (
            <motion.div key="wrong" {...fade} className="flex flex-col gap-2.5">
              <Link
                href={resolvePortalDashboard(wrongRoleUser.roles).href}
                className="skeuo-btn-obsidian w-full rounded-2xl px-4 py-3 text-sm"
              >
                {resolvePortalDashboard(wrongRoleUser.roles).label}ga o‘tish
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <button type="button" onClick={switchAccount} className="skeuo-btn-secondary w-full rounded-2xl px-4 py-3 text-sm">
                <LogOut className="h-4 w-4" aria-hidden="true" />
                Chiqish va boshqa hisob bilan kirish
              </button>
            </motion.div>
          ) : step === "mfa" ? (
            <motion.form
              key="mfa"
              {...fade}
              onSubmit={(e) => {
                e.preventDefault();
                void submitCode(code);
              }}
              className="flex flex-col gap-4"
            >
              <div>
                <label htmlFor={`${ids}-code`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
                  6 xonali kod
                </label>
                <div className="relative">
                  <KeyRound className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--fb-ink-muted)]" aria-hidden="true" />
                  <input
                    ref={codeRef}
                    id={`${ids}-code`}
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    required
                    value={code}
                    onChange={(e) => {
                      const next = e.target.value.replace(/\D/g, "").slice(0, 6);
                      setCode(next);
                      if (next.length === 6) void submitCode(next);
                    }}
                    placeholder="••••••"
                    className="skeuo-input w-full rounded-2xl py-3.5 pl-11 pr-4 text-center font-mono text-2xl tracking-[0.5em]"
                  />
                </div>
                <p className="mt-1.5 text-xs text-[var(--fb-ink-muted)]">Kod har 30 soniyada yangilanadi. 6 ta raqam kiritilishi bilan avtomatik tekshiriladi.</p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setMfaTicket(null);
                    setCode("");
                    setError(null);
                  }}
                  className="skeuo-btn-secondary rounded-2xl px-4 py-3 text-sm"
                >
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                  Orqaga
                </button>
                <button type="submit" data-tone={config.tone} disabled={busy || code.length !== 6} className="skeuo-btn-tone flex-1 rounded-2xl px-4 py-3 text-sm disabled:opacity-50">
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <ShieldCheck className="h-4 w-4" aria-hidden="true" />}
                  {busy ? "Tekshirilmoqda…" : "Tasdiqlash"}
                </button>
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() => void submitPasskey(mfaTicket || undefined)}
                className="skeuo-btn-secondary w-full rounded-2xl px-4 py-2.5 text-xs font-semibold disabled:opacity-60"
              >
                <Fingerprint className="h-4 w-4" aria-hidden="true" />
                Yoki Passkey bilan tasdiqlash
              </button>
            </motion.form>
          ) : (
            <motion.form key="password" {...fade} onSubmit={submitPassword} className="flex flex-col gap-4" noValidate>
              <div>
                <label htmlFor={`${ids}-id`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
                  Telefon raqam yoki elektron pochta
                </label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--fb-ink-muted)]" aria-hidden="true" />
                  <input
                    ref={identifierRef}
                    id={`${ids}-id`}
                    type="text"
                    inputMode="email"
                    autoComplete="username"
                    autoCapitalize="none"
                    spellCheck={false}
                    required
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder={config.identifierPlaceholder}
                    className="skeuo-input w-full rounded-2xl py-3 pl-11 pr-4 text-sm"
                  />
                </div>
              </div>

              <div>
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <label htmlFor={`${ids}-pw`} className="text-sm font-semibold text-[var(--fb-ink)]">
                    Parol
                  </label>
                  <Link href="/parolni-tiklash" className="text-xs font-medium text-[var(--fb-ink-secondary)] underline-offset-2 hover:underline">
                    Parolni unutdingizmi?
                  </Link>
                </div>
                <div className="relative">
                  <input
                    id={`${ids}-pw`}
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyUp={(e) => setCapsLock(e.getModifierState("CapsLock"))}
                    onBlur={() => setCapsLock(false)}
                    placeholder="Parolingiz"
                    className="skeuo-input w-full rounded-2xl py-3 pl-4 pr-12 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Parolni yashirish" : "Parolni ko‘rsatish"}
                    aria-pressed={showPassword}
                    className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)]"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
                  </button>
                </div>
                {capsLock && <p className="mt-1.5 text-xs font-medium text-amber-700 dark:text-amber-300">Caps Lock yoqilgan.</p>}
              </div>

              <button type="submit" data-tone={config.tone} disabled={busy || redirecting} className="skeuo-btn-tone mt-1 w-full rounded-2xl px-4 py-3.5 text-sm disabled:opacity-60">
                {busy || redirecting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                {busy ? "Tekshirilmoqda…" : redirecting ? "Ochilmoqda…" : config.submitLabel}
                {!busy && !redirecting && <ArrowRight className="h-4 w-4" aria-hidden="true" />}
              </button>

              <button
                type="button"
                disabled={busy || redirecting}
                onClick={() => void submitPasskey()}
                className="skeuo-btn-secondary w-full rounded-2xl px-4 py-3 text-sm font-semibold disabled:opacity-60"
              >
                <Fingerprint className="h-4 w-4" aria-hidden="true" />
                Passkey bilan kirish
              </button>
            </motion.form>
          )}
        </AnimatePresence>

        <div className="mt-auto border-t border-[var(--fb-hairline)] pt-4 text-center text-sm text-[var(--fb-ink-secondary)]">
          {config.register ? (
            <>
              Hisobingiz yo‘qmi?{" "}
              <Link href={config.register.href} className={`font-semibold underline underline-offset-2 ${TONE_TEXT[config.tone]}`}>
                {config.register.label}
              </Link>
            </>
          ) : (
            config.registerNote
          )}
          <div className="mt-3 flex items-center justify-center gap-3 text-xs text-[var(--fb-ink-muted)]">
            <Link href="/shartlar" className="hover:text-[var(--fb-ink)]">
              Shartlar
            </Link>
            <span aria-hidden="true">·</span>
            <Link href="/maxfiylik" className="hover:text-[var(--fb-ink)]">
              Maxfiylik
            </Link>
            <span aria-hidden="true">·</span>
            <Link href="/haqida" className="hover:text-[var(--fb-ink)]">
              Yordam
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

/** Page shell: back link + panel (search params isolated so portal SSR links always emit). */
export function LoginScreen({ config, back = { href: "/", label: "Bosh sahifa" } }: { config: LoginPanelConfig; back?: { href: string; label: string } }) {
  return (
    <div className="w-full px-4 sm:px-6 py-6 sm:py-10">
      <div className="mx-auto mb-4 w-full max-w-5xl">
        <Link href={back.href} className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          {back.label}
        </Link>
      </div>
      <LoginPanel config={config} />
    </div>
  );
}
