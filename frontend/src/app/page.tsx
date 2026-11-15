"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  ChevronDown,
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
import {
  SkeuoRevealGrid,
  SkeuoRevealItem,
  SkeuoStatCard,
  SkeuoToggle,
  SkeuoVerticalMeter,
} from "@/components/skeuo/SkeuoPrimitives";

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
    <article className="rounded-3xl skeuo-card skeuo-card-interactive p-5 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 gap-3.5">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl skeuo-well text-[#D95F2B]">
            <Building2 className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-[var(--fb-ink)]">{job.organization_name}</span>
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/25 bg-emerald-500/12 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300">
                <ShieldCheck className="h-3 w-3" aria-hidden="true" />
                Tasdiqlangan tashkilot
              </span>
            </div>
            <h2 className="font-display text-base font-bold text-[var(--fb-ink)] transition-colors hover:text-[#D95F2B]">
              <Link href={`/ishlar/${job.id}`}>{job.title}</Link>
            </h2>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--fb-ink-muted)]">
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
        <span className="shrink-0 self-start skeuo-badge-recessed text-[var(--fb-ink)]">
          {job.kind === "PART_TIME" ? "Yarim stavka" : job.kind === "INTERNSHIP" ? "Amaliyot" : job.kind}
        </span>
      </div>

      <div className="mt-4 grid gap-3 border-t border-[var(--fb-border)] pt-4 sm:grid-cols-2">
        <div>
          <p className="text-[11px] font-medium text-[var(--fb-ink-muted)]">To‘lov</p>
          <p className="mt-0.5 text-sm font-bold text-[#D95F2B]">{paymentLabel(job)}</p>
        </div>
        <div>
          <p className="text-[11px] font-medium text-[var(--fb-ink-muted)]">Bo‘sh o‘rin</p>
          <p className="mt-0.5 text-sm font-bold text-[var(--fb-ink)]">
            {job.vacancies_available} ta
          </p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--fb-border)] pt-3.5">
        {job.description ? (
          <details className="group text-xs text-[var(--fb-ink-muted)]">
            <summary className="flex cursor-pointer list-none items-center gap-1 font-semibold text-[var(--fb-ink)] hover:text-[#D95F2B]">
              Tavsifni ko‘rish <ArrowRight className="h-3.5 w-3.5 transition-transform group-open:rotate-90" aria-hidden="true" />
            </summary>
            <p className="mt-2 whitespace-pre-wrap leading-relaxed">{job.description}</p>
          </details>
        ) : <div />}
        <Link
          href={`/ishlar/${job.id}`}
          className="skeuo-btn-accent group rounded-full px-4 py-1.5 text-xs"
        >
          <span>Batafsil</span>
          <ArrowRight className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5" aria-hidden="true" />
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

  const catalogItems = page?.items ?? [];
  const totalOpenSlots = catalogItems.reduce((sum, item) => sum + (item.vacancies_available || 0), 0);
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

  return (
    <main className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-3.5 sm:px-4 py-5 sm:py-6 md:px-8">
      <section className="rounded-[28px] sm:rounded-[32px] skeuo-stage p-4 sm:p-5 md:p-8 overflow-hidden">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,0.75fr)] lg:items-center">
          {/* Left: Discovery Search Column */}
          <div className="min-w-0">
            <div className="inline-flex items-center gap-2 rounded-full skeuo-well-sm px-3.5 py-1 text-[11px] font-bold uppercase tracking-[0.14em] text-[#D95F2B]">
              <BriefcaseBusiness className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Ommaviy katalog</span>
            </div>
            <h1 className="mt-3 font-display text-2xl font-bold tracking-tight text-[var(--fb-ink)] md:text-4xl">
              Ish va amaliyot imkoniyatlari
            </h1>
            <p className="mt-2.5 max-w-2xl text-sm leading-relaxed text-[var(--fb-ink-muted)]">
              Dars jadvalingizga mos smenali ishlar va rasmiy dual ta’lim amaliyotlarini toping. Faqat tasdiqlangan tashkilotlar e’lonlari ko‘rsatiladi.
            </p>

            <form
              onSubmit={submitFilters}
              className="mt-6 flex flex-col gap-2 rounded-[26px] skeuo-well p-2 lg:flex-row lg:items-center"
            >
              <label className="relative flex-1 min-w-0">
                <span className="sr-only">Lavozim yoki ko‘nikma</span>
                <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--fb-ink-muted)]" aria-hidden="true" />
                <input
                  id="opportunity-query"
                  type="search"
                  value={draftQuery}
                  onChange={(event) => setDraftQuery(event.target.value)}
                  placeholder="Lavozim, kompaniya yoki ko‘nikma..."
                  className="w-full rounded-2xl bg-transparent py-2.5 pl-10 pr-3 text-sm text-[var(--fb-ink)] placeholder:text-[var(--fb-ink-muted)] focus:outline-none"
                />
              </label>
              <div className="hidden lg:block h-6 w-px bg-[var(--fb-border)]" aria-hidden="true" />
              <label className="relative lg:w-[156px]">
                <span className="sr-only">Hudud</span>
                <select
                  id="opportunity-region"
                  value={draftRegion}
                  onChange={(event) => setDraftRegion(event.target.value)}
                  className="w-full appearance-none rounded-2xl bg-black/[0.03] dark:bg-white/[0.04] lg:bg-transparent py-2.5 pl-3.5 pr-8 text-sm font-medium text-[var(--fb-ink)] focus:outline-none cursor-pointer"
                >
                  <option value="">Barcha hududlar</option>
                  <option value="Toshkent">Toshkent</option>
                  <option value="Samarqand">Samarqand</option>
                  <option value="Farg">Farg‘ona</option>
                  <option value="Buxoro">Buxoro</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--fb-ink-muted)]" aria-hidden="true" />
              </label>
              <div className="hidden lg:block h-6 w-px bg-[var(--fb-border)]" aria-hidden="true" />
              <label className="relative lg:w-[152px]">
                <span className="sr-only">To‘lov turi</span>
                <select
                  id="opportunity-payment"
                  value={draftPaid}
                  onChange={(event) => setDraftPaid(event.target.value as Filters["paid"])}
                  className="w-full appearance-none rounded-2xl bg-black/[0.03] dark:bg-white/[0.04] lg:bg-transparent py-2.5 pl-3.5 pr-8 text-sm font-medium text-[var(--fb-ink)] focus:outline-none cursor-pointer"
                >
                  <option value="">Barcha to‘lovlar</option>
                  <option value="true">To‘lovli</option>
                  <option value="false">To‘lovsiz</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--fb-ink-muted)]" aria-hidden="true" />
              </label>
              <button
                type="submit"
                className="skeuo-btn-accent shrink-0 rounded-full px-5 py-2.5 text-sm"
              >
                <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
                <span>Qidirish</span>
              </button>
            </form>

            {/* Quick Preset Chips */}
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
              <span className="text-[var(--fb-ink-muted)] font-medium">Tezkor filtr:</span>
              <button
                type="button"
                onClick={() => {
                  setDraftRegion("Toshkent");
                  setHistory([]);
                  setCursor(null);
                  setFilters((f) => ({ ...f, region: "Toshkent" }));
                  setReload((v) => v + 1);
                }}
                className={`rounded-full px-3.5 py-1.5 text-xs ${
                  filters.region === "Toshkent" ? "skeuo-btn-obsidian" : "skeuo-btn-secondary"
                }`}
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
                className={`rounded-full px-3.5 py-1.5 text-xs ${
                  filters.paid === "true" ? "skeuo-btn-obsidian" : "skeuo-btn-secondary"
                }`}
              >
                Faqat to‘lovli
              </button>
              <button
                type="button"
                onClick={clearFilters}
                className={`rounded-full px-3.5 py-1.5 text-xs ${
                  !filters.query && !filters.region && !filters.paid
                    ? "skeuo-btn-obsidian"
                    : "skeuo-btn-secondary"
                }`}
              >
                Barcha e’lonlar
              </button>
            </div>
          </div>

          {/* Right: 4-Portal Role Entry Matrix */}
          <div className="grid min-w-0 gap-2.5 rounded-3xl skeuo-well p-3.5 sm:p-4">
            <div className="px-1 text-[11px] font-bold uppercase tracking-wider text-[var(--fb-ink-muted)]">
              Rolingiz bo‘yicha kabinetni tanlang
            </div>
            <div className="rounded-2xl skeuo-card skeuo-card-interactive p-3.5 space-y-2.5">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-xs font-bold text-[var(--fb-ink)]">
                    Talaba / Nomzod Kabineti
                  </p>
                  <p className="text-[11px] text-[var(--fb-ink-muted)] mt-0.5">
                    Rezyume, dars jadvali, arizalar va kundalik e-imzo
                  </p>
                </div>
                <span className="shrink-0 rounded-full border border-sky-500/30 bg-sky-500/12 px-2.5 py-0.5 text-[10px] font-bold text-sky-700 dark:text-sky-300">
                  Talaba
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2 pt-0.5">
                <Link
                  href="/talaba/kirish"
                  className="skeuo-btn-accent rounded-full px-3.5 py-1 text-[11px]"
                >
                  Talaba kirishi
                </Link>
                <Link
                  href="/nomzod"
                  className="skeuo-btn-secondary rounded-full px-3 py-1 text-[11px]"
                >
                  Kabinet
                </Link>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 rounded-2xl skeuo-card skeuo-card-interactive px-3.5 py-3">
              <div className="min-w-0">
                <Link
                  href="/employer"
                  className="text-xs font-bold text-[var(--fb-ink)] hover:text-[#D95F2B] transition-colors"
                >
                  Korxona & HR Markazi
                </Link>
                <p className="text-[11px] text-[var(--fb-ink-muted)] mt-0.5 truncate">
                  Vakansiya joylash, nomzod saralash va mentor tasdig‘i
                </p>
              </div>
              <div className="shrink-0 flex flex-wrap items-center gap-1.5">
                <Link
                  href="/korxona/kirish"
                  className="skeuo-btn-obsidian rounded-full px-3 py-1 text-[10px]"
                >
                  Korxona kirishi
                </Link>
                <Link
                  href="/employer"
                  className="skeuo-btn-secondary rounded-full px-2.5 py-1 text-[10px]"
                >
                  Kabinet
                </Link>
              </div>
            </div>
            <div className="rounded-2xl skeuo-card skeuo-card-interactive px-3.5 py-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-bold text-[var(--fb-ink)]">
                    Universitet / OTM Portali
                  </p>
                  <p className="text-[11px] text-[var(--fb-ink-muted)] mt-0.5">
                    Dekanat nazorati, dars jadvali va yig‘ma hisobotlar
                  </p>
                </div>
                <span className="shrink-0 rounded-full border border-indigo-500/30 bg-indigo-500/12 px-2.5 py-0.5 text-[10px] font-bold text-indigo-700 dark:text-indigo-300">
                  OTM
                </span>
              </div>
              <div className="mt-2.5 flex flex-wrap items-center gap-2">
                <Link
                  href="/universitet/kirish"
                  className="skeuo-btn-obsidian rounded-full px-3 py-1 text-[11px]"
                >
                  OTM kirishi
                </Link>
                <Link
                  href="/university"
                  className="skeuo-btn-secondary rounded-full px-2.5 py-1 text-[11px]"
                >
                  Kabinet
                </Link>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-2xl skeuo-card skeuo-card-interactive px-3.5 py-2.5">
              <div className="min-w-0">
                <p className="text-[11px] font-bold text-amber-700 dark:text-amber-300">Platforma Operatori</p>
                <p className="text-[10px] text-[var(--fb-ink-muted)] truncate">Audit, moderatsiya va moliya nazorati</p>
              </div>
              <Link
                href="/operator/kirish"
                className="skeuo-btn-secondary shrink-0 rounded-full px-3 py-1 text-[11px]"
              >
                Operator kirishi
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Row A: Tactile KPI Stat Strip (natural compact proportions) */}
      <section aria-label="Katalog ko‘rsatkichlari" className="grid gap-4 sm:grid-cols-3">
        <SkeuoStatCard
          title="Faol e’lonlar"
          value={status === "ready" ? catalogItems.length : "—"}
          subtitle="Joriy qidiruv natijasi"
          icon={BriefcaseBusiness}
          tone="orange"
        />
        <SkeuoStatCard
          title="Bo‘sh ish o‘rinlari"
          value={status === "ready" ? totalOpenSlots : "—"}
          subtitle="Mavjud amaliyot kvotalari"
          icon={MapPin}
          tone="sky"
        />
        <SkeuoStatCard
          title="Tasdiqlangan korxonalar"
          value={status === "ready" ? verifiedOrgCount : "—"}
          subtitle="Rasmiy tekshirilgan"
          icon={ShieldCheck}
          tone="emerald"
        />
      </section>

      {/* Row B: Signature Hardware Bento Panel (Meters + Live Filter Toggles) */}
      <section
        aria-label="Katalog puls va tezkor boshqaruv"
        className="grid gap-6 rounded-[28px] skeuo-card p-5 sm:p-6 lg:grid-cols-[275px_minmax(0,1fr)] lg:items-center"
      >
        <div className="space-y-4">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full skeuo-well-sm px-3 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[#D95F2B]">
              Jonli ko‘rsatkichlar
            </span>
            <h2 className="mt-2.5 font-display text-lg font-bold tracking-tight text-[var(--fb-ink)]">
              Katalog balansi
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-[var(--fb-ink-muted)]">
              Faol vakansiyalar bo‘yicha to‘lovli, hududiy va moslashuvchan format ulushi.
            </p>
          </div>

          <div className="space-y-2.5 pt-2 border-t border-[var(--fb-border)]">
            <SkeuoToggle
              checked={filters.paid === "true"}
              tone="orange"
              label="Faqat to‘lovli e’lonlar"
              description={`${paidCount} ta haq to‘lanadigan o‘rin`}
              onChange={(next) => {
                const paidVal: Filters["paid"] = next ? "true" : "";
                setDraftPaid(paidVal);
                setHistory([]);
                setCursor(null);
                setFilters((f) => ({ ...f, paid: paidVal }));
                setReload((v) => v + 1);
              }}
            />
            <SkeuoToggle
              checked={filters.region === "Toshkent"}
              tone="emerald"
              label="Toshkent sh. ustuvor"
              description={`${tashkentCount} ta poytaxt vakansiyasi`}
              onChange={(next) => {
                const regVal = next ? "Toshkent" : "";
                setDraftRegion(regVal);
                setHistory([]);
                setCursor(null);
                setFilters((f) => ({ ...f, region: regVal }));
                setReload((v) => v + 1);
              }}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-4">
          <SkeuoVerticalMeter
            compact
            title="To‘lovli ulush"
            percentage={paidPercent}
            amountLabel={`${paidCount} / ${catalogItems.length || 0}`}
            subtitle="Maoshli e’lonlar"
            tone="orange"
          />
          <SkeuoVerticalMeter
            compact
            title="Toshkent hududi"
            percentage={tashkentPercent}
            amountLabel={`${tashkentCount} ta`}
            subtitle="Poytaxt bo‘yicha"
            tone="sky"
          />
          <SkeuoVerticalMeter
            compact
            title="Gibrid / Masofa"
            percentage={flexModePercent}
            amountLabel={`${flexModeCount} ta`}
            subtitle="Erkin / Gibrid"
            tone="emerald"
          />
          <SkeuoVerticalMeter
            compact
            title="Faol kvota"
            percentage={activeQuotaPercent}
            amountLabel={`${totalOpenSlots} o‘rin`}
            subtitle="Umumiy kvota"
            tone="indigo"
          />
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <section aria-labelledby="feed-heading" className="min-w-0">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b border-[var(--fb-border)] pb-3">
            <div>
              <h2 id="feed-heading" className="font-display text-lg font-bold text-[var(--fb-ink)]">E’lonlar</h2>
              <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">
                {status === "ready" && page
                  ? `Joriy sahifada ${page.items.length} ta e’lon`
                  : "Yangi e’lonlar birinchi ko‘rsatiladi"}
              </p>
            </div>
            {(filters.query || filters.region || filters.paid) && (
              <button type="button" onClick={clearFilters} className="text-xs font-semibold text-[#D95F2B] hover:underline">
                Filtrlarni tozalash
              </button>
            )}
          </div>

          <div aria-live="polite" aria-busy={status === "loading"}>
            {status === "loading" && (
              <div role="status" className="rounded-3xl skeuo-card p-8 text-center text-sm text-[var(--fb-ink-muted)]">
                E’lonlar yuklanmoqda…
              </div>
            )}
            {status === "error" && (
              <div role="alert" className="rounded-3xl skeuo-card border border-amber-500/25 p-8 text-center">
                <CircleAlert className="mx-auto h-6 w-6 text-amber-600 dark:text-amber-400" aria-hidden="true" />
                <p className="mt-3 text-sm font-semibold text-[var(--fb-ink)]">E’lonlarni yuklab bo‘lmadi</p>
                <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">Ulanishni tekshirib, qayta urinib ko‘ring.</p>
                <button type="button" onClick={() => setReload((value) => value + 1)} className="mt-4 inline-flex items-center gap-2 rounded-full skeuo-btn-secondary px-4 py-2 text-xs font-semibold">
                  <RotateCw className="h-3.5 w-3.5" aria-hidden="true" /> Qayta urinish
                </button>
              </div>
            )}
            {status === "ready" && page?.items.length === 0 && (
              <div className="rounded-3xl skeuo-card p-8 text-center">
                <Search className="mx-auto h-6 w-6 text-[var(--fb-ink-muted)]" aria-hidden="true" />
                <p className="mt-3 text-sm font-semibold text-[var(--fb-ink)]">Hozircha e’lon topilmadi</p>
                <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">Boshqa so‘z yoki hudud bilan qidirib ko‘ring.</p>
              </div>
            )}
            {status === "ready" && page && page.items.length > 0 && (
              <SkeuoRevealGrid className="grid gap-4 md:grid-cols-2">
                {page.items.map((job) => (
                  <SkeuoRevealItem key={job.id}>
                    <VacancyCard job={job} />
                  </SkeuoRevealItem>
                ))}
              </SkeuoRevealGrid>
            )}
          </div>

          {status === "ready" && page && (history.length > 0 || page.has_more) && (
            <nav aria-label="E’lonlar sahifalari" className="mt-5 flex items-center justify-between border-t border-[var(--fb-border)] pt-4 text-xs">
              <button type="button" onClick={previousPage} disabled={history.length === 0} className="skeuo-btn-secondary rounded-full px-3.5 py-2 disabled:cursor-not-allowed disabled:opacity-40">
                <ChevronLeft className="h-4 w-4" aria-hidden="true" /> Oldingi
              </button>
              <span className="font-mono font-semibold text-[var(--fb-ink-muted)]">{history.length + 1}-sahifa</span>
              <button type="button" onClick={nextPage} disabled={!page.has_more || !page.next_after} className="skeuo-btn-secondary rounded-full px-3.5 py-2 disabled:cursor-not-allowed disabled:opacity-40">
                Keyingi <ChevronRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </nav>
          )}
        </section>

        <aside aria-label="Katalog haqida" className="space-y-4">
          <div className="rounded-3xl skeuo-card p-5">
            <div className="flex items-center gap-2 text-[#D95F2B]">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              <h2 className="font-display text-sm font-bold text-[var(--fb-ink)]">Katalog mezonlari</h2>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-[var(--fb-ink-muted)]">Ommaviy ro‘yxatda faqat e’lon qilingan imkoniyatlar va tasdiqlangan tashkilotlar ko‘rinadi. Bo‘sh o‘rinlar soni tashkilot kvotasiga ko‘ra avtomatik yangilanadi.</p>
          </div>
          <div className="rounded-3xl skeuo-card p-5">
            <div className="flex items-center gap-2 text-[#D95F2B]">
              <BriefcaseBusiness className="h-4 w-4" aria-hidden="true" />
              <h2 className="font-display text-sm font-bold text-[var(--fb-ink)]">Kabinet imkoniyatlari</h2>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-[var(--fb-ink-muted)]">Bu sahifa ommaviy e’lonlarni ko‘rsatadi. Ariza, saqlangan e’lon va shaxsiy moslik natijalari hisobga bog‘langan alohida jarayonlardir.</p>
          </div>
        </aside>
      </div>
    </main>
  );
}
