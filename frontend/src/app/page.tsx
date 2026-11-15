"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Clock3,
  MapPin,
  RotateCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import { fetchOpportunities, Opportunity, OpportunityPage } from "@/lib/api";

type Filters = { query: string; region: string; paid: "" | "true" | "false" };
type FeedStatus = "loading" | "ready" | "error";
type FeedSnapshot =
  | { key: string; status: "ready"; page: OpportunityPage }
  | { key: string; status: "error"; page: null };
const emptyFilters: Filters = { query: "", region: "", paid: "" };

const modeLabels: Record<string, string> = {
  ONSITE: "Ish joyida",
  HYBRID: "Gibrid",
  REMOTE: "Masofadan",
};

function paymentLabel(job: Opportunity): string {
  if (!job.is_paid) return "To‘lovsiz";
  const format = (value: number) => value.toLocaleString("uz-UZ");
  if (job.salary_min !== null && job.salary_max !== null) {
    return `${format(job.salary_min)}–${format(job.salary_max)} ${job.currency}`;
  }
  if (job.salary_min !== null) return `${format(job.salary_min)} ${job.currency} dan`;
  if (job.salary_max !== null) return `${format(job.salary_max)} ${job.currency} gacha`;
  return "To‘lov miqdori ko‘rsatilmagan";
}

function VacancyCard({ job }: { job: Opportunity }) {
  const place = job.region || job.organization_region;
  const mode = job.work_mode ? modeLabels[job.work_mode] || job.work_mode : null;
  const posted = job.published_at ? new Date(job.published_at) : null;
  const postedLabel = posted && !Number.isNaN(posted.getTime())
    ? posted.toLocaleDateString("uz-UZ")
    : null;

  return (
    <article className="rounded-xl border border-white/[0.08] bg-surface-card p-5 transition-colors hover:border-primary/35">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
            <Building2 className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-zinc-200">{job.organization_name}</span>
              <span className="inline-flex items-center gap-1 rounded border border-emerald-500/20 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-300">
                <ShieldCheck className="h-3 w-3" aria-hidden="true" />
                Tasdiqlangan tashkilot
              </span>
            </div>
            <h2 className="font-heading text-base font-bold text-white transition-colors hover:text-primary">
              <Link href={`/ishlar/${job.id}`}>{job.title}</Link>
            </h2>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-400">
              {place && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5" aria-hidden="true" />{place}
                </span>
              )}
              {mode && (
                <span className="inline-flex items-center gap-1">
                  <BriefcaseBusiness className="h-3.5 w-3.5" aria-hidden="true" />{mode}
                </span>
              )}
              {postedLabel && (
                <span className="inline-flex items-center gap-1">
                  <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />{postedLabel}
                </span>
              )}
            </div>
          </div>
        </div>
        <span className="shrink-0 self-start rounded border border-white/[0.08] bg-surface-lowest px-2.5 py-1 text-xs text-zinc-300">
          {job.kind === "PART_TIME" ? "Yarim stavka" : job.kind === "INTERNSHIP" ? "Amaliyot" : job.kind}
        </span>
      </div>

      <div className="mt-4 grid gap-3 border-t border-white/[0.06] pt-4 sm:grid-cols-2">
        <div>
          <p className="text-[11px] text-zinc-500">To‘lov</p>
          <p className="mt-0.5 text-sm font-semibold text-primary">{paymentLabel(job)}</p>
        </div>
        <div>
          <p className="text-[11px] text-zinc-500">Bo‘sh o‘rin</p>
          <p className="mt-0.5 text-sm font-semibold text-zinc-200">
            {job.vacancies_available} ta
          </p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.06] pt-3">
        {job.description ? (
          <details className="group text-xs text-zinc-400">
            <summary className="flex cursor-pointer list-none items-center gap-1 font-semibold text-zinc-300 hover:text-primary">
              Tavsifni ko‘rish <ArrowRight className="h-3.5 w-3.5 transition-transform group-open:rotate-90" aria-hidden="true" />
            </summary>
            <p className="mt-2 whitespace-pre-wrap leading-relaxed">{job.description}</p>
          </details>
        ) : <div />}
        <Link
          href={`/ishlar/${job.id}`}
          className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary transition-colors hover:bg-primary hover:text-white"
        >
          Batafsil / Ariza <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </div>
    </article>
  );
}

