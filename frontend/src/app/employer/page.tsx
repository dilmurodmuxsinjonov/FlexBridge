"use client";

import { useState } from "react";
import {
  Users,
  Briefcase,
  Clock,
  Calendar,
  CheckCircle2,
  FileCheck,
  Filter,
  Plus,
  Search,
  ExternalLink,
  ChevronRight,
  ShieldAlert,
  ArrowRight,
  Building,
  GraduationCap,
  Sparkles,
} from "lucide-react";
import { CandidateApplication } from "@/lib/api";

export default function EmployerPortal() {
  const [candidates, setCandidates] = useState<CandidateApplication[]>([
    {
      id: "cand-1",
      student_name: "Azizbek Rahimov",
      student_id: "TATU-2022-0814",
      university: "TATU",
      course: "3-kurs (Kompyuter injiniringi)",
      gpa: 4.62,
      match_score: 96,
      shift_compatibility: "To‘liq mos",
      stage: "new",
      skills: ["Python", "FastAPI", "PostgreSQL", "Git"],
      submission_date: "Bugun, 10:24",
    },
    {
      id: "cand-2",
      student_name: "Madina Karimova",
      student_id: "INHA-2022-0312",
      university: "Inha University",
      course: "3-kurs (CSE)",
      gpa: 4.75,
      match_score: 94,
      shift_compatibility: "To‘liq mos",
      stage: "new",
      skills: ["Python", "Django", "Docker", "REST API"],
      submission_date: "Bugun, 08:15",
    },
    {
      id: "cand-3",
      student_name: "Javohir Usmonov",
      student_id: "AMITY-2021-0491",
      university: "Amity University",
      course: "4-kurs (IT)",
      gpa: 4.4,
      match_score: 91,
      shift_compatibility: "To‘liq mos",
      stage: "review",
      skills: ["Python", "Redis", "Asyncio", "Linux"],
      submission_date: "Kecha",
      mentor: "B. Aliyev (Lead Architect)",
    },
    {
      id: "cand-4",
      student_name: "Farrux Toirov",
      student_id: "TATU-2022-0199",
      university: "TATU",
      course: "3-kurs (Dasturiy injiniring)",
      gpa: 4.55,
      match_score: 95,
      shift_compatibility: "To‘liq mos",
      stage: "interview",
      skills: ["Python", "PostgreSQL", "FastAPI"],
      submission_date: "2 kun oldin",
      interview_time: "Bugun, 15:30 (Google Meet)",
      mentor: "B. Aliyev (Senior Backend)",
    },
    {
      id: "cand-5",
      student_name: "Nilufar Sobirova",
      student_id: "TATU-2022-0640",
      university: "TATU",
      course: "3-kurs (Kiberxavfsizlik)",
      gpa: 4.8,
      match_score: 97,
      shift_compatibility: "To‘liq mos",
      stage: "offered",
      skills: ["Python", "Cryptography", "Network"],
      submission_date: "4 kun oldin",
      mentor: "M. Yusupov (Security Tech)",
    },
  ]);

  const [selectedCandidate, setSelectedCandidate] = useState<CandidateApplication>(
    candidates[0]
  );

  const moveCandidate = (id: string, newStage: CandidateApplication["stage"]) => {
    setCandidates((prev) =>
      prev.map((c) => (c.id === id ? { ...c, stage: newStage } : c))
    );
  };

  const stages: { key: CandidateApplication["stage"]; title: string; count: number }[] = [
    { key: "new", title: "Yangi arizalar", count: candidates.filter((c) => c.stage === "new").length },
    { key: "review", title: "Ko'rib chiqilmoqda / Test", count: candidates.filter((c) => c.stage === "review").length },
    { key: "interview", title: "Suhbat bosqichi", count: candidates.filter((c) => c.stage === "interview").length },
    { key: "offered", title: "Taklif & Qabul", count: candidates.filter((c) => c.stage === "offered").length },
  ];

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* VACANCY CONTEXT HEADER */}
      <section className="w-full bg-surface-card border border-white/[0.08] rounded-lg p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                Uzum Technologies HR Hub
              </span>
              <span className="text-zinc-500 text-xs">• Mirzo Ulug'bek filiali</span>
              <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                14 ta faol vakansiya
              </span>
            </div>
            <h1 className="font-heading text-lg md:text-xl font-bold text-zinc-100">
              Junior Backend Python Dasturchi (Talabalar uchun moslashtirilgan)
            </h1>
            <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-400">
              <span>Smena: 14:00 - 18:00 (0.5 stavka)</span>
              <span>•</span>
              <span>Davlat akkreditatsiyasi №UZ-448</span>
              <span>•</span>
              <span className="text-emerald-400 font-semibold">Dual ta'lim dasturi faol</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              className="px-3.5 py-2 rounded bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-200 transition-all flex items-center gap-1.5"
            >
              <Filter className="w-3.5 h-3.5 text-zinc-400" />
              <span>Universitetlar</span>
            </button>
            <button
              type="button"
              className="px-3.5 py-2 rounded bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-200 transition-all flex items-center gap-1.5"
            >
              <FileCheck className="w-3.5 h-3.5 text-zinc-400" />
              <span>Eksport (CSV)</span>
            </button>
            <button
              type="button"
              className="px-4 py-2 rounded bg-primary hover:bg-primary-hover text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-sm active:scale-[0.98]"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Yangi vakansiya</span>
            </button>
          </div>
        </div>

        {/* METRICS ROW */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 pt-4 border-t border-white/[0.06]">
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">Jami arizalar</span>
            <div className="font-mono text-base font-bold text-zinc-100 mt-0.5">
              38 ta <span className="text-[11px] text-emerald-400 font-normal">(+12 bugun)</span>
            </div>
          </div>
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">O'rtacha neyro-moslik</span>
            <div className="font-mono text-base font-bold text-emerald-400 mt-0.5">
              92.4%
            </div>
          </div>
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">O'rtacha GPA</span>
            <div className="font-mono text-base font-bold text-primary mt-0.5">
              4.45 <span className="text-[11px] text-zinc-500 font-normal">(TATU, Inha)</span>
            </div>
          </div>
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">Kvota holati</span>
            <div className="font-mono text-base font-bold text-amber-400 mt-0.5">
              4 ta bo'sh o'rin
            </div>
          </div>
        </div>
      </section>

      {/* DUAL-PANEL KANBAN & COLLISION INSPECTOR */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* KANBAN BOARD (8 columns on XL) */}
        <div className="xl:col-span-8 flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {stages.map((stg) => {
              const stageCandidates = candidates.filter((c) => c.stage === stg.key);

              return (
                <div
                  key={stg.key}
                  className="flex flex-col rounded-lg bg-surface-card border border-white/[0.08] min-h-[500px]"
                >
                  {/* Column Header */}
                  <div className="p-3 border-b border-white/[0.06] flex items-center justify-between">
                    <span className="text-xs font-semibold text-zinc-200">
                      {stg.title}
                    </span>
                    <span className="px-1.5 py-0.2 rounded bg-white/[0.06] text-[10px] font-mono text-zinc-400">
                      {stageCandidates.length}
                    </span>
                  </div>

                  {/* Cards Container */}
                  <div className="p-2.5 flex-1 flex flex-col gap-2.5 overflow-y-auto">
                    {stageCandidates.length === 0 ? (
                      <div className="text-center py-10 text-[11px] text-zinc-500">
                        Hozircha nomzod yo'q
                      </div>
                    ) : (
                      stageCandidates.map((cand) => {
                        const isSelected = selectedCandidate.id === cand.id;

                        return (
                          <div
                            key={cand.id}
                            onClick={() => setSelectedCandidate(cand)}
                            className={`p-3 rounded bg-surface-lowest border cursor-pointer transition-all ${
                              isSelected
                                ? "border-primary ring-1 ring-primary shadow-sm"
                                : "border-white/[0.06] hover:border-white/[0.15]"
                            }`}
                          >
                            {/* Candidate top info */}
                            <div className="flex items-start justify-between gap-1 mb-1.5">
                              <div>
                                <h4 className="text-xs font-bold text-zinc-100 hover:text-primary transition-colors">
                                  {cand.student_name}
                                </h4>
                                <span className="text-[10px] text-zinc-400 font-mono">
                                  {cand.university} • {cand.course}
                                </span>
                              </div>
                              <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono font-bold">
                                {cand.match_score}%
                              </span>
                            </div>

                            {/* GPA & Shift Info */}
                            <div className="flex items-center justify-between text-[11px] text-zinc-400 py-1.5 my-1.5 border-y border-white/[0.04]">
                              <span>
                                GPA: <strong className="text-zinc-200 font-mono">{cand.gpa}</strong>
                              </span>
                              <span className="text-emerald-400 text-[10px]">
                                {cand.shift_compatibility}
                              </span>
                            </div>

                            {/* Skills */}
                            <div className="flex flex-wrap gap-1 mb-2">
                              {cand.skills.slice(0, 3).map((s) => (
                                <span
                                  key={s}
                                  className="px-1.5 py-0.2 rounded bg-white/[0.04] text-[9px] font-mono text-zinc-300"
                                >
                                  {s}
                                </span>
                              ))}
                            </div>

                            {/* Quick Action Transitions */}
                            <div className="flex items-center justify-between pt-1 text-[10px]">
                              {cand.stage === "new" && (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    moveCandidate(cand.id, "review");
                                  }}
                                  className="w-full py-1 rounded bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 font-semibold transition-all text-center"
                                >
                                  Testga o'tkazish →
                                </button>
                              )}
                              {cand.stage === "review" && (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    moveCandidate(cand.id, "interview");
                                  }}
                                  className="w-full py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/20 font-semibold transition-all text-center"
                                >
                                  Suhbat belgilash →
                                </button>
                              )}
                              {cand.stage === "interview" && (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    moveCandidate(cand.id, "offered");
                                  }}
                                  className="w-full py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 font-semibold transition-all text-center"
                                >
                                  Taklif yuborish (Offer) →
                                </button>
                              )}
                              {cand.stage === "offered" && (
                                <span className="w-full py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-center font-semibold">
                                  Shartnoma imzolanmoqda
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT DRAWER: SCHEDULE COLLISION INSPECTOR (4 columns on XL) */}
        <aside className="xl:col-span-4 flex flex-col gap-4">
          <div className="p-4 rounded-lg bg-surface-card border border-white/[0.08]">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div>
                <span className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block">
                  Dars va Ish Grafigi Sinxroni
                </span>
                <h3 className="font-heading text-sm font-bold text-zinc-100">
                  {selectedCandidate.student_name} ({selectedCandidate.university})
                </h3>
              </div>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono text-xs font-bold">
                {selectedCandidate.match_score}% Mos
              </span>
            </div>

            {/* Time Grid Comparison */}
            <div className="mt-4 flex flex-col gap-2">
              <span className="text-[11px] text-zinc-400 font-medium">
                Haftalik grafik tahlili (Dushanba - Juma):
              </span>

              {/* Block 1: Academic Classes */}
              <div className="p-3 rounded bg-surface-lowest border border-white/[0.06] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-indigo-400" />
                  <div>
                    <span className="text-xs font-medium text-zinc-200 block">
                      Universitet darslari (HEMIS)
                    </span>
                    <span className="text-[10px] text-zinc-400 font-mono">
                      08:30 - 13:30 (Kunduzgi)
                    </span>
                  </div>
                </div>
                <span className="text-[10px] text-zinc-400 font-mono">Band</span>
              </div>

              {/* Block 2: Transition / Lunch */}
              <div className="p-2 px-3 rounded bg-surface-lowest/50 border border-dashed border-white/[0.06] flex items-center justify-between">
                <span className="text-[10px] text-zinc-400">Tushlik va yo'l vaqti</span>
                <span className="text-[10px] text-zinc-400 font-mono">13:30 - 14:00 (30 daq.)</span>
              </div>

              {/* Block 3: Work Shift */}
              <div className="p-3 rounded bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400" />
                  <div>
                    <span className="text-xs font-semibold text-emerald-300 block">
                      Korxona ish smenasi (Uzum)
                    </span>
                    <span className="text-[10px] text-emerald-400 font-mono">
                      14:00 - 18:00 (4 soat/kun)
                    </span>
                  </div>
                </div>
                <span className="text-[10px] text-emerald-400 font-semibold font-mono">
                  100% Mos
                </span>
              </div>
            </div>

            {/* Compliance Guarantee */}
            <div className="mt-4 p-3 rounded bg-surface-lowest border border-white/[0.06] flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <p className="text-[11px] text-zinc-300 leading-relaxed">
                O'zbekiston Respublikasi <strong>Mehnat Kodeksi 118-moddasi</strong>ga
                muvofiq talaba uchun haftalik 20 soatlik norma to'liq ta'minlangan.
              </p>
            </div>

            {/* Mentor Assignment */}
            <div className="mt-4 pt-3 border-t border-white/[0.06] flex flex-col gap-2">
              <span className="text-[11px] text-zinc-400 font-medium">
                Biriktirilgan korxona mentori:
              </span>
              <div className="p-2.5 rounded bg-surface-lowest border border-white/[0.06] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded bg-zinc-800 flex items-center justify-center text-xs font-semibold text-primary">
                    BA
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-zinc-200 block">
                      Bekzod Aliyev
                    </span>
                    <span className="text-[10px] text-zinc-400">
                      Senior Backend Architect
                    </span>
                  </div>
                </div>
                <span className="text-[10px] text-primary hover:underline cursor-pointer">
                  O'zgartirish
                </span>
              </div>
            </div>

            <button
              type="button"
              className="w-full mt-4 py-2 rounded bg-primary hover:bg-primary-hover text-white text-xs font-semibold transition-all active:scale-[0.98]"
            >
              Uchrashuv va sinov topshirig'ini tasdiqlash
            </button>
          </div>
        </aside>
      </div>
    </main>
  );
}
