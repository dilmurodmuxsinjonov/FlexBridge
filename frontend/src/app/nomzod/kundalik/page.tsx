"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  Calendar,
  Clock,
  Briefcase,
  Building2,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  Save,
  Send,
  RefreshCw,
  LogOut,
  ChevronRight,
  ShieldCheck,
  FileCheck,
  Award,
  Layers,
} from "lucide-react";
import {
  AuthUser,
  fetchAuthMe,
  logoutUser,
  CandidatePlacementItem,
  DailyLogItem,
  fetchCandidatePlacements,
  fetchPlacementLogs,
  saveDraftDailyLog,
  submitDailyLog,
} from "@/lib/api";
import AuthModal from "@/components/AuthModal";

export default function CandidateKundalikPage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  const [placements, setPlacements] = useState<CandidatePlacementItem[]>([]);
  const [selectedPlacement, setSelectedPlacement] = useState<CandidatePlacementItem | null>(null);
  const [logs, setLogs] = useState<DailyLogItem[]>([]);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);

  // Form state
  const todayStr = useMemo(() => new Date().toISOString().split("T")[0], []);
  const [selectedDate, setSelectedDate] = useState<string>(todayStr);
  const [dayType, setDayType] = useState<"WORKED" | "ABSENT">("WORKED");
  const [summaryText, setSummaryText] = useState("");
  const [tasks, setTasks] = useState<Array<{ title: string; minutes: number }>>([
    { title: "Kafedra va amaliyot rejasi bo'yicha vazifalar", minutes: 240 },
  ]);

  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Load current user
  const loadUser = useCallback(async () => {
    try {
      setAuthLoading(true);
      const auth = await fetchAuthMe();
      setUser(auth);
    } catch {
      setUser(null);
    } finally {
      setAuthLoading(false);
    }
  }, []);

  // Load placements
  const loadPlacements = useCallback(async () => {
    try {
      const res = await fetchCandidatePlacements();
      setPlacements(res.items || []);
      if (res.items && res.items.length > 0) {
        setSelectedPlacement((prev) => prev || res.items[0]);
      }
    } catch (err: unknown) {
      console.error("Failed to load placements:", err);
    }
  }, []);

  // Load logs for selected placement
  const loadLogs = useCallback(async (placementId: string) => {
    try {
      setIsLoadingLogs(true);
      const res = await fetchPlacementLogs(placementId);
      setLogs(res.items || []);
    } catch (err: unknown) {
      console.error("Failed to load logs:", err);
    } finally {
      setIsLoadingLogs(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    if (user) {
      loadPlacements();
    }
  }, [user, loadPlacements]);

  useEffect(() => {
    if (selectedPlacement) {
      loadLogs(selectedPlacement.id);
    }
  }, [selectedPlacement, loadLogs]);

  // Synchronize form when selectedDate or logs change
  useEffect(() => {
    const existingLog = logs.find((l) => l.local_date === selectedDate);
    if (existingLog) {
      setDayType(existingLog.day_type || "WORKED");
      setSummaryText(existingLog.summary || "");
      if (existingLog.tasks && existingLog.tasks.length > 0) {
        setTasks(existingLog.tasks.map((t) => ({ title: t.title, minutes: t.minutes })));
      } else {
        setTasks([{ title: existingLog.summary || "Amaliyot vazifasi", minutes: existingLog.total_minutes || 240 }]);
      }
    } else {
      setDayType("WORKED");
      setSummaryText("");
      setTasks([{ title: "Kafedra va amaliyot rejasi bo'yicha vazifalar", minutes: 240 }]);
    }
  }, [selectedDate, logs]);

  const activeLogForDate = useMemo(() => {
    return logs.find((l) => l.local_date === selectedDate);
  }, [logs, selectedDate]);

  const totalCalculatedMinutes = useMemo(() => {
    if (dayType === "ABSENT") return 0;
    return tasks.reduce((sum, t) => sum + (Number(t.minutes) || 0), 0);
  }, [dayType, tasks]);

  const totalCompletedHours = useMemo(() => {
    const totalMins = logs
      .filter((l) => l.status === "REVIEWED" || l.status === "SUBMITTED")
      .reduce((sum, l) => sum + (l.total_minutes || 0), 0);
    return (totalMins / 60).toFixed(1);
  }, [logs]);

  const handleAddTask = () => {
    setTasks([...tasks, { title: "", minutes: 120 }]);
  };

  const handleRemoveTask = (index: number) => {
    setTasks(tasks.filter((_, i) => i !== index));
  };

  const handleTaskChange = (index: number, field: "title" | "minutes", value: string | number) => {
    const updated = [...tasks];
    if (field === "minutes") {
      updated[index].minutes = Number(value) || 0;
    } else {
      updated[index].title = String(value);
    }
    setTasks(updated);
  };

  const handleSaveDraft = async () => {
    if (!selectedPlacement) return;
    try {
      setIsSaving(true);
      setNotification(null);

      if (dayType === "WORKED" && totalCalculatedMinutes > 480) {
        setNotification({
          type: "error",
          message: "O'zbekiston Respublikasi Mehnat Kodeksi (118-modda) bo'yicha kunlik amaliyot vaqti 8 soatdan (480 daqiqa) oshishi mumkin emas.",
        });
        setIsSaving(false);
        return;
      }

      await saveDraftDailyLog(selectedPlacement.id, selectedDate, {
        day_type: dayType,
        summary_text: summaryText,
        total_minutes: totalCalculatedMinutes,
        tasks: tasks.map((t) => ({
          title: t.title || "Amaliyot vazifasi",
          minutes: t.minutes,
        })),
      });

      setNotification({
        type: "success",
        message: `${selectedDate} sanasi uchun qoralama kundalik muvaffaqiyatli saqlandi.`,
      });

      await loadLogs(selectedPlacement.id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Qoralamani saqlashda xatolik yuz berdi";
      setNotification({ type: "error", message: msg });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmitForReview = async () => {
    if (!selectedPlacement) return;
    try {
      setIsSubmitting(true);
      setNotification(null);

      // Save draft first if not yet created or modified
      const draftResult = await saveDraftDailyLog(selectedPlacement.id, selectedDate, {
        day_type: dayType,
        summary_text: summaryText,
        total_minutes: totalCalculatedMinutes,
        tasks: tasks.map((t) => ({
          title: t.title || "Amaliyot vazifasi",
          minutes: t.minutes,
        })),
      });

      // Submit
      const logIdToSubmit = draftResult.id || activeLogForDate?.id;
      if (!logIdToSubmit) {
        throw new Error("Kundalik identifikatori aniqlanmadi.");
      }

      await submitDailyLog(logIdToSubmit);

      setNotification({
        type: "success",
        message: `${selectedDate} sanasidagi kundalik o'qituvchi va mentor tekshiruviga muvaffaqiyatli topshirildi.`,
      });

      await loadLogs(selectedPlacement.id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Kundalikni topshirishda xatolik yuz berdi";
      setNotification({ type: "error", message: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "SUBMITTED":
        return {
          label: "Ko'rib chiqilmoqda",
          className: "bg-sky-500/10 text-sky-400 border-sky-500/20",
          icon: Clock,
        };
      case "REVIEWED":
        return {
          label: "Tasdiqlandi",
          className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
          icon: CheckCircle2,
        };
      case "NEEDS_REVISION":
        return {
          label: "Qaytarildi (Tuzatish)",
          className: "bg-amber-500/10 text-amber-400 border-amber-500/20",
          icon: AlertCircle,
        };
      case "DRAFT":
      default:
        return {
          label: "Qoralama",
          className: "bg-zinc-800 text-zinc-400 border-zinc-700",
          icon: FileCheck,
        };
    }
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 flex flex-col font-sans">
      {/* Top Banner / Breadcrumb */}
      <div className="border-b border-white/5 bg-[#121214]/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <Link href="/" className="hover:text-zinc-200 transition-colors">
              Bosh sahifa
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
            <Link href="/nomzod/arizalar" className="hover:text-zinc-200 transition-colors">
              Mening arizalarim
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
            <span className="text-zinc-100 font-medium">Amaliyot Kundaligi</span>
          </div>

          <div className="flex items-center gap-3">
            {authLoading ? (
              <div className="w-20 h-7 bg-zinc-800 animate-pulse rounded" />
            ) : user ? (
              <div className="flex items-center gap-3">
                <span className="text-xs text-zinc-400 font-mono">
                  ID: {user.user_id.slice(0, 8)}...
                </span>
                <button
                  onClick={async () => {
                    await logoutUser();
                    setUser(null);
                  }}
                  className="text-xs text-zinc-500 hover:text-red-400 transition-colors flex items-center gap-1"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  Chiqish
                </button>
              </div>
            ) : (
              <button
                onClick={() => setAuthModalOpen(true)}
                className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors"
              >
                Kirish
              </button>
            )}
          </div>
        </div>
      </div>

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {/* Sub-Navigation between Candidate Pages */}
        <div className="flex items-center gap-2 border-b border-white/[0.06] pb-3 mb-6 text-xs overflow-x-auto">
          <Link
            href="/nomzod"
            className="px-3 py-1.5 rounded-lg border border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors whitespace-nowrap"
          >
            Kasbiy Profil
          </Link>
          <Link
            href="/nomzod/arizalar"
            className="px-3 py-1.5 rounded-lg border border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors whitespace-nowrap"
          >
            Mening Arizalarim
          </Link>
          <Link
            href="/nomzod/shartnomalar"
            className="px-3 py-1.5 rounded-lg border border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors whitespace-nowrap"
          >
            Shartnomalar & Amaliyot
          </Link>
          <span className="px-3 py-1.5 rounded-lg border border-primary/30 bg-primary/10 text-primary font-semibold whitespace-nowrap">
            Amaliyot Kundaligi
          </span>
          <Link
            href="/nomzod/baholar"
            className="px-3 py-1.5 rounded-lg border border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors whitespace-nowrap"
          >
            Baholar & Sharhlar
          </Link>
          <Link
            href="/nomzod/saqlanganlar"
            className="px-3 py-1.5 rounded-lg border border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors whitespace-nowrap"
          >
            Saqlangan E&apos;lonlar
          </Link>
        </div>

        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-white flex items-center gap-3">
                <Calendar className="w-7 h-7 text-blue-500" />
                Elektron Amaliyot Kundaligi
              </h1>
              <p className="text-sm text-zinc-400 mt-1">
                Kunlik bajarilgan vazifalar hisoboti, mentor bahosi va universitet akademik tasdig‘i
              </p>
            </div>

            {selectedPlacement && (
              <div className="flex items-center gap-3 bg-[#121214] border border-white/5 rounded-xl px-4 py-3">
                <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400">
                  <Clock className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs text-zinc-400 uppercase tracking-wider font-mono">Bajarilgan soat</div>
                  <div className="text-lg font-bold text-white tabular-nums">
                    {totalCompletedHours} <span className="text-xs text-zinc-500 font-normal">/ 200 soat</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Notifications */}
        {notification && (
          <div
            className={`mb-6 p-4 rounded-xl border flex items-center gap-3 ${
              notification.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                : "bg-red-500/10 border-red-500/20 text-red-400"
            }`}
          >
            {notification.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 shrink-0" />
            )}
            <p className="text-sm font-medium">{notification.message}</p>
          </div>
        )}

        {/* Placement Selection (if multiple) */}
        {placements.length > 1 && (
          <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
            {placements.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedPlacement(p)}
                className={`px-4 py-2 rounded-xl text-xs font-medium border transition-colors flex items-center gap-2 ${
                  selectedPlacement?.id === p.id
                    ? "bg-blue-600/10 border-blue-500/30 text-blue-400"
                    : "bg-[#121214] border-white/5 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Building2 className="w-3.5 h-3.5" />
                {p.organization_name || "Korxona"} ({p.start_date} - {p.end_date})
              </button>
            ))}
          </div>
        )}

        {/* Active Placement Card */}
        {selectedPlacement ? (
          <div className="mb-8 bg-[#121214] border border-white/5 rounded-2xl p-5 sm:p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 shrink-0">
                  <Briefcase className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-medium text-white">
                    {selectedPlacement.opportunity_title || "Dasturiy injiniring amaliyoti"}
                  </h3>
                  <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs text-zinc-400 mt-1">
                    <span className="flex items-center gap-1.5">
                      <Building2 className="w-3.5 h-3.5 text-zinc-500" />
                      {selectedPlacement.organization_name || "Tashkilot"}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-zinc-500" />
                      {selectedPlacement.start_date} — {selectedPlacement.end_date}
                    </span>
                    {selectedPlacement.academic_track && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] bg-purple-500/10 text-purple-400 border border-purple-500/20 font-medium">
                        Akademik uch tomonlama shartnoma
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Faol amaliyot
                </span>
              </div>
            </div>
          </div>
        ) : !authLoading && user ? (
          <div className="mb-8 p-8 bg-[#121214] border border-white/5 rounded-2xl text-center">
            <Briefcase className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
            <h3 className="text-base font-medium text-zinc-200">Faol amaliyot topilmadi</h3>
            <p className="text-xs text-zinc-400 mt-1 max-w-md mx-auto">
              Sizda hozircha rasmiylashtirilgan amaliyot biriktiruvi mavjud emas. Avval vakansiyalarga ariza topshiring.
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-4 py-2 mt-4 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors"
            >
              Vakansiyalarni ko‘rish
            </Link>
          </div>
        ) : null}

        {/* Main Content Layout: Editor (Left) & Log History (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Daily Log Editor */}
          <div className="lg:col-span-7 space-y-6">
            <div className="bg-[#121214] border border-white/5 rounded-2xl p-5 sm:p-6">
              <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-5">
                <div>
                  <h2 className="text-base font-semibold text-white flex items-center gap-2">
                    <FileCheck className="w-4 h-4 text-blue-400" />
                    Kunlik hisobot kiritish
                  </h2>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Kunlik bajargan amaliy vazifalaringizni batafsil yozib boring
                  </p>
                </div>

                {activeLogForDate && (
                  <div>
                    {(() => {
                      const badge = getStatusBadge(activeLogForDate.status);
                      const Icon = badge.icon;
                      return (
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${badge.className}`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                          {badge.label}
                        </span>
                      );
                    })()}
                  </div>
                )}
              </div>

              {/* Date & Day Type Row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                    Sana (Kun)
                  </label>
                  <input
                    type="date"
                    value={selectedDate}
                    max={todayStr}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-[#09090b] border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                    Kun turi
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setDayType("WORKED")}
                      className={`px-3 py-2.5 rounded-xl text-xs font-medium border transition-colors ${
                        dayType === "WORKED"
                          ? "bg-blue-600/10 border-blue-500 text-blue-400"
                          : "bg-[#09090b] border-white/10 text-zinc-400 hover:text-zinc-200"
                      }`}
                    >
                      Ish kuni
                    </button>
                    <button
                      type="button"
                      onClick={() => setDayType("ABSENT")}
                      className={`px-3 py-2.5 rounded-xl text-xs font-medium border transition-colors ${
                        dayType === "ABSENT"
                          ? "bg-amber-500/10 border-amber-500 text-amber-400"
                          : "bg-[#09090b] border-white/10 text-zinc-400 hover:text-zinc-200"
                      }`}
                    >
                      Dam olish / Sababli
                    </button>
                  </div>
                </div>
              </div>

              {/* Day Summary */}
              <div className="mb-5">
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Kunning umumiy xulosasi / asosiy natijasi
                </label>
                <textarea
                  rows={2}
                  value={summaryText}
                  onChange={(e) => setSummaryText(e.target.value)}
                  placeholder="Masalan: Bugun backend arxitekturasi va REST API integratsiyasi bo'yicha amaliy ishlar olib borildi..."
                  className="w-full px-3.5 py-2.5 bg-[#09090b] border border-white/10 rounded-xl text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-blue-500 transition-colors resize-none"
                />
              </div>

              {/* Tasks Breakdown */}
              {dayType === "WORKED" && (
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-xs font-medium text-zinc-400">
                      Bajarilgan aniq vazifalar va sarflangan vaqt
                    </label>
                    <button
                      type="button"
                      onClick={handleAddTask}
                      className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Vazifa qo‘shish
                    </button>
                  </div>

                  <div className="space-y-3">
                    {tasks.map((task, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 bg-[#09090b] border border-white/5 rounded-xl p-2.5"
                      >
                        <input
                          type="text"
                          value={task.title}
                          onChange={(e) => handleTaskChange(idx, "title", e.target.value)}
                          placeholder="Vazifa tavsifi..."
                          className="flex-1 bg-transparent border-0 text-sm text-white placeholder:text-zinc-600 focus:outline-none"
                        />
                        <div className="flex items-center gap-1 shrink-0">
                          <input
                            type="number"
                            min={15}
                            max={480}
                            step={15}
                            value={task.minutes}
                            onChange={(e) => handleTaskChange(idx, "minutes", e.target.value)}
                            className="w-16 px-2 py-1 bg-zinc-900 border border-white/10 rounded-lg text-xs text-white text-right focus:outline-none focus:border-blue-500 tabular-nums"
                          />
                          <span className="text-xs text-zinc-500">daq</span>
                        </div>
                        {tasks.length > 1 && (
                          <button
                            type="button"
                            onClick={() => handleRemoveTask(idx)}
                            className="p-1 text-zinc-500 hover:text-red-400 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>

                  <div className="mt-3 flex items-center justify-between text-xs text-zinc-400 px-1">
                    <span>Jami sarflangan vaqt:</span>
                    <span
                      className={`font-mono font-medium tabular-nums ${
                        totalCalculatedMinutes > 480 ? "text-red-400 font-bold" : "text-white"
                      }`}
                    >
                      {totalCalculatedMinutes} daqiqa ({(totalCalculatedMinutes / 60).toFixed(1)} soat) / 480 daq me'yor
                    </span>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center justify-end gap-3 pt-4 border-t border-white/5">
                <button
                  type="button"
                  disabled={isSaving || isSubmitting || activeLogForDate?.status === "SUBMITTED" || activeLogForDate?.status === "REVIEWED"}
                  onClick={handleSaveDraft}
                  className="px-4 py-2.5 rounded-xl text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  {isSaving ? "Saqlanmoqda..." : "Qoralamani saqlash"}
                </button>

                <button
                  type="button"
                  disabled={
                    isSaving ||
                    isSubmitting ||
                    activeLogForDate?.status === "SUBMITTED" ||
                    activeLogForDate?.status === "REVIEWED" ||
                    (dayType === "WORKED" && totalCalculatedMinutes <= 0)
                  }
                  onClick={handleSubmitForReview}
                  className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-blue-500/20"
                >
                  <Send className="w-4 h-4" />
                  {isSubmitting ? "Topshirilmoqda..." : "Tekshiruvga topshirish"}
                </button>
              </div>

              {/* Immutable note if submitted */}
              {(activeLogForDate?.status === "SUBMITTED" || activeLogForDate?.status === "REVIEWED") && (
                <div className="mt-4 p-3 bg-blue-500/5 border border-blue-500/20 rounded-xl flex items-center gap-2 text-xs text-blue-300">
                  <ShieldCheck className="w-4 h-4 text-blue-400 shrink-0" />
                  Ushbu kundalik allaqachon tekshiruvga topshirilgan. O'zgarmaslik (immutability) qoidasiga ko'ra tahrirlash cheklangan.
                </div>
              )}
            </div>

            {/* Mentor & Academic Review Details (if available for selected date) */}
            {activeLogForDate && (
              <div className="bg-[#121214] border border-white/5 rounded-2xl p-5 sm:p-6 space-y-4">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Award className="w-4 h-4 text-emerald-400" />
                  Taqrizlar va Xulosalar
                </h3>

                {activeLogForDate.workplace_reviews && activeLogForDate.workplace_reviews.length > 0 ? (
                  <div className="p-3.5 bg-[#09090b] border border-white/5 rounded-xl">
                    <div className="text-xs font-medium text-zinc-300 flex items-center justify-between mb-1">
                      <span>Ish beruvchi (Mentor) xulosasi:</span>
                      <span className="text-[11px] text-zinc-500">
                        {activeLogForDate.workplace_reviews[0].decided_at}
                      </span>
                    </div>
                    <div className="text-xs text-emerald-400 font-medium">
                      Qaror: {activeLogForDate.workplace_reviews[0].decision}
                    </div>
                    {activeLogForDate.workplace_reviews[0].comment && (
                      <p className="text-xs text-zinc-400 mt-1 italic">
                        "{activeLogForDate.workplace_reviews[0].comment}"
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-zinc-500 italic">
                    Mentor xulosasi hali kiritilmagan
                  </div>
                )}

                {activeLogForDate.academic_reviews && activeLogForDate.academic_reviews.length > 0 ? (
                  <div className="p-3.5 bg-[#09090b] border border-white/5 rounded-xl">
                    <div className="text-xs font-medium text-zinc-300 flex items-center justify-between mb-1">
                      <span>Universitet o'qituvchisi taqrizi:</span>
                      <span className="text-[11px] text-zinc-500">
                        {activeLogForDate.academic_reviews[0].decided_at}
                      </span>
                    </div>
                    <div className="text-xs text-purple-400 font-medium">
                      Qaror: {activeLogForDate.academic_reviews[0].decision}
                    </div>
                    {activeLogForDate.academic_reviews[0].comment && (
                      <p className="text-xs text-zinc-400 mt-1 italic">
                        "{activeLogForDate.academic_reviews[0].comment}"
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-zinc-500 italic">
                    O'qituvchi taqrizi hali kiritilmagan
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Column: Log History Table */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-[#121214] border border-white/5 rounded-2xl p-5 sm:p-6">
              <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-4">
                <div>
                  <h2 className="text-base font-semibold text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-blue-400" />
                    Kundaliklar tarixi
                  </h2>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Kiritilgan va topshirilgan kunlik hisobotlar
                  </p>
                </div>

                <button
                  onClick={() => selectedPlacement && loadLogs(selectedPlacement.id)}
                  disabled={isLoadingLogs}
                  className="p-1.5 text-zinc-400 hover:text-white transition-colors rounded-lg bg-zinc-800"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingLogs ? "animate-spin" : ""}`} />
                </button>
              </div>

              {isLoadingLogs ? (
                <div className="py-12 text-center text-zinc-500 text-xs">
                  Yuklanmoqda...
                </div>
              ) : logs.length === 0 ? (
                <div className="py-12 text-center">
                  <Calendar className="w-8 h-8 text-zinc-600 mx-auto mb-2" />
                  <p className="text-xs text-zinc-400">Hozircha kundalik yozuvlari mavjud emas.</p>
                  <p className="text-[11px] text-zinc-600 mt-1">
                    Chapdagi forma orqali birinchi kunlik hisobotingizni kiriting.
                  </p>
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
                  {logs.map((log) => {
                    const badge = getStatusBadge(log.status);
                    const isSelected = log.local_date === selectedDate;
                    return (
                      <button
                        key={log.id}
                        type="button"
                        onClick={() => setSelectedDate(log.local_date)}
                        className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                          isSelected
                            ? "bg-blue-600/10 border-blue-500/40"
                            : "bg-[#09090b] border-white/5 hover:border-white/10"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-xs font-semibold text-white font-mono">
                            {log.local_date}
                          </span>
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${badge.className}`}
                          >
                            {badge.label}
                          </span>
                        </div>

                        <p className="text-xs text-zinc-400 line-clamp-1 mb-2">
                          {log.summary || "Amaliyot vazifalari bajarildi"}
                        </p>

                        <div className="flex items-center justify-between text-[11px] text-zinc-500">
                          <span>
                            {log.day_type === "WORKED" ? "Ish kuni" : "Dam olish"}
                          </span>
                          <span className="tabular-nums font-mono text-zinc-400">
                            {log.total_minutes} daq ({(log.total_minutes / 60).toFixed(1)} soat)
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onSuccess={() => {
          setAuthModalOpen(false);
          loadUser();
        }}
      />
    </div>
  );
}
