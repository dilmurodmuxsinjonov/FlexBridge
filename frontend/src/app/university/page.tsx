"use client";

import { useState } from "react";
import {
  Building2,
  FileText,
  Download,
  CheckCircle2,
  AlertTriangle,
  Send,
  Search,
  Filter,
  GraduationCap,
  Calendar,
  Clock,
  Award,
  ExternalLink,
  ShieldCheck,
  Check,
} from "lucide-react";
import { InternshipDiaryEntry } from "@/lib/api";

export default function UniversityPortal() {
  const [selectedStudent, setSelectedStudent] = useState<InternshipDiaryEntry>({
    student_id: "TATU-2021-0894",
    student_name: "Alisher Qodirov",
    university: "TATU (Dasturiy injiniring)",
    course: "4-kurs",
    company_name: "Uzum Market (Backend Python Dasturchi)",
    mentor_name: "Bekzod Aliyev (Senior Backend Architect)",
    week_number: 6,
    period: "10 - 15 Noyabr 2026",
    mentor_review:
      "Talaba FastAPI mikroservislarini PostgreSQL bilan integratsiyalash vazifasini a'lo darajada bajardi. Ish soatlariga qat'iy rioya qilmoqda (haftasiga 20 soat qonuniy me'yor). Mustaqil topshiriqlarni muddatidan oldin yakunladi.",
    mentor_score: 98,
    teacher_name: "Dotsent M. Ergashev (Dasturiy ta'minot kafedrasi)",
    teacher_review:
      "O'quv rejasidagi 'Ma'lumotlar bazasi arxitekturasi' va 'Taqsimlangan tizimlar' fanlari amaliy talablariga 100% to'liq mos keladi.",
    compliance_verified: true,
    hours_completed: 20,
    grade_score: 95,
    status: "verified_hemis",
  });

  const [confirmedHemis, setConfirmedHemis] = useState(false);

  const studentsList = [
    {
      id: "TATU-2021-0894",
      name: "Alisher Qodirov",
      faculty: "Dasturiy injiniring",
      course: "4-kurs",
      company: "Uzum Market",
      role: "Backend Python",
      mentor: "B. Aliyev",
      contract: "3 tomonlama tasdiqlangan",
      diary_status: "Barcha haftalar topshirilgan (100%)",
      score: 95,
      status_type: "verified",
    },
    {
      id: "TATU-2022-1140",
      name: "Shahnoza Rustamova",
      faculty: "Kiberxavfsizlik",
      course: "3-kurs",
      company: "Kapitalbank ATB",
      role: "SOC Analyst Intern",
      mentor: "M. Yusupov",
      contract: "Universitet imzosi kutilmoqda",
      diary_status: "3-hafta tekshiruvda",
      score: 91,
      status_type: "pending",
    },
    {
      id: "TATU-2021-0312",
      name: "Jasurbek Mirzayev",
      faculty: "Sun'iy intellekt",
      course: "4-kurs",
      company: "Payme",
      role: "Data Analyst",
      mentor: "D. Karimov",
      contract: "Faol",
      diary_status: "Kechikkan (2 kun)",
      score: 82,
      status_type: "warning",
    },
    {
      id: "TATU-2021-0551",
      name: "Nilufar Karimova",
      faculty: "Telekommunikatsiya",
      course: "4-kurs",
      company: "Uzum Tezkor",
      role: "DevOps Trainee",
      mentor: "K. Sodiqov",
      contract: "3 tomonlama tasdiqlangan",
      diary_status: "5-hafta topshirilgan",
      score: 94,
      status_type: "verified",
    },
    {
      id: "TATU-2022-0419",
      name: "Bobur Bekmurodov",
      faculty: "Dasturiy injiniring",
      course: "3-kurs",
      company: "EPAM Systems",
      role: "Java Junior",
      mentor: "A. Voronin",
      contract: "3 tomonlama tasdiqlangan",
      diary_status: "A'lo (100%)",
      score: 98,
      status_type: "verified",
    },
  ];

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* UNIVERSITY SUB-BAR & EXPORT ACTIONS */}
      <section className="w-full bg-surface-card border border-white/[0.08] rounded-lg p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                TATU Karyera Markazi
              </span>
              <span className="text-zinc-500 text-xs">
                • 2025-2026 o'quv yili amaliyoti
              </span>
            </div>
            <h1 className="font-heading text-lg md:text-xl font-bold text-zinc-100">
              Universitet Koordinatori va Talabalar Amaliyoti Nazorati Portali
            </h1>
            <p className="text-xs text-zinc-400">
              HEMIS API v3.2 sinxronizatsiyasi • 2,410 nafar ro'yxatdan o'tgan talaba
            </p>
          </div>

          {/* Action triggers */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="px-3 py-1.5 rounded bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-200 transition-all flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5 text-zinc-400" />
              <span>Forma №4-A (PDF)</span>
            </button>
            <button
              type="button"
              className="px-3 py-1.5 rounded bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-200 transition-all flex items-center gap-1.5"
            >
              <FileText className="w-3.5 h-3.5 text-zinc-400" />
              <span>HEMIS Eksport (JSON)</span>
            </button>
            <button
              type="button"
              className="px-3.5 py-1.5 rounded bg-primary hover:bg-primary-hover text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-sm active:scale-[0.98]"
            >
              <span>+ Yangi shartnoma</span>
            </button>
          </div>
        </div>

        {/* TELEMETRY KPI CARDS (4-column) */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 pt-4 border-t border-white/[0.06]">
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">Jami band talabalar</span>
            <div className="font-mono text-base font-bold text-zinc-100 mt-0.5">
              842 ta <span className="text-[11px] text-emerald-400 font-normal">(34.9%)</span>
            </div>
          </div>
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">Hamkor korxonalar</span>
            <div className="font-mono text-base font-bold text-primary mt-0.5">
              68 ta <span className="text-[11px] text-zinc-500 font-normal">(Uzum, KB, EPAM)</span>
            </div>
          </div>
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">O'rtacha oylik maosh</span>
            <div className="font-mono text-base font-bold text-emerald-400 mt-0.5">
              4,850,000 UZS
            </div>
          </div>
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">Kundalik topshirish intizomi</span>
            <div className="font-mono text-base font-bold text-amber-400 mt-0.5">
              94.2% <span className="text-[11px] text-zinc-500 font-normal">(19 kutilmoqda)</span>
            </div>
          </div>
        </div>
      </section>

      {/* DUAL-PANEL WORKSPACE (60% List + 40% Electronic Diary Inspection) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* LEFT SIDE: PLACEMENT LIST (7 columns) */}
        <div className="xl:col-span-7 flex flex-col gap-4">
          <div className="rounded-lg bg-surface-card border border-white/[0.08] overflow-hidden">
            {/* Table Filter Bar */}
            <div className="p-3.5 border-b border-white/[0.06] flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-zinc-200">
                  Talabalar Amaliyoti Taqsimoti
                </span>
                <span className="px-1.5 py-0.2 rounded bg-white/[0.06] text-[10px] font-mono text-zinc-400">
                  842 ta
                </span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Talaba ID yoki ism..."
                  className="px-2.5 py-1 bg-surface-lowest border border-white/[0.08] rounded text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-primary"
                />
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-white/[0.06] bg-surface-lowest text-zinc-400 font-semibold text-[11px]">
                    <th className="py-2.5 px-3">Talaba</th>
                    <th className="py-2.5 px-3">Korxona / Rol</th>
                    <th className="py-2.5 px-3">Shartnoma</th>
                    <th className="py-2.5 px-3">Kundalik</th>
                    <th className="py-2.5 px-3 text-right">Ball</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {studentsList.map((st) => {
                    const isSelected = selectedStudent.student_id === st.id;

                    return (
                      <tr
                        key={st.id}
                        onClick={() =>
                          setSelectedStudent({
                            ...selectedStudent,
                            student_id: st.id,
                            student_name: st.name,
                            university: `TATU (${st.faculty})`,
                            course: st.course,
                            company_name: `${st.company} (${st.role})`,
                            mentor_name: st.mentor,
                            grade_score: st.score,
                          })
                        }
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? "bg-primary/10 text-white"
                            : "hover:bg-white/[0.02] text-zinc-300"
                        }`}
                      >
                        <td className="py-3 px-3">
                          <span className="font-semibold text-zinc-100 block">
                            {st.name}
                          </span>
                          <span className="text-[10px] text-zinc-500 font-mono">
                            {st.faculty} • {st.course}
                          </span>
                        </td>
                        <td className="py-3 px-3">
                          <span className="text-zinc-200 block">{st.company}</span>
                          <span className="text-[10px] text-zinc-400">{st.role}</span>
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                              st.status_type === "verified"
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : st.status_type === "pending"
                                ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                                : "bg-red-500/10 text-red-400 border-red-500/20"
                            }`}
                          >
                            {st.contract}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-[11px] text-zinc-400">
                          {st.diary_status}
                        </td>
                        <td className="py-3 px-3 text-right font-mono font-bold text-zinc-100">
                          {st.score}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination footer */}
            <div className="p-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-zinc-400">
              <span>Ko'rsatilmoqda: 1 - 5 jami 842 ta talaba</span>
              <div className="flex gap-1">
                <button
                  type="button"
                  className="px-2 py-0.5 rounded bg-surface border border-white/[0.08]"
                >
                  1
                </button>
                <button
                  type="button"
                  className="px-2 py-0.5 rounded bg-surface border border-white/[0.08]"
                >
                  2
                </button>
                <button
                  type="button"
                  className="px-2 py-0.5 rounded bg-surface border border-white/[0.08]"
                >
                  ...
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT SIDE: ELECTRONIC DIARY INSPECTOR (5 columns) */}
        <aside className="xl:col-span-5 flex flex-col gap-4">
          <div className="p-4 rounded-lg bg-surface-card border border-white/[0.08]">
            {/* Header */}
            <div className="pb-3 border-b border-white/[0.06] flex items-start justify-between">
              <div>
                <span className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block">
                  Elektron Amaliyot Kundaligi
                </span>
                <h3 className="font-heading text-sm font-bold text-zinc-100">
                  {selectedStudent.student_name} — {selectedStudent.week_number}-hafta
                </h3>
                <span className="text-[10px] text-zinc-400 font-mono">
                  Davr: {selectedStudent.period}
                </span>
              </div>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono text-xs font-bold">
                {selectedStudent.grade_score} ball
              </span>
            </div>

            {/* Mentor Review Box */}
            <div className="mt-4 p-3 rounded bg-surface-lowest border border-white/[0.06]">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-zinc-200">
                  Korxona mentori taqrizi
                </span>
                <span className="text-[10px] text-emerald-400 font-mono font-bold">
                  {selectedStudent.mentor_score} / 100 ball
                </span>
              </div>
              <p className="text-xs text-zinc-300 italic leading-relaxed">
                "{selectedStudent.mentor_review}"
              </p>
              <div className="mt-2.5 pt-2 border-t border-white/[0.04] flex items-center justify-between text-[10px] text-zinc-400">
                <span>Mentor: {selectedStudent.mentor_name}</span>
                <span className="flex items-center gap-1 text-emerald-400">
                  <ShieldCheck className="w-3 h-3" /> E-IMZO tasdiqlangan
                </span>
              </div>
            </div>

            {/* Faculty Department Review Box */}
            <div className="mt-3 p-3 rounded bg-surface-lowest border border-white/[0.06]">
              <span className="text-xs font-semibold text-zinc-200 block mb-1">
                Kafedra ekspertizasi va o'quv rejasiga muvofiqligi
              </span>
              <p className="text-xs text-zinc-300 leading-relaxed">
                {selectedStudent.teacher_review}
              </p>
              <span className="text-[10px] text-zinc-400 block mt-2">
                Mas'ul: {selectedStudent.teacher_name}
              </span>
            </div>

            {/* Work hours check */}
            <div className="mt-3 p-2.5 rounded bg-surface-lowest border border-white/[0.06] flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-primary" />
                <span className="text-zinc-300">
                  Haftalik ish soati:{" "}
                  <strong className="text-zinc-100 font-mono">
                    {selectedStudent.hours_completed} soat
                  </strong>
                </span>
              </div>
              <span className="text-[10px] text-emerald-400 font-semibold font-mono">
                0% To'qnashuv
              </span>
            </div>

            {/* Confirmation CTA */}
            <div className="mt-4 flex flex-col gap-2">
              <button
                type="button"
                onClick={() => setConfirmedHemis(true)}
                className={`w-full py-2.5 rounded text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                  confirmedHemis
                    ? "bg-emerald-600 text-white"
                    : "bg-primary hover:bg-primary-hover text-white active:scale-[0.98]"
                }`}
              >
                {confirmedHemis ? (
                  <>
                    <Check className="w-4 h-4" />
                    <span>HEMIS tizimiga muvaffaqiyatli uzatildi!</span>
                  </>
                ) : (
                  <>
                    <Award className="w-4 h-4" />
                    <span>Rasmiy hisobotga kiritish va HEMIS ga uzatish (95 ball)</span>
                  </>
                )}
              </button>

              <button
                type="button"
                className="w-full py-2 rounded bg-surface hover:bg-surface-high border border-white/[0.08] text-zinc-300 text-xs font-medium transition-all"
              >
                Kafedra bayonnomasini yuklab olish (PDF)
              </button>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
