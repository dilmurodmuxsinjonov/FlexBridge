"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeftRight,
  ArrowRight,
  BookOpenCheck,
  BriefcaseBusiness,
  Building2,
  CalendarClock,
  CheckCircle2,
  CircleAlert,
  Compass,
  FileCheck2,
  FileText,
  GraduationCap,
  LayoutDashboard,
  Lock,
  MessageSquareLock,
  RotateCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import {
  fetchAuthMe,
  fetchOpportunities,
  type AuthUser,
  type OpportunityPage,
} from "@/lib/api";
import { resolvePortalDashboard } from "@/lib/roles";
import { useAsyncData } from "@/lib/useAsyncData";
import CountUp from "@/components/motion/CountUp";
import VacancyCard from "@/components/public/VacancyCard";

const ROLE_CARDS = [
  {
    id: "student",
    badge: "Talaba",
    title: "Talaba / Nomzod",
    icon: UserCheck,
    summary:
      "Rezyume yarating, o‘quv jadvalingizga to‘qnashmaydigan smenali ish yoki amaliyot toping va kunlik kundalikni E-Imzo bilan tasdiqlang.",
    audience: "Bakalavr, magistratura talabalari va bitiruvchilar uchun",
    loginHref: "/talaba/kirish",
    loginLabel: "Talaba kirishi",
    portalHref: "/nomzod",
    portalLabel: "Kabinet",
  },
  {
    id: "employer",
    badge: "Ish beruvchi",
    title: "Korxona / HR & Mentor",
    icon: Building2,
    summary:
      "KYB tekshiruvidan o‘tgan tashkilot sifatida vakansiya joylang, nomzodlarni Kanban bosqichlarida saralang va amaliyot mentorligini yuriting.",
    audience: "Rasmiy korxonalar, HR mutaxassislar va amaliyot mentorlari uchun",
    loginHref: "/korxona/kirish",
    loginLabel: "Korxona kirishi",
    portalHref: "/employer",
    portalLabel: "Kabinet",
  },
  {
    id: "university",
    badge: "OTM Nazorat",
    title: "Universitet / OTM Dekanat",
    icon: GraduationCap,
    summary:
      "Talabalarni amaliyot joylariga biriktiring, dars jadvalini boshqaring, kundaliklarni tekshiring va yakuniy akademik xulosalarni eksport qiling.",
    audience: "OTM dekanati, kafedra mudirlari va amaliyot rahbarlari uchun",
    loginHref: "/universitet/kirish",
    loginLabel: "OTM kirishi",
    portalHref: "/university",
    portalLabel: "Kabinet",
  },
  {
    id: "operator",
    badge: "Operator",
    title: "Platforma Nazorati",
    icon: ShieldAlert,
    summary:
      "Tashkilot KYB va OTM vakolatlarini tasdiqlang, e’lonlarni moderatsiya qiling, o‘zgarmas audit jurnali va moliya intizomini kuzating.",
    audience: "MFA himoyali maxsus platforma operatorlari va auditorlar uchun",
    loginHref: "/operator/kirish",
    loginLabel: "Operator kirishi",
    portalHref: "/operator",
    portalLabel: "Panel",
  },
] as const;

const CAPABILITIES = [
  {
    title: "Dars jadvaliga moslik",
    icon: CalendarClock,
    detail:
      "OTM o‘quv jadvalidagi bo‘sh soatlar bilan smena vaqtlari avtomatik solishtiriladi va Mehnat Kodeksi 118-modda me’yori saqlanadi.",
  },
  {
    title: "E-Imzoli Kundalik & Shartnoma",
    icon: BookOpenCheck,
    detail:
      "Uch tomonlama amaliyot shartnomasi, kunlik ish qaydnomasi, mentor bahosi va yakuniy akademik xulosa raqamli imzo bilan muhrlanadi.",
  },
  {
    title: "KYB & OTM tasdiqlash",
    icon: ShieldCheck,
    detail:
      "Har bir korxona STIR va rasmiy hujjatlar asosida tekshiriladi, OTM vakillari esa akkreditatsiya reestri orqali vakolat oladi.",
  },
  {
    title: "Ichki xavfsiz chat & guruhlar",
    icon: MessageSquareLock,
    detail:
      "Kontakt kodi va guruh kanallari orqali talaba, HR menejer va kafedra rahbari o‘rtasida xavfsiz to‘g‘ridan-to‘g‘ri muloqot olib boriladi.",
  },
] as const;

const CHAIN_NODES = [
  {
    label: "Talaba",
    detail: "Jadval, ariza va kundalik",
  },
  {
    label: "Korxona",
    detail: "KYB, vakansiya va mentor",
  },
  {
    label: "OTM",
    detail: "Dekanat, dars jadvali, baho",
  },
  {
    label: "Operator",
    detail: "Audit, moderatsiya, moliya",
  },
] as const;

