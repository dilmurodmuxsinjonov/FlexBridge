"use client";

import { useState } from "react";
import {
  Search,
  Filter,
  SlidersHorizontal,
  Bookmark,
  ChevronRight,
  ShieldCheck,
  Zap,
  Calendar,
  Clock,
  Building,
  GraduationCap,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  FileBadge,
} from "lucide-react";
import { fetchOpportunities, Opportunity } from "@/lib/api";

export default function StudentPortal() {
  const [activeTab, setActiveTab] = useState<"match" | "new" | "salary">("match");
  const [appliedJobs, setAppliedJobs] = useState<string[]>([]);
  const [savedJobs, setSavedJobs] = useState<string[]>([]);

  // Opportunities list
  const vacancies: Opportunity[] = [
    {
      id: "opp-001",
      title: "Junior Frontend Developer (Vue / React)",
      company_name: "Uzum Technologies",
      company_code: "UZ",
      accreditation_number: "UZ-448",
      location: "Toshkent sh. (Yashnobod)",
      salary_range: "4,500,000 - 6,000,000 UZS",
      shift_time: "14:30 - 18:30 (Darsdan keyin)",
      compatibility_score: 98,
      available_seats: 2,
      target_universities: "TATU, Inha, Amity 3-4 kurslar uchun tasdiqlangan kvota",
      work_mode: "0.5 stavka",
      verified: true,
      tags: ["React", "TypeScript", "Tailwind CSS", "Git"],
    },
    {
      id: "opp-002",
      title: "SMM & Kontent Kopirayter",
      company_name: "Korzinka Bosh Ofisi",
      company_code: "KZ",
      accreditation_number: "KZ-102",
      location: "Toshkent sh. (Mirobod tumani)",
      salary_range: "3,200,000 UZS / oy",
      shift_time: "Moslashuvchan 20 soat / hafta",
      compatibility_score: 92,
      available_seats: 4,
      target_universities: "O'zDJTU, O'zMU talabalari uchun tasdiqlangan",
      work_mode: "Gibrid",
      verified: true,
      tags: ["Kopirayting", "SMM", "Kreativ", "Gibrid"],
    },
    {
      id: "opp-003",
      title: "Moliya va Audit Amaliyotchisi (Intern)",
      company_name: "Kapitalbank ATB",
      company_code: "KB",
      accreditation_number: "KB-771",
      location: "Toshkent sh. (Sayilgoh filiali)",
      salary_range: "3,800,000 UZS / oy",
      shift_time: "09:00 - 13:00 (Ertalabki smena)",
      compatibility_score: 89,
      available_seats: 1,
      target_universities: "TDIU, Jahon Iqtisodiyoti 3-4 kurs talabalari uchun",
      work_mode: "Akademik amaliyot",
      verified: true,
      tags: ["Audit", "IFRS", "Excel", "Bank ishi"],
    },
    {
      id: "opp-004",
      title: "Data Analyst Intern (SQL & Python)",
      company_name: "Payme (Inspire Group)",
      company_code: "PM",
      accreditation_number: "PM-314",
      location: "Masofaviy / Toshkent",
      salary_range: "5,000,000 UZS / oy",
      shift_time: "Masofaviy (Remote) • Erkin grafik (20s/hafta)",
      compatibility_score: 95,
      available_seats: 3,
      target_universities: "Barcha IT va Matematika yo'nalishlari talabalari",
      work_mode: "Remote",
      verified: true,
      tags: ["Python", "PostgreSQL", "Pandas", "Metabase"],
    },
  ];

  const handleApply = (id: string) => {
    if (!appliedJobs.includes(id)) {
      setAppliedJobs([...appliedJobs, id]);
    }
  };

  const handleToggleSave = (id: string) => {
    if (savedJobs.includes(id)) {
      setSavedJobs(savedJobs.filter((item) => item !== id));
    } else {
      setSavedJobs([...savedJobs, id]);
    }
  };

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* HERO COMMAND CENTER (Matrix Search & Fast Filters) */}
      <section className="w-full bg-surface-card border border-white/[0.08] rounded-lg p-4 backdrop-blur-md">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center gap-3">
          {/* Main search input */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <input
              type="text"
              defaultValue="Frontend React"
              placeholder="Lavozim yoki ko'nikma (Frontend, Python, Ma'lumotlar tahlili...)"
              className="w-full pl-9 pr-4 py-2 bg-surface-lowest border border-white/[0.1] rounded text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-primary transition-all font-sans"
            />
          </div>

          <div className="h-px lg:h-8 lg:w-px bg-white/[0.08] hidden lg:block" />

          {/* Selectors Cluster */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 items-center">
            {/* Region */}
            <select className="w-full appearance-none px-3 py-2 bg-surface-lowest border border-white/[0.1] rounded text-xs text-zinc-200 cursor-pointer focus:outline-none focus:border-primary">
              <option>Toshkent sh.</option>
              <option>Samarqand</option>
              <option>Farg'ona</option>
              <option>Buxoro</option>
            </select>

            {/* Contract Type */}
            <select className="w-full appearance-none px-3 py-2 bg-surface-lowest border border-white/[0.1] rounded text-xs text-zinc-200 cursor-pointer focus:outline-none focus:border-primary">
              <option>Yarim stavka (0.5)</option>
              <option>Akademik amaliyot</option>
              <option>Moslashuvchan smena</option>
            </select>

            {/* Mode switch */}
            <div className="col-span-2 sm:col-span-1 flex items-center bg-surface-lowest p-0.5 rounded border border-white/[0.1]">
              <button
                type="button"
                className="flex-1 py-1 text-center text-[11px] rounded bg-white/[0.08] text-primary font-semibold"
              >
                Barchasi
              </button>
              <button
                type="button"
                className="flex-1 py-1 text-center text-[11px] rounded text-zinc-400 hover:text-zinc-200"
              >
                Gibrid
              </button>
              <button
                type="button"
                className="flex-1 py-1 text-center text-[11px] rounded text-zinc-400 hover:text-zinc-200"
              >
                Remote
              </button>
            </div>
          </div>

          {/* Action trigger */}
          <button
            type="button"
            className="px-4 py-2 rounded bg-primary hover:bg-primary-hover text-white text-xs font-semibold flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Filtrlash</span>
            <span className="px-1.5 py-0.2 rounded bg-blue-900/40 text-[10px] font-mono">
              142
            </span>
          </button>
        </div>

        {/* Micro-pills */}
        <div className="mt-3 pt-3 border-t border-white/[0.06] flex flex-wrap items-center gap-2 text-xs">
          <span className="text-zinc-500 uppercase text-[10px] tracking-wider font-semibold">
            Tezkor filter:
          </span>
          <button
            type="button"
            className="px-2 py-0.5 rounded bg-surface text-zinc-300 hover:text-primary border border-white/[0.06] flex items-center gap-1.5 text-[11px]"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Darsdan keyingi smena (14:00+)</span>
          </button>
          <button
            type="button"
            className="px-2 py-0.5 rounded bg-surface text-zinc-300 hover:text-primary border border-white/[0.06] text-[11px]"
          >
            Stajirovka shartnomasi bilan
          </button>
          <button
            type="button"
            className="px-2 py-0.5 rounded bg-surface text-zinc-300 hover:text-primary border border-white/[0.06] text-[11px]"
          >
            Maosh &gt; 4,000,000 UZS
          </button>
        </div>
      </section>

      {/* 2-COLUMN MAIN WORKSPACE (70% Feed + 30% Analytical Sidebar) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT FEED (8 columns) */}
        <section className="lg:col-span-8 flex flex-col gap-4">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-white/[0.08] gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-heading text-lg font-bold text-zinc-100">
                  Tasdiqlangan Bo'sh Ish O'rinlari
                </h1>
                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-semibold">
                  Rasmiy akkreditatsiyalangan
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-0.5">
                O'zbekiston Respublikasi Mehnat va Oliy Ta'lim vazirliklari reestridan{" "}
                <span className="font-mono text-zinc-200 font-semibold">142 ta</span> faol vakansiya
              </p>
            </div>

            {/* Sorting Tabs */}
            <div className="flex items-center gap-1 bg-surface-lowest p-1 rounded border border-white/[0.08] self-start sm:self-auto text-xs">
              <button
                type="button"
                onClick={() => setActiveTab("match")}
                className={`px-2.5 py-1 rounded font-medium transition-all ${
                  activeTab === "match"
                    ? "bg-white/[0.08] text-primary font-semibold"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Eng mos keluvchi
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("new")}
                className={`px-2.5 py-1 rounded font-medium transition-all ${
                  activeTab === "new"
                    ? "bg-white/[0.08] text-primary font-semibold"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Yangi qo'shilgan
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("salary")}
                className={`px-2.5 py-1 rounded font-medium transition-all ${
                  activeTab === "salary"
                    ? "bg-white/[0.08] text-primary font-semibold"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Yuqori maosh
              </button>
            </div>
          </div>

          {/* VACANCY CARDS FEED */}
          <div className="space-y-3.5">
            {vacancies.map((job) => {
              const isApplied = appliedJobs.includes(job.id);
              const isSaved = savedJobs.includes(job.id);

              return (
                <article
                  key={job.id}
                  className="p-4 md:p-5 rounded-lg bg-surface-card border border-white/[0.08] hover:border-primary/40 transition-all duration-200 relative group"
                >
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    <div className="flex items-start gap-3.5 flex-1">
                      {/* Company Avatar Badge */}
                      <div className="w-11 h-11 rounded-lg bg-surface-container border border-white/[0.1] flex items-center justify-center shrink-0 text-primary font-bold text-sm tracking-wider">
                        {job.company_code}
                      </div>

                      <div className="flex-1 min-w-0">
                        {/* Company Name & Accreditation */}
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <span className="text-xs font-semibold text-zinc-200">
                            {job.company_name}
                          </span>
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-semibold">
                            <ShieldCheck className="w-3 h-3" />
                            <span>Akkreditatsiya №{job.accreditation_number}</span>
                          </span>
                          <span className="text-zinc-500 text-[11px]">
                            • {job.location}
                          </span>
                        </div>

                        {/* Vacancy Title */}
                        <h2 className="font-heading text-sm md:text-base font-bold text-zinc-100 group-hover:text-primary transition-colors">
                          {job.title}
                        </h2>

                        {/* Metrics Grid */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-1.5 gap-x-4 mt-3 pt-3 border-t border-white/[0.06] text-xs">
                          <div className="flex items-center gap-2 text-zinc-200">
                            <span className="text-zinc-400">Maosh:</span>
                            <span className="font-mono font-semibold text-primary">
                              {job.salary_range}
                            </span>
                            <span className="text-zinc-500 text-[10px]">
                              ({job.work_mode})
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-zinc-300">
                            <Clock className="w-3.5 h-3.5 text-zinc-400" />
                            <span>
                              {job.shift_time}{" "}
                              <span className="text-emerald-400 font-medium">
                                (Darsdan keyin)
                              </span>
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-zinc-400 sm:col-span-2 text-[11px]">
                            <GraduationCap className="w-3.5 h-3.5 text-zinc-500" />
                            <span>{job.target_universities}</span>
                          </div>
                        </div>

                        {/* Tags */}
                        <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                          {job.tags.map((tag) => (
                            <span
                              key={tag}
                              className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] text-zinc-300 text-[10px] font-mono"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Right Gauges & CTA Cluster */}
                    <div className="flex md:flex-col items-center md:items-end justify-between md:justify-start gap-3 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-white/[0.06]">
                      {/* Compatibility Gauge */}
                      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
                        <Zap className="w-3.5 h-3.5" />
                        <span className="font-mono font-bold">
                          {job.compatibility_score}% Moslik
                        </span>
                      </div>

                      <div className="text-[10px] text-amber-400 font-mono bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                        {job.available_seats} ta kvota qoldi
                      </div>

                      {/* CTA Buttons */}
                      <div className="flex items-center gap-2 mt-auto">
                        <button
                          type="button"
                          onClick={() => handleToggleSave(job.id)}
                          aria-label="Saqlab qo'yish"
                          className={`p-2 rounded border transition-colors ${
                            isSaved
                              ? "bg-primary/20 border-primary text-primary"
                              : "bg-surface-lowest border-white/[0.08] text-zinc-400 hover:text-white"
                          }`}
                        >
                          <Bookmark className="w-3.5 h-3.5" />
                        </button>

                        <button
                          type="button"
                          onClick={() => handleApply(job.id)}
                          disabled={isApplied}
                          className={`px-3.5 py-1.5 rounded text-xs font-semibold flex items-center gap-1 transition-all active:scale-[0.98] ${
                            isApplied
                              ? "bg-emerald-600/30 text-emerald-300 border border-emerald-500/40"
                              : "bg-primary hover:bg-primary-hover text-white"
                          }`}
                        >
                          {isApplied ? (
                            <>
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                              <span>Ariza yuborildi</span>
                            </>
                          ) : (
                            <>
                              <span>Ariza topshirish</span>
                              <ChevronRight className="w-3.5 h-3.5" />
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between pt-3 pb-6 border-t border-white/[0.08] text-xs text-zinc-400">
            <span>
              Ko'rsatilmoqda: <strong className="text-zinc-200 font-mono">1 - 4</strong> jami{" "}
              <strong className="text-zinc-200 font-mono">142</strong> ta vakansiya
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                className="px-2.5 py-1 rounded bg-surface border border-white/[0.08] text-zinc-400 disabled:opacity-40"
                disabled
              >
                Oldingi
              </button>
              <button
                type="button"
                className="px-2.5 py-1 rounded bg-primary text-white font-semibold font-mono"
              >
                1
              </button>
              <button
                type="button"
                className="px-2.5 py-1 rounded bg-surface border border-white/[0.08] text-zinc-300 hover:text-white font-mono"
              >
                2
              </button>
              <button
                type="button"
                className="px-2.5 py-1 rounded bg-surface border border-white/[0.08] text-zinc-300 hover:text-white"
              >
                Keyingi
              </button>
            </div>
          </div>
        </section>

        {/* RIGHT ANALYTICAL SIDEBAR (4 columns) */}
        <aside className="lg:col-span-4 flex flex-col gap-4">
          {/* WIDGET 1: Neuro-Match & Schedule Gauge */}
          <div className="p-4 rounded-lg bg-surface-card border border-white/[0.08]">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-0.5">
                  Shaxsiy Neyro-Moslik
                </span>
                <h3 className="font-heading text-sm font-bold text-zinc-100">
                  Mening Moslik Ko'rsatkichim
                </h3>
              </div>
              <div className="w-12 h-12 rounded-full border-2 border-emerald-500/40 flex items-center justify-center bg-emerald-500/10 shrink-0">
                <span className="font-mono text-base font-bold text-emerald-400">
                  96%
                </span>
              </div>
            </div>

            <div className="mt-3 text-xs text-zinc-300 bg-surface-lowest p-3 rounded border border-white/[0.06]">
              <div className="flex items-center gap-2 mb-1.5 text-zinc-100 font-medium">
                <Calendar className="w-3.5 h-3.5 text-primary" />
                <span>Dars jadvali: 08:30 - 13:30 (Kunduzgi)</span>
              </div>
              <p className="text-zinc-400 text-[11px] leading-relaxed">
                TATU dars jadvalingiz bilan to'qnashmaydigan{" "}
                <strong className="text-zinc-200">18 ta</strong> akkreditatsiyalangan
                kompaniya smenasi aniqlandi.
              </p>
            </div>

            <div className="mt-3 flex items-center justify-between text-[11px]">
              <span className="text-zinc-500">HEMIS sinx: Bugun, 09:12</span>
              <span className="text-primary hover:underline font-semibold cursor-pointer">
                Jadvalni yangilash
              </span>
            </div>
          </div>

          {/* WIDGET 2: Daily Diary Submission Tracker */}
          <div className="p-4 rounded-lg bg-surface-card border border-white/[0.08]">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-primary" />
                <h3 className="font-heading text-sm font-bold text-zinc-100">
                  Akademik Amaliyot Statusi
                </h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                Faol
              </span>
            </div>

            {/* Progress */}
            <div className="mt-3">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-zinc-400">Kundalik monitoringi (Modul-1)</span>
                <span className="font-mono font-semibold text-zinc-200">
                  14/20 kun (70%)
                </span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-surface-lowest overflow-hidden">
                <div className="h-full bg-gradient-to-r from-primary to-emerald-400 w-[70%]" />
              </div>
            </div>

            {/* Alert */}
            <div className="mt-3 p-3 rounded bg-surface-lowest border border-white/[0.06] flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-medium text-zinc-200">
                  Bugungi amaliyot kundaligi topshirilmagan
                </p>
                <p className="text-[11px] text-zinc-400 mt-0.5">
                  Topshirish muddati: Bugun soat{" "}
                  <span className="font-mono text-amber-400 font-semibold">21:00</span> gacha
                </p>
              </div>
            </div>

            {/* Curator info */}
            <div className="mt-3 text-[11px] flex items-center justify-between text-zinc-400 py-2 border-y border-white/[0.06]">
              <span>Kompaniya kuratori:</span>
              <span className="text-zinc-200 font-semibold flex items-center gap-1">
                Sanjar Karimov
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              </span>
            </div>

            <button
              type="button"
              className="w-full mt-3 py-2 rounded bg-surface hover:bg-surface-high border border-white/[0.1] text-zinc-200 text-xs font-semibold transition-all active:scale-[0.98]"
            >
              Bugungi hisobotni yozish
            </button>
          </div>
        </aside>
      </div>
    </main>
  );
}
