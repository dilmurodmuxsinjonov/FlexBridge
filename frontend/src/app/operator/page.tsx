"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Lock,
  CheckCircle2,
  Loader2,
  LogIn,
  LogOut,
  AlertCircle,
} from "lucide-react";
import { fetchAuthMe, fetchOperatorAuditEvents, logoutUser, AuthUser, OperatorAuditEventItem } from "@/lib/api";
import AuthModal from "@/components/AuthModal";

export default function OperatorPortal() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  const [auditEvents, setAuditEvents] = useState<OperatorAuditEventItem[]>([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [eventsError, setEventsError] = useState<string | null>(null);

  const loadAuditEvents = useCallback(async () => {
    setIsLoadingEvents(true);
    setEventsError(null);
    try {
      const items = await fetchOperatorAuditEvents();
      setAuditEvents(items);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 403) {
        setEventsError("Ruxsat berilmadi: Ushbu bo‘lim faqat platforma AUDITOR yoki ADMIN rollari uchun ruxsat etilgan.");
      } else {
        setEventsError(err instanceof Error ? err.message : "Audit jurnallarini yuklashda xatolik yuz berdi");
      }
    } finally {
      setIsLoadingEvents(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    fetchAuthMe().then((user) => {
      if (isMounted) {
        setCurrentUser(user);
        setIsAuthLoading(false);
        if (user) {
          loadAuditEvents();
        }
      }
    });
    return () => {
      isMounted = false;
    };
  }, [loadAuditEvents]);

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setAuditEvents([]);
    setEventsError(null);
  };

  const handleLoginSuccess = (user: AuthUser) => {
    setCurrentUser(user);
    loadAuditEvents();
  };

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* HEADER BAR */}
      <section className="w-full bg-surface-card border border-white/[0.08] rounded-lg p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                Operator va Xavfsizlik Portali
              </span>
              <span className="text-zinc-500 text-xs">• API-118 / CAP-036</span>
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
              Platforma Audit Tarmog‘i va Xavfsizlik Nazorati
            </h1>
            <p className="text-xs text-zinc-400">
              O‘zgartirib bo‘lmas (append-only) audit voqealari, kriptografik xeshlar va tizim jurnallari.
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
                <span>Operator sifatida kirish</span>
              </button>
            )}
          </div>
        </div>
      </section>

      {/* UNAUTHENTICATED STATE */}
      {!currentUser && !isAuthLoading && (
        <section className="w-full bg-surface-card/60 border border-white/[0.08] rounded-xl p-8 flex flex-col items-center justify-center text-center gap-4 py-16">
          <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <Lock className="w-7 h-7" />
          </div>
          <div className="flex flex-col gap-1 max-w-md">
            <h2 className="text-base md:text-lg font-heading font-semibold text-white">
              Xavfsizlik audit jurnallariga kirish uchun tizimga kiring
            </h2>
            <p className="text-xs text-zinc-400">
              Ushbu bo‘lim faqat vakolatli xavfsizlik auditorlari va tizim ma’murlari uchun mo‘ljallangan.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsLoginModalOpen(true)}
            className="mt-2 px-5 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-xs font-semibold text-white transition-all flex items-center gap-2 shadow-lg shadow-primary/25"
          >
            <LogIn className="w-4 h-4" />
            <span>Auditor hisobi bilan kirish</span>
          </button>
        </section>
      )}

      {/* AUTHENTICATED AUDIT LOGS */}
      {currentUser && (
        <div className="flex flex-col gap-6">
          {eventsError && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{eventsError}</span>
            </div>
          )}

          {isLoadingEvents ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-3 text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span className="text-xs">Audit voqealari jurnali yuklanmoqda...</span>
            </div>
          ) : auditEvents.length === 0 ? (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl p-12 flex flex-col items-center justify-center gap-2 text-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mb-1" />
              <h3 className="text-sm font-semibold text-white">Hozirda yangi audit voqealari yo‘q</h3>
              <p className="text-xs text-zinc-400 max-w-md">
                Barcha tizim hodisalari xavfsiz saqlanmoqda.
              </p>
            </div>
          ) : (
            <div className="w-full bg-surface-card border border-white/[0.08] rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-white/[0.08] flex items-center justify-between">
                <span className="text-xs font-semibold text-white">
                  Audit Voqealari ({auditEvents.length} ta qayd)
                </span>
                <button
                  type="button"
                  onClick={loadAuditEvents}
                  className="text-xs text-primary hover:underline"
                >
                  Yangilash
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-white/[0.02] text-zinc-400 border-b border-white/[0.06] font-mono text-[11px]">
                    <tr>
                      <th className="px-4 py-2.5">Sana / Vaqt</th>
                      <th className="px-4 py-2.5">Harakat</th>
                      <th className="px-4 py-2.5">Aktyor (User ID)</th>
                      <th className="px-4 py-2.5">Obyekt turi</th>
                      <th className="px-4 py-2.5">Obyekt kaliti</th>
                      <th className="px-4 py-2.5">Digest / Xesh</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.06]">
                    {auditEvents.map((evt) => (
                      <tr key={evt.id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="px-4 py-3 font-mono text-[11px] text-zinc-400 whitespace-nowrap">
                          {evt.occurred_at ? new Date(evt.occurred_at).toLocaleString("uz-UZ") : "-"}
                        </td>
                        <td className="px-4 py-3 font-semibold text-white">
                          <span className="px-1.5 py-0.5 rounded bg-white/[0.06] text-primary border border-primary/20 text-[10px] font-mono">
                            {evt.action}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-zinc-300">
                          {evt.actor_id ? `${evt.actor_id.slice(0, 8)}...` : "Tizim"}
                        </td>
                        <td className="px-4 py-3 text-zinc-300">{evt.object_type || "-"}</td>
                        <td className="px-4 py-3 font-mono text-zinc-400">
                          {evt.object_key ? `${evt.object_key.slice(0, 12)}...` : "-"}
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-emerald-400/80">
                          {evt.after_digest ? `${evt.after_digest.slice(0, 10)}...` : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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
        title="Operator Tizimiga Kirish"
        subtitle="Platforma xavfsizlik auditori yoki ma’muri hisob ma’lumotlarini kiriting"
      />
    </main>
  );
}
