"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ArrowRight, GraduationCap, Lock, LogOut, ShieldAlert } from "lucide-react";
import { fetchAuthMe, logoutUser, type AuthUser } from "@/lib/api";
import { isAcademicRoles, resolvePortalDashboard } from "@/lib/roles";

export default function UniversityLayout({ children }: { children: React.ReactNode }) {
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

  const isAcademic = Boolean(currentUser && isAcademicRoles(currentUser.roles));
  const isWrongRoleUser = Boolean(authResolved && currentUser && !isAcademic);

  const handleAcademicSwitchLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    window.dispatchEvent(new Event("flexbridge:auth-changed"));
    router.push("/universitet/kirish");
    router.refresh();
  };

  if (isWrongRoleUser && currentUser) {
    const dash = resolvePortalDashboard(currentUser.roles);
    return (
      <div className="min-h-screen bg-[#09090b] text-zinc-100 px-4 py-12">
        <div className="rounded-2xl border border-amber-500/25 bg-[#121214] p-8 max-w-xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-300">
            <ShieldAlert className="h-4 w-4" />
            <span>Rol chegarasi</span>
          </div>
          <h1 className="font-heading text-xl font-bold text-white">
            Bu bo‘lim faqat Universitet / OTM koordinatori va o‘qituvchilari uchun ajratilgan
          </h1>
          <p className="text-xs leading-relaxed text-zinc-400">
            Siz hozir{" "}
            <span className="font-mono text-zinc-200">{currentUser.roles.join(", ")}</span>{" "}
            hisobi bilan tizimga kirgansiz. OTM dekanati va amaliyot nazorati kabinetiga kirish uchun akademik rolga ega hisobingiz bilan kiring.
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
              onClick={handleAcademicSwitchLogout}
              className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Chiqish va OTM sifatida kirish</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100">
      <div className="border-b border-indigo-500/15 bg-surface/60">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-2.5 md:px-8 text-xs">
          <div className="flex items-center gap-2 text-indigo-300 font-medium">
            <GraduationCap className="h-3.5 w-3.5 text-indigo-400" />
            <span>Universitet / OTM Akademik Nazorati</span>
          </div>
          {authResolved && (
            <div className="flex items-center gap-3">
              {currentUser && isAcademic ? (
                <span className="inline-flex items-center gap-1.5 text-[11px] text-indigo-400 font-medium">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                  <span>OTM sessiyasi faol</span>
                </span>
              ) : !currentUser ? (
                <div className="flex items-center gap-2">
                  <Link
                    href="/universitet/kirish"
                    className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-indigo-500 transition-colors"
                  >
                    <Lock className="h-3 w-3" />
                    <span>OTM kirishi</span>
                  </Link>
                  <Link
                    href="/universitet/royxatdan-otish"
                    className="inline-flex items-center rounded-lg border border-indigo-500/25 bg-indigo-500/10 px-2.5 py-1 text-[11px] font-medium text-indigo-300 hover:bg-indigo-500/20 transition-colors"
                  >
                    OTM vakili ulanishi
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
