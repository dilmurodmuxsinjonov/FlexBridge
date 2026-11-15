"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Building2, Lock, LogOut, ShieldAlert, ArrowRight } from "lucide-react";
import { fetchAuthMe, logoutUser, type AuthUser } from "@/lib/api";
import { isEmployerRoles, resolvePortalDashboard } from "@/lib/roles";

export default function EmployerLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authResolved, setAuthResolved] = useState(false);

  useEffect(() => {
    let active = true;
    const syncAuth = () => {
      fetchAuthMe()
        .then((user) => {
          if (active) {
            setCurrentUser(user);
            setAuthResolved(true);
          }
        })
        .catch(() => {
          if (active) {
            setCurrentUser(null);
            setAuthResolved(true);
          }
        });
    };
    syncAuth();
    window.addEventListener("flexbridge:auth-changed", syncAuth);
    return () => {
      active = false;
      window.removeEventListener("flexbridge:auth-changed", syncAuth);
    };
  }, [pathname]);

  const isEmployer = Boolean(currentUser && isEmployerRoles(currentUser.roles));
  const isWrongRoleUser = Boolean(authResolved && currentUser && !isEmployer);

  const handleEmployerSwitchLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    router.push("/korxona/kirish");
    router.refresh();
  };

  if (isWrongRoleUser && currentUser) {
    const dash = resolvePortalDashboard(currentUser.roles);
    return (
      <div className="min-h-screen text-[var(--fb-ink)] px-4 py-12">
        <div className="rounded-3xl skeuo-card p-8 max-w-xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/35 bg-amber-500/12 px-3 py-1 text-xs font-semibold text-amber-700 dark:text-amber-300">
            <ShieldAlert className="h-4 w-4" />
            <span>Rol chegarasi</span>
          </div>
          <h1 className="font-display text-xl font-bold text-[var(--fb-ink)]">
            Bu bo‘lim faqat Korxona / Ish beruvchi vakillari uchun ajratilgan
          </h1>
          <p className="text-xs leading-relaxed text-zinc-400">
            Siz hozir{" "}
            <span className="font-mono text-zinc-200">{currentUser.roles.join(", ")}</span>{" "}
            hisobi bilan tizimga kirgansiz. Korxona HR va mentorlik kabinetiga kirish uchun tashkilotga biriktirilgan korxona hisobingiz bilan kiring.
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Link
              href={dash.href}
              className="inline-flex items-center gap-1.5 rounded-xl bg-white/10 border border-white/15 px-4 py-2 text-xs font-semibold text-white hover:bg-white/15 transition-colors"
            >
              <span>{dash.label}</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <button
              type="button"
              onClick={handleEmployerSwitchLogout}
              className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Chiqish va korxona sifatida kirish</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-[var(--fb-ink)]">
      <div className="mx-auto max-w-[1440px] px-4 pt-2 md:px-8">
        <div className="skeuo-card rounded-2xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 font-semibold">
            <Building2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <span>Korxona / HR & Mentorlik Kabineti</span>
          </div>
          {authResolved && (
            <div className="flex items-center gap-3">
              {currentUser && isEmployer ? (
                <span className="inline-flex items-center gap-1.5 text-[11px] text-emerald-700 dark:text-emerald-400 font-semibold">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.7)]" />
                  <span>Korxona sessiyasi faol</span>
                </span>
              ) : !currentUser ? (
                <div className="flex items-center gap-2">
                  <Link
                    href="/korxona/kirish"
                    className="inline-flex items-center gap-1 rounded-full skeuo-btn-obsidian px-3 py-1.5 text-[11px] font-semibold"
                  >
                    <Lock className="h-3 w-3" />
                    <span>Korxona kirishi</span>
                  </Link>
                  <Link
                    href="/korxona/royxatdan-otish"
                    className="inline-flex items-center rounded-full skeuo-btn-secondary px-3 py-1.5 text-[11px] font-semibold"
                  >
                    Vakil ulanishi
                  </Link>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
      {children}
    </div>
  );
}
