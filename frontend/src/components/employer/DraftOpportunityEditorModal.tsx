"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  Coins,
  FileEdit,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { fetchOpportunityDetail } from "@/lib/api";
import {
  updateOpportunityDraft,
  updateOpportunitySchedule,
  updateOpportunityTerms,
  type DraftShiftInput,
} from "@/lib/employerGovernance";

type EditorTab = "CORE" | "TERMS" | "SCHEDULE";

const WEEKDAYS: Array<{ value: number; label: string }> = [
  { value: 1, label: "Dushanba" },
  { value: 2, label: "Seshanba" },
  { value: 3, label: "Chorshanba" },
  { value: 4, label: "Payshanba" },
  { value: 5, label: "Juma" },
  { value: 6, label: "Shanba" },
  { value: 7, label: "Yakshanba" },
];

const CONTRACT_OPTIONS = [
  { value: "LABOR_PART_TIME", label: "Yarim stavka mehnat shartnomasi (MK)" },
  { value: "FIXED_TERM", label: "Muddatli mehnat shartnomasi" },
  { value: "PART_TIME_CONTRACT", label: "Yarim stavka shartnomasi" },
  { value: "PAID_INTERNSHIP_CONTRACT", label: "To‘lovli amaliyot shartnomasi" },
  { value: "INTERNSHIP_AGREEMENT", label: "Amaliyot shartnomasi" },
  { value: "ACADEMIC_TRIPARTITE", label: "Uch tomonlama OTM shartnomasi" },
  { value: "APPRENTICESHIP", label: "Shogirdlik shartnomasi" },
];

function minutesToTime(mins: number): string {
  const safe = Math.max(0, Math.min(1439, mins));
  const h = Math.floor(safe / 60);
  const m = safe % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
}

function timeToMinutes(hhmm: string): number {
  const [hStr, mStr] = hhmm.split(":");
  const h = Number(hStr);
  const m = Number(mStr);
  if (!Number.isFinite(h) || !Number.isFinite(m)) return 540;
  return h * 60 + m;
}

