"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Mail,
  Phone,
  Plus,
  RefreshCw,
  X,
} from "lucide-react";
import { fetchAuthChallengeStatus, fetchAuthOptions } from "@/lib/api";
import { humanizeMessage } from "@/lib/errorText";
import {
  bindSecondaryContact,
  consumeContactChallenge,
  fetchMyContacts,
  resendAuthChallenge,
  startContactChallenge,
  type UserContactItem,
} from "@/lib/authSecurity";
import TelegramVerification, { type TelegramMode } from "@/components/TelegramVerification";

export default function ContactsPanel({ totpEnabled }: { totpEnabled: boolean }) {
  const [contacts, setContacts] = useState<UserContactItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [telegramMode, setTelegramMode] = useState<TelegramMode>("DISABLED");
  const [botUsername, setBotUsername] = useState("");

  const [showAdd, setShowAdd] = useState(false);
  const [destination, setDestination] = useState("");
  const [deliveryMethod, setDeliveryMethod] = useState<"SMS" | "TELEGRAM">("SMS");

  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [deepLink, setDeepLink] = useState<string | null>(null);
  const [telegramVerified, setTelegramVerified] = useState(false);
  const [code, setCode] = useState("");
  const [resendIn, setResendIn] = useState(0);
  const [verificationToken, setVerificationToken] = useState<string | null>(null);

  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const isEmail = destination.includes("@");
  const channel: "EMAIL" | "PHONE" = isEmail ? "EMAIL" : "PHONE";
  const effectiveDelivery: "EMAIL" | "SMS" | "TELEGRAM" = isEmail ? "EMAIL" : deliveryMethod;

  useEffect(() => {
    let active = true;
    Promise.allSettled([fetchMyContacts(), fetchAuthOptions()])
      .then(([cRes, oRes]) => {
        if (!active) return;
        if (cRes.status === "fulfilled") setContacts(cRes.value);
        if (oRes.status === "fulfilled") {
          if (oRes.value.telegram_mode) setTelegramMode(oRes.value.telegram_mode);
          if (oRes.value.telegram_bot_username) setBotUsername(oRes.value.telegram_bot_username);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (resendIn <= 0) return;
    const t = setTimeout(() => setResendIn((v) => v - 1), 1000);
    return () => clearTimeout(t);
  }, [resendIn]);

  useEffect(() => {
    if (!challengeId || effectiveDelivery !== "TELEGRAM" || telegramVerified || verificationToken) return;
    let active = true;
    const interval = setInterval(async () => {
      try {
        const st = await fetchAuthChallengeStatus(challengeId);
        if (active && st.telegram_verified) setTelegramVerified(true);
      } catch {
        // retry silently
      }
    }, 3000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [challengeId, effectiveDelivery, telegramVerified, verificationToken]);

  const resetWizard = () => {
    setShowAdd(false);
    setDestination("");
    setChallengeId(null);
    setDeepLink(null);
    setTelegramVerified(false);
    setCode("");
    setVerificationToken(null);
    setPassword("");
    setTotpCode("");
  };

  const handleStartChallenge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!destination.trim()) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const res = await startContactChallenge(channel, destination.trim(), effectiveDelivery);
      setChallengeId(res.challenge_id);
      setDeepLink(res.telegram_deep_link ?? null);
      if (res.telegram_bot_username) setBotUsername(res.telegram_bot_username);
      setTelegramVerified(false);
      setCode("");
      setResendIn(res.resend_after ?? 60);
    } catch (err: unknown) {
      setError(humanizeMessage(err instanceof Error ? err.message : null));
    } finally {
      setBusy(false);
    }
  };

  const handleResend = async () => {
    if (!challengeId || resendIn > 0) return;
    setBusy(true);
    setError(null);
    try {
      const res = await resendAuthChallenge(challengeId, "CONTACT");
      setChallengeId(res.challenge_id);
      setDeepLink(res.telegram_deep_link ?? null);
      if (res.telegram_bot_username) setBotUsername(res.telegram_bot_username);
      setTelegramVerified(false);
      setCode("");
      setResendIn(res.resend_after ?? 60);
      setNotice("Tasdiqlash kodi qayta yuborildi (API-021).");
    } catch (err: unknown) {
      setError(humanizeMessage(err instanceof Error ? err.message : null));
    } finally {
      setBusy(false);
    }
  };

  const handleConsumeCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!challengeId || code.trim().length !== 6) return;
    setBusy(true);
    setError(null);
    try {
      const res = await consumeContactChallenge(challengeId, code.trim());
      setVerificationToken(res.verification_token);
    } catch (err: unknown) {
      setError(humanizeMessage(err instanceof Error ? err.message : null));
    } finally {
      setBusy(false);
    }
  };

  const handleBindContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verificationToken || !password.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await bindSecondaryContact({
        verification_token: verificationToken,
        current_password: password.trim(),
        totp_code: totpCode.trim() || undefined,
      });
      const latest = await fetchMyContacts();
      setContacts(latest);
      resetWizard();
      setNotice("Qo‘shimcha aloqa manzili tasdiqlandi va hisobingizga bog‘landi.");
    } catch (err: unknown) {
      setError(humanizeMessage(err instanceof Error ? err.message : null));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-5 md:p-6 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Mail className="w-5 h-5 text-sky-400" />
            Tasdiqlangan Aloqalar ({contacts.length})
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Kirish va tiklash uchun bog‘langan telefon raqamlar hamda elektron pochta manzillari.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setShowAdd((prev) => !prev);
            setError(null);
          }}
          className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold flex items-center gap-1.5 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Qo‘shimcha aloqa qo‘shish</span>
        </button>
      </div>

      {error && (
        <div role="alert" className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {notice && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between gap-2">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            {notice}
          </span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Yopish" className="text-emerald-400">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {showAdd && (
        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.08] space-y-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-white">Yangi telefon yoki e-pochta ulash</span>
            <button type="button" onClick={resetWizard} className="text-zinc-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>

          {!challengeId ? (
            <form onSubmit={handleStartChallenge} className="space-y-3">
              <input
                type="text"
                required
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="+998901234567 yoki name@example.com"
                className="w-full px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-xs text-white"
              />
              {!isEmail && telegramMode !== "DISABLED" && (
                <div className="flex gap-2">
                  {(["SMS", "TELEGRAM"] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setDeliveryMethod(m)}
                      className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${
                        deliveryMethod === m
                          ? "bg-sky-500/20 border-sky-500/40 text-sky-300"
                          : "bg-white/[0.04] border-white/[0.08] text-zinc-400"
                      }`}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              )}
              <button
                type="submit"
                disabled={busy || !destination.trim()}
                className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
              >
                {busy && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Kod yuborish</span>
              </button>
            </form>
          ) : !verificationToken ? (
            <form onSubmit={handleConsumeCode} className="space-y-3">
              {effectiveDelivery === "TELEGRAM" && (
                <TelegramVerification
                  mode={telegramMode}
                  challengeId={challengeId}
                  phone={destination.trim()}
                  botUsername={botUsername}
                  deepLink={deepLink}
                  verified={telegramVerified}
                  onSimulatedCode={(c) => {
                    setCode(c);
                    setTelegramVerified(true);
                  }}
                />
              )}
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  maxLength={6}
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="6 xonali kod"
                  className="px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-xs text-white font-mono"
                />
                <button
                  type="submit"
                  disabled={busy || code.trim().length !== 6}
                  className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold disabled:opacity-50"
                >
                  Kodni tasdiqlash
                </button>
                <button
                  type="button"
                  disabled={busy || resendIn > 0}
                  onClick={() => void handleResend()}
                  className="px-3 py-2 rounded-lg bg-white/[0.06] text-zinc-300 text-xs font-semibold inline-flex items-center gap-1 disabled:opacity-50"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>{resendIn > 0 ? `Qayta yuborish (${resendIn}s)` : "Kodni qayta yuborish"}</span>
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleBindContact} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Tasdiqlash uchun joriy parol *"
                  className="px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-xs text-white"
                />
                {totpEnabled && (
                  <input
                    type="text"
                    maxLength={6}
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                    placeholder="Joriy 6 xonali TOTP kodi"
                    className="px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-xs text-white font-mono"
                  />
                )}
              </div>
              <button
                type="submit"
                disabled={busy || !password.trim()}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
              >
                {busy && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Aloqani bog‘lash</span>
              </button>
            </form>
          )}
        </div>
      )}

      {loading ? (
        <div className="py-4 flex items-center gap-2 text-xs text-zinc-400">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Aloqalar yuklanmoqda...</span>
        </div>
      ) : contacts.length === 0 ? (
        <p className="text-xs text-zinc-400">Tasdiqlangan aloqa manzili topilmadi.</p>
      ) : (
        <div className="divide-y divide-white/[0.06]">
          {contacts.map((c) => (
            <div key={c.id} className="py-3 flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2.5">
                {c.channel === "EMAIL" ? (
                  <Mail className="w-4 h-4 text-sky-400" />
                ) : (
                  <Phone className="w-4 h-4 text-emerald-400" />
                )}
                <div>
                  <span className="font-mono font-semibold text-white">{c.masked_destination}</span>
                  <div className="text-[11px] text-zinc-400">
                    {c.channel === "EMAIL" ? "Elektron pochta" : "Telefon raqam"}
                  </div>
                </div>
              </div>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                  c.is_primary
                    ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                    : "bg-white/[0.06] text-zinc-300 border-white/[0.1]"
                }`}
              >
                {c.is_primary ? "Asosiy" : "Qo‘shimcha"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
