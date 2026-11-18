"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ClipboardList,
  Loader2,
  PlayCircle,
  Plus,
  Trash2,
  UserCheck,
  UserPlus,
  X,
  XCircle,
} from "lucide-react";
import type { OrganizationPlacementItem } from "@/lib/api";
import { enumLabel } from "@/lib/labels";
import {
  fetchHostPlacementPlan,
  fetchOrgMentors,
  fetchPlacementMentorAssignments,
  nominatePlacementMentor,
  publishHostPlacementPlan,
  revokePlacementMentor,
  submitHostDecision,
  type OrgMentorOption,
  type PlacementMentorAssignmentItem,
  type PlanTaskDraft,
} from "@/lib/placementLifecycle";
import PlacementCompletionControls from "@/components/placements/PlacementCompletionControls";

type LifecycleTab = "PLAN" | "MENTORS_STATUS" | "COMPLETION";

const DEFAULT_TASK = (index: number): PlanTaskDraft => ({
  code: `TASK-${index + 1}`,
  title: "",
  expected_result: "",
  required: true,
  target_minutes: 60,
});

export default function PlacementLifecycleModal({
  isOpen,
  placement,
  orgId,
  onClose,
  onUpdated,
}: {
  isOpen: boolean;
  placement: OrganizationPlacementItem | null;
  orgId: string;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [tab, setTab] = useState<LifecycleTab>("PLAN");
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [status, setStatus] = useState("");
  const [termsId, setTermsId] = useState("");
  const [version, setVersion] = useState(1);

  const [title, setTitle] = useState("");
  const [objectives, setObjectives] = useState("");
  const [dailyLimit, setDailyLimit] = useState(480);
  const [weeklyLimit, setWeeklyLimit] = useState(2400);
  const [requiredMinutes, setRequiredMinutes] = useState(4800);
  const [tasks, setTasks] = useState<PlanTaskDraft[]>([DEFAULT_TASK(0)]);

  const [mentors, setMentors] = useState<OrgMentorOption[]>([]);
  const [assignments, setAssignments] = useState<PlacementMentorAssignmentItem[]>([]);
  const [selectedMentorId, setSelectedMentorId] = useState("");
  const [confirmCancel, setConfirmCancel] = useState(false);

  const targetKey = isOpen && placement ? `${placement.id}:${refreshTick}` : null;
  const loading = Boolean(targetKey && (!loadedKey || !loadedKey.startsWith(`${placement?.id}:`)));

  const triggerReload = useCallback(() => {
    setRefreshTick((t) => t + 1);
  }, []);

  useEffect(() => {
    if (!targetKey || !placement) return;
    let active = true;
    Promise.allSettled([
      fetchHostPlacementPlan(placement.id),
      orgId ? fetchOrgMentors(orgId) : Promise.resolve([]),
      fetchPlacementMentorAssignments(placement.id),
    ])
      .then(([planRes, mentorsRes, asgRes]) => {
        if (!active) return;
        setConfirmCancel(false);
        setError(null);
        if (planRes.status === "fulfilled") {
          const p = planRes.value;
          setStatus(p.status || placement.status);
          setTermsId(p.terms_id || placement.current_terms_id);
          setVersion(p.version || placement.version);
          setTitle(p.title || "");
          setObjectives(p.objectives || "");
          setDailyLimit(p.daily_limit_minutes || 480);
          setWeeklyLimit(p.weekly_limit_minutes || 2400);
          setRequiredMinutes(p.required_minutes || 4800);
          setTasks(p.tasks && p.tasks.length > 0 ? p.tasks : [DEFAULT_TASK(0)]);
        } else {
          setStatus(placement.status);
          setTermsId(placement.current_terms_id);
          setVersion(placement.version);
        }

        if (mentorsRes.status === "fulfilled") {
          setMentors(mentorsRes.value);
          if (mentorsRes.value.length > 0) {
            setSelectedMentorId((cur) => cur || mentorsRes.value[0].user_id);
          }
        }
        if (asgRes.status === "fulfilled") {
          setAssignments(asgRes.value);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Amaliyot ma’lumotlari yuklanmadi.");
        }
      })
      .finally(() => {
        if (active) setLoadedKey(targetKey);
      });
    return () => {
      active = false;
    };
  }, [targetKey, placement, orgId]);

  if (!isOpen || !placement) return null;

  const canEditPlan = status === "PLANNED" || status === "PENDING_START_CONFIRMATION";
  const canHostDecision =
    status === "PLANNED" || status === "PENDING_START_CONFIRMATION" || status === "ACTIVE";

  const handlePublishPlan = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanedTasks = tasks
      .filter((t) => t.title.trim().length > 0)
      .map((t, idx) => ({
        code: t.code.trim() || `TASK-${idx + 1}`,
        title: t.title.trim(),
        expected_result: t.expected_result.trim() || "Natija topshirig‘i",
        required: t.required,
        target_minutes: t.target_minutes ? Number(t.target_minutes) : null,
      }));
    if (title.trim().length < 2 || cleanedTasks.length === 0) {
      setError("Reja sarlavhasi va kamida bitta vazifa kiritilishi shart.");
      return;
    }
    setBusy("PLAN");
    setError(null);
    setNotice(null);
    try {
      await publishHostPlacementPlan(placement.id, {
        terms_id: termsId,
        version,
        title: title.trim(),
        objectives: objectives.trim(),
        daily_limit_minutes: Number(dailyLimit),
        weekly_limit_minutes: Number(weeklyLimit),
        required_minutes: Number(requiredMinutes),
        tasks: cleanedTasks,
      });
      setNotice("Amaliyot rejasi yangilandi (API-050).");
      triggerReload();
      onUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Rejani saqlashda xatolik.");
    } finally {
      setBusy(null);
    }
  };

  const handleNominateMentor = async () => {
    if (!selectedMentorId) return;
    setBusy("NOMINATE");
    setError(null);
    setNotice(null);
    try {
      await nominatePlacementMentor(placement.id, selectedMentorId);
      setNotice("Mentor biriktirildi (API-087). Mentor qabul qilishi kutilmoqda.");
      triggerReload();
      onUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Mentorni biriktirib bo‘lmadi.");
    } finally {
      setBusy(null);
    }
  };

  const handleRevokeMentor = async (assignmentId: string) => {
    setBusy(`REVOKE_${assignmentId}`);
    setError(null);
    setNotice(null);
    try {
      await revokePlacementMentor(placement.id, assignmentId, termsId, version);
      setNotice("Mentor biriktiruvi bekor qilindi.");
      triggerReload();
      onUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Mentorni olib tashlab bo‘lmadi.");
    } finally {
      setBusy(null);
    }
  };

  const handleHostDecision = async (action: "ACTIVATE" | "CANCEL") => {
    setBusy(action);
    setError(null);
    setNotice(null);
    try {
      await submitHostDecision(placement.id, termsId, version, action);
      setConfirmCancel(false);
      setNotice(action === "ACTIVATE" ? "Amaliyot faollashtirildi (ACTIVE)." : "Amaliyot bekor qilindi.");
      triggerReload();
      onUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Korxona qarori bajarilmadi.");
    } finally {
      setBusy(null);
    }
  };

  const tabs: Array<{ id: LifecycleTab; label: string }> = [
    { id: "PLAN", label: "Reja (API-050)" },
    { id: "MENTORS_STATUS", label: "Mentor & Holat (API-087/088)" },
    { id: "COMPLETION", label: "Yakunlash & Eksport" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
      <div className="w-full max-w-3xl max-h-[90vh] flex flex-col rounded-2xl border border-white/10 bg-[#0d1117] text-white shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-white/10 px-5 py-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-bold text-white">Amaliyot hayotiy sikli</h2>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/15 text-blue-300 border border-blue-500/25">
                {enumLabel(status || placement.status)}
              </span>
              <span className="text-[11px] font-mono text-zinc-400">v{version}</span>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5 font-mono">
              {placement.start_date} — {placement.end_date} · {placement.academic_track ? "Dual ta’lim" : "Mustaqil"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Yopish"
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/10 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex flex-wrap gap-1.5 border-b border-white/10 px-5 py-2.5 bg-white/[0.02]">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                tab === item.id
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/35"
                  : "text-zinc-400 hover:text-white hover:bg-white/[0.05] border border-transparent"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/25 text-xs text-rose-300 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
          {notice && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-xs text-emerald-300 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{notice}</span>
            </div>
          )}

          {loading ? (
            <div className="py-10 flex items-center justify-center gap-2 text-xs text-zinc-400">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span>Ma’lumotlar yuklanmoqda...</span>
            </div>
          ) : (
            <>
              {tab === "PLAN" && (
                <form onSubmit={handlePublishPlan} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <label className="flex flex-col gap-1">
                      <span className="text-[11px] font-semibold text-zinc-300">Reja sarlavhasi</span>
                      <input
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        disabled={!canEditPlan}
                        placeholder="Backend amaliyot dasturi"
                        className="px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10 text-xs text-white disabled:opacity-60"
                      />
                    </label>
                    <label className="flex flex-col gap-1">
                      <span className="text-[11px] font-semibold text-zinc-300">Maqsadlar</span>
                      <input
                        type="text"
                        value={objectives}
                        onChange={(e) => setObjectives(e.target.value)}
                        disabled={!canEditPlan}
                        placeholder="API va ma’lumotlar bazasi amaliyoti"
                        className="px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10 text-xs text-white disabled:opacity-60"
                      />
                    </label>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <label className="flex flex-col gap-1">
                      <span className="text-[11px] text-zinc-400">Kunlik me’yor (daq.)</span>
                      <input
                        type="number"
                        min={60}
                        max={480}
                        value={dailyLimit}
                        onChange={(e) => setDailyLimit(Number(e.target.value) || 0)}
                        disabled={!canEditPlan}
                        className="px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10 text-xs text-white disabled:opacity-60"
                      />
                    </label>
                    <label className="flex flex-col gap-1">
                      <span className="text-[11px] text-zinc-400">Haftalik me’yor (daq.)</span>
                      <input
                        type="number"
                        min={60}
                        max={2400}
                        value={weeklyLimit}
                        onChange={(e) => setWeeklyLimit(Number(e.target.value) || 0)}
                        disabled={!canEditPlan}
                        className="px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10 text-xs text-white disabled:opacity-60"
                      />
                    </label>
                    <label className="flex flex-col gap-1">
                      <span className="text-[11px] text-zinc-400">Jami talab (daq.)</span>
                      <input
                        type="number"
                        min={60}
                        value={requiredMinutes}
                        onChange={(e) => setRequiredMinutes(Number(e.target.value) || 0)}
                        disabled={!canEditPlan}
                        className="px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10 text-xs text-white disabled:opacity-60"
                      />
                    </label>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                        <ClipboardList className="w-3.5 h-3.5 text-emerald-400" />
                        O‘quv reja vazifalari ({tasks.length})
                      </span>
                      {canEditPlan && (
                        <button
                          type="button"
                          onClick={() => setTasks((prev) => [...prev, DEFAULT_TASK(prev.length)])}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-xs text-zinc-200"
                        >
                          <Plus className="w-3.5 h-3.5" /> Vazifa qo‘shish
                        </button>
                      )}
                    </div>
                    {tasks.map((task, idx) => (
                      <div key={`${task.code}-${idx}`} className="p-3 rounded-xl bg-white/[0.03] border border-white/10 space-y-2">
                        <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                          <input
                            type="text"
                            value={task.code}
                            disabled={!canEditPlan}
                            onChange={(e) =>
                              setTasks((prev) => prev.map((it, i) => (i === idx ? { ...it, code: e.target.value } : it)))
                            }
                            placeholder="Kod"
                            className="px-2.5 py-1.5 rounded-lg bg-black/30 border border-white/10 text-xs text-white disabled:opacity-60"
                          />
                          <input
                            type="text"
                            value={task.title}
                            disabled={!canEditPlan}
                            onChange={(e) =>
                              setTasks((prev) => prev.map((it, i) => (i === idx ? { ...it, title: e.target.value } : it)))
                            }
                            placeholder="Vazifa nomi"
                            className="sm:col-span-2 px-2.5 py-1.5 rounded-lg bg-black/30 border border-white/10 text-xs text-white disabled:opacity-60"
                          />
                          <input
                            type="number"
                            min={0}
                            value={task.target_minutes ?? 60}
                            disabled={!canEditPlan}
                            onChange={(e) =>
                              setTasks((prev) =>
                                prev.map((it, i) => (i === idx ? { ...it, target_minutes: Number(e.target.value) || 0 } : it))
                              )
                            }
                            placeholder="Daqiqa"
                            className="px-2.5 py-1.5 rounded-lg bg-black/30 border border-white/10 text-xs text-white disabled:opacity-60"
                          />
                        </div>
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <input
                            type="text"
                            value={task.expected_result}
                            disabled={!canEditPlan}
                            onChange={(e) =>
                              setTasks((prev) =>
                                prev.map((it, i) => (i === idx ? { ...it, expected_result: e.target.value } : it))
                              )
                            }
                            placeholder="Kutilayotgan natija"
                            className="flex-1 min-w-[200px] px-2.5 py-1.5 rounded-lg bg-black/30 border border-white/10 text-xs text-white disabled:opacity-60"
                          />
                          {canEditPlan && tasks.length > 1 && (
                            <button
                              type="button"
                              onClick={() => setTasks((prev) => prev.filter((_, i) => i !== idx))}
                              className="p-1.5 rounded-lg text-rose-400 hover:bg-rose-500/10"
                              aria-label="Vazifani o‘chirish"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {canEditPlan ? (
                    <div className="flex justify-end">
                      <button
                        type="submit"
                        disabled={busy !== null}
                        className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white inline-flex items-center gap-1.5 disabled:opacity-50"
                      >
                        {busy === "PLAN" && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                        <span>Rejani nashr qilish</span>
                      </button>
                    </div>
                  ) : (
                    <p className="text-[11px] text-zinc-400">
                      Faol yoki yakunlangan amaliyot rejasini o‘zgartirish uchun yangi versiya bosqichi kerak emas (reja qulflangan).
                    </p>
                  )}
                </form>
              )}

              {tab === "MENTORS_STATUS" && (
                <div className="space-y-5">
                  <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                        <UserPlus className="w-3.5 h-3.5 text-emerald-400" />
                        Mentorni biriktirish (`API-087`)
                      </h3>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <select
                        value={selectedMentorId}
                        onChange={(e) => setSelectedMentorId(e.target.value)}
                        className="flex-1 min-w-[220px] px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-xs text-white"
                      >
                        {mentors.length === 0 ? (
                          <option value="">Tashkilotda faol mentor topilmadi</option>
                        ) : (
                          mentors.map((m) => (
                            <option key={m.user_id} value={m.user_id}>
                              {m.display_name}
                            </option>
                          ))
                        )}
                      </select>
                      <button
                        type="button"
                        disabled={!selectedMentorId || busy !== null}
                        onClick={() => void handleNominateMentor()}
                        className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white inline-flex items-center gap-1.5 disabled:opacity-50"
                      >
                        {busy === "NOMINATE" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UserCheck className="w-3.5 h-3.5" />}
                        <span>Mentorni biriktirish</span>
                      </button>
                    </div>

                    <div className="space-y-2 pt-2">
                      {assignments.length === 0 ? (
                        <p className="text-xs text-zinc-500">Hozircha bu amaliyotga mentor biriktirilmagan.</p>
                      ) : (
                        assignments.map((asg) => (
                          <div
                            key={asg.id}
                            className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-lg bg-black/25 border border-white/10 text-xs"
                          >
                            <div>
                              <div className="font-semibold text-white">{asg.display_name}</div>
                              <div className="text-[11px] text-zinc-400">
                                {asg.accepted_at ? "Mentor tasdiqlagan" : "Mentor tasdiqlashi kutilmoqda"}
                              </div>
                            </div>
                            <button
                              type="button"
                              disabled={busy !== null}
                              onClick={() => void handleRevokeMentor(asg.id)}
                              className="px-2.5 py-1 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 text-[11px] font-semibold disabled:opacity-50"
                            >
                              Olib tashlash
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {canHostDecision && (
                    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10 space-y-3">
                      <h3 className="text-xs font-bold text-white">Korxona holat qarori (`API-088`)</h3>
                      <div className="flex flex-wrap items-center gap-2">
                        {(status === "PLANNED" || status === "PENDING_START_CONFIRMATION") && (
                          <button
                            type="button"
                            disabled={busy !== null}
                            onClick={() => void handleHostDecision("ACTIVATE")}
                            className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white inline-flex items-center gap-1.5 disabled:opacity-50"
                          >
                            {busy === "ACTIVATE" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PlayCircle className="w-3.5 h-3.5" />}
                            <span>Amaliyotni faollashtirish</span>
                          </button>
                        )}
                        {!confirmCancel ? (
                          <button
                            type="button"
                            disabled={busy !== null}
                            onClick={() => setConfirmCancel(true)}
                            className="px-3.5 py-2 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-xs font-semibold text-rose-300 inline-flex items-center gap-1.5"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Amaliyotni bekor qilish</span>
                          </button>
                        ) : (
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              disabled={busy !== null}
                              onClick={() => void handleHostDecision("CANCEL")}
                              className="px-3.5 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white inline-flex items-center gap-1.5"
                            >
                              {busy === "CANCEL" && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                              <span>Ha, bekor qilinsin</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => setConfirmCancel(false)}
                              className="px-3 py-2 rounded-lg bg-white/10 text-xs text-zinc-300"
                            >
                              Yo‘q
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {tab === "COMPLETION" && (
                <PlacementCompletionControls
                  placementId={placement.id}
                  status={status || placement.status}
                  termsId={termsId || placement.current_terms_id}
                  version={version || placement.version}
                  onUpdated={() => {
                    triggerReload();
                    onUpdated();
                  }}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
