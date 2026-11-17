"use client";

import { useId, useState } from "react";
import Link from "next/link";
import { AlertCircle, CheckCircle2, FileText, Landmark, Loader2, ShieldCheck } from "lucide-react";
import { fetchUserSecurityOverview } from "@/lib/api";
import { useAsyncData } from "@/lib/useAsyncData";
import { describeStaffError, fetchMyVerifiedContacts, newIdempotencyKey, submitAppointment, uploadStaffPdf } from "@/lib/universityStaff";

const REGIONS = [
  "Toshkent shahri", "Toshkent viloyati", "Andijon", "Buxoro", "Farg‘ona", "Jizzax", "Xorazm", "Namangan",
  "Navoiy", "Qashqadaryo", "Qoraqalpog‘iston", "Samarqand", "Sirdaryo", "Surxondaryo",
];

const today = () => new Date().toISOString().slice(0, 10);

function FilePick({ id, label, hint, file, onPick }: { id: string; label: string; hint: string; file: File | null; onPick: (f: File | null) => void }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
        {label}
      </label>
      <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-[var(--fb-hairline)] px-3.5 py-3 text-sm text-[var(--fb-ink-secondary)] hover:border-indigo-400">
        <FileText className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="min-w-0 truncate">{file ? file.name : hint}</span>
        <input id={id} type="file" accept="application/pdf,.pdf" className="sr-only" onChange={(e) => onPick(e.target.files?.[0] ?? null)} />
      </label>
    </div>
  );
}

/**
 * Connect a university to FlexBridge: the signed-in representative becomes the
 * university's coordinator (its own account that later adds staff) once a
 * platform moderator verifies the appointment order and signed agreement and
 * the representative accepts the reviewed request.
 */
