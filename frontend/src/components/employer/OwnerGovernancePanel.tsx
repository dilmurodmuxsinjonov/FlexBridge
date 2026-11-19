"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Crown,
  FileUp,
  KeyRound,
  Loader2,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  UserPlus,
} from "lucide-react";
import { fetchUserSecurityOverview } from "@/lib/api";
import { fetchTeam, type TeamOverview } from "@/lib/orgTeam";
import { uploadStaffPdf } from "@/lib/universityStaff";
import {
  fetchIncomingOwnerRequests,
  fetchIncomingOwnerTransfers,
  fetchOrgContinuityCases,
  fetchVerifiedContacts,
  objectOrgContinuity,
  patchOrganizationProfile,
  respondOwnerCase,
  submitOrgContinuity,
  submitOwnerAddition,
  submitOwnerTransfer,
  type IncomingOwnerCaseItem,
  type OrgContinuityCaseItem,
  type VerifiedContactItem,
} from "@/lib/employerGovernance";
import { enumLabel } from "@/lib/labels";

type GovTab = "PROFILE" | "OWNERSHIP" | "CONTINUITY" | "INBOX";

export default function OwnerGovernancePanel({ orgId }: { orgId: string | null }) {
  const [tab, setTab] = useState<GovTab>("OWNERSHIP");
  const [refreshing, setRefreshing] = useState(false);
  const [loadedOrg, setLoadedOrg] = useState<string | null>(null);
  const [mfaSession, setMfaSession] = useState<boolean>(false);
  const [team, setTeam] = useState<TeamOverview | null>(null);
  const [contacts, setContacts] = useState<VerifiedContactItem[]>([]);
  const [incomingReq, setIncomingReq] = useState<IncomingOwnerCaseItem[]>([]);
  const [incomingTrf, setIncomingTrf] = useState<IncomingOwnerCaseItem[]>([]);
  const [continuityCases, setContinuityCases] = useState<OrgContinuityCaseItem[]>([]);

  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Profile edit form (API-071)
  const [publicName, setPublicName] = useState("");
  const [legalName, setLegalName] = useState("");
  const [region, setRegion] = useState("");
  const [website, setWebsite] = useState("");
  const [description, setDescription] = useState("");
  const [profileFile, setProfileFile] = useState<File | null>(null);
  const [profileNote, setProfileNote] = useState("");

  // Owner addition / transfer form
  const [addMemberId, setAddMemberId] = useState("");
  const [addFile, setAddFile] = useState<File | null>(null);
  const [addNote, setAddNote] = useState("");

  const [trfMemberId, setTrfMemberId] = useState("");
  const [trfFile, setTrfFile] = useState<File | null>(null);
  const [trfNote, setTrfNote] = useState("");

  // Continuity intake / objection form
  const [contContactId, setContContactId] = useState("");
  const [contFile, setContFile] = useState<File | null>(null);
  const [contNote, setContNote] = useState("");
  const [objReasons, setObjReasons] = useState<Record<string, string>>({});

  // Consent contact pickers
  const [consentContacts, setConsentContacts] = useState<Record<string, string>>({});

  const fetchSnapshot = useCallback(async (targetOrgId: string) => {
    const sec = await fetchUserSecurityOverview().catch(() => null);
    const isMfa = Boolean(sec?.sessions?.some((s) => s.is_current && s.assurance === "MFA"));
    const [teamData, contactsList] = await Promise.all([
      fetchTeam(targetOrgId).catch(() => null),
      fetchVerifiedContacts().catch(() => []),
    ]);
    const [reqList, trfList, contList] = isMfa
      ? await Promise.all([
          fetchIncomingOwnerRequests().catch(() => []),
          fetchIncomingOwnerTransfers().catch(() => []),
          teamData ? fetchOrgContinuityCases(targetOrgId).catch(() => []) : Promise.resolve([]),
        ])
      : [[], [], []];
    return { isMfa, teamData, contactsList, reqList, trfList, contList };
  }, []);

  const applySnapshot = useCallback(
    (snap: Awaited<ReturnType<typeof fetchSnapshot>>, targetOrgId: string) => {
      setMfaSession(snap.isMfa);
      setTeam(snap.teamData);
      setContacts(snap.contactsList);
      if (snap.contactsList.length > 0) {
        setContContactId((prev) => prev || snap.contactsList[0].id);
      }
      if (snap.teamData?.organization) {
        setPublicName(snap.teamData.organization.public_name || "");
        setLegalName(snap.teamData.organization.legal_name || "");
        setRegion(snap.teamData.organization.region || "");
      }
      setIncomingReq(snap.reqList);
      setIncomingTrf(snap.trfList);
      setContinuityCases(snap.contList);
      setLoadedOrg(targetOrgId);
    },
    []
  );

  const reload = useCallback(async () => {
    if (!orgId) return;
    setRefreshing(true);
    try {
      const snap = await fetchSnapshot(orgId);
      applySnapshot(snap, orgId);
    } finally {
      setRefreshing(false);
    }
  }, [orgId, fetchSnapshot, applySnapshot]);

  useEffect(() => {
    if (!orgId) return;
    let active = true;
    fetchSnapshot(orgId)
      .then((snap) => {
        if (active) applySnapshot(snap, orgId);
      })
      .catch(() => {
        if (active) setLoadedOrg(orgId);
      });
    return () => {
      active = false;
    };
  }, [orgId, fetchSnapshot, applySnapshot]);

  if (!orgId) return null;
  const loading = refreshing || loadedOrg !== orgId;

  const isOwner = Boolean(team?.members?.some((m) => m.is_self && m.roles.includes("OWNER")));
  const nonOwnerMembers = (team?.members || []).filter(
    (m) => m.status === "ACTIVE" && !m.is_self && !m.roles.includes("OWNER")
  );
  const otherOwnerMembers = (team?.members || []).filter(
    (m) => m.status === "ACTIVE" && !m.is_self && m.roles.includes("OWNER")
  );
  const totalIncoming = incomingReq.length + incomingTrf.length;

  const runAction = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await fn();
      await reload();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Amalni bajarib bo‘lmadi.");
    } finally {
      setBusy(null);
    }
  };

  const handleProfilePatch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!profileFile || profileNote.trim().length < 15) {
      setError("Tasdiqlovchi PDF hujjat va kamida 15 belgidan iborat asosnoma kiriting.");
      return;
    }
    void runAction("profile", async () => {
      const up = await uploadStaffPdf(profileFile, "ORGANIZATION_EVIDENCE");
      const res = await patchOrganizationProfile(orgId, {
        public_name: publicName.trim() || undefined,
        legal_name: legalName.trim() || undefined,
        region: region.trim() || undefined,
        website: website.trim() || null,
        description: description.trim() || null,
        file_ids: [up.file_id],
        evidence_note: profileNote.trim(),
      });
      setProfileFile(null);
      setProfileNote("");
      setNotice(
        res.case_id
          ? `Rekvizit o‘zgarishi tekshiruvga yuborildi (Ariza: ${res.case_id}).`
          : "Tashkilot ma’lumotlarida o‘zgarish aniqlanmadi."
      );
    });
  };

  const handleAddOwner = (e: React.FormEvent) => {
    e.preventDefault();
    if (!addMemberId || !addFile || addNote.trim().length < 15) {
      setError("Xodimni tanlang, PDF hujjat yuklang va kamida 15 belgili izoh yozing.");
      return;
    }
    void runAction("add-owner", async () => {
      const up = await uploadStaffPdf(addFile, "ORGANIZATION_EVIDENCE");
      const res = await submitOwnerAddition(orgId, {
        target_membership_id: addMemberId,
        file_ids: [up.file_id],
        evidence_note: addNote.trim(),
      });
      setAddMemberId("");
      setAddFile(null);
      setAddNote("");
      setNotice(`Hamrahbar qo‘shish so‘rovi yuborildi (Holat: ${enumLabel(res.status)}). Xodim roziligi kutilmoqda.`);
    });
  };

  const handleTransferOwner = (e: React.FormEvent) => {
    e.preventDefault();
    if (!trfMemberId || !trfFile || trfNote.trim().length < 15) {
      setError("Voris rahbarni tanlang, PDF hujjat yuklang va kamida 15 belgili izoh yozing.");
      return;
    }
    void runAction("transfer-owner", async () => {
      const up = await uploadStaffPdf(trfFile, "ORGANIZATION_EVIDENCE");
      const res = await submitOwnerTransfer(orgId, {
        target_membership_id: trfMemberId,
        file_ids: [up.file_id],
        evidence_note: trfNote.trim(),
      });
      setTrfMemberId("");
      setTrfFile(null);
      setTrfNote("");
      setNotice(`Rahbarlikni topshirish so‘rovi yuborildi (${enumLabel(res.status)}).`);
    });
  };

  const handleContinuitySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!contContactId || !contFile || contNote.trim().length < 15) {
      setError("Tasdiqlangan kontakt, PDF hujjat va kamida 15 belgili asosnoma kerak.");
      return;
    }
    void runAction("continuity-submit", async () => {
      const up = await uploadStaffPdf(contFile, "ORGANIZATION_EVIDENCE");
      const res = await submitOrgContinuity(orgId, {
        contact_id: contContactId,
        file_ids: [up.file_id],
        evidence_note: contNote.trim(),
      });
      setContFile(null);
      setContNote("");
      setNotice(`Vorislik arizasi Moderator va Komplayens tekshiruviga yuborildi (${res.id}).`);
    });
  };

  return (
    <section
      aria-labelledby="owner-gov-heading"
      className="rounded-[24px] skeuo-card p-5 sm:p-6 space-y-5"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-[var(--fb-border)] pb-4">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full skeuo-badge-recessed px-2.5 py-0.5 text-[11px] font-semibold text-[#c94f1d] dark:text-[#f47a3d]">
            <Crown className="h-3.5 w-3.5" aria-hidden="true" />
            Rahbarlik, Rekvizitlar & Vorislik
          </span>
          <h3
            id="owner-gov-heading"
            className="mt-1.5 font-heading text-base sm:text-lg font-bold text-[var(--fb-ink)]"
          >
            Korxona Boshqaruvi va Vakolat O‘tkazish
          </h3>
          <p className="text-xs text-[var(--fb-ink-muted)]">
            Rasmiy rekvizit o‘zgartirish, hamrahbar (OWNER) qo‘shish, rahbarlikni topshirish va vorislik himoyasi.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void reload()}
          disabled={loading}
          className="skeuo-btn-secondary inline-flex items-center gap-1.5 self-start rounded-full px-3.5 py-1.5 text-xs font-semibold"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Yangilash
        </button>
      </div>

      {!mfaSession && (
        <div className="flex flex-col gap-2 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-800 dark:text-amber-200 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-2.5">
            <KeyRound className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
            <span>
              Rahbarlik vorisligi va rasmiy rekvizitlarni o‘zgartirish faqat{" "}
              <strong>2FA (MFA) bilan kirilgan</strong> joriy sessiyada ruxsat etiladi.
            </span>
          </div>
          <Link
            href="/nomzod/xavfsizlik"
            prefetch={false}
            className="skeuo-btn-obsidian shrink-0 rounded-full px-3.5 py-1.5 text-[11px] font-semibold"
          >
            2FA sozlash
          </Link>
        </div>
      )}

      {/* Sub-navigation */}
      <div className="flex flex-wrap gap-2">
        {(
          [
            { id: "OWNERSHIP", label: "Hamrahbar & O‘tkazish" },
            { id: "CONTINUITY", label: `Vorislik (${continuityCases.length})` },
            { id: "INBOX", label: `Mening roziligim (${totalIncoming})` },
            ...(isOwner ? [{ id: "PROFILE" as const, label: "Rasmiy rekvizitlarni tahrirlash" }] : []),
          ] as Array<{ id: GovTab; label: string }>
        ).map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => {
              setTab(item.id);
              setError(null);
              setNotice(null);
            }}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold transition ${
              tab === item.id ? "skeuo-btn-obsidian" : "skeuo-btn-secondary"
            }`}
          >
            {item.label}
          </button>
        ))}
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
      {notice && (
        <div className="flex items-start gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-800 dark:text-emerald-300">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{notice}</span>
        </div>
      )}

      {tab === "PROFILE" && isOwner && (
        <form onSubmit={handleProfilePatch} className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="gov-pub-name" className="block text-xs font-semibold text-[var(--fb-ink)]">
              Ommaviy nom (Public name)
            </label>
            <input
              id="gov-pub-name"
              type="text"
              value={publicName}
              onChange={(e) => setPublicName(e.target.value)}
              className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
            />
          </div>
          <div>
            <label htmlFor="gov-legal-name" className="block text-xs font-semibold text-[var(--fb-ink)]">
              Yuridik nom (Legal name)
            </label>
            <input
              id="gov-legal-name"
              type="text"
              value={legalName}
              onChange={(e) => setLegalName(e.target.value)}
              className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
            />
          </div>
          <div>
            <label htmlFor="gov-region" className="block text-xs font-semibold text-[var(--fb-ink)]">
              Hudud
            </label>
            <input
              id="gov-region"
              type="text"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
            />
          </div>
          <div>
            <label htmlFor="gov-web" className="block text-xs font-semibold text-[var(--fb-ink)]">
              Veb-sayt (ixtiyoriy)
            </label>
            <input
              id="gov-web"
              type="url"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="https://kompaniya.uz"
              className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
            />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="gov-desc" className="block text-xs font-semibold text-[var(--fb-ink)]">
              Tashkilot tavsifi (ixtiyoriy)
            </label>
            <textarea
              id="gov-desc"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="skeuo-input mt-1 w-full rounded-xl p-2.5 text-xs"
            />
          </div>
          <div>
            <label htmlFor="gov-prof-file" className="block text-xs font-semibold text-[var(--fb-ink)]">
              Tasdiqlovchi hujjat (PDF)
            </label>
            <input
              id="gov-prof-file"
              type="file"
              accept="application/pdf"
              onChange={(e) => setProfileFile(e.target.files?.[0] || null)}
              className="skeuo-input mt-1 w-full rounded-xl px-3 py-1.5 text-xs"
            />
          </div>
          <div>
            <label htmlFor="gov-prof-note" className="block text-xs font-semibold text-[var(--fb-ink)]">
              O‘zgartirish asosi (kamida 15 belgi)
            </label>
            <input
              id="gov-prof-note"
              type="text"
              value={profileNote}
              onChange={(e) => setProfileNote(e.target.value)}
              placeholder="Masalan: Guvohnoma qayta rasmiylashtirilishi munosabati bilan..."
              className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
            />
          </div>
          <div className="sm:col-span-2 flex justify-end">
            <button
              type="submit"
              disabled={!mfaSession || busy === "profile"}
              className="skeuo-btn-obsidian inline-flex items-center gap-1.5 rounded-full px-5 py-2 text-xs font-semibold disabled:opacity-50"
            >
              {busy === "profile" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Building2 className="h-3.5 w-3.5" />}
              O‘zgartirish so‘rovini yuborish
            </button>
          </div>
        </form>
      )}

      {tab === "OWNERSHIP" && (
        <div className="grid gap-5 md:grid-cols-2">
          {/* Add Co-Owner */}
          <form onSubmit={handleAddOwner} className="rounded-2xl skeuo-well p-4 space-y-3">
            <div className="flex items-center gap-2">
              <UserPlus className="h-4 w-4 text-[#c94f1d]" aria-hidden="true" />
              <h4 className="text-xs font-bold text-[var(--fb-ink)]">Yangi hamrahbar (OWNER) qo‘shish</h4>
            </div>
            {!isOwner ? (
              <p className="text-xs text-[var(--fb-ink-muted)]">
                Faqat korxonaning amaldagi rahbari (OWNER) jamoa xodimiga OWNER vakolatini taklif qila oladi.
              </p>
            ) : (
              <>
                <select
                  aria-label="Hamrahbarlikka nomzod xodim"
                  value={addMemberId}
                  onChange={(e) => setAddMemberId(e.target.value)}
                  className="skeuo-input w-full rounded-xl px-3 py-2 text-xs"
                >
                  <option value="">
                    {nonOwnerMembers.length ? "Faol xodimni tanlang…" : "Boshqa nomzod xodim topilmadi"}
                  </option>
                  {nonOwnerMembers.map((m) => (
                    <option key={m.membership_id} value={m.membership_id}>
                      {m.display_name} ({m.roles.map((r) => enumLabel(r)).join(", ")})
                    </option>
                  ))}
                </select>
                <input
                  aria-label="Hamrahbarlik hujjati PDF"
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setAddFile(e.target.files?.[0] || null)}
                  className="skeuo-input w-full rounded-xl px-3 py-1.5 text-xs"
                />
                <input
                  aria-label="Hamrahbar tayinlash sababi"
                  type="text"
                  value={addNote}
                  onChange={(e) => setAddNote(e.target.value)}
                  placeholder="Buyruq / qaror asosi (kamida 15 belgi)..."
                  className="skeuo-input w-full rounded-xl px-3 py-2 text-xs"
                />
                <button
                  type="submit"
                  disabled={!mfaSession || !addMemberId || busy === "add-owner"}
                  className="skeuo-btn-obsidian inline-flex w-full items-center justify-center gap-1.5 rounded-full py-2 text-xs font-semibold disabled:opacity-50"
                >
                  {busy === "add-owner" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Hamrahbar so‘rovi yuborish
                </button>
              </>
            )}
          </form>

          {/* Relinquish / Transfer OWNER */}
          <form onSubmit={handleTransferOwner} className="rounded-2xl skeuo-well p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Crown className="h-4 w-4 text-emerald-500" aria-hidden="true" />
              <h4 className="text-xs font-bold text-[var(--fb-ink)]">Rahbarlikni mavjud OWNER ga topshirish</h4>
            </div>
            {!isOwner ? (
              <p className="text-xs text-[var(--fb-ink-muted)]">
                Rahbarlikni o‘tkazish faqat amaldagi OWNER tomonidan boshqa OWNER roziligi bilan bajariladi.
              </p>
            ) : (
              <>
                <select
                  aria-label="Qabul qiluvchi OWNER"
                  value={trfMemberId}
                  onChange={(e) => setTrfMemberId(e.target.value)}
                  className="skeuo-input w-full rounded-xl px-3 py-2 text-xs"
                >
                  <option value="">
                    {otherOwnerMembers.length
                      ? "Qabul qiluvchi hamrahbarni tanlang…"
                      : "Avval kamida 1 ta hamrahbar qo‘shing"}
                  </option>
                  {otherOwnerMembers.map((m) => (
                    <option key={m.membership_id} value={m.membership_id}>
                      {m.display_name}
                    </option>
                  ))}
                </select>
                <input
                  aria-label="Topshirish dalili PDF"
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setTrfFile(e.target.files?.[0] || null)}
                  className="skeuo-input w-full rounded-xl px-3 py-1.5 text-xs"
                />
                <input
                  aria-label="Rahbarlikni topshirish sababi"
                  type="text"
                  value={trfNote}
                  onChange={(e) => setTrfNote(e.target.value)}
                  placeholder="Vakolatni topshirish sababi (kamida 15 belgi)..."
                  className="skeuo-input w-full rounded-xl px-3 py-2 text-xs"
                />
                <button
                  type="submit"
                  disabled={!mfaSession || !trfMemberId || busy === "transfer-owner"}
                  className="skeuo-btn-secondary inline-flex w-full items-center justify-center gap-1.5 rounded-full py-2 text-xs font-semibold disabled:opacity-50"
                >
                  {busy === "transfer-owner" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Topshirish so‘rovini yuborish
                </button>
              </>
            )}
          </form>
        </div>
      )}

      {tab === "CONTINUITY" && (
        <div className="space-y-4">
          {isOwner ? (
            <div className="space-y-3">
              <p className="text-xs text-[var(--fb-ink-secondary)]">
                Amaldagi rahbar mavjud bo‘lmagan hollarda xodimlar ochgan vorislik da’volari shu yerda ko‘rinadi; agar faol bo‘lsangiz darhol e’tiroz bildira olasiz.
              </p>
              {continuityCases.length === 0 ? (
                <div className="rounded-2xl skeuo-well p-6 text-center text-xs text-[var(--fb-ink-muted)]">
                  Tashkilot bo‘yicha ochiq vorislik da’volari mavjud emas.
                </div>
              ) : (
                <ul className="space-y-3">
                  {continuityCases.map((c) => (
                    <li key={c.id} className="rounded-2xl skeuo-well p-4 space-y-2.5">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="text-xs font-bold text-[var(--fb-ink)]">
                            Arizachi: {c.applicant_display_name}
                          </p>
                          <p className="text-[11px] text-[var(--fb-ink-muted)] font-mono">
                            {c.id} · {enumLabel(c.status)}
                          </p>
                        </div>
                        <span className="rounded-full skeuo-badge-recessed px-2.5 py-0.5 text-[11px] font-semibold">
                          {enumLabel(c.status)}
                        </span>
                      </div>
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <input
                          type="text"
                          value={objReasons[c.id] || ""}
                          onChange={(e) =>
                            setObjReasons((prev) => ({ ...prev, [c.id]: e.target.value }))
                          }
                          placeholder="E’tiroz sababi (kamida 15 belgi)..."
                          className="skeuo-input flex-1 rounded-xl px-3 py-2 text-xs"
                        />
                        <button
                          type="button"
                          disabled={busy === `obj:${c.id}` || (objReasons[c.id] || "").trim().length < 15}
                          onClick={() =>
                            void runAction(`obj:${c.id}`, async () => {
                              await objectOrgContinuity(orgId, c.id, objReasons[c.id].trim());
                              setNotice("Vorislik so‘roviga rasmiy e’tiroz kiritildi va u bekor qilindi.");
                            })
                          }
                          className="skeuo-btn-obsidian inline-flex items-center justify-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold disabled:opacity-50"
                        >
                          <ShieldAlert className="h-3.5 w-3.5" />
                          E’tiroz bildirish
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <form onSubmit={handleContinuitySubmit} className="rounded-2xl skeuo-well p-4 space-y-3">
              <div className="flex items-center gap-2">
                <FileUp className="h-4 w-4 text-[#c94f1d]" aria-hidden="true" />
                <h4 className="text-xs font-bold text-[var(--fb-ink)]">
                  Ega mavjud bo‘lmaganda vorislik arizasi topshirish
                </h4>
              </div>
              <p className="text-xs text-[var(--fb-ink-muted)]">
                Tasdiqlangan shaxsiy kontaktingiz va rasmiy PDF dalilingiz Moderator + Komplayens ikki bosqichli tekshiruviga yuboriladi.
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <select
                  aria-label="Tasdiqlangan kontakt"
                  value={contContactId}
                  onChange={(e) => setContContactId(e.target.value)}
                  className="skeuo-input rounded-xl px-3 py-2 text-xs"
                >
                  <option value="">
                    {contacts.length ? "Tasdiqlangan kontaktni tanlang…" : "Tasdiqlangan kontakt topilmadi"}
                  </option>
                  {contacts.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.channel}: {c.masked_destination}
                    </option>
                  ))}
                </select>
                <input
                  aria-label="Vorislik dalili PDF"
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setContFile(e.target.files?.[0] || null)}
                  className="skeuo-input rounded-xl px-3 py-1.5 text-xs"
                />
              </div>
              <textarea
                rows={2}
                value={contNote}
                onChange={(e) => setContNote(e.target.value)}
                placeholder="Rahbar vakolati o‘tishi asosi (kamida 15 belgi)..."
                className="skeuo-input w-full rounded-xl p-2.5 text-xs"
              />
              <button
                type="submit"
                disabled={!mfaSession || !contContactId || busy === "continuity-submit"}
                className="skeuo-btn-obsidian inline-flex items-center gap-1.5 rounded-full px-5 py-2 text-xs font-semibold disabled:opacity-50"
              >
                {busy === "continuity-submit" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Vorislik arizasini yuborish
              </button>
            </form>
          )}
        </div>
      )}

      {tab === "INBOX" && (
        <div className="space-y-3">
          {totalIncoming === 0 ? (
            <div className="rounded-2xl skeuo-well p-6 text-center text-xs text-[var(--fb-ink-muted)]">
              Sizning nomingizga kelgan faol rahbarlik roziligi so‘rovlari yo‘q.
            </div>
          ) : (
            <ul className="space-y-3">
              {[
                ...incomingReq.map((r) => ({ ...r, kind: "requests" as const })),
                ...incomingTrf.map((t) => ({ ...t, kind: "transfers" as const })),
              ].map((item) => {
                const chosenContact = consentContacts[item.case_id] || contacts[0]?.id || "";
                return (
                  <li key={`${item.kind}-${item.case_id}`} className="rounded-2xl skeuo-well p-4 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-xs font-bold text-[var(--fb-ink)]">
                          {item.public_name} —{" "}
                          {item.kind === "requests" ? "Hamrahbar (OWNER) taklifi" : "Rahbarlikni qabul qilish"}
                        </p>
                        <p className="text-[11px] text-[var(--fb-ink-muted)] font-mono">
                          Holat: {enumLabel(item.status)} · Rev {item.current_revision}
                        </p>
                      </div>
                      <ShieldCheck className="h-4 w-4 text-emerald-500" aria-hidden="true" />
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <select
                        aria-label="Tasdiqlash kontakti"
                        value={chosenContact}
                        onChange={(e) =>
                          setConsentContacts((prev) => ({ ...prev, [item.case_id]: e.target.value }))
                        }
                        className="skeuo-input rounded-xl px-3 py-1.5 text-xs"
                      >
                        <option value="">Kontakt tanlang…</option>
                        {contacts.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.channel}: {c.masked_destination}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        disabled={!chosenContact || busy === `acc:${item.case_id}`}
                        onClick={() =>
                          void runAction(`acc:${item.case_id}`, async () => {
                            await respondOwnerCase(item.kind, item.case_id, {
                              expected_revision: item.current_revision,
                              decision: "ACCEPT",
                              contact_id: chosenContact,
                            });
                            setNotice("Rozilik yuborildi — yakuniy tasdiq moderator tekshiruviga o‘tdi.");
                          })
                        }
                        className="skeuo-btn-obsidian rounded-full px-4 py-1.5 text-xs font-semibold disabled:opacity-50"
                      >
                        Rozilik beraman
                      </button>
                      <button
                        type="button"
                        disabled={busy === `dec:${item.case_id}`}
                        onClick={() =>
                          void runAction(`dec:${item.case_id}`, async () => {
                            await respondOwnerCase(item.kind, item.case_id, {
                              expected_revision: item.current_revision,
                              decision: "DECLINE",
                            });
                            setNotice("So‘rov rad etildi.");
                          })
                        }
                        className="skeuo-btn-secondary rounded-full px-4 py-1.5 text-xs font-semibold"
                      >
                        Rad etish
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
