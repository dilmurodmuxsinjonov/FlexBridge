"use client";

import React, { useMemo, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
  ShieldOff,
  UserCheck,
  UserPlus,
  X,
} from "lucide-react";
import { enumLabel } from "@/lib/labels";
import {
  fetchDirectoryUsers,
  fetchStaffGrants,
  grantStaffRole,
  revokeStaffRole,
  type DirectoryUserItem,
  type StaffGrantItem,
} from "@/lib/platformAdmin";
import { ROLE_AUTHORITY_SUMMARY, isSuperAdmin } from "@/lib/roles";
import { useAsyncData } from "@/lib/useAsyncData";

const PLATFORM_GRANT_ROLES = [
  "MODERATOR",
  "SUPPORT",
  "FINANCE",
  "AUDITOR",
  "COMPLIANCE",
  "OPERATIONS",
  "SECURITY_LEAD",
  "ADMIN",
] as const;

const SCOPE_FILTERS = [
  { id: "ALL", label: "Barchasi" },
  { id: "PLATFORM", label: "Platforma" },
  { id: "ORG", label: "Korxona" },
  { id: "INSTITUTION", label: "OTM va bazaviy" },
] as const;

const SCOPE_LABELS: Record<string, string> = {
  PLATFORM: "Platforma",
  ORG: "Korxona",
  INSTITUTION: "OTM",
  BASE: "Bazaviy",
};

const subscribeNoop = () => () => {};

function formatUzDate(value?: string | null): string {
  if (!value) return "—";
  const dt = new Date(value);
  return Number.isNaN(dt.getTime()) ? "—" : dt.toLocaleDateString("uz-UZ");
}

function grantDisplayName(g: StaffGrantItem): string {
  return g.display_name || g.user_display_name || "Nomsiz xodim";
}

function granterDisplayName(g: StaffGrantItem): string {
  return g.granter_display_name || g.granted_by_display_name || "Tizim vakolati";
}