export default function UniversityConnectForm({ onSubmitted }: { onSubmitted?: () => void }) {
  const ids = useId();
  const prereq = useAsyncData("connect-prereq", async () => {
    const [security, contacts] = await Promise.all([fetchUserSecurityOverview(), fetchMyVerifiedContacts()]);
    const current = security.sessions?.find((s) => s.is_current);
    return { totp: Boolean(security.totp_enabled), mfaSession: current?.assurance === "MFA", contacts };
  });

  const [name, setName] = useState("");
  const [region, setRegion] = useState(REGIONS[0]);
  const [registry, setRegistry] = useState("");
  const [appointmentFile, setAppointmentFile] = useState<File | null>(null);
  const [agreementFile, setAgreementFile] = useState<File | null>(null);
  const [agreementFrom, setAgreementFrom] = useState(today());
  const [agreementTo, setAgreementTo] = useState("");
  const [legalBasis, setLegalBasis] = useState("");
  const [note, setNote] = useState("");
  const [chosenContact, setChosenContact] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const contacts = prereq.data?.contacts ?? [];
  const contactId = chosenContact || contacts.find((c) => c.is_primary)?.id || contacts[0]?.id || "";
  const ready = prereq.data?.totp && prereq.data?.mfaSession && contacts.length > 0;
  const valid =
    name.trim().length >= 2 && /^[A-Za-z0-9][A-Za-z0-9-]{2,63}$/.test(registry.trim()) && appointmentFile && agreementFile &&
    legalBasis.trim().length >= 15 && note.trim().length >= 15 && contactId;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!valid || !appointmentFile || !agreementFile) return;
    setBusy(true);
    setError(null);
    try {
      const doc = await uploadStaffPdf(appointmentFile, "INSTITUTION_APPOINTMENT");
      const agreement = await uploadStaffPdf(agreementFile, "INSTITUTION_AGREEMENT");
      await submitAppointment(
        {
          registry_code: registry.trim(),
          name: name.trim(),
          region,
          document_file_id: doc.file_id,
          agreement_file_id: agreement.file_id,
          file_ids: [doc.file_id, agreement.file_id],
          agreement_valid_from: agreementFrom,
          agreement_valid_to: agreementTo || null,
          purposes: ["ACADEMIC_VIEW"],
          contact_id: contactId,
          valid_from: today(),
          valid_to: null,
          legal_basis: legalBasis.trim(),
          evidence_note: note.trim(),
        },
        newIdempotencyKey("connect")
      );
      setDone(true);
      onSubmitted?.();
    } catch (err) {
      setError(describeStaffError(err));
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <div className="flex items-start gap-2.5 rounded-2xl border border-emerald-500/25 bg-emerald-500/10 p-4 text-sm text-emerald-700 dark:text-emerald-300">
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>
          Ariza yuborildi. FlexBridge hujjatlarni odatda 3 ish kunida tekshiradi. Tasdiqlangach, quyidagi ro‘yxatda tayinlovni bir marta
          tasdiqlaysiz va universitet kabinetingiz ochiladi.
        </span>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" aria-labelledby={`${ids}-title`}>
      <div className="space-y-1">
        <h3 id={`${ids}-title`} className="font-heading text-base font-bold text-[var(--fb-ink)] flex items-center gap-2">
          <Landmark className="h-4 w-4 text-indigo-600 dark:text-indigo-300" aria-hidden="true" />
          Universitetni FlexBridge’ga ulash
        </h3>
        <p className="text-sm text-[var(--fb-ink-secondary)]">
          Ariza tasdiqlangach, siz universitetning koordinatori bo‘lasiz: talabalikni tasdiqlaysiz va o‘z xodimlaringizni qo‘shasiz.
        </p>
      </div>

      {prereq.isLoading && !prereq.data ? (
        <div className="flex items-center gap-2 text-sm text-[var(--fb-ink-secondary)]">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Tekshirilmoqda…
        </div>
      ) : !ready ? (
        <div className="rounded-2xl border border-amber-500/25 bg-amber-500/10 p-4 text-sm text-amber-800 dark:text-amber-300 space-y-1.5">
          <p className="font-semibold flex items-center gap-1.5">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" /> Avval hisobingizni himoyalang
          </p>
          <ul className="list-disc pl-5 space-y-0.5">
            {!prereq.data?.totp && (
              <li>
                <Link href="/nomzod/xavfsizlik" className="underline underline-offset-2 font-semibold">
                  Xavfsizlik
                </Link>{" "}
                bo‘limida ikki bosqichli himoyani (authenticator) yoqing.
              </li>
            )}
            {prereq.data?.totp && !prereq.data?.mfaSession && <li>Tizimdan chiqib, authenticator kodi bilan qayta kiring.</li>}
            {contacts.length === 0 && <li>Telefon raqamingiz yoki pochtangiz tasdiqlangan bo‘lishi kerak.</li>}
          </ul>
        </div>
      ) : null}

      {error && (
        <div role="alert" className="flex items-start gap-2.5 rounded-2xl border border-rose-500/25 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {error}
        </div>
      )}

      <fieldset disabled={!ready || busy} className="grid grid-cols-1 gap-4 sm:grid-cols-2 min-w-0 disabled:opacity-60">
        <div className="sm:col-span-2">
          <label htmlFor={`${ids}-name`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
            Universitetning rasmiy nomi
          </label>
          <input id={`${ids}-name`} value={name} onChange={(e) => setName(e.target.value)} placeholder="Masalan: Toshkent axborot texnologiyalari universiteti" className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm" />
        </div>
        <div>
          <label htmlFor={`${ids}-region`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
            Hudud
          </label>
          <select id={`${ids}-region`} value={region} onChange={(e) => setRegion(e.target.value)} className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm">
            {REGIONS.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`${ids}-registry`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
            STIR (INN)
          </label>
          <input id={`${ids}-registry`} value={registry} onChange={(e) => setRegistry(e.target.value)} inputMode="numeric" placeholder="9 xonali STIR" className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm" />
        </div>
        <FilePick id={`${ids}-doc`} label="Sizning tayinlov hujjatingiz (PDF)" hint="Rektor buyrug‘i yoki ishonchnoma" file={appointmentFile} onPick={setAppointmentFile} />
        <FilePick id={`${ids}-agr`} label="Hamkorlik shartnomasi (PDF)" hint="FlexBridge bilan imzolangan shartnoma" file={agreementFile} onPick={setAgreementFile} />
        <div>
          <label htmlFor={`${ids}-af`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
            Shartnoma kuchga kirgan sana
          </label>
          <input id={`${ids}-af`} type="date" max={today()} value={agreementFrom} onChange={(e) => setAgreementFrom(e.target.value)} className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm" />
        </div>
        <div>
          <label htmlFor={`${ids}-at`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
            Shartnoma tugash sanasi <span className="font-normal text-[var(--fb-ink-muted)]">(ixtiyoriy)</span>
          </label>
          <input id={`${ids}-at`} type="date" min={today()} value={agreementTo} onChange={(e) => setAgreementTo(e.target.value)} className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm" />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor={`${ids}-basis`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
            Huquqiy asos
          </label>
          <input id={`${ids}-basis`} value={legalBasis} onChange={(e) => setLegalBasis(e.target.value)} placeholder="Masalan: Rektorning 2026-yil 1-sentabrdagi 245-son buyrug‘i" className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm" />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor={`${ids}-note`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
            Tekshiruvchi uchun izoh
          </label>
          <textarea id={`${ids}-note`} value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder="Lavozimingiz va universitetdagi vazifangiz" className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm" />
        </div>
        {contacts.length > 0 && (
          <div className="sm:col-span-2">
            <label htmlFor={`${ids}-contact`} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
              Bog‘lanish uchun kontakt
            </label>
            <select id={`${ids}-contact`} value={contactId} onChange={(e) => setChosenContact(e.target.value)} className="skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm">
              {contacts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.channel === "EMAIL" ? "Pochta" : "Telefon"}: {c.masked_destination}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="sm:col-span-2">
          <button type="submit" disabled={!valid || busy} data-tone="indigo" className="skeuo-btn-tone w-full rounded-xl px-5 py-3 text-sm disabled:opacity-50">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
            {busy ? "Yuborilmoqda…" : "Arizani yuborish"}
          </button>
        </div>
      </fieldset>
    </form>
  );
}