export default function LandingPage() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let active = true;
    const syncAuth = () => {
      fetchAuthMe()
        .then((user) => {
          if (active) setCurrentUser(user);
        })
        .catch(() => {
          if (active) setCurrentUser(null);
        });
    };
    syncAuth();
    window.addEventListener("flexbridge:auth-changed", syncAuth);
    return () => {
      active = false;
      window.removeEventListener("flexbridge:auth-changed", syncAuth);
    };
  }, []);

  const featured = useAsyncData<OpportunityPage>("landing:featured-opportunities", () =>
    fetchOpportunities({ limit: 4 })
  );

  const items = featured.data?.items ?? [];
  const totalOpenSlots = items.reduce((sum, item) => sum + (item.vacancies_available || 0), 0);
  const verifiedOrgCount = new Set(items.map((item) => item.organization_id)).size;
  const dashboard = currentUser ? resolvePortalDashboard(currentUser.roles) : null;

  return (
    <main className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-3.5 py-5 sm:px-6 sm:py-6 md:px-8">
      {/* Signed-in Quick Jump Banner */}
      {currentUser && dashboard && (
        <section
          aria-label="Faol sessiya"
          className="fb-panel skeuo-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-6"
        >
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl skeuo-well text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-[var(--fb-ink)]">
                Siz tizimga kirgansiz{currentUser.display_name ? `: ${currentUser.display_name}` : ""}
              </p>
              <p className="text-xs text-[var(--fb-ink-muted)]">
                Shaxsiy ishchi hududingizga bir bosishda o‘tishingiz mumkin.
              </p>
            </div>
          </div>
          <Link
            href={dashboard.href}
            prefetch={false}
            className="skeuo-btn-obsidian shrink-0 rounded-full px-4 py-2 text-xs"
          >
            <LayoutDashboard className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Kabinetimga o‘tish ({dashboard.label})</span>
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </section>
      )}

      {/* Hero Bento Grid */}
      <section className="grid gap-5 lg:grid-cols-[minmax(0,1.28fr)_minmax(0,0.72fr)]">
        {/* Left Hero Narrative & Primary CTAs */}
        <div className="fb-panel skeuo-card flex min-w-0 flex-col justify-between gap-6 p-6 sm:p-8 md:p-10">
          <div className="space-y-4">
            <div className="inline-flex flex-wrap items-center gap-2 rounded-full skeuo-well-sm px-3.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-[#c94f1d] dark:text-[#f47a3d]">
              <ShieldCheck className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span>O‘zR Mehnat Kodeksi 118-modda · Rasmiy ekotizim</span>
            </div>

            <h1 className="font-display text-3xl font-bold leading-[1.08] tracking-tight text-[var(--fb-ink)] sm:text-4xl lg:text-[2.75rem]">
              Talabalar amaliyoti, smenali ish va OTM nazorati — bitta rasmiy ekotizimda
            </h1>

            <p className="max-w-2xl text-sm leading-relaxed text-[var(--fb-ink-secondary)] sm:text-base">
              FlexBridge talabalarning dars jadvaliga to‘qnashmaydigan smenali ish va dual ta’lim
              amaliyotlarini, O‘zR Mehnat Kodeksi 118-moddasi asosida ikki tomonlama E-Imzo
              shartnomalarini hamda universitet dekanati nazoratini yagona platformada birlashtiradi.
            </p>
          </div>

          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/royxatdan-otish"
                prefetch={false}
                className="skeuo-btn-accent rounded-full px-5 py-3 text-xs sm:text-sm"
              >
                <span>Ro‘yxatdan o‘tish</span>
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/kirish"
                prefetch={false}
                className="skeuo-btn-obsidian rounded-full px-5 py-3 text-xs sm:text-sm"
              >
                <Lock className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Hisobga kirish</span>
              </Link>
              <Link
                href="/elonlar"
                prefetch={false}
                className="skeuo-btn-secondary rounded-full px-5 py-3 text-xs sm:text-sm"
              >
                <Search className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Ochiq e’lonlarni ko‘rish</span>
              </Link>
            </div>

            <div className="grid gap-2.5 border-t border-[var(--fb-border)] pt-4 text-xs text-[var(--fb-ink-secondary)] sm:grid-cols-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-[#c94f1d] dark:text-[#f47a3d]" aria-hidden="true" />
                <span>Ikki tomonlama raqamli E-Imzo</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-[#c94f1d] dark:text-[#f47a3d]" aria-hidden="true" />
                <span>Dars jadvaliga mos smenalar</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-[#c94f1d] dark:text-[#f47a3d]" aria-hidden="true" />
                <span>KYB va OTM rasmiy tekshiruvi</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Monochrome Dark Bento Showcase: Live Metrics + 4-Party Verified Chain */}
        <aside
          data-skeuo-dark="true"
          aria-label="Platforma jonli ko‘rsatkichlari va 4 tomonlama zanjir"
          className="fb-ink-card flex min-w-0 flex-col justify-between gap-6 p-6 sm:p-7"
        >
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-zinc-400">
                Jonli platforma holati
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/10 px-2.5 py-0.5 text-[11px] font-semibold text-white">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
                <span>Faol reestr</span>
              </span>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2.5">
              <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-3">
                <p className="text-[11px] text-zinc-300">So‘nggi e’lon</p>
                <p className="mt-1 font-display text-2xl font-bold text-white tabular-nums">
                  {featured.isLoading && !featured.data ? "—" : <CountUp value={items.length} />}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-3">
                <p className="text-[11px] text-zinc-300">Bo‘sh o‘rin</p>
                <p className="mt-1 font-display text-2xl font-bold text-white tabular-nums">
                  {featured.isLoading && !featured.data ? "—" : <CountUp value={totalOpenSlots} />}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-3">
                <p className="text-[11px] text-zinc-300">Korxona</p>
                <p className="mt-1 font-display text-2xl font-bold text-white tabular-nums">
                  {featured.isLoading && !featured.data ? "—" : <CountUp value={verifiedOrgCount} />}
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-3 border-t border-white/10 pt-5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-semibold text-white">
                4 tomonlama tasdiqlangan ishonch zanjiri
              </p>
              <ArrowLeftRight className="h-3.5 w-3.5 text-zinc-400" aria-hidden="true" />
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              {CHAIN_NODES.map((node, index) => (
                <div
                  key={node.label}
                  className="rounded-2xl border border-white/10 bg-white/[0.05] p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-white">{node.label}</span>
                    <span className="font-mono text-[10px] font-semibold text-zinc-400 tabular-nums">
                      0{index + 1}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] leading-snug text-zinc-300">{node.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </section>

      {/* 4-Role Ecosystem Bento Grid */}
      <section aria-labelledby="roles-heading" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#c94f1d] dark:text-[#f47a3d]">
              Rollar ekotizimi
            </p>
            <h2
              id="roles-heading"
              className="mt-1 font-display text-xl font-bold tracking-tight text-[var(--fb-ink)] sm:text-2xl"
            >
              Kimlar uchun va qanday ishlaydi?
            </h2>
          </div>
          <Link
            href="/kirish"
            prefetch={false}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]"
          >
            <span>Yagona kirish oynasi</span>
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {ROLE_CARDS.map((role) => {
            const Icon = role.icon;
            return (
              <article
                key={role.id}
                className="fb-panel skeuo-card skeuo-card-interactive flex min-w-0 flex-col justify-between gap-4 p-5 sm:p-6"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl skeuo-well text-[var(--fb-ink)]">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <span className="rounded-full skeuo-badge-recessed px-2.5 py-0.5 text-[10px] font-bold text-[var(--fb-ink-secondary)]">
                      {role.badge}
                    </span>
                  </div>

                  <h3 className="font-display text-base font-bold text-[var(--fb-ink)]">
                    {role.title}
                  </h3>
                  <p className="text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
                    {role.summary}
                  </p>
                </div>

                <div className="space-y-3 border-t border-[var(--fb-border)] pt-3.5">
                  <p className="text-[11px] font-medium text-[var(--fb-ink-muted)]">
                    {role.audience}
                  </p>
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      href={role.loginHref}
                      prefetch={false}
                      className="skeuo-btn-obsidian rounded-full px-3.5 py-1.5 text-[11px]"
                    >
                      {role.loginLabel}
                    </Link>
                    <Link
                      href={role.portalHref}
                      prefetch={false}
                      className="skeuo-btn-secondary rounded-full px-3 py-1.5 text-[11px]"
                    >
                      {role.portalLabel}
                    </Link>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* Key Capabilities Showcase */}
      <section
        aria-labelledby="capabilities-heading"
        className="fb-panel skeuo-card space-y-5 p-5 sm:p-7"
      >
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#c94f1d] dark:text-[#f47a3d]">
              Tizim arxitekturasi
            </p>
            <h2
              id="capabilities-heading"
              className="mt-1 font-display text-xl font-bold tracking-tight text-[var(--fb-ink)] sm:text-2xl"
            >
              Asosiy imkoniyatlar
            </h2>
          </div>
          <Link
            href="/haqida"
            prefetch={false}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]"
          >
            <span>Qo‘llanmalarni o‘qish</span>
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((cap) => {
            const Icon = cap.icon;
            return (
              <div key={cap.title} className="rounded-2xl skeuo-well p-4 sm:p-5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl skeuo-card text-[#c94f1d] dark:text-[#f47a3d]">
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </div>
                <h3 className="mt-3 font-display text-sm font-bold text-[var(--fb-ink)]">
                  {cap.title}
                </h3>
                <p className="mt-1.5 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
                  {cap.detail}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Live Featured Vacancies Preview */}
      <section aria-labelledby="featured-heading" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-[var(--fb-border)] pb-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#c94f1d] dark:text-[#f47a3d]">
              Ommaviy katalogdan lavha
            </p>
            <h2
              id="featured-heading"
              className="mt-1 font-display text-xl font-bold tracking-tight text-[var(--fb-ink)] sm:text-2xl"
            >
              So‘nggi tasdiqlangan e’lonlar
            </h2>
          </div>
          <Link
            href="/elonlar"
            prefetch={false}
            className="skeuo-btn-obsidian rounded-full px-4 py-2 text-xs"
          >
            <span>Barcha e’lonlarni ko‘rish</span>
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>

        <div aria-live="polite" aria-busy={featured.isLoading}>
          {featured.isLoading && !featured.data && (
            <div
              role="status"
              className="fb-panel skeuo-card p-8 text-center text-sm text-[var(--fb-ink-muted)]"
            >
              E’lonlar yuklanmoqda…
            </div>
          )}

          {featured.error && !featured.isLoading && (
            <div
              role="alert"
              className="fb-panel skeuo-card border border-amber-500/25 p-8 text-center"
            >
              <CircleAlert
                className="mx-auto h-6 w-6 text-amber-600 dark:text-amber-400"
                aria-hidden="true"
              />
              <p className="mt-3 text-sm font-semibold text-[var(--fb-ink)]">
                So‘nggi e’lonlarni yuklab bo‘lmadi
              </p>
              <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">
                Qayta urinib ko‘ring yoki to‘liq katalogga o‘ting.
              </p>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                <button
                  type="button"
                  onClick={() => void featured.reload()}
                  className="inline-flex items-center gap-2 rounded-full skeuo-btn-secondary px-4 py-2 text-xs font-semibold"
                >
                  <RotateCw className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Qayta urinish</span>
                </button>
                <Link
                  href="/elonlar"
                  prefetch={false}
                  className="skeuo-btn-obsidian rounded-full px-4 py-2 text-xs"
                >
                  Katalogga o‘tish
                </Link>
              </div>
            </div>
          )}

          {!featured.error && featured.data && items.length === 0 && (
            <div className="fb-panel skeuo-card p-8 text-center">
              <BriefcaseBusiness
                className="mx-auto h-6 w-6 text-[var(--fb-ink-muted)]"
                aria-hidden="true"
              />
              <p className="mt-3 text-sm font-semibold text-[var(--fb-ink)]">
                Hozircha nashr qilingan e’lonlar yo‘q
              </p>
              <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">
                Yangi vakansiyalar tasdiqlanishi bilan shu yerda va katalogda ko‘rinadi.
              </p>
              <div className="mt-4">
                <Link
                  href="/elonlar"
                  prefetch={false}
                  className="skeuo-btn-secondary inline-flex rounded-full px-4 py-2 text-xs"
                >
                  Katalogni ochish
                </Link>
              </div>
            </div>
          )}

          {!featured.error && items.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2">
              {items.slice(0, 4).map((job) => (
                <VacancyCard key={job.id} job={job} compact />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Bottom Legal & Trust Bento Strip */}
      <section
        aria-label="Huquqiy asos va qo‘llanmalar"
        className="fb-panel skeuo-card flex flex-col justify-between gap-4 p-5 sm:flex-row sm:items-center sm:px-7"
      >
        <div className="space-y-1">
          <p className="text-xs font-bold text-[var(--fb-ink)]">
            Huquqiy kafolatlar va me’yoriy hujjatlar
          </p>
          <p className="text-xs text-[var(--fb-ink-secondary)]">
            Shaxsiy ma’lumotlar himoyasi, O‘zR Mehnat Kodeksi 118-modda talablari va platforma
            foydalanish qoidalari bilan tanishing.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Link
            href="/haqida"
            prefetch={false}
            className="skeuo-btn-secondary rounded-full px-3.5 py-2 text-xs"
          >
            <Compass className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Platforma haqida</span>
          </Link>
          <Link
            href="/shartlar"
            prefetch={false}
            className="skeuo-btn-secondary rounded-full px-3.5 py-2 text-xs"
          >
            <FileText className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Shartlar</span>
          </Link>
          <Link
            href="/maxfiylik"
            prefetch={false}
            className="skeuo-btn-secondary rounded-full px-3.5 py-2 text-xs"
          >
            <FileCheck2 className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Maxfiylik</span>
          </Link>
        </div>
      </section>
    </main>
  );
}