export default function DraftOpportunityEditorModal({
  isOpen,
  opportunityId,
  onClose,
  onSaved,
}: {
  isOpen: boolean;
  opportunityId: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [tab, setTab] = useState<EditorTab>("CORE");
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [oppKind, setOppKind] = useState<string>("INTERNSHIP");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // CORE (API-078)
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [region, setRegion] = useState("Toshkent shahri");
  const [workMode, setWorkMode] = useState<"ONSITE" | "HYBRID" | "REMOTE">("HYBRID");
  const [eligibility, setEligibility] = useState<
    "ALL_CANDIDATES" | "STUDENTS_ONLY" | "ACADEMIC_TRIPARTITE" | "OPEN"
  >("STUDENTS_ONLY");
  const [capacity, setCapacity] = useState<number>(1);
  const [contractType, setContractType] = useState<string>("INTERNSHIP_AGREEMENT");
  const [programRequired, setProgramRequired] = useState("");

  // TERMS (API-079)
  const [isPaid, setIsPaid] = useState<boolean>(true);
  const [salaryMin, setSalaryMin] = useState<string>("");
  const [salaryMax, setSalaryMax] = useState<string>("");
  const [salaryPeriod, setSalaryPeriod] = useState<"HOUR" | "MONTH">("MONTH");
  const [salaryBasis, setSalaryBasis] = useState<"GROSS" | "NET">("GROSS");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  // SCHEDULE (API-080)
  const [schedulePolicy, setSchedulePolicy] = useState<"STRICT" | "NEGOTIABLE" | "FIXED">("STRICT");
  const [shiftMatchMode, setShiftMatchMode] = useState<"ALL" | "ANY">("ALL");
  const [shifts, setShifts] = useState<DraftShiftInput[]>([]);

  const targetKey = isOpen && opportunityId ? opportunityId : null;
  const loading = Boolean(targetKey && loadedKey !== targetKey);

  useEffect(() => {
    if (!targetKey) return;
    let active = true;
    fetchOpportunityDetail(targetKey)
      .then((detail) => {
        if (!active) return;
        const rev = detail.revision;
        setOppKind(detail.kind || "INTERNSHIP");
        setTitle(rev.title || "");
        setDescription(rev.description || "");
        setRegion(rev.region || "Toshkent shahri");
        setWorkMode(
          rev.work_mode === "ONSITE" || rev.work_mode === "REMOTE" ? rev.work_mode : "HYBRID"
        );
        setEligibility(
          rev.eligibility === "ALL_CANDIDATES" ||
            rev.eligibility === "ACADEMIC_TRIPARTITE" ||
            rev.eligibility === "OPEN"
            ? rev.eligibility
            : "STUDENTS_ONLY"
        );
        setCapacity(detail.capacity || 1);
        setContractType(rev.contract_type || "INTERNSHIP_AGREEMENT");
        setProgramRequired("");

        setIsPaid(detail.kind === "PART_TIME" ? true : Boolean(rev.is_paid));
        setSalaryMin(rev.salary_min !== null ? String(rev.salary_min) : "");
        setSalaryMax(rev.salary_max !== null ? String(rev.salary_max) : "");
        setSalaryPeriod(rev.salary_period === "HOUR" ? "HOUR" : "MONTH");
        setSalaryBasis(rev.salary_basis === "NET" ? "NET" : "GROSS");
        setStartDate("");
        setEndDate("");

        setSchedulePolicy(
          rev.schedule_policy === "NEGOTIABLE" || rev.schedule_policy === "FIXED"
            ? rev.schedule_policy
            : "STRICT"
        );
        setShiftMatchMode("ALL");
        setShifts(
          (detail.shifts || []).map((s) => ({
            weekday: s.weekday,
            start_minute: s.start_minute,
            end_minute: s.end_minute,
            group_code: s.group_code || "GROUP_A",
            timezone: "Asia/Tashkent",
          }))
        );
        setError(null);
        setNotice(null);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Qoralama tafsilotlarini yuklab bo‘lmadi.");
        }
      })
      .finally(() => {
        if (active) setLoadedKey(targetKey);
      });
    return () => {
      active = false;
    };
  }, [targetKey]);

  if (!isOpen || !opportunityId) return null;

  const handleSaveCore = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setError("Sarlavha va batafsil tavsif bo‘sh bo‘lmasligi kerak.");
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await updateOpportunityDraft(opportunityId, {
        title: title.trim(),
        description: description.trim(),
        region: region.trim(),
        work_mode: workMode,
        eligibility,
        capacity: Math.max(1, Number(capacity) || 1),
        contract_type: contractType,
        program_required: programRequired.trim() || null,
      });
      setNotice("Asosiy qoralama ma’lumotlari saqlandi.");
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Saqlashda xatolik yuz berdi.");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveTerms = async (e: React.FormEvent) => {
    e.preventDefault();
    const minVal = salaryMin ? Number(salaryMin) : null;
    const maxVal = salaryMax ? Number(salaryMax) : null;
    if (isPaid && (!minVal || minVal <= 0)) {
      setError("To‘lovli e’lon uchun minimal ish haqi / stipendiya noldan katta bo‘lishi shart.");
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await updateOpportunityTerms(opportunityId, {
        is_paid: oppKind === "PART_TIME" ? true : isPaid,
        salary_min: isPaid ? minVal : null,
        salary_max: isPaid ? maxVal : null,
        currency: "UZS",
        salary_period: isPaid ? salaryPeriod : null,
        salary_basis: isPaid ? salaryBasis : null,
        start_date: startDate || null,
        end_date: endDate || null,
        program_required: programRequired.trim() || null,
      });
      setNotice("To‘lov va muddat shartlari yangilandi.");
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Shartlarni saqlab bo‘lmadi.");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    for (const s of shifts) {
      if (s.end_minute <= s.start_minute) {
        setError("Har bir smenada tugash vaqti boshlanishidan keyin bo‘lishi shart.");
        return;
      }
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await updateOpportunitySchedule(opportunityId, {
        schedule_policy: schedulePolicy,
        shift_match_mode: shiftMatchMode,
        shifts,
      });
      setNotice("Haftalik smena va jadval tartibi yangilandi.");
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Jadvalni saqlab bo‘lmadi.");
    } finally {
      setSaving(false);
    }
  };

  const addShift = () => {
    setShifts((prev) => [
      ...prev,
      { weekday: 1, start_minute: 540, end_minute: 780, group_code: "GROUP_A", timezone: "Asia/Tashkent" },
    ]);
  };

  const updateShift = (idx: number, patch: Partial<DraftShiftInput>) => {
    setShifts((prev) => prev.map((item, i) => (i === idx ? { ...item, ...patch } : item)));
  };

  const removeShift = (idx: number) => {
    setShifts((prev) => prev.filter((_, i) => i !== idx));
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="draft-editor-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
    >
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-[28px] skeuo-card p-6 sm:p-7">
        <div className="flex items-center justify-between border-b border-[var(--fb-border)] pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl skeuo-well text-[#c94f1d] dark:text-[#f47a3d]">
              <FileEdit className="h-4 w-4" aria-hidden="true" />
            </div>
            <div>
              <h2
                id="draft-editor-title"
                className="font-heading text-base sm:text-lg font-bold text-[var(--fb-ink)]"
              >
                Qoralama vakansiyani tahrirlash
              </h2>
              <p className="text-[11px] text-[var(--fb-ink-muted)]">
                Nashr qilishdan oldin asosiy matn, to‘lov shartlari va MK 118 smenalarini sozlang.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Oynani yopish"
            className="flex h-8 w-8 items-center justify-center rounded-xl skeuo-btn-secondary p-0"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Subtabs */}
        <div className="mt-4 flex flex-wrap gap-2">
          {(
            [
              { id: "CORE", label: "Asosiy ma’lumot", icon: FileEdit },
              { id: "TERMS", label: "To‘lov va muddat", icon: Coins },
              { id: "SCHEDULE", label: "Smenalar jadvali", icon: CalendarClock },
            ] as const
          ).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => {
                setTab(id);
                setError(null);
                setNotice(null);
              }}
              className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold transition ${
                tab === id ? "skeuo-btn-obsidian" : "skeuo-btn-secondary"
              }`}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>

        {error && (
          <div
            role="alert"
            className="mt-4 flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {notice && (
          <div className="mt-4 flex items-start gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-800 dark:text-emerald-300">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{notice}</span>
          </div>
        )}

        {loading ? (
          <div className="py-12 flex flex-col items-center gap-3 text-xs text-[var(--fb-ink-muted)]">
            <Loader2 className="h-6 w-6 animate-spin text-[#c94f1d]" />
            <span>Qoralama ma’lumotlari yuklanmoqda...</span>
          </div>
        ) : tab === "CORE" ? (
          <form onSubmit={handleSaveCore} className="mt-4 space-y-4">
            <div>
              <label htmlFor="draft-title" className="block text-xs font-semibold text-[var(--fb-ink)]">
                Lavozim / Amaliyot sarlavhasi
              </label>
              <input
                id="draft-title"
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
              />
            </div>

            <div>
              <label htmlFor="draft-desc" className="block text-xs font-semibold text-[var(--fb-ink)]">
                Tavsif, vazifalar va nomzodga talablar
              </label>
              <textarea
                id="draft-desc"
                rows={4}
                required
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="skeuo-input mt-1 w-full rounded-xl p-3 text-xs"
              />
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="draft-region" className="block text-xs font-semibold text-[var(--fb-ink)]">
                  Hudud / Manzil
                </label>
                <input
                  id="draft-region"
                  type="text"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                />
              </div>
              <div>
                <label htmlFor="draft-workmode" className="block text-xs font-semibold text-[var(--fb-ink)]">
                  Ish rejimi
                </label>
                <select
                  id="draft-workmode"
                  value={workMode}
                  onChange={(e) => setWorkMode(e.target.value as "ONSITE" | "HYBRID" | "REMOTE")}
                  className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                >
                  <option value="ONSITE">Ish joyida (Onsite)</option>
                  <option value="HYBRID">Gibrid (Hybrid)</option>
                  <option value="REMOTE">Masofadan (Remote)</option>
                </select>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label htmlFor="draft-capacity" className="block text-xs font-semibold text-[var(--fb-ink)]">
                  Kvota (o‘rinlar soni)
                </label>
                <input
                  id="draft-capacity"
                  type="number"
                  min={1}
                  max={500}
                  value={capacity}
                  onChange={(e) => setCapacity(Number(e.target.value))}
                  className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                />
              </div>
              <div>
                <label htmlFor="draft-eligibility" className="block text-xs font-semibold text-[var(--fb-ink)]">
                  Nomzod toifasi
                </label>
                <select
                  id="draft-eligibility"
                  value={eligibility}
                  onChange={(e) =>
                    setEligibility(
                      e.target.value as "ALL_CANDIDATES" | "STUDENTS_ONLY" | "ACADEMIC_TRIPARTITE" | "OPEN"
                    )
                  }
                  className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                >
                  <option value="STUDENTS_ONLY">Faqat talabalar</option>
                  <option value="ACADEMIC_TRIPARTITE">Uch tomonlama OTM amaliyoti</option>
                  <option value="ALL_CANDIDATES">Barcha nomzodlar</option>
                </select>
              </div>
              <div>
                <label htmlFor="draft-contract" className="block text-xs font-semibold text-[var(--fb-ink)]">
                  Shartnoma turi
                </label>
                <select
                  id="draft-contract"
                  value={contractType}
                  onChange={(e) => setContractType(e.target.value)}
                  className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                >
                  {CONTRACT_OPTIONS.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label htmlFor="draft-program" className="block text-xs font-semibold text-[var(--fb-ink)]">
                Talab qilinadigan yo‘nalish / mutaxassislik (ixtiyoriy)
              </label>
              <input
                id="draft-program"
                type="text"
                value={programRequired}
                onChange={(e) => setProgramRequired(e.target.value)}
                placeholder="Masalan: Dasturiy injiniring, Moliya"
                className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
              />
            </div>

            <div className="flex justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="skeuo-btn-secondary rounded-full px-4 py-2 text-xs font-semibold"
              >
                Yopish
              </button>
              <button
                type="submit"
                disabled={saving}
                className="skeuo-btn-obsidian inline-flex items-center gap-1.5 rounded-full px-5 py-2 text-xs font-semibold disabled:opacity-50"
              >
                {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Asosiy qismni saqlash
              </button>
            </div>
          </form>
        ) : tab === "TERMS" ? (
          <form onSubmit={handleSaveTerms} className="mt-4 space-y-4">
            <div className="flex items-center gap-2.5 rounded-xl skeuo-well p-3">
              <input
                id="draft-is-paid"
                type="checkbox"
                disabled={oppKind === "PART_TIME"}
                checked={oppKind === "PART_TIME" ? true : isPaid}
                onChange={(e) => setIsPaid(e.target.checked)}
                className="rounded accent-[#c94f1d]"
              />
              <label htmlFor="draft-is-paid" className="text-xs font-semibold text-[var(--fb-ink)]">
                Haq to‘lanadigan o‘rin{" "}
                {oppKind === "PART_TIME" && "(Yarim stavkali ishda majburiy)"}
              </label>
            </div>

            {isPaid && (
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor="draft-sal-min" className="block text-xs font-semibold text-[var(--fb-ink)]">
                    Minimal maosh / stipendiya (UZS)
                  </label>
                  <input
                    id="draft-sal-min"
                    type="number"
                    min={1}
                    value={salaryMin}
                    onChange={(e) => setSalaryMin(e.target.value)}
                    placeholder="2500000"
                    className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                  />
                </div>
                <div>
                  <label htmlFor="draft-sal-max" className="block text-xs font-semibold text-[var(--fb-ink)]">
                    Maksimal maosh (ixtiyoriy, UZS)
                  </label>
                  <input
                    id="draft-sal-max"
                    type="number"
                    min={1}
                    value={salaryMax}
                    onChange={(e) => setSalaryMax(e.target.value)}
                    placeholder="4500000"
                    className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                  />
                </div>
                <div>
                  <label htmlFor="draft-sal-period" className="block text-xs font-semibold text-[var(--fb-ink)]">
                    Hisoblash davri
                  </label>
                  <select
                    id="draft-sal-period"
                    value={salaryPeriod}
                    onChange={(e) => setSalaryPeriod(e.target.value as "HOUR" | "MONTH")}
                    className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                  >
                    <option value="MONTH">Oylik (MONTH)</option>
                    <option value="HOUR">Soatbay (HOUR)</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="draft-sal-basis" className="block text-xs font-semibold text-[var(--fb-ink)]">
                    Soliq asosi
                  </label>
                  <select
                    id="draft-sal-basis"
                    value={salaryBasis}
                    onChange={(e) => setSalaryBasis(e.target.value as "GROSS" | "NET")}
                    className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                  >
                    <option value="GROSS">Brutto (soliqdan oldin)</option>
                    <option value="NET">Netto (qo‘lga tegadigan)</option>
                  </select>
                </div>
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="draft-start-date" className="block text-xs font-semibold text-[var(--fb-ink)]">
                  Boshlanish sanasi (ixtiyoriy)
                </label>
                <input
                  id="draft-start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                />
              </div>
              <div>
                <label htmlFor="draft-end-date" className="block text-xs font-semibold text-[var(--fb-ink)]">
                  Tugash sanasi (ixtiyoriy)
                </label>
                <input
                  id="draft-end-date"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="skeuo-btn-secondary rounded-full px-4 py-2 text-xs font-semibold"
              >
                Yopish
              </button>
              <button
                type="submit"
                disabled={saving}
                className="skeuo-btn-obsidian inline-flex items-center gap-1.5 rounded-full px-5 py-2 text-xs font-semibold disabled:opacity-50"
              >
                {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                To‘lov shartlarini saqlash
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSaveSchedule} className="mt-4 space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="draft-sched-policy" className="block text-xs font-semibold text-[var(--fb-ink)]">
                  Jadval siyosati
                </label>
                <select
                  id="draft-sched-policy"
                  value={schedulePolicy}
                  onChange={(e) =>
                    setSchedulePolicy(e.target.value as "STRICT" | "NEGOTIABLE" | "FIXED")
                  }
                  className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                >
                  <option value="STRICT">Qat’iy jadval (STRICT)</option>
                  <option value="NEGOTIABLE">Kelishiladigan (NEGOTIABLE)</option>
                  <option value="FIXED">Belgilangan (FIXED)</option>
                </select>
              </div>
              <div>
                <label htmlFor="draft-match-mode" className="block text-xs font-semibold text-[var(--fb-ink)]">
                  Smena moslik qoidasi
                </label>
                <select
                  id="draft-match-mode"
                  value={shiftMatchMode}
                  onChange={(e) => setShiftMatchMode(e.target.value as "ALL" | "ANY")}
                  className="skeuo-input mt-1 w-full rounded-xl px-3 py-2 text-xs"
                >
                  <option value="ALL">Guruhdagi barcha smenalar to‘qnashmasin (ALL)</option>
                  <option value="ANY">Kamida bitta smena mos kelsin (ANY)</option>
                </select>
              </div>
            </div>

            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[var(--fb-ink)]">
                  Haftalik smenalar ({shifts.length} ta)
                </span>
                <button
                  type="button"
                  onClick={addShift}
                  className="skeuo-btn-secondary inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Smena qo‘shish
                </button>
              </div>

              {shifts.length === 0 ? (
                <p className="rounded-xl skeuo-well p-4 text-center text-xs text-[var(--fb-ink-muted)]">
                  Hozircha smena kiritilmagan — moslik tekshiruvi uchun smena qo‘shing.
                </p>
              ) : (
                <div className="space-y-2">
                  {shifts.map((sh, idx) => (
                    <div
                      key={`${sh.group_code}-${sh.weekday}-${idx}`}
                      className="grid grid-cols-1 gap-2 rounded-xl skeuo-well p-3 sm:grid-cols-[1fr_110px_110px_90px_auto]"
                    >
                      <select
                        aria-label={`Hafta kuni ${idx + 1}`}
                        value={sh.weekday}
                        onChange={(e) => updateShift(idx, { weekday: Number(e.target.value) })}
                        className="skeuo-input rounded-lg px-2 py-1.5 text-xs"
                      >
                        {WEEKDAYS.map((w) => (
                          <option key={w.value} value={w.value}>
                            {w.label}
                          </option>
                        ))}
                      </select>
                      <input
                        aria-label={`Boshlanish ${idx + 1}`}
                        type="time"
                        value={minutesToTime(sh.start_minute)}
                        onChange={(e) => updateShift(idx, { start_minute: timeToMinutes(e.target.value) })}
                        className="skeuo-input rounded-lg px-2 py-1.5 text-xs"
                      />
                      <input
                        aria-label={`Tugash ${idx + 1}`}
                        type="time"
                        value={minutesToTime(sh.end_minute)}
                        onChange={(e) => updateShift(idx, { end_minute: timeToMinutes(e.target.value) })}
                        className="skeuo-input rounded-lg px-2 py-1.5 text-xs"
                      />
                      <input
                        aria-label={`Guruh ${idx + 1}`}
                        type="text"
                        value={sh.group_code}
                        onChange={(e) => updateShift(idx, { group_code: e.target.value })}
                        placeholder="GROUP_A"
                        className="skeuo-input rounded-lg px-2 py-1.5 text-xs"
                      />
                      <button
                        type="button"
                        onClick={() => removeShift(idx)}
                        aria-label="Smenani o‘chirish"
                        className="flex h-8 w-8 items-center justify-center rounded-lg skeuo-btn-secondary p-0 text-rose-500"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="skeuo-btn-secondary rounded-full px-4 py-2 text-xs font-semibold"
              >
                Yopish
              </button>
              <button
                type="submit"
                disabled={saving}
                className="skeuo-btn-obsidian inline-flex items-center gap-1.5 rounded-full px-5 py-2 text-xs font-semibold disabled:opacity-50"
              >
                {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Smenalarni saqlash
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
