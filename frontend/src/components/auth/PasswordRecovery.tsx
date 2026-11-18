"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  LockKeyhole,
  Mail,
  MessageSquare,
  Send,
  ShieldCheck,
} from "lucide-react";
import TelegramVerification, { type TelegramMode } from "@/components/TelegramVerification";
import { fetchAuthChallengeStatus, fetchAuthOptions } from "@/lib/api";
import { resendAuthChallenge } from "@/lib/authSecurity";
import { describeLoginError } from "@/lib/errors";
import {
  RecoveryError,
  completeRecovery,
  fetchRecoveryStatus,
  normalizeRecoveryDestination,
  requestRecovery,
  startRecovery,
  verifyRecoveryCode,
  type RecoveryDelivery,
} from "@/lib/recovery";

type Step = "contact" | "code" | "factor" | "password" | "done" | "review";

const STEPS: Array<{ id: Step; label: string }> = [
  { id: "contact", label: "Kontakt" },
  { id: "code", label: "Kod" },
  { id: "factor", label: "Tasdiqlash" },
  { id: "password", label: "Yangi parol" },
];

function message(err: unknown): string {
  if (err instanceof RecoveryError) return describeLoginError(err.code);
  return describeLoginError(err instanceof Error ? err.message : null);
}

function passwordProblems(pw: string): string[] {
  const problems: string[] = [];
  if (pw.length < 12) problems.push("kamida 12 ta belgi");
  if (!/[A-Za-zА-Яа-яЎўҚқҒғҲҳ]/.test(pw) || !/[0-9]/.test(pw)) problems.push("harf va raqam aralash");
  return problems;
}

/**
 * Self-service password recovery. Security model (backend IAM.md): an OTP to a
 * verified contact alone never resets a password — the user also proves an
 * independent factor (authenticator code or a backup code). Without one the
 * request is queued for manual identity review, with the same response whether
 * or not the account exists.
 */
