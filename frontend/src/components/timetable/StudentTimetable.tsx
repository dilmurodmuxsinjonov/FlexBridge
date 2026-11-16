"use client";

import React, { useState } from "react";
import Link from "next/link";
import { BookOpen, CalendarDays, Clock3, DoorOpen, GraduationCap, Info, UserRound } from "lucide-react";
import { classesOn, currentOrNext, hhmm, LESSON_LABEL, type ClassSlot, type MyTimetable } from "@/lib/timetable";
import { isoWeekday, uzDate } from "@/lib/person";

const DAYS = [
  { n: 1, short: "Du", long: "Dushanba" },
  { n: 2, short: "Se", long: "Seshanba" },
  { n: 3, short: "Ch", long: "Chorshanba" },
  { n: 4, short: "Pa", long: "Payshanba" },
  { n: 5, short: "Ju", long: "Juma" },
  { n: 6, short: "Sh", long: "Shanba" },
  { n: 7, short: "Ya", long: "Yakshanba" },
];

function LessonCard({ s, dense = false }: { s: ClassSlot; dense?: boolean }) {
  return (
    <div className={`fb-file-row !items-start flex-col !gap-1 ${dense ? "!p-2.5" : ""}`}>
      <div className="flex w-full items-center justify-between gap-2 text-[11px] text-[var(--fb-ink-muted)]">
        <span className="tabular-nums">{s.start_time}–{s.end_time}</span>
        <span className="rounded-full bg-[var(--fb-card-top)] px-2 py-0.5 font-medium text-[var(--fb-ink-secondary)]">{LESSON_LABEL[s.lesson_type] || s.lesson_type}</span>
      </div>
      <p className="w-full text-xs font-semibold leading-snug text-[var(--fb-ink)]">{s.subject_name}</p>
      <p className="flex w-full items-center gap-2 truncate text-[11px] text-[var(--fb-ink-muted)]">
        <span className="inline-flex items-center gap-1"><DoorOpen className="h-3 w-3" aria-hidden="true" />{s.room}</span>
        {s.teacher_name && <span className="inline-flex min-w-0 items-center gap-1 truncate"><UserRound className="h-3 w-3 shrink-0" aria-hidden="true" />{s.teacher_name}</span>}
      </p>
    </div>
  );
}

function EmptyState({ status }: { status: MyTimetable["status"] }) {
  const noEnrollment = status === "NO_VERIFIED_ENROLLMENT";
  return (
    <section className="fb-panel skeuo-card flex flex-col items-center gap-3 px-6 py-14 text-center">
      <span className="fb-avatar h-14 w-14" aria-hidden="true"><GraduationCap className="h-6 w-6" /></span>
      <h2 className="text-lg font-semibold text-[var(--fb-ink)]">
        {noEnrollment ? "Talabaligingiz hali tasdiqlanmagan" : "Universitet jadvalni hali joylamagan"}
      </h2>
      <p className="max-w-md text-sm text-[var(--fb-ink-secondary)]">
        {noEnrollment
          ? "O‘quv jadvali faqat universitet tasdiqlagan talabalarga ko‘rinadi. Profilingizdagi «HEMIS» bo‘limidan talabalikni tasdiqlashga yuboring."
          : "Koordinator jadvalni kiritishi bilan darslaringiz va ish uchun bo‘sh vaqtlaringiz shu yerda chiqadi."}
      </p>
      {noEnrollment && (
        <Link href="/nomzod" className="rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold">Profilga o‘tish</Link>
      )}
    </section>
  );
}

