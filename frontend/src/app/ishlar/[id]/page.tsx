"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
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
  Bookmark,
  Flag,
} from "lucide-react";
import {
  fetchOpportunityDetail,
  submitOpportunityApplication,
  fetchAuthMe,
  saveOpportunity,
  OpportunityDetail,
  AuthUser,
} from "@/lib/api";
import { enumLabel } from "@/lib/labels";
import AuthModal from "@/components/AuthModal";
import ModerationReportModal from "@/components/public/ModerationReportModal";

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

  // Auth, Application & Reporting State
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [pendingAuthIntent, setPendingAuthIntent] = useState<"apply" | "report">("apply");
  const [applicationModalOpen, setApplicationModalOpen] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [applicationNote, setApplicationNote] = useState("");
  const [scheduleConfirmed, setScheduleConfirmed] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<{ id: string } | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSaved, setIsSaved] = useState(false);
  const [saving, setSaving] = useState(false);

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
      setPendingAuthIntent("apply");
      setAuthModalOpen(true);
    } else {
      setApplicationModalOpen(true);
    }
  };

  const handleReportClick = () => {
    if (!user) {
      setPendingAuthIntent("report");
      setAuthModalOpen(true);
    } else {
      setReportModalOpen(true);
    }
  };

  const handleToggleSave = async () => {
    if (!user) {
      setPendingAuthIntent("apply");
      setAuthModalOpen(true);
      return;
    }
    if (!opportunity) return;
    try {
      setSaving(true);
      const res = await saveOpportunity(opportunity.id, true);
      setIsSaved(res.saved);
    } catch (err: unknown) {
      console.error("Save error:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleAuthSuccess = async () => {
    const freshUser = await fetchAuthMe();
    setUser(freshUser);
    setAuthModalOpen(false);
    if (pendingAuthIntent === "report") {
      setReportModalOpen(true);
    } else {
      setApplicationModalOpen(true);
    }
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
        <div className="flex flex-col items-center justify-center rounded-[28px] skeuo-card p-16 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-[#c94f1d]" />
          <p className="mt-4 text-sm font-medium text-[var(--fb-ink-secondary)]">
            Vakansiya tafsilotlari yuklanmoqda...
          </p>
        </div>
      </main>
    );
  }

  if (error || !opportunity) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12">
        <div className="rounded-[28px] skeuo-card p-12 text-center">
          <AlertCircle className="mx-auto h-10 w-10 text-amber-500" />
          <h1 className="mt-4 font-heading text-lg font-bold text-[var(--fb-ink)]">
            E’lon topilmadi yoki yopilgan
          </h1>
          <p className="mt-2 text-sm text-[var(--fb-ink-muted)]">
            {error || "Ushbu identifikator bo‘yicha e’lon mavjud emas."}
          </p>
          <div className="mt-6">
            <Link
              href="/elonlar"
              prefetch={false}
              className="skeuo-btn-obsidian inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold"
            >
              <ArrowLeft className="h-4 w-4" /> E’lonlar katalogiga qaytish
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const rev = opportunity.revision;
  const orgId = opportunity.organization.id || opportunity.organization_id;
  const isPartTime = opportunity.kind === "PART_TIME";
  const formattedSalary =
    rev.salary_min !== null
      ? `${rev.salary_min.toLocaleString("uz-UZ")} ${rev.currency}`
      : "Kelishuv asosida";

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      {/* Breadcrumb Navigation */}
      <nav aria-label="Breadcrumb" className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Link
          href="/elonlar"
          prefetch={false}
          className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--fb-ink-muted)] transition-colors hover:text-[var(--fb-accent)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Barcha e’lonlarga qaytish
        </Link>
        {orgId && (
          <Link
            href={`/tashkilot/${orgId}`}
            prefetch={false}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--fb-ink-secondary)] transition-colors hover:text-[var(--fb-accent)]"
          >
            <Building2 className="h-3.5 w-3.5" />
            <span>Tashkilotning barcha e’lonlari</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        )}
      </nav>

      {/* Main Header Card */}
      <section className="rounded-[28px] skeuo-card p-6 lg:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl skeuo-well text-[#c94f1d] dark:text-[#f47a3d]">
              <Building2 className="h-7 w-7" aria-hidden="true" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                {orgId ? (
                  <Link
                    href={`/tashkilot/${orgId}`}
                    prefetch={false}
                    className="text-sm font-semibold text-[var(--fb-ink)] underline-offset-4 hover:text-[#c94f1d] hover:underline dark:hover:text-[#f47a3d]"
                  >
                    {opportunity.organization.name}
                  </Link>
                ) : (
                  <span className="text-sm font-semibold text-[var(--fb-ink)]">
                    {opportunity.organization.name}
                  </span>
                )}
                {opportunity.organization.status === "VERIFIED" && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-600/25 bg-emerald-600/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:text-emerald-300">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Tasdiqlangan korxona
                  </span>
                )}
              </div>
              <h1 className="mt-1.5 font-heading text-2xl font-bold text-[var(--fb-ink)] sm:text-3xl">
                {rev.title}
              </h1>
              <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-[var(--fb-ink-muted)]">
                {rev.region && (
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin className="h-4 w-4 opacity-75" /> {rev.region}
                  </span>
                )}
                {rev.work_mode && (
                  <span className="inline-flex items-center gap-1.5">
                    <BriefcaseBusiness className="h-4 w-4 opacity-75" /> {enumLabel(rev.work_mode)}
                  </span>
                )}
                {opportunity.published_at && (
                  <span className="inline-flex items-center gap-1.5">
                    <Clock3 className="h-4 w-4 opacity-75" />{" "}
                    {new Date(opportunity.published_at).toLocaleDateString("uz-UZ")}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex shrink-0 flex-col items-start gap-3 lg:items-end">
            <span className="rounded-full skeuo-badge-recessed px-3 py-1 text-xs font-semibold text-[var(--fb-ink)]">
              {isPartTime ? "Yarim stavka bandlik" : "Talaba amaliyoti"}
            </span>
            <div className="text-left lg:text-right">
              <p className="text-xs text-[var(--fb-ink-muted)]">To‘lov / Maosh</p>
              <p className="font-heading text-xl font-bold tabular-nums text-[#c94f1d] dark:text-[#f47a3d]">
                {formattedSalary}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Grid Content */}
      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        {/* Left Column: Details */}
        <div className="space-y-6">
          {/* Key Facts Summary */}
          <section
            aria-labelledby="facts-heading"
            className="grid gap-4 sm:grid-cols-3"
          >
            <h2 id="facts-heading" className="sr-only">Asosiy ma’lumotlar</h2>
            <div className="rounded-2xl skeuo-card p-4">
              <span className="text-xs text-[var(--fb-ink-muted)]">Bo‘sh o‘rinlar</span>
              <p className="mt-1 font-heading text-lg font-bold tabular-nums text-[var(--fb-ink)]">
                {opportunity.vacancies_available}{" "}
                <span className="text-xs font-normal text-[var(--fb-ink-muted)]">
                  / {opportunity.capacity} jami
                </span>
              </p>
            </div>
            <div className="rounded-2xl skeuo-card p-4">
              <span className="text-xs text-[var(--fb-ink-muted)]">Grafik tartibi</span>
              <p className="mt-1 font-heading text-lg font-bold text-[var(--fb-ink)]">
                {rev.schedule_policy === "STRICT" ? "Qat’iy jadval" : "Moslashuvchan"}
              </p>
            </div>
            <div className="rounded-2xl skeuo-card p-4">
              <span className="text-xs text-[var(--fb-ink-muted)]">Shartnoma formati</span>
              <p className="mt-1 font-heading text-lg font-bold text-[var(--fb-ink)] break-words">
                {rev.contract_type ? enumLabel(rev.contract_type) : "Rasmiy mehnat"}
              </p>
            </div>
          </section>

          {/* Description Section */}
          <section
            aria-labelledby="description-heading"
            className="rounded-[26px] skeuo-card p-6 lg:p-8"
          >
            <h2
              id="description-heading"
              className="flex items-center gap-2 font-heading text-lg font-bold text-[var(--fb-ink)]"
            >
              <FileText className="h-5 w-5 text-[#c94f1d] dark:text-[#f47a3d]" /> Tavsif va talablar
            </h2>
            <div className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fb-ink-secondary)]">
              {rev.description || "Ushbu vakansiya bo‘yicha batafsil tavsif kiritilmagan."}
            </div>
          </section>

          {/* Schedule / Shifts Section */}
          {opportunity.shifts && opportunity.shifts.length > 0 && (
            <section
              aria-labelledby="schedule-heading"
              className="rounded-[26px] skeuo-card p-6 lg:p-8"
            >
              <h2
                id="schedule-heading"
                className="flex items-center gap-2 font-heading text-lg font-bold text-[var(--fb-ink)]"
              >
                <CalendarDays className="h-5 w-5 text-[#c94f1d] dark:text-[#f47a3d]" /> Ish / Amaliyot vaqtlari (Smenalar)
              </h2>
              <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">
                MK 118-modda: Dars vaqtlari bilan to‘qnashmaydigan rasmiy smena taqvimi.
              </p>

              <div className="mt-4 space-y-2.5">
                {opportunity.shifts.map((shift) => (
                  <div
                    key={shift.id}
                    className="flex items-center justify-between rounded-xl skeuo-well px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span className="h-2 w-2 rounded-full bg-[#c94f1d]" />
                      <span className="text-sm font-semibold text-[var(--fb-ink)]">
                        {weekdayNames[shift.weekday] || `Hafta kuni ${shift.weekday}`}
                      </span>
                    </div>
                    <span className="font-mono text-xs font-semibold tabular-nums text-[var(--fb-ink-secondary)]">
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
              className="rounded-[26px] skeuo-card p-6 lg:p-8"
            >
              <h2
                id="skills-heading"
                className="flex items-center gap-2 font-heading text-lg font-bold text-[var(--fb-ink)]"
              >
                <Sparkles className="h-5 w-5 text-[#c94f1d] dark:text-[#f47a3d]" /> Talab etiladigan ko‘nikmalar
              </h2>
              <div className="mt-4 flex flex-wrap gap-2">
                {opportunity.skills.map((skill) => (
                  <span
                    key={skill.id}
                    className="rounded-xl border border-[#c94f1d]/25 bg-[#c94f1d]/10 px-3 py-1.5 text-xs font-semibold text-[#c94f1d] dark:text-[#f47a3d]"
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
          <div className="rounded-[26px] skeuo-card p-6">
            <h2 className="font-heading text-base font-bold text-[var(--fb-ink)]">
              Nomzod arizasi
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
              Ushbu vakansiyaga bevosita platforma orqali ariza topshiring. Arizangiz to‘g‘ridan-to‘g‘ri ish beruvchi HR kabinetiga tushadi.
            </p>

            <div className="mt-6 space-y-2.5">
              <button
                type="button"
                onClick={handleApplyClick}
                disabled={opportunity.vacancies_available <= 0}
                className="flex w-full items-center justify-center gap-2 rounded-2xl skeuo-btn-obsidian py-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
                {opportunity.vacancies_available > 0
                  ? "Ariza topshirish"
                  : "Bo‘sh o‘rinlar qolmagan"}
              </button>

              <button
                type="button"
                onClick={handleToggleSave}
                disabled={saving}
                className="flex w-full items-center justify-center gap-2 rounded-2xl skeuo-btn-secondary py-2.5 text-xs font-semibold disabled:opacity-50"
              >
                {saving ? (
                  <Loader2 className="h-4 w-4 animate-spin text-[#c94f1d]" />
                ) : (
                  <Bookmark
                    className={`h-4 w-4 ${
                      isSaved ? "fill-[#c94f1d] text-[#c94f1d]" : "text-[var(--fb-ink-muted)]"
                    }`}
                  />
                )}
                {isSaved ? "Saqlangan" : "Saqlab qo‘yish"}
              </button>

              <button
                type="button"
                onClick={handleReportClick}
                className="flex w-full items-center justify-center gap-2 rounded-2xl skeuo-well py-2 text-xs font-medium text-[var(--fb-ink-muted)] transition-colors hover:text-amber-600 dark:hover:text-amber-400"
              >
                <Flag className="h-3.5 w-3.5" aria-hidden="true" />
                E’lon ustidan shikoyat qilish
              </button>
            </div>

            {user && (
              <div className="mt-4 flex items-center gap-2 border-t border-[var(--fb-border)] pt-3 text-xs text-[var(--fb-ink-muted)]">
                <UserCheck className="h-3.5 w-3.5 text-emerald-500" />
                <span>
                  Kirilgan hisob:{" "}
                  <strong className="text-[var(--fb-ink)]">{user.display_name || "talaba"}</strong>
                </span>
              </div>
            )}
          </div>

          <div className="rounded-[26px] skeuo-card p-6">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--fb-ink-muted)]">
              Ish beruvchi kafolatlari
            </h3>
            <ul className="mt-4 space-y-3 text-xs text-[var(--fb-ink-secondary)]">
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                <span>O‘zbekiston Respublikasi Mehnat Kodeksi (118-modda) muvofiqligi</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                <span>Oylik yoki soatbay rasmiy to‘lov kafolati</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
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

      {/* Moderation Abuse Report Modal (API-007) */}
      <ModerationReportModal
        isOpen={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
        targetLabel={rev.title}
        opportunityId={opportunity.id}
      />

      {/* Application Submission Drawer/Modal */}
      {applicationModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="application-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
        >
          <div className="w-full max-w-lg rounded-[28px] skeuo-card p-6 sm:p-7">
            <div className="flex items-center justify-between border-b border-[var(--fb-border)] pb-4">
              <h2
                id="application-modal-title"
                className="font-heading text-lg font-bold text-[var(--fb-ink)]"
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
                className="flex h-8 w-8 items-center justify-center rounded-xl skeuo-btn-secondary p-0 text-xs"
              >
                ✕
              </button>
            </div>

            {submitSuccess ? (
              <div className="py-6 text-center">
                <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-500" />
                <h3 className="mt-4 font-heading text-base font-bold text-[var(--fb-ink)]">
                  Arizangiz muvaffaqiyatli topshirildi!
                </h3>
                <p className="mt-2 text-xs text-[var(--fb-ink-secondary)]">
                  Ariza raqami:{" "}
                  <span className="font-mono font-semibold text-[var(--fb-ink)]">
                    {submitSuccess.id}
                  </span>
                </p>
                <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">
                  Ish beruvchi arizangizni ko‘rib chiqqach, siz bilan platforma xabarlari orqali bog‘lanadi.
                </p>
                <div className="mt-6">
                  <button
                    type="button"
                    onClick={() => {
                      setApplicationModalOpen(false);
                      setSubmitSuccess(null);
                    }}
                    className="skeuo-btn-obsidian rounded-full px-6 py-2.5 text-xs font-semibold"
                  >
                    Tushunarli
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleApplicationSubmit} className="mt-4 space-y-4">
                <div>
                  <p className="text-xs font-semibold text-[var(--fb-ink)]">
                    Lavozim: <span className="text-[#c94f1d] dark:text-[#f47a3d]">{rev.title}</span>
                  </p>
                  <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">
                    Tashkilot: {opportunity.organization.name}
                  </p>
                </div>

                <div>
                  <label htmlFor="cover-note" className="block text-xs font-semibold text-[var(--fb-ink)]">
                    Qo‘shimcha izoh yoki motivatsiya xati (ixtiyoriy)
                  </label>
                  <textarea
                    id="cover-note"
                    rows={4}
                    value={applicationNote}
                    onChange={(e) => setApplicationNote(e.target.value)}
                    placeholder="Nima uchun ushbu vakansiyada ishlashni xohlaysiz va ko‘nikmalaringiz qanday mos keladi..."
                    className="skeuo-input mt-1.5 w-full rounded-xl p-3 text-xs"
                  />
                </div>

                <div className="flex items-start gap-2.5 rounded-xl skeuo-well p-3">
                  <input
                    id="schedule-confirm"
                    type="checkbox"
                    checked={scheduleConfirmed}
                    onChange={(e) => setScheduleConfirmed(e.target.checked)}
                    className="mt-0.5 rounded accent-[#c94f1d]"
                  />
                  <label htmlFor="schedule-confirm" className="text-xs text-[var(--fb-ink-secondary)]">
                    Ko‘rsatilgan ish vaqtlari dars jadvalimga xalaqit bermasligini tasdiqlayman (MK 118-modda).
                  </label>
                </div>

                {submitError && (
                  <div
                    role="alert"
                    className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300"
                  >
                    {submitError}
                  </div>
                )}

                <div className="flex items-center justify-end gap-3 pt-3">
                  <button
                    type="button"
                    onClick={() => setApplicationModalOpen(false)}
                    className="skeuo-btn-secondary rounded-full px-4 py-2 text-xs font-semibold"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="submit"
                    disabled={submitting || !scheduleConfirmed}
                    className="skeuo-btn-obsidian inline-flex items-center gap-2 rounded-full px-5 py-2 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-50"
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