export default function PasswordRecovery() {
  const ids = useId();
  const prefersReduced = useReducedMotion();

  const [step, setStep] = useState<Step>("contact");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 1 — contact
  const [contact, setContact] = useState("");
  const [delivery, setDelivery] = useState<RecoveryDelivery>("SMS");
  const [telegramMode, setTelegramMode] = useState<TelegramMode>("DISABLED");
  const [botUsername, setBotUsername] = useState("");

  // Step 2 — OTP
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [deepLink, setDeepLink] = useState<string | null>(null);
  const [telegramVerified, setTelegramVerified] = useState(false);
  const [code, setCode] = useState("");
  const [resendIn, setResendIn] = useState(0);
  const [verificationToken, setVerificationToken] = useState<string | null>(null);

  // Step 3 — second factor
  const [factorKind, setFactorKind] = useState<"totp" | "backup">("totp");
  const [factor, setFactor] = useState("");

  // Step 4 — new password
  const [recoveryId, setRecoveryId] = useState<string | null>(null);
  const [recoveryToken, setRecoveryToken] = useState<string | null>(null);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [reviewStatus, setReviewStatus] = useState<string | null>(null);

  const sectionRef = useRef<HTMLElement>(null);
  const isEmail = contact.includes("@");
  const effectiveDelivery: RecoveryDelivery = isEmail ? "EMAIL" : delivery;

  useEffect(() => {
    let active = true;
    fetchAuthOptions()
      .then((opts) => {
        if (!active) return;
        if (opts.telegram_mode) setTelegramMode(opts.telegram_mode);
        if (opts.telegram_bot_username) setBotUsername(opts.telegram_bot_username);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  // Keep the card in view when a step change shortens the page (mobile).
  useEffect(() => {
    const el = sectionRef.current;
    if (el && el.getBoundingClientRect().top < 0) el.scrollIntoView({ block: "start", behavior: prefersReduced ? "auto" : "smooth" });
  }, [step, prefersReduced]);

  useEffect(() => {
    if (resendIn <= 0) return;
    const t = setTimeout(() => setResendIn((v) => v - 1), 1000);
    return () => clearTimeout(t);
  }, [resendIn]);

  // Telegram delivery: wait until the bot confirms the shared contact.
  useEffect(() => {
    if (step !== "code" || !challengeId || effectiveDelivery !== "TELEGRAM" || telegramVerified) return;
    let active = true;
    const interval = setInterval(async () => {
      try {
        const status = await fetchAuthChallengeStatus(challengeId);
        if (active && status.telegram_verified) setTelegramVerified(true);
      } catch {
        // transient; keep polling
      }
    }, 3000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [step, challengeId, effectiveDelivery, telegramVerified]);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  };

  const sendCode = () =>
    run(async () => {
      const { channel, destination } = normalizeRecoveryDestination(contact);
      const res = await startRecovery(channel, destination, effectiveDelivery);
      setChallengeId(res.challenge_id);
      setDeepLink(res.telegram_deep_link ?? null);
      if (res.telegram_bot_username) setBotUsername(res.telegram_bot_username);
      setTelegramVerified(false);
      setCode("");
      setResendIn(res.resend_after ?? 60);
      setStep("code");
    });

  const resendCode = () =>
    run(async () => {
      if (!challengeId) return;
      const res = await resendAuthChallenge(challengeId, "RECOVERY");
      setChallengeId(res.challenge_id);
      setDeepLink(res.telegram_deep_link ?? null);
      if (res.telegram_bot_username) setBotUsername(res.telegram_bot_username);
      setTelegramVerified(false);
      setCode("");
      setResendIn(res.resend_after ?? 60);
    });

  const checkCode = (value: string) =>
    run(async () => {
      if (!challengeId) return;
      const res = await verifyRecoveryCode(challengeId, value);
      setVerificationToken(res.verification_token);
      setStep("factor");
    });

  const submitFactor = (withFactor: boolean) =>
    run(async () => {
      if (!verificationToken) return;
      const value = factor.trim();
      const res = await requestRecovery(
        verificationToken,
        withFactor ? (factorKind === "totp" ? { totp_code: value } : { recovery_code: value }) : {}
      );
      // The proof is single-use: any outcome means a new OTP is needed to retry.
      setVerificationToken(null);
      setRecoveryId(res.recovery_id);
      setRecoveryToken(res.recovery_token);
      if (res.status === "READY_TO_RESET" && res.reset_token) {
        setResetToken(res.reset_token);
        setStep("password");
      } else {
        setReviewStatus(res.status);
        setStep("review");
      }
    });

  const savePassword = () =>
    run(async () => {
      if (!recoveryId || !resetToken) return;
      if (passwordProblems(pw).length) throw new RecoveryError("PASSWORD_TOO_SHORT", 400);
      if (pw !== pw2) throw new Error("Parollar bir xil emas.");
      await completeRecovery(recoveryId, resetToken, pw);
      setResetToken(null);
      setPw("");
      setPw2("");
      setStep("done");
    });

  const refreshReview = () =>
    run(async () => {
      if (!recoveryId || !recoveryToken) return;
      const res = await fetchRecoveryStatus(recoveryId, recoveryToken);
      setReviewStatus(res.status);
    });

  const restart = () => {
    setStep("contact");
    setChallengeId(null);
    setVerificationToken(null);
    setCode("");
    setFactor("");
    setError(null);
  };

  const fade = prefersReduced
    ? {}
    : { initial: { opacity: 0, y: 6 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -6 }, transition: { duration: 0.2, ease: "easeOut" as const } };
  const stepIndex = STEPS.findIndex((s) => s.id === step);
  const problems = passwordProblems(pw);

  return (
    <div className="w-full px-4 sm:px-6 py-6 sm:py-10">
      <div className="mx-auto w-full max-w-lg">
        <Link href="/kirish" className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Kirish sahifasi
        </Link>

        <section ref={sectionRef} className="skeuo-card rounded-[28px] p-6 sm:p-9 flex flex-col gap-6 scroll-mt-24" aria-labelledby={`${ids}-title`}>
          <div className="space-y-2.5">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-orange-500/25 bg-orange-500/10 px-3 py-1 text-xs font-semibold text-[#c2410c] dark:text-orange-300">
              <LockKeyhole className="h-3.5 w-3.5" aria-hidden="true" />
              Parolni tiklash
            </span>
            <h1 id={`${ids}-title`} className="font-heading text-2xl sm:text-[28px] font-bold tracking-tight text-[var(--fb-ink)]">
              {step === "done" ? "Parol yangilandi" : step === "review" ? "So‘rov qabul qilindi" : "Hisobingizga qayta kirish"}
            </h1>
            {stepIndex >= 0 && (
              <ol className="flex items-center gap-1.5 pt-1" aria-label="Bosqichlar">
                {STEPS.map((s, i) => (
                  <li key={s.id} className="flex flex-1 flex-col gap-1">
                    <span className={`h-1.5 rounded-full ${i <= stepIndex ? "bg-[var(--fb-accent)]" : "bg-[var(--fb-well-deep)]"}`} />
                    <span className={`text-[11px] ${i === stepIndex ? "font-semibold text-[var(--fb-ink)]" : "text-[var(--fb-ink-muted)]"}`} aria-current={i === stepIndex ? "step" : undefined}>
                      {s.label}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </div>

          {error && (
            <div role="alert" className="flex items-start gap-2.5 rounded-2xl border border-rose-500/25 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          <AnimatePresence mode="wait" initial={false}>
            {step === "contact" && (
              <motion.form
                key="contact"
                {...fade}
                className="flex flex-col gap-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (contact.trim()) void sendCode();
                }}
              >
                <p className="text-sm leading-relaxed text-[var(--fb-ink-secondary)]">
                  Hisobingizga bog‘langan telefon raqam yoki pochtani kiriting — unga 6 xonali kod yuboramiz.
                </p>
                <div>
                  <label htmlFor={`${ids}-contact`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
                    Telefon raqam yoki elektron pochta
                  </label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--fb-ink-muted)]" aria-hidden="true" />
                    <input
                      id={`${ids}-contact`}
                      type="text"
                      inputMode="email"
                      autoComplete="username"
                      autoCapitalize="none"
                      spellCheck={false}
                      required
                      autoFocus
                      value={contact}
                      onChange={(e) => setContact(e.target.value)}
                      placeholder="+998 90 123 45 67 yoki pochta@misol.uz"
                      className="skeuo-input w-full rounded-2xl py-3 pl-11 pr-4 text-sm"
                    />
                  </div>
                </div>
                {!isEmail && telegramMode !== "DISABLED" && (
                  <fieldset>
                    <legend className="mb-1.5 text-sm font-semibold text-[var(--fb-ink)]">Kodni qayerga yuboraylik?</legend>
                    <div className="grid grid-cols-2 gap-2">
                      {(
                        [
                          ["SMS", "SMS", MessageSquare],
                          ["TELEGRAM", "Telegram", Send],
                        ] as const
                      ).map(([value, label, Icon]) => (
                        <label
                          key={value}
                          className={`flex cursor-pointer items-center justify-center gap-2 rounded-2xl border px-3 py-2.5 text-sm font-semibold ${
                            delivery === value ? "border-[var(--fb-accent)] bg-orange-500/10 text-[var(--fb-ink)]" : "skeuo-well text-[var(--fb-ink-secondary)]"
                          }`}
                        >
                          <input type="radio" name={`${ids}-delivery`} value={value} checked={delivery === value} onChange={() => setDelivery(value)} className="sr-only" />
                          <Icon className="h-4 w-4" aria-hidden="true" />
                          {label}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                )}
                <button type="submit" disabled={busy || !contact.trim()} className="skeuo-btn-tone w-full rounded-2xl px-4 py-3.5 text-sm disabled:opacity-60">
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                  {busy ? "Yuborilmoqda…" : "Kod olish"}
                  {!busy && <ArrowRight className="h-4 w-4" aria-hidden="true" />}
                </button>
              </motion.form>
            )}

            {step === "code" && challengeId && (
              <motion.div key="code" {...fade} className="flex flex-col gap-4">
                {effectiveDelivery === "TELEGRAM" ? (
                  <TelegramVerification
                    mode={telegramMode}
                    challengeId={challengeId}
                    phone={normalizeRecoveryDestination(contact).destination}
                    botUsername={botUsername}
                    deepLink={deepLink}
                    verified={telegramVerified}
                    onSimulatedCode={(c) => {
                      setCode(c);
                      setTelegramVerified(true);
                    }}
                  />
                ) : (
                  <p className="text-sm leading-relaxed text-[var(--fb-ink-secondary)]">
                    Agar <span className="font-semibold text-[var(--fb-ink)]">{contact.trim()}</span> hisobga bog‘langan bo‘lsa, unga 6 xonali kod yuborildi. Kod 5 daqiqa amal qiladi.
                  </p>
                )}
                <form
                  className="flex flex-col gap-3"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (code.length === 6) void checkCode(code);
                  }}
                >
                  <label htmlFor={`${ids}-otp`} className="text-sm font-semibold text-[var(--fb-ink)]">
                    6 xonali kod
                  </label>
                  <input
                    id={`${ids}-otp`}
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    required
                    autoFocus
                    value={code}
                    onChange={(e) => {
                      const next = e.target.value.replace(/\D/g, "").slice(0, 6);
                      setCode(next);
                      if (next.length === 6 && (effectiveDelivery !== "TELEGRAM" || telegramVerified)) void checkCode(next);
                    }}
                    placeholder="••••••"
                    className="skeuo-input w-full rounded-2xl py-3.5 px-4 text-center font-mono text-2xl tracking-[0.5em]"
                  />
                  <div className="flex gap-2">
                    <button type="button" onClick={restart} className="skeuo-btn-secondary rounded-2xl px-4 py-3 text-sm">
                      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                      Orqaga
                    </button>
                    <button type="submit" disabled={busy || code.length !== 6} className="skeuo-btn-tone flex-1 rounded-2xl px-4 py-3 text-sm disabled:opacity-50">
                      {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                      {busy ? "Tekshirilmoqda…" : "Tasdiqlash"}
                    </button>
                  </div>
                  <button
                    type="button"
                    disabled={busy || resendIn > 0}
                    onClick={() => void (challengeId ? resendCode() : sendCode())}
                    className="self-center text-xs font-medium text-[var(--fb-ink-secondary)] underline-offset-2 hover:underline disabled:no-underline disabled:opacity-60"
                  >
                    {resendIn > 0 ? `Qayta yuborish ${resendIn} soniyadan so‘ng` : "Kodni qayta yuborish"}
                  </button>
                </form>
              </motion.div>
            )}

            {step === "factor" && (
              <motion.div key="factor" {...fade} className="flex flex-col gap-4">
                <p className="text-sm leading-relaxed text-[var(--fb-ink-secondary)]">
                  Xavfsizlik uchun yana bir tasdiq kerak: authenticator ilovadagi kod yoki ilgari saqlab qo‘ygan zaxira kodingiz.
                </p>
                <div role="tablist" aria-label="Tasdiqlash usuli" className="grid grid-cols-2 gap-1 rounded-2xl skeuo-well p-1">
                  {(
                    [
                      ["totp", "Authenticator kodi"],
                      ["backup", "Zaxira kod"],
                    ] as const
                  ).map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      role="tab"
                      aria-selected={factorKind === value}
                      onClick={() => {
                        setFactorKind(value);
                        setFactor("");
                      }}
                      className={`rounded-xl px-3 py-2 text-sm font-semibold ${factorKind === value ? "skeuo-card text-[var(--fb-ink)]" : "text-[var(--fb-ink-secondary)]"}`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <form
                  className="flex flex-col gap-3"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void submitFactor(true);
                  }}
                >
                  <label htmlFor={`${ids}-factor`} className="text-sm font-semibold text-[var(--fb-ink)]">
                    {factorKind === "totp" ? "Ilovadagi 6 xonali kod" : "Zaxira kod"}
                  </label>
                  <div className="relative">
                    <KeyRound className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--fb-ink-muted)]" aria-hidden="true" />
                    <input
                      id={`${ids}-factor`}
                      type="text"
                      inputMode={factorKind === "totp" ? "numeric" : "text"}
                      autoComplete="one-time-code"
                      autoCapitalize="none"
                      spellCheck={false}
                      required
                      autoFocus
                      value={factor}
                      onChange={(e) => setFactor(factorKind === "totp" ? e.target.value.replace(/\D/g, "").slice(0, 6) : e.target.value)}
                      placeholder={factorKind === "totp" ? "••••••" : "Zaxira kodingiz"}
                      className="skeuo-input w-full rounded-2xl py-3 pl-11 pr-4 text-sm font-mono"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={busy || (factorKind === "totp" ? factor.length !== 6 : factor.trim().length < 20)}
                    className="skeuo-btn-tone w-full rounded-2xl px-4 py-3.5 text-sm disabled:opacity-50"
                  >
                    {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <ShieldCheck className="h-4 w-4" aria-hidden="true" />}
                    {busy ? "Tekshirilmoqda…" : "Davom etish"}
                  </button>
                </form>
                <div className="rounded-2xl skeuo-well p-3.5 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
                  Ikkalasi ham yo‘qmi? So‘rovingiz shaxsingizni tekshirish uchun yuboriladi — talaba bo‘lsangiz, uni universitetingiz
                  koordinatori tasdiqlaydi.{" "}
                  <button type="button" disabled={busy} onClick={() => void submitFactor(false)} className="font-semibold text-[var(--fb-ink)] underline underline-offset-2">
                    Qo‘lda tekshiruvga yuborish
                  </button>
                </div>
              </motion.div>
            )}

            {step === "password" && (
              <motion.form
                key="password"
                {...fade}
                className="flex flex-col gap-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  void savePassword();
                }}
              >
                <p className="text-sm leading-relaxed text-[var(--fb-ink-secondary)]">
                  Yangi parol o‘rnating. Saqlangach, barcha qurilmalardagi eski sessiyalar yopiladi va ikki bosqichli himoyani qaytadan yoqishingiz kerak bo‘ladi.
                </p>
                <div>
                  <label htmlFor={`${ids}-pw`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
                    Yangi parol
                  </label>
                  <div className="relative">
                    <input
                      id={`${ids}-pw`}
                      type={showPw ? "text" : "password"}
                      autoComplete="new-password"
                      required
                      minLength={12}
                      autoFocus
                      value={pw}
                      onChange={(e) => setPw(e.target.value)}
                      className="skeuo-input w-full rounded-2xl py-3 pl-4 pr-12 text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw((v) => !v)}
                      aria-label={showPw ? "Parolni yashirish" : "Parolni ko‘rsatish"}
                      aria-pressed={showPw}
                      className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)]"
                    >
                      {showPw ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
                    </button>
                  </div>
                  <p className={`mt-1.5 text-xs ${pw && problems.length ? "text-amber-700 dark:text-amber-300" : "text-[var(--fb-ink-muted)]"}`}>
                    {pw && !problems.length ? "Yaxshi parol." : "Kamida 12 ta belgi, harf va raqam aralash."}
                  </p>
                </div>
                <div>
                  <label htmlFor={`${ids}-pw2`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
                    Parolni takrorlang
                  </label>
                  <input
                    id={`${ids}-pw2`}
                    type={showPw ? "text" : "password"}
                    autoComplete="new-password"
                    required
                    value={pw2}
                    onChange={(e) => setPw2(e.target.value)}
                    className="skeuo-input w-full rounded-2xl py-3 px-4 text-sm"
                  />
                  {pw2 && pw !== pw2 && <p className="mt-1.5 text-xs text-amber-700 dark:text-amber-300">Parollar bir xil emas.</p>}
                </div>
                <button
                  type="submit"
                  disabled={busy || problems.length > 0 || pw !== pw2}
                  className="skeuo-btn-tone w-full rounded-2xl px-4 py-3.5 text-sm disabled:opacity-50"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                  {busy ? "Saqlanmoqda…" : "Parolni saqlash"}
                </button>
              </motion.form>
            )}

            {step === "done" && (
              <motion.div key="done" {...fade} className="flex flex-col gap-4">
                <div className="flex items-start gap-2.5 rounded-2xl border border-emerald-500/25 bg-emerald-500/10 p-3.5 text-sm text-emerald-700 dark:text-emerald-300">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>Yangi parolingiz saqlandi. Endi u bilan kiring. Kirgach, «Xavfsizlik» bo‘limida ikki bosqichli himoyani qayta yoqing.</span>
                </div>
                <Link href="/kirish" className="skeuo-btn-tone w-full rounded-2xl px-4 py-3.5 text-sm">
                  Kirish sahifasiga
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </motion.div>
            )}

            {step === "review" && (
              <motion.div key="review" {...fade} className="flex flex-col gap-4">
                {reviewStatus === "APPROVED" ? (
                  <div className="flex items-start gap-2.5 rounded-2xl border border-emerald-500/25 bg-emerald-500/10 p-3.5 text-sm text-emerald-700 dark:text-emerald-300">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                    <span>
                      Shaxsingiz tasdiqlandi. Endi «Boshidan boshlash»ni bosing va xuddi shu telefon/pochta bilan kod oling — qo‘shimcha tasdiq
                      so‘ralmaydi. Tasdiq 72 soat amal qiladi.
                    </span>
                  </div>
                ) : (
                  <p className="text-sm leading-relaxed text-[var(--fb-ink-secondary)]">
                    Ikkinchi tasdiq bo‘lmagani uchun shaxsingiz tekshiriladi. Talaba bo‘lsangiz, universitetingiz koordinatoriga (dekanatga) murojaat
                    qiling — u sizni tekshirib, so‘rovni tasdiqlaydi. Bu hisobingizni telefon raqamingiz boshqa birovga o‘tib qolgan holatlardan himoya qiladi.
                  </p>
                )}
                <div className="rounded-2xl skeuo-well p-3.5 text-sm">
                  <div className="text-xs text-[var(--fb-ink-muted)]">So‘rov raqami</div>
                  <div className="font-mono font-semibold text-[var(--fb-ink)] break-all">{recoveryId}</div>
                  <div className="mt-2 text-xs text-[var(--fb-ink-muted)]">Holati</div>
                  <div className="font-semibold text-[var(--fb-ink)]">
                    {reviewStatus === "PENDING_REVIEW"
                      ? "Tekshiruv kutilmoqda"
                      : reviewStatus === "APPROVED"
                        ? "Tasdiqlandi"
                        : reviewStatus === "REJECTED"
                          ? "Rad etildi"
                          : reviewStatus === "COMPLETED" || reviewStatus === "CONSUMED"
                            ? "Yakunlangan"
                            : reviewStatus}
                  </div>
                </div>
                <p className="text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
                  Talaba bo‘lmasangiz, so‘rov raqamini saqlab{" "}
                  <Link href="/haqida" className="font-semibold underline underline-offset-2">
                    qo‘llab-quvvatlash xizmatiga
                  </Link>{" "}
                  yozing. Tasdiq kelgach yoki authenticator ilovangiz/zaxira kodingiz topilsa, jarayonni boshidan boshlang.
                </p>
                <div className="flex gap-2">
                  <button type="button" onClick={restart} className="skeuo-btn-secondary flex-1 rounded-2xl px-4 py-3 text-sm">
                    Boshidan boshlash
                  </button>
                  <button type="button" disabled={busy} onClick={() => void refreshReview()} className="skeuo-btn-secondary flex-1 rounded-2xl px-4 py-3 text-sm">
                    {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                    Holatni yangilash
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </div>
    </div>
  );
}
