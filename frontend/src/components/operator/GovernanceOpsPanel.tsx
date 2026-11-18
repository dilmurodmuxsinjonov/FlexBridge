"use client";

import React, { useMemo, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import {
  Activity,
  AlertCircle,
  Building2,
  CheckCircle2,
  Clock,
  FileText,
  KeyRound,
  Loader2,
  RefreshCw,
  Scale,
  ShieldCheck,
  X,
} from "lucide-react";
import { enumLabel } from "@/lib/labels";
import {
  RETENTION_CATEGORIES,
  claimModerationAppeal,
  claimOwnerContinuityCase,
  decideModerationAppeal,
  decideOwnerContinuityCase,
  decideRecoveryRequest,
  evaluateRetentionDryRun,
  fetchModerationAppeals,
  fetchOwnerContinuityCases,
  fetchPilotReadiness,
  fetchPrivacyRequests,
  fetchRecoveryRequests,
  resolvePrivacyRequest,
  type ModerationAppealItem,
  type OwnerContinuityCaseItem,
  type PrivacyRequestItem,
  type RecoveryRequestItem,
  type RetentionEvaluationResult,
} from "@/lib/platformAdmin";
import { canUseOperatorModule, normalizeRoles } from "@/lib/roles";
import { useAsyncData } from "@/lib/useAsyncData";

export type GovernanceSection =
  | "PRIVACY"
  | "RECOVERY"
  | "APPEALS"
  | "CONTINUITY"
  | "OPERATIONS";

type ModalActionState =
  | { kind: "PRIVACY"; item: PrivacyRequestItem }
  | { kind: "RECOVERY"; item: RecoveryRequestItem }
  | { kind: "APPEAL"; item: ModerationAppealItem }
  | { kind: "CONTINUITY"; stage: "MODERATOR" | "COMPLIANCE"; item: OwnerContinuityCaseItem }
  | null;

const subscribeNoop = () => () => {};

function formatUzDateTime(value?: string | null): string {
  if (!value) return "—";
  const dt = new Date(value);
  return Number.isNaN(dt.getTime()) ? "—" : dt.toLocaleString("uz-UZ");
}

function decisionOptionsFor(modal: NonNullable<ModalActionState>): Array<{ value: string; label: string }> {
  if (modal.kind === "PRIVACY") {
    return [
      { value: "RESOLVED", label: "Hal qilindi" },
      { value: "REJECTED", label: "Rad etildi" },
    ];
  }
  if (modal.kind === "RECOVERY") {
    return [
      { value: "APPROVE", label: "Tasdiqlash (72 soat)" },
      { value: "REJECT", label: "Rad etish" },
    ];
  }
  if (modal.kind === "APPEAL") {
    return [
      { value: "UPHOLD", label: "Rad qarorini kuchida qoldirish" },
      { value: "REOPEN", label: "E’lonni qayta ochish" },
    ];
  }
  if (modal.stage === "MODERATOR") {
    return [
      { value: "RECOMMEND", label: "Komplayensga tavsiya etish" },
      { value: "NEEDS_INFO", label: "Ma’lumot so‘rash" },
      { value: "REJECT", label: "Rad etish" },
    ];
  }
  return [
    { value: "APPROVE", label: "Yangi egaga tasdiqlash" },
    { value: "NEEDS_INFO", label: "Ma’lumot so‘rash" },
    { value: "REJECT", label: "Rad etish" },
  ];
}

export default function GovernanceOpsPanel({
  roles,
  initialSection,
}: {
  roles: string[];
  initialSection?: GovernanceSection;
}) {
  const upperRoles = useMemo(() => normalizeRoles(roles), [roles]);
  const mounted = useSyncExternalStore(subscribeNoop, () => true, () => false);

  const availableSections = useMemo(() => {
    const list: Array<{ id: GovernanceSection; label: string }> = [];
    if (canUseOperatorModule(upperRoles, "PRIVACY_REQUESTS")) {
      list.push({ id: "PRIVACY", label: "Maxfiylik (GDPR)" });
    }
    if (canUseOperatorModule(upperRoles, "RECOVERY_REVIEWS")) {
      list.push({ id: "RECOVERY", label: "Parol tiklash" });
    }
    if (canUseOperatorModule(upperRoles, "APPEALS")) {
      list.push({ id: "APPEALS", label: "Apellyatsiyalar" });
    }
    if (canUseOperatorModule(upperRoles, "CONTINUITY")) {
      list.push({ id: "CONTINUITY", label: "Egasi vorisligi" });
    }
    if (canUseOperatorModule(upperRoles, "OPERATIONS")) {
      list.push({ id: "OPERATIONS", label: "Pilot va saqlash" });
    }
    return list;
  }, [upperRoles]);

  const [requestedSection, setRequestedSection] = useState<GovernanceSection | undefined>(initialSection);
  const [prevInitial, setPrevInitial] = useState(initialSection);
  if (prevInitial !== initialSection) {
    setPrevInitial(initialSection);
    if (initialSection) setRequestedSection(initialSection);
  }

  const activeSection: GovernanceSection = availableSections.some((s) => s.id === requestedSection)
    ? (requestedSection as GovernanceSection)
    : (availableSections[0]?.id ?? "PRIVACY");

  // Privacy state
  const [privacyStatus, setPrivacyStatus] = useState<string>("");
  const privacyQuery = useAsyncData(
    activeSection === "PRIVACY" && canUseOperatorModule(upperRoles, "PRIVACY_REQUESTS")
      ? `gov-privacy:${privacyStatus}`
      : null,
    () => fetchPrivacyRequests({ status: privacyStatus || undefined, limit: 50 })
  );

  // Recovery state
  const [recoveryStatus, setRecoveryStatus] = useState<string>("PENDING_REVIEW");
  const recoveryQuery = useAsyncData(
    activeSection === "RECOVERY" && canUseOperatorModule(upperRoles, "RECOVERY_REVIEWS")
      ? `gov-recovery:${recoveryStatus}`
      : null,
    () => fetchRecoveryRequests({ status: recoveryStatus, limit: 50 })
  );

  // Appeals state
  const appealsQuery = useAsyncData(
    activeSection === "APPEALS" && canUseOperatorModule(upperRoles, "APPEALS") ? "gov-appeals" : null,
    () => fetchModerationAppeals(50)
  );

  // Continuity state
  const hasModerator = upperRoles.includes("MODERATOR");
  const hasCompliance = upperRoles.includes("COMPLIANCE");
  const [requestedStage, setRequestedStage] = useState<"MODERATOR" | "COMPLIANCE">(
    hasModerator ? "MODERATOR" : "COMPLIANCE"
  );
  const activeStage: "MODERATOR" | "COMPLIANCE" =
    requestedStage === "MODERATOR" && hasModerator
      ? "MODERATOR"
      : requestedStage === "COMPLIANCE" && hasCompliance
      ? "COMPLIANCE"
      : hasModerator
      ? "MODERATOR"
      : "COMPLIANCE";

  const continuityOpenQuery = useAsyncData(
    activeSection === "CONTINUITY" && canUseOperatorModule(upperRoles, "CONTINUITY")
      ? `gov-continuity-open:${activeStage}`
      : null,
    () => fetchOwnerContinuityCases(activeStage, { unassigned: true, limit: 50 })
  );
  const continuityMineQuery = useAsyncData(
    activeSection === "CONTINUITY" && canUseOperatorModule(upperRoles, "CONTINUITY")
      ? `gov-continuity-mine:${activeStage}`
      : null,
    () => fetchOwnerContinuityCases(activeStage, { unassigned: false, limit: 50 })
  );

  // Operations state
  const pilotQuery = useAsyncData(
    activeSection === "OPERATIONS" && canUseOperatorModule(upperRoles, "OPERATIONS")
      ? "gov-pilot-readiness"
      : null,
    fetchPilotReadiness
  );
  const [retentionCategory, setRetentionCategory] = useState<string>(RETENTION_CATEGORIES[0]);
  const [retentionAgeDays, setRetentionAgeDays] = useState<number>(30);
  const [retentionBusy, setRetentionBusy] = useState(false);
  const [retentionResult, setRetentionResult] = useState<RetentionEvaluationResult | null>(null);

  // Shared notice / error / modal
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [claimingId, setClaimingId] = useState<string | null>(null);

  const [modal, setModal] = useState<ModalActionState>(null);
  const [decision, setDecision] = useState<string>("");
  const [reason, setReason] = useState<string>("");
  const [modalBusy, setModalBusy] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  function openModal(next: NonNullable<ModalActionState>) {
    const opts = decisionOptionsFor(next);
    setModal(next);
    setDecision(opts[0]?.value ?? "");
    setReason("");
    setModalError(null);
  }

  async function handleClaimAppeal(caseId: string) {
    setClaimingId(caseId);
    setActionError(null);
    setNotice(null);
    try {
      await claimModerationAppeal(caseId);
      setNotice("Apellyatsiya ishi sizga biriktirildi.");
      await appealsQuery.reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Biriktirib bo‘lmadi.");
    } finally {
      setClaimingId(null);
    }
  }

  async function handleClaimContinuity(caseId: string) {
    setClaimingId(caseId);
    setActionError(null);
    setNotice(null);
    try {
      await claimOwnerContinuityCase(activeStage, caseId);
      setNotice("Vorislik ishi sizga biriktirildi. Endi qaror chiqarishingiz mumkin.");
      await Promise.all([continuityOpenQuery.reload(), continuityMineQuery.reload()]);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Biriktirib bo‘lmadi.");
    } finally {
      setClaimingId(null);
    }
  }

  async function handleModalSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!modal) return;
    const minLen = modal.kind === "PRIVACY" ? 5 : 15;
    const trimmed = reason.trim();
    if (trimmed.length < minLen) {
      setModalError(`Asoslantirish kamida ${minLen} belgidan iborat bo‘lishi kerak.`);
      return;
    }

    setModalBusy(true);
    setModalError(null);
    setNotice(null);
    try {
      if (modal.kind === "PRIVACY") {
        await resolvePrivacyRequest(modal.item.id, {
          status: decision as "RESOLVED" | "REJECTED",
          reason: trimmed,
        });
        setNotice(`${modal.item.display_name || "Foydalanuvchi"} maxfiylik so‘rovi yangilandi.`);
        setModal(null);
        await privacyQuery.reload();
      } else if (modal.kind === "RECOVERY") {
        const res = await decideRecoveryRequest(modal.item.id, {
          decision: decision as "APPROVE" | "REJECT",
          reason: trimmed,
        });
        setNotice(
          res.status === "APPROVED"
            ? `${modal.item.display_name || "Hisob"} uchun tiklash tasdiqlandi (72 soat amal qiladi).`
            : `${modal.item.display_name || "Hisob"} bo‘yicha tiklash so‘rovi rad etildi.`
        );
        setModal(null);
        await recoveryQuery.reload();
      } else if (modal.kind === "APPEAL") {
        await decideModerationAppeal(modal.item.case_id, {
          decision: decision as "UPHOLD" | "REOPEN",
          reason: trimmed,
        });
        setNotice("Apellyatsiya bo‘yicha yakuniy qaror muhrlandi.");
        setModal(null);
        await appealsQuery.reload();
      } else {
        await decideOwnerContinuityCase(modal.stage, modal.item.id, {
          decision: decision as "RECOMMEND" | "APPROVE" | "REJECT" | "NEEDS_INFO",
          reason: trimmed,
          expected_revision: 1,
        });
        setNotice("Vorislik qarori muvaffaqiyatli qabul qilindi.");
        setModal(null);
        await Promise.all([continuityOpenQuery.reload(), continuityMineQuery.reload()]);
      }
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Qarorni saqlashda xatolik yuz berdi.");
    } finally {
      setModalBusy(false);
    }
  }

  async function handleRetentionRun(e: React.FormEvent) {
    e.preventDefault();
    setRetentionBusy(true);
    setActionError(null);
    setNotice(null);
    try {
      const res = await evaluateRetentionDryRun({
        data_category: retentionCategory,
        age_days: retentionAgeDays,
      });
      setRetentionResult(res);
      setNotice("Saqlash muddati bo‘yicha xavfsiz tekshiruv (dry-run) qayd etildi.");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Tekshiruvni bajarib bo‘lmadi.");
    } finally {
      setRetentionBusy(false);
    }
  }

  function reloadActive() {
    if (activeSection === "PRIVACY") void privacyQuery.reload();
    if (activeSection === "RECOVERY") void recoveryQuery.reload();
    if (activeSection === "APPEALS") void appealsQuery.reload();
    if (activeSection === "CONTINUITY") {
      void continuityOpenQuery.reload();
      void continuityMineQuery.reload();
    }
    if (activeSection === "OPERATIONS") void pilotQuery.reload();
  }

  return (
    <section className="fb-panel skeuo-card flex flex-col gap-5 p-5 sm:p-6" aria-labelledby="gov-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="gov-title" className="text-lg font-semibold text-[var(--fb-ink)]">
            Komplayens, maxfiylik va tiklash navbatlari
          </h2>
          <p className="text-xs text-[var(--fb-ink-muted)]">
            GDPR so‘rovlari, parolni tiklash tasdig‘i, apellyatsiyalar, korxona vorisligi va pilot tayyorligi.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="fb-seg flex-wrap" role="group" aria-label="Boshqaruv bo‘limlari">
            {availableSections.map((s) => (
              <button
                key={s.id}
                type="button"
                aria-pressed={activeSection === s.id}
                onClick={() => setRequestedSection(s.id)}
              >
                {s.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={reloadActive}
            className="fb-icon-btn fb-icon-btn-light h-9 w-9"
            aria-label="Ro‘yxatni yangilash"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
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
      {actionError && (
        <p
          role="alert"
          className="flex items-center gap-2 rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-4 py-3 text-xs font-medium text-rose-700 dark:text-rose-300"
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{actionError}</span>
        </p>
      )}

      {/* 1. PRIVACY REQUESTS */}
      {activeSection === "PRIVACY" && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-[var(--fb-ink-secondary)]">
              Foydalanuvchilarning shaxsiy ma’lumotlarni eksport qilish, tuzatish yoki o‘chirish bo‘yicha arizalari.
            </p>
            <select
              aria-label="Maxfiylik holati filtri"
              value={privacyStatus}
              onChange={(e) => setPrivacyStatus(e.target.value)}
              className="skeuo-input rounded-full px-3.5 py-1.5 text-xs"
            >
              <option value="">Barcha holatlar</option>
              <option value="PENDING">{enumLabel("PENDING")}</option>
              <option value="IN_PROGRESS">{enumLabel("IN_PROGRESS")}</option>
              <option value="RESOLVED">{enumLabel("RESOLVED")}</option>
              <option value="REJECTED">{enumLabel("REJECTED")}</option>
            </select>
          </div>

          {privacyQuery.error && (
            <p role="alert" className="rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-4 py-3 text-xs text-rose-700 dark:text-rose-300">
              {privacyQuery.error.message}
            </p>
          )}
          {privacyQuery.isLoading && !privacyQuery.data ? (
            <p className="flex items-center justify-center gap-2 py-10 text-xs text-[var(--fb-ink-muted)]">
              <Loader2 className="h-4 w-4 animate-spin" /> Yuklanmoqda…
            </p>
          ) : (privacyQuery.data ?? []).length === 0 ? (
            <div className="rounded-[22px] skeuo-well px-6 py-10 text-center text-xs text-[var(--fb-ink-secondary)]">
              Maxfiylik so‘rovlari topilmadi.
            </div>
          ) : (
            <ul className="flex flex-col gap-3">
              {(privacyQuery.data ?? []).map((req) => {
                const canResolve = req.status === "PENDING" || req.status === "IN_PROGRESS";
                return (
                  <li key={req.id} className="rounded-[22px] skeuo-well p-4 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex min-w-0 items-start gap-3">
                      <span className="fb-avatar h-9 w-9 shrink-0" aria-hidden="true">
                        <FileText className="h-4 w-4" />
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-[var(--fb-ink)]">
                          {req.display_name || "Foydalanuvchi"} · {enumLabel(req.kind)}
                        </p>
                        <p className="text-xs text-[var(--fb-ink-muted)]">
                          {enumLabel(req.status)} · Muddat: {formatUzDateTime(req.due_at)}
                        </p>
                        {req.reason && (
                          <p className="mt-1 text-xs text-[var(--fb-ink-secondary)]">{req.reason}</p>
                        )}
                      </div>
                    </div>
                    {canResolve && (
                      <button
                        type="button"
                        onClick={() => openModal({ kind: "PRIVACY", item: req })}
                        className="skeuo-btn-obsidian rounded-full px-4 py-1.5 text-xs font-semibold"
                      >
                        Hal qilish
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      {/* 2. RECOVERY REVIEWS */}
      {activeSection === "RECOVERY" && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-[var(--fb-ink-secondary)]">
              2FA yoki zaxira kodini yo‘qotgan hisoblar uchun shaxsni tasdiqlab tiklashga ruxsat berish (2FA talab etiladi).
            </p>
            <select
              aria-label="Tiklash holati filtri"
              value={recoveryStatus}
              onChange={(e) => setRecoveryStatus(e.target.value)}
              className="skeuo-input rounded-full px-3.5 py-1.5 text-xs"
            >
              <option value="PENDING_REVIEW">{enumLabel("PENDING_REVIEW")}</option>
              <option value="APPROVED">{enumLabel("APPROVED")}</option>
              <option value="REJECTED">{enumLabel("REJECTED")}</option>
            </select>
          </div>

          {recoveryQuery.error && (
            <p role="alert" className="rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-4 py-3 text-xs text-rose-700 dark:text-rose-300">
              {recoveryQuery.error.message}
            </p>
          )}
          {recoveryQuery.isLoading && !recoveryQuery.data ? (
            <p className="flex items-center justify-center gap-2 py-10 text-xs text-[var(--fb-ink-muted)]">
              <Loader2 className="h-4 w-4 animate-spin" /> Yuklanmoqda…
            </p>
          ) : (recoveryQuery.data ?? []).length === 0 ? (
            <div className="rounded-[22px] skeuo-well px-6 py-10 text-center text-xs text-[var(--fb-ink-secondary)]">
              Tanlangan holatda parol tiklash arizalari yo‘q.
            </div>
          ) : (
            <ul className="flex flex-col gap-3">
              {(recoveryQuery.data ?? []).map((item) => (
                <li key={item.id} className="rounded-[22px] skeuo-well p-4 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="fb-avatar h-9 w-9 shrink-0" aria-hidden="true">
                      <KeyRound className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[var(--fb-ink)]">
                        {item.display_name || "Foydalanuvchi"}
                      </p>
                      <p className="text-xs text-[var(--fb-ink-muted)]">
                        {enumLabel(item.status)} · Yuborilgan: {formatUzDateTime(item.created_at)}
                      </p>
                      {(item.masked_contacts ?? []).length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1.5">
                          {(item.masked_contacts ?? []).map((c, idx) => (
                            <span key={`${c.channel}-${idx}`} className="fb-capsule px-2.5 py-0.5 text-[11px]">
                              {c.channel}: {c.masked}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  {item.status === "PENDING_REVIEW" && (
                    <button
                      type="button"
                      onClick={() => openModal({ kind: "RECOVERY", item })}
                      className="skeuo-btn-obsidian rounded-full px-4 py-1.5 text-xs font-semibold"
                    >
                      Ko‘rib chiqish
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* 3. MODERATION APPEALS */}
      {activeSection === "APPEALS" && (
        <div className="flex flex-col gap-4">
          <p className="text-xs text-[var(--fb-ink-secondary)]">
            Rad etilgan e’lonlar bo‘yicha shikoyatlar. Asl qarorni chiqargan moderatordan mustaqil boshqa moderator ko‘radi.
          </p>
          {appealsQuery.error && (
            <p role="alert" className="rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-4 py-3 text-xs text-rose-700 dark:text-rose-300">
              {appealsQuery.error.message}
            </p>
          )}
          {appealsQuery.isLoading && !appealsQuery.data ? (
            <p className="flex items-center justify-center gap-2 py-10 text-xs text-[var(--fb-ink-muted)]">
              <Loader2 className="h-4 w-4 animate-spin" /> Yuklanmoqda…
            </p>
          ) : (appealsQuery.data ?? []).length === 0 ? (
            <div className="rounded-[22px] skeuo-well px-6 py-10 text-center text-xs text-[var(--fb-ink-secondary)]">
              Ko‘rib chiqiladigan apellyatsiya yo‘q.
            </div>
          ) : (
            <ul className="flex flex-col gap-3">
              {(appealsQuery.data ?? []).map((item, idx) => (
                <li key={item.case_id} className="rounded-[22px] skeuo-well p-4 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <span className="fb-avatar h-9 w-9 shrink-0" aria-hidden="true">
                      <Scale className="h-4 w-4" />
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-[var(--fb-ink)]">
                        E’lon apellyatsiyasi №{idx + 1}
                      </p>
                      <p className="text-xs text-[var(--fb-ink-muted)]">
                        {enumLabel(item.status)} · Muddat: {formatUzDateTime(item.due_at)}
                      </p>
                    </div>
                  </div>
                  {item.status === "OPEN" ? (
                    <button
                      type="button"
                      disabled={claimingId === item.case_id}
                      onClick={() => void handleClaimAppeal(item.case_id)}
                      className="skeuo-btn-secondary rounded-full px-4 py-1.5 text-xs font-semibold disabled:opacity-50"
                    >
                      {claimingId === item.case_id ? "Biriktirilmoqda…" : "O‘zimga biriktirish"}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => openModal({ kind: "APPEAL", item })}
                      className="skeuo-btn-obsidian rounded-full px-4 py-1.5 text-xs font-semibold"
                    >
                      Qaror chiqarish
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* 4. OWNER CONTINUITY */}
      {activeSection === "CONTINUITY" && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-[var(--fb-ink-secondary)]">
              Korxona asosiy egasi aloqasini yo‘qotganda vakolatni tiklash: 1-bosqich Moderator, 2-bosqich Komplayens.
            </p>
            <div className="fb-seg" role="group" aria-label="Vorislik bosqichi">
              {hasModerator && (
                <button
                  type="button"
                  aria-pressed={activeStage === "MODERATOR"}
                  onClick={() => setRequestedStage("MODERATOR")}
                >
                  1-bosqich (Moderator)
                </button>
              )}
              {hasCompliance && (
                <button
                  type="button"
                  aria-pressed={activeStage === "COMPLIANCE"}
                  onClick={() => setRequestedStage("COMPLIANCE")}
                >
                  2-bosqich (Komplayens)
                </button>
              )}
            </div>
          </div>

          {(continuityOpenQuery.error || continuityMineQuery.error) && (
            <p role="alert" className="rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-4 py-3 text-xs text-rose-700 dark:text-rose-300">
              {continuityOpenQuery.error?.message || continuityMineQuery.error?.message}
            </p>
          )}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* UNASSIGNED QUEUE */}
            <div className="rounded-[22px] skeuo-well p-4 flex flex-col gap-3">
              <h3 className="text-sm font-semibold text-[var(--fb-ink)]">
                Olinmagan navbat ({(continuityOpenQuery.data ?? []).length})
              </h3>
              {continuityOpenQuery.isLoading && !continuityOpenQuery.data ? (
                <p className="py-6 text-center text-xs text-[var(--fb-ink-muted)]">Yuklanmoqda…</p>
              ) : (continuityOpenQuery.data ?? []).length === 0 ? (
                <p className="py-6 text-center text-xs text-[var(--fb-ink-muted)]">Navbat bo‘sh.</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {(continuityOpenQuery.data ?? []).map((item, idx) => (
                    <li key={item.id} className="fb-file-row flex items-center justify-between gap-2 text-xs">
                      <div className="min-w-0">
                        <p className="font-semibold text-[var(--fb-ink)] flex items-center gap-1.5">
                          <Building2 className="h-3.5 w-3.5 shrink-0" />
                          <span>Vorislik arizasi №{idx + 1}</span>
                        </p>
                        <p className="text-[11px] text-[var(--fb-ink-muted)]">
                          {enumLabel(item.status)} · Muddat: {formatUzDateTime(item.due_at)}
                        </p>
                      </div>
                      <button
                        type="button"
                        disabled={claimingId === item.id}
                        onClick={() => void handleClaimContinuity(item.id)}
                        className="skeuo-btn-secondary rounded-full px-3 py-1 text-[11px] font-semibold disabled:opacity-50"
                      >
                        {claimingId === item.id ? "Olinmoqda…" : "Olish"}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* ASSIGNED TO ME */}
            <div className="rounded-[22px] skeuo-well p-4 flex flex-col gap-3">
              <h3 className="text-sm font-semibold text-[var(--fb-ink)]">
                Menga biriktirilgan ({(continuityMineQuery.data ?? []).length})
              </h3>
              {continuityMineQuery.isLoading && !continuityMineQuery.data ? (
                <p className="py-6 text-center text-xs text-[var(--fb-ink-muted)]">Yuklanmoqda…</p>
              ) : (continuityMineQuery.data ?? []).length === 0 ? (
                <p className="py-6 text-center text-xs text-[var(--fb-ink-muted)]">
                  Sizga biriktirilgan vorislik ishi yo‘q.
                </p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {(continuityMineQuery.data ?? []).map((item, idx) => (
                    <li key={item.id} className="fb-file-row flex items-center justify-between gap-2 text-xs">
                      <div className="min-w-0">
                        <p className="font-semibold text-[var(--fb-ink)]">Biriktirilgan ish №{idx + 1}</p>
                        <p className="text-[11px] text-[var(--fb-ink-muted)]">
                          {enumLabel(item.status)} · Muddat: {formatUzDateTime(item.due_at)}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => openModal({ kind: "CONTINUITY", stage: activeStage, item })}
                        className="skeuo-btn-obsidian rounded-full px-3 py-1 text-[11px] font-semibold"
                      >
                        Qaror
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 5. PILOT READINESS & RETENTION */}
      {activeSection === "OPERATIONS" && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-[22px] skeuo-well p-4 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-[var(--fb-accent)]" />
              <h3 className="text-sm font-semibold text-[var(--fb-ink)]">Pilot tayyorlik holati</h3>
            </div>
            {pilotQuery.error && (
              <p role="alert" className="text-xs text-rose-700 dark:text-rose-300">
                {pilotQuery.error.message}
              </p>
            )}
            {pilotQuery.isLoading && !pilotQuery.data ? (
              <p className="py-6 text-center text-xs text-[var(--fb-ink-muted)]">Yuklanmoqda…</p>
            ) : pilotQuery.data ? (
              <dl className="grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-xl skeuo-well-sm p-3">
                  <dt className="text-[var(--fb-ink-muted)]">Umumiy maqom</dt>
                  <dd className="mt-1 font-semibold text-[var(--fb-ink)]">
                    {pilotQuery.data.pilot_ready ? "Pilotga tayyor" : "Tayyorlik bosqichida"}
                  </dd>
                </div>
                <div className="rounded-xl skeuo-well-sm p-3">
                  <dt className="text-[var(--fb-ink-muted)]">Qabul holati</dt>
                  <dd className="mt-1 font-semibold text-[var(--fb-ink)]">
                    {enumLabel(pilotQuery.data.acceptance_status)}
                  </dd>
                </div>
                <div className="rounded-xl skeuo-well-sm p-3">
                  <dt className="text-[var(--fb-ink-muted)]">Ma’lumotlar bazasi</dt>
                  <dd className="mt-1 font-semibold text-[var(--fb-ink)]">
                    {pilotQuery.data.schema_migrated ? "Migratsiya tayyor" : "Tekshirilmoqda"}
                  </dd>
                </div>
                <div className="rounded-xl skeuo-well-sm p-3">
                  <dt className="text-[var(--fb-ink-muted)]">R2 frilans flagi</dt>
                  <dd className="mt-1 font-semibold text-[var(--fb-ink)]">
                    {pilotQuery.data.r2_freelance_enabled ? "Yoqilgan" : "O‘chirilgan (R1 qoidasi)"}
                  </dd>
                </div>
                <div className="col-span-2 rounded-xl skeuo-well-sm p-3 flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[var(--fb-ink-muted)]">Tiklash maqsadlari (RPO / RTO)</span>
                  <span className="font-semibold text-[var(--fb-ink)]">
                    {pilotQuery.data.disaster_recovery_targets?.rpo_hours ?? 24} soat /{" "}
                    {pilotQuery.data.disaster_recovery_targets?.rto_hours ?? 4} soat ·{" "}
                    {pilotQuery.data.disaster_recovery_targets?.restore_drill_verified
                      ? "Mashq tasdiqlangan"
                      : "Mashq kutilmoqda"}
                  </span>
                </div>
              </dl>
            ) : null}
          </div>

          <div className="rounded-[22px] skeuo-well p-4 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-[var(--fb-ink)]" />
              <h3 className="text-sm font-semibold text-[var(--fb-ink)]">
                Ma’lumotlarni saqlash muddati tekshiruvi
              </h3>
            </div>
            {!hasCompliance ? (
              <div className="rounded-2xl skeuo-well-sm p-4 text-xs text-[var(--fb-ink-secondary)]">
                <p className="font-semibold text-[var(--fb-ink)] flex items-center gap-1.5 mb-1">
                  <ShieldCheck className="h-4 w-4 text-[var(--fb-accent)]" />
                  Muvofiqlik (Komplayens) vakolati talab etiladi
                </p>
                Xavfsiz dry-run baholashni faqat Muvofiqlik (COMPLIANCE) roliga ega va 2FA bilan kirgan xodim ishga tushira oladi.
              </div>
            ) : (
              <form onSubmit={handleRetentionRun} className="flex flex-col gap-3">
                <label className="flex flex-col gap-1 text-xs font-medium text-[var(--fb-ink-secondary)]">
                  Ma’lumot toifasi
                  <select
                    value={retentionCategory}
                    onChange={(e) => setRetentionCategory(e.target.value)}
                    className="skeuo-input rounded-xl px-3 py-2 text-xs"
                  >
                    {RETENTION_CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>
                        {enumLabel(cat)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="flex flex-col gap-1 text-xs font-medium text-[var(--fb-ink-secondary)]">
                  Yozuv yoshi (kun)
                  <input
                    type="number"
                    min={0}
                    max={365000}
                    value={retentionAgeDays}
                    onChange={(e) => setRetentionAgeDays(Number(e.target.value))}
                    className="skeuo-input rounded-xl px-3 py-2 text-xs"
                  />
                </label>

                <button
                  type="submit"
                  disabled={retentionBusy}
                  className="skeuo-btn-obsidian rounded-full px-4 py-2 text-xs font-semibold justify-center disabled:opacity-50"
                >
                  {retentionBusy ? "Baholanmoqda…" : "Xavfsiz bahoni yozish (Dry-run)"}
                </button>

                {retentionResult && (
                  <div className="rounded-2xl skeuo-well-sm p-3 text-xs flex flex-col gap-1">
                    <span className="font-semibold text-[var(--fb-ink)]">
                      Natija: {enumLabel(retentionResult.evaluation?.outcome || retentionResult.status)}
                    </span>
                    <span className="text-[var(--fb-ink-muted)]">
                      {enumLabel(retentionResult.mode)} · O‘chirilgan yozuvlar: {retentionResult.records_actioned}
                    </span>
                  </div>
                )}
              </form>
            )}
          </div>
        </div>
      )}

      {/* UNIFIED PORTAL DECISION MODAL */}
      {mounted &&
        modal &&
        createPortal(
          <div
            className="fixed inset-0 z-[90] flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-4"
            onMouseDown={(e) => e.target === e.currentTarget && setModal(null)}
          >
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="gov-modal-title"
              className="skeuo-card w-full max-w-md rounded-t-[28px] sm:rounded-[28px] p-6 flex flex-col gap-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 id="gov-modal-title" className="text-base font-semibold text-[var(--fb-ink)]">
                    {modal.kind === "PRIVACY"
                      ? "Maxfiylik so‘rovini hal qilish"
                      : modal.kind === "RECOVERY"
                      ? "Parol tiklash so‘rovini tasdiqlash"
                      : modal.kind === "APPEAL"
                      ? "Apellyatsiya bo‘yicha qaror"
                      : "Korxona egasi vorisligi qarori"}
                  </h2>
                  <p className="mt-0.5 text-xs text-[var(--fb-ink-muted)]">
                    {modal.kind === "PRIVACY"
                      ? `${modal.item.display_name || "Foydalanuvchi"} · ${enumLabel(modal.item.kind)}`
                      : modal.kind === "RECOVERY"
                      ? modal.item.display_name || "Foydalanuvchi"
                      : modal.kind === "APPEAL"
                      ? "E’lon moderatsiyasi apellyatsiyasi"
                      : `${modal.stage === "MODERATOR" ? "1-bosqich (Moderator)" : "2-bosqich (Komplayens)"}`}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setModal(null)}
                  className="fb-icon-btn fb-icon-btn-light h-8 w-8"
                  aria-label="Oynani yopish"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {modalError && (
                <p
                  role="alert"
                  className="rounded-2xl bg-[color-mix(in_srgb,#f43f5e_14%,transparent)] px-3.5 py-2.5 text-xs text-rose-700 dark:text-rose-300"
                >
                  {modalError}
                </p>
              )}

              <form onSubmit={handleModalSubmit} className="flex flex-col gap-3">
                <label className="flex flex-col gap-1 text-xs font-medium text-[var(--fb-ink-secondary)]">
                  Qaror
                  <select
                    value={decision}
                    onChange={(e) => setDecision(e.target.value)}
                    className="skeuo-input rounded-xl px-3 py-2 text-xs"
                  >
                    {decisionOptionsFor(modal).map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="flex flex-col gap-1 text-xs font-medium text-[var(--fb-ink-secondary)]">
                  Qaror asosi (kamida {modal.kind === "PRIVACY" ? 5 : 15} belgi)
                  <textarea
                    rows={3}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Tekshiruv natijasi va dalillarni qisqacha yozing…"
                    className="skeuo-input resize-none rounded-xl px-3 py-2 text-xs"
                  />
                </label>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setModal(null)}
                    className="skeuo-btn-secondary rounded-full px-4 py-2 text-xs"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="submit"
                    disabled={modalBusy || reason.trim().length < (modal.kind === "PRIVACY" ? 5 : 15)}
                    className="skeuo-btn-obsidian rounded-full px-4 py-2 text-xs font-semibold disabled:opacity-50"
                  >
                    {modalBusy ? "Saqlanmoqda…" : "Qarorni yuborish"}
                  </button>
                </div>
              </form>
            </div>
          </div>,
          document.body
        )}
    </section>
  );
}
