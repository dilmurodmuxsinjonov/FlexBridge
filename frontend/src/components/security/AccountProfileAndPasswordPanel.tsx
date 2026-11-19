"use client";

import React, { useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  KeyRound,
  Loader2,
  Save,
  UserCheck,
} from "lucide-react";
import { changeMyPassword, updateMyProfile } from "@/lib/authSecurity";
import { humanizeMessage } from "@/lib/errorText";
import { ROLE_AUTHORITY_SUMMARY } from "@/lib/roles";

export interface AccountProfileAndPasswordPanelProps {
  displayName: string;
  roles: string[];
  totpEnabled: boolean;
  onDisplayNameUpdated: (nextName: string) => void;
  onPasswordChanged: () => void | Promise<void>;
}

const ROLE_LABELS = new Map<string, string>(
  ROLE_AUTHORITY_SUMMARY.map((item) => [item.code, item.labelUz])
);

export default function AccountProfileAndPasswordPanel({
  displayName,
  roles,
  totpEnabled,
  onDisplayNameUpdated,
  onPasswordChanged,
}: AccountProfileAndPasswordPanelProps) {
  // Profile name state (`null` means track incoming `displayName` prop without an effect).
  const [nameDraft, setNameDraft] = useState<string | null>(null);
  const [profileBusy, setProfileBusy] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileNotice, setProfileNotice] = useState<string | null>(null);

  // Password change state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordNotice, setPasswordNotice] = useState<string | null>(null);

  const effectiveName = nameDraft ?? displayName;

  const roleBadges = useMemo(
    () =>
      roles.map((code) => ({
        code,
        label: ROLE_LABELS.get(code.trim().toUpperCase()) ?? code,
      })),
    [roles]
  );

  const handleSaveName = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = effectiveName.replace(/\s+/g, " ").trim();
    if (trimmed.length < 2) {
      setProfileError("Ism-familiya kamida 2 ta belgidan iborat bo‘lishi kerak.");
      return;
    }
    setProfileBusy(true);
    setProfileError(null);
    setProfileNotice(null);
    try {
      const res = await updateMyProfile(trimmed);
      setNameDraft(null);
      onDisplayNameUpdated(res.display_name);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("flexbridge:auth-changed"));
      }
      setProfileNotice("Akkaunt nomi muvaffaqiyatli yangilandi.");
    } catch (err: unknown) {
      setProfileError(humanizeMessage(err instanceof Error ? err.message : null));
    } finally {
      setProfileBusy(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordNotice(null);
    if (!currentPassword) {
      setPasswordError("Joriy parolni kiriting.");
      return;
    }
    if (newPassword.length < 12) {
      setPasswordError("Yangi parol kamida 12 ta belgidan iborat bo‘lishi shart.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("Yangi parol va tasdiqlash maydoni mos kelmadi.");
      return;
    }
    if (newPassword === currentPassword) {
      setPasswordError("Yangi parol joriy paroldan farq qilishi kerak.");
      return;
    }
    setPasswordBusy(true);
    try {
      const res = await changeMyPassword(
        currentPassword,
        newPassword,
        totpCode.trim() || undefined
      );
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTotpCode("");
      await onPasswordChanged();
      setPasswordNotice(
        res.revoked_other_sessions > 0
          ? `Parol muvaffaqiyatli almashtirildi. Boshqa qurilmalardagi ${res.revoked_other_sessions} ta faol sessiya yakunlandi.`
          : "Parol muvaffaqiyatli almashtirildi. Joriy sessiyangiz saqlab qolindi."
      );
    } catch (err: unknown) {
      setPasswordError(humanizeMessage(err instanceof Error ? err.message : null));
    } finally {
      setPasswordBusy(false);
    }
  };

  return (
    <section aria-label="Profil nomi va parol sozlamalari" className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Card 1: Akkaunt nomi va rollar */}
      <div className="skeuo-card rounded-2xl p-5 md:p-6 space-y-4">
        <div className="border-b border-[var(--fb-border)] pb-4">
          <h2 className="text-base font-semibold text-[var(--fb-ink)] flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-sky-500" aria-hidden="true" />
            <span>Akkaunt nomi &amp; rollar</span>
          </h2>
          <p className="text-xs text-[var(--fb-ink-secondary)] mt-1">
            Kabinet, xabarlar, shartnomalar va imzolarda ko‘rinadigan rasmiy ismingizni tahrirlang.
          </p>
        </div>

        {roleBadges.length > 0 && (
          <div className="flex flex-wrap gap-1.5" aria-label="Biriktirilgan rollar">
            {roleBadges.map((r) => (
              <span
                key={r.code}
                className="skeuo-badge-recessed rounded-full px-2.5 py-1 text-[11px] font-medium"
                title={r.code}
              >
                {r.label}
              </span>
            ))}
          </div>
        )}

        {profileError && (
          <div
            role="alert"
            className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/25 text-rose-700 dark:text-rose-300 text-xs flex items-start gap-2"
          >
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
            <span>{profileError}</span>
          </div>
        )}

        {profileNotice && (
          <div
            role="status"
            className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-700 dark:text-emerald-300 text-xs flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>{profileNotice}</span>
          </div>
        )}

        <form onSubmit={handleSaveName} className="space-y-3">
          <div>
            <label
              htmlFor="account-display-name"
              className="block text-[11px] font-semibold text-[var(--fb-ink-secondary)] mb-1"
            >
              To‘liq ism-familiya
            </label>
            <input
              id="account-display-name"
              type="text"
              required
              minLength={2}
              maxLength={200}
              value={effectiveName}
              onChange={(e) => setNameDraft(e.target.value)}
              placeholder="Masalan: Dilnoza Karimova"
              className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-xs"
            />
          </div>
          <div className="flex items-center justify-between gap-2 pt-1">
            <span className="text-[11px] text-[var(--fb-ink-muted)]">
              Kamida 2 belgi, barcha rollarda ishlaydi.
            </span>
            <button
              type="submit"
              disabled={profileBusy || effectiveName.trim().length < 2}
              className="skeuo-btn-obsidian rounded-xl px-4 py-2 text-xs font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
            >
              {profileBusy ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <Save className="w-3.5 h-3.5" aria-hidden="true" />
              )}
              <span>Nomni saqlash</span>
            </button>
          </div>
        </form>
      </div>

      {/* Card 2: Parolni almashtirish */}
      <div className="skeuo-card rounded-2xl p-5 md:p-6 space-y-4">
        <div className="border-b border-[var(--fb-border)] pb-4">
          <h2 className="text-base font-semibold text-[var(--fb-ink)] flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-amber-500" aria-hidden="true" />
            <span>Parolni almashtirish</span>
          </h2>
          <p className="text-xs text-[var(--fb-ink-secondary)] mt-1">
            Yangi parol o‘rnatilganda joriy qurilmadagi sessiyangiz saqlanadi, qolgan barcha qurilmalar avtomatik chiqariladi.
          </p>
        </div>

        {passwordError && (
          <div
            role="alert"
            className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/25 text-rose-700 dark:text-rose-300 text-xs flex items-start gap-2"
          >
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
            <span>{passwordError}</span>
          </div>
        )}

        {passwordNotice && (
          <div
            role="status"
            className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-700 dark:text-emerald-300 text-xs flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>{passwordNotice}</span>
          </div>
        )}

        <form onSubmit={handleChangePassword} className="space-y-3">
          <div>
            <label
              htmlFor="account-current-password"
              className="block text-[11px] font-semibold text-[var(--fb-ink-secondary)] mb-1"
            >
              Joriy parol *
            </label>
            <input
              id="account-current-password"
              type="password"
              required
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Joriy parolingiz"
              className="skeuo-input w-full rounded-xl px-3.5 py-2 text-xs"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="account-new-password"
                className="block text-[11px] font-semibold text-[var(--fb-ink-secondary)] mb-1"
              >
                Yangi parol (kamida 12 belgi) *
              </label>
              <input
                id="account-new-password"
                type="password"
                required
                minLength={12}
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Kamida 12 ta belgi"
                className="skeuo-input w-full rounded-xl px-3.5 py-2 text-xs"
              />
            </div>

            <div>
              <label
                htmlFor="account-confirm-password"
                className="block text-[11px] font-semibold text-[var(--fb-ink-secondary)] mb-1"
              >
                Yangi parolni tasdiqlash *
              </label>
              <input
                id="account-confirm-password"
                type="password"
                required
                minLength={12}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Parolni qayta kiriting"
                className="skeuo-input w-full rounded-xl px-3.5 py-2 text-xs"
              />
            </div>
          </div>

          {totpEnabled && (
            <div>
              <label
                htmlFor="account-password-totp"
                className="block text-[11px] font-semibold text-[var(--fb-ink-secondary)] mb-1"
              >
                6 xonali TOTP kodi (oxirgi 5 daqiqada MFA bilan kirmagan bo‘lsangiz)
              </label>
              <input
                id="account-password-totp"
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                placeholder="123456"
                className="skeuo-input w-full rounded-xl px-3.5 py-2 text-xs font-mono"
              />
            </div>
          )}

          <div className="flex justify-end pt-1">
            <button
              type="submit"
              disabled={passwordBusy || !currentPassword || newPassword.length < 12 || !confirmPassword}
              className="skeuo-btn-obsidian rounded-xl px-4 py-2 text-xs font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
            >
              {passwordBusy && <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />}
              <span>Parolni yangilash</span>
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
