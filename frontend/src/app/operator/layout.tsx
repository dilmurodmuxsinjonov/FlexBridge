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
      <div className="min-h-[calc(100vh-4rem)] bg-background text-zinc-100 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-lg rounded-2xl border border-amber-500/30 bg-[#121214] p-7 space-y-5 shadow-2xl">
          <div className="inline-flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-mono font-semibold text-amber-300">
            <ShieldAlert className="w-4 h-4" />
            <span>SOC Rol Chegarasi (Role Boundary)</span>
          </div>
          <div className="space-y-2">
            <h1 className="font-heading text-xl font-bold text-white">
              Bu terminal faqat Platforma Operatori va Auditorlari uchun
            </h1>
            <p className="text-xs leading-relaxed text-zinc-400">
              Siz hozir{" "}
              <span className="font-mono text-zinc-200">
                {currentUser.user_id}
              </span>{" "}
              (<span className="font-mono text-amber-300">{currentUser.roles.join(", ")}</span>)
              hisobi bilan tizimdasiz. SOC xavfsizlik terminaliga kirish uchun vakolatli{" "}
              <code className="text-amber-300">OPERATOR</code> /{" "}
              <code className="text-amber-300">MODERATOR</code> /{" "}
              <code className="text-amber-300">AUDITOR</code> hisobi talab qilinadi.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-white/[0.06]">
            <Link
              href={targetDashboard.href}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary-hover transition-colors"
            >
              <span>{targetDashboard.label}ga qaytish</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
            <button
              type="button"
              onClick={handleLogoutAndSwitch}
              className="inline-flex items-center gap-1.5 rounded-lg border border-amber-500/35 bg-amber-500/10 px-4 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 transition-colors"
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
    <div className="min-h-[calc(100vh-4rem)] bg-background text-zinc-100">
      {authLoaded && !currentUser && (
        <div className="border-b border-amber-500/20 bg-amber-500/[0.06] px-4 py-2.5 text-xs">
          <div className="max-w-[1440px] mx-auto flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-amber-200">
              <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                <strong>Operator SOC Terminal:</strong> Dual-control vakolat va 2FA (TOTP) asosidagi xavfsiz kirish.
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Link
                href="/operator/kirish"
                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-[11px] font-semibold text-zinc-950 hover:bg-amber-500 transition-colors"
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
