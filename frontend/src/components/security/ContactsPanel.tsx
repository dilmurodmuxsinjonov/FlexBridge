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
  Star,
  Trash2,
  X,
} from "lucide-react";
import { fetchAuthChallengeStatus, fetchAuthOptions } from "@/lib/api";
import { humanizeMessage } from "@/lib/errorText";
import {
  bindSecondaryContact,
  consumeContactChallenge,
  fetchMyContacts,
  removeMyContact,
  resendAuthChallenge,
  setPrimaryContact,
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

  const [pendingAction, setPendingAction] = useState<{
    kind: "primary" | "remove";
    contact: UserContactItem;
  } | null>(null);
  const [actionPassword, setActionPassword] = useState("");
  const [actionTotp, setActionTotp] = useState("");
  const [actionBusy, setActionBusy] = useState(false);

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

  const openContactAction = (kind: "primary" | "remove", contact: UserContactItem) => {
    setError(null);
    setNotice(null);
    setActionPassword("");
    setActionTotp("");
    setPendingAction({ kind, contact });
  };

  const handleConfirmContactAction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pendingAction || !actionPassword.trim()) return;
    setActionBusy(true);
    setError(null);
    setNotice(null);
    try {
      const totp = actionTotp.trim() || undefined;
      if (pendingAction.kind === "primary") {
        await setPrimaryContact(pendingAction.contact.id, actionPassword.trim(), totp);
        setNotice(`${pendingAction.contact.masked_destination} asosiy kirish aloqasi sifatida belgilandi.`);
      } else {
        const res = await removeMyContact(pendingAction.contact.id, actionPassword.trim(), totp);
        setNotice(
          res.promoted_primary_contact_id
            ? `${pendingAction.contact.masked_destination} o‘chirildi va keyingi tasdiqlangan aloqa avtomatik asosiy qilib belgilandi.`
            : `${pendingAction.contact.masked_destination} hisobdan o‘chirildi.`
        );
      }
      const latest = await fetchMyContacts();
      setContacts(latest);
      setPendingAction(null);
      setActionPassword("");
      setActionTotp("");
    } catch (err: unknown) {
      setError(humanizeMessage(err instanceof Error ? err.message : null));
    } finally {
      setActionBusy(false);
    }
  };

  return (
    <div className="skeuo-card p-5 md:p-6 rounded-2xl space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--fb-border)] pb-4">
        <div>
          <h2 className="text-base font-semibold text-[var(--fb-ink)] flex items-center gap-2">
            <Mail className="w-5 h-5 text-sky-500" aria-hidden="true" />
            Tasdiqlangan Aloqalar ({contacts.length})
          </h2>
          <p className="text-xs text-[var(--fb-ink-secondary)] mt-1">
            Kirish va tiklash uchun bog‘langan telefon raqamlar hamda elektron pochta manzillari.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setShowAdd((prev) => !prev);
            setPendingAction(null);
            setError(null);
          }}
          className="skeuo-btn-obsidian px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" aria-hidden="true" />
          <span>Qo‘shimcha aloqa qo‘shish</span>
        </button>
      </div>

      {error && (
        <div role="alert" className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/25 text-rose-700 dark:text-rose-300 text-xs flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {notice && (
        <div role="status" className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-700 dark:text-emerald-300 text-xs flex items-center justify-between gap-2">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
            {notice}
          </span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Yopish" className="text-emerald-600 dark:text-emerald-400">
            <X className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        </div>
      )}

      {showAdd && (
        <div className="skeuo-well p-4 rounded-xl space-y-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-[var(--fb-ink)]">Yangi telefon yoki e-pochta ulash</span>
            <button type="button" onClick={resetWizard} aria-label="Qo‘shish oynasini yopish" className="text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)]">
              <X className="w-4 h-4" aria-hidden="true" />
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
                className="skeuo-input w-full px-3.5 py-2 rounded-xl text-xs"
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
                          ? "bg-sky-500/15 border-sky-500/40 text-sky-700 dark:text-sky-300"
                          : "skeuo-btn-secondary"
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
                className="skeuo-btn-obsidian px-4 py-2 rounded-xl text-xs font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
              >
                {busy && <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />}
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
                  className="skeuo-input px-3.5 py-2 rounded-xl text-xs font-mono"
                />
                <button
                  type="submit"
                  disabled={busy || code.trim().length !== 6}
                  className="skeuo-btn-obsidian px-4 py-2 rounded-xl text-xs font-semibold disabled:opacity-50"
                >
                  Kodni tasdiqlash
                </button>
                <button
                  type="button"
                  disabled={busy || resendIn > 0}
                  onClick={() => void handleResend()}
                  className="skeuo-btn-secondary px-3 py-2 rounded-xl text-xs font-semibold inline-flex items-center gap-1 disabled:opacity-50"
                >
                  <RefreshCw className="w-3 h-3" aria-hidden="true" />
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
                  className="skeuo-input px-3.5 py-2 rounded-xl text-xs"
                />
                {totpEnabled && (
                  <input
                    type="text"
                    maxLength={6}
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                    placeholder="Joriy 6 xonali TOTP kodi"
                    className="skeuo-input px-3.5 py-2 rounded-xl text-xs font-mono"
                  />
                )}
              </div>
              <button
                type="submit"
                disabled={busy || !password.trim()}
                className="skeuo-btn-accent px-4 py-2 rounded-xl text-xs font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
              >
                {busy && <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />}
                <span>Aloqani bog‘lash</span>
              </button>
            </form>
          )}
        </div>
      )}

      {pendingAction && (
        <form onSubmit={handleConfirmContactAction} className="skeuo-well p-4 rounded-xl space-y-3 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-[var(--fb-ink)]">
              {pendingAction.kind === "primary"
                ? `${pendingAction.contact.masked_destination} manzilini asosiy login sifatida belgilash`
                : `${pendingAction.contact.masked_destination} manzilini hisobdan o‘chirish`}
            </span>
            <button
              type="button"
              onClick={() => setPendingAction(null)}
              aria-label="Tasdiqlashni bekor qilish"
              className="text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)]"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="password"
              required
              value={actionPassword}
              onChange={(e) => setActionPassword(e.target.value)}
              placeholder="Tasdiqlash uchun joriy parol *"
              aria-label="Aloqa amali uchun joriy parol"
              className="skeuo-input px-3.5 py-2 rounded-xl text-xs"
            />
            {totpEnabled && (
              <input
                type="text"
                maxLength={6}
                value={actionTotp}
                onChange={(e) => setActionTotp(e.target.value.replace(/\D/g, ""))}
                placeholder="Joriy 6 xonali TOTP kodi"
                aria-label="Aloqa amali uchun TOTP kodi"
                className="skeuo-input px-3.5 py-2 rounded-xl text-xs font-mono"
              />
            )}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setPendingAction(null)}
              className="skeuo-btn-secondary px-3 py-1.5 rounded-xl text-xs font-semibold"
            >
              Bekor qilish
            </button>
            <button
              type="submit"
              disabled={actionBusy || !actionPassword.trim()}
              className={`px-4 py-1.5 rounded-xl text-xs font-semibold inline-flex items-center gap-1.5 disabled:opacity-50 ${
                pendingAction.kind === "remove"
                  ? "bg-rose-600 hover:bg-rose-500 text-white"
                  : "skeuo-btn-obsidian"
              }`}
            >
              {actionBusy && <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />}
              <span>
                {pendingAction.kind === "primary" ? "Asosiy qilib tasdiqlash" : "O‘chirishni tasdiqlash"}
              </span>
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="py-4 flex items-center gap-2 text-xs text-[var(--fb-ink-secondary)]">
          <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
          <span>Aloqalar yuklanmoqda...</span>
        </div>
      ) : contacts.length === 0 ? (
        <p className="text-xs text-[var(--fb-ink-secondary)]">Tasdiqlangan aloqa manzili topilmadi.</p>
      ) : (
        <div className="divide-y divide-[var(--fb-border)]">
          {contacts.map((c) => {
            const canRemove = contacts.length > 1;
            return (
              <div key={c.id} className="py-3 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2.5">
                  {c.channel === "EMAIL" ? (
                    <Mail className="w-4 h-4 text-sky-500 shrink-0" aria-hidden="true" />
                  ) : (
                    <Phone className="w-4 h-4 text-emerald-500 shrink-0" aria-hidden="true" />
                  )}
                  <div>
                    <span className="font-mono font-semibold text-[var(--fb-ink)]">{c.masked_destination}</span>
                    <div className="text-[11px] text-[var(--fb-ink-muted)]">
                      {c.channel === "EMAIL" ? "Elektron pochta" : "Telefon raqam"}
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                      c.is_primary
                        ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300 border-emerald-500/25"
                        : "skeuo-badge-recessed"
                    }`}
                  >
                    {c.is_primary ? "Asosiy" : "Qo‘shimcha"}
                  </span>
                  {!c.is_primary && (
                    <button
                      type="button"
                      onClick={() => openContactAction("primary", c)}
                      className="skeuo-btn-secondary px-2.5 py-1 rounded-lg text-[11px] font-semibold inline-flex items-center gap-1"
                    >
                      <Star className="w-3 h-3" aria-hidden="true" />
                      <span>Asosiy qilish</span>
                    </button>
                  )}
                  {canRemove ? (
                    <button
                      type="button"
                      onClick={() => openContactAction("remove", c)}
                      className="px-2.5 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-700 dark:text-rose-300 border border-rose-500/25 text-[11px] font-semibold inline-flex items-center gap-1 transition"
                    >
                      <Trash2 className="w-3 h-3" aria-hidden="true" />
                      <span>O‘chirish</span>
                    </button>
                  ) : (
                    <span
                      title="Hisobda kamida bitta tasdiqlangan kirish manzili qolishi shart"
                      className="text-[10px] text-[var(--fb-ink-muted)]"
                    >
                      Yagona kirish manzili
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
