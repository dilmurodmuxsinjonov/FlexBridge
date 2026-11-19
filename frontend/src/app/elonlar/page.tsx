"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  BriefcaseBusiness,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  RotateCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import { fetchOpportunities, type OpportunityPage } from "@/lib/api";
import { useAsyncData } from "@/lib/useAsyncData";
import CountUp from "@/components/motion/CountUp";
import { SkeuoToggle } from "@/components/skeuo/SkeuoPrimitives";
import VacancyCard from "@/components/public/VacancyCard";

type Filters = { query: string; region: string; paid: "" | "true" | "false" };
const EMPTY_FILTERS: Filters = { query: "", region: "", paid: "" };

function BalanceMeter({
  title,
  percentage,
  amountLabel,
  subtitle,
}: {
  title: string;
  percentage: number;
  amountLabel: string;
  subtitle: string;
}) {
  const safePct = Math.max(0, Math.min(100, percentage));
  return (
    <div className="flex flex-col justify-between gap-3 rounded-2xl skeuo-well p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-semibold text-[var(--fb-ink)]">{title}</p>
        <span className="font-mono text-xs font-bold text-[#c94f1d] dark:text-[#f47a3d] tabular-nums">
          {safePct}%
        </span>
      </div>
      <div>
        <p className="font-display text-xl font-bold tracking-tight text-[var(--fb-ink)] tabular-nums">
          {amountLabel}
        </p>
        <div className="fb-progress mt-2.5" aria-hidden="true">
          <span style={{ width: `${safePct}%` }} />
        </div>
        <p className="mt-2 text-[11px] text-[var(--fb-ink-muted)]">{subtitle}</p>
      </div>
    </div>
  );
}

