"use client";

import React, { useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Lock,
  RefreshCw,
  Sliders,
  ToggleLeft,
  ToggleRight,
  X,
} from "lucide-react";
import { enumLabel } from "@/lib/labels";
import { fetchFeatureFlags, patchFeatureFlag, type FeatureFlagItem } from "@/lib/platformAdmin";
import { isSuperAdmin } from "@/lib/roles";
import { useAsyncData } from "@/lib/useAsyncData";

const subscribeNoop = () => () => {};

function categoryBadge(cat: FeatureFlagItem["category"]): { label: string; tone: string } {
  if (cat === "R1") {
    return {
      label: "R1 boshqariladigan",
      tone: "bg-[color-mix(in_srgb,#10b981_14%,transparent)] text-emerald-700 dark:text-emerald-300",
    };
  }
  if (cat === "PROTECTED") {
    return {
      label: "Himoyalangan (R1 qulfi)",
      tone: "bg-[color-mix(in_srgb,#f59e0b_16%,transparent)] text-amber-800 dark:text-amber-300",
    };
  }
  return {
    label: "R2 (keyingi bosqich)",
    tone: "bg-[color-mix(in_srgb,var(--fb-ink)_10%,transparent)] text-[var(--fb-ink-secondary)]",
  };
}

export default function FeatureFlagsPanel({ roles }: { roles: string[] }) {
  const canToggle = isSuperAdmin(roles);
  const mounted = useSyncExternalStore(subscribeNoop, () => true, () => false);
  const flagsQuery = useAsyncData("operator-feature-flags", fetchFeatureFlags);

  const [pendingFlag, setPendingFlag] = useState<{ flag: FeatureFlagItem; nextEnabled: boolean } | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const items = flagsQuery.data ?? [];

  async function handleConfirm(e: React.FormEvent) {
    e.preventDefault();
    if (!pendingFlag) return;
    const trimmed = reason.trim();
    if (trimmed.length < 15) {
      setSubmitError("O‘zgartirish sababi kamida 15 belgidan iborat bo‘lishi kerak.");
      return;
    }
    setBusy(true);
    setSubmitError(null);
    try {
      const res = await patchFeatureFlag(pendingFlag.flag.code, {
        enabled: pendingFlag.nextEnabled,
        reason: trimmed,
        expectedVersion: pendingFlag.flag.version,
      });
      setNotice(
        `«${enumLabel(pendingFlag.flag.code)}» ${res.enabled ? "yoqildi" : "o‘chirildi"} (versiya ${res.version}).`
      );
      setPendingFlag(null);
      setReason("");
      await flagsQuery.reload();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Flag holatini saqlab bo‘lmadi.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="fb-panel skeuo-card flex flex-col gap-5 p-5 sm:p-6" aria-labelledby="flags-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="flags-title" className="text-lg font-semibold text-[var(--fb-ink)]">
            Global funksional flaglar
          </h2>
          <p className="text-xs text-[var(--fb-ink-muted)]">
            R1 modullarini boshqarish. Himoyalangan va R2 funksiyalar tizim xavfsizligi uchun qulflangan.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void flagsQuery.reload()}
          className="fb-icon-btn fb-icon-btn-light h-9 w-9"
          aria-label="Flaglar ro‘yxatini yangilash"
        >
          <RefreshCw className={`h-4 w-4 ${flagsQuery.isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* SAFETY POLICY BANNER */}
      <div
        data-skeuo-dark="true"
        className="fb-ink-card rounded-[22px] p-4 flex flex-wrap items-center justify-between gap-3 text-xs"
      >
        <div className="flex items-start gap-3">
          <span className="fb-avatar h-9 w-9 shrink-0" aria-hidden="true">
            <Sliders className="h-4 w-4" />
          </span>
          <div>
            <p className="font-semibold">
              Himoyalangan va R2 flaglar avtomatik yoqilmaydi
            </p>
            <p className="mt-0.5 fb-muted">
              {canToggle
                ? "Har bir o‘zgarish versiya nazorati va kamida 15 belgili sabab bilan audit jurnaliga muhrlanadi."
                : "Sizning rolingiz faqat holatni ko‘ra oladi. O‘zgartirish faqat Bosh administrator (2FA) uchun ochiq."}
            </p>
          </div>
        </div>
      </div>

      {notice && (
        <p
          role="status"
          className="flex items-center gap-2 rounded-2xl bg-[color-mix(in_srgb,#10b981_14%,transparent)] px-4 py-3 text-xs font-medium text-emerald-700 dark:text-emerald-300"
        >
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{notice}</span>
        </p>
      )}
      {flagsQuery.error && (
        <p
          role="alert"
          className="flex items-center gap-2 rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-4 py-3 text-xs font-medium text-rose-700 dark:text-rose-300"
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{flagsQuery.error.message}</span>
        </p>
      )}

      {flagsQuery.isLoading && !flagsQuery.data ? (
        <p className="flex items-center justify-center gap-2 py-12 text-xs text-[var(--fb-ink-muted)]">
          <Loader2 className="h-4 w-4 animate-spin" /> Yuklanmoqda…
        </p>
      ) : items.length === 0 ? (
        <div className="rounded-[22px] skeuo-well px-6 py-10 text-center text-xs text-[var(--fb-ink-secondary)]">
          Funksional flaglar ro‘yxati bo‘sh.
        </div>
      ) : (
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {items.map((flag) => {
            const badge = categoryBadge(flag.category);
            const isAlias = Boolean(flag.alias_of);
            const canDisableOnly = flag.disable_only && flag.enabled && !isAlias;
            const canEditThis = canToggle && !isAlias && (flag.mutable || canDisableOnly);
            const nextEnabled = !flag.enabled;
            const blockedReason = !canToggle
              ? "Faqat Bosh administrator o‘zgartiradi"
              : isAlias
              ? "Asosiy flag taxallusi — faqat o‘qish"
              : !flag.mutable && !flag.enabled
              ? "Xavfsizlik qulflangan (R1 doirasida yoqib bo‘lmaydi)"
              : null;

            return (
              <li key={flag.code} className="rounded-[22px] skeuo-well p-4 flex flex-col justify-between gap-3">
                <div className="flex flex-col gap-2">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-[var(--fb-ink)]">
                        {enumLabel(flag.code)}
                      </h3>
                      <p className="mt-0.5 text-[11px] text-[var(--fb-ink-muted)]">
                        Versiya {flag.version}
                        {flag.alias_of ? ` · Bog‘langan: ${enumLabel(flag.alias_of)}` : ""}
                      </p>
                    </div>
                    <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${badge.tone}`}>
                      {badge.label}
                    </span>
                  </div>

                  {flag.reason && (
                    <p className="text-xs leading-relaxed text-[var(--fb-ink-secondary)]">{flag.reason}</p>
                  )}
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[color-mix(in_srgb,var(--fb-ink)_10%,transparent)] pt-3">
                  <span
                    className={`inline-flex items-center gap-1.5 text-xs font-semibold ${
                      flag.enabled
                        ? "text-emerald-700 dark:text-emerald-300"
                        : "text-[var(--fb-ink-muted)]"
                    }`}
                  >
                    {flag.enabled ? (
                      <>
                        <ToggleRight className="h-4 w-4" /> Yoqilgan
                      </>
                    ) : (
                      <>
                        <ToggleLeft className="h-4 w-4" /> O‘chirilgan
                      </>
                    )}
                  </span>

                  {canEditThis ? (
                    <button
                      type="button"
                      onClick={() => {
                        setPendingFlag({ flag, nextEnabled });
                        setReason("");
                        setSubmitError(null);
                      }}
                      className="skeuo-btn-obsidian rounded-full px-3.5 py-1.5 text-xs font-semibold"
                    >
                      {nextEnabled ? "Yoqish" : "O‘chirish"}
                    </button>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[11px] text-[var(--fb-ink-muted)]">
                      <Lock className="h-3 w-3 shrink-0" />
                      <span>{blockedReason || "Qulflangan"}</span>
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* CONFIRMATION MODAL */}
      {mounted &&
        pendingFlag &&
        createPortal(
          <div
            className="fixed inset-0 z-[90] flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-4"
            onMouseDown={(e) => e.target === e.currentTarget && setPendingFlag(null)}
          >
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="flag-modal-title"
              className="skeuo-card w-full max-w-md rounded-t-[28px] sm:rounded-[28px] p-6 flex flex-col gap-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 id="flag-modal-title" className="text-base font-semibold text-[var(--fb-ink)]">
                    {enumLabel(pendingFlag.flag.code)}ni {pendingFlag.nextEnabled ? "yoqish" : "o‘chirish"}
                  </h2>
                  <p className="mt-0.5 text-xs text-[var(--fb-ink-muted)]">
                    Joriy versiya: {pendingFlag.flag.version} · Holat:{" "}
                    {pendingFlag.flag.enabled ? "Yoqilgan" : "O‘chirilgan"} →{" "}
                    {pendingFlag.nextEnabled ? "Yoqilgan" : "O‘chirilgan"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setPendingFlag(null)}
                  className="fb-icon-btn fb-icon-btn-light h-8 w-8"
                  aria-label="Oynani yopish"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {submitError && (
                <p
                  role="alert"
                  className="rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-3.5 py-2.5 text-xs text-rose-700 dark:text-rose-300"
                >
                  {submitError}
                </p>
              )}

              <form onSubmit={handleConfirm} className="flex flex-col gap-3">
                <label className="flex flex-col gap-1 text-xs font-medium text-[var(--fb-ink-secondary)]">
                  O‘zgartirish asosi (audit uchun, kamida 15 belgi)
                  <textarea
                    rows={3}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Masalan: Pilot OTM bilan yarim stavka e’lonlari sinovi boshlandi"
                    className="skeuo-input resize-none rounded-xl px-3 py-2 text-xs"
                  />
                </label>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setPendingFlag(null)}
                    className="skeuo-btn-secondary rounded-full px-4 py-2 text-xs"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="submit"
                    disabled={busy || reason.trim().length < 15}
                    className="skeuo-btn-obsidian rounded-full px-4 py-2 text-xs font-semibold disabled:opacity-50"
                  >
                    {busy ? "Saqlanmoqda…" : "Tasdiqlash"}
                  </button>
                </div>
              </form>
            </div>
          </div>,
          document.body
        )}
    </section>
  );
}
