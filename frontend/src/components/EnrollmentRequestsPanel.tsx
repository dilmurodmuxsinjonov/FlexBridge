"use client";

import { useState } from "react";
import { AlertCircle, CheckCircle2, FileText, GraduationCap, Loader2, RefreshCw } from "lucide-react";
import {
  claimEnrollmentRequest,
  decideEnrollmentRequest,
  fetchEnrollmentRequestDetail,
  fetchEnrollmentRequests,
  openEnrollmentEvidence,
  type EnrollmentRequestDetail,
  type EnrollmentRequestItem,
} from "@/lib/api";
import { describeRequestError } from "@/lib/errors";
import { useAsyncData } from "@/lib/useAsyncData";

type Decision = "APPROVE" | "REJECT" | "NEEDS_INFO";

const DECISIONS: Array<{ id: Decision; label: string; hint: string }> = [
  { id: "APPROVE", label: "Tasdiqlash", hint: "Talaba shu OTMda haqiqatan o‘qiydi" },
  { id: "NEEDS_INFO", label: "Qo‘shimcha hujjat so‘rash", hint: "Ma’lumot yetarli emas" },
  { id: "REJECT", label: "Rad etish", hint: "Talabalik tasdiqlanmadi" },
];

const STATUS_LABELS: Record<string, string> = {
  PENDING: "Yangi",
  IN_REVIEW: "Ko‘rib chiqilmoqda",
  NEEDS_INFO: "Hujjat kutilmoqda",
};

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("uz-UZ");
}

/**
 * Coordinator queue for confirming that applicants really study at this
 * university (until HEMIS is connected). Claim -> check evidence -> decide.
 */