export default function PublicCatalogPage() {
  const [draftQuery, setDraftQuery] = useState("");
  const [draftRegion, setDraftRegion] = useState("");
  const [draftPaid, setDraftPaid] = useState<Filters["paid"]>("");
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [cursor, setCursor] = useState<string | null>(null);
  const [history, setHistory] = useState<(string | null)[]>([]);

  const requestKey = JSON.stringify([
    "catalog",
    filters.query,
    filters.region,
    filters.paid,
    cursor,
  ]);

  const feed = useAsyncData<OpportunityPage>(requestKey, () =>
    fetchOpportunities({
      query: filters.query || undefined,
      region: filters.region || undefined,
      is_paid: filters.paid === "" ? undefined : filters.paid === "true",
      after: cursor || undefined,
      limit: 12,
    })
  );

  const page = feed.data ?? null;
  const catalogItems = page?.items ?? [];
  const totalOpenSlots = catalogItems.reduce(
    (sum, item) => sum + (item.vacancies_available || 0),
    0
  );
  const verifiedOrgCount = new Set(catalogItems.map((item) => item.organization_id)).size;
  const paidCount = catalogItems.filter((item) => item.is_paid).length;
  const paidPercent = catalogItems.length
    ? Math.round((paidCount / catalogItems.length) * 100)
    : 0;
  const tashkentCount = catalogItems.filter((item) =>
    `${item.region || ""} ${item.organization_region || ""}`.toLowerCase().includes("toshkent")
  ).length;
  const tashkentPercent = catalogItems.length
    ? Math.round((tashkentCount / catalogItems.length) * 100)
    : 0;
  const flexModeCount = catalogItems.filter(
    (item) => item.work_mode === "HYBRID" || item.work_mode === "REMOTE"
  ).length;
  const flexModePercent = catalogItems.length
    ? Math.round((flexModeCount / catalogItems.length) * 100)
    : 0;
  const activeQuotaPercent = catalogItems.length
    ? Math.min(100, Math.round((totalOpenSlots / Math.max(catalogItems.length * 3, 1)) * 100))
    : 0;

  function submitFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setHistory([]);
    setCursor(null);
    setFilters({ query: draftQuery.trim(), region: draftRegion, paid: draftPaid });
  }

  function clearFilters() {
    setDraftQuery("");
    setDraftRegion("");
    setDraftPaid("");
    setHistory([]);
    setCursor(null);
    setFilters(EMPTY_FILTERS);
  }

  function applyQuickFilter(next: Partial<Filters>) {
    const merged: Filters = {
      query: next.query ?? draftQuery.trim(),
      region: next.region ?? draftRegion,
      paid: next.paid ?? draftPaid,
    };
    setDraftQuery(merged.query);
    setDraftRegion(merged.region);
    setDraftPaid(merged.paid);
    setHistory([]);
    setCursor(null);
    setFilters(merged);
  }

  function nextPage() {
    if (!page?.has_more || !page.next_after) return;
    setHistory((prev) => [...prev, cursor]);
    setCursor(page.next_after);
  }

  function previousPage() {
    if (history.length === 0) return;
    setCursor(history[history.length - 1]);
    setHistory((prev) => prev.slice(0, -1));
  }

  const hasActiveFilters = Boolean(filters.query || filters.region || filters.paid);

  return (
    <main className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-3.5 py-5 sm:px-6 sm:py-6 md:px-8">
      {/* Top Bento Hero: Search Console + Dark Telemetry Ink Card */}
      <section className="grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
        <div className="fb-panel skeuo-card flex min-w-0 flex-col justify-between p-5 sm:p-7 md:p-8">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="inline-flex items-center gap-2 rounded-full skeuo-well-sm px-3.5 py-1 text-[11px] font-bold uppercase tracking-[0.14em] text-[#c94f1d] dark:text-[#f47a3d]">
                <BriefcaseBusiness className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Ommaviy e’lonlar katalogi</span>
              </span>
              <Link
                href="/"
                prefetch={false}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]"
              >
                <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Bosh sahifa</span>
              </Link>
            </div>

            <h1 className="mt-4 font-display text-2xl font-bold tracking-tight text-[var(--fb-ink)] sm:text-3xl md:text-4xl">
              Tasdiqlangan ish va amaliyot o‘rinlari
            </h1>
            <p className="mt-2.5 max-w-2xl text-sm leading-relaxed text-[var(--fb-ink-secondary)]">
              Dars jadvalingizga mos smenali ishlar va rasmiy dual ta’lim amaliyotlarini hudud hamda
              to‘lov sharti bo‘yicha saralang.
            </p>
          </div>

          <div className="mt-6">
            <form
              onSubmit={submitFilters}
              className="flex flex-col gap-2 rounded-[24px] skeuo-well p-2 lg:flex-row lg:items-center"
            >
              <label className="relative min-w-0 flex-1">
                <span className="sr-only">Lavozim yoki ko‘nikma</span>
                <Search
                  className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--fb-ink-muted)]"
                  aria-hidden="true"
                />
                <input
                  id="opportunity-query"
                  type="search"
                  value={draftQuery}
                  onChange={(event) => setDraftQuery(event.target.value)}
                  placeholder="Lavozim, kompaniya yoki ko‘nikma..."
                  className="w-full rounded-2xl bg-transparent py-2.5 pl-10 pr-3 text-sm text-[var(--fb-ink)] focus:outline-none"
                />
              </label>

              <div className="hidden h-6 w-px bg-[var(--fb-border)] lg:block" aria-hidden="true" />

              <label className="relative lg:w-[164px]">
                <span className="sr-only">Hudud</span>
                <select
                  id="opportunity-region"
                  value={draftRegion}
                  onChange={(event) => setDraftRegion(event.target.value)}
                  className="w-full cursor-pointer appearance-none rounded-2xl bg-black/[0.03] py-2.5 pl-3.5 pr-8 text-sm font-medium text-[var(--fb-ink)] focus:outline-none dark:bg-white/[0.04] lg:bg-transparent"
                >
                  <option value="">Barcha hududlar</option>
                  <option value="Toshkent">Toshkent</option>
                  <option value="Samarqand">Samarqand</option>
                  <option value="Farg">Farg‘ona</option>
                  <option value="Buxoro">Buxoro</option>
                  <option value="Andijon">Andijon</option>
                  <option value="Namangan">Namangan</option>
                </select>
                <ChevronDown
                  className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--fb-ink-muted)]"
                  aria-hidden="true"
                />
              </label>

              <div className="hidden h-6 w-px bg-[var(--fb-border)] lg:block" aria-hidden="true" />

              <label className="relative lg:w-[154px]">
                <span className="sr-only">To‘lov turi</span>
                <select
                  id="opportunity-payment"
                  value={draftPaid}
                  onChange={(event) => setDraftPaid(event.target.value as Filters["paid"])}
                  className="w-full cursor-pointer appearance-none rounded-2xl bg-black/[0.03] py-2.5 pl-3.5 pr-8 text-sm font-medium text-[var(--fb-ink)] focus:outline-none dark:bg-white/[0.04] lg:bg-transparent"
                >
                  <option value="">Barcha to‘lovlar</option>
                  <option value="true">To‘lovli</option>
                  <option value="false">To‘lovsiz</option>
                </select>
                <ChevronDown
                  className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--fb-ink-muted)]"
                  aria-hidden="true"
                />
              </label>

              <button
                type="submit"
                className="skeuo-btn-accent shrink-0 rounded-full px-5 py-2.5 text-sm"
              >
                <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
                <span>Qidirish</span>
              </button>
            </form>

            {/* Quick Preset Pills */}
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
              <span className="font-medium text-[var(--fb-ink-muted)]">Tezkor filtr:</span>
              <button
                type="button"
                onClick={clearFilters}
                className={`rounded-full px-3.5 py-1.5 text-xs ${
                  !hasActiveFilters ? "skeuo-btn-obsidian" : "skeuo-btn-secondary"
                }`}
              >
                Barcha e’lonlar
              </button>
              <button
                type="button"
                onClick={() =>
                  applyQuickFilter({
                    region: filters.region === "Toshkent" ? "" : "Toshkent",
                  })
                }
                className={`rounded-full px-3.5 py-1.5 text-xs ${
                  filters.region === "Toshkent" ? "skeuo-btn-obsidian" : "skeuo-btn-secondary"
                }`}
              >
                Toshkent sh.
              </button>
              <button
                type="button"
                onClick={() =>
                  applyQuickFilter({
                    paid: filters.paid === "true" ? "" : "true",
                  })
                }
                className={`rounded-full px-3.5 py-1.5 text-xs ${
                  filters.paid === "true" ? "skeuo-btn-obsidian" : "skeuo-btn-secondary"
                }`}
              >
                Faqat to‘lovli
              </button>
            </div>
          </div>
        </div>

        {/* Monochrome Dark Bento Showcase Card */}
        <aside
          data-skeuo-dark="true"
          aria-label="Katalog jonli ko‘rsatkichlari"
          className="fb-ink-card flex min-w-0 flex-col justify-between gap-5 p-6 sm:p-7"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-zinc-400">
                Jonli katalog holati
              </p>
              <p className="mt-1.5 font-display text-3xl sm:text-4xl font-bold tracking-tight text-white tabular-nums">
                {feed.isLoading && !page ? "—" : <CountUp value={catalogItems.length} />}
              </p>
              <p className="mt-1 text-xs text-zinc-300">Joriy sahifadagi faol e’lonlar</p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-[11px] font-semibold text-white">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
              <span>Tekshirilgan</span>
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-3.5">
              <p className="text-[11px] text-zinc-300">Bo‘sh kvota</p>
              <p className="mt-1 font-display text-2xl font-bold text-white tabular-nums">
                {feed.isLoading && !page ? "—" : <CountUp value={totalOpenSlots} />}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-3.5">
              <p className="text-[11px] text-zinc-300">Korxonalar</p>
              <p className="mt-1 font-display text-2xl font-bold text-white tabular-nums">
                {feed.isLoading && !page ? "—" : <CountUp value={verifiedOrgCount} />}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/10 pt-4 text-xs">
            <span className="text-zinc-300">Ariza topshirish uchun hisobga kiring</span>
            <Link
              href="/kirish"
              prefetch={false}
              className="inline-flex items-center gap-1.5 rounded-full bg-white px-3.5 py-1.5 font-semibold text-[#0c0d10] transition hover:bg-zinc-200"
            >
              <span>Hisobga kirish</span>
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </div>
        </aside>
      </section>

      {/* Monochrome Bento Telemetry & Filter Toggles */}
      <section
        aria-label="Katalog balansi va tezkor boshqaruv"
        className="fb-panel skeuo-card grid gap-6 p-5 sm:p-6 lg:grid-cols-[290px_minmax(0,1fr)] lg:items-center"
      >
        <div className="space-y-4">
          <div>
            <span className="inline-flex items-center rounded-full skeuo-well-sm px-3 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[#c94f1d] dark:text-[#f47a3d]">
              Jonli tahlil
            </span>
            <h2 className="mt-2.5 font-display text-lg font-bold tracking-tight text-[var(--fb-ink)]">
              Katalog balansi
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
              Tanlangan e’lonlar kesimida to‘lovli, hududiy va moslashuvchan format ulushi.
            </p>
          </div>

          <div className="space-y-2.5 border-t border-[var(--fb-border)] pt-3">
            <SkeuoToggle
              checked={filters.paid === "true"}
              tone="orange"
              label="Faqat to‘lovli e’lonlar"
              description={`${paidCount} ta maoshli vakansiya`}
              onChange={(next) =>
                applyQuickFilter({ paid: next ? "true" : "" })
              }
            />
            <SkeuoToggle
              checked={filters.region === "Toshkent"}
              tone="emerald"
              label="Toshkent sh. ustuvor"
              description={`${tashkentCount} ta poytaxt vakansiyasi`}
              onChange={(next) =>
                applyQuickFilter({ region: next ? "Toshkent" : "" })
              }
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-4">
          <BalanceMeter
            title="To‘lovli ulush"
            percentage={paidPercent}
            amountLabel={`${paidCount} / ${catalogItems.length}`}
            subtitle="Maoshli e’lonlar"
          />
          <BalanceMeter
            title="Toshkent hududi"
            percentage={tashkentPercent}
            amountLabel={`${tashkentCount} ta`}
            subtitle="Poytaxt bo‘yicha"
          />
          <BalanceMeter
            title="Gibrid / Masofa"
            percentage={flexModePercent}
            amountLabel={`${flexModeCount} ta`}
            subtitle="Moslashuvchan"
          />
          <BalanceMeter
            title="Faol kvota"
            percentage={activeQuotaPercent}
            amountLabel={`${totalOpenSlots} o‘rin`}
            subtitle="Mavjud kvota"
          />
        </div>
      </section>

      {/* Main Feed + Criteria Sidebar */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_290px]">
        <section aria-labelledby="feed-heading" className="min-w-0">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b border-[var(--fb-border)] pb-3">
            <div>
              <h2 id="feed-heading" className="font-display text-lg font-bold text-[var(--fb-ink)]">
                Ochiq vakansiyalar va amaliyotlar
              </h2>
              <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">
                {page
                  ? `Joriy sahifada ${page.items.length} ta e’lon`
                  : "Eng so‘nggi tasdiqlangan e’lonlar yuklanmoqda"}
              </p>
            </div>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="text-xs font-semibold text-[#c94f1d] dark:text-[#f47a3d] hover:underline"
              >
                Filtrlarni tozalash
              </button>
            )}
          </div>

          <div aria-live="polite" aria-busy={feed.isLoading}>
            {feed.isLoading && !page && (
              <div
                role="status"
                className="fb-panel skeuo-card p-8 text-center text-sm text-[var(--fb-ink-muted)]"
              >
                E’lonlar yuklanmoqda…
              </div>
            )}

            {feed.error && !feed.isLoading && (
              <div
                role="alert"
                className="fb-panel skeuo-card border border-amber-500/25 p-8 text-center"
              >
                <CircleAlert
                  className="mx-auto h-6 w-6 text-amber-600 dark:text-amber-400"
                  aria-hidden="true"
                />
                <p className="mt-3 text-sm font-semibold text-[var(--fb-ink)]">
                  E’lonlarni yuklab bo‘lmadi
                </p>
                <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">
                  Internet ulanishini tekshirib, qayta urinib ko‘ring.
                </p>
                <button
                  type="button"
                  onClick={() => void feed.reload()}
                  className="mt-4 inline-flex items-center gap-2 rounded-full skeuo-btn-secondary px-4 py-2 text-xs font-semibold"
                >
                  <RotateCw className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Qayta urinish</span>
                </button>
              </div>
            )}

            {!feed.error && page && page.items.length === 0 && (
              <div className="fb-panel skeuo-card p-8 text-center">
                <Search className="mx-auto h-6 w-6 text-[var(--fb-ink-muted)]" aria-hidden="true" />
                <p className="mt-3 text-sm font-semibold text-[var(--fb-ink)]">
                  Mos e’lon topilmadi
                </p>
                <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">
                  Qidiruv so‘zi yoki hudud filtrini o‘zgartirib ko‘ring.
                </p>
              </div>
            )}

            {!feed.error && page && page.items.length > 0 && (
              <div className="grid gap-4 md:grid-cols-2">
                {page.items.map((job) => (
                  <VacancyCard key={job.id} job={job} />
                ))}
              </div>
            )}
          </div>

          {!feed.error && page && (history.length > 0 || page.has_more) && (
            <nav
              aria-label="E’lonlar sahifalari"
              className="mt-5 flex items-center justify-between border-t border-[var(--fb-border)] pt-4 text-xs"
            >
              <button
                type="button"
                onClick={previousPage}
                disabled={history.length === 0}
                className="skeuo-btn-secondary rounded-full px-3.5 py-2 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                <span>Oldingi</span>
              </button>
              <span className="font-mono font-semibold text-[var(--fb-ink-muted)] tabular-nums">
                {history.length + 1}-sahifa
              </span>
              <button
                type="button"
                onClick={nextPage}
                disabled={!page.has_more || !page.next_after}
                className="skeuo-btn-secondary rounded-full px-3.5 py-2 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <span>Keyingi</span>
                <ChevronRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </nav>
          )}
        </section>

        <aside aria-label="Katalog haqida" className="space-y-4">
          <div className="fb-panel skeuo-card p-5">
            <div className="flex items-center gap-2 text-[#c94f1d] dark:text-[#f47a3d]">
              <ShieldCheck className="h-4 w-4 shrink-0" aria-hidden="true" />
              <h3 className="font-display text-sm font-bold text-[var(--fb-ink)]">
                Katalog mezonlari
              </h3>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
              Ommaviy katalogda faqat moderatsiyadan o‘tgan e’lonlar va KYB tekshiruvidan o‘tgan
              tashkilotlar ko‘rsatiladi. Bo‘sh o‘rinlar kvotaga ko‘ra yangilanadi.
            </p>
          </div>

          <div className="fb-panel skeuo-card p-5">
            <div className="flex items-center gap-2 text-[#c94f1d] dark:text-[#f47a3d]">
              <BriefcaseBusiness className="h-4 w-4 shrink-0" aria-hidden="true" />
              <h3 className="font-display text-sm font-bold text-[var(--fb-ink)]">
                Kabinet imkoniyatlari
              </h3>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
              Ariza topshirish, saqlangan e’lonlar, shaxsiy o‘quv jadvali bilan moslik va amaliyot
              kundaligi talaba kabineti orqali boshqariladi.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link
                href="/talaba/kirish"
                prefetch={false}
                className="skeuo-btn-obsidian rounded-full px-3.5 py-1.5 text-xs"
              >
                Talaba kirishi
              </Link>
              <Link
                href="/royxatdan-otish"
                prefetch={false}
                className="skeuo-btn-secondary rounded-full px-3.5 py-1.5 text-xs"
              >
                Ro‘yxatdan o‘tish
              </Link>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