export default function StaffRolesPanel({
  currentUserId,
  roles,
}: {
  currentUserId: string;
  roles: string[];
}) {
  const canMutate = isSuperAdmin(roles);
  const mounted = useSyncExternalStore(subscribeNoop, () => true, () => false);
  const grantsQuery = useAsyncData("operator-staff-grants", fetchStaffGrants);

  const [scopeFilter, setScopeFilter] = useState<(typeof SCOPE_FILTERS)[number]["id"]>("ALL");
  const [userSearch, setUserSearch] = useState("");
  const [selectedUser, setSelectedUser] = useState<DirectoryUserItem | null>(null);
  const [roleCode, setRoleCode] = useState<string>("MODERATOR");
  const [durationDays, setDurationDays] = useState<number>(3650);
  const [grantReason, setGrantReason] = useState("");
  const [grantBusy, setGrantBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const [revokeTarget, setRevokeTarget] = useState<StaffGrantItem | null>(null);
  const [revokeReason, setRevokeReason] = useState("");
  const [revokeBusy, setRevokeBusy] = useState(false);
  const [revokeError, setRevokeError] = useState<string | null>(null);

  const userDirectoryQuery = useAsyncData(
    canMutate ? `staff-role-user-search:${userSearch.trim()}` : null,
    () => fetchDirectoryUsers({ q: userSearch.trim(), limit: 12 })
  );

  const filteredMatrix = useMemo(() => {
    if (scopeFilter === "ALL") return ROLE_AUTHORITY_SUMMARY;
    if (scopeFilter === "INSTITUTION") {
      return ROLE_AUTHORITY_SUMMARY.filter((item) => item.scope === "INSTITUTION" || item.scope === "BASE");
    }
    return ROLE_AUTHORITY_SUMMARY.filter((item) => item.scope === scopeFilter);
  }, [scopeFilter]);

  const activeGrants = grantsQuery.data?.active_grants ?? [];
  const recentRevoked = grantsQuery.data?.recent_revoked ?? [];
  const directoryUsers = userDirectoryQuery.data ?? [];

  async function handleGrantSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canMutate) return;
    setFormError(null);
    setNotice(null);
    if (!selectedUser) {
      setFormError("Avval ro‘yxatdan xodim yoki foydalanuvchini tanlang.");
      return;
    }
    if (selectedUser.id === currentUserId) {
      setFormError("O‘zingizga platforma rolini bera olmaysiz.");
      return;
    }
    const trimmedReason = grantReason.trim();
    if (trimmedReason.length < 10) {
      setFormError("Asoslantirish kamida 10 belgidan iborat bo‘lishi kerak.");
      return;
    }

    setGrantBusy(true);
    try {
      await grantStaffRole({
        user_id: selectedUser.id,
        role_code: roleCode,
        reason: trimmedReason,
        duration_days: durationDays,
      });
      setNotice(
        `${selectedUser.display_name || "Foydalanuvchi"} uchun «${enumLabel(roleCode)}» vakolati berildi.`
      );
      setSelectedUser(null);
      setGrantReason("");
      await grantsQuery.reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Rol berishda xatolik yuz berdi.");
    } finally {
      setGrantBusy(false);
    }
  }

  async function handleRevokeSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!revokeTarget) return;
    const trimmed = revokeReason.trim();
    if (trimmed.length < 10) {
      setRevokeError("Bekor qilish sababi kamida 10 belgidan iborat bo‘lishi kerak.");
      return;
    }
    setRevokeBusy(true);
    setRevokeError(null);
    try {
      const targetId = revokeTarget.grant_id || revokeTarget.id;
      await revokeStaffRole(targetId, trimmed);
      setNotice(
        `${grantDisplayName(revokeTarget)} ning «${enumLabel(revokeTarget.role_code)}» vakolati bekor qilindi.`
      );
      setRevokeTarget(null);
      setRevokeReason("");
      await grantsQuery.reload();
    } catch (err) {
      setRevokeError(err instanceof Error ? err.message : "Rolni bekor qilishda xatolik yuz berdi.");
    } finally {
      setRevokeBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {/* 1. ROLE PERMISSIONS & AUTHORITY MATRIX */}
      <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="staff-matrix-title">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="staff-matrix-title" className="text-lg font-semibold text-[var(--fb-ink)]">
              Rollar va vakolatlar matritsasi
            </h2>
            <p className="text-xs text-[var(--fb-ink-muted)]">
              Qaysi rol kim tomonidan beriladi va nima qila oladi — barcha rollar uchun yagona nazorat jadvali.
            </p>
          </div>
          <div className="fb-seg" role="group" aria-label="Rol doirasi filtri">
            {SCOPE_FILTERS.map((f) => (
              <button
                key={f.id}
                type="button"
                aria-pressed={scopeFilter === f.id}
                onClick={() => setScopeFilter(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {filteredMatrix.map((item) => (
            <article key={item.code} className="rounded-[22px] skeuo-well p-4 flex flex-col gap-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-[var(--fb-ink)]">{item.labelUz}</h3>
                <div className="flex items-center gap-1.5">
                  <span className="fb-capsule px-2.5 py-0.5 text-[11px] font-medium">
                    {SCOPE_LABELS[item.scope] || item.scope}
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                      item.requiresMfa
                        ? "bg-[color-mix(in_srgb,var(--fb-accent)_14%,transparent)] text-[var(--fb-accent)]"
                        : "bg-[color-mix(in_srgb,var(--fb-ink)_8%,transparent)] text-[var(--fb-ink-secondary)]"
                    }`}
                  >
                    {item.requiresMfa ? "2FA majburiy" : "Oddiy kirish"}
                  </span>
                </div>
              </div>
              <p className="text-xs leading-relaxed text-[var(--fb-ink-secondary)]">{item.purposeUz}</p>
              <div className="mt-1 flex flex-col gap-1 border-t border-[color-mix(in_srgb,var(--fb-ink)_10%,transparent)] pt-2 text-[11px] text-[var(--fb-ink-muted)]">
                <span>
                  <strong className="text-[var(--fb-ink)]">Kim tayinlaydi:</strong> {item.grantedByUz}
                </span>
                <span>
                  <strong className="text-[var(--fb-ink)]">Cheklov:</strong> {item.guardrailUz}
                </span>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* 2. ACTIVE STAFF GRANTS + GRANT FORM */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        {/* ACTIVE GRANTS LIST */}
        <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="active-grants-title">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 id="active-grants-title" className="text-base font-semibold text-[var(--fb-ink)]">
                Amaldagi platforma vakolatlari
              </h2>
              <p className="text-xs text-[var(--fb-ink-muted)]">
                Faol xodim rollari va ularning amal qilish muddati.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void grantsQuery.reload()}
              className="fb-icon-btn fb-icon-btn-light h-9 w-9"
              aria-label="Rollar ro‘yxatini yangilash"
            >
              <RefreshCw className={`h-4 w-4 ${grantsQuery.isLoading ? "animate-spin" : ""}`} />
            </button>
          </div>

          {notice && (
            <p
              role="status"
              className="flex items-center gap-2 rounded-2xl bg-[color-mix(in_srgb,#10b981_14%,transparent)] px-4 py-3 text-xs font-medium text-emerald-700 dark:text-emerald-300"
            >
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{notice}</span>
            </p>
          )}
          {grantsQuery.error && (
            <p
              role="alert"
              className="flex items-center gap-2 rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-4 py-3 text-xs font-medium text-rose-700 dark:text-rose-300"
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{grantsQuery.error.message}</span>
            </p>
          )}

          {grantsQuery.isLoading && !grantsQuery.data ? (
            <p className="flex items-center justify-center gap-2 py-12 text-xs text-[var(--fb-ink-muted)]">
              <Loader2 className="h-4 w-4 animate-spin" /> Yuklanmoqda…
            </p>
          ) : activeGrants.length === 0 ? (
            <div className="rounded-[22px] skeuo-well px-6 py-10 text-center text-xs text-[var(--fb-ink-secondary)]">
              Hozircha faol xodim vakolatlari topilmadi.
            </div>
          ) : (
            <ul className="flex flex-col gap-3">
              {activeGrants.map((grant) => {
                const isSelfAdmin = grant.user_id === currentUserId && grant.role_code === "ADMIN";
                const grantKey = grant.grant_id || grant.id;
                return (
                  <li key={grantKey} className="rounded-[22px] skeuo-well p-4 flex flex-col gap-2.5">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-semibold text-[var(--fb-ink)]">
                            {grantDisplayName(grant)}
                          </span>
                          <span className="fb-capsule px-2.5 py-0.5 text-[11px] font-semibold">
                            {enumLabel(grant.role_code)}
                          </span>
                          {grant.user_id === currentUserId && (
                            <span className="rounded-full bg-[color-mix(in_srgb,var(--fb-ink)_10%,transparent)] px-2 py-0.5 text-[10px] font-semibold text-[var(--fb-ink-secondary)]">
                              Siz
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-xs text-[var(--fb-ink-muted)]">
                          {grant.masked_contact || "Aloqa yashirilgan"} · Tayinlagan: {granterDisplayName(grant)}
                        </p>
                      </div>
                      <span className="text-[11px] font-medium text-[var(--fb-ink-secondary)]">
                        {grant.is_permanent ? "Doimiy vakolat" : `Muddat: ${formatUzDate(grant.expires_at)}`}
                      </span>
                    </div>
                    {grant.reason && (
                      <p className="text-xs text-[var(--fb-ink-secondary)]">{grant.reason}</p>
                    )}
                    {canMutate && (
                      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                        <button
                          type="button"
                          disabled={isSelfAdmin}
                          onClick={() => {
                            setRevokeTarget(grant);
                            setRevokeReason("");
                            setRevokeError(null);
                          }}
                          title={isSelfAdmin ? "O‘z Bosh administrator rolingizni bekor qila olmaysiz" : undefined}
                          className="inline-flex items-center gap-1.5 rounded-full skeuo-btn-secondary px-3.5 py-1.5 text-xs font-semibold disabled:opacity-45"
                        >
                          <ShieldOff className="h-3.5 w-3.5" />
                          <span>Bekor qilish</span>
                        </button>
                        {isSelfAdmin && (
                          <span className="text-[11px] text-[var(--fb-ink-muted)]">
                            O‘z Bosh administrator vakolatingizni o‘zingiz bekor qila olmaysiz
                          </span>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}

          {recentRevoked.length > 0 && (
            <div className="mt-2 border-t border-[color-mix(in_srgb,var(--fb-ink)_10%,transparent)] pt-4">
              <h3 className="text-xs font-semibold text-[var(--fb-ink-secondary)] mb-2">
                Yaqinda bekor qilingan vakolatlar
              </h3>
              <ul className="flex flex-col gap-2">
                {recentRevoked.slice(0, 5).map((grant) => (
                  <li
                    key={grant.grant_id || grant.id}
                    className="fb-file-row flex items-center justify-between gap-3 text-xs"
                  >
                    <span className="min-w-0 truncate font-medium text-[var(--fb-ink)]">
                      {grantDisplayName(grant)} · {enumLabel(grant.role_code)}
                    </span>
                    <span className="shrink-0 text-[11px] text-[var(--fb-ink-muted)]">
                      {formatUzDate(grant.revoked_at)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* GRANT FORM */}
        <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="grant-role-title">
          <div className="flex items-start gap-3">
            <span className="fb-avatar h-10 w-10 shrink-0" aria-hidden="true">
              <UserPlus className="h-4 w-4" />
            </span>
            <div>
              <h2 id="grant-role-title" className="text-base font-semibold text-[var(--fb-ink)]">
                Yangi xodimga rol tayinlash
              </h2>
              <p className="text-xs text-[var(--fb-ink-muted)]">
                Faqat 2FA bilan kirgan Bosh administrator boshqa faol hisobga platforma vakolatini beradi.
              </p>
            </div>
          </div>

          {!canMutate ? (
            <div className="rounded-[22px] skeuo-well p-4 text-xs leading-relaxed text-[var(--fb-ink-secondary)]">
              <p className="font-semibold text-[var(--fb-ink)] mb-1 flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-[var(--fb-accent)]" />
                Faqat ko‘rish rejimi
              </p>
              Rol berish va bekor qilish faqat Bosh administrator (ADMIN) hamda 2FA (TOTP) tasdig‘i bilan bajariladi.
            </div>
          ) : (
            <form onSubmit={handleGrantSubmit} className="flex flex-col gap-3.5">
              {formError && (
                <p
                  role="alert"
                  className="flex items-center gap-2 rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-3.5 py-2.5 text-xs text-rose-700 dark:text-rose-300"
                >
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{formError}</span>
                </p>
              )}

              <div>
                <label htmlFor="staff-user-search" className="block text-xs font-medium text-[var(--fb-ink-secondary)] mb-1">
                  Xodimni qidirish (ism, telefon yoki elektron pochta)
                </label>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-[var(--fb-ink-muted)]" />
                  <input
                    id="staff-user-search"
                    type="text"
                    value={userSearch}
                    onChange={(e) => setUserSearch(e.target.value)}
                    placeholder="Masalan: Dilmurod yoki +998..."
                    className="skeuo-input w-full rounded-xl pl-8 pr-3 py-2 text-xs"
                  />
                </div>
                {selectedUser ? (
                  <div className="mt-2 flex items-center justify-between gap-2 rounded-2xl skeuo-well-sm px-3 py-2 text-xs">
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-[var(--fb-ink)] flex items-center gap-1.5">
                        <UserCheck className="h-3.5 w-3.5 text-[var(--fb-accent)] shrink-0" />
                        <span>{selectedUser.display_name || "Nomsiz foydalanuvchi"}</span>
                      </p>
                      <p className="truncate text-[11px] text-[var(--fb-ink-muted)]">
                        {selectedUser.masked_contact || "Aloqa yashirilgan"}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelectedUser(null)}
                      className="rounded-full px-2.5 py-1 text-[11px] font-semibold text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]"
                    >
                      Almashtirish
                    </button>
                  </div>
                ) : (
                  <ul className="mt-2 max-h-48 overflow-y-auto flex flex-col gap-1.5">
                    {userDirectoryQuery.isLoading && !userDirectoryQuery.data ? (
                      <li className="py-2 text-center text-[11px] text-[var(--fb-ink-muted)]">Qidirilmoqda…</li>
                    ) : directoryUsers.length === 0 ? (
                      <li className="py-2 text-center text-[11px] text-[var(--fb-ink-muted)]">Mos foydalanuvchi topilmadi</li>
                    ) : (
                      directoryUsers.map((u) => {
                        const isSelf = u.id === currentUserId;
                        const disabled = isSelf || u.status !== "ACTIVE";
                        return (
                          <li key={u.id}>
                            <button
                              type="button"
                              disabled={disabled}
                              onClick={() => setSelectedUser(u)}
                              className="w-full rounded-xl skeuo-well-sm px-3 py-2 text-left text-xs transition hover:opacity-95 disabled:opacity-45"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <span className="truncate font-semibold text-[var(--fb-ink)]">
                                  {u.display_name || "Nomsiz foydalanuvchi"}
                                </span>
                                <span className="shrink-0 text-[10px] text-[var(--fb-ink-muted)]">
                                  {isSelf ? "Sizning hisobingiz" : enumLabel(u.status)}
                                </span>
                              </div>
                              <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-[var(--fb-ink-muted)]">
                                <span>{u.masked_contact || "Aloqa yashirilgan"}</span>
                                {u.platform_roles.length > 0 && (
                                  <span>· {u.platform_roles.map((r) => enumLabel(r)).join(", ")}</span>
                                )}
                              </div>
                            </button>
                          </li>
                        );
                      })
                    )}
                  </ul>
                )}
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="flex flex-col gap-1 text-xs font-medium text-[var(--fb-ink-secondary)]">
                  Beriladigan rol
                  <select
                    value={roleCode}
                    onChange={(e) => setRoleCode(e.target.value)}
                    className="skeuo-input rounded-xl px-3 py-2 text-xs"
                  >
                    {PLATFORM_GRANT_ROLES.map((code) => (
                      <option key={code} value={code}>
                        {enumLabel(code)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="flex flex-col gap-1 text-xs font-medium text-[var(--fb-ink-secondary)]">
                  Amal qilish muddati
                  <select
                    value={durationDays}
                    onChange={(e) => setDurationDays(Number(e.target.value))}
                    className="skeuo-input rounded-xl px-3 py-2 text-xs"
                  >
                    <option value={3650}>Doimiy (10 yil)</option>
                    <option value={365}>1 yil (365 kun)</option>
                    <option value={90}>90 kun</option>
                    <option value={30}>30 kun</option>
                  </select>
                </label>
              </div>

              <label className="flex flex-col gap-1 text-xs font-medium text-[var(--fb-ink-secondary)]">
                Tayinlash asosi (audit jurnaliga yoziladi, kamida 10 belgi)
                <textarea
                  rows={3}
                  value={grantReason}
                  onChange={(e) => setGrantReason(e.target.value)}
                  placeholder="Masalan: Muvofiqlik bo‘limiga doimiy mas’ul sifatida tayinlandi"
                  className="skeuo-input resize-none rounded-xl px-3 py-2 text-xs"
                />
              </label>

              <button
                type="submit"
                disabled={grantBusy || !selectedUser || grantReason.trim().length < 10}
                className="skeuo-btn-obsidian w-full rounded-full py-2.5 px-4 text-xs font-semibold disabled:opacity-50 justify-center"
              >
                {grantBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <UserPlus className="h-3.5 w-3.5" />}
                <span>Vakolatni berish</span>
              </button>
            </form>
          )}
        </section>
      </div>

      {/* REVOKE CONFIRMATION MODAL */}
      {mounted &&
        revokeTarget &&
        createPortal(
          <div
            className="fixed inset-0 z-[90] flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-4"
            onMouseDown={(e) => e.target === e.currentTarget && setRevokeTarget(null)}
          >
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="revoke-grant-title"
              className="skeuo-card w-full max-w-md rounded-t-[28px] sm:rounded-[28px] p-6 flex flex-col gap-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 id="revoke-grant-title" className="text-base font-semibold text-[var(--fb-ink)]">
                    Rol vakolatini bekor qilish
                  </h2>
                  <p className="mt-0.5 text-xs text-[var(--fb-ink-muted)]">
                    {grantDisplayName(revokeTarget)} · {enumLabel(revokeTarget.role_code)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setRevokeTarget(null)}
                  className="fb-icon-btn fb-icon-btn-light h-8 w-8"
                  aria-label="Oynani yopish"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {revokeError && (
                <p
                  role="alert"
                  className="rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-3.5 py-2.5 text-xs text-rose-700 dark:text-rose-300"
                >
                  {revokeError}
                </p>
              )}

              <form onSubmit={handleRevokeSubmit} className="flex flex-col gap-3">
                <label className="flex flex-col gap-1 text-xs font-medium text-[var(--fb-ink-secondary)]">
                  Bekor qilish sababi (kamida 10 belgi)
                  <textarea
                    rows={3}
                    value={revokeReason}
                    onChange={(e) => setRevokeReason(e.target.value)}
                    placeholder="Masalan: Xodim boshqa bo‘limga o‘tgani sababli vakolat olib tashlandi"
                    className="skeuo-input resize-none rounded-xl px-3 py-2 text-xs"
                  />
                </label>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setRevokeTarget(null)}
                    className="skeuo-btn-secondary rounded-full px-4 py-2 text-xs"
                  >
                    Yopish
                  </button>
                  <button
                    type="submit"
                    disabled={revokeBusy || revokeReason.trim().length < 10}
                    className="skeuo-btn-accent rounded-full px-4 py-2 text-xs font-semibold disabled:opacity-50"
                  >
                    {revokeBusy ? "Bekor qilinmoqda…" : "Tasdiqlash va bekor qilish"}
                  </button>
                </div>
              </form>
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}
