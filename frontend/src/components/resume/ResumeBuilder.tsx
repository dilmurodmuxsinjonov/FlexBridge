"use client";

import { useId, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Briefcase,
  Check,
  CheckCircle2,
  Eye,
  GraduationCap,
  Languages as LanguagesIcon,
  Loader2,
  Pencil,
  Plus,
  Trash2,
  Trophy,
  UserRound,
  X,
} from "lucide-react";
import {
  fetchCandidateProfile,
  uploadCandidatePdfFile,
  fetchCandidateResumeDetails,
  saveCandidateResumeDetails,
  setCandidateVisibility,
  updateCandidateProfile,
  type CandidateAchievementItem,
  type CandidateLanguageItem,
  type CandidateWorkExperienceItem,
  type CandidateVisibility,
  type EmployerResumeView,
} from "@/lib/api";
import { ACHIEVEMENT_LABELS, LANGUAGE_LEVEL_LABELS, WORK_MODE_LABELS, WORK_TYPE_LABELS, toBackendResume } from "@/lib/resumeContract";
import { useAsyncData } from "@/lib/useAsyncData";
import ResumePreview from "@/components/ResumePreview";
import {
  STEPS,
  completeness,
  describeSaveError,
  emptyAchievement,
  emptyExperience,
  experienceMonths,
  fromMonth,
  toDraft,
  toMonth,
  validateAchievement,
  validateExperience,
  validateStep,
  type Draft,
  type Errors,
  type StepId,
} from "./resumeDraft";

const REGIONS = [
  "Toshkent shahri", "Toshkent viloyati", "Andijon", "Buxoro", "Farg‘ona", "Jizzax", "Xorazm", "Namangan",
  "Navoiy", "Qashqadaryo", "Qoraqalpog‘iston", "Samarqand", "Sirdaryo", "Surxondaryo",
];
const COMMON_LANGUAGES = ["O‘zbek tili", "Rus tili", "Ingliz tili", "Qoraqalpoq tili", "Turk tili", "Nemis tili", "Koreys tili", "Arab tili", "Xitoy tili"];
const STEP_ICONS = { basics: UserRound, education: GraduationCap, experience: Briefcase, languages: LanguagesIcon, extras: Trophy, review: Eye } as const;

const inputCls = "skeuo-input w-full rounded-xl px-3.5 py-2.5 text-sm";

function Field({ id, label, hint, error, optional, children }: { id: string; label: string; hint?: string; error?: string; optional?: boolean; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-[var(--fb-ink)]">
        {label} {optional && <span className="font-normal text-[var(--fb-ink-muted)]">(ixtiyoriy)</span>}
      </label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="mt-1 text-xs font-medium text-rose-700 dark:text-rose-300">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="mt-1 text-xs text-[var(--fb-ink-muted)]">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

function ChipInput({ id, values, onChange, placeholder, max = 10 }: { id: string; values: string[]; onChange: (v: string[]) => void; placeholder: string; max?: number }) {
  const [text, setText] = useState("");
  const add = () => {
    const v = text.trim().replace(/,$/, "");
    if (v && !values.includes(v) && values.length < max) onChange([...values, v]);
    setText("");
  };
  return (
    <div className="skeuo-input w-full rounded-xl px-2 py-1.5 flex flex-wrap items-center gap-1.5 focus-within:ring-[3px] focus-within:ring-[var(--fb-focus)] focus-within:border-[var(--fb-accent)]">
      {values.map((v) => (
        <span key={v} className="inline-flex items-center gap-1 rounded-full bg-[var(--fb-well-deep)] px-2.5 py-1 text-xs font-medium text-[var(--fb-ink)]">
          {v}
          <button type="button" onClick={() => onChange(values.filter((x) => x !== v))} aria-label={`${v} ni olib tashlash`} className="text-[var(--fb-ink-muted)] hover:text-[var(--fb-ink)]">
            <X className="h-3 w-3" aria-hidden="true" />
          </button>
        </span>
      ))}
      <input
        id={id}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            add();
          } else if (e.key === "Backspace" && !text && values.length) {
            onChange(values.slice(0, -1));
          }
        }}
        onBlur={add}
        placeholder={values.length >= max ? "" : placeholder}
        disabled={values.length >= max}
        data-chip-input="true"
        className="min-w-[8rem] flex-1 bg-transparent px-1.5 py-1 text-sm outline-none"
      />
    </div>
  );
}

/**
 * Step-by-step resume builder for students (Issue #241): one topic per step,
 * labelled fields with examples, list items edited in cards, saving on every
 * step, and a final "how employers see me" review with search visibility.
 */
