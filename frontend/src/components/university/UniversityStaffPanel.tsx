"use client";

import { useId, useState } from "react";
import { useAsyncData } from "@/lib/useAsyncData";
import { AlertCircle, CheckCircle2, FileText, Loader2, Plus, RefreshCw, ShieldCheck, UserMinus, Users, X } from "lucide-react";
import {
  STATUS_LABELS,
  describeStaffError,
  fetchMyVerifiedContacts,
  fetchStaff,
  newIdempotencyKey,
  revokeAppointment,
  submitAppointment,
  uploadStaffPdf,
  type StaffAppointment,
  type StaffOverview,
  type VerifiedContact,
} from "@/lib/universityStaff";

const today = () => new Date().toISOString().slice(0, 10);
const fmt = (d?: string | null) => (d ? d.slice(0, 10).split("-").reverse().join(".") : "");

function StatusBadge({ item }: { item: StaffAppointment }) {
  const tone = item.role_active
    ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300 border-emerald-500/25"
    : item.status === "REVOKED" || item.status === "REJECTED"
      ? "bg-zinc-500/10 text-[var(--fb-ink-secondary)] border-zinc-500/20"
      : "bg-amber-500/12 text-amber-800 dark:text-amber-300 border-amber-500/25";
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${tone}`}>
      {item.role_active ? "Faol" : STATUS_LABELS[item.status] ?? item.status}
    </span>
  );
}

/**
 * The university account's staff administration: list every appointment of the
 * institution, add a teacher by their FlexBridge phone/e-mail with the signed
 * appointment order, and revoke access. Each request is reviewed by a platform
 * moderator and accepted by the named person before the role exists.
 */
export default function UniversityStaffPanel({ institutionId }: { institutionId: string | null }) {
  const ids = useId();
  const staff = useAsyncData<{ overview: StaffOverview; contacts: VerifiedContact[] }>(
    institutionId ? `staff:${institutionId}` : null,
    async () => {
      const [overview, contacts] = await Promise.all([fetchStaff(institutionId as string), fetchMyVerifiedContacts().catch(() => [])]);
      return { overview, contacts };
    }
  );
  const data = staff.data?.overview ?? null;
  const contacts = staff.data?.contacts ?? [];
  const loading = staff.isLoading;
  const [actionError, setError] = useState<string | null>(null);
  const error = actionError ?? (staff.error ? describeStaffError(staff.error) : null);
  const [notice, setNotice] = useState<string | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [target, setTarget] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [validFrom, setValidFrom] = useState(today());
  const [validTo, setValidTo] = useState("");
  const [legalBasis, setLegalBasis] = useState("");
  const [note, setNote] = useState("");
  const [chosenContact, setContactId] = useState("");
  const contactId = chosenContact || contacts.find((c) => c.is_primary)?.id || contacts[0]?.id || "";
  const [submitting, setSubmitting] = useState(false);

  const [revokeId, setRevokeId] = useState<string | null>(null);
  const [revokeReason, setRevokeReason] = useState("");
  const [revoking, setRevoking] = useState(false);

  const load = async () => {
    setError(null);
    await staff.reload();
  };

  const resetForm = () => {
    setTarget("");
    setFile(null);
    setValidFrom(today());
    setValidTo("");
    setLegalBasis("");
    setNote("");
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data?.agreement || !institutionId || !file) return;
    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      const doc = await uploadStaffPdf(file, "INSTITUTION_APPOINTMENT");
      const destination = target.trim();
      const isEmail = destination.includes("@");
      let phone = destination.replace(/[\s()-]/g, "");
      if (/^[0-9]{9}$/.test(phone)) phone = "+998" + phone;
      else if (/^998[0-9]{9}$/.test(phone)) phone = "+" + phone;
      await submitAppointment(
        {
          registry_code: data.institution.registry_code,
          agreement_id: data.agreement.id,
          document_file_id: doc.file_id,
          file_ids: [doc.file_id],
          contact_id: contactId,
          valid_from: validFrom,
          valid_to: validTo || null,
          legal_basis: legalBasis.trim(),
          evidence_note: note.trim(),
          target_channel: isEmail ? "EMAIL" : "PHONE",
          target_destination: isEmail ? destination : phone,
        },
        newIdempotencyKey("staff")
      );
      setNotice("So‘rov yuborildi. Platforma uni tekshiradi, so‘ng xodim o‘z hisobida tayinlovni tasdiqlaydi — shundan keyin u faol bo‘ladi.");
      resetForm();
      setFormOpen(false);
      await load();
    } catch (err) {
      setError(describeStaffError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const confirmRevoke = async () => {
    if (!revokeId || !institutionId) return;
    setRevoking(true);
    setError(null);
    try {
      await revokeAppointment(revokeId, revokeReason.trim());
      setNotice("Xodimning universitetdagi ruxsati bekor qilindi.");
      setRevokeId(null);
      setRevokeReason("");
      await load();
    } catch (err) {
      setError(describeStaffError(err));
    } finally {
      setRevoking(false);
    }
  };

  if (!institutionId) {
    return (
      <section className="skeuo-card rounded-[24px] p-6 text-sm text-[var(--fb-ink-secondary)]">
        Universitetingiz hali ulanmagan yoki siz uning koordinatori emassiz.
      </section>
    );
  }

  const canSubmit =
    Boolean(file) && target.trim().length >= 5 && legalBasis.trim().length >= 15 && note.trim().length >= 15 && Boolean(contactId) && !submitting;

  return (
    <section className="skeuo-card rounded-[24px] p-5 sm:p-6 flex flex-col gap-5" aria-labelledby={`${ids}-title`}>
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 id={`${ids}-title`} className="font-heading text-lg font-bold text-[var(--fb-ink)] flex items-center gap-2">
            <Users className="h-5 w-5 text-indigo-600 dark:text-indigo-300" aria-hidden="true" />
            Xodimlar
          </h2>
          <p className="text-sm text-[var(--fb-ink-secondary)] max-w-2xl">
            Kafedra o‘qituvchilari va amaliyot rahbarlarini qo‘shing. Har bir tayinlov FlexBridge tomonidan tekshiriladi va xodim o‘zi rozilik
            bergandan keyin faollashadi.
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button type="button" onClick={() => void load()} disabled={loading} className="skeuo-btn-secondary rounded-xl px-3 py-2 text-xs" aria-label="Yangilash">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() => setFormOpen((v) => !v)}
            disabled={!data?.agreement}
            aria-expanded={formOpen}
            data-tone="indigo"
            className="skeuo-btn-tone rounded-xl px-4 py-2 text-xs disabled:opacity-50"
          >
            {formOpen ? <X className="h-3.5 w-3.5" aria-hidden="true" /> : <Plus className="h-3.5 w-3.5" aria-hidden="true" />}
            {formOpen ? "Yopish" : "Xodim qo‘shish"}
          </button>
        </div>
      </div>

      <ol className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        {["1. Siz so‘rov yuborasiz", "2. Platforma tekshiradi", "3. Xodim rozilik beradi", "4. Ruxsat faollashadi"].map((s) => (
          <li key={s} className="rounded-xl skeuo-well px-3 py-2 text-[var(--fb-ink-secondary)]">
            {s}
          </li>
        ))}
      </ol>

      {data && !data.agreement && (
        <div className="flex items-start gap-2.5 rounded-2xl border border-amber-500/25 bg-amber-500/10 p-3.5 text-sm text-amber-800 dark:text-amber-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Universitetning amaldagi shartnomasi topilmadi — u tasdiqlanmaguncha yangi xodim qo‘shib bo‘lmaydi.
        </div>
      )}
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

      {formOpen && data?.agreement && (
        <form onSubmit={submit} className="rounded-2xl skeuo-well p-4 sm:p-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label htmlFor={`${ids}-target`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
              Xodimning telefon raqami yoki pochtasi
            </label>
            <input
              id={`${ids}-target`}
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="+998 90 123 45 67 yoki xodim@otm.uz"
              autoComplete="off"
              className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm"
              required
            />
            <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">Xodim avval FlexBridge’da ro‘yxatdan o‘tgan va shu kontaktni tasdiqlagan bo‘lishi kerak.</p>
          </div>
          <div className="sm:col-span-2">
            <label htmlFor={`${ids}-file`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
              Tayinlov hujjati (PDF)
            </label>
            <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-[var(--fb-hairline)] px-3.5 py-3 text-sm text-[var(--fb-ink-secondary)] hover:border-indigo-400">
              <FileText className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="min-w-0 truncate">{file ? file.name : "Buyruq yoki ishonchnoma PDF faylini tanlang (10 MB gacha)"}</span>
              <input
                id={`${ids}-file`}
                type="file"
                accept="application/pdf,.pdf"
                className="sr-only"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>
          <div>
            <label htmlFor={`${ids}-from`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
              Boshlanish sanasi
            </label>
            <input id={`${ids}-from`} type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm" required />
          </div>
          <div>
            <label htmlFor={`${ids}-to`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
              Tugash sanasi <span className="font-normal text-[var(--fb-ink-muted)]">(ixtiyoriy)</span>
            </label>
            <input id={`${ids}-to`} type="date" value={validTo} min={validFrom} onChange={(e) => setValidTo(e.target.value)} className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm" />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor={`${ids}-basis`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
              Huquqiy asos
            </label>
            <input
              id={`${ids}-basis`}
              value={legalBasis}
              onChange={(e) => setLegalBasis(e.target.value)}
              placeholder="Masalan: Rektorning 2026-yil 1-sentabrdagi 245-son buyrug‘i"
              className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm"
              required
              minLength={15}
            />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor={`${ids}-note`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
              Tekshiruvchi uchun izoh
            </label>
            <textarea
              id={`${ids}-note`}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              placeholder="Masalan: Dasturiy injiniring kafedrasi o‘qituvchisi, talabalarning amaliyotiga rahbarlik qiladi"
              className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm"
              required
              minLength={15}
            />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor={`${ids}-contact`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
              Siz bilan bog‘lanish uchun kontakt
            </label>
            {contacts.length ? (
              <select id={`${ids}-contact`} value={contactId} onChange={(e) => setContactId(e.target.value)} className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm">
                {contacts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.channel === "EMAIL" ? "Pochta" : "Telefon"}: {c.masked_destination}
                  </option>
                ))}
              </select>
            ) : (
              <p className="text-xs text-amber-800 dark:text-amber-300">Hisobingizda tasdiqlangan kontakt yo‘q.</p>
            )}
          </div>
          <div className="sm:col-span-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <p className="flex items-center gap-1.5 text-xs text-[var(--fb-ink-muted)]">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
              Yuborish uchun ikki bosqichli himoya bilan kirgan bo‘lishingiz kerak.
            </p>
            <button type="submit" disabled={!canSubmit} data-tone="indigo" className="skeuo-btn-tone rounded-xl px-5 py-2.5 text-sm disabled:opacity-50">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              {submitting ? "Yuborilmoqda…" : "So‘rov yuborish"}
            </button>
          </div>
        </form>
      )}

      {loading && !data ? (
        <div className="flex items-center gap-2 text-sm text-[var(--fb-ink-secondary)]">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Yuklanmoqda…
        </div>
      ) : data && data.items.length === 0 ? (
        <p className="rounded-2xl skeuo-well p-6 text-center text-sm text-[var(--fb-ink-secondary)]">Hozircha xodimlar yo‘q.</p>
      ) : data ? (
        <ul className="flex flex-col gap-2.5">
          {data.items.map((item) => (
            <li key={item.id} className="rounded-2xl skeuo-well p-4 flex flex-col gap-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-[var(--fb-ink)]">{item.display_name}</span>
                    {item.is_self && <span className="text-xs text-[var(--fb-ink-muted)]">(siz)</span>}
                    <span className="rounded-full border border-indigo-500/25 bg-indigo-500/10 px-2 py-0.5 text-xs font-semibold text-indigo-700 dark:text-indigo-300">
                      {item.role === "COORDINATOR" ? "Koordinator" : "O‘qituvchi"}
                    </span>
                    <StatusBadge item={item} />
                  </div>
                  <div className="mt-1 text-xs text-[var(--fb-ink-muted)]">
                    {fmt(item.valid_from)} — {item.valid_to ? fmt(item.valid_to) : "muddatsiz"}
                    {item.decision_reason && !item.role_active ? ` · Izoh: ${item.decision_reason}` : ""}
                  </div>
                </div>
                {!item.is_self && item.status !== "REVOKED" && (
                  <button
                    type="button"
                    onClick={() => {
                      setRevokeId(item.id);
                      setRevokeReason("");
                    }}
                    className="skeuo-btn-secondary self-start rounded-xl px-3 py-1.5 text-xs"
                  >
                    <UserMinus className="h-3.5 w-3.5" aria-hidden="true" />
                    {item.role_active ? "Ruxsatni bekor qilish" : "So‘rovni bekor qilish"}
                  </button>
                )}
              </div>
              {revokeId === item.id && (
                <div className="flex flex-col sm:flex-row gap-2">
                  <label htmlFor={`${ids}-revoke`} className="sr-only">
                    Bekor qilish sababi
                  </label>
                  <input
                    id={`${ids}-revoke`}
                    value={revokeReason}
                    onChange={(e) => setRevokeReason(e.target.value)}
                    placeholder="Sabab (kamida 15 belgi), masalan: universitetdan ishdan bo‘shadi"
                    className="skeuo-input flex-1 rounded-xl px-3.5 py-2 text-sm"
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <button type="button" onClick={() => setRevokeId(null)} className="skeuo-btn-secondary rounded-xl px-3 py-2 text-xs">
                      Yo‘q
                    </button>
                    <button
                      type="button"
                      disabled={revokeReason.trim().length < 15 || revoking}
                      onClick={() => void confirmRevoke()}
                      className="rounded-xl bg-rose-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
                    >
                      {revoking ? "…" : "Tasdiqlash"}
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
