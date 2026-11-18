"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Fingerprint,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { humanizeMessage } from "@/lib/errorText";
import {
  finishPasskeyRegistration,
  revokePasskey,
  startPasskeyRegistration,
  type PasskeyOverviewItem,
} from "@/lib/authSecurity";
import { createPasskeyCredential, isWebAuthnSupported } from "@/lib/webauthn";

export default function PasskeysPanel({
  passkeys,
  totpEnabled,
  onUpdated,
}: {
  passkeys: PasskeyOverviewItem[];
  totpEnabled: boolean;
  onUpdated: () => void | Promise<void>;
}) {
  const [showAdd, setShowAdd] = useState(false);
  const [revokeTargetId, setRevokeTargetId] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const webauthnOk = isWebAuthnSupported();

  const resetForm = () => {
    setPassword("");
    setTotpCode("");
    setShowAdd(false);
    setRevokeTargetId(null);
  };

  const handleRegisterPasskey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setError("Passkey qo‘shish uchun joriy parolingizni kiriting.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const opts = await startPasskeyRegistration(password.trim(), totpCode.trim() || undefined);
      const credential = await createPasskeyCredential(opts.public_key);
      const verified = await finishPasskeyRegistration(opts.ceremony_token, credential);
      resetForm();
      setNotice(
        verified.reauthentication_required
          ? "Passkey muvaffaqiyatli qo‘shildi! Xavfsizlik uchun sessiyani yangilab qayta kirish talab qilinishi mumkin."
          : "Passkey muvaffaqiyatli ro‘yxatdan o‘tkazildi."
      );
      await onUpdated();
    } catch (err: unknown) {
      setError(humanizeMessage(err instanceof Error ? err.message : null));
    } finally {
      setBusy(false);
    }
  };

  const handleRevokePasskey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!revokeTargetId || !password.trim()) {
      setError("Bekor qilish uchun joriy parolingizni kiriting.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const res = await revokePasskey(revokeTargetId, password.trim(), totpCode.trim() || undefined);
      resetForm();
      setNotice(
        res.reauthentication_required
          ? "Passkey o‘chirildi. Xavfsizlik sessiyangiz yangilandi."
          : "Passkey bekor qilindi."
      );
      await onUpdated();
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
            <Fingerprint className="w-5 h-5 text-emerald-400" />
            Passkey (WebAuthn / Biometrik Kirish) ({passkeys.length})
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Touch ID, Face ID, Windows Hello yoki xavfsizlik kaliti orqali parolsiz yoki tezkor 2FA kirish.
          </p>
        </div>
        <button
          type="button"
          disabled={!webauthnOk && false}
          onClick={() => {
            setRevokeTargetId(null);
            setShowAdd((prev) => !prev);
            setError(null);
            setPassword("");
            setTotpCode("");
          }}
          className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Passkey qo‘shish</span>
        </button>
      </div>

      {!webauthnOk && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
          Joriy muhitda brauzer WebAuthn API aniqlanmadi. Passkey ro‘yxatdan o‘tkazish uchun HTTPS/localhost zamonaviy brauzerdan foydalaning.
        </div>
      )}

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

      {(showAdd || revokeTargetId) && (
        <form
          onSubmit={revokeTargetId ? handleRevokePasskey : handleRegisterPasskey}
          className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.08] space-y-3 text-xs"
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold text-white">
              {revokeTargetId ? "Passkeyni o‘chirishni tasdiqlang" : "Yangi Passkey ulash"}
            </span>
            <button type="button" onClick={resetForm} className="text-zinc-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-[11px] text-zinc-400">Joriy parol *</span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-xs text-white"
              />
            </label>
            {totpEnabled && (
              <label className="flex flex-col gap-1">
                <span className="text-[11px] text-zinc-400">Joriy 6 xonali TOTP kodi</span>
                <input
                  type="text"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                  placeholder="123456"
                  className="px-3 py-2 rounded-lg bg-[#18181b] border border-white/[0.1] text-xs text-white font-mono"
                />
              </label>
            )}
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-3 py-1.5 rounded-lg bg-zinc-800 text-zinc-300">
              Bekor qilish
            </button>
            <button
              type="submit"
              disabled={busy}
              className={`px-4 py-1.5 rounded-lg text-white font-semibold inline-flex items-center gap-1.5 disabled:opacity-50 ${
                revokeTargetId ? "bg-rose-600 hover:bg-rose-500" : "bg-emerald-600 hover:bg-emerald-500"
              }`}
            >
              {busy && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{revokeTargetId ? "Passkeyni o‘chirish" : "Qurilma bilan tasdiqlash"}</span>
            </button>
          </div>
        </form>
      )}

      {passkeys.length === 0 ? (
        <p className="text-xs text-zinc-400">Hozircha Passkey ulanmagan.</p>
      ) : (
        <div className="divide-y divide-white/[0.06]">
          {passkeys.map((pk) => (
            <div key={pk.id} className="py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white">
                    {pk.device_type === "multiDevice" ? "Sinxronlangan Passkey" : "Qurilma Passkey"}
                  </span>
                  {pk.backed_up && (
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[10px]">
                      Zaxiralangan
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-zinc-400 font-mono mt-0.5">
                  Yaratilgan: {pk.created_at ? new Date(pk.created_at).toLocaleDateString("uz-UZ") : "—"}
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowAdd(false);
                  setRevokeTargetId(pk.id);
                  setPassword("");
                  setTotpCode("");
                  setError(null);
                }}
                className="px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/20 text-xs font-semibold inline-flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>O‘chirish</span>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
