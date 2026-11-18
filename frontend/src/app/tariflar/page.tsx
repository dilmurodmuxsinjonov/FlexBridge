"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  BriefcaseBusiness,
  Building2,
  CheckCircle2,
  Clock3,
  Layers,
  Loader2,
  RotateCcw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { enumLabel } from "@/lib/labels";
import {
  fetchPublicPrices,
  fetchPublicServices,
  type PublicPricesResponse,
  type PublicServicesResponse,
} from "@/lib/publicCatalog";

export default function PublicServicesAndTariffsPage() {
  const [services, setServices] = useState<PublicServicesResponse | null>(null);
  const [prices, setPrices] = useState<PublicPricesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([fetchPublicServices(), fetchPublicPrices()])
      .then(([svcData, priceData]) => {
        if (!active) return;
        setServices(svcData);
        setPrices(priceData);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Tarif ma’lumotlarini yuklab bo‘lmadi.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href="/"
          prefetch={false}
          className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--fb-ink-muted)] transition-colors hover:text-[var(--fb-accent)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Bosh sahifaga qaytish
        </Link>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/haqida"
            prefetch={false}
            className="skeuo-btn-secondary rounded-full px-4 py-1.5 text-xs font-semibold"
          >
            Platforma qo‘llanmalari
          </Link>
          <Link
            href="/korxona/royxatdan-otish"
            prefetch={false}
            className="skeuo-btn-obsidian inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-semibold"
          >
            Korxona ulash
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>
      </div>

      {/* Hero Header */}
      <section className="rounded-[28px] skeuo-card p-6 sm:p-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-1.5 rounded-full skeuo-badge-recessed px-3 py-1 text-[11px] font-semibold text-[#c94f1d] dark:text-[#f47a3d]">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              Ochiq xizmatlar va narx siyosati
            </span>
            <h1 className="mt-3 font-heading text-2xl sm:text-3xl font-bold text-[var(--fb-ink)]">
              FlexBridge Xizmatlar Katalogi & Shaffof Tariflar
            </h1>
            <p className="mt-2 text-xs sm:text-sm leading-relaxed text-[var(--fb-ink-secondary)]">
              Talabalar uchun platformadan foydalanish, ariza topshirish va amaliyot kundaligi yuritish mutlaqo bepul.
              Ish beruvchi tashkilotlar esa tasdiqlangan kvota va 30 kunlik e’lon paketlaridan shaffof narxlarda foydalanadilar.
            </p>
          </div>
          {prices && (
            <div className="rounded-2xl skeuo-well px-4 py-3 text-xs">
              <p className="text-[11px] text-[var(--fb-ink-muted)]">Hisob-kitob valyutasi va modeli</p>
              <p className="mt-0.5 font-heading font-bold text-[var(--fb-ink)]">
                {prices.currency} • {enumLabel(prices.pricing_model)}
              </p>
            </div>
          )}
        </div>
      </section>

      {loading ? (
        <div className="flex flex-col items-center justify-center rounded-[28px] skeuo-card p-16 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-[#c94f1d]" />
          <p className="mt-4 text-sm text-[var(--fb-ink-secondary)]">
            Xizmatlar va tariflar yuklanmoqda...
          </p>
        </div>
      ) : error ? (
        <div className="rounded-[28px] skeuo-card p-8 text-center">
          <AlertCircle className="mx-auto h-9 w-9 text-amber-500" />
          <p className="mt-3 text-sm font-semibold text-[var(--fb-ink)]">{error}</p>
        </div>
      ) : (
        <>
          {/* Tariffs Section (API-012) */}
          {prices && (
            <section aria-labelledby="tariffs-heading" className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2
                    id="tariffs-heading"
                    className="font-heading text-xl font-bold text-[var(--fb-ink)]"
                  >
                    Ish beruvchilar uchun e’lon tariflari
                  </h2>
                  <p className="text-xs text-[var(--fb-ink-muted)]">
                    Faol tasdiqlangan tashkilotlar uchun e’lon joylashtirish paketlari.
                  </p>
                </div>
              </div>

              <div className="grid gap-5 md:grid-cols-3">
                {prices.plans.map((plan) => {
                  const isFeatured = plan.plan_code === "ORG_PLAN_30D";
                  return (
                    <article
                      key={plan.plan_code}
                      className={`skeuo-card flex flex-col justify-between gap-5 rounded-[26px] p-6 ${
                        isFeatured ? "ring-2 ring-[#c94f1d]/40" : ""
                      }`}
                    >
                      <div className="space-y-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="rounded-full skeuo-badge-recessed px-2.5 py-0.5 font-mono text-[11px] font-semibold text-[var(--fb-ink)]">
                            {enumLabel(plan.plan_code)}
                          </span>
                          {isFeatured && (
                            <span className="rounded-full border border-[#c94f1d]/30 bg-[#c94f1d]/10 px-2.5 py-0.5 text-[10px] font-bold text-[#c94f1d] dark:text-[#f47a3d]">
                              Korporativ tanlov
                            </span>
                          )}
                        </div>

                        <h3 className="font-heading text-lg font-bold text-[var(--fb-ink)]">
                          {plan.title}
                        </h3>

                        <div className="rounded-2xl skeuo-well p-4">
                          <p className="font-heading text-2xl font-bold tabular-nums text-[#c94f1d] dark:text-[#f47a3d]">
                            {plan.price_uzs === 0
                              ? "0 UZS (Bepul)"
                              : `${plan.price_uzs.toLocaleString("uz-UZ")} ${prices.currency}`}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-[var(--fb-ink-muted)]">
                            <span className="inline-flex items-center gap-1">
                              <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                              {plan.duration_days} kun amal qiladi
                            </span>
                            <span className="inline-flex items-center gap-1">
                              <Layers className="h-3.5 w-3.5" aria-hidden="true" />
                              {plan.opportunity_slots} ta faol e’lon
                            </span>
                          </div>
                        </div>

                        <p className="text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
                          {plan.description}
                        </p>
                      </div>

                      <Link
                        href="/employer"
                        prefetch={false}
                        className={`${
                          isFeatured ? "skeuo-btn-obsidian" : "skeuo-btn-secondary"
                        } inline-flex w-full items-center justify-center gap-2 rounded-2xl py-2.5 text-xs font-semibold`}
                      >
                        <BriefcaseBusiness className="h-3.5 w-3.5" aria-hidden="true" />
                        Kabinetda tanlash
                      </Link>
                    </article>
                  );
                })}
              </div>

              {/* Refund & Activation Guarantee */}
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl skeuo-card p-5 flex items-start gap-3.5">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl skeuo-well text-emerald-600 dark:text-emerald-400">
                    <RotateCcw className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-heading text-sm font-bold text-[var(--fb-ink)]">
                      To‘lovni qaytarish kafolati ({prices.refund_policy.full_refund_window_hours} soat)
                    </h3>
                    <p className="mt-1 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
                      {prices.refund_policy.description}
                    </p>
                  </div>
                </div>

                <div className="rounded-2xl skeuo-card p-5 flex items-start gap-3.5">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl skeuo-well text-[#c94f1d] dark:text-[#f47a3d]">
                    <ShieldCheck className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-heading text-sm font-bold text-[var(--fb-ink)]">
                      Faollashtirish va nazorat tartibi
                    </h3>
                    <p className="mt-1 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
                      Buyurtma yaratilganda to‘lov provayderi tasdig‘idan so‘ng kvota avtomatik ochiladi. Pilot sinov rejimida bepul OTM/host kvotalari amal qiladi.
                    </p>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Services Catalog Section (API-011) */}
          {services && (
            <section aria-labelledby="services-heading" className="space-y-4">
              <div>
                <h2
                  id="services-heading"
                  className="font-heading text-xl font-bold text-[var(--fb-ink)]"
                >
                  Platforma xizmat yo‘nalishlari va chegaralari
                </h2>
                <p className="text-xs text-[var(--fb-ink-muted)]">
                  Har bir xizmat kimlar uchun mo‘ljallangani va joriy R1 / 2-bosqich holati bilan ochiq ko‘rsatiladi.
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                {services.services.map((svc) => (
                  <article
                    key={svc.code}
                    className="skeuo-card rounded-[24px] p-5 sm:p-6 flex flex-col justify-between gap-4"
                  >
                    <div className="space-y-2.5">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                            svc.is_active
                              ? "border border-emerald-600/25 bg-emerald-600/10 text-emerald-800 dark:text-emerald-300"
                              : "skeuo-badge-recessed text-[var(--fb-ink-muted)]"
                          }`}
                        >
                          {svc.is_active ? (
                            <>
                              <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
                              R{svc.stage} faol xizmat
                            </>
                          ) : (
                            <>
                              <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                              {svc.stage}-bosqich (kelgusi)
                            </>
                          )}
                        </span>
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--fb-ink-muted)]">
                          <Building2 className="h-3.5 w-3.5" aria-hidden="true" />
                          {svc.target_audience}
                        </span>
                      </div>

                      <h3 className="font-heading text-base sm:text-lg font-bold text-[var(--fb-ink)]">
                        {svc.name_uz}
                      </h3>
                      <p className="text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
                        {svc.description}
                      </p>
                    </div>

                    <ul className="space-y-1.5 border-t border-[var(--fb-border)] pt-3">
                      {svc.conditions.map((cond) => (
                        <li
                          key={cond}
                          className="flex items-start gap-2 text-xs text-[var(--fb-ink-secondary)]"
                        >
                          <CheckCircle2
                            className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${
                              svc.is_active ? "text-emerald-500" : "text-[var(--fb-ink-muted)]"
                            }`}
                            aria-hidden="true"
                          />
                          <span>{cond}</span>
                        </li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </main>
  );
}
