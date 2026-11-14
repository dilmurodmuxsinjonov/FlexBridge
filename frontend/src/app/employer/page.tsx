"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Users,
  Briefcase,
  Calendar,
  Search,
  Building,
  GraduationCap,
  Loader2,
  LogIn,
  LogOut,
  AlertCircle,
} from "lucide-react";
import { fetchAuthMe, fetchEmployerDashboard, logoutUser, AuthUser, EmployerDashboardMetrics } from "@/lib/api";
import AuthModal from "@/components/AuthModal";

export default function EmployerPortal() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Organization selection & dashboard data
  const [orgId, setOrgId] = useState("");
  const [dashboard, setDashboard] = useState<EmployerDashboardMetrics | null>(null);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  const loadDashboard = useCallback(async (targetOrgId: string) => {
    if (!targetOrgId.trim()) return;
    setIsLoadingDashboard(true);
    setDashboardError(null);

    try {
      const data = await fetchEmployerDashboard(targetOrgId.trim());
      setDashboard(data);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 404) {
        setDashboardError("Tashkilot topilmadi yoki unga kirish huquqingiz yo'q (IDOR himoyasi).");
      } else if (status === 401) {
        setDashboardError("Sessiya muddati tugagan. Iltimos, qayta tizimga kiring.");
        setCurrentUser(null);
      } else {
        setDashboardError(err instanceof Error ? err.message : "Ma'lumotlarni yuklashda xatolik yuz berdi.");
      }
      setDashboard(null);
    } finally {
      setIsLoadingDashboard(false);
    }
  }, []);

  // Load session on mount
  useEffect(() => {
    let isMounted = true;
    fetchAuthMe().then((user) => {
      if (isMounted) {
        setCurrentUser(user);
        setIsAuthLoading(false);
      }
    });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setDashboard(null);
    setDashboardError(null);
  };

  const handleLoginSuccess = (user: AuthUser) => {
    setCurrentUser(user);
    if (orgId) {
      loadDashboard(orgId);
    }
  };

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* AUTH STATUS & HEADER BAR */}
      <section className="w-full bg-surface-card border border-white/[0.08] rounded-lg p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                Ish Beruvchi Portali
              </span>
              <span className="text-zinc-500 text-xs">• API-068 / CAP-015</span>
              {currentUser ? (
                <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                  <span>Kirilgan: {currentUser.user_id.slice(0, 8)}...</span>
                  <span className="text-zinc-500">({currentUser.roles.join(", ")})</span>
                </span>
              ) : (
                <span className="text-[11px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                  Avtorizatsiyadan o‘tilmagan
                </span>
              )}
            </div>
            <h1 className="font-heading text-lg md:text-xl font-bold text-zinc-100">
              Tashkilot HR va Vakansiyalar Boshqaruvi
            </h1>
            <p className="text-xs text-zinc-400">
              Haqiqiy backend API-068 orqali tashkilot statistikasi va arizalar monitoringi.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {isAuthLoading ? (
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Yuklanmoqda...</span>
              </div>
            ) : currentUser ? (
              <button
                type="button"
                onClick={handleLogout}
                className="px-3.5 py-2 rounded bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-rose-300 hover:text-rose-200 transition-all flex items-center gap-1.5"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Chiqish</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIsLoginModalOpen(true)}
                className="px-3.5 py-2 rounded bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shadow-md shadow-primary/20"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Tizimga kirish</span>
              </button>
            )}
          </div>
        </div>
      </section>

      {/* UNAUTHENTICATED STATE */}
      {!currentUser && !isAuthLoading && (
        <section className="w-full bg-surface-card/60 border border-white/[0.08] rounded-xl p-8 flex flex-col items-center justify-center text-center gap-4 py-16">
          <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <Building className="w-7 h-7" />
          </div>
          <div className="flex flex-col gap-1 max-w-md">
            <h2 className="text-base md:text-lg font-heading font-semibold text-white">
              Tashkilot ma’lumotlariga kirish uchun tizimga kiring
            </h2>
            <p className="text-xs text-zinc-400">
              Ushbu bo‘lim tashkilot HR vakillari va rahbarlari uchun mo‘ljallangan. Tashkilotingiz tahlillarini ko‘rish uchun tizimga kiring.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsLoginModalOpen(true)}
            className="mt-2 px-5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-2 shadow-lg shadow-primary/25"
          >
            <LogIn className="w-4 h-4" />
            <span>HR hisobi bilan kirish</span>
          </button>
        </section>
      )}

      {/* AUTHENTICATED WORKSPACE */}
      {currentUser && (
        <div className="flex flex-col gap-6">
          {/* ORG ID SELECTOR */}
          <section className="w-full bg-surface-card border border-white/[0.08] rounded-lg p-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="flex flex-1 items-center gap-2">
              <label htmlFor="orgIdInput" className="text-xs font-medium text-zinc-300 shrink-0">
                Tashkilot ID (UUID):
              </label>
              <input
                id="orgIdInput"
                type="text"
                value={orgId}
                onChange={(e) => setOrgId(e.target.value)}
                placeholder="masalan: e1a54054-0eb7-4eb2-a7d1-e63013d39ea3"
                className="w-full max-w-md px-3 py-1.5 rounded bg-surface border border-white/[0.08] text-xs font-mono text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50"
              />
            </div>
            <button
              type="button"
              disabled={isLoadingDashboard || !orgId.trim()}
              onClick={() => loadDashboard(orgId)}
              className="px-4 py-1.5 rounded bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center justify-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoadingDashboard ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Yuklanmoqda...</span>
                </>
              ) : (
                <>
                  <Search className="w-3.5 h-3.5" />
                  <span>Tahlillarni yuklash</span>
                </>
              )}
            </button>
          </section>

          {/* DASHBOARD ERROR MESSAGE */}
          {dashboardError && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <div className="flex flex-col gap-0.5">
                <span className="font-semibold">Kirish rad etildi / Xatolik:</span>
                <span>{dashboardError}</span>
              </div>
            </div>
          )}

          {/* METRICS DISPLAY */}
          {dashboard?.metrics && (
            <div className="flex flex-col gap-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* VACANCIES / OPPORTUNITIES */}
                <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-2">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs font-medium">Vakansiyalar</span>
                    <Briefcase className="w-4 h-4 text-primary" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-white">
                    {dashboard.metrics.opportunities.total}
                  </div>
                  <div className="text-[11px] text-zinc-400 flex flex-wrap gap-2">
                    <span className="text-emerald-400">
                      {dashboard.metrics.opportunities.published} faol
                    </span>
                    <span>•</span>
                    <span>{dashboard.metrics.opportunities.draft} qoralama</span>
                  </div>
                </div>

                {/* APPLICATIONS */}
                <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-2">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs font-medium">Nomzodlar arizalari</span>
                    <Users className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-white">
                    {dashboard.metrics.applications.total}
                  </div>
                  <div className="text-[11px] text-zinc-400 flex flex-wrap gap-2">
                    <span className="text-amber-400">
                      {dashboard.metrics.applications.pending} kutilmoqda
                    </span>
                    <span>•</span>
                    <span className="text-emerald-400">
                      {dashboard.metrics.applications.offered} taklif qilingan
                    </span>
                  </div>
                </div>

                {/* INTERVIEWS */}
                <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-2">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs font-medium">Suhbatlar</span>
                    <Calendar className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-white">
                    {dashboard.metrics.interviews.total}
                  </div>
                  <div className="text-[11px] text-zinc-400 flex flex-wrap gap-2">
                    <span className="text-blue-400">
                      {dashboard.metrics.interviews.scheduled} rejalashtirilgan
                    </span>
                    <span>•</span>
                    <span>{dashboard.metrics.interviews.completed} yakunlangan</span>
                  </div>
                </div>

                {/* ENGAGEMENTS */}
                <div className="p-4 rounded-xl bg-surface-card border border-white/[0.08] flex flex-col gap-2">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs font-medium">Stajirovkalar (Dual ta&apos;lim)</span>
                    <GraduationCap className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-white">
                    {dashboard.metrics.engagements.total}
                  </div>
                  <div className="text-[11px] text-zinc-400 flex flex-wrap gap-2">
                    <span className="text-emerald-400">
                      {dashboard.metrics.engagements.active} faol
                    </span>
                    <span>•</span>
                    <span>{dashboard.metrics.engagements.completed} yakunlangan</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* LOGIN MODAL */}
      <AuthModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onSuccess={handleLoginSuccess}
        title="Ish Beruvchi Tizimiga Kirish"
        subtitle="Tashkilot HR yoki Rahbar hisob ma’lumotlaringizni kiriting"
      />
    </main>
  );
}
