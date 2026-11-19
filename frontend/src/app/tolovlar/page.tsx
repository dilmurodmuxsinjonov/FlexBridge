"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  CheckCircle2,
  Clock3,
  CreditCard,
  Layers,
  Loader2,
  Lock,
  Receipt,
  RotateCcw,
  ShieldCheck,
  Wallet,
} from "lucide-react";
import {
  createOrgOrder,
  fetchAuthMe,
  fetchMyWorkspaces,
  fetchOrgBillingOverview,
  fetchOrgEntitlements,
  type AuthUser,
  type OrgBillingOverviewResponse,
  type OrgEntitlementsResponse,
  type WorkspaceItem,
} from "@/lib/api";
import { enumLabel } from "@/lib/labels";
import { fetchPublicPrices, type PublicPricePlan, type PublicPricesResponse } from "@/lib/publicCatalog";

type PaymentProviderId = "CLICK" | "PAYME" | "UZUM" | "INVOICE";

interface PaymentProviderOption {
  id: PaymentProviderId;
  title: string;
  subtitle: string;
  badge: string;
}

const PAYMENT_PROVIDERS: readonly PaymentProviderOption[] = [
  {
    id: "CLICK",
    title: "Click",
    subtitle: "Uzcard / Humo karta va ilova orqali tezkor to‘lov",
    badge: "Tez orada ulanadi",
  },
  {
    id: "PAYME",
    title: "Payme",
    subtitle: "Shaxsiy yoki korporativ karta orqali onlayn to‘lov",
    badge: "Tez orada ulanadi",
  },
  {
    id: "UZUM",
    title: "Uzum Bank",
    subtitle: "Uzum ilovasi orqali tasdiqlanuvchi to‘lov",
    badge: "Tez orada ulanadi",
  },
  {
    id: "INVOICE",
    title: "Hisob-faktura (bank o‘tkazmasi)",
    subtitle: "Yuridik shaxslar uchun shartnoma va hisob raqami asosida",
    badge: "Tez orada ulanadi",
  },
];

const BILLING_CAPABLE_ROLES = new Set(["OWNER", "BILLING"]);

