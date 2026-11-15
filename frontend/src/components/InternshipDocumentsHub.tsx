"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Award,
  CheckCircle2,
  Download,
  FileCheck,
  FileText,
  KeyRound,
  Loader2,
  Save,
  ShieldCheck,
  AlertCircle,
  BookOpen,
  Building2,
  GraduationCap,
} from "lucide-react";
import {
  DiaryPassport,
  DocumentDownloadReceipt,
  EImzoCertificateItem,
  EImzoParty,
  EImzoSignatureStamp,
  FinalConclusionDocument,
  StandardizedDiaryWorkspace,
  fetchFinalConclusionDocument,
  fetchMyEImzo,
  fetchStandardizedDiary,
  requestOfficialDocumentDownload,
  saveMyEImzo,
  saveStandardizedDiary,
  signFinalConclusionDocument,
  signInternshipDiary,
} from "@/lib/api";

interface InternshipDocumentsHubProps {
  party: EImzoParty;
  placementId: string;
}

const PARTY_LABELS: Record<EImzoParty, { title: string; badge: string; accent: string }> = {
  CANDIDATE: {
    title: "Talaba (Amaliyotchi) E-Imzo",
    badge: "TALABA TOMONI",
    accent: "text-sky-300 border-sky-500/30 bg-sky-500/10",
  },
  EMPLOYER: {
    title: "Korxona (Mentor / Rahbar) E-Imzo",
    badge: "KORXONA TOMONI",
    accent: "text-emerald-300 border-emerald-500/30 bg-emerald-500/10",
  },
  UNIVERSITY: {
    title: "Universitet (OTM Rahbari) E-Imzo",
    badge: "OTM TOMONI",
    accent: "text-indigo-300 border-indigo-500/30 bg-indigo-500/10",
  },
};

function StampCard({ party, stamp }: { party: EImzoParty; stamp: EImzoSignatureStamp | null }) {
  const meta = PARTY_LABELS[party];
  return (
    <div
      className={`p-3.5 rounded-xl border transition-all ${
        stamp
          ? "bg-emerald-500/[0.06] border-emerald-500/25"
          : "bg-surface-lowest border-white/[0.08]"
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${meta.accent}`}>
          {meta.badge}
        </span>
        {stamp ? (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Tasdiqlangan
          </span>
        ) : (
          <span className="text-[11px] text-zinc-500">Imzolanmagan</span>
        )}
      </div>
      {stamp ? (
        <div className="space-y-1 text-[11px] text-zinc-300">
          <div className="font-semibold text-white truncate">{stamp.signer_name}</div>
          <div className="text-zinc-400 truncate">
            {stamp.signer_position} • {stamp.organization_name}
          </div>
          <div className="font-mono text-[10px] text-emerald-300 break-all">
            Kod: {stamp.verification_code}
          </div>
          <div className="font-mono text-[10px] text-zinc-500 truncate">
            Sertifikat: {stamp.certificate_serial} • {new Date(stamp.signed_at).toLocaleString()}
          </div>
        </div>
      ) : (
        <p className="text-[11px] text-zinc-500 mt-1">
          Ushbu tomonning maxsus E-Imzo tasdig&apos;i kutilmoqda.
        </p>
      )}
    </div>
  );
}

