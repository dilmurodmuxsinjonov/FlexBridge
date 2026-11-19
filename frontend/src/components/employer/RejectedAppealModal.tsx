"use client";

import React, { useState } from "react";
import { AlertCircle, CheckCircle2, Gavel, Loader2, X } from "lucide-react";
import { submitModerationAppeal } from "@/lib/placementLifecycle";

export default function RejectedAppealModal({
  isOpen,
  opportunityTitle,
  actionId,
  onClose,
  onSubmitted,
}: {
  isOpen: boolean;
  opportunityTitle: string;
  actionId: string | null;
  onClose: () => void;
  onSubmitted: () => void;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [doneCaseId, setDoneCaseId] = useState<string | null>(null);

  if (!isOpen || !actionId) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (reason.trim().length < 15) {
      setError("Apellyatsiya asosi kamida 15 ta belgidan iborat bo‘lishi shart.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await submitModerationAppeal(actionId, reason);
      setDoneCaseId(res.case_id);
      onSubmitted();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Apellyatsiyani yuborishda xatolik yuz berdi.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0d1117] text-white shadow-2xl p-6 space-y-4 text-xs">
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <h3 className="text-sm font-bold flex items-center gap-2">
            <Gavel className="w-4 h-4 text-amber-400" />
            <span>Rad qaroriga apellyatsiya (`API-111`)</span>
          </h3>
          <button type="button" onClick={onClose} aria-label="Yopish" className="text-zinc-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-zinc-300">
          Vakansiya: <strong className="text-white">{opportunityTitle}</strong>
        </p>

        {error && (
          <div role="alert" className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/25 text-rose-300 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {doneCaseId ? (
          <div className="space-y-3">
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <span>Apellyatsiya yuborildi (#{doneCaseId.slice(0, 8)}). Mustaqil moderator ko‘rib chiqadi.</span>
            </div>
            <div className="flex justify-end">
              <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg bg-white/10 text-white font-semibold">
                Yopish
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <label className="flex flex-col gap-1">
              <span className="text-zinc-300 font-semibold">Apellyatsiya sababi (kamida 15 belgi) *</span>
              <textarea
                rows={4}
                required
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Rad etilgan qaror bo‘yicha qo‘shimcha dalil va asoslarni yozing..."
                className="px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-white"
              />
            </label>
            <p className="text-[11px] text-zinc-400">
              Eslatma: apellyatsiya topshirish uchun hisobda ikki bosqichli himoya (2FA) yoqilgan bo‘lishi talab qilinadi.
            </p>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={onClose} className="px-3 py-2 rounded-lg bg-white/[0.06] text-zinc-300">
                Bekor qilish
              </button>
              <button
                type="submit"
                disabled={busy || reason.trim().length < 15}
                className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
              >
                {busy && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Apellyatsiyani yuborish</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
