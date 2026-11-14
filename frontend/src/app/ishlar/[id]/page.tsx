"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Building2,
  ShieldCheck,
  MapPin,
  BriefcaseBusiness,
  Clock3,
  CalendarDays,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Send,
  Loader2,
  FileText,
  UserCheck,
} from "lucide-react";
import {
  fetchOpportunityDetail,
  submitOpportunityApplication,
  fetchAuthMe,
  OpportunityDetail,
  AuthUser,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";

const weekdayNames: Record<number, string> = {
  1: "Dushanba",
  2: "Seshanba",
  3: "Chorshanba",
  4: "Payshanba",
  5: "Juma",
  6: "Shanba",
  7: "Yakshanba",
};

function formatMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
}

export default function OpportunityDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const [opportunity, setOpportunity] = useState<OpportunityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Auth & Application State
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [applicationModalOpen, setApplicationModalOpen] = useState(false);
  const [applicationNote, setApplicationNote] = useState("");
  const [scheduleConfirmed, setScheduleConfirmed] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<{ id: string } | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const [oppData, userData] = await Promise.all([
          fetchOpportunityDetail(id),
          fetchAuthMe(),
        ]);
        if (active) {
          setOpportunity(oppData);
          setUser(userData);
        }
      } catch (err: unknown) {
        if (active) {
          const message = err instanceof Error ? err.message : "E'lonni yuklab bo'lmadi";
          setError(message);
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadData();
    return () => {
      active = false;
    };
  }, [id]);

  const handleApplyClick = () => {
    if (!user) {
      setAuthModalOpen(true);
    } else {
      setApplicationModalOpen(true);
    }
  };

  const handleAuthSuccess = async () => {
    const freshUser = await fetchAuthMe();
    setUser(freshUser);
    setAuthModalOpen(false);
    setApplicationModalOpen(true);
  };

  const handleApplicationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!opportunity) return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await submitOpportunityApplication(opportunity.id, {
        note: applicationNote.trim() || undefined,
      });
      setSubmitSuccess({ id: res.application_id || "yangi" });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Ariza topshirishda xatolik yuz berdi";
      setSubmitError(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12">
        <div className="flex flex-col items-center justify-center rounded-2xl border border-white/[0.08] bg-surface-card p-16 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="mt-4 text-sm font-medium text-zinc-300">Vakansiya tafsilotlari yuklanmoqda...</p>
        </div>
      </main>
    );
  }

  if (error || !opportunity) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12">
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/[0.05] p-12 text-center">
          <AlertCircle className="mx-auto h-10 w-10 text-amber-400" />
          <h1 className="mt-4 text-lg font-bold text-white">E’lon topilmadi yoki yopilgan</h1>
          <p className="mt-2 text-sm text-zinc-400">
            {error || "Ushbu identifikator bo‘yicha e’lon mavjud emas."}
          </p>
          <div className="mt-6">
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-lg border border-white/[0.1] bg-surface-lowest px-4 py-2 text-sm font-semibold text-zinc-200 transition-colors hover:border-primary/50"
            >
              <ArrowLeft className="h-4 w-4" /> Bosh sahifaga qaytish
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const rev = opportunity.revision;
  const isPartTime = opportunity.kind === "PART_TIME";
  const formattedSalary =
    rev.salary_min !== null
      ? `${rev.salary_min.toLocaleString("uz-UZ")} ${rev.currency}`
      : "Kelishuv asosida";

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      {/* Breadcrumb Navigation */}
      <nav aria-label="Breadcrumb" className="mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs font-semibold text-zinc-400 transition-colors hover:text-primary"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Barcha e’lonlarga qaytish
        </Link>
      </nav>

      {/* Main Header Card */}
      <section className="rounded-2xl border border-white/[0.08] bg-surface-card p-6 lg:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-primary">
              <Building2 className="h-7 w-7" aria-hidden="true" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-zinc-200">
                  {opportunity.organization.name}
                </span>
                {opportunity.organization.status === "VERIFIED" && (
                  <span className="inline-flex items-center gap-1 rounded border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-300">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Tasdiqlangan korxona
                  </span>
                )}
              </div>
              <h1 className="mt-1 font-heading text-2xl font-bold text-white sm:text-3xl">
                {rev.title}
              </h1>
              <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-zinc-400">
                {rev.region && (
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin className="h-4 w-4 text-zinc-500" /> {rev.region}
                  </span>
                )}
                {rev.work_mode && (
                  <span className="inline-flex items-center gap-1.5">
                    <BriefcaseBusiness className="h-4 w-4 text-zinc-500" /> {rev.work_mode}
                  </span>
                )}
                {opportunity.published_at && (
                  <span className="inline-flex items-center gap-1.5">
                    <Clock3 className="h-4 w-4 text-zinc-500" />{" "}
                    {new Date(opportunity.published_at).toLocaleDateString("uz-UZ")}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex shrink-0 flex-col items-start gap-3 lg:items-end">
            <span className="rounded-lg border border-white/[0.1] bg-surface-lowest px-3 py-1.5 text-xs font-semibold text-zinc-300">
              {isPartTime ? "Yarim stavka bandlik" : "Talaba amaliyoti"}
            </span>
            <div className="text-left lg:text-right">
              <p className="text-xs text-zinc-500">To‘lov / Maosh</p>
              <p className="font-heading text-xl font-bold tabular-nums text-primary">
                {formattedSalary}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Grid Content */}
      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        {/* Left Column: Details */}
        <div className="space-y-8">
          {/* Key Facts Summary */}
          <section
            aria-labelledby="facts-heading"
            className="grid gap-4 sm:grid-cols-3"
          >
            <h2 id="facts-heading" className="sr-only">Asosiy ma’lumotlar</h2>
            <div className="rounded-xl border border-white/[0.08] bg-surface-card p-4">
              <span className="text-xs text-zinc-500">Bo‘sh o‘rinlar</span>
              <p className="mt-1 font-heading text-lg font-bold tabular-nums text-white">
                {opportunity.vacancies_available}{" "}
                <span className="text-xs font-normal text-zinc-400">/ {opportunity.capacity} jami</span>
              </p>
            </div>
            <div className="rounded-xl border border-white/[0.08] bg-surface-card p-4">
              <span className="text-xs text-zinc-500">Grafik tartibi</span>
              <p className="mt-1 font-heading text-lg font-bold text-white">
                {rev.schedule_policy === "STRICT" ? "Qat’iy jadval" : "Moslashuvchan"}
              </p>
            </div>
            <div className="rounded-xl border border-white/[0.08] bg-surface-card p-4">
              <span className="text-xs text-zinc-500">Shartnoma formati</span>
              <p className="mt-1 font-heading text-lg font-bold text-white">
                {rev.contract_type || "Rasmiy mehnat"}
              </p>
            </div>
          </section>

          {/* Description Section */}
          <section
            aria-labelledby="description-heading"
            className="rounded-2xl border border-white/[0.08] bg-surface-card p-6 lg:p-8"
          >
            <h2
              id="description-heading"
              className="flex items-center gap-2 font-heading text-lg font-bold text-white"
            >
              <FileText className="h-5 w-5 text-primary" /> Tavsif va talablar
            </h2>
            <div className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-zinc-300">
              {rev.description || "Ushbu vakansiya bo‘yicha batafsil tavsif kiritilmagan."}
            </div>
          </section>

          {/* Schedule / Shifts Section */}
          {opportunity.shifts && opportunity.shifts.length > 0 && (
            <section
              aria-labelledby="schedule-heading"
              className="rounded-2xl border border-white/[0.08] bg-surface-card p-6 lg:p-8"
            >
              <h2
                id="schedule-heading"
                className="flex items-center gap-2 font-heading text-lg font-bold text-white"
              >
                <CalendarDays className="h-5 w-5 text-primary" /> Ish / Amaliyot vaqtlari (Smenalar)
              </h2>
              <p className="mt-1 text-xs text-zinc-400">
                MK 118-modda: Dars vaqtlari bilan to‘qnashmaydigan rasmiy smena taqvimi.
              </p>

              <div className="mt-4 space-y-2.5">
                {opportunity.shifts.map((shift) => (
                  <div
                    key={shift.id}
                    className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-surface-lowest px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span className="h-2 w-2 rounded-full bg-primary" />
                      <span className="text-sm font-semibold text-white">
                        {weekdayNames[shift.weekday] || `Hafta kuni ${shift.weekday}`}
                      </span>
                    </div>
                    <span className="font-mono text-xs font-semibold tabular-nums text-zinc-300">
                      {formatMinutes(shift.start_minute)} — {formatMinutes(shift.end_minute)}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Required Skills Section */}
          {opportunity.skills && opportunity.skills.length > 0 && (
            <section
              aria-labelledby="skills-heading"
              className="rounded-2xl border border-white/[0.08] bg-surface-card p-6 lg:p-8"
            >
              <h2
                id="skills-heading"
                className="flex items-center gap-2 font-heading text-lg font-bold text-white"
              >
                <Sparkles className="h-5 w-5 text-primary" /> Talab etiladigan ko‘nikmalar
              </h2>
              <div className="mt-4 flex flex-wrap gap-2">
                {opportunity.skills.map((skill) => (
                  <span
                    key={skill.id}
                    className="rounded-lg border border-primary/20 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary"
                  >
                    {skill.name}
                  </span>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Right Column: Action Sidebar */}
        <aside aria-label="Ariza harakati" className="space-y-6">
          <div className="rounded-2xl border border-white/[0.08] bg-surface-card p-6">
            <h2 className="font-heading text-base font-bold text-white">
              Nomzod arizasi
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-zinc-400">
              Ushbu vakansiyaga bevosita platforma orqali ariza topshiring. Arizangiz to‘g‘ridan-to‘g‘ri ish beruvchi HR kabinetiga tushadi.
            </p>

            <div className="mt-6">
              <button
                type="button"
                onClick={handleApplyClick}
                disabled={opportunity.vacancies_available <= 0}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3 text-sm font-semibold text-white shadow-lg shadow-primary/20 transition-all hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
                {opportunity.vacancies_available > 0
                  ? "Ariza topshirish"
                  : "Bo‘sh o‘rinlar qolmagan"}
              </button>
            </div>

            {user && (
              <div className="mt-4 flex items-center gap-2 border-t border-white/[0.06] pt-3 text-xs text-zinc-400">
                <UserCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span>
                  Kirilgan hisob: <strong className="text-zinc-200">{user.user_id.slice(0, 8)}...</strong>
                </span>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-white/[0.08] bg-surface-card p-6">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Ish beruvchi kafolatlari
            </h3>
            <ul className="mt-4 space-y-3 text-xs text-zinc-300">
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                <span>O‘zbekiston Respublikasi Mehnat Kodeksi (118-modda) muvofiqligi</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                <span>Oylik yoki soatbay rasmiy to‘lov kafolati</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                <span>Universitet amaliyoti sifatida to‘liq tan olinishi</span>
              </li>
            </ul>
          </div>
        </aside>
      </div>

      {/* Auth Modal for Unauthenticated Users */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onSuccess={handleAuthSuccess}
      />

      {/* Application Submission Drawer/Modal */}
      {applicationModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="application-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-lg rounded-2xl border border-white/[0.1] bg-[#121214] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <h2
                id="application-modal-title"
                className="font-heading text-lg font-bold text-white"
              >
                Vakansiyaga ariza topshirish
              </h2>
              <button
                type="button"
                onClick={() => {
                  setApplicationModalOpen(false);
                  setSubmitSuccess(null);
                  setSubmitError(null);
                }}
                className="rounded-lg p-1 text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {submitSuccess ? (
              <div className="py-6 text-center">
                <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-400" />
                <h3 className="mt-4 text-base font-bold text-white">
                  Arizangiz muvaffaqiyatli topshirildi!
                </h3>
                <p className="mt-2 text-xs text-zinc-400">
                  Ariza raqami: <span className="font-mono text-zinc-200">{submitSuccess.id}</span>
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  Ish beruvchi arizangizni ko‘rib chiqqach, siz bilan platforma xabarlari orqali bog‘lanadi.
                </p>
                <div className="mt-6">
                  <button
                    type="button"
                    onClick={() => {
                      setApplicationModalOpen(false);
                      setSubmitSuccess(null);
                    }}
                    className="rounded-lg bg-primary px-5 py-2.5 text-xs font-semibold text-white hover:bg-primary-hover"
                  >
                    Tushunarli
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleApplicationSubmit} className="mt-4 space-y-4">
                <div>
                  <p className="text-xs font-semibold text-zinc-200">
                    Lavozim: <span className="text-primary">{rev.title}</span>
                  </p>
                  <p className="mt-1 text-xs text-zinc-400">
                    Tashkilot: {opportunity.organization.name}
                  </p>
                </div>

                <div>
                  <label htmlFor="cover-note" className="block text-xs font-semibold text-zinc-300">
                    Qo‘shimcha izoh yoki motivatsiya xati (ixtiyoriy)
                  </label>
                  <textarea
                    id="cover-note"
                    rows={4}
                    value={applicationNote}
                    onChange={(e) => setApplicationNote(e.target.value)}
                    placeholder="Nima uchun ushbu vakansiyada ishlashni xohlaysiz va ko‘nikmalaringiz qanday mos keladi..."
                    className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-surface-lowest p-3 text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none"
                  />
                </div>

                <div className="flex items-start gap-2.5 rounded-xl border border-white/[0.06] bg-surface-lowest p-3">
                  <input
                    id="schedule-confirm"
                    type="checkbox"
                    checked={scheduleConfirmed}
                    onChange={(e) => setScheduleConfirmed(e.target.checked)}
                    className="mt-0.5 rounded border-white/[0.2] bg-surface-card text-primary focus:ring-primary"
                  />
                  <label htmlFor="schedule-confirm" className="text-xs text-zinc-300">
                    Ko‘rsatilgan ish vaqtlari dars jadvalimga xalaqit bermasligini tasdiqlayman (MK 118-modda).
                  </label>
                </div>

                {submitError && (
                  <div
                    role="alert"
                    className="rounded-xl border border-rose-500/20 bg-rose-500/[0.05] p-3 text-xs text-rose-300"
                  >
                    {submitError}
                  </div>
                )}

                <div className="flex items-center justify-end gap-3 pt-3">
                  <button
                    type="button"
                    onClick={() => setApplicationModalOpen(false)}
                    className="rounded-lg border border-white/[0.1] px-4 py-2 text-xs font-semibold text-zinc-300 hover:border-zinc-500"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="submit"
                    disabled={submitting || !scheduleConfirmed}
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-xs font-semibold text-white hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Yuborilmoqda...
                      </>
                    ) : (
                      <>
                        <Send className="h-3.5 w-3.5" /> Arizani jo‘natish
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