export default function EnrollmentRequestsPanel({ institutionId }: { institutionId: string | null }) {
  const requests = useAsyncData(institutionId ? `enrollment-requests:${institutionId}` : null, () =>
    fetchEnrollmentRequests(institutionId ?? "")
  );
  const [selected, setSelected] = useState<EnrollmentRequestItem | null>(null);
  const [detail, setDetail] = useState<EnrollmentRequestDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [decision, setDecision] = useState<Decision>("APPROVE");
  const [reason, setReason] = useState("");

  if (!institutionId) {
    return (
      <div className="skeuo-card rounded-3xl p-6 text-sm text-[var(--fb-ink-secondary)]">
        Siz hali hech qaysi OTMga koordinator sifatida biriktirilmagansiz.
      </div>
    );
  }

  const items = requests.data ?? [];

  const open = async (item: EnrollmentRequestItem) => {
    setSelected(item);
    setDetail(null);
    setError(null);
    setSuccess(null);
    setReason("");
    setBusy(true);
    try {
      if (!item.assigned_to_me) await claimEnrollmentRequest(institutionId, item.case_id);
      setDetail(await fetchEnrollmentRequestDetail(institutionId, item.case_id));
    } catch (err: unknown) {
      setError(describeRequestError(err, "So‘rovni ochib bo‘lmadi."));
    } finally {
      setBusy(false);
    }
  };

  const viewFile = async (fileId: string) => {
    if (!selected) return;
    setError(null);
    try {
      const url = await openEnrollmentEvidence(institutionId, selected.case_id, fileId);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err: unknown) {
      setError(describeRequestError(err, "Hujjatni ochib bo‘lmadi."));
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected || !detail) return;
    if (reason.trim().length < 15) {
      setError("Izoh kamida 15 belgidan iborat bo‘lsin (masalan: qaysi ro‘yxat bilan tekshirildi).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await decideEnrollmentRequest(institutionId, selected.case_id, {
        decision,
        expected_revision: detail.case.current_revision,
        reason: reason.trim(),
      });
      setSuccess(`${selected.student_name}: ${DECISIONS.find((d) => d.id === decision)?.label.toLowerCase()} saqlandi.`);
      setSelected(null);
      setDetail(null);
      void requests.reload();
    } catch (err: unknown) {
      setError(describeRequestError(err, "Qarorni saqlab bo‘lmadi."));
    } finally {
      setBusy(false);
    }
  };

  const current = detail?.submissions.find((s) => s.revision === detail.case.current_revision);

  return (
    <section className="flex flex-col gap-4">
      <div className="skeuo-card rounded-3xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="font-heading text-lg font-bold text-[var(--fb-ink)] flex items-center gap-2">
            <GraduationCap className="w-5 h-5" aria-hidden="true" /> Talabalikni tasdiqlash
          </h2>
          <p className="text-xs text-[var(--fb-ink-secondary)] mt-1 max-w-2xl">
            Talabalar o‘zini shu OTM talabasi deb ko‘rsatgan. Talabalar ro‘yxatingiz (yoki HEMIS) bilan solishtiring va
            qaror qabul qiling. HEMIS ulanganidan keyin bu jarayon avtomatlashadi.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void requests.reload()}
          disabled={requests.isLoading}
          className="px-4 py-2 rounded-full skeuo-btn-secondary text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50 shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${requests.isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
          Yangilash
        </button>
      </div>

      {success && (
        <div role="status" className="p-3 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 text-xs text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" /> {success}
        </div>
      )}
      {(error || requests.error) && (
        <div role="alert" className="p-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 text-xs text-rose-800 dark:text-rose-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
          {error ?? describeRequestError(requests.error, "So‘rovlarni yuklab bo‘lmadi.")}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <div className="skeuo-card rounded-3xl p-3 flex flex-col gap-2">
          {requests.isLoading && items.length === 0 ? (
            <p className="p-4 text-xs text-[var(--fb-ink-secondary)] flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> Yuklanmoqda…
            </p>
          ) : items.length === 0 ? (
            <p className="p-4 text-xs text-[var(--fb-ink-secondary)]">Hozircha tasdiqlanishi kerak bo‘lgan so‘rov yo‘q.</p>
          ) : (
            items.map((item) => (
              <button
                key={item.case_id}
                type="button"
                disabled={item.claimed_by_other || busy}
                onClick={() => void open(item)}
                aria-pressed={selected?.case_id === item.case_id}
                className={`text-left rounded-2xl p-3 border transition-colors disabled:opacity-60 ${
                  selected?.case_id === item.case_id
                    ? "border-[var(--fb-accent)] bg-[var(--fb-well)]"
                    : "border-[var(--fb-hairline)] hover:border-[var(--fb-accent)]/50"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-[var(--fb-ink)] truncate">{item.student_name}</span>
                  <span className="text-[11px] text-[var(--fb-ink-secondary)] shrink-0">
                    {item.claimed_by_other ? "Boshqa xodimda" : STATUS_LABELS[item.status] ?? item.status}
                  </span>
                </div>
                <div className="text-xs text-[var(--fb-ink-secondary)] mt-0.5 truncate">{item.program}</div>
                <div className="text-[11px] text-[var(--fb-ink-muted)] mt-0.5">
                  O‘qish boshlangan: {formatDate(item.start_date)} · Yuborilgan: {formatDate(item.submitted_at)}
                </div>
              </button>
            ))
          )}
        </div>

        <div className="skeuo-card rounded-3xl p-5">
          {!selected ? (
            <p className="text-xs text-[var(--fb-ink-secondary)]">Chapdagi ro‘yxatdan talabani tanlang.</p>
          ) : busy && !detail ? (
            <p className="text-xs text-[var(--fb-ink-secondary)] flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> Ochilmoqda…
            </p>
          ) : detail && current ? (
            <form onSubmit={submit} className="flex flex-col gap-4">
              <div>
                <h3 className="font-heading text-base font-bold text-[var(--fb-ink)]">{selected.student_name}</h3>
                <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <dt className="text-[var(--fb-ink-muted)]">Yo‘nalish</dt>
                  <dd className="text-[var(--fb-ink)]">{current.program}</dd>
                  <dt className="text-[var(--fb-ink-muted)]">O‘qish davri</dt>
                  <dd className="text-[var(--fb-ink)]">
                    {formatDate(current.start_date)} — {current.end_date ? formatDate(current.end_date) : "hozirgacha"}
                  </dd>
                </dl>
                {current.evidence_note && (
                  <p className="mt-2 text-xs text-[var(--fb-ink-secondary)] whitespace-pre-line">{current.evidence_note}</p>
                )}
              </div>

              <div className="flex flex-wrap gap-2">
                {current.files.map((f, i) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => void viewFile(f.id)}
                    className="px-3 py-1.5 rounded-full skeuo-btn-secondary text-xs font-semibold flex items-center gap-1.5"
                  >
                    <FileText className="w-3.5 h-3.5" aria-hidden="true" /> Hujjat {i + 1} ({Math.ceil(f.byte_size / 1024)} KB)
                  </button>
                ))}
              </div>

              <fieldset className="flex flex-col gap-2">
                <legend className="text-xs font-semibold text-[var(--fb-ink)] mb-1">Qaror</legend>
                {DECISIONS.map((d) => (
                  <label key={d.id} className="flex items-start gap-2 text-xs cursor-pointer">
                    <input
                      type="radio"
                      name="enrollment-decision"
                      value={d.id}
                      checked={decision === d.id}
                      onChange={() => setDecision(d.id)}
                      className="mt-0.5"
                    />
                    <span>
                      <span className="font-semibold text-[var(--fb-ink)]">{d.label}</span>
                      <span className="text-[var(--fb-ink-muted)]"> — {d.hint}</span>
                    </span>
                  </label>
                ))}
              </fieldset>

              <div className="flex flex-col gap-1">
                <label htmlFor="enrollment-reason" className="text-xs font-semibold text-[var(--fb-ink)]">
                  Izoh (talaba ko‘radi)
                </label>
                <textarea
                  id="enrollment-reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  rows={3}
                  placeholder="Masalan: Dekanat ro‘yxati bilan solishtirildi, 3-kurs talabasi."
                  className="px-3 py-2 rounded-2xl skeuo-input text-sm"
                />
              </div>

              <button
                type="submit"
                disabled={busy}
                className="self-start px-5 py-2.5 rounded-full skeuo-btn-obsidian text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
              >
                {busy && <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />}
                Qarorni saqlash
              </button>
            </form>
          ) : null}
        </div>
      </div>
    </section>
  );
}
