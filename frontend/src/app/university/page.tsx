"use client";

import { useEffect, useState, useCallback } from "react";
import {
  CheckCircle2,
  AlertCircle,
  GraduationCap,
  Loader2,
  LogIn,
  LogOut,
} from "lucide-react";
import { fetchAuthMe, fetchUniversityReviewQueue, logoutUser, AuthUser, AcademicReviewQueueItem } from "@/lib/api";
import AuthModal from "@/components/AuthModal";

export default function UniversityPortal() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  const [queueItems, setQueueItems] = useState<AcademicReviewQueueItem[]>([]);
  const [isLoadingQueue, setIsLoadingQueue] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);

  const loadQueue = useCallback(async () => {
    setIsLoadingQueue(true);
    setQueueError(null);
    try {
      const items = await fetchUniversityReviewQueue();
      setQueueItems(items);
    } catch (err: unknown) {
      setQueueError(err instanceof Error ? err.message : "Navbatni yuklashda xatolik yuz berdi");
    } finally {
      setIsLoadingQueue(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    fetchAuthMe().then((user) => {
      if (isMounted) {
        setCurrentUser(user);
        setIsAuthLoading(false);
        if (user) {
          loadQueue();
        }
      }
    });
    return () => {
      isMounted = false;
    };
  }, [loadQueue]);

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setQueueItems([]);
    setQueueError(null);
  };

  const handleLoginSuccess = (user: AuthUser) => {
    setCurrentUser(user);
    loadQueue();
  };

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* HEADER BAR */}
      <section className="w-full bg-surface-card border border-white/[0.08] rounded-lg p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                Universitet Portali
              </span>
              <span className="text-zinc-500 text-xs">• API-105 / Akademik Navbat</span>
              {currentUser ? (
                <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  Kirilgan: {currentUser.user_id.slice(0, 8)}... ({currentUser.roles.join(", ")})
                </span>
              ) : (
                <span className="text-[11px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                  Avtorizatsiyadan o‘tilmagan
                </span>
              )}
            </div>
            <h1 className="font-heading text-lg md:text-xl font-bold text-zinc-100">
              Akademik Nazorat va Kundaliklar Navbati
            </h1>
            <p className="text-xs text-zinc-400">
              Oliy ta’lim muassasasi kafedra o‘qituvchilari uchun stajirovkalar va kundalik hisobotlarini ko‘rib chiqish tizimi.
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
                <span>O‘qituvchi sifatida kirish</span>
              </button>
            )}
          </div>
        </div>
      </section>

      {/* UNAUTHENTICATED STATE */}
      {!currentUser && !isAuthLoading && (
        <section className="w-full bg-surface-card/60 border border-white/[0.08] rounded-xl p-8 flex flex-col items-center justify-center text-center gap-4 py-16">
          <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <GraduationCap className="w-7 h-7" />
          </div>
          <div className="flex flex-col gap-1 max-w-md">
            <h2 className="text-base md:text-lg font-heading font-semibold text-white">
              Akademik navbatni ko‘rish uchun tizimga kiring
            </h2>
            <p className="text-xs text-zinc-400">
              Talabalar amaliyot kundaliklarini tasdiqlash uchun kafedra mas’ul o‘qituvchisi hisobingiz orqali tizimga kiring.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsLoginModalOpen(true)}
            className="mt-2 px-5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-2 shadow-lg shadow-primary/25"
          >
            <LogIn className="w-4 h-4" />
            <span>Tizimga kirish</span>
          </button>
        </section>
      )}

      {/* AUTHENTICATED REVIEW QUEUE */}
      {currentUser && (
        <div className="flex flex-col gap-6">
          {queueError && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{queueError}</span>
            </div>
          )}

          {isLoadingQueue ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-3 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span className="text-xs">Akademik ko‘rib chiqish navbati yuklanmoqda...</span>
            </div>
          ) : queueItems.length === 0 ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-2 text-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mb-1" />
              <h3 className="text-sm font-semibold text-white">Hozirda ko‘rib chiqish navbati bo‘sh</h3>
              <p className="text-xs text-zinc-400 max-w-md">
                Sizga biriktirilgan talabalarning barcha topshirilgan amaliyot kundaliklari ko‘rib chiqilgan.
              </p>
            </div>
          ) : (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-white/[0.08] flex items-center justify-between">
                <span className="text-xs font-semibold text-white">
                  Kutilayotgan kundaliklar ({queueItems.length} ta)
                </span>
                <button
                  type="button"
                  onClick={loadQueue}
                  className="text-xs text-primary hover:underline"
                >
                  Yangilash
                </button>
              </div>

              <div className="divide-y divide-white/[0.06]">
                {queueItems.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 hover:bg-white/[0.02] transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">
                          {item.student_name || "Talaba"}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                          Rev #{item.revision}
                        </span>
                        <span className="text-xs text-zinc-400">• Sana: {item.local_date}</span>
                      </div>
                      <div className="text-xs text-zinc-400 flex flex-wrap items-center gap-2">
                        <span>Maqsad: {item.purpose}</span>
                        <span>•</span>
                        <span className="font-mono text-[11px]">
                          Kundalik ID: {item.daily_log_id.slice(0, 8)}...
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[11px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                        Ko‘rib chiqish kutilmoqda
                      </span>
                    </div>
                  </div>
                ))}
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
        title="Universitet O‘qituvchisi Kirishi"
        subtitle="O‘qituvchi yoki kafedra hisob ma’lumotlaringizni kiriting"
      />
    </main>
  );
}
