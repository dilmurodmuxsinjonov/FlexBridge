"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ArrowRight,
  LogIn,
  LogOut,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
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
        <div className="w-full max-w-lg rounded-3xl skeuo-card p-7 space-y-5">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/35 bg-amber-500/12 px-3 py-1 text-xs font-semibold text-amber-700 dark:text-amber-300">
            <ShieldAlert className="w-4 h-4" />
            <span>Kirish Chegarasi</span>
          </div>
          <div className="space-y-2">
            <h1 className="font-display text-xl font-bold text-[var(--fb-ink)]">
              Bu bo‘lim faqat Platforma Operatorlari va Auditorlari uchun
            </h1>
            <p className="text-xs leading-relaxed text-[var(--fb-ink-muted)]">
              Siz hozir boshqa foydalanuvchi hisobi bilan tizimdasiz. Operator nazorat paneliga kirish uchun vakolatli platforma operatori hisobi talab qilinadi.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-[var(--fb-border)]">
            <Link
              href={targetDashboard.href}
              className="skeuo-btn-obsidian rounded-full px-4 py-2 text-xs"
            >
              <span>{targetDashboard.label}ga qaytish</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
            <button
              type="button"
              onClick={handleLogoutAndSwitch}
              className="skeuo-btn-accent rounded-full px-4 py-2 text-xs"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Chiqish va Operator sifatida kirish</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] text-[var(--fb-ink)]">
      {authLoaded && !currentUser && (
        <div className="max-w-[1440px] mx-auto px-4 pt-2 md:px-8 text-xs">
          <div className="skeuo-card rounded-2xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-amber-700 dark:text-amber-200">
              <ShieldCheck className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
              <span>
                <strong>Operator Nazorat Terminali:</strong> Ikki bosqichli tasdiqlash va 2FA (TOTP) asosidagi xavfsiz kirish.
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Link
                href="/operator/kirish"
                className="inline-flex items-center gap-1.5 rounded-full skeuo-btn-obsidian px-3.5 py-1.5 text-[11px] font-semibold"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Operator alohida kirishi</span>
              </Link>
            </div>
          </div>
        </div>
      )}
      {children}
    </div>
  );
}