export default function InternshipDocumentsHub({ party, placementId }: InternshipDocumentsHubProps) {
  const [cert, setCert] = useState<EImzoCertificateItem | null>(null);
  const [certForm, setCertForm] = useState({
    full_name: "",
    position_title: "",
    organization_or_university: "",
    stir_or_pinfl: "",
  });
  const [isSavingCert, setIsSavingCert] = useState(false);

  const [diaryWs, setDiaryWs] = useState<StandardizedDiaryWorkspace | null>(null);
  const [conclusionDoc, setConclusionDoc] = useState<FinalConclusionDocument | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Standardized passport edit state
  const [passportForm, setPassportForm] = useState<Partial<DiaryPassport>>({});
  const [isSavingPassport, setIsSavingPassport] = useState(false);

  // Signing states
  const [diarySignNote, setDiarySignNote] = useState("Amaliyot kundaligi yozuvlari standart talablariga muvofiq tekshirildi va tasdiqlandi.");
  const [isSigningDiary, setIsSigningDiary] = useState(false);
  const [isDownloadingDoc, setIsDownloadingDoc] = useState<string | null>(null);
  const [lastReceipt, setLastReceipt] = useState<DocumentDownloadReceipt | null>(null);

  // Document 2 Conclusion separate forms
  const [candForm, setCandForm] = useState({
    student_reflection: "",
    achievements_highlight: "",
    recommended_improvements: "",
  });
  const [empForm, setEmpForm] = useState({
    overall_score: 92,
    employer_verdict: "RECOMMENDED_FOR_HIRE" as "RECOMMENDED_FOR_HIRE" | "SUCCESSFULLY_COMPLETED" | "CONDITIONAL" | "NOT_RECOMMENDED",
    hire_recommendation: true,
    characterization_summary: "",
    discipline: 5,
    technical_skills: 5,
    teamwork: 5,
    initiative: 5,
    communication: 5,
  });
  const [uniForm, setUniForm] = useState({
    academic_score: 90,
    letter_grade: "A" as "A" | "B" | "C" | "D" | "F",
    ects_credits: 4,
    defense_date: new Date().toISOString().split("T")[0],
    academic_verdict: "APPROVED_CREDIT" as "APPROVED_CREDIT" | "REVISION_REQUIRED" | "FAILED",
    academic_summary: "",
  });
  const [isSigningConclusion, setIsSigningConclusion] = useState(false);

  const loadAll = useCallback(async () => {
    if (!placementId) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [eimzoRes, diaryRes, concRes] = await Promise.all([
        fetchMyEImzo(party),
        fetchStandardizedDiary(placementId),
        fetchFinalConclusionDocument(placementId),
      ]);
      const myCert = eimzoRes.certificates[party];
      setCert(myCert);
      if (myCert) {
        setCertForm({
          full_name: myCert.full_name || "",
          position_title: myCert.position_title || "",
          organization_or_university: myCert.organization_or_university || "",
          stir_or_pinfl: myCert.stir_or_pinfl || "",
        });
      }
      setDiaryWs(diaryRes);
      setPassportForm(diaryRes.diary_passport);
      setConclusionDoc(concRes);

      if (concRes.candidate_section) {
        setCandForm({
          student_reflection: concRes.candidate_section.student_reflection || "",
          achievements_highlight: concRes.candidate_section.achievements_highlight || "",
          recommended_improvements: concRes.candidate_section.recommended_improvements || "",
        });
      }
      if (concRes.employer_section) {
        const cr = concRes.employer_section.competency_ratings;
        setEmpForm({
          overall_score: concRes.employer_section.overall_score,
          employer_verdict: concRes.employer_section.employer_verdict,
          hire_recommendation: concRes.employer_section.hire_recommendation,
          characterization_summary: concRes.employer_section.characterization_summary || "",
          discipline: cr?.discipline ?? 5,
          technical_skills: cr?.technical_skills ?? 5,
          teamwork: cr?.teamwork ?? 5,
          initiative: cr?.initiative ?? 5,
          communication: cr?.communication ?? 5,
        });
      }
      if (concRes.university_section) {
        setUniForm({
          academic_score: concRes.university_section.academic_score,
          letter_grade: concRes.university_section.letter_grade,
          ects_credits: concRes.university_section.ects_credits,
          defense_date: concRes.university_section.defense_date || new Date().toISOString().split("T")[0],
          academic_verdict: concRes.university_section.academic_verdict,
          academic_summary: concRes.university_section.academic_summary || "",
        });
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Hujjat ma'lumotlarini yuklashda xatolik.");
    } finally {
      setIsLoading(false);
    }
  }, [party, placementId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch on mount/dependency change; loader resets its loading/error flags
    loadAll();
  }, [loadAll]);

  const handleSaveCert = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingCert(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const updated = await saveMyEImzo({ party, ...certForm });
      setCert(updated);
      setSuccessMsg(`${PARTY_LABELS[party].title} muvaffaqiyatli faollashtirildi (${updated.certificate_serial}).`);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "E-Imzo kalitini saqlashda xatolik.");
    } finally {
      setIsSavingCert(false);
    }
  };

  const handleSavePassport = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingPassport(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const updated = await saveStandardizedDiary(placementId, { diary_passport: passportForm });
      setDiaryWs(updated);
      setSuccessMsg("Standart amaliyot kundaligi pasport rekvizitlari saqlandi.");
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Pasport rekvizitlarini saqlashda xatolik.");
    } finally {
      setIsSavingPassport(false);
    }
  };

  const handleSignDiary = async () => {
    setIsSigningDiary(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await signInternshipDiary(placementId, {
        party,
        scope: "PERIOD",
        confirmation_note: diarySignNote,
      });
      setDiaryWs(res.workspace);
      setSuccessMsg(`1-Hujjat (Kundalik) ${party} E-Imzo bilan tasdiqlandi! Tekshiruv kodi: ${res.stamp.verification_code}`);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Kundalikni E-Imzo bilan tasdiqlashda xatolik.");
    } finally {
      setIsSigningDiary(false);
    }
  };

  const handleSignConclusion = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSigningConclusion(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      let body: Record<string, unknown> = { party };
      if (party === "CANDIDATE") {
        body = { ...body, ...candForm };
      } else if (party === "EMPLOYER") {
        body = {
          ...body,
          overall_score: Number(empForm.overall_score),
          employer_verdict: empForm.employer_verdict,
          hire_recommendation: empForm.hire_recommendation,
          characterization_summary: empForm.characterization_summary,
          competency_ratings: {
            discipline: empForm.discipline,
            technical_skills: empForm.technical_skills,
            teamwork: empForm.teamwork,
            initiative: empForm.initiative,
            communication: empForm.communication,
          },
        };
      } else {
        body = {
          ...body,
          academic_score: Number(uniForm.academic_score),
          letter_grade: uniForm.letter_grade,
          ects_credits: Number(uniForm.ects_credits),
          defense_date: uniForm.defense_date,
          academic_verdict: uniForm.academic_verdict,
          academic_summary: uniForm.academic_summary,
        };
      }
      const res = await signFinalConclusionDocument(placementId, body);
      setConclusionDoc(res.document);
      setSuccessMsg(`2-Hujjat (Yakuniy Amaliyot Xulosasi) ${party} E-Imzo bilan tasdiqlandi! Kod: ${res.stamp.verification_code}`);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Yakuniy xulosani imzolashda xatolik.");
    } finally {
      setIsSigningConclusion(false);
    }
  };

  const handleDownload = async (docType: "DIARY" | "CONCLUSION", format: "PDF" | "JSON") => {
    const key = `${docType}-${format}`;
    setIsDownloadingDoc(key);
    setErrorMsg(null);
    try {
      const receipt = await requestOfficialDocumentDownload(placementId, docType, format);
      setLastReceipt(receipt);
      const link = document.createElement("a");
      link.href = receipt.bff_download_url;
      link.download = receipt.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setSuccessMsg(`${receipt.filename} (${Math.round(receipt.byte_size / 1024 * 10) / 10} KB) yuklab olish boshlandi.`);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Hujjatni yuklab olishda xatolik.");
    } finally {
      setIsDownloadingDoc(null);
    }
  };

  if (isLoading && !diaryWs) {
    return (
      <div className="p-6 rounded-2xl bg-surface-card border border-white/[0.08] flex items-center justify-center gap-3 text-xs text-zinc-400">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        <span>Standart hujjatlar va E-Imzo holati yuklanmoqda...</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/25 text-rose-300 text-xs flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-xs flex items-start gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* 0. Party Dedicated E-Imzo Key Management */}
      <div className="p-5 rounded-2xl bg-surface-card border border-white/[0.08] space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary/15 border border-primary/25 flex items-center justify-center text-primary">
              <KeyRound className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">{PARTY_LABELS[party].title}</h3>
              <p className="text-[11px] text-zinc-400">
                Seriya: <span className="font-mono text-zinc-200">{cert?.certificate_serial || "-"}</span> • Holat:{" "}
                <span className={cert?.active ? "text-emerald-400 font-semibold" : "text-amber-300 font-semibold"}>
                  {cert?.active ? "FAOL (HMAC-SHA256)" : "SOZLANMAGAN (Birinchi imzoda avtomatik faollashadi)"}
                </span>
              </p>
            </div>
          </div>
          <span className={`text-[10px] font-semibold px-2.5 py-1 rounded border ${PARTY_LABELS[party].accent}`}>
            {PARTY_LABELS[party].badge}
          </span>
        </div>

        <form onSubmit={handleSaveCert} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div>
            <label className="block text-[11px] text-zinc-400 mb-1">F.I.Sh. (Imzo egasi)</label>
            <input
              type="text"
              required
              value={certForm.full_name}
              onChange={(e) => setCertForm({ ...certForm, full_name: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-surface-lowest border border-white/[0.08] text-xs text-white focus:border-primary focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-[11px] text-zinc-400 mb-1">Lavozimi / Maqomi</label>
            <input
              type="text"
              required
              value={certForm.position_title}
              onChange={(e) => setCertForm({ ...certForm, position_title: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-surface-lowest border border-white/[0.08] text-xs text-white focus:border-primary focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-[11px] text-zinc-400 mb-1">OTM / Tashkilot nomi</label>
            <input
              type="text"
              required
              value={certForm.organization_or_university}
              onChange={(e) => setCertForm({ ...certForm, organization_or_university: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-surface-lowest border border-white/[0.08] text-xs text-white focus:border-primary focus:outline-none"
            />
          </div>
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-[11px] text-zinc-400 mb-1">STIR / PINFL</label>
              <input
                type="text"
                placeholder="301234567"
                value={certForm.stir_or_pinfl}
                onChange={(e) => setCertForm({ ...certForm, stir_or_pinfl: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-surface-lowest border border-white/[0.08] text-xs text-white focus:border-primary focus:outline-none font-mono"
              />
            </div>
            <button
              type="submit"
              disabled={isSavingCert}
              className="px-3.5 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.1] text-xs font-semibold text-white flex items-center gap-1.5 self-end disabled:opacity-50"
            >
              {isSavingCert ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5 text-primary" />}
              <span>Saqlash</span>
            </button>
          </div>
        </form>
      </div>

      {/* 1. DOCUMENT 1: STANDARDIZED INTERNSHIP DIARY (ONGOING SIGNING + DOWNLOAD) */}
      {diaryWs && (
        <div className="p-5 rounded-2xl bg-surface-card border border-white/[0.08] space-y-5">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/15 text-blue-300 border border-blue-500/25">
                  1-HUJJAT • DOIMIY TASDIQLANADIGAN
                </span>
                <span className="text-[11px] font-mono text-zinc-500">
                  {diaryWs.stats.total_entries} kun • {diaryWs.stats.total_hours}/{diaryWs.stats.normative_hours} soat
                </span>
              </div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-primary" />
                <span>Standart Amaliyot Kundaligi va 3-Tomonlama Doimiy E-Imzo</span>
              </h3>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={isDownloadingDoc !== null}
                onClick={() => handleDownload("DIARY", "PDF")}
                className="px-3.5 py-2 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white flex items-center gap-1.5 shadow-sm shadow-primary/20 disabled:opacity-50"
              >
                {isDownloadingDoc === "DIARY-PDF" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                <span>Kundalik PDF Yuklab Olish</span>
              </button>
              <button
                type="button"
                disabled={isDownloadingDoc !== null}
                onClick={() => handleDownload("DIARY", "JSON")}
                className="px-3 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.1] text-xs font-semibold text-zinc-200 flex items-center gap-1.5 disabled:opacity-50"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>JSON</span>
              </button>
            </div>
          </div>

          {/* Standardized Diary Passport Form */}
          <form onSubmit={handleSavePassport} className="p-4 rounded-xl bg-surface-lowest border border-white/[0.06] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-zinc-200 uppercase tracking-wider">
                Standart Kundalik Pasporti (OTM / Fakultet / Shartnoma / Me&apos;yoriy Soat)
              </span>
              <button
                type="submit"
                disabled={isSavingPassport}
                className="px-3 py-1.5 rounded-lg bg-surface-high hover:bg-white/[0.08] border border-white/[0.1] text-xs font-semibold text-white flex items-center gap-1.5 disabled:opacity-50"
              >
                {isSavingPassport ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3 text-emerald-400" />}
                <span>Pasportni Yangilash</span>
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <div>
                <label className="block text-[10px] text-zinc-400 mb-1">OTM Nomi</label>
                <input
                  type="text"
                  value={passportForm.otm_name || ""}
                  onChange={(e) => setPassportForm({ ...passportForm, otm_name: e.target.value })}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-white text-xs"
                />
              </div>
              <div>
                <label className="block text-[10px] text-zinc-400 mb-1">Fakultet / Kafedra</label>
                <input
                  type="text"
                  value={passportForm.faculty_name || ""}
                  onChange={(e) => setPassportForm({ ...passportForm, faculty_name: e.target.value })}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-white text-xs"
                />
              </div>
              <div>
                <label className="block text-[10px] text-zinc-400 mb-1">Guruh / Kurs</label>
                <input
                  type="text"
                  value={passportForm.academic_group || ""}
                  onChange={(e) => setPassportForm({ ...passportForm, academic_group: e.target.value })}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-white text-xs"
                />
              </div>
              <div>
                <label className="block text-[10px] text-zinc-400 mb-1">Amaliyot Turi</label>
                <select
                  value={passportForm.internship_type || "ISHLAB_CHIQARISH"}
                  onChange={(e) =>
                    setPassportForm({
                      ...passportForm,
                      internship_type: e.target.value as DiaryPassport["internship_type"],
                    })
                  }
                  className="w-full px-2.5 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-white text-xs"
                >
                  <option value="ISHLAB_CHIQARISH">Ishlab chiqarish amaliyoti</option>
                  <option value="MALAKA">Malakaviy amaliyot</option>
                  <option value="DIPLOM_OLDI">Diplom oldi amaliyoti</option>
                  <option value="TANISHUV">Tanishuv amaliyoti</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] text-zinc-400 mb-1">Korxona Bo&apos;limi</label>
                <input
                  type="text"
                  value={passportForm.host_department || ""}
                  onChange={(e) => setPassportForm({ ...passportForm, host_department: e.target.value })}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-white text-xs"
                />
              </div>
              <div>
                <label className="block text-[10px] text-zinc-400 mb-1">Shartnoma Raqami</label>
                <input
                  type="text"
                  value={passportForm.contract_number || ""}
                  onChange={(e) => setPassportForm({ ...passportForm, contract_number: e.target.value })}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-white text-xs font-mono"
                />
              </div>
              <div>
                <label className="block text-[10px] text-zinc-400 mb-1">Korxona STIR</label>
                <input
                  type="text"
                  value={passportForm.host_org_stir || ""}
                  onChange={(e) => setPassportForm({ ...passportForm, host_org_stir: e.target.value })}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-white text-xs font-mono"
                />
              </div>
              <div>
                <label className="block text-[10px] text-zinc-400 mb-1">Me&apos;yoriy Soat</label>
                <input
                  type="number"
                  min={16}
                  max={2000}
                  value={passportForm.normative_hours ?? 144}
                  onChange={(e) => setPassportForm({ ...passportForm, normative_hours: Number(e.target.value) })}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-surface border border-white/[0.08] text-white text-xs font-mono"
                />
              </div>
            </div>
          </form>

          {/* 3-Party Live Diary Stamps + Continuous Sign Trigger */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <StampCard party="CANDIDATE" stamp={diaryWs.signatures.CANDIDATE} />
            <StampCard party="EMPLOYER" stamp={diaryWs.signatures.EMPLOYER} />
            <StampCard party="UNIVERSITY" stamp={diaryWs.signatures.UNIVERSITY} />
          </div>

          <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center p-3.5 rounded-xl bg-primary/[0.06] border border-primary/20">
            <input
              type="text"
              value={diarySignNote}
              onChange={(e) => setDiarySignNote(e.target.value)}
              placeholder="Davriy E-Imzo tasdiq izohi..."
              className="flex-1 px-3 py-2 rounded-lg bg-surface-lowest border border-white/[0.08] text-xs text-white focus:border-primary focus:outline-none"
            />
            <button
              type="button"
              disabled={isSigningDiary}
              onClick={handleSignDiary}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50 whitespace-nowrap"
            >
              {isSigningDiary ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
              <span>1-Hujjatni {party} E-Imzo bilan Tasdiqlash</span>
            </button>
          </div>
        </div>
      )}

      {/* 2. DOCUMENT 2: FINAL INTERNSHIP CONCLUSION (SEPARATE END-OF-INTERNSHIP SIGNING + DOWNLOAD) */}
      {conclusionDoc && (
        <div className="p-5 rounded-2xl bg-surface-card border border-white/[0.08] space-y-5">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/25">
                  2-HUJJAT • YAKUNIY ALOHIDA TASDIQLANADIGAN
                </span>
                <span className="text-[11px] font-mono text-zinc-400">
                  {conclusionDoc.signed_parties_count}/3 tomon imzolagan ({conclusionDoc.overall_status})
                </span>
              </div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Award className="w-4 h-4 text-purple-400" />
                <span>Yakuniy Amaliyot Xulosasi va Uch Tomonlama Alohida E-Imzo</span>
              </h3>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={isDownloadingDoc !== null}
                onClick={() => handleDownload("CONCLUSION", "PDF")}
                className="px-3.5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                {isDownloadingDoc === "CONCLUSION-PDF" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                <span>Yakuniy Xulosa PDF Yuklab Olish</span>
              </button>
              <button
                type="button"
                disabled={isDownloadingDoc !== null}
                onClick={() => handleDownload("CONCLUSION", "JSON")}
                className="px-3 py-2 rounded-lg bg-surface hover:bg-surface-high border border-white/[0.1] text-xs font-semibold text-zinc-200 flex items-center gap-1.5 disabled:opacity-50"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>JSON</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <StampCard party="EMPLOYER" stamp={conclusionDoc.signatures.EMPLOYER} />
            <StampCard party="UNIVERSITY" stamp={conclusionDoc.signatures.UNIVERSITY} />
            <StampCard party="CANDIDATE" stamp={conclusionDoc.signatures.CANDIDATE} />
          </div>

          {/* Current Party Separate Final Conclusion Form */}
          <form onSubmit={handleSignConclusion} className="p-4 rounded-xl bg-surface-lowest border border-white/[0.08] space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white flex items-center gap-2">
                {party === "EMPLOYER" ? <Building2 className="w-4 h-4 text-emerald-400" /> : party === "UNIVERSITY" ? <GraduationCap className="w-4 h-4 text-indigo-400" /> : <FileCheck className="w-4 h-4 text-sky-400" />}
                <span>Sizning Tomoningiz Yakuniy Xulosasi ({PARTY_LABELS[party].badge})</span>
              </span>
            </div>

            {party === "CANDIDATE" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="md:col-span-2">
                  <label className="block text-[11px] text-zinc-400 mb-1">Talabaning yakuniy o&apos;zini baholashi va hisoboti *</label>
                  <textarea
                    required
                    rows={3}
                    value={candForm.student_reflection}
                    onChange={(e) => setCandForm({ ...candForm, student_reflection: e.target.value })}
                    placeholder="Amaliyot davomida o'zlashtirilgan bilimlar, loyihalar va yakuniy natijalar haqida..."
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Asosiy yutuqlar</label>
                  <input
                    type="text"
                    value={candForm.achievements_highlight}
                    onChange={(e) => setCandForm({ ...candForm, achievements_highlight: e.target.value })}
                    placeholder="Masalan: ERP modulini ishga tushirish, 12 ta PR..."
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Taklif va mulohazalar</label>
                  <input
                    type="text"
                    value={candForm.recommended_improvements}
                    onChange={(e) => setCandForm({ ...candForm, recommended_improvements: e.target.value })}
                    placeholder="Amaliyot jarayonini takomillashtirish bo'yicha taklif..."
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-xs text-white"
                  />
                </div>
              </div>
            )}

            {party === "EMPLOYER" && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Korxona yakuniy balli (0-100)</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={empForm.overall_score}
                    onChange={(e) => setEmpForm({ ...empForm, overall_score: Number(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Korxona yakuniy qarori</label>
                  <select
                    value={empForm.employer_verdict}
                    onChange={(e) =>
                      setEmpForm({
                        ...empForm,
                        employer_verdict: e.target.value as typeof empForm.employer_verdict,
                      })
                    }
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-white"
                  >
                    <option value="RECOMMENDED_FOR_HIRE">Ishga qabul qilishga tavsiya etiladi</option>
                    <option value="SUCCESSFULLY_COMPLETED">Muvaffaqiyatli yakunladi</option>
                    <option value="CONDITIONAL">Shartli / Qisman yakunladi</option>
                    <option value="NOT_RECOMMENDED">Tavsiya etilmaydi</option>
                  </select>
                </div>
                <div className="flex items-center gap-2 pt-5">
                  <input
                    id="hire-rec"
                    type="checkbox"
                    checked={empForm.hire_recommendation}
                    onChange={(e) => setEmpForm({ ...empForm, hire_recommendation: e.target.checked })}
                    className="w-4 h-4 rounded border-white/[0.1]"
                  />
                  <label htmlFor="hire-rec" className="text-xs text-zinc-200 cursor-pointer">
                    Shtatga ishga taklif etishga tavsiya
                  </label>
                </div>
                <div className="sm:col-span-3">
                  <label className="block text-[11px] text-zinc-400 mb-1">Korxona yakuniy tavsifnomasi *</label>
                  <textarea
                    required
                    rows={3}
                    value={empForm.characterization_summary}
                    onChange={(e) => setEmpForm({ ...empForm, characterization_summary: e.target.value })}
                    placeholder="Talabaning mehnat intizomi, texnik saviyasi va jamoaviy ishlashi bo'yicha rasmiy tavsifnoma..."
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-white"
                  />
                </div>
              </div>
            )}

            {party === "UNIVERSITY" && (
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Akademik ball (0-100)</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={uniForm.academic_score}
                    onChange={(e) => setUniForm({ ...uniForm, academic_score: Number(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Baho / Kredit (ECTS)</label>
                  <div className="flex gap-2">
                    <select
                      value={uniForm.letter_grade}
                      onChange={(e) => setUniForm({ ...uniForm, letter_grade: e.target.value as typeof uniForm.letter_grade })}
                      className="w-20 px-2 py-2 rounded-lg bg-surface border border-white/[0.08] text-white font-bold"
                    >
                      {["A", "B", "C", "D", "F"].map((g) => (
                        <option key={g} value={g}>{g}</option>
                      ))}
                    </select>
                    <input
                      type="number"
                      step={0.5}
                      min={0.5}
                      max={30}
                      value={uniForm.ects_credits}
                      onChange={(e) => setUniForm({ ...uniForm, ects_credits: Number(e.target.value) })}
                      className="flex-1 px-2.5 py-2 rounded-lg bg-surface border border-white/[0.08] text-white font-mono"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">Himoya sanasi</label>
                  <input
                    type="date"
                    value={uniForm.defense_date}
                    onChange={(e) => setUniForm({ ...uniForm, defense_date: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-zinc-400 mb-1">OTM yakuniy qarori</label>
                  <select
                    value={uniForm.academic_verdict}
                    onChange={(e) =>
                      setUniForm({
                        ...uniForm,
                        academic_verdict: e.target.value as typeof uniForm.academic_verdict,
                      })
                    }
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-white"
                  >
                    <option value="APPROVED_CREDIT">Kredit qabul qilindi</option>
                    <option value="REVISION_REQUIRED">Qayta topshirish talab etiladi</option>
                    <option value="FAILED">Qabul qilinmadi</option>
                  </select>
                </div>
                <div className="sm:col-span-4">
                  <label className="block text-[11px] text-zinc-400 mb-1">Kafedra / OTM rahbari yakuniy xulosasi *</label>
                  <textarea
                    required
                    rows={3}
                    value={uniForm.academic_summary}
                    onChange={(e) => setUniForm({ ...uniForm, academic_summary: e.target.value })}
                    placeholder="Talabaning amaliyot dasturini bajarishi va himoya natijalari bo'yicha rasmiy akademik xulosa..."
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-white/[0.08] text-white"
                  />
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isSigningConclusion}
                className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                {isSigningConclusion ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                <span>2-Hujjat (Yakuniy Xulosa)ni {party} E-Imzo bilan Imzolash</span>
              </button>
            </div>
          </form>

          {/* Read-only preview of other parties' finalized sections */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
            <div className="p-3 rounded-xl bg-surface border border-white/[0.06]">
              <div className="font-semibold text-emerald-300 mb-1">Korxona Bahosi</div>
              {conclusionDoc.employer_section ? (
                <div className="text-zinc-300 space-y-1">
                  <div>Ball: <strong className="text-white">{conclusionDoc.employer_section.overall_score}/100</strong> • {conclusionDoc.employer_section.employer_verdict}</div>
                  <p className="text-zinc-400 line-clamp-3">{conclusionDoc.employer_section.characterization_summary}</p>
                </div>
              ) : <div className="text-zinc-500">Hali kiritilmagan</div>}
            </div>
            <div className="p-3 rounded-xl bg-surface border border-white/[0.06]">
              <div className="font-semibold text-indigo-300 mb-1">Universitet Xulosasi</div>
              {conclusionDoc.university_section ? (
                <div className="text-zinc-300 space-y-1">
                  <div>Baho: <strong className="text-white">{conclusionDoc.university_section.academic_score}/100 ({conclusionDoc.university_section.letter_grade})</strong> • {conclusionDoc.university_section.ects_credits} ECTS</div>
                  <p className="text-zinc-400 line-clamp-3">{conclusionDoc.university_section.academic_summary}</p>
                </div>
              ) : <div className="text-zinc-500">Hali kiritilmagan</div>}
            </div>
            <div className="p-3 rounded-xl bg-surface border border-white/[0.06]">
              <div className="font-semibold text-sky-300 mb-1">Talaba Hisoboti</div>
              {conclusionDoc.candidate_section ? (
                <p className="text-zinc-300 line-clamp-4">{conclusionDoc.candidate_section.student_reflection}</p>
              ) : <div className="text-zinc-500">Hali kiritilmagan</div>}
            </div>
          </div>

          {lastReceipt && (
            <div className="p-3 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/20 flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="text-emerald-300 font-mono truncate">
                Yuklangan fayl: {lastReceipt.filename} (SHA-256: {lastReceipt.sha256.slice(0, 16)}...)
              </span>
              <a
                href={lastReceipt.bff_download_url}
                download={lastReceipt.filename}
                className="px-3 py-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 font-semibold border border-emerald-500/30"
              >
                Qayta Yuklab Olish
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
