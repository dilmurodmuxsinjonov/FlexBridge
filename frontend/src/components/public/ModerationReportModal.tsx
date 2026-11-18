"use client";

import React, { useState } from "react";
import { AlertCircle, CheckCircle2, Flag, Loader2, X } from "lucide-react";
import { submitModerationCase, type CreateModerationCaseResult } from "@/lib/publicCatalog";
import { enumLabel } from "@/lib/labels";

const CATEGORIES = [
  "MISLEADING_TERMS",
  "UNPAID_VIOLATION",
  "SPAM_OR_SCAM",
  "HARASSMENT_OR_ABUSE",
  "OTHER_VIOLATION",
] as const;

const SEVERITIES: Array<{ value: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"; label: string }> = [
  { value: "LOW", label: "Past (aniqlik kiritish)" },
  { value: "MEDIUM", label: "O‘rta (shartlar buzilishi)" },
  { value: "HIGH", label: "Yuqori (jiddiy qoidabuzarlik)" },
  { value: "CRITICAL", label: "Juda muhim (firibgarlik / xavf)" },
];

export default function ModerationReportModal({
  isOpen,
  onClose,
  targetLabel,
  opportunityId,
  organizationId,
}: {
  isOpen: boolean;
  onClose: () => void;
  targetLabel: string;
  opportunityId?: string;
  organizationId?: string;
}) {
  const [category, setCategory] = useState<string>(CATEGORIES[0]);
  const [severity, setSeverity] = useState<"LOW" | "MEDIUM" | "HIGH" | "CRITICAL">("MEDIUM");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<CreateModerationCaseResult | null>(null);

  if (!isOpen) return null;

  const trimmedReason = reason.trim();
  const canSubmit = trimmedReason.length >= 10 && !submitting;

  const handleClose = () => {
    setError(null);
    setReceipt(null);
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (trimmedReason.length < 10) {
      setError("Kamida 10 ta belgidan iborat asosli izoh yozing.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await submitModerationCase({
        category,
        severity,
        reason: trimmedReason,
        ...(opportunityId ? { opportunity_id: opportunityId } : { organization_id: organizationId }),
      });
      setReceipt(res);
      setReason("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Murojaat yuborilmadi.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="moderation-report-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
    >
      <div className="w-full max-w-lg rounded-[28px] skeuo-card p-6 sm:p-7">
        <div className="flex items-center justify-between border-b border-[var(--fb-border)] pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl skeuo-well text-amber-600 dark:text-amber-400">
              <Flag className="h-4 w-4" aria-hidden="true" />
            </div>
            <div>
              <h2
                id="moderation-report-title"
                className="font-heading text-base font-bold text-[var(--fb-ink)]"
              >
                Moderatsiyaga shikoyat yuborish
              </h2>
              <p className="text-[11px] text-[var(--fb-ink-muted)] truncate max-w-[260px] sm:max-w-[340px]">
                {targetLabel}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Oynani yopish"
            className="flex h-8 w-8 items-center justify-center rounded-xl skeuo-btn-secondary p-0"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {receipt ? (
          <div className="py-6 text-center space-y-3">
            <CheckCircle2 className="mx-auto h-11 w-11 text-emerald-500" aria-hidden="true" />
            <h3 className="font-heading text-base font-bold text-[var(--fb-ink)]">
              Murojaatingiz qabul qilindi
            </h3>
            <p className="text-xs text-[var(--fb-ink-secondary)]">
              Moderatorlar jamoasi ushbu murojaatni ko‘rib chiqadi. Holat:{" "}
              <strong className="text-[var(--fb-ink)]">{enumLabel(receipt.status)}</strong>
            </p>
            <p className="font-mono text-[11px] text-[var(--fb-ink-muted)]">
              Ariza raqami: {receipt.id}
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={handleClose}
                className="skeuo-btn-obsidian rounded-full px-6 py-2.5 text-xs font-semibold"
              >
                Tushunarli
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="report-category"
                  className="block text-xs font-semibold text-[var(--fb-ink)]"
                >
                  Qoidabuzarlik turi
                </label>
                <select
                  id="report-category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="skeuo-input mt-1.5 w-full rounded-xl px-3 py-2.5 text-xs"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {enumLabel(c)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label
                  htmlFor="report-severity"
                  className="block text-xs font-semibold text-[var(--fb-ink)]"
                >
                  Muhimlik darajasi
                </label>
                <select
                  id="report-severity"
                  value={severity}
                  onChange={(e) =>
                    setSeverity(e.target.value as "LOW" | "MEDIUM" | "HIGH" | "CRITICAL")
                  }
                  className="skeuo-input mt-1.5 w-full rounded-xl px-3 py-2.5 text-xs"
                >
                  {SEVERITIES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label
                  htmlFor="report-reason"
                  className="block text-xs font-semibold text-[var(--fb-ink)]"
                >
                  Batafsil izoh (kamida 10 belgi)
                </label>
                <span className="font-mono text-[11px] text-[var(--fb-ink-muted)] tabular-nums">
                  {trimmedReason.length}/4000
                </span>
              </div>
              <textarea
                id="report-reason"
                rows={4}
                maxLength={4000}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Aniq dalil yoki muammoni yozing (masalan: haqiqiy ish haqi ko‘rsatilganidan farq qiladi)..."
                className="skeuo-input mt-1.5 w-full rounded-xl p-3 text-xs"
              />
            </div>

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={handleClose}
                className="skeuo-btn-secondary rounded-full px-4 py-2 text-xs font-semibold"
              >
                Bekor qilish
              </button>
              <button
                type="submit"
                disabled={!canSubmit}
                className="skeuo-btn-obsidian inline-flex items-center gap-2 rounded-full px-5 py-2 text-xs font-semibold disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Yuborilmoqda...
                  </>
                ) : (
                  <>
                    <Flag className="h-3.5 w-3.5" />
                    Moderatsiyaga yuborish
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