export default function PaymentsPage() {
  const [prices, setPrices] = useState<PublicPricesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedPlanCode, setSelectedPlanCode] = useState<string>("ORG_PLAN_30D");
  const [selectedProvider, setSelectedProvider] = useState<PaymentProviderId>("CLICK");

  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [employerOrgs, setEmployerOrgs] = useState<WorkspaceItem[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const [billingOverview, setBillingOverview] = useState<OrgBillingOverviewResponse | null>(null);
  const [entitlements, setEntitlements] = useState<OrgEntitlementsResponse | null>(null);
  const [loadingOrgBilling, setLoadingOrgBilling] = useState(false);

  const [creatingOrder, setCreatingOrder] = useState(false);
  const [orderNotice, setOrderNotice] = useState<string | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);

  const loadEmployerBilling = useCallback(async (organizationId: string) => {
    if (!organizationId) return;
    setLoadingOrgBilling(true);
    try {
      const [overview, ent] = await Promise.all([
        fetchOrgBillingOverview(organizationId),
        fetchOrgEntitlements(organizationId),
      ]);
      setBillingOverview(overview);
      setEntitlements(ent);
    } catch {
      setBillingOverview(null);
      setEntitlements(null);
    } finally {
      setLoadingOrgBilling(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const requestedPlan =
      typeof window !== "undefined"
        ? new URLSearchParams(window.location.search).get("plan")?.trim() || null
        : null;

    Promise.all([
      fetchPublicPrices(),
      fetchAuthMe().catch(() => null),
    ])
      .then(async ([pricesRes, user]) => {
        if (!active) return;
        setPrices(pricesRes);

        const availableCodes = new Set(pricesRes.plans.map((p) => p.plan_code));
        if (requestedPlan && availableCodes.has(requestedPlan)) {
          setSelectedPlanCode(requestedPlan);
        } else if (availableCodes.has("ORG_PLAN_30D")) {
          setSelectedPlanCode("ORG_PLAN_30D");
        } else if (pricesRes.plans[0]) {
          setSelectedPlanCode(pricesRes.plans[0].plan_code);
        }

        setAuthUser(user);
        if (user) {
          try {
            const ws = await fetchMyWorkspaces();
            if (!active) return;
            const eligible = ws.organizations.filter((org) =>
              org.roles.some((role) => BILLING_CAPABLE_ROLES.has(role))
            );
            setEmployerOrgs(eligible);
            if (eligible[0]) {
              const firstOrgId = eligible[0].id;
              setSelectedOrgId(firstOrgId);
              const [overview, ent] = await Promise.all([
                fetchOrgBillingOverview(firstOrgId),
                fetchOrgEntitlements(firstOrgId),
              ]).catch(() => [null, null] as const);
              if (active) {
                setBillingOverview(overview);
                setEntitlements(ent);
              }
            }
          } catch {
            // Non-employer or unauthenticated session keeps checkout preview only.
          }
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setLoadError(err instanceof Error ? err.message : "To‘lov va tarif ma’lumotlarini yuklab bo‘lmadi.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const selectedPlan: PublicPricePlan | null = useMemo(() => {
    if (!prices) return null;
    return prices.plans.find((p) => p.plan_code === selectedPlanCode) ?? prices.plans[0] ?? null;
  }, [prices, selectedPlanCode]);

  const activeProviderOption = useMemo(
    () => PAYMENT_PROVIDERS.find((item) => item.id === selectedProvider) ?? PAYMENT_PROVIDERS[0],
    [selectedProvider]
  );

  const handleCreatePendingOrder = async () => {
    if (!selectedOrgId || !selectedPlan || selectedPlan.price_uzs <= 0) return;
    setCreatingOrder(true);
    setOrderNotice(null);
    setOrderError(null);
    try {
      const idempotencyKey =
        typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
          ? `ord_${crypto.randomUUID()}`
          : `ord_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
      const res = await createOrgOrder(selectedOrgId, {
        plan_code: selectedPlan.plan_code,
        idempotency_key: idempotencyKey,
      });
      setOrderNotice(
        `Buyurtma #${res.order.id.slice(0, 8)} yaratildi (To‘lov kutilmoqda). Summa: ${res.order.amount.toLocaleString("uz-UZ")} ${res.order.currency}.`
      );
      await loadEmployerBilling(selectedOrgId);
    } catch (err: unknown) {
      setOrderError(err instanceof Error ? err.message : "Buyurtma yaratib bo‘lmadi.");
    } finally {
      setCreatingOrder(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href="/tariflar"
          prefetch={false}
          className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--fb-ink-muted)] transition-colors hover:text-[var(--fb-accent)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Tariflar katalogiga qaytish
        </Link>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/"
            prefetch={false}
            className="skeuo-btn-secondary rounded-full px-4 py-1.5 text-xs font-semibold"
          >
            Bosh sahifa
          </Link>
          {employerOrgs.length > 0 && (
            <Link
              href="/employer"
              prefetch={false}
              className="skeuo-btn-obsidian inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-semibold"
            >
              Korxona kabineti
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          )}
        </div>
      </div>

      {/* Header + Provider Gateway Readiness Notice */}
      <section className="rounded-[28px] skeuo-card p-6 sm:p-8 space-y-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full skeuo-badge-recessed px-3 py-1 text-[11px] font-semibold text-[#c94f1d] dark:text-[#f47a3d]">
              <CreditCard className="h-3.5 w-3.5" aria-hidden="true" />
              To‘lovlar va obuna rasmiylashtirish
            </span>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold text-[var(--fb-ink)]">
              Onlayn to‘lov sahifasi
            </h1>
            <p className="text-xs sm:text-sm leading-relaxed text-[var(--fb-ink-secondary)]">
              Ish beruvchi tashkilotlar uchun e’lon paketlari, buyurtma yaratish va hisob-fakturalar markazi.
              Talabalar va nomzodlar uchun FlexBridge’dan foydalanish, ariza berish hamda amaliyot kundaligi mutlaqo bepul (0 UZS).
            </p>
          </div>

          <div
            role="status"
            className="rounded-2xl border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-xs max-w-sm"
          >
            <p className="font-heading font-bold text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              To‘lov shlyuzi hozircha ulanmagan
            </p>
            <p className="mt-1 leading-relaxed text-amber-900/85 dark:text-amber-200/85">
              Click, Payme va Uzum Bank interfeyslari tayyorlangan, biroq jonli to‘lov qabul qilish hali faollashtirilmagan.
              Yaratilgan buyurtmalar “To‘lov kutilmoqda” holatida saqlanadi.
            </p>
          </div>
        </div>
      </section>

      {loading ? (
        <div className="flex flex-col items-center justify-center rounded-[28px] skeuo-card p-16 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-[#c94f1d]" />
          <p className="mt-4 text-sm text-[var(--fb-ink-secondary)]">
            Tarif va to‘lov ma’lumotlari yuklanmoqda...
          </p>
        </div>
      ) : loadError ? (
        <div className="rounded-[28px] skeuo-card p-8 text-center">
          <AlertCircle className="mx-auto h-9 w-9 text-amber-500" />
          <p className="mt-3 text-sm font-semibold text-[var(--fb-ink)]">{loadError}</p>
        </div>
      ) : prices && selectedPlan ? (
        <>
          <div className="grid gap-6 lg:grid-cols-12 items-start">
            {/* Left column: Tariff & Provider selection */}
            <div className="lg:col-span-7 space-y-6">
              {/* Step 1: Select Tariff */}
              <section className="rounded-[26px] skeuo-card p-6 space-y-4">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <h2 className="font-heading text-lg font-bold text-[var(--fb-ink)]">
                      1. Tarif paketini tanlang
                    </h2>
                    <p className="text-xs text-[var(--fb-ink-muted)]">
                      Barcha narxlar shaffof tarzda {prices.currency} valyutasida ko‘rsatilgan.
                    </p>
                  </div>
                  <span className="rounded-full skeuo-badge-recessed px-2.5 py-0.5 text-[11px] font-semibold text-[var(--fb-ink)]">
                    {enumLabel(prices.pricing_model)}
                  </span>
                </div>

                <div className="space-y-3" role="radiogroup" aria-label="Tarif paketlari">
                  {prices.plans.map((plan) => {
                    const active = plan.plan_code === selectedPlan.plan_code;
                    return (
                      <button
                        key={plan.plan_code}
                        type="button"
                        role="radio"
                        aria-checked={active}
                        onClick={() => setSelectedPlanCode(plan.plan_code)}
                        className={`w-full text-left rounded-2xl p-4 transition-all border ${
                          active
                            ? "border-[#c94f1d] bg-[#c94f1d]/10 ring-2 ring-[#c94f1d]/30"
                            : "border-black/10 dark:border-white/10 skeuo-well hover:border-[#c94f1d]/50"
                        }`}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="font-heading text-sm font-bold text-[var(--fb-ink)]">
                                {plan.title}
                              </span>
                              <span className="rounded-full skeuo-badge-recessed px-2 py-0.5 text-[10px] font-semibold text-[var(--fb-ink-secondary)]">
                                {enumLabel(plan.plan_code)}
                              </span>
                            </div>
                            <p className="text-xs text-[var(--fb-ink-secondary)] leading-relaxed">
                              {plan.description}
                            </p>
                            <div className="pt-1 flex flex-wrap gap-3 text-[11px] text-[var(--fb-ink-muted)]">
                              <span className="inline-flex items-center gap-1">
                                <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                                {plan.duration_days} kun
                              </span>
                              <span className="inline-flex items-center gap-1">
                                <Layers className="h-3.5 w-3.5" aria-hidden="true" />
                                {plan.opportunity_slots} ta faol e’lon
                              </span>
                            </div>
                          </div>

                          <div className="text-right shrink-0">
                            <p className="font-heading text-base font-bold tabular-nums text-[#c94f1d] dark:text-[#f47a3d]">
                              {plan.price_uzs === 0
                                ? "0 UZS"
                                : `${plan.price_uzs.toLocaleString("uz-UZ")} ${prices.currency}`}
                            </p>
                            <p className="text-[11px] text-[var(--fb-ink-muted)]">
                              {plan.price_uzs === 0 ? "Pilot / Hamkor" : "Bir martalik to‘lov"}
                            </p>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </section>

              {/* Step 2: Select Payment Method (Adapter-Ready Preview) */}
              <section className="rounded-[26px] skeuo-card p-6 space-y-4">
                <div>
                  <h2 className="font-heading text-lg font-bold text-[var(--fb-ink)]">
                    2. To‘lov usuli (shlyuz ulanganda faollashadi)
                  </h2>
                  <p className="text-xs text-[var(--fb-ink-muted)]">
                    Provayder shartnomasi va HMAC webhook kalitlari kiritilgach tanlangan usul orqali to‘lash ishga tushadi.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="To‘lov usullari">
                  {PAYMENT_PROVIDERS.map((provider) => {
                    const active = provider.id === selectedProvider;
                    return (
                      <button
                        key={provider.id}
                        type="button"
                        role="radio"
                        aria-checked={active}
                        onClick={() => setSelectedProvider(provider.id)}
                        className={`text-left rounded-2xl p-4 transition-all border ${
                          active
                            ? "border-[#c94f1d] bg-[#c94f1d]/10 ring-2 ring-[#c94f1d]/30"
                            : "border-black/10 dark:border-white/10 skeuo-well hover:border-[#c94f1d]/50"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="inline-flex items-center gap-2 font-heading text-sm font-bold text-[var(--fb-ink)]">
                            <Wallet className="h-4 w-4 text-[#c94f1d] dark:text-[#f47a3d]" aria-hidden="true" />
                            {provider.title}
                          </span>
                          <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-800 dark:text-amber-300">
                            {provider.badge}
                          </span>
                        </div>
                        <p className="mt-1.5 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
                          {provider.subtitle}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </section>
            </div>

            {/* Right column: Order summary & checkout actions */}
            <aside className="lg:col-span-5 rounded-[26px] skeuo-card p-6 space-y-5 lg:sticky lg:top-24">
              <div className="flex items-center justify-between gap-2">
                <h2 className="font-heading text-lg font-bold text-[var(--fb-ink)]">
                  Buyurtma xulosasi
                </h2>
                <Receipt className="h-4 w-4 text-[var(--fb-ink-muted)]" aria-hidden="true" />
              </div>

              {employerOrgs.length > 0 && (
                <div className="space-y-1.5">
                  <label
                    htmlFor="payments-org-select"
                    className="block text-xs font-semibold text-[var(--fb-ink)]"
                  >
                    Tashkilot
                  </label>
                  <select
                    id="payments-org-select"
                    value={selectedOrgId}
                    onChange={(e) => {
                      const nextId = e.target.value;
                      setSelectedOrgId(nextId);
                      void loadEmployerBilling(nextId);
                    }}
                    className="w-full rounded-xl skeuo-well px-3 py-2 text-xs text-[var(--fb-ink)] border border-black/10 dark:border-white/10"
                  >
                    {employerOrgs.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name} ({org.region})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="rounded-2xl skeuo-well p-4 space-y-2.5 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[var(--fb-ink-muted)]">Tanlangan tarif</span>
                  <span className="font-semibold text-[var(--fb-ink)]">{selectedPlan.title}</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[var(--fb-ink-muted)]">Amal qilish muddati</span>
                  <span className="font-semibold text-[var(--fb-ink)]">{selectedPlan.duration_days} kun</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[var(--fb-ink-muted)]">Faol e’lon limiti</span>
                  <span className="font-semibold text-[var(--fb-ink)]">{selectedPlan.opportunity_slots} ta</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[var(--fb-ink-muted)]">To‘lov usuli</span>
                  <span className="font-semibold text-[var(--fb-ink)]">{activeProviderOption.title}</span>
                </div>
                <div className="border-t border-black/10 dark:border-white/10 pt-2.5 flex items-baseline justify-between gap-2">
                  <span className="font-heading font-bold text-[var(--fb-ink)]">Jami summa</span>
                  <span className="font-heading text-xl font-bold tabular-nums text-[#c94f1d] dark:text-[#f47a3d]">
                    {selectedPlan.price_uzs === 0
                      ? "0 UZS"
                      : `${selectedPlan.price_uzs.toLocaleString("uz-UZ")} ${prices.currency}`}
                  </span>
                </div>
              </div>

              {orderNotice && (
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-800 dark:text-emerald-300 flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
                  <span>{orderNotice}</span>
                </div>
              )}

              {orderError && (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-800 dark:text-rose-300 flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
                  <span>{orderError}</span>
                </div>
              )}

              <div className="space-y-2.5">
                <button
                  type="button"
                  disabled
                  aria-disabled="true"
                  className="w-full inline-flex items-center justify-center gap-2 rounded-2xl py-3 px-4 text-xs font-semibold border border-black/10 dark:border-white/15 bg-black/5 dark:bg-white/5 text-[var(--fb-ink-muted)] cursor-not-allowed"
                >
                  <Lock className="h-3.5 w-3.5" aria-hidden="true" />
                  Onlayn to‘lash — provayder ulanmagan
                </button>
                <p className="text-[11px] leading-relaxed text-[var(--fb-ink-muted)]">
                  To‘lov tizimi ulangach {activeProviderOption.title} orqali bir bosishda to‘lov ochiladi va tasdiq webhookidan so‘ng kvota avtomatik yoqiladi.
                </p>

                {employerOrgs.length > 0 ? (
                  selectedPlan.price_uzs > 0 ? (
                    <button
                      type="button"
                      disabled={creatingOrder || !selectedOrgId}
                      onClick={() => void handleCreatePendingOrder()}
                      className="skeuo-btn-obsidian w-full inline-flex items-center justify-center gap-2 rounded-2xl py-2.5 px-4 text-xs font-semibold disabled:opacity-50"
                    >
                      {creatingOrder ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                          Buyurtma yaratilmoqda...
                        </>
                      ) : (
                        <>
                          <BriefcaseBusiness className="h-3.5 w-3.5" aria-hidden="true" />
                          Buyurtma yaratish (To‘lov kutilmoqda)
                        </>
                      )}
                    </button>
                  ) : (
                    <p className="rounded-xl skeuo-well p-3 text-[11px] leading-relaxed text-[var(--fb-ink-secondary)]">
                      Pilot sinov kvotasi tashkilot verifikatsiyasi va OTM hamkorligi asosida moderatsiya orqali beriladi.
                    </p>
                  )
                ) : authUser ? (
                  <p className="rounded-xl skeuo-well p-3 text-[11px] leading-relaxed text-[var(--fb-ink-secondary)]">
                    Tashkilot buyurtmasini rasmiylashtirish uchun korxona rahbari (OWNER) yoki moliyachisi (BILLING) hisobidan kirish talab qilinadi.
                  </p>
                ) : (
                  <Link
                    href="/korxona/kirish?redirect=/tolovlar"
                    prefetch={false}
                    className="skeuo-btn-obsidian w-full inline-flex items-center justify-center gap-2 rounded-2xl py-2.5 px-4 text-xs font-semibold"
                  >
                    <Building2 className="h-3.5 w-3.5" aria-hidden="true" />
                    Buyurtma berish uchun korxona kirishi
                  </Link>
                )}
              </div>

              <div className="border-t border-black/10 dark:border-white/10 pt-4 space-y-2.5 text-[11px] text-[var(--fb-ink-secondary)]">
                <div className="flex items-start gap-2">
                  <RotateCcw className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" aria-hidden="true" />
                  <span>
                    <strong className="text-[var(--fb-ink)]">
                      {prices.refund_policy.full_refund_window_hours} soatlik qaytarish kafolati:
                    </strong>{" "}
                    {prices.refund_policy.description}
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <ShieldCheck className="h-4 w-4 text-[#c94f1d] dark:text-[#f47a3d] shrink-0 mt-0.5" aria-hidden="true" />
                  <span>
                    To‘lovlar server tomonidagi idempotent buyurtma va imzolangan webhook (API-X04) tekshiruvisiz faollashtirilmaydi.
                  </span>
                </div>
              </div>
            </aside>
          </div>

          {/* Employer Live Billing Overview & Orders History (only for authenticated OWNER/BILLING) */}
          {employerOrgs.length > 0 && (
            <section className="rounded-[26px] skeuo-card p-6 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="font-heading text-lg font-bold text-[var(--fb-ink)]">
                    Tashkilot buyurtmalari va joriy kvota
                  </h2>
                  <p className="text-xs text-[var(--fb-ink-muted)]">
                    Haqiqiy DB buyurtmalari, hisob-fakturalar va kvota holati.
                  </p>
                </div>
                <Link
                  href="/employer"
                  prefetch={false}
                  className="skeuo-btn-secondary rounded-full px-3.5 py-1.5 text-xs font-semibold"
                >
                  Korxona Moliya bo‘limi
                </Link>
              </div>

              {loadingOrgBilling ? (
                <div className="py-6 flex items-center justify-center gap-2 text-xs text-[var(--fb-ink-muted)]">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  Tashkilot hisobi yuklanmoqda...
                </div>
              ) : billingOverview ? (
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-2xl skeuo-well p-3.5 text-xs">
                      <p className="text-[11px] text-[var(--fb-ink-muted)]">Joriy tarif</p>
                      <p className="mt-0.5 font-heading font-bold text-[var(--fb-ink)]">
                        {enumLabel(billingOverview.plan.code)} ({enumLabel(billingOverview.plan.status)})
                      </p>
                    </div>
                    <div className="rounded-2xl skeuo-well p-3.5 text-xs">
                      <p className="text-[11px] text-[var(--fb-ink-muted)]">Bo‘sh vakansiya slotlari</p>
                      <p className="mt-0.5 font-heading font-bold tabular-nums text-[var(--fb-ink)]">
                        {entitlements?.usage.concurrent_slots_available ?? 0} /{" "}
                        {entitlements?.usage.concurrent_active_limit ?? 0}
                      </p>
                    </div>
                    <div className="rounded-2xl skeuo-well p-3.5 text-xs">
                      <p className="text-[11px] text-[var(--fb-ink-muted)]">Qolgan muddat</p>
                      <p className="mt-0.5 font-heading font-bold tabular-nums text-[var(--fb-ink)]">
                        {entitlements?.usage.days_remaining ?? 0} kun
                      </p>
                    </div>
                  </div>

                  {billingOverview.orders.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-black/10 dark:border-white/10 text-[var(--fb-ink-muted)]">
                            <th className="py-2 pr-3 font-medium">Buyurtma</th>
                            <th className="py-2 pr-3 font-medium">Tarif</th>
                            <th className="py-2 pr-3 font-medium">Summa</th>
                            <th className="py-2 pr-3 font-medium">Holat</th>
                            <th className="py-2 font-medium">Sana</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-black/5 dark:divide-white/5">
                          {billingOverview.orders.map((order) => (
                            <tr key={order.id}>
                              <td className="py-2.5 pr-3 font-mono text-[var(--fb-ink-secondary)]">
                                #{order.id.slice(0, 8)}
                              </td>
                              <td className="py-2.5 pr-3 font-semibold text-[var(--fb-ink)]">
                                {enumLabel(order.plan_code || "XIZMAT_PAKETI")}
                              </td>
                              <td className="py-2.5 pr-3 font-bold tabular-nums text-[var(--fb-ink)]">
                                {order.amount.toLocaleString("uz-UZ")} {order.currency}
                              </td>
                              <td className="py-2.5 pr-3">
                                <span
                                  className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                                    order.status === "PAID"
                                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                                      : order.status === "PENDING_PAYMENT"
                                      ? "border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-300"
                                      : "border-black/10 dark:border-white/15 skeuo-well text-[var(--fb-ink-muted)]"
                                  }`}
                                >
                                  {enumLabel(order.status)}
                                </span>
                              </td>
                              <td className="py-2.5 text-[var(--fb-ink-muted)]">
                                {order.created_at ? new Date(order.created_at).toLocaleDateString("uz-UZ") : "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-xs text-[var(--fb-ink-muted)]">
                      Tashkilotda hali buyurtmalar mavjud emas.
                    </p>
                  )}
                </div>
              ) : null}
            </section>
          )}
        </>
      ) : null}
    </main>
  );
}
