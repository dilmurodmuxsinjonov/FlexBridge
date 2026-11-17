"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ArrowRight, LogOut, ShieldAlert } from "lucide-react";
import { AuthUser, fetchAuthMe, logoutUser } from "@/lib/api";
import { isOperatorRoles, resolvePortalDashboard } from "@/lib/roles";

export default function OperatorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authLoaded, setAuthLoaded] = useState(false);

  const isDedicatedAuthRoute = Boolean(pathname?.startsWith("/operator/kirish"));

  useEffect(() => {
    let active = true;
    const syncAuth = () => {
      fetchAuthMe().then((user) => {
        if (!active) return;
        setCurrentUser(user);
        setAuthLoaded(true);
      });
    };
    syncAuth();
    window.addEventListener("flexbridge:auth-changed", syncAuth);
    return () => {
      active = false;
      window.removeEventListener("flexbridge:auth-changed", syncAuth);
    };
  }, [pathname]);

  const handleLogoutAndSwitch = async () => {
    await logoutUser();
    setCurrentUser(null);
    window.dispatchEvent(new Event("flexbridge:auth-changed"));
    router.push("/operator/kirish");
    router.refresh();
  };

  if (isDedicatedAuthRoute) {
    return <>{children}</>;
  }

  if (authLoaded && currentUser && !isOperatorRoles(currentUser.roles)) {
    const targetDashboard = resolvePortalDashboard(currentUser.roles);
    return (
      <div className="min-h-[calc(100vh-4rem)] text-[var(--fb-ink)] flex items-center justify-center px-4 py-12">
        <section
          aria-labelledby="op-boundary-title"
          className="fb-panel skeuo-card w-full max-w-lg rounded-[28px] p-7 space-y-5"
        >
          <div className="inline-flex items-center gap-2 rounded-full skeuo-well-sm px-3 py-1 text-xs font-semibold text-[var(--fb-ink-secondary)]">
            <ShieldAlert className="w-4 h-4 text-[var(--fb-accent)]" aria-hidden="true" />
            <span>Kirish chegarasi</span>
          </div>
          <div className="space-y-2">
            <h1 id="op-boundary-title" className="font-display text-xl font-bold text-[var(--fb-ink)]">
              Bu bo‘lim faqat platforma xodimlari uchun
            </h1>
            <p className="text-xs leading-relaxed text-[var(--fb-ink-muted)]">
              Siz hozir {targetDashboard.label.toLowerCase()} hisobi bilan tizimdasiz. Operator Markaziga kirish uchun vakolatli platforma xodimi hisobiga o‘ting.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-[color-mix(in_srgb,var(--fb-ink)_10%,transparent)]">
            <Link
              href={targetDashboard.href}
              className="skeuo-btn-obsidian rounded-full px-4 py-2 text-xs"
            >
              <span>{targetDashboard.label}ga qaytish</span>
              <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </Link>
            <button
              type="button"
              onClick={handleLogoutAndSwitch}
              className="skeuo-btn-secondary rounded-full px-4 py-2 text-xs"
            >
              <LogOut className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Chiqish va operator sifatida kirish</span>
            </button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] text-[var(--fb-ink)]">
      {children}
    </div>
  );
}