export default function ResumeBuilder() {
  const ids = useId();
  const loaded = useAsyncData("resume-builder", async () => {
    const [profile, resume] = await Promise.all([fetchCandidateProfile().catch(() => null), fetchCandidateResumeDetails()]);
    return { profile, resume };
  });

  const [draft, setDraft] = useState<Draft | null>(null);
  if (loaded.data && draft === null) setDraft(toDraft(loaded.data.profile, loaded.data.resume));

  const [visibility, setVisibility] = useState<CandidateVisibility | null>(null);
  const currentVisibility: CandidateVisibility = visibility ?? (loaded.data?.profile?.visibility === "EMPLOYERS" ? "EMPLOYERS" : "PRIVATE");

  const [step, setStep] = useState<StepId>("basics");
  const [errors, setErrors] = useState<Errors>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  const [editingExp, setEditingExp] = useState<{ index: number | null; item: CandidateWorkExperienceItem } | null>(null);
  const [expErrors, setExpErrors] = useState<Errors>({});
  const [editingAch, setEditingAch] = useState<{ index: number | null; item: CandidateAchievementItem } | null>(null);
  const [achErrors, setAchErrors] = useState<Errors>({});
  const [cvState, setCvState] = useState<{ busy: boolean; message: string | null }>({ busy: false, message: null });

  if (loaded.isLoading && !draft) {
    return (
      <div className="skeuo-card rounded-[24px] p-8 flex items-center justify-center gap-2 text-sm text-[var(--fb-ink-secondary)]">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Rezyume yuklanmoqda…
      </div>
    );
  }
  if (!draft) {
    return (
      <div role="alert" className="skeuo-card rounded-[24px] p-6 flex items-start gap-2.5 text-sm text-rose-700 dark:text-rose-300">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>
          Rezyumeni yuklab bo‘lmadi.{" "}
          <button type="button" onClick={() => void loaded.reload()} className="font-semibold underline underline-offset-2">
            Qayta urinish
          </button>
        </span>
      </div>
    );
  }

  const d = draft;
  const update = (patch: Partial<Draft>) => {
    setDraft({ ...d, ...patch });
    setDirty(true);
  };
  const setPrefs = (patch: Partial<Draft["prefs"]>) => update({ prefs: { ...d.prefs, ...patch } });
  const setEdu = (patch: Partial<Draft["education"]>) => update({ education: { ...d.education, ...patch } });
  const done = completeness(d);
  const doneCount = Object.values(done).filter(Boolean).length;
  const stepIndex = STEPS.findIndex((s) => s.id === step);

  const save = async (): Promise<boolean> => {
    const stepErrors = validateStep(step, d);
    setErrors(stepErrors);
    if (Object.keys(stepErrors).length) return false;
    if (!dirty) return true;
    setSaving(true);
    setSaveError(null);
    try {
      const profile = loaded.data?.profile;
      const months = experienceMonths(d.experience);
      if (!profile || d.headline !== (profile.headline ?? "") || d.region !== (profile.region ?? "") || months !== (profile.experience_months ?? 0)) {
        await updateCandidateProfile({ headline: d.headline.trim(), region: d.region || undefined, experience_months: months });
      }
      await saveCandidateResumeDetails({
        work_experiences: d.experience,
        languages: d.languages,
        achievements: d.achievements,
        education_details: d.education,
        career_preferences: d.prefs,
      });
      setDirty(false);
      setSavedAt(new Date().toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit" }));
      return true;
    } catch (err) {
      setSaveError(describeSaveError(err));
      return false;
    } finally {
      setSaving(false);
    }
  };

  const goTo = async (target: StepId) => {
    if (target === step) return;
    if (editingExp || editingAch) {
      setSaveError("Avval ochiq kartochkani saqlang yoki bekor qiling.");
      return;
    }
    if (await save()) {
      setStep(target);
      setErrors({});
    }
  };

  const commitExperience = () => {
    if (!editingExp) return;
    const e = validateExperience(editingExp.item);
    setExpErrors(e);
    if (Object.keys(e).length) return;
    const list = [...d.experience];
    if (editingExp.index === null) list.unshift(editingExp.item);
    else list[editingExp.index] = editingExp.item;
    update({ experience: list });
    setEditingExp(null);
  };
  const commitAchievement = () => {
    if (!editingAch) return;
    const e = validateAchievement(editingAch.item);
    setAchErrors(e);
    if (Object.keys(e).length) return;
    const list = [...d.achievements];
    if (editingAch.index === null) list.unshift(editingAch.item);
    else list[editingAch.index] = editingAch.item;
    update({ achievements: list });
    setEditingAch(null);
  };

  const err = (k: string) => errors[k];
  const describedBy = (id: string, has: boolean) => ({ "aria-invalid": has || undefined, "aria-describedby": has ? `${id}-error` : `${id}-hint` });

  const preview = toBackendResume({
    work_experiences: d.experience,
    achievements: d.achievements,
    languages: d.languages,
    education_details: d.education,
    career_preferences: d.prefs,
  }) as unknown as EmployerResumeView;

  const exp = editingExp;
  const setExp = (patch: Partial<CandidateWorkExperienceItem>) => exp && setEditingExp({ ...exp, item: { ...exp.item, ...patch } });
  const ach = editingAch;
  const setAch = (patch: Partial<CandidateAchievementItem>) => ach && setEditingAch({ ...ach, item: { ...ach.item, ...patch } });

  return (
    <section className="skeuo-card rounded-[24px] p-4 sm:p-6 flex flex-col gap-5" aria-labelledby={`${ids}-title`}>
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <h2 id={`${ids}-title`} className="font-heading text-xl font-bold text-[var(--fb-ink)]">
            Rezyumem
          </h2>
          <p className="text-sm text-[var(--fb-ink-secondary)]">Bo‘limlarni ketma-ket to‘ldiring. Har bir qadamda o‘zgarishlar avtomatik saqlanadi.</p>
        </div>
        <div className="text-sm text-[var(--fb-ink-secondary)] shrink-0" aria-live="polite">
          {saving ? (
            <span className="inline-flex items-center gap-1.5">
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> Saqlanmoqda…
            </span>
          ) : savedAt && !dirty ? (
            <span className="inline-flex items-center gap-1.5 text-emerald-700 dark:text-emerald-300">
              <Check className="h-3.5 w-3.5" aria-hidden="true" /> Saqlandi · {savedAt}
            </span>
          ) : (
            <span>
              Tayyorlik: <strong className="text-[var(--fb-ink)]">{doneCount}/5</strong> bo‘lim
            </span>
          )}
        </div>
      </div>

      <nav aria-label="Rezyume bo‘limlari" className="-mx-1 overflow-x-auto no-scrollbar">
        <ol className="flex min-w-max gap-1.5 px-1">
          {STEPS.map((s, i) => {
            const Icon = STEP_ICONS[s.id];
            const active = s.id === step;
            const complete = s.id !== "review" && done[s.id as keyof typeof done];
            return (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => void goTo(s.id)}
                  aria-current={active ? "step" : undefined}
                  className={`flex items-center gap-2 rounded-xl px-3 py-2 text-left text-sm transition-colors ${
                    active ? "skeuo-well ring-1 ring-[var(--fb-accent)] text-[var(--fb-ink)]" : "text-[var(--fb-ink-secondary)] hover:bg-[var(--fb-well)]"
                  }`}
                >
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      complete ? "bg-emerald-500 text-white" : active ? "bg-[var(--fb-accent)] text-white" : "bg-[var(--fb-well-deep)] text-[var(--fb-ink-secondary)]"
                    }`}
                  >
                    {complete ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : i + 1}
                  </span>
                  <span className="font-semibold whitespace-nowrap">{s.title}</span>
                  <Icon className="hidden md:block h-3.5 w-3.5 opacity-60" aria-hidden="true" />
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      <div>
        <h3 className="font-heading text-lg font-bold text-[var(--fb-ink)]">
          {stepIndex + 1}. {STEPS[stepIndex].title}
        </h3>
        <p className="text-sm text-[var(--fb-ink-secondary)]">{STEPS[stepIndex].hint}</p>
      </div>

      {saveError && (
        <div role="alert" className="flex items-start gap-2.5 rounded-2xl border border-rose-500/25 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {saveError}
        </div>
      )}

      {step === "basics" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <Field id={`${ids}-headline`} label="Kasbiy sarlavha" hint="Masalan: «Python dasturchi — amaliyot izlayapman» yoki «Buxgalteriya talabasi, Excel». Ish beruvchi birinchi shuni ko‘radi." error={err("headline")}>
              <input id={`${ids}-headline`} value={d.headline} maxLength={120} onChange={(e) => update({ headline: e.target.value })} className={inputCls} {...describedBy(`${ids}-headline`, Boolean(err("headline")))} />
            </Field>
          </div>
          <div className="md:col-span-2">
            <Field id={`${ids}-about`} label="O‘zingiz haqingizda" hint={`2–4 jumla: nimani yaxshi bilasiz, nimaga qiziqasiz, qanday ish qidiryapsiz. ${d.prefs.career_objective.length}/600`}>
              <textarea
                id={`${ids}-about`}
                rows={4}
                maxLength={600}
                value={d.prefs.career_objective}
                onChange={(e) => setPrefs({ career_objective: e.target.value })}
                placeholder="Men TATU 3-kurs talabasiman. Python va SQL bilan kichik loyihalar qilganman. Haftasiga 20 soat ishlay oladigan backend amaliyotini qidiryapman."
                className={inputCls}
              />
            </Field>
          </div>
          <div className="md:col-span-2">
            <Field id={`${ids}-roles`} label="Qanday lavozimlarni qidiryapsiz?" hint="Har birini yozib Enter bosing (10 tagacha).">
              <ChipInput id={`${ids}-roles`} values={d.prefs.desired_roles} onChange={(v) => setPrefs({ desired_roles: v })} placeholder="Masalan: Backend amaliyotchi" />
            </Field>
          </div>
          <Field id={`${ids}-region`} label="Qaysi hududda ishlaysiz?">
            <select id={`${ids}-region`} value={d.region} onChange={(e) => update({ region: e.target.value })} className={inputCls}>
              <option value="">Tanlang</option>
              {REGIONS.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </Field>
          <Field id={`${ids}-hours`} label="Haftasiga necha soat ishlay olasiz?" hint="Dars jadvalingizga mos bo‘lsin. Talabalar uchun odatda 15–25 soat." error={err("hours")}>
            <input id={`${ids}-hours`} type="number" min={0} max={60} value={d.prefs.preferred_weekly_hours} onChange={(e) => setPrefs({ preferred_weekly_hours: Number(e.target.value) })} className={inputCls} {...describedBy(`${ids}-hours`, Boolean(err("hours")))} />
          </Field>
          <fieldset className="md:col-span-2">
            <legend className="mb-1.5 text-sm font-semibold text-[var(--fb-ink)]">Ish formati</legend>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {Object.entries(WORK_MODE_LABELS).map(([value, label]) => (
                <label
                  key={value}
                  className={`cursor-pointer rounded-xl border px-3 py-2.5 text-center text-sm font-semibold ${
                    d.prefs.work_mode === value ? "border-[var(--fb-accent)] bg-orange-500/10 text-[var(--fb-ink)]" : "skeuo-well text-[var(--fb-ink-secondary)]"
                  }`}
                >
                  <input type="radio" name={`${ids}-mode`} value={value} checked={d.prefs.work_mode === value} onChange={() => setPrefs({ work_mode: value })} className="sr-only" />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
          <Field id={`${ids}-salary`} label="Kutilayotgan oylik (so‘m)" optional hint="Bo‘sh qoldirsangiz «kelishiladi» deb hisoblanadi.">
            <input id={`${ids}-salary`} type="number" min={0} step={100000} value={d.prefs.expected_stipend_uzs || ""} onChange={(e) => setPrefs({ expected_stipend_uzs: Number(e.target.value) || 0 })} placeholder="3 000 000" className={inputCls} />
          </Field>
        </div>
      )}

      {step === "education" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <Field id={`${ids}-uni`} label="Oliy ta’lim muassasasi">
              <input id={`${ids}-uni`} value={d.education.university_name} onChange={(e) => setEdu({ university_name: e.target.value })} placeholder="Masalan: Toshkent axborot texnologiyalari universiteti" className={inputCls} />
            </Field>
          </div>
          <Field id={`${ids}-faculty`} label="Fakultet">
            <input id={`${ids}-faculty`} value={d.education.faculty} onChange={(e) => setEdu({ faculty: e.target.value })} placeholder="Kompyuter injiniringi" className={inputCls} />
          </Field>
          <Field id={`${ids}-major`} label="Yo‘nalish (mutaxassislik)">
            <input id={`${ids}-major`} value={d.education.major} onChange={(e) => setEdu({ major: e.target.value })} placeholder="Dasturiy injiniring" className={inputCls} />
          </Field>
          <Field id={`${ids}-degree`} label="Daraja">
            <select id={`${ids}-degree`} value={d.education.degree_level} onChange={(e) => setEdu({ degree_level: e.target.value })} className={inputCls}>
              <option value="BAKALAVR">Bakalavr</option>
              <option value="MAGISTR">Magistr</option>
              <option value="KOLLEJ">Kollej / texnikum</option>
              <option value="DOKTORANTURA">Doktorantura</option>
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field id={`${ids}-year`} label="Kurs">
              <select id={`${ids}-year`} value={d.education.study_year} onChange={(e) => setEdu({ study_year: Number(e.target.value) })} className={inputCls}>
                {[1, 2, 3, 4, 5, 6].map((y) => (
                  <option key={y} value={y}>
                    {y}-kurs
                  </option>
                ))}
              </select>
            </Field>
            <Field id={`${ids}-grad`} label="Bitirish yili">
              <select id={`${ids}-grad`} value={d.education.graduation_year} onChange={(e) => setEdu({ graduation_year: Number(e.target.value) })} className={inputCls}>
                {Array.from({ length: 10 }, (_, i) => new Date().getFullYear() - 2 + i).map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field id={`${ids}-gpa`} label="O‘rtacha ball (GPA)" optional hint="Yuqori bo‘lsa ko‘rsating, masalan 4.6 / 5.">
            <input id={`${ids}-gpa`} value={d.education.gpa} maxLength={20} onChange={(e) => setEdu({ gpa: e.target.value })} placeholder="4.6" className={inputCls} />
          </Field>
          <Field id={`${ids}-thesis`} label="Kurs / bitiruv ishi mavzusi" optional>
            <input id={`${ids}-thesis`} value={d.education.thesis_or_research_topic} onChange={(e) => setEdu({ thesis_or_research_topic: e.target.value })} className={inputCls} />
          </Field>
        </div>
      )}

      {step === "experience" && (
        <div className="flex flex-col gap-3">
          {!exp && (
            <button
              type="button"
              onClick={() => {
                setEditingExp({ index: null, item: emptyExperience() });
                setExpErrors({});
              }}
              className="skeuo-btn-secondary self-start rounded-xl px-4 py-2 text-sm"
            >
              <Plus className="h-4 w-4" aria-hidden="true" /> Tajriba qo‘shish
            </button>
          )}

          {exp && (
            <div className="rounded-2xl skeuo-well p-4 grid grid-cols-1 gap-4 md:grid-cols-2" role="group" aria-label="Tajriba kartochkasi">
              <Field id={`${ids}-role`} label="Lavozim" error={expErrors.role_title}>
                <input id={`${ids}-role`} autoFocus value={exp.item.role_title} onChange={(e) => setExp({ role_title: e.target.value })} placeholder="Backend amaliyotchi" className={inputCls} />
              </Field>
              <Field id={`${ids}-company`} label="Tashkilot" error={expErrors.company_name}>
                <input id={`${ids}-company`} value={exp.item.company_name} onChange={(e) => setExp({ company_name: e.target.value })} placeholder="Uzinfocom" className={inputCls} />
              </Field>
              <Field id={`${ids}-type`} label="Turi">
                <select id={`${ids}-type`} value={exp.item.employment_type} onChange={(e) => setExp({ employment_type: e.target.value })} className={inputCls}>
                  {Object.entries(WORK_TYPE_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
              </Field>
              <Field id={`${ids}-loc`} label="Shahar" optional>
                <input id={`${ids}-loc`} value={exp.item.location} onChange={(e) => setExp({ location: e.target.value })} placeholder="Toshkent" className={inputCls} />
              </Field>
              <Field id={`${ids}-start`} label="Boshlagan oy" error={expErrors.start_date}>
                <input id={`${ids}-start`} type="month" value={toMonth(exp.item.start_date)} onChange={(e) => setExp({ start_date: fromMonth(e.target.value) })} className={inputCls} />
              </Field>
              <div>
                <Field id={`${ids}-end`} label="Tugatgan oy" error={expErrors.end_date}>
                  <input id={`${ids}-end`} type="month" disabled={Boolean(exp.item.is_current)} value={toMonth(exp.item.end_date)} onChange={(e) => setExp({ end_date: fromMonth(e.target.value) || null })} className={inputCls} />
                </Field>
                <label className="mt-2 inline-flex items-center gap-2 text-sm text-[var(--fb-ink-secondary)]">
                  <input type="checkbox" checked={Boolean(exp.item.is_current)} onChange={(e) => setExp({ is_current: e.target.checked, end_date: e.target.checked ? null : exp.item.end_date })} />
                  Hozir ham shu yerda
                </label>
              </div>
              <div className="md:col-span-2">
                <Field id={`${ids}-desc`} label="Nima qildingiz?" optional hint="Har bir ishni yangi qatordan yozing. Raqamlar bilan yozsangiz yaxshiroq: «20 ta API yozdim», «so‘rovlar 30% tezlashdi».">
                  <textarea
                    id={`${ids}-desc`}
                    rows={4}
                    value={exp.item.description ?? ""}
                    onChange={(e) => setExp({ description: e.target.value })}
                    placeholder={"• Foydalanuvchilar uchun REST API yozdim\n• Ma’lumotlar bazasi so‘rovlarini optimallashtirdim"}
                    className={inputCls}
                  />
                </Field>
              </div>
              <div className="md:col-span-2">
                <Field id={`${ids}-tech`} label="Ishlatgan vositalar / dasturlar" optional hint="Enter bilan qo‘shing: Python, Excel, Figma, 1C…">
                  <ChipInput id={`${ids}-tech`} max={20} values={exp.item.technologies ?? []} onChange={(v) => setExp({ technologies: v })} placeholder="Python" />
                </Field>
              </div>
              <div className="md:col-span-2 flex gap-2 justify-end">
                <button type="button" onClick={() => setEditingExp(null)} className="skeuo-btn-secondary rounded-xl px-4 py-2 text-sm">
                  Bekor qilish
                </button>
                <button type="button" onClick={commitExperience} className="skeuo-btn-tone rounded-xl px-4 py-2 text-sm">
                  <Check className="h-4 w-4" aria-hidden="true" /> Kartochkani saqlash
                </button>
              </div>
            </div>
          )}

          {d.experience.length === 0 && !exp ? (
            <div className="rounded-2xl skeuo-well p-5 text-sm text-[var(--fb-ink-secondary)]">
              <p className="font-semibold text-[var(--fb-ink)]">Hali ish tajribangiz yo‘qmi? Bu normal.</p>
              <p className="mt-1">
                Talabalar uchun amaliyot, kurs loyihasi, frilans buyurtma, ko‘ngillilik yoki tashkilotdagi faollik ham tajriba hisoblanadi. Bo‘lmasa, bu
                qadamni o‘tkazib yuboring.
              </p>
            </div>
          ) : (
            <ul className="flex flex-col gap-2.5">
              {d.experience.map((w, i) => (
                <li key={`${w.company_name}-${i}`} className="rounded-2xl skeuo-well p-4 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-semibold text-[var(--fb-ink)]">
                      {w.role_title} · {w.company_name}
                    </div>
                    <div className="text-xs text-[var(--fb-ink-muted)]">
                      {[WORK_TYPE_LABELS[w.employment_type] ?? w.employment_type, w.location, `${toMonth(w.start_date)} — ${w.is_current || !w.end_date ? "hozirgacha" : toMonth(w.end_date)}`]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button type="button" aria-label={`${w.role_title} ni tahrirlash`} onClick={() => setEditingExp({ index: i, item: { ...w } })} className="skeuo-btn-secondary rounded-lg p-2">
                      <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                    <button type="button" aria-label={`${w.role_title} ni o‘chirish`} onClick={() => update({ experience: d.experience.filter((_, j) => j !== i) })} className="skeuo-btn-secondary rounded-lg p-2">
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {step === "languages" && (
        <div className="flex flex-col gap-3">
          <datalist id={`${ids}-langs`}>
            {COMMON_LANGUAGES.map((l) => (
              <option key={l} value={l} />
            ))}
          </datalist>
          {d.languages.length === 0 && <p className="text-sm text-[var(--fb-ink-secondary)]">Ona tilingizdan boshlang, keyin boshqa tillarni qo‘shing.</p>}
          <ul className="flex flex-col gap-2.5">
            {d.languages.map((l, i) => {
              const setLang = (patch: Partial<CandidateLanguageItem>) => update({ languages: d.languages.map((x, j) => (j === i ? { ...x, ...patch } : x)) });
              return (
                <li key={i} className="rounded-2xl skeuo-well p-3 grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end">
                  <Field id={`${ids}-lang-${i}`} label="Til" error={err(`lang_${i}`)}>
                    <input id={`${ids}-lang-${i}`} list={`${ids}-langs`} value={l.language} onChange={(e) => setLang({ language: e.target.value })} placeholder="Ingliz tili" className={inputCls} />
                  </Field>
                  <Field id={`${ids}-level-${i}`} label="Daraja">
                    <select id={`${ids}-level-${i}`} value={l.proficiency} onChange={(e) => setLang({ proficiency: e.target.value })} className={inputCls}>
                      {Object.entries(LANGUAGE_LEVEL_LABELS).map(([v, lbl]) => (
                        <option key={v} value={v}>
                          {lbl}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field id={`${ids}-cert-${i}`} label="Sertifikat" optional>
                    <input
                      id={`${ids}-cert-${i}`}
                      value={[l.certificate_name, l.score].filter(Boolean).join(" ")}
                      onChange={(e) => setLang({ certificate_name: e.target.value || null, score: null })}
                      placeholder="IELTS 7.0"
                      className={inputCls}
                    />
                  </Field>
                  <button type="button" aria-label="Tilni o‘chirish" onClick={() => update({ languages: d.languages.filter((_, j) => j !== i) })} className="skeuo-btn-secondary rounded-xl p-2.5 justify-self-start">
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </button>
                </li>
              );
            })}
          </ul>
          <button
            type="button"
            onClick={() => update({ languages: [...d.languages, { language: d.languages.length ? "" : "O‘zbek tili", proficiency: d.languages.length ? "B1" : "NATIVE" }] })}
            className="skeuo-btn-secondary self-start rounded-xl px-4 py-2 text-sm"
          >
            <Plus className="h-4 w-4" aria-hidden="true" /> Til qo‘shish
          </button>
        </div>
      )}

      {step === "extras" && (
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-2">
              <h4 className="text-sm font-bold text-[var(--fb-ink)]">Yutuqlar</h4>
              {!ach && (
                <button
                  type="button"
                  onClick={() => {
                    setEditingAch({ index: null, item: emptyAchievement() });
                    setAchErrors({});
                  }}
                  className="skeuo-btn-secondary rounded-xl px-3 py-1.5 text-xs"
                >
                  <Plus className="h-3.5 w-3.5" aria-hidden="true" /> Yutuq qo‘shish
                </button>
              )}
            </div>
            <p className="text-xs text-[var(--fb-ink-muted)]">Olimpiada, hakaton, grant, stipendiya, maqola, tanlov — kichik bo‘lsa ham yozing.</p>
            {ach && (
              <div className="rounded-2xl skeuo-well p-4 grid grid-cols-1 gap-4 md:grid-cols-2" role="group" aria-label="Yutuq kartochkasi">
                <Field id={`${ids}-at`} label="Nomi" error={achErrors.title}>
                  <input id={`${ids}-at`} autoFocus value={ach.item.title} onChange={(e) => setAch({ title: e.target.value })} placeholder="Respublika informatika olimpiadasi, 2-o‘rin" className={inputCls} />
                </Field>
                <Field id={`${ids}-ac`} label="Turi">
                  <select id={`${ids}-ac`} value={ach.item.category} onChange={(e) => setAch({ category: e.target.value })} className={inputCls}>
                    {Object.entries(ACHIEVEMENT_LABELS).map(([v, l]) => (
                      <option key={v} value={v}>
                        {l}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field id={`${ids}-ai`} label="Kim bergan" error={achErrors.issuer}>
                  <input id={`${ids}-ai`} value={ach.item.issuer} onChange={(e) => setAch({ issuer: e.target.value })} placeholder="Oliy ta’lim vazirligi" className={inputCls} />
                </Field>
                <Field id={`${ids}-ad`} label="Sana" optional>
                  <input id={`${ids}-ad`} type="month" value={toMonth(ach.item.awarded_date)} onChange={(e) => setAch({ awarded_date: fromMonth(e.target.value) || null })} className={inputCls} />
                </Field>
                <div className="md:col-span-2 flex gap-2 justify-end">
                  <button type="button" onClick={() => setEditingAch(null)} className="skeuo-btn-secondary rounded-xl px-4 py-2 text-sm">
                    Bekor qilish
                  </button>
                  <button type="button" onClick={commitAchievement} className="skeuo-btn-tone rounded-xl px-4 py-2 text-sm">
                    <Check className="h-4 w-4" aria-hidden="true" /> Kartochkani saqlash
                  </button>
                </div>
              </div>
            )}
            <ul className="flex flex-col gap-2.5">
              {d.achievements.map((a, i) => (
                <li key={`${a.title}-${i}`} className="rounded-2xl skeuo-well p-4 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-semibold text-[var(--fb-ink)]">{a.title}</div>
                    <div className="text-xs text-[var(--fb-ink-muted)]">{[ACHIEVEMENT_LABELS[a.category] ?? a.category, a.issuer, toMonth(a.awarded_date)].filter(Boolean).join(" · ")}</div>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button type="button" aria-label={`${a.title} ni tahrirlash`} onClick={() => setEditingAch({ index: i, item: { ...a } })} className="skeuo-btn-secondary rounded-lg p-2">
                      <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                    <button type="button" aria-label={`${a.title} ni o‘chirish`} onClick={() => update({ achievements: d.achievements.filter((_, j) => j !== i) })} className="skeuo-btn-secondary rounded-lg p-2">
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <h4 className="md:col-span-2 text-sm font-bold text-[var(--fb-ink)]">Havolalar</h4>
            <Field id={`${ids}-gh`} label="GitHub" optional hint="Foydalanuvchi nomi yoki havola.">
              <input id={`${ids}-gh`} value={d.prefs.github_username} onChange={(e) => setPrefs({ github_username: e.target.value })} placeholder="username" className={inputCls} />
            </Field>
            <Field id={`${ids}-li`} label="LinkedIn" optional>
              <input id={`${ids}-li`} value={d.prefs.linkedin_url} onChange={(e) => setPrefs({ linkedin_url: e.target.value })} placeholder="https://linkedin.com/in/…" className={inputCls} />
            </Field>
            <Field id={`${ids}-tg`} label="Telegram" optional hint="Ish beruvchilarga ko‘rsatilmaydi.">
              <input id={`${ids}-tg`} value={d.prefs.telegram_username} onChange={(e) => setPrefs({ telegram_username: e.target.value })} placeholder="@username" className={inputCls} />
            </Field>
          </div>
        </div>
      )}

      {step === "review" && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,18rem)]">
          <div className="rounded-2xl skeuo-well p-5 flex flex-col gap-4">
            <div>
              <div className="font-heading text-lg font-bold text-[var(--fb-ink)]">{d.headline || "Kasbiy sarlavha yozilmagan"}</div>
              <div className="text-sm text-[var(--fb-ink-secondary)]">{d.region}</div>
            </div>
            <ResumePreview resume={preview} />
          </div>
          <aside className="flex flex-col gap-3">
            <div className="rounded-2xl skeuo-well p-4">
              <h4 className="text-sm font-bold text-[var(--fb-ink)] mb-2">Tayyorlik: {doneCount}/5</h4>
              <ul className="flex flex-col gap-1.5 text-sm">
                {STEPS.filter((s) => s.id !== "review").map((s) => {
                  const ok = done[s.id as keyof typeof done];
                  return (
                    <li key={s.id}>
                      <button type="button" onClick={() => void goTo(s.id)} className="flex items-center gap-2 text-left hover:underline">
                        {ok ? <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" /> : <AlertCircle className="h-4 w-4 text-amber-600" aria-hidden="true" />}
                        <span className={ok ? "text-[var(--fb-ink-secondary)]" : "font-semibold text-[var(--fb-ink)]"}>{s.title}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
            <div className="rounded-2xl skeuo-well p-4 flex flex-col gap-2">
              <span className="text-sm font-semibold text-[var(--fb-ink)]">Tayyor PDF rezyumengiz bormi?</span>
              <span className="text-xs text-[var(--fb-ink-muted)]">Biriktirsangiz, ish beruvchilar uni ham ko‘ra oladi (10 MB gacha).</span>
              <label className="skeuo-btn-secondary self-start cursor-pointer rounded-xl px-3 py-2 text-xs">
                {cvState.busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Plus className="h-3.5 w-3.5" aria-hidden="true" />}
                PDF tanlash
                <input
                  type="file"
                  accept="application/pdf,.pdf"
                  className="sr-only"
                  disabled={cvState.busy}
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    setCvState({ busy: true, message: null });
                    try {
                      const b64 = await new Promise<string>((resolve, reject) => {
                        const r = new FileReader();
                        r.onload = () => resolve(String(r.result).split(",")[1] ?? "");
                        r.onerror = () => reject(new Error("read"));
                        r.readAsDataURL(f);
                      });
                      const res = await uploadCandidatePdfFile({ filename: f.name, purpose: "CV", title: d.headline || "Rezyume", content_base64: b64 });
                      setCvState({ busy: false, message: `Biriktirildi: ${res.filename}` });
                    } catch (er) {
                      setCvState({ busy: false, message: er instanceof Error && !/^[A-Z_]+$/.test(er.message) ? er.message : "PDF yuklanmadi. Fayl PDF ekanini tekshiring." });
                    }
                  }}
                />
              </label>
              {cvState.message && <span className="text-xs text-[var(--fb-ink-secondary)]">{cvState.message}</span>}
            </div>
            <div className="rounded-2xl skeuo-well p-4">
              <label className="flex items-start gap-3 text-sm">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={currentVisibility === "EMPLOYERS"}
                  onChange={async (e) => {
                    const next: CandidateVisibility = e.target.checked ? "EMPLOYERS" : "PRIVATE";
                    try {
                      setVisibility(await setCandidateVisibility(next));
                    } catch {
                      setSaveError("Ko‘rinish sozlamasini saqlab bo‘lmadi.");
                    }
                  }}
                />
                <span>
                  <span className="font-semibold text-[var(--fb-ink)]">Ish beruvchilar meni qidiruvda topsin</span>
                  <span className="block text-xs text-[var(--fb-ink-muted)]">Telefon, pochta va Telegram ko‘rsatilmaydi. Istalgan payt o‘chirasiz.</span>
                </span>
              </label>
            </div>
          </aside>
        </div>
      )}

      <div className="flex items-center justify-between gap-2 border-t border-[var(--fb-hairline)] pt-4">
        <button type="button" disabled={stepIndex === 0 || saving} onClick={() => void goTo(STEPS[stepIndex - 1].id)} className="skeuo-btn-secondary rounded-xl px-4 py-2.5 text-sm disabled:opacity-40">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Orqaga
        </button>
        {step !== "review" ? (
          <button type="button" disabled={saving} onClick={() => void goTo(STEPS[stepIndex + 1].id)} className="skeuo-btn-tone rounded-xl px-5 py-2.5 text-sm disabled:opacity-60">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
            Saqlash va davom etish <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : (
          <button type="button" disabled={saving || !dirty} onClick={() => void save()} className="skeuo-btn-tone rounded-xl px-5 py-2.5 text-sm disabled:opacity-60">
            <Check className="h-4 w-4" aria-hidden="true" /> {dirty ? "Saqlash" : "Hammasi saqlangan"}
          </button>
        )}
      </div>
    </section>
  );
}
