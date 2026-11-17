"use client";

import { useId, useState } from "react";
import { AlertCircle, CheckCircle2, KeyRound, Loader2, RefreshCw } from "lucide-react";
import { useAsyncData } from "@/lib/useAsyncData";
import { decideRecoveryRequest, describeStaffError, fetchRecoveryRequests } from "@/lib/universityStaff";

const fmt = (iso: string) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleString("uz-UZ", { dateStyle: "short", timeStyle: "short" });
};

/**
 * Coordinator queue: students of this university who lost access and have no
 * authenticator or backup code. Approving vouches for their identity (checked in
 * person or by phone) and lets the same contact reset the password once within
 * 72 hours. It never reveals or sets the password itself.
 */
export default function RecoveryRequestsPanel({ institutionId }: { institutionId: string | null }) {
  const ids = useId();
  const q = useAsyncData(institutionId ? `recovery:${institutionId}` : null, () => fetchRecoveryRequests(institutionId as string));
  const [openId, setOpenId] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  if (!institutionId) return null;
  const error = actionError ?? (q.error ? describeStaffError(q.error) : null);
  const items = q.data?.items ?? [];

  const decide = async (id: string, decision: "APPROVE" | "REJECT") => {
    setBusy(true);
    setActionError(null);
    setNotice(null);
    try {
      await decideRecoveryRequest(institutionId, id, decision, reason.trim());
      setNotice(
        decision === "APPROVE"
          ? "Tasdiqlandi. Talaba 72 soat ichida «Parolni tiklash» sahifasida jarayonni qayta boshlab, yangi parol o‘rnata oladi."
          : "So‘rov rad etildi."
      );
      setOpenId(null);
      setReason("");
      await q.reload();
    } catch (err) {
      setActionError(describeStaffError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="skeuo-card rounded-[24px] p-5 sm:p-6 flex flex-col gap-4" aria-labelledby={`${ids}-title`}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 id={`${ids}-title`} className="font-heading text-lg font-bold text-[var(--fb-ink)] flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-indigo-600 dark:text-indigo-300" aria-hidden="true" />
            Parolni tiklash so‘rovlari
          </h2>
          <p className="text-sm text-[var(--fb-ink-secondary)] max-w-2xl">
            Hisobiga kira olmayotgan va ikki bosqichli himoyasi bo‘lmagan talabalaringiz. Talabani shaxsan yoki telefon orqali tekshirib, keyin
            tasdiqlang — shundan so‘ng u 72 soat ichida o‘zi yangi parol o‘rnatadi. Parolni siz ko‘rmaysiz va o‘rnatmaysiz.
          </p>
        </div>
        <button type="button" onClick={() => void q.reload()} disabled={q.isLoading} aria-label="Yangilash" className="skeuo-btn-secondary rounded-xl px-3 py-2 text-xs shrink-0">
          <RefreshCw className={`h-3.5 w-3.5 ${q.isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
        </button>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-2.5 rounded-2xl border border-rose-500/25 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {error}
        </div>
      )}
      {notice && (
        <div className="flex items-start gap-2.5 rounded-2xl border border-emerald-500/25 bg-emerald-500/10 p-3.5 text-sm text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {notice}
        </div>
      )}

      {q.isLoading && !q.data ? (
        <div className="flex items-center gap-2 text-sm text-[var(--fb-ink-secondary)]">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Yuklanmoqda…
        </div>
      ) : items.length === 0 ? (
        <p className="rounded-2xl skeuo-well p-5 text-center text-sm text-[var(--fb-ink-secondary)]">Hozircha so‘rovlar yo‘q.</p>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {items.map((item) => (
            <li key={item.id} className="rounded-2xl skeuo-well p-4 flex flex-col gap-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-semibold text-[var(--fb-ink)]">{item.student_name}</div>
                  <div className="text-xs text-[var(--fb-ink-muted)]">
                    {fmt(item.created_at)}
                    {item.contacts.length ? " · " + item.contacts.map((c) => (c.channel === "EMAIL" ? "pochta " : "tel. ") + c.masked).join(", ") : ""}
                  </div>
                </div>
                {openId !== item.id && (
                  <button
                    type="button"
                    onClick={() => {
                      setOpenId(item.id);
                      setReason("");
                    }}
                    className="skeuo-btn-secondary self-start rounded-xl px-3 py-1.5 text-xs"
                  >
                    Ko‘rib chiqish
                  </button>
                )}
              </div>
              {openId === item.id && (
                <div className="flex flex-col gap-2">
                  <label htmlFor={`${ids}-reason`} className="text-sm font-semibold text-[var(--fb-ink)]">
                    Qanday tekshirdingiz?
                  </label>
                  <input
                    id={`${ids}-reason`}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Masalan: dekanatda pasporti bilan shaxsan tekshirildi"
                    className="skeuo-input w-full rounded-xl px-3.5 py-2 text-sm"
                    autoFocus
                  />
                  <div className="flex flex-wrap gap-2">
                    <button type="button" onClick={() => setOpenId(null)} className="skeuo-btn-secondary rounded-xl px-3 py-2 text-xs">
                      Bekor
                    </button>
                    <button
                      type="button"
                      disabled={busy || reason.trim().length < 15}
                      onClick={() => void decide(item.id, "REJECT")}
                      className="skeuo-btn-secondary rounded-xl px-3 py-2 text-xs disabled:opacity-50"
                    >
                      Rad etish
                    </button>
                    <button
                      type="button"
                      disabled={busy || reason.trim().length < 15}
                      onClick={() => void decide(item.id, "APPROVE")}
                      data-tone="indigo"
                      className="skeuo-btn-tone rounded-xl px-4 py-2 text-xs disabled:opacity-50"
                    >
                      {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : null}
                      Shaxsi tasdiqlandi
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