export default function StudentPortal() {
  const [draftQuery, setDraftQuery] = useState("");
  const [draftRegion, setDraftRegion] = useState("");
  const [draftPaid, setDraftPaid] = useState<Filters["paid"]>("");
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [cursor, setCursor] = useState<string | null>(null);
  const [history, setHistory] = useState<(string | null)[]>([]);
  const [snapshot, setSnapshot] = useState<FeedSnapshot | null>(null);
  const [reload, setReload] = useState(0);
  const requestKey = JSON.stringify([filters.query, filters.region, filters.paid, cursor, reload]);
  const current = snapshot?.key === requestKey ? snapshot : null;
  const status: FeedStatus = current?.status || "loading";
  const page = current?.page || null;

  useEffect(() => {
    const controller = new AbortController();
    fetchOpportunities({
      query: filters.query || undefined,
      region: filters.region || undefined,
      is_paid: filters.paid === "" ? undefined : filters.paid === "true",
      after: cursor || undefined,
      signal: controller.signal,
    })
      .then((result) => {
        if (!controller.signal.aborted) {
          setSnapshot({ key: requestKey, status: "ready", page: result });
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setSnapshot({ key: requestKey, status: "error", page: null });
        }
      });
    return () => controller.abort();
  }, [filters, cursor, requestKey]);

  function submitFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setHistory([]);
    setCursor(null);
    setFilters({ query: draftQuery.trim(), region: draftRegion, paid: draftPaid });
    setReload((value) => value + 1);
  }

  function clearFilters() {
    setDraftQuery("");
    setDraftRegion("");
    setDraftPaid("");
    setHistory([]);
    setCursor(null);
    setFilters(emptyFilters);
    setReload((value) => value + 1);
  }

  function nextPage() {
    if (!page?.has_more || !page.next_after) return;
    setHistory((current) => [...current, cursor]);
    setCursor(page.next_after);
  }

  function previousPage() {
    if (history.length === 0) return;
    setCursor(history[history.length - 1]);
    setHistory((current) => current.slice(0, -1));
  }

  return (
    <main className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-4 py-8 md:px-8">
      <section className="rounded-2xl border border-white/[0.08] bg-surface-card p-5 md:p-7">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,0.75fr)] lg:items-center">
          {/* Left: Discovery Search Column */}
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
              <BriefcaseBusiness className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Ommaviy katalog</span>
            </div>
            <h1 className="mt-3 font-heading text-2xl font-bold tracking-tight text-white md:text-4xl">
              Ish va amaliyot imkoniyatlari
            </h1>
            <p className="mt-2.5 max-w-2xl text-sm leading-relaxed text-zinc-400">
              Dars jadvalingizga mos smenali ishlar va rasmiy dual ta’lim amaliyotlarini toping. Faqat tasdiqlangan tashkilotlar e’lonlari ko‘rsatiladi.
            </p>

            <form onSubmit={submitFilters} className="mt-6 grid gap-3 sm:grid-cols-[minmax(0,1fr)_150px_150px_auto]">
              <label className="relative block">
                <span className="sr-only">Lavozim yoki ko‘nikma</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" aria-hidden="true" />
                <input
                  id="opportunity-query"
                  type="search"
                  value={draftQuery}
                  onChange={(event) => setDraftQuery(event.target.value)}
                  placeholder="Lavozim yoki ko‘nikma"
                  className="w-full rounded-lg border border-white/[0.1] bg-surface-lowest py-2.5 pl-10 pr-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-primary focus:outline-none"
                />
              </label>
              <label>
                <span className="sr-only">Hudud</span>
                <select id="opportunity-region" value={draftRegion} onChange={(event) => setDraftRegion(event.target.value)} className="w-full rounded-lg border border-white/[0.1] bg-surface-lowest px-3 py-2.5 text-sm text-zinc-200 focus:border-primary focus:outline-none">
                  <option value="">Barcha hududlar</option>
                  <option value="Toshkent">Toshkent</option>
                  <option value="Samarqand">Samarqand</option>
                  <option value="Farg">Farg‘ona</option>
                  <option value="Buxoro">Buxoro</option>
                </select>
              </label>
              <label>
                <span className="sr-only">To‘lov turi</span>
                <select id="opportunity-payment" value={draftPaid} onChange={(event) => setDraftPaid(event.target.value as Filters["paid"])} className="w-full rounded-lg border border-white/[0.1] bg-surface-lowest px-3 py-2.5 text-sm text-zinc-200 focus:border-primary focus:outline-none">
                  <option value="">Barcha to‘lovlar</option>
                  <option value="true">To‘lovli</option>
                  <option value="false">To‘lovsiz</option>
                </select>
              </label>
              <button type="submit" className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary">
                <SlidersHorizontal className="h-4 w-4" aria-hidden="true" /> Qidirish
              </button>
            </form>

            {/* Quick Preset Chips */}
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
              <span className="text-zinc-500">Tezkor tanlov:</span>
              <button
                type="button"
                onClick={() => {
                  setDraftRegion("Toshkent");
                  setHistory([]);
                  setCursor(null);
                  setFilters((f) => ({ ...f, region: "Toshkent" }));
                  setReload((v) => v + 1);
                }}
                className="rounded-lg border border-white/[0.08] bg-surface-lowest px-2.5 py-1 text-zinc-300 hover:border-primary/40 hover:text-white transition-colors"
              >
                Toshkent sh.
              </button>
              <button
                type="button"
                onClick={() => {
                  setDraftPaid("true");
                  setHistory([]);
                  setCursor(null);
                  setFilters((f) => ({ ...f, paid: "true" }));
                  setReload((v) => v + 1);
                }}
                className="rounded-lg border border-white/[0.08] bg-surface-lowest px-2.5 py-1 text-zinc-300 hover:border-emerald-500/40 hover:text-emerald-300 transition-colors"
              >
                Faqat to‘lovli
              </button>
              <button
                type="button"
                onClick={clearFilters}
                className="rounded-lg border border-white/[0.08] bg-surface-lowest px-2.5 py-1 text-zinc-400 hover:text-white transition-colors"
              >
                Barcha e’lonlar
              </button>
            </div>
          </div>

          {/* Right: 3-Portal Role Entry Matrix */}
          <div className="grid gap-2.5 rounded-xl border border-white/[0.08] bg-surface-lowest/70 p-3.5">
            <div className="px-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
              Rolingiz bo‘yicha kabinetni tanlang
            </div>
            <div className="rounded-xl border border-sky-500/20 bg-surface-card p-4 space-y-2.5">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-xs font-bold text-white">
                    Talaba / Nomzod Kabineti
                  </p>
                  <p className="text-[11px] text-zinc-400 mt-0.5">
                    Rezyume, HEMIS jadvali, arizalar va kundalik e-imzo
                  </p>
                </div>
                <span className="shrink-0 rounded-md border border-sky-500/25 bg-sky-500/10 px-2 py-1 text-[10px] font-semibold text-sky-400">
                  Talaba
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <Link
                  href="/talaba/kirish"
                  className="inline-flex items-center rounded-lg bg-sky-500 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-sky-400 transition-colors"
                >
                  Talaba kirishi
                </Link>
                <Link
                  href="/nomzod"
                  className="inline-flex items-center rounded-lg border border-sky-500/25 bg-sky-500/10 px-2.5 py-1 text-[11px] font-medium text-sky-300 hover:bg-sky-500/20 transition-colors"
                >
                  Kabinet
                </Link>
              </div>
            </div>
            <div className="flex items-center justify-between gap-3 rounded-xl border border-emerald-500/20 bg-surface-card px-4 py-3 hover:border-emerald-400/50 hover:bg-emerald-500/[0.06] transition-colors">
              <div>
                <Link
                  href="/employer"
                  className="text-xs font-bold text-white hover:text-emerald-300 transition-colors"
                >
                  Korxona & HR Markazi
                </Link>
                <p className="text-[11px] text-zinc-400 mt-0.5">
                  Vakansiya joylash, Kanban saralash va mentor tasdig‘i
                </p>
              </div>
              <div className="shrink-0 flex items-center gap-1.5">
                <Link
                  href="/korxona/kirish"
                  className="rounded-md border border-emerald-500/35 bg-emerald-500/15 px-2.5 py-1 text-[10px] font-semibold text-emerald-300 hover:bg-emerald-500/25 transition-colors"
                >
                  Korxona kirishi
                </Link>
                <Link
                  href="/employer"
                  className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 text-[10px] font-semibold text-zinc-300 hover:text-white transition-colors"
                >
                  Kabinet
                </Link>
              </div>
            </div>
            <div className="rounded-xl border border-indigo-500/20 bg-surface-card px-4 py-3 hover:border-indigo-400/40 transition-colors">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-bold text-white">
                    Universitet / OTM Portali
                  </p>
                  <p className="text-[11px] text-zinc-400 mt-0.5">
                    Dekanat nazorati, dars jadvali va yig‘ma hisobotlar
                  </p>
                </div>
                <span className="shrink-0 rounded-md border border-indigo-500/25 bg-indigo-500/10 px-2 py-1 text-[10px] font-semibold text-indigo-400">
                  OTM
                </span>
              </div>
              <div className="mt-2.5 flex flex-wrap items-center gap-2">
                <Link
                  href="/universitet/kirish"
                  className="rounded-md bg-indigo-500/15 border border-indigo-500/30 px-2.5 py-1 text-[11px] font-semibold text-indigo-300 hover:bg-indigo-500/25 transition-colors"
                >
                  OTM kirishi →
                </Link>
                <Link
                  href="/university"
                  className="rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[11px] font-medium text-zinc-300 hover:bg-white/[0.06] transition-colors"
                >
                  Kabinet
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <section aria-labelledby="feed-heading" className="min-w-0">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b border-white/[0.08] pb-3">
            <div>
              <h2 id="feed-heading" className="font-heading text-lg font-bold text-zinc-100">E’lonlar</h2>
              <p className="mt-1 text-xs text-zinc-400">
                {status === "ready" && page
                  ? `Joriy sahifada ${page.items.length} ta e’lon`
                  : "Yangi e’lonlar birinchi ko‘rsatiladi"}
              </p>
            </div>
            {(filters.query || filters.region || filters.paid) && (
              <button type="button" onClick={clearFilters} className="text-xs font-semibold text-primary hover:underline">
                Filtrlarni tozalash
              </button>
            )}
          </div>

          <div aria-live="polite" aria-busy={status === "loading"}>
            {status === "loading" && (
              <div role="status" className="rounded-xl border border-white/[0.08] bg-surface-card p-8 text-center text-sm text-zinc-400">
                E’lonlar yuklanmoqda…
              </div>
            )}
            {status === "error" && (
              <div role="alert" className="rounded-xl border border-amber-500/20 bg-amber-500/[0.06] p-8 text-center">
                <CircleAlert className="mx-auto h-6 w-6 text-amber-400" aria-hidden="true" />
                <p className="mt-3 text-sm font-semibold text-zinc-100">E’lonlarni yuklab bo‘lmadi</p>
                <p className="mt-1 text-xs text-zinc-400">Ulanishni tekshirib, qayta urinib ko‘ring.</p>
                <button type="button" onClick={() => setReload((value) => value + 1)} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-white/[0.1] px-3 py-2 text-xs font-semibold text-zinc-200 hover:border-primary/50">
                  <RotateCw className="h-3.5 w-3.5" aria-hidden="true" /> Qayta urinish
                </button>
              </div>
            )}
            {status === "ready" && page?.items.length === 0 && (
              <div className="rounded-xl border border-white/[0.08] bg-surface-card p-8 text-center">
                <Search className="mx-auto h-6 w-6 text-zinc-500" aria-hidden="true" />
                <p className="mt-3 text-sm font-semibold text-zinc-100">Hozircha e’lon topilmadi</p>
                <p className="mt-1 text-xs text-zinc-400">Boshqa so‘z yoki hudud bilan qidirib ko‘ring.</p>
              </div>
            )}
            {status === "ready" && page && page.items.length > 0 && (
              <div className="space-y-3.5">{page.items.map((job) => <VacancyCard key={job.id} job={job} />)}</div>
            )}
          </div>

          {status === "ready" && page && (history.length > 0 || page.has_more) && (
            <nav aria-label="E’lonlar sahifalari" className="mt-5 flex items-center justify-between border-t border-white/[0.08] pt-4 text-xs">
              <button type="button" onClick={previousPage} disabled={history.length === 0} className="inline-flex items-center gap-1 rounded-lg border border-white/[0.1] px-3 py-2 text-zinc-300 hover:border-primary/50 disabled:cursor-not-allowed disabled:opacity-40">
                <ChevronLeft className="h-4 w-4" aria-hidden="true" /> Oldingi
              </button>
              <span className="font-mono text-zinc-400">{history.length + 1}-sahifa</span>
              <button type="button" onClick={nextPage} disabled={!page.has_more || !page.next_after} className="inline-flex items-center gap-1 rounded-lg border border-white/[0.1] px-3 py-2 text-zinc-300 hover:border-primary/50 disabled:cursor-not-allowed disabled:opacity-40">
                Keyingi <ChevronRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </nav>
          )}
        </section>

        <aside aria-label="Katalog haqida" className="space-y-4">
          <div className="rounded-xl border border-white/[0.08] bg-surface-card p-5">
            <div className="flex items-center gap-2 text-primary"><ShieldCheck className="h-4 w-4" aria-hidden="true" /><h2 className="font-heading text-sm font-bold text-zinc-100">Katalog mezonlari</h2></div>
            <p className="mt-3 text-xs leading-relaxed text-zinc-400">Ommaviy ro‘yxatda faqat e’lon qilingan imkoniyatlar va tasdiqlangan tashkilotlar ko‘rinadi. Bo‘sh o‘rinlar soni server javobidan olinadi.</p>
          </div>
          <div className="rounded-xl border border-white/[0.08] bg-surface-card p-5">
            <div className="flex items-center gap-2 text-primary"><BriefcaseBusiness className="h-4 w-4" aria-hidden="true" /><h2 className="font-heading text-sm font-bold text-zinc-100">Shaxsiy amallar</h2></div>
            <p className="mt-3 text-xs leading-relaxed text-zinc-400">Bu sahifa ommaviy e’lonlarni ko‘rsatadi. Ariza, saqlangan e’lon va shaxsiy moslik natijalari hisobga bog‘langan alohida jarayonlardir.</p>
          </div>
        </aside>
      </div>
    </main>
  );
}
