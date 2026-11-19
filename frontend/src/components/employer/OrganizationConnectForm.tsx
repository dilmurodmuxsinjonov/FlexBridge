"use client";

import { useId, useState } from "react";
import Link from "next/link";
import { AlertCircle, Building2, CheckCircle2, FileText, Loader2, ShieldCheck } from "lucide-react";
import { fetchUserSecurityOverview } from "@/lib/api";
import { useAsyncData } from "@/lib/useAsyncData";
import { uploadStaffPdf } from "@/lib/universityStaff";
import { ROLE_LABELS, describeOrgError, registerOrganization, type OrgRole } from "@/lib/orgTeam";

const REGIONS = [
  "Toshkent shahri", "Toshkent viloyati", "Andijon", "Buxoro", "Farg‘ona", "Jizzax", "Xorazm", "Namangan",
  "Navoiy", "Qashqadaryo", "Qoraqalpog‘iston", "Samarqand", "Sirdaryo", "Surxondaryo",
];

/**
 * Register a company on FlexBridge. A new company's founder becomes its main
 * (OWNER) account after the platform verifies the documents; if the company is
 * already registered, the same form asks its owner to let you join.
 */
export default function OrganizationConnectForm() {
  const ids = useId();
  const prereq = useAsyncData("org-connect-prereq", async () => {
    const security = await fetchUserSecurityOverview();
    const current = security.sessions?.find((s) => s.is_current);
    return { totp: Boolean(security.totp_enabled), mfaSession: current?.assurance === "MFA" };
  });

  const [taxId, setTaxId] = useState("");
  const [legalName, setLegalName] = useState("");
  const [publicName, setPublicName] = useState("");
  const [region, setRegion] = useState(REGIONS[0]);
  const [website, setWebsite] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [note, setNote] = useState("");
  const [joinRole, setJoinRole] = useState<Exclude<OrgRole, "OWNER">>("HR");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ created: boolean; status: string } | null>(null);

  const ready = prereq.data?.totp && prereq.data?.mfaSession;
  const valid =
    /^[0-9\s-]{3,40}$/.test(taxId.trim()) && legalName.trim().length >= 2 && publicName.trim().length >= 2 && file && note.trim().length >= 15;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!valid || !file) return;
    setBusy(true);
    setError(null);
    try {
      const doc = await uploadStaffPdf(file, "ORGANIZATION_EVIDENCE");
      const site = website.trim();
      const res = await registerOrganization({
        tax_id: taxId.trim(),
        legal_name: legalName.trim(),
        public_name: publicName.trim(),
        region,
        description: description.trim() || undefined,
        website: site ? (/^https?:\/\//.test(site) ? site : `https://${site}`) : undefined,
        file_ids: [doc.file_id],
        evidence_note: note.trim(),
        membership_role: joinRole,
      });
      setResult({ created: res.created, status: res.membership_status });
    } catch (err) {
      setError(describeOrgError(err));
    } finally {
      setBusy(false);
    }
  };

  if (result) {
    return (
      <div className="flex items-start gap-2.5 rounded-2xl border border-emerald-500/25 bg-emerald-500/10 p-4 text-sm text-emerald-700 dark:text-emerald-300">
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>
          {result.created || result.status === "PENDING_VERIFICATION"
            ? "Ariza yuborildi. FlexBridge hujjatlarni tekshirgach, siz korxonaning asosiy (rahbar) akkauntiga ega bo‘lasiz va xodimlarni o‘zingiz qo‘shasiz."
            : "Bu korxona allaqachon ro‘yxatdan o‘tgan. Qo‘shilish so‘rovingiz korxona rahbariga yuborildi — u tasdiqlagach, kabinet ochiladi."}{" "}
          <Link href="/employer" className="font-semibold underline underline-offset-2">
            Korxona kabineti
          </Link>
        </span>
      </div>
    );
  }

  const field = "skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm";
  const label = "mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]";

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" aria-labelledby={`${ids}-title`}>
      <div className="space-y-1">
        <h3 id={`${ids}-title`} className="font-heading text-base font-bold text-[var(--fb-ink)] flex items-center gap-2">
          <Building2 className="h-4 w-4 text-emerald-600 dark:text-emerald-300" aria-hidden="true" />
          Korxonani FlexBridge’ga ulash
        </h3>
        <p className="text-sm text-[var(--fb-ink-secondary)]">
          Tasdiqlangach, siz korxonaning asosiy (rahbar) akkauntiga ega bo‘lasiz: vakansiya joylaysiz va xodimlarni o‘zingiz qo‘shasiz.
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
          {!prereq.data?.totp ? (
            <p>
              <Link href="/hisob" className="underline underline-offset-2 font-semibold">
                Hisob va xavfsizlik
              </Link>{" "}
              bo‘limida ikki bosqichli himoyani (authenticator) yoqing.
            </p>
          ) : (
            <p>Tizimdan chiqib, authenticator kodi bilan qayta kiring.</p>
          )}
        </div>
      ) : null}

      {error && (
        <div role="alert" className="flex items-start gap-2.5 rounded-2xl border border-rose-500/25 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {error}
        </div>
      )}

      <fieldset disabled={!ready || busy} className="grid grid-cols-1 gap-4 sm:grid-cols-2 min-w-0 disabled:opacity-60">
        <div>
          <label htmlFor={`${ids}-tax`} className={label}>
            STIR (INN)
          </label>
          <input id={`${ids}-tax`} value={taxId} onChange={(e) => setTaxId(e.target.value)} inputMode="numeric" placeholder="9 xonali STIR" className={field} />
        </div>
        <div>
          <label htmlFor={`${ids}-region`} className={label}>
            Hudud
          </label>
          <select id={`${ids}-region`} value={region} onChange={(e) => setRegion(e.target.value)} className={field}>
            {REGIONS.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`${ids}-legal`} className={label}>
            Yuridik nomi
          </label>
          <input id={`${ids}-legal`} value={legalName} onChange={(e) => setLegalName(e.target.value)} placeholder="«Misol Soft» MChJ" className={field} />
        </div>
        <div>
          <label htmlFor={`${ids}-public`} className={label}>
            Talabalarga ko‘rinadigan nomi
          </label>
          <input id={`${ids}-public`} value={publicName} onChange={(e) => setPublicName(e.target.value)} placeholder="Misol Soft" className={field} />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor={`${ids}-site`} className={label}>
            Veb-sayt <span className="font-normal text-[var(--fb-ink-muted)]">(ixtiyoriy)</span>
          </label>
          <input id={`${ids}-site`} value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="misolsoft.uz" className={field} />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor={`${ids}-desc`} className={label}>
            Qisqacha ta’rif <span className="font-normal text-[var(--fb-ink-muted)]">(ixtiyoriy)</span>
          </label>
          <textarea id={`${ids}-desc`} value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={field} />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor={`${ids}-file`} className={label}>
            Vakolatingizni tasdiqlovchi hujjat (PDF)
          </label>
          <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-[var(--fb-hairline)] px-3.5 py-3 text-sm text-[var(--fb-ink-secondary)] hover:border-emerald-400">
            <FileText className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="min-w-0 truncate">{file ? file.name : "Ishonchnoma, rahbar buyrug‘i yoki davlat ro‘yxatidan o‘tganlik guvohnomasi"}</span>
            <input id={`${ids}-file`} type="file" accept="application/pdf,.pdf" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
        </div>
        <div className="sm:col-span-2">
          <label htmlFor={`${ids}-note`} className={label}>
            Tekshiruvchi uchun izoh
          </label>
          <textarea
            id={`${ids}-note`}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="Lavozimingiz va korxonani kim nomidan ro‘yxatdan o‘tkazayotganingiz"
            className={field}
          />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor={`${ids}-role`} className={label}>
            Korxona allaqachon ro‘yxatdan o‘tgan bo‘lsa, qaysi rolda qo‘shilasiz?
          </label>
          <select id={`${ids}-role`} value={joinRole} onChange={(e) => setJoinRole(e.target.value as Exclude<OrgRole, "OWNER">)} className={field}>
            {(["HR", "MENTOR", "HOST_COORDINATOR", "BILLING"] as const).map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">Yangi korxona uchun bu tanlov hisobga olinmaydi — siz uning rahbari bo‘lasiz.</p>
        </div>
        <div className="sm:col-span-2">
          <button type="submit" disabled={!valid || busy} data-tone="emerald" className="skeuo-btn-tone w-full rounded-xl px-5 py-3 text-sm disabled:opacity-50">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
            {busy ? "Yuborilmoqda…" : "Arizani yuborish"}
          </button>
        </div>
      </fieldset>
    </form>
  );
}
