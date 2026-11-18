"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Briefcase,
  CheckCircle2,
  AlertCircle,
  Lock,
  MessageSquareText,
  Plus,
  Paperclip,
  RefreshCw,
  Save,
  Send,
  Trash2,
} from "lucide-react";
import {
  AuthUser,
  fetchAuthMe,
  CandidatePlacementItem,
  DailyLogItem,
  fetchCandidatePlacements,
  fetchPlacementLogs,
  fetchStandardizedDiary,
  saveDraftDailyLog,
  submitDailyLog,
  saveStandardizedDiary,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";
import { useAsyncData } from "@/lib/useAsyncData";
import InternshipDocumentsHub from "@/components/InternshipDocumentsHub";
import DiaryCalendar from "@/components/diary/DiaryCalendar";
import { DECISION_LABEL, STATUS_LABEL, localISODate, longDate, reviewsOf, weekdayOf } from "@/lib/diary";
import TaskEvidenceDrawer from "@/components/diary/TaskEvidenceDrawer";
import { classesOn, fetchMyTimetable, workClashes } from "@/lib/timetable";

// Stable empty values: the form sync below compares `logs` by identity.
const EMPTY_PLACEMENTS: CandidatePlacementItem[] = [];
const EMPTY_LOGS: DailyLogItem[] = [];
const DAILY_LIMIT = 480; // Labour Code art. 118: at most 8 hours a day
const EMPTY_TASK: { id?: string; title: string; minutes: number; evidence_count?: number } = { title: "", minutes: 0 };

type Task = { id?: string; title: string; minutes: number; evidence_count?: number };
type Standard = {
  workStart: string;
  workEnd: string;
  department: string;
  tools: string;
  skills: string;
  artifact: string;
  safety: boolean;
};

async function loadCurrentUser(): Promise<AuthUser | null> {
  try {
    return await fetchAuthMe();
  } catch {
    return null;
  }
}

const loadPlacementItems = async () => (await fetchCandidatePlacements()).items || [];

const clampDate = (iso: string, min: string, max: string) => (iso < min ? min : iso > max ? max : iso);

export default function CandidateKundalikPage() {
  const auth = useAsyncData("auth-me", loadCurrentUser);
  const user = auth.data ?? null;
  const [authModalOpen, setAuthModalOpen] = useState(false);

  const placementsQuery = useAsyncData(user ? `placements:${user.user_id}` : null, loadPlacementItems);
  const placements = placementsQuery.data ?? EMPTY_PLACEMENTS;
  const [chosenPlacementId, setChosenPlacementId] = useState<string | null>(null);
  const placement = placements.find((p) => p.id === chosenPlacementId) ?? placements[0] ?? null;
  const placementId = placement?.id ?? null;

  const logsQuery = useAsyncData(placementId ? `logs:${placementId}` : null, async () =>
    (await fetchPlacementLogs(placementId ?? "")).items
  );
  const logs = logsQuery.data ?? EMPTY_LOGS;
  const diaryQuery = useAsyncData(placementId ? `diary:${placementId}` : null, () =>
    fetchStandardizedDiary(placementId ?? "").catch(() => null)
  );
  const diary = diaryQuery.data ?? null;
  const timetableQuery = useAsyncData(user ? `my-timetable:${user.user_id}` : null, () =>
    fetchMyTimetable().catch(() => null)
  );
  const timetable = timetableQuery.data?.status === "OK" ? timetableQuery.data : null;

  // Date window: the placement period, never in the future (local time, not UTC).
  const today = useMemo(() => localISODate(), []);
  const minDate = placement?.start_date ?? today;
  const maxDate = placement ? (placement.end_date < today ? placement.end_date : today) : today;
  const [pickedDate, setPickedDate] = useState<string | null>(null);
  const selectedDate = clampDate(pickedDate ?? today, minDate, maxDate);
  const [pickedMonth, setPickedMonth] = useState<string | null>(null);
  const month = pickedMonth ?? selectedDate.slice(0, 7);

  // Form state
  const [dayType, setDayType] = useState<"WORKED" | "ABSENT">("WORKED");
  const [summaryText, setSummaryText] = useState("");
  const [tasks, setTasks] = useState<Task[]>([EMPTY_TASK]);
  const [std, setStd] = useState<Standard>({ workStart: "09:00", workEnd: "17:00", department: "", tools: "", skills: "", artifact: "", safety: true });

  const [busy, setBusy] = useState<"save" | "submit" | null>(null);
  const [evidenceTask, setEvidenceTask] = useState<{ id: string; title: string } | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error" | "warning"; message: string } | null>(null);

  const activeLog = logs.find((l) => l.local_date === selectedDate);
  const locked = Boolean(activeLog && activeLog.status !== "DRAFT");
  const weekday = weekdayOf(selectedDate);
  const dayClasses = timetable ? classesOn(timetable.slots, weekday) : [];

  // Sync the form when the date, logs, diary or timetable change. Adjusted during
  // render (react.dev "You Might Not Need an Effect") instead of a cascading effect.
  const [syncKey, setSyncKey] = useState<{ date: string; logs: DailyLogItem[]; diary: unknown; tt: unknown } | null>(null);
  if (!syncKey || syncKey.date !== selectedDate || syncKey.logs !== logs || syncKey.diary !== diary || syncKey.tt !== timetable) {
    setSyncKey({ date: selectedDate, logs, diary, tt: timetable });
    const entry = diary?.entries.find((e) => e.log_date === selectedDate)?.standard_entry;
    const freeToday = timetable?.free_windows.find((d) => d.weekday === weekday)?.free_intervals[0];
    setStd({
      workStart: entry?.work_start_time || freeToday?.start_time || "09:00",
      workEnd: entry?.work_end_time || freeToday?.end_time || "17:00",
      department: entry?.department_unit || "",
      tools: entry?.tools_used || "",
      skills: entry?.skills_practiced || "",
      artifact: entry?.outcome_artifact || "",
      safety: entry ? entry.safety_instructed : true,
    });
    if (activeLog) {
      setDayType(activeLog.day_type || "WORKED");
      setSummaryText(activeLog.summary || "");
      setTasks(
        activeLog.tasks && activeLog.tasks.length > 0
          ? activeLog.tasks.map((t) => ({ id: t.id, title: t.title, minutes: t.minutes, evidence_count: t.evidence_count }))
          : [EMPTY_TASK]
      );
    } else {
      setDayType("WORKED");
      setSummaryText("");
      setTasks([EMPTY_TASK]);
    }
  }

  const totalMinutes = dayType === "ABSENT" ? 0 : tasks.reduce((sum, t) => sum + (Number(t.minutes) || 0), 0);
  const clashes = timetable && dayType === "WORKED" ? workClashes(timetable.slots, weekday, std.workStart, std.workEnd) : [];

  const counts = useMemo(() => {
    const c = { DRAFT: 0, SUBMITTED: 0, REVIEWED: 0, NEEDS_REVISION: 0 } as Record<DailyLogItem["status"], number>;
    logs.forEach((l) => (c[l.status] += 1));
    return c;
  }, [logs]);
  const loggedHours = logs.filter((l) => l.status !== "DRAFT").reduce((s, l) => s + (l.total_minutes || 0), 0) / 60;
  const normative = diary?.stats.normative_hours || 0;

  const setTask = (i: number, patch: Partial<Task>) => setTasks((ts) => ts.map((t, j) => (j === i ? { ...t, ...patch } : t)));

  async function persist(submit: boolean) {
    if (!placement) return;
    if (dayType === "WORKED" && totalMinutes > DAILY_LIMIT) {
      setNotification({ type: "error", message: "Kunlik amaliyot vaqti 8 soatdan (480 daqiqa) oshmasligi kerak (Mehnat kodeksi, 118-modda)." });
      return;
    }
    if (submit && dayType === "WORKED" && totalMinutes <= 0) {
      setNotification({ type: "error", message: "Yuborishdan oldin kamida bitta vazifa va unga sarflangan vaqtni kiriting." });
      return;
    }
    setBusy(submit ? "submit" : "save");
    setNotification(null);
    try {
      const draft = await saveDraftDailyLog(placement.id, selectedDate, {
        day_type: dayType,
        summary_text: summaryText,
        total_minutes: totalMinutes,
        tasks:
          dayType === "ABSENT"
            ? []
            : tasks.filter((t) => t.minutes > 0).map((t) => ({ title: t.title.trim() || "Amaliyot vazifasi", minutes: t.minutes })),
      });
      let extrasError: string | null = null;
      await saveStandardizedDiary(placement.id, {
        daily_entry: {
          daily_log_id: draft?.id,
          log_date: selectedDate,
          work_start_time: std.workStart,
          work_end_time: std.workEnd,
          department_unit: std.department,
          tools_used: std.tools,
          skills_practiced: std.skills,
          outcome_artifact: std.artifact,
          safety_instructed: std.safety,
        },
      }).catch((err: unknown) => {
        extrasError = err instanceof Error ? err.message : "noma’lum xato";
      });
      if (submit) {
        const id = draft?.id || activeLog?.id;
        if (!id) throw new Error("Kundalik yozuvi topilmadi. Sahifani yangilab, qayta urinib ko‘ring.");
        await submitDailyLog(id);
      }
      setNotification(
        extrasError
          ? { type: "warning", message: `Asosiy yozuv saqlandi, lekin qo‘shimcha maydonlar saqlanmadi: ${extrasError}` }
          : {
              type: "success",
              message: submit
                ? `${longDate(selectedDate)} — mentor va o‘qituvchi tekshiruviga yuborildi.`
                : `${longDate(selectedDate)} — qoralama saqlandi.`,
            }
      );
      await Promise.all([logsQuery.reload(), diaryQuery.reload()]);
    } catch (err: unknown) {
      setNotification({ type: "error", message: err instanceof Error ? err.message : "Saqlab bo‘lmadi." });
    } finally {
      setBusy(null);
    }
  }

  const input = "skeuo-input w-full rounded-2xl px-3.5 py-2.5 text-sm disabled:opacity-60";
  const reviews = activeLog ? reviewsOf(activeLog) : [];

  return (
    <div className="flex w-full flex-col gap-5 text-[var(--fb-ink)]">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-[var(--fb-ink-muted)]">{placement?.organization_name || "Amaliyot"}</p>
          <h1 className="fb-display mt-1">Kundalik</h1>
          {placement && (
            <p className="mt-2 text-sm text-[var(--fb-ink-secondary)]">
              {placement.opportunity_title || "Amaliyot"} · {placement.start_date} — {placement.end_date}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {placements.length > 1 && (
            <div className="fb-seg" role="group" aria-label="Amaliyotni tanlash">
              {placements.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  aria-pressed={p.id === placementId}
                  onClick={() => {
                    setChosenPlacementId(p.id);
                    setPickedDate(null);
                    setPickedMonth(null);
                  }}
                >
                  {p.organization_name || "Korxona"}
                </button>
              ))}
            </div>
          )}
          {placement && (
            <button
              type="button"
              onClick={() => void Promise.all([logsQuery.reload(), diaryQuery.reload()])}
              className="fb-icon-btn fb-icon-btn-light"
              aria-label="Yangilash"
            >
              <RefreshCw className={`h-4 w-4 ${logsQuery.isLoading ? "animate-spin" : ""}`} />
            </button>
          )}
        </div>
      </header>

      {notification && (
        <div
          role={notification.type === "error" ? "alert" : "status"}
          className={`fb-panel skeuo-card flex items-start gap-3 px-4 py-3 text-sm ${
            notification.type === "success"
              ? "text-emerald-700 dark:text-emerald-300"
              : notification.type === "warning"
                ? "text-amber-800 dark:text-amber-300"
                : "text-rose-700 dark:text-rose-300"
          }`}
        >
          {notification.type === "success" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />}
          <p>{notification.message}</p>
        </div>
      )}

      {!auth.isLoading && !user && (
        <section className="fb-panel skeuo-card mx-auto flex max-w-md flex-col items-center gap-3 p-10 text-center">
          <h2 className="text-lg font-semibold">Kundalikni yuritish uchun kiring</h2>
          <button type="button" onClick={() => setAuthModalOpen(true)} className="rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold">
            Talaba kirishi
          </button>
        </section>
      )}

      {user && placementsQuery.error && (
        <p role="alert" className="fb-panel skeuo-card px-4 py-3 text-sm text-rose-700 dark:text-rose-300">
          Amaliyotlarni yuklab bo‘lmadi: {placementsQuery.error.message}
        </p>
      )}

      {user && !placementsQuery.isLoading && !placementsQuery.error && !placement && (
        <section className="fb-panel skeuo-card flex flex-col items-center gap-3 px-6 py-14 text-center">
          <span className="fb-avatar h-14 w-14" aria-hidden="true">
            <Briefcase className="h-6 w-6" />
          </span>
          <h2 className="text-lg font-semibold">Faol amaliyot topilmadi</h2>
          <p className="max-w-md text-sm text-[var(--fb-ink-secondary)]">Kundalik amaliyot shartnomasi rasmiylashtirilgandan keyin ochiladi.</p>
          <Link href="/" className="rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold">
            Vakansiyalarni ko‘rish
          </Link>
        </section>
      )}

      {placement && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.75fr)]">
          <div className="flex min-w-0 flex-col gap-5">
            <section className="fb-panel skeuo-card p-5" aria-label="Kundalik kalendari">
              <DiaryCalendar
                month={month}
                onMonthChange={setPickedMonth}
                logs={logs}
                selected={selectedDate}
                onSelect={(d) => {
                  setPickedDate(d);
                  setNotification(null);
                }}
                minDate={minDate}
                maxDate={maxDate}
                today={today}
                classDays={timetable ? new Set(timetable.slots.map((s) => s.weekday)) : undefined}
              />
            </section>

            <section data-skeuo-dark="true" className="fb-ink-card flex flex-col gap-4 p-5" aria-labelledby="diary-hours">
              <h2 id="diary-hours" className="text-sm font-semibold fb-muted">Amaliyot soatlari</h2>
              <p className="font-display text-4xl font-bold tabular-nums">
                {Math.round(loggedHours * 10) / 10}
                <span className="ml-1 text-base font-semibold fb-muted">{normative ? `/ ${normative} soat` : "soat yuborilgan"}</span>
              </p>
              {normative > 0 && (
                <div className="fb-progress" role="img" aria-label={`Me’yorning ${Math.min(100, Math.round((loggedHours / normative) * 100))} foizi`}>
                  <span style={{ width: `${Math.min(100, (loggedHours / normative) * 100)}%` }} />
                </div>
              )}
              <dl className="grid grid-cols-2 gap-3 text-xs">
                {(["REVIEWED", "SUBMITTED", "NEEDS_REVISION", "DRAFT"] as const).map((k) => (
                  <div key={k}>
                    <dt className="fb-muted">{STATUS_LABEL[k]}</dt>
                    <dd className="text-lg font-bold tabular-nums">{counts[k]}</dd>
                  </div>
                ))}
              </dl>
            </section>
          </div>

          <div className="flex min-w-0 flex-col gap-5">
            <section className="fb-panel skeuo-card flex flex-col gap-5 p-5 sm:p-6" aria-labelledby="diary-day">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 id="diary-day" className="text-xl font-semibold tracking-tight">{longDate(selectedDate)}</h2>
                  <p className="text-xs text-[var(--fb-ink-muted)]">{selectedDate === today ? "Bugun" : "Kunlik hisobot"}</p>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    activeLog?.status === "REVIEWED" ? "fb-nav-active" : activeLog?.status === "NEEDS_REVISION" ? "bg-[var(--fb-accent)] text-white" : "fb-capsule"
                  }`}
                >
                  {activeLog ? STATUS_LABEL[activeLog.status] : "Yozilmagan"}
                </span>
              </div>

              {timetable && (
                <div className="flex flex-col gap-2">
                  <p className="text-xs font-medium text-[var(--fb-ink-muted)]">Shu kuni darslaringiz</p>
                  {dayClasses.length === 0 ? (
                    <p className="text-xs text-[var(--fb-ink-secondary)]">Dars yo‘q.</p>
                  ) : (
                    <ul className="flex flex-wrap gap-2">
                      {dayClasses.map((c) => (
                        <li key={c.start_minute} className="fb-capsule px-3 py-1 text-[11px] font-medium tabular-nums">
                          {c.start_time}–{c.end_time} · {c.subject_name}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {locked && (
                <p className="flex items-start gap-2 rounded-2xl skeuo-well px-3.5 py-3 text-xs text-[var(--fb-ink-secondary)]">
                  <Lock className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  Bu kun tekshiruvga yuborilgan — yozuvni endi o‘zgartirib bo‘lmaydi.
                </p>
              )}

              <fieldset disabled={locked || busy !== null} className="flex min-w-0 flex-col gap-5">
                <div className="fb-seg w-fit" role="group" aria-label="Kun turi">
                  <button type="button" aria-pressed={dayType === "WORKED"} onClick={() => setDayType("WORKED")}>
                    Ish kuni
                  </button>
                  <button type="button" aria-pressed={dayType === "ABSENT"} onClick={() => setDayType("ABSENT")}>
                    Kelmadim (sababli)
                  </button>
                </div>

                {dayType === "WORKED" && (
                  <>
                    <div className="grid grid-cols-2 gap-3 sm:max-w-sm">
                      <label className="flex flex-col gap-1.5 text-xs font-medium text-[var(--fb-ink-secondary)]">
                        Kelish
                        <input type="time" value={std.workStart} onChange={(e) => setStd({ ...std, workStart: e.target.value })} className={input} />
                      </label>
                      <label className="flex flex-col gap-1.5 text-xs font-medium text-[var(--fb-ink-secondary)]">
                        Ketish
                        <input type="time" value={std.workEnd} onChange={(e) => setStd({ ...std, workEnd: e.target.value })} className={input} />
                      </label>
                    </div>
                    {clashes.length > 0 && (
                      <p role="alert" className="flex items-start gap-2 rounded-2xl bg-amber-500/12 px-3.5 py-3 text-xs text-amber-800 dark:text-amber-300">
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                        <span>
                          Bu vaqt darsingiz bilan to‘qnashadi: {clashes.map((c) => `${c.subject_name} (${c.start_time}–${c.end_time})`).join(", ")}. Amaliyot
                          dars vaqtiga to‘g‘ri kelmasligi kerak.
                        </span>
                      </p>
                    )}

                    <div className="flex flex-col gap-2">
                      <div className="flex items-center justify-between">
                        <p className="text-xs font-medium text-[var(--fb-ink-secondary)]">Bajarilgan vazifalar</p>
                        <button
                          type="button"
                          onClick={() => setTasks([...tasks, EMPTY_TASK])}
                          className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold hover:bg-[var(--fb-well-deep)]"
                        >
                          <Plus className="h-3.5 w-3.5" /> Vazifa
                        </button>
                      </div>
                      {tasks.map((t, i) => (
                        <div key={i} className="fb-file-row !gap-2 !p-2 !pl-3.5">
                          <input
                            aria-label={`${i + 1}-vazifa`}
                            value={t.title}
                            onChange={(e) => setTask(i, { title: e.target.value })}
                            placeholder="Masalan: Buyurtmalar sahifasi uchun API yozdim"
                            className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--fb-ink-muted)]"
                          />
                          <input
                            aria-label={`${i + 1}-vazifa vaqti, daqiqa`}
                            type="number"
                            min={0}
                            max={DAILY_LIMIT}
                            step={15}
                            value={t.minutes || ""}
                            placeholder="0"
                            onChange={(e) => setTask(i, { minutes: Math.max(0, Number(e.target.value) || 0) })}
                            className="w-16 rounded-xl bg-[var(--fb-card-top)] px-2 py-1.5 text-right text-xs tabular-nums outline-none"
                          />
                          <span className="text-[11px] text-[var(--fb-ink-muted)]">daq</span>
                          {t.id && (
                            <button
                              type="button"
                              onClick={() => setEvidenceTask({ id: t.id!, title: t.title || `${i + 1}-vazifa` })}
                              className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold text-[var(--fb-ink-secondary)] hover:bg-[var(--fb-well-deep)]"
                              aria-label={`${i + 1}-vazifa dalillari`}
                            >
                              <Paperclip className="h-3.5 w-3.5" />
                              <span>{t.evidence_count ? t.evidence_count : "Dalil"}</span>
                            </button>
                          )}
                          {tasks.length > 1 && (
                            <button
                              type="button"
                              onClick={() => setTasks(tasks.filter((_, j) => j !== i))}
                              className="rounded-full p-1.5 text-[var(--fb-ink-muted)] hover:text-rose-600"
                              aria-label={`${i + 1}-vazifani o‘chirish`}
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      ))}
                      <div className="flex items-center gap-3 pt-1">
                        <div className="fb-progress flex-1" aria-hidden="true">
                          <span
                            style={{
                              width: `${Math.min(100, (totalMinutes / DAILY_LIMIT) * 100)}%`,
                              background: totalMinutes > DAILY_LIMIT ? "var(--fb-accent)" : undefined,
                            }}
                          />
                        </div>
                        <span className={`text-xs tabular-nums ${totalMinutes > DAILY_LIMIT ? "font-bold text-rose-600" : "text-[var(--fb-ink-secondary)]"}`}>
                          {Math.floor(totalMinutes / 60)} soat {totalMinutes % 60} daq / 8 soat
                        </span>
                      </div>
                    </div>
                  </>
                )}

                <label className="flex flex-col gap-1.5 text-xs font-medium text-[var(--fb-ink-secondary)]">
                  {dayType === "WORKED" ? "Kun xulosasi" : "Kelmaslik sababi"}
                  <textarea
                    rows={3}
                    value={summaryText}
                    onChange={(e) => setSummaryText(e.target.value)}
                    placeholder={dayType === "WORKED" ? "Bugun nimani o‘rgandingiz va qanday natijaga erishdingiz?" : "Masalan: imtihon, kasallik (ma’lumotnoma bor)"}
                    className={`${input} resize-none`}
                  />
                </label>

                <details className="rounded-2xl skeuo-well px-4 py-3">
                  <summary className="cursor-pointer text-xs font-semibold text-[var(--fb-ink-secondary)]">Universitet shakli uchun qo‘shimcha maydonlar</summary>
                  <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {(
                      [
                        ["department", "Bo‘lim / ish joyi", "Masalan: Dasturiy ta’minot bo‘limi"],
                        ["tools", "Uskunalar va texnologiyalar", "Python, PostgreSQL, Figma"],
                        ["skills", "O‘zlashtirilgan ko‘nikmalar", "REST API, kod sharhi"],
                        ["artifact", "Natija / hujjat", "PR #42, hisobot, maket"],
                      ] as const
                    ).map(([key, label, ph]) => (
                      <label key={key} className="flex flex-col gap-1.5 text-xs font-medium text-[var(--fb-ink-secondary)]">
                        {label}
                        <input value={std[key]} onChange={(e) => setStd({ ...std, [key]: e.target.value })} placeholder={ph} className={input} />
                      </label>
                    ))}
                    <label className="flex items-center gap-2 text-xs text-[var(--fb-ink-secondary)] sm:col-span-2">
                      <input type="checkbox" checked={std.safety} onChange={(e) => setStd({ ...std, safety: e.target.checked })} className="h-4 w-4" />
                      Xavfsizlik texnikasi bo‘yicha yo‘riqnomadan o‘tdim
                    </label>
                  </div>
                </details>

                <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--fb-border)] pt-4">
                  <button type="button" onClick={() => void persist(false)} className="inline-flex items-center gap-2 rounded-full skeuo-btn-secondary px-4 py-2.5 text-xs font-semibold disabled:opacity-50">
                    <Save className="h-4 w-4" /> {busy === "save" ? "Saqlanmoqda…" : "Qoralamani saqlash"}
                  </button>
                  <button type="button" onClick={() => void persist(true)} className="inline-flex items-center gap-2 rounded-full skeuo-btn-obsidian px-5 py-2.5 text-xs font-semibold disabled:opacity-50">
                    <Send className="h-4 w-4" /> {busy === "submit" ? "Yuborilmoqda…" : "Tekshiruvga yuborish"}
                  </button>
                </div>
              </fieldset>
            </section>

            {reviews.length > 0 && (
              <section data-skeuo-dark="true" className="fb-ink-card flex flex-col gap-3 p-5 sm:p-6" aria-labelledby="diary-reviews">
                <h2 id="diary-reviews" className="flex items-center gap-2 text-sm font-semibold">
                  <MessageSquareText className="h-4 w-4" aria-hidden="true" /> Mentor va universitet izohlari
                </h2>
                <ul className="flex flex-col gap-3">
                  {reviews.map((r, i) => (
                    <li key={`${r.by}-${r.decided_at}-${i}`} className="rounded-2xl bg-white/5 px-4 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                        <span className="font-semibold">
                          {r.by === "MENTOR" ? "Mentor" : "Universitet o‘qituvchisi"} · {DECISION_LABEL[r.decision] || r.decision}
                        </span>
                        <span className="fb-muted tabular-nums">{r.decided_at ? new Date(r.decided_at).toLocaleDateString("uz-UZ") : ""}</span>
                      </div>
                      {r.comment && <p className="mt-1.5 text-sm leading-relaxed">“{r.comment}”</p>}
                    </li>
                  ))}
                </ul>
                {activeLog?.status === "NEEDS_REVISION" && (
                  <p className="text-xs fb-muted">Yuborilgan yozuvni o‘zgartirib bo‘lmaydi — izoh bo‘yicha mentoringiz bilan kelishib oling.</p>
                )}
              </section>
            )}
          </div>
        </div>
      )}

      {placement && <InternshipDocumentsHub party="CANDIDATE" placementId={placement.id} />}

      <TaskEvidenceDrawer
        isOpen={Boolean(evidenceTask)}
        entryId={evidenceTask?.id ?? null}
        taskTitle={evidenceTask?.title ?? ""}
        locked={locked}
        onClose={() => setEvidenceTask(null)}
        onAttached={() => void logsQuery.reload()}
      />
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        requiredPortal="CANDIDATE"
        title="Talaba / Nomzod kirishi"
        subtitle="Amaliyot kundaligi va e-imzo uchun talaba hisobingizga kiring"
        onSuccess={() => {
          setAuthModalOpen(false);
          void auth.reload();
        }}
      />
    </div>
  );
}