/** The student's own weekly class timetable, today's lessons and free work windows. */
export default function StudentTimetable({ data, now = new Date() }: { data: MyTimetable; now?: Date }) {
  const today = isoWeekday(now);
  const [day, setDay] = useState(today);

  const header = (
    <header className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <div className="min-w-0">
        <p className="text-sm text-[var(--fb-ink-muted)]">{data.institution_name || "Universitet"}</p>
        <h1 className="fb-display mt-1">O‘quv jadvali</h1>
        <p className="mt-2 text-sm text-[var(--fb-ink-secondary)]">
          {[data.group_code && `Guruh ${data.group_code}`, data.program, data.academic_semester].filter(Boolean).join(" · ") ||
            "Darslaringiz va ish uchun bo‘sh vaqtlaringiz"}
        </p>
      </div>
      <span className="fb-capsule inline-flex w-fit items-center gap-2 px-3.5 py-2 text-xs font-semibold">
        <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" /> {uzDate(now)}
      </span>
    </header>
  );

  if (data.status !== "OK") {
    return (
      <div className="flex flex-col gap-5">
        {header}
        <EmptyState status={data.status} />
      </div>
    );
  }

  const slots = data.slots;
  const days = DAYS.filter((d) => d.n <= 6 || classesOn(slots, 7).length > 0);
  const maxPara = Math.max(...slots.map((s) => s.para_number), 1);
  const paras = Array.from({ length: maxPara }, (_, i) => i + 1);
  const paraTime = (p: number) => slots.find((s) => s.para_number === p);
  const todayClasses = classesOn(slots, today);
  const next = currentOrNext(slots, now);
  const classMinutes = slots.reduce((sum, s) => sum + (s.end_minute - s.start_minute), 0);
  const freeMinutes = data.free_windows.reduce((sum, d) => sum + d.free_intervals.reduce((a, iv) => a + iv.duration_minutes, 0), 0);
  const selectedFree = data.free_windows.find((d) => d.weekday === day);

  return (
    <div className="flex flex-col gap-5">
      {header}

      {data.matched_by === "DEFAULT" && (
        <p className="fb-panel skeuo-card flex items-start gap-2 px-4 py-3 text-xs text-[var(--fb-ink-secondary)]">
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Guruhingiz yo‘nalish nomidan aniqlanmadi, shuning uchun universitetning {data.group_code} guruhi jadvali ko‘rsatilmoqda. Noto‘g‘ri bo‘lsa, koordinatoringizga yozing.
        </p>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <section data-skeuo-dark="true" className="fb-ink-card flex flex-col gap-3 p-5 sm:p-6" aria-labelledby="tt-next">
          <h2 id="tt-next" className="text-sm font-semibold fb-muted">{next?.inProgress ? "Hozir darsda" : "Keyingi dars"}</h2>
          {next ? (
            <>
              <p className="font-display text-2xl font-bold leading-tight">{next.slot.subject_name}</p>
              <p className="text-sm fb-muted tabular-nums">
                {next.slot.start_time}–{next.slot.end_time} · {next.slot.room}
              </p>
              {next.slot.teacher_name && <p className="text-xs fb-muted">{next.slot.teacher_name}</p>}
              <span className="mt-auto inline-flex w-fit rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold">
                {LESSON_LABEL[next.slot.lesson_type] || next.slot.lesson_type} · {next.slot.para_number}-para
              </span>
            </>
          ) : (
            <p className="text-lg font-semibold">Bugun boshqa dars yo‘q</p>
          )}
        </section>

        <section className="fb-panel skeuo-card flex flex-col gap-3 p-5 sm:p-6" aria-labelledby="tt-today">
          <h2 id="tt-today" className="text-base font-semibold text-[var(--fb-ink)]">Bugun</h2>
          {todayClasses.length === 0 ? (
            <p className="text-sm text-[var(--fb-ink-secondary)]">Darslar yo‘q — ish uchun to‘liq kun.</p>
          ) : (
            <ol className="flex flex-col gap-2">
              {todayClasses.map((s) => (
                <li key={`${s.start_minute}-${s.subject_name}`} className="flex items-center gap-3 text-xs">
                  <span className="w-20 shrink-0 tabular-nums text-[var(--fb-ink-muted)]">{s.start_time}–{s.end_time}</span>
                  <span className="min-w-0 flex-1 truncate font-semibold text-[var(--fb-ink)]">{s.subject_name}</span>
                  <span className="shrink-0 text-[var(--fb-ink-muted)]">{s.room}</span>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="fb-panel skeuo-card grid grid-cols-3 gap-3 p-5 sm:p-6" aria-label="Haftalik yuklama">
          {[
            { label: "Dars soni", value: slots.length, Icon: BookOpen },
            { label: "Dars soati", value: Math.round((classMinutes / 60) * 10) / 10, Icon: Clock3 },
            { label: "Ish uchun soat", value: Math.round((freeMinutes / 60) * 10) / 10, Icon: CalendarDays },
          ].map(({ label, value, Icon }) => (
            <div key={label} className="flex min-w-0 flex-col gap-1">
              <Icon className="h-4 w-4 text-[var(--fb-ink-muted)]" aria-hidden="true" />
              <span className="font-display text-2xl font-bold tabular-nums text-[var(--fb-ink)]">{value}</span>
              <span className="text-[11px] leading-tight text-[var(--fb-ink-muted)]">{label}<br />haftada</span>
            </div>
          ))}
        </section>
      </div>

      {/* Desktop: week grid (paras x days) */}
      <section className="fb-panel skeuo-card hidden p-5 sm:p-6 md:block" aria-labelledby="tt-week">
        <h2 id="tt-week" className="mb-4 text-base font-semibold text-[var(--fb-ink)]">Haftalik jadval</h2>
        <div className="grid gap-2" style={{ gridTemplateColumns: `72px repeat(${days.length}, minmax(0, 1fr))` }}>
          <span />
          {days.map((d) => (
            <span
              key={d.n}
              className={`rounded-full py-1.5 text-center text-xs font-semibold ${d.n === today ? "fb-nav-active" : "text-[var(--fb-ink-muted)]"}`}
              aria-current={d.n === today ? "date" : undefined}
            >
              {d.long}
            </span>
          ))}
          {paras.map((p) => {
            const t = paraTime(p);
            return (
              <React.Fragment key={p}>
                <div className="flex flex-col justify-center pr-1 text-[11px] text-[var(--fb-ink-muted)]">
                  <span className="font-semibold text-[var(--fb-ink-secondary)]">{p}-para</span>
                  {t && <span className="tabular-nums">{t.start_time}</span>}
                </div>
                {days.map((d) => {
                  const s = slots.find((x) => x.weekday === d.n && x.para_number === p);
                  return (
                    <div key={`${p}-${d.n}`} className={`min-h-[84px] rounded-[18px] ${d.n === today ? "bg-[color-mix(in_srgb,var(--fb-well-deep)_50%,transparent)]" : ""}`}>
                      {s ? <LessonCard s={s} dense /> : <span className="sr-only">Dars yo‘q</span>}
                    </div>
                  );
                })}
              </React.Fragment>
            );
          })}
        </div>
      </section>

      {/* Mobile: one day at a time */}
      <section className="fb-panel skeuo-card flex flex-col gap-3 p-4 md:hidden" aria-label="Kunlik jadval">
        <div className="fb-seg w-full justify-between overflow-x-auto no-scrollbar" role="group" aria-label="Hafta kuni">
          {days.map((d) => (
            <button key={d.n} type="button" aria-pressed={day === d.n} onClick={() => setDay(d.n)}>
              {d.short}
            </button>
          ))}
        </div>
        {classesOn(slots, day).length === 0 ? (
          <p className="py-6 text-center text-sm text-[var(--fb-ink-secondary)]">Bu kuni dars yo‘q.</p>
        ) : (
          classesOn(slots, day).map((s) => <LessonCard key={`${s.start_minute}-${s.subject_name}`} s={s} />)
        )}
        {selectedFree && selectedFree.free_intervals.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {selectedFree.free_intervals.map((iv) => (
              <span key={iv.start_minute} className="fb-bar px-3 py-1 text-[11px] font-semibold tabular-nums">Ish: {iv.start_time}–{iv.end_time}</span>
            ))}
          </div>
        )}
      </section>

      <section className="fb-panel skeuo-card p-5 sm:p-6 hidden md:block" aria-labelledby="tt-free">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="tt-free" className="text-base font-semibold text-[var(--fb-ink)]">Ish uchun bo‘sh oynalar</h2>
          <p className="text-xs text-[var(--fb-ink-muted)]">
            Darsdan oldin va keyin {data.commute_buffer_minutes ?? 30} daqiqa yo‘l vaqti qoldirilgan · ish beruvchilar smenani shunga moslaydi
          </p>
        </div>
        <ul className="grid grid-cols-2 gap-3 lg:grid-cols-6">
          {data.free_windows.map((d) => (
            <li key={d.weekday} className="flex flex-col gap-1.5">
              <span className={`text-xs font-semibold ${d.weekday === today ? "text-[var(--fb-ink)]" : "text-[var(--fb-ink-muted)]"}`}>{d.weekday_name}</span>
              {d.free_intervals.length === 0 ? (
                <span className="text-[11px] text-[var(--fb-ink-muted)]">Bo‘sh oyna yo‘q</span>
              ) : (
                d.free_intervals.map((iv) => (
                  <span key={iv.start_minute} className={`fb-bar px-3 py-1 text-center text-[11px] font-semibold tabular-nums ${d.weekday === today ? "fb-bar-today" : ""}`}>
                    {hhmm(iv.start_minute)}–{hhmm(iv.end_minute)}
                  </span>
                ))
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
