"use client";

import React, { useState } from "react";
import { Briefcase, CheckCircle2, Loader2, RefreshCw, XCircle } from "lucide-react";
import { APPROVE_REASONS, decideVacancy, fetchModerationQueue, REJECT_REASONS, type ModerationVacancy } from "@/lib/moderation";
import { enumLabel } from "@/lib/labels";
import { useAsyncData } from "@/lib/useAsyncData";

function pay(v: ModerationVacancy): string {
  if (!v.is_paid) return "To‘lovsiz";
  if (v.salary_min == null) return "To‘lov ko‘rsatilmagan";
  const per = v.salary_period === "HOUR" ? "/ soat" : v.salary_period === "MONTH" ? "/ oy" : "";
  return `${v.salary_min.toLocaleString("uz-UZ")}${v.salary_max ? `–${v.salary_max.toLocaleString("uz-UZ")}` : ""} ${v.currency || "UZS"} ${per}`.trim();
}

function Decision({ v, onDone }: { v: ModerationVacancy; onDone: (msg: string) => void }) {
  const [action, setAction] = useState<"APPROVE" | "REJECT" | null>(null);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reasons = action === "REJECT" ? REJECT_REASONS : APPROVE_REASONS;

  if (v.own) return <p className="text-xs text-[var(--fb-ink-muted)]">Bu e’lonni siz yozgansiz — boshqa moderator ko‘rib chiqadi.</p>;
  if (!action) {
    return (
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => { setAction("APPROVE"); setReason(APPROVE_REASONS[0].code); }} className="inline-flex items-center gap-1.5 rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold">
          <CheckCircle2 className="h-3.5 w-3.5" /> Tasdiqlash
        </button>
        <button type="button" onClick={() => { setAction("REJECT"); setReason(REJECT_REASONS[0].code); }} className="inline-flex items-center gap-1.5 rounded-full skeuo-btn-secondary px-4 py-2 text-xs font-semibold">
          <XCircle className="h-3.5 w-3.5" /> Rad etish
        </button>
      </div>
    );
  }
  return (
    <form
      className="flex flex-col gap-2 rounded-2xl skeuo-well p-3"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError(null);
        try {
          await decideVacancy(v.id, action, reason, note.trim());
          onDone(action === "APPROVE" ? `«${v.title}» tasdiqlandi — korxona endi uni e’lon qila oladi.` : `«${v.title}» rad etildi.`);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Xatolik");
        } finally {
          setBusy(false);
        }
      }}
    >
      <label className="flex flex-col gap-1 text-xs font-medium text-[var(--fb-ink-secondary)]">
        Sabab
        <select value={reason} onChange={(e) => setReason(e.target.value)} className="skeuo-input rounded-xl px-3 py-2 text-xs">
          {reasons.map((r) => <option key={r.code} value={r.code}>{r.label}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium text-[var(--fb-ink-secondary)]">
        Izoh (audit jurnaliga yoziladi, kamida 15 belgi)
        <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} className="skeuo-input resize-none rounded-xl px-3 py-2 text-xs" placeholder={action === "APPROVE" ? "Masalan: matn, to‘lov va shartnoma turi tekshirildi" : "Masalan: to‘lov miqdori ko‘rsatilmagan, aniqlashtirilsin"} />
      </label>
      {error && <p role="alert" className="text-xs text-rose-700 dark:text-rose-300">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={busy || note.trim().length < 15} className="rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold disabled:opacity-50">
          {busy ? "Yuborilmoqda…" : action === "APPROVE" ? "Tasdiqlashni yuborish" : "Rad etishni yuborish"}
        </button>
        <button type="button" onClick={() => setAction(null)} className="rounded-full px-3 py-2 text-xs font-semibold text-[var(--fb-ink-secondary)]">Bekor qilish</button>
      </div>
    </form>
  );
}

/** Vacancy moderation queue: a draft becomes publishable only after a moderator approves it. */
export default function ModerationPanel({ onCountChange }: { onCountChange?: (n: number) => void }) {
  const queue = useAsyncData("operator-moderation-queue", fetchModerationQueue);
  const [notice, setNotice] = useState<string | null>(null);
  const items = queue.data ?? [];
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="mod-title">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 id="mod-title" className="text-lg font-semibold text-[var(--fb-ink)]">E’lonlar moderatsiyasi</h2>
          <p className="text-xs text-[var(--fb-ink-muted)]">Korxona yaratgan e’lon tasdiqlanmaguncha katalogga chiqmaydi. Eng eskisi yuqorida.</p>
        </div>
        <button type="button" onClick={() => void queue.reload()} className="fb-icon-btn fb-icon-btn-light" aria-label="Ro‘yxatni yangilash">
          <RefreshCw className={`h-4 w-4 ${queue.isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>
      {notice && <p role="status" className="rounded-2xl bg-emerald-500/10 px-4 py-3 text-xs text-emerald-700 dark:text-emerald-300">{notice}</p>}
      {queue.error && <p role="alert" className="rounded-2xl bg-rose-500/10 px-4 py-3 text-xs text-rose-700 dark:text-rose-300">{queue.error.message}</p>}
      {queue.isLoading && !queue.data ? (
        <p className="flex items-center justify-center gap-2 py-12 text-xs text-[var(--fb-ink-muted)]"><Loader2 className="h-4 w-4 animate-spin" /> Yuklanmoqda…</p>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-[22px] skeuo-well px-6 py-12 text-center">
          <CheckCircle2 className="h-7 w-7 text-[var(--fb-ink)]" />
          <p className="text-sm font-semibold text-[var(--fb-ink)]">Moderatsiya kutayotgan e’lon yo‘q</p>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {items.map((v) => (
            <li key={v.id} className="rounded-[22px] skeuo-well p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <span className="fb-avatar h-10 w-10 shrink-0" aria-hidden="true"><Briefcase className="h-4 w-4" /></span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[var(--fb-ink)]">{v.title}</p>
                    <p className="text-xs text-[var(--fb-ink-muted)]">
                      {v.organization_name}
                      {v.organization_status !== "VERIFIED" ? " · korxona hali tasdiqlanmagan" : ""}
                    </p>
                  </div>
                </div>
                <span className="text-[11px] text-[var(--fb-ink-muted)] tabular-nums">{v.created_at ? new Date(v.created_at).toLocaleString("uz-UZ") : ""}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]">
                {[enumLabel(v.kind), v.contract_type && enumLabel(v.contract_type), v.work_mode && enumLabel(v.work_mode), v.region, pay(v), `${v.capacity} o‘rin`]
                  .filter(Boolean)
                  .map((t) => <span key={String(t)} className="fb-capsule px-2.5 py-0.5 font-medium">{t}</span>)}
              </div>
              {v.description && v.description !== v.title && <p className="mt-3 line-clamp-3 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">{v.description}</p>}
              <div className="mt-3">
                <Decision
                  v={v}
                  onDone={(msg) => {
                    setNotice(msg);
                    void queue.reload().then(() => onCountChange?.(Math.max(0, items.length - 1)));
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
