"use client";

import React, { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Flag,
  Globe,
  Loader2,
  MapPin,
  ShieldCheck,
  Star,
} from "lucide-react";
import { fetchAuthMe, type AuthUser } from "@/lib/api";
import { enumLabel } from "@/lib/labels";
import {
  fetchPublicOrganization,
  fetchPublicOrganizationOpportunities,
  fetchPublicOrganizationRatingSummary,
  safeExternalWebsiteUrl,
  type PublicOrganizationOpportunitiesResponse,
  type PublicOrganizationProfile,
  type PublicOrganizationRatingSummary,
} from "@/lib/publicCatalog";
import AuthModal from "@/components/AuthModal";
import ModerationReportModal from "@/components/public/ModerationReportModal";

const MODE_LABELS: Record<string, string> = {
  ONSITE: "Ish joyida",
  HYBRID: "Gibrid",
  REMOTE: "Masofadan",
};

export default function PublicOrganizationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const [org, setOrg] = useState<PublicOrganizationProfile | null>(null);
  const [opps, setOpps] = useState<PublicOrganizationOpportunitiesResponse | null>(null);
  const [rating, setRating] = useState<PublicOrganizationRatingSummary | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [resolvedId, setResolvedId] = useState<string | null>(null);
  const [paging, setPaging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cursorHistory, setCursorHistory] = useState<(string | null)[]>([]);
  const [currentCursor, setCurrentCursor] = useState<string | null>(null);

  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);

  const loading = resolvedId !== id;

  useEffect(() => {
    let active = true;

    Promise.all([
      fetchPublicOrganization(id),
      fetchPublicOrganizationOpportunities(id, { limit: 12 }),
      fetchPublicOrganizationRatingSummary(id).catch(() => null),
      fetchAuthMe().catch(() => null),
    ])
      .then(([orgData, oppsData, ratingData, me]) => {
        if (!active) return;
        setError(null);
        setOrg(orgData);
        setOpps(oppsData);
        setRating(ratingData);
        setUser(me);
      })
      .catch((err: unknown) => {
        if (active) {
          setOrg(null);
          setError(err instanceof Error ? err.message : "Tasdiqlangan tashkilot topilmadi.");
        }
      })
      .finally(() => {
        if (active) setResolvedId(id);
      });

    return () => {
      active = false;
    };
  }, [id]);

  const loadPage = async (nextCursor: string | null, pushHistory?: string | null) => {
    setPaging(true);
    try {
      const res = await fetchPublicOrganizationOpportunities(id, {
        limit: 12,
        after: nextCursor,
      });
      if (pushHistory !== undefined) {
        setCursorHistory((prev) => [...prev, pushHistory]);
      }
      setCurrentCursor(nextCursor);
      setOpps(res);
    } finally {
      setPaging(false);
    }
  };

  const handleReportClick = () => {
    if (!user) {
      setAuthModalOpen(true);
    } else {
      setReportOpen(true);
    }
  };

  const handleAuthSuccess = async () => {
    const fresh = await fetchAuthMe().catch(() => null);
    setUser(fresh);
    setAuthModalOpen(false);
    if (fresh) setReportOpen(true);
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-12">
        <div className="flex flex-col items-center justify-center rounded-[28px] skeuo-card p-16 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-[#c94f1d]" />
          <p className="mt-4 text-sm font-medium text-[var(--fb-ink-secondary)]">
            Tashkilot profili yuklanmoqda...
          </p>
        </div>
      </main>
    );
  }

  if (error || !org) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-12">
        <div className="rounded-[28px] skeuo-card p-10 text-center">
          <AlertCircle className="mx-auto h-10 w-10 text-amber-500" />
          <h1 className="mt-4 font-heading text-xl font-bold text-[var(--fb-ink)]">
            Tashkilot topilmadi yoki hali tasdiqlanmagan
          </h1>
          <p className="mt-2 text-xs sm:text-sm text-[var(--fb-ink-muted)]">
            {error || "Faqat operator tomonidan tasdiqlangan (KYB) korxonalar ochiq katalogda ko‘rsatiladi."}
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link
              href="/elonlar"
              prefetch={false}
              className="skeuo-btn-obsidian inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-xs font-semibold"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              E’lonlar katalogiga o‘tish
            </Link>
            <Link
              href="/"
              prefetch={false}
              className="skeuo-btn-secondary inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-xs font-semibold"
            >
              Bosh sahifa
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const websiteHref = safeExternalWebsiteUrl(org.website);
  const openItems = opps?.items ?? [];

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 space-y-6">
      <nav aria-label="Breadcrumb" className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href="/elonlar"
          prefetch={false}
          className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--fb-ink-muted)] transition-colors hover:text-[var(--fb-accent)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Barcha e’lonlarga qaytish
        </Link>
        <button
          type="button"
          onClick={handleReportClick}
          className="skeuo-btn-secondary inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold"
        >
          <Flag className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" aria-hidden="true" />
          Tashkilot ustidan shikoyat
        </button>
      </nav>

      {/* Organization Hero Card */}
      <section className="rounded-[28px] skeuo-card p-6 sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl skeuo-well text-[#c94f1d] dark:text-[#f47a3d]">
              <Building2 className="h-8 w-8" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-600/25 bg-emerald-600/10 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-800 dark:text-emerald-300">
                  <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                  KYB Tasdiqlangan korxona
                </span>
                {org.region && (
                  <span className="inline-flex items-center gap-1 rounded-full skeuo-badge-recessed px-2.5 py-0.5 text-[11px] font-medium text-[var(--fb-ink-secondary)]">
                    <MapPin className="h-3 w-3" aria-hidden="true" />
                    {org.region}
                  </span>
                )}
              </div>
              <h1 className="mt-2 font-heading text-2xl sm:text-3xl font-bold text-[var(--fb-ink)] break-words">
                {org.public_name}
              </h1>
              {org.description ? (
                <p className="mt-3 max-w-2xl whitespace-pre-wrap text-xs sm:text-sm leading-relaxed text-[var(--fb-ink-secondary)]">
                  {org.description}
                </p>
              ) : (
                <p className="mt-2 text-xs text-[var(--fb-ink-muted)]">
                  Korxona platformada rasmiy shartnoma va MK 118-modda talablari asosida talabalarga ish va amaliyot taklif etadi.
                </p>
              )}

              {org.capabilities.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {org.capabilities.map((cap) => (
                    <span
                      key={cap}
                      className="inline-flex items-center gap-1.5 rounded-xl skeuo-well px-3 py-1.5 text-xs font-semibold text-[var(--fb-ink)]"
                    >
                      <ShieldCheck className="h-3.5 w-3.5 text-[#c94f1d] dark:text-[#f47a3d]" />
                      {enumLabel(cap)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-3 lg:min-w-[260px]">
            {/* Public Rating Summary (API-010) */}
            <div className="rounded-2xl skeuo-well p-4">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--fb-ink-muted)]">
                  Hamkorlik reytingi
                </span>
                <Star className="h-4 w-4 text-amber-500" aria-hidden="true" />
              </div>
              {rating?.score_status === "PUBLISHED" && rating.score !== null ? (
                <div className="mt-2">
                  <p className="font-heading text-2xl font-bold tabular-nums text-[var(--fb-ink)]">
                    {rating.score.toFixed(1)}{" "}
                    <span className="text-xs font-normal text-[var(--fb-ink-muted)]">
                      / 5.0 ({rating.sample_size} ta baho)
                    </span>
                  </p>
                </div>
              ) : (
                <div className="mt-2 space-y-1">
                  <p className="text-xs font-semibold text-[var(--fb-ink)]">
                    {enumLabel(rating?.score_status || "UNRATED")}
                  </p>
                  <p className="text-[11px] text-[var(--fb-ink-muted)]">
                    {rating && !rating.feature_enabled
                      ? "Ommaviy reytinglar hozircha R1 himoyalangan rejimida."
                      : "Xolislik va maxfiylik uchun baho kamida 5 ta tasdiqlangan fikrdan so‘ng ochiladi."}
                  </p>
                </div>
              )}
            </div>

            {websiteHref && (
              <a
                href={websiteHref}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="skeuo-btn-secondary inline-flex items-center justify-between gap-2 rounded-2xl px-4 py-2.5 text-xs font-semibold"
              >
                <span className="inline-flex items-center gap-2 truncate">
                  <Globe className="h-4 w-4 shrink-0 text-[#c94f1d] dark:text-[#f47a3d]" />
                  <span className="truncate">{org.website}</span>
                </span>
                <ExternalLink className="h-3.5 w-3.5 shrink-0 opacity-70" aria-hidden="true" />
              </a>
            )}
          </div>
        </div>
      </section>

      {/* Open Opportunities Grid (API-009) */}
      <section aria-labelledby="org-opps-heading" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2
              id="org-opps-heading"
              className="font-heading text-lg sm:text-xl font-bold text-[var(--fb-ink)]"
            >
              Faol vakansiyalar va amaliyot o‘rinlari
            </h2>
            <p className="text-xs text-[var(--fb-ink-muted)]">
              Faqat moderatsiyadan o‘tgan va hozir ariza qabul qilayotgan ochiq e’lonlar.
            </p>
          </div>
          <span className="rounded-full skeuo-badge-recessed px-3 py-1 font-mono text-xs font-semibold text-[var(--fb-ink)] tabular-nums">
            {openItems.length} ta e’lon
          </span>
        </div>

        {openItems.length === 0 ? (
          <div className="rounded-[28px] skeuo-card p-10 text-center">
            <BriefcaseBusiness className="mx-auto h-9 w-9 text-[var(--fb-ink-muted)]" />
            <h3 className="mt-3 font-heading text-base font-bold text-[var(--fb-ink)]">
              Hozircha faol e’lonlar mavjud emas
            </h3>
            <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">
              Ushbu tashkilotda hozir ochiq kvota qolmagan. Boshqa tasdiqlangan vakansiyalarni ko‘rib chiqing.
            </p>
            <div className="mt-5">
              <Link
                href="/elonlar"
                prefetch={false}
                className="skeuo-btn-obsidian inline-flex items-center gap-2 rounded-full px-5 py-2 text-xs font-semibold"
              >
                Katalogni ko‘rish
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              {openItems.map((item) => (
                <article
                  key={item.id}
                  className="skeuo-card skeuo-card-interactive flex flex-col justify-between gap-4 rounded-[24px] p-5"
                >
                  <div>
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="font-heading text-base font-bold text-[var(--fb-ink)] leading-snug">
                        <Link
                          href={`/ishlar/${item.id}`}
                          prefetch={false}
                          className="hover:text-[#c94f1d] dark:hover:text-[#f47a3d] transition-colors"
                        >
                          {item.title}
                        </Link>
                      </h3>
                      <span className="shrink-0 rounded-full skeuo-badge-recessed px-2.5 py-0.5 text-[11px] font-semibold text-[var(--fb-ink)]">
                        {enumLabel(item.kind)}
                      </span>
                    </div>

                    <div className="mt-2.5 flex flex-wrap gap-3 text-xs text-[var(--fb-ink-muted)]">
                      {item.location && (
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                          {item.location}
                        </span>
                      )}
                      <span className="inline-flex items-center gap-1">
                        <BriefcaseBusiness className="h-3.5 w-3.5" aria-hidden="true" />
                        {MODE_LABELS[item.work_mode] || enumLabel(item.work_mode)}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-3 border-t border-[var(--fb-border)] pt-3">
                    <span className="font-mono text-xs font-semibold text-[var(--fb-ink)] tabular-nums">
                      Bo‘sh kvota: {item.vacancies_available} / {item.capacity}
                    </span>
                    <Link
                      href={`/ishlar/${item.id}`}
                      prefetch={false}
                      className="skeuo-btn-obsidian inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-semibold"
                    >
                      Batafsil
                      <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                    </Link>
                  </div>
                </article>
              ))}
            </div>

            {(cursorHistory.length > 0 || opps?.has_more) && (
              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  disabled={cursorHistory.length === 0 || paging}
                  onClick={() => {
                    const prev = cursorHistory[cursorHistory.length - 1] ?? null;
                    setCursorHistory((h) => h.slice(0, -1));
                    loadPage(prev);
                  }}
                  className="skeuo-btn-secondary inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold disabled:opacity-40"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Oldingi
                </button>
                <button
                  type="button"
                  disabled={!opps?.has_more || !opps.next_cursor || paging}
                  onClick={() => {
                    if (opps?.next_cursor) loadPage(opps.next_cursor, currentCursor);
                  }}
                  className="skeuo-btn-secondary inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold disabled:opacity-40"
                >
                  Keyingi
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </>
        )}
      </section>

      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onSuccess={handleAuthSuccess}
      />

      <ModerationReportModal
        isOpen={reportOpen}
        onClose={() => setReportOpen(false)}
        targetLabel={org.public_name}
        organizationId={org.id}
      />
    </main>
  );
}
