"use client";

import React, { useMemo, useState } from "react";
import { Building2, GraduationCap, Loader2, RefreshCw, Search, ShieldCheck, Users } from "lucide-react";
import { enumLabel } from "@/lib/labels";
import {
  fetchDirectoryInstitutions,
  fetchDirectoryOrganizations,
  fetchDirectoryUsers,
} from "@/lib/platformAdmin";
import { normalizeRoles } from "@/lib/roles";
import { useAsyncData } from "@/lib/useAsyncData";

type DirectoryTab = "users" | "organizations" | "institutions";

const USER_ROLES_ALLOWED = new Set(["ADMIN", "SECURITY_LEAD", "OPERATIONS", "AUDITOR"]);
const ENTITY_ROLES_ALLOWED = new Set(["ADMIN", "OPERATIONS", "MODERATOR", "AUDITOR"]);

function formatUzDate(value?: string | null): string {
  if (!value) return "—";
  const dt = new Date(value);
  return Number.isNaN(dt.getTime()) ? "—" : dt.toLocaleDateString("uz-UZ");
}

export default function DirectoryPanel({ roles }: { roles: string[] }) {
  const upperRoles = useMemo(() => normalizeRoles(roles), [roles]);
  const canViewUsers = upperRoles.some((r) => USER_ROLES_ALLOWED.has(r));
  const canViewEntities = upperRoles.some((r) => ENTITY_ROLES_ALLOWED.has(r));

  const availableTabs = useMemo(() => {
    const list: Array<{ id: DirectoryTab; label: string }> = [];
    if (canViewUsers) list.push({ id: "users", label: "Foydalanuvchilar" });
    if (canViewEntities) {
      list.push({ id: "organizations", label: "Korxonalar" });
      list.push({ id: "institutions", label: "OTM / Universitetlar" });
    }
    return list;
  }, [canViewUsers, canViewEntities]);

  const [requestedTab, setRequestedTab] = useState<DirectoryTab>("users");
  const activeTab: DirectoryTab = availableTabs.some((t) => t.id === requestedTab)
    ? requestedTab
    : (availableTabs[0]?.id ?? "users");

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const usersQuery = useAsyncData(
    activeTab === "users" && canViewUsers
      ? `dir-users:${search.trim()}:${roleFilter}`
      : null,
    () => fetchDirectoryUsers({ q: search.trim(), role: roleFilter, limit: 40 })
  );

  const orgsQuery = useAsyncData(
    activeTab === "organizations" && canViewEntities
      ? `dir-orgs:${search.trim()}:${statusFilter}`
      : null,
    () => fetchDirectoryOrganizations({ q: search.trim(), status: statusFilter, limit: 40 })
  );

  const instsQuery = useAsyncData(
    activeTab === "institutions" && canViewEntities
      ? `dir-insts:${search.trim()}:${statusFilter}`
      : null,
    () => fetchDirectoryInstitutions({ q: search.trim(), status: statusFilter, limit: 40 })
  );

  const currentQuery =
    activeTab === "users" ? usersQuery : activeTab === "organizations" ? orgsQuery : instsQuery;

  return (
    <section className="fb-panel skeuo-card flex flex-col gap-5 p-5 sm:p-6" aria-labelledby="dir-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="dir-title" className="text-lg font-semibold text-[var(--fb-ink)]">
            Yagona katalog va reyestr
          </h2>
          <p className="text-xs text-[var(--fb-ink-muted)]">
            Foydalanuvchilar, korxonalar va oliy ta’lim muassasalari bo‘yicha himoyalangan qidiruv.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="fb-seg" role="group" aria-label="Katalog bo‘limlari">
            {availableTabs.map((t) => (
              <button
                key={t.id}
                type="button"
                aria-pressed={activeTab === t.id}
                onClick={() => setRequestedTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => void currentQuery.reload()}
            className="fb-icon-btn fb-icon-btn-light h-9 w-9"
            aria-label="Katalogni yangilash"
          >
            <RefreshCw className={`h-4 w-4 ${currentQuery.isLoading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* SEARCH & FILTER BAR */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_220px]">
        <label className="relative block">
          <span className="sr-only">Qidiruv</span>
          <Search className="pointer-events-none absolute left-3.5 top-2.5 h-4 w-4 text-[var(--fb-ink-muted)]" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={
              activeTab === "users"
                ? "Ism, niqoblangan telefon yoki elektron pochta…"
                : activeTab === "organizations"
                ? "Korxona nomi, STIR yoki hudud…"
                : "Universitet nomi, reestr kodi yoki STIR…"
            }
            className="skeuo-input w-full rounded-full pl-9 pr-4 py-2 text-xs"
          />
        </label>

        {activeTab === "users" ? (
          <select
            aria-label="Rol bo‘yicha filtr"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="skeuo-input rounded-full px-4 py-2 text-xs"
          >
            <option value="">Barcha rollar</option>
            <option value="ADMIN">{enumLabel("ADMIN")}</option>
            <option value="SECURITY_LEAD">{enumLabel("SECURITY_LEAD")}</option>
            <option value="OPERATIONS">{enumLabel("OPERATIONS")}</option>
            <option value="COMPLIANCE">{enumLabel("COMPLIANCE")}</option>
            <option value="MODERATOR">{enumLabel("MODERATOR")}</option>
            <option value="AUDITOR">{enumLabel("AUDITOR")}</option>
            <option value="FINANCE">{enumLabel("FINANCE")}</option>
            <option value="SUPPORT">{enumLabel("SUPPORT")}</option>
          </select>
        ) : (
          <select
            aria-label="Tasdiq holati bo‘yicha filtr"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="skeuo-input rounded-full px-4 py-2 text-xs"
          >
            <option value="">Barcha holatlar</option>
            <option value="VERIFIED">{enumLabel("VERIFIED")}</option>
            <option value="PENDING_REVIEW">{enumLabel("PENDING_REVIEW")}</option>
            <option value="NEEDS_INFO">{enumLabel("NEEDS_INFO")}</option>
            <option value="UNVERIFIED">{enumLabel("UNVERIFIED")}</option>
            <option value="REJECTED">{enumLabel("REJECTED")}</option>
          </select>
        )}
      </div>

      {currentQuery.error && (
        <p
          role="alert"
          className="rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-4 py-3 text-xs text-rose-700 dark:text-rose-300"
        >
          {currentQuery.error.message}
        </p>
      )}

      {currentQuery.isLoading && !currentQuery.data ? (
        <p className="flex items-center justify-center gap-2 py-12 text-xs text-[var(--fb-ink-muted)]">
          <Loader2 className="h-4 w-4 animate-spin" /> Yuklanmoqda…
        </p>
      ) : activeTab === "users" ? (
        (usersQuery.data ?? []).length === 0 ? (
          <div className="rounded-[22px] skeuo-well px-6 py-10 text-center text-xs text-[var(--fb-ink-secondary)]">
            Qidiruv bo‘yicha foydalanuvchi topilmadi.
          </div>
        ) : (
          <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {(usersQuery.data ?? []).map((u) => (
              <li key={u.id} className="rounded-[22px] skeuo-well p-4 flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span className="fb-avatar h-9 w-9 shrink-0" aria-hidden="true">
                      <Users className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-[var(--fb-ink)]">
                        {u.display_name || "Nomsiz foydalanuvchi"}
                      </p>
                      <p className="truncate text-xs text-[var(--fb-ink-muted)]">
                        {u.masked_contact || "Aloqa yashirilgan"}
                      </p>
                    </div>
                  </div>
                  <span className="fb-capsule shrink-0 px-2.5 py-0.5 text-[11px] font-medium">
                    {enumLabel(u.status)}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                  <span className="inline-flex items-center gap-1 rounded-full bg-[color-mix(in_srgb,var(--fb-ink)_8%,transparent)] px-2.5 py-0.5 font-medium text-[var(--fb-ink-secondary)]">
                    <ShieldCheck className="h-3 w-3" />
                    {u.mfa_enabled ? "2FA faol" : "2FA o‘chiq"}
                  </span>
                  {u.platform_roles.map((r) => (
                    <span key={r} className="fb-capsule px-2.5 py-0.5 font-semibold">
                      {enumLabel(r)}
                    </span>
                  ))}
                  {u.last_login_at && (
                    <span className="ml-auto text-[var(--fb-ink-muted)]">
                      Oxirgi kirish: {formatUzDate(u.last_login_at)}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )
      ) : activeTab === "organizations" ? (
        (orgsQuery.data ?? []).length === 0 ? (
          <div className="rounded-[22px] skeuo-well px-6 py-10 text-center text-xs text-[var(--fb-ink-secondary)]">
            Qidiruv bo‘yicha korxona topilmadi.
          </div>
        ) : (
          <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {(orgsQuery.data ?? []).map((org) => (
              <li key={org.id} className="rounded-[22px] skeuo-well p-4 flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span className="fb-avatar h-9 w-9 shrink-0" aria-hidden="true">
                      <Building2 className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-[var(--fb-ink)]">
                        {org.public_name || org.legal_name || "Nomsiz korxona"}
                      </p>
                      <p className="truncate text-xs text-[var(--fb-ink-muted)]">
                        {org.region || "Hudud ko‘rsatilmagan"}
                        {org.tax_id ? ` · STIR: ${org.tax_id}` : ""}
                      </p>
                    </div>
                  </div>
                  <span className="fb-capsule shrink-0 px-2.5 py-0.5 text-[11px] font-medium">
                    {enumLabel(org.verification_status)}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--fb-ink-secondary)]">
                  <span>Jamoa a’zolari: {org.active_members_count ?? 0}</span>
                  <span>·</span>
                  <span>Faol e’lonlar: {org.published_opportunities_count ?? 0}</span>
                  <span className="ml-auto text-[var(--fb-ink-muted)]">{formatUzDate(org.created_at)}</span>
                </div>
              </li>
            ))}
          </ul>
        )
      ) : (instsQuery.data ?? []).length === 0 ? (
        <div className="rounded-[22px] skeuo-well px-6 py-10 text-center text-xs text-[var(--fb-ink-secondary)]">
          Qidiruv bo‘yicha oliy ta’lim muassasasi topilmadi.
        </div>
      ) : (
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {(instsQuery.data ?? []).map((inst) => (
            <li key={inst.id} className="rounded-[22px] skeuo-well p-4 flex flex-col gap-2">
              <div className="flex items-start justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2.5">
                  <span className="fb-avatar h-9 w-9 shrink-0" aria-hidden="true">
                    <GraduationCap className="h-4 w-4" />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-[var(--fb-ink)]">
                      {inst.official_name || inst.short_name || "OTM"}
                    </p>
                    <p className="truncate text-xs text-[var(--fb-ink-muted)]">
                      {inst.region || "Hudud ko‘rsatilmagan"}
                      {inst.registry_code ? ` · Reestr: ${inst.registry_code}` : ""}
                    </p>
                  </div>
                </div>
                <span className="fb-capsule shrink-0 px-2.5 py-0.5 text-[11px] font-medium">
                  {enumLabel(inst.verification_status)}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--fb-ink-secondary)]">
                <span>Tasdiqlangan talabalar: {inst.verified_students_count ?? 0}</span>
                <span>·</span>
                <span>OTM xodimlari: {inst.active_staff_count ?? 0}</span>
                <span className="ml-auto text-[var(--fb-ink-muted)]">{formatUzDate(inst.created_at)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
