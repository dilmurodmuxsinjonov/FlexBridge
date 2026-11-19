"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  User,
  FileText,
  Bookmark,
  FileCheck2,
  BookOpen,
  Award,
  Bell,
  Shield,
  LifeBuoy,
  Search,
  LogOut,
  ShieldAlert,
  ArrowRight,
  CalendarDays,
  MessageCircle,
} from "lucide-react";
import { fetchAuthMe, logoutUser, type AuthUser } from "@/lib/api";
import { isStudentOnlyRoles, resolvePortalDashboard } from "@/lib/roles";
import SectionDock from "@/components/shell/SectionDock";

function getOtherRoleDashboard(roles: string[]): { href: string; label: string } {
  const dash = resolvePortalDashboard(roles);
  return { href: dash.href, label: dash.label };
}

interface SidebarGroup {
  title: string;
  items: {
    href: string;
    label: string;
    short: string;
    icon: typeof User;
    exact?: boolean;
  }[];
}

const STUDENT_NAV_GROUPS: SidebarGroup[] = [
  {
    title: "Karyera & Rezyume",
    items: [
      { href: "/nomzod", label: "Profil & Rezyume", short: "Profil", icon: User, exact: true },
      { href: "/elonlar", label: "E’lonlar Katalogi", short: "E’lonlar", icon: Search },
    ],
  },
  {
    title: "Arizalar & Shartnomalar",
    items: [
      { href: "/nomzod/arizalar", label: "Mening Arizalarim", short: "Arizalar", icon: FileText },
      { href: "/nomzod/saqlanganlar", label: "Saqlangan E’lonlar", short: "Saqlangan", icon: Bookmark },
      { href: "/nomzod/shartnomalar", label: "Shartnomalar & Amaliyot", short: "Shartnomalar", icon: FileCheck2 },
    ],
  },
  {
    title: "O‘qish & Amaliyot",
    items: [
      { href: "/nomzod/jadval", label: "O‘quv jadvali", short: "Jadval", icon: CalendarDays },
      { href: "/nomzod/kundalik", label: "Kundalik & E-Imzo", short: "Kundalik", icon: BookOpen },
      { href: "/nomzod/baholar", label: "Baholar & Apellyatsiya", short: "Baholar", icon: Award },
    ],
  },
  {
    title: "Hisob & Aloqa",
    items: [
      { href: "/xabarlar", label: "Xabarlar", short: "Xabarlar", icon: MessageCircle },
      { href: "/nomzod/bildirishnomalar", label: "Bildirishnomalar", short: "Bildirishnoma", icon: Bell },
      { href: "/nomzod/xavfsizlik", label: "Xavfsizlik & MFA", short: "Xavfsizlik", icon: Shield },
      { href: "/nomzod/yordam", label: "Yordam & Maxfiylik", short: "Yordam", icon: LifeBuoy },
    ],
  },
];

export default function NomzodLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const flatItems = STUDENT_NAV_GROUPS.flatMap((g) => g.items);
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

  const isCandidate = Boolean(currentUser && isStudentOnlyRoles(currentUser.roles));
  const isWrongRoleUser = Boolean(authResolved && currentUser && !isCandidate);

  const handleStudentSwitchLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    window.dispatchEvent(new Event("flexbridge:auth-changed"));
    router.push("/talaba/kirish");
    router.refresh();
  };

  return (
    <div className="min-h-screen text-[var(--fb-ink)]">
      {/* Sections live in the floating capsule at the bottom (device shell, Issue #263) */}
      <SectionDock label="Talaba bo‘limlari">
        {flatItems
          .filter((item) => item.href !== "/xabarlar")
          .map((item) => {
            const isActive = item.exact ? pathname === item.href : pathname?.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                title={item.label}
                aria-label={item.label}
                aria-current={isActive ? "page" : undefined}
                className="fb-nav-item"
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.short}</span>
              </Link>
            );
          })}
      </SectionDock>

      <div className="mx-auto w-full max-w-[1440px] px-4 py-5 md:px-8">
        {/* Main Workspace Content */}
        <div className="min-w-0">
          {isWrongRoleUser && currentUser ? (
            <div className="rounded-3xl skeuo-card p-8 max-w-xl mx-auto my-8 space-y-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/35 bg-amber-500/12 px-3 py-1 text-xs font-semibold text-amber-700 dark:text-amber-300">
                <ShieldAlert className="h-4 w-4" />
                <span>Rol chegarasi</span>
              </div>
              <h1 className="font-display text-xl font-bold text-[var(--fb-ink)]">
                Bu bo‘lim faqat Talaba / Nomzodlar uchun ajratilgan
              </h1>
              <p className="text-xs leading-relaxed text-zinc-400">
                Siz hozir{" "}
                <span className="font-mono text-zinc-200">
                  {currentUser.roles.join(", ")}
                </span>{" "}
                hisobi bilan tizimga kirgansiz. Talaba kabinetining funksiyalaridan (rezyume, arizalar, amaliyot kundaligi) foydalanish uchun talaba hisobingiz bilan alohida kiring.
              </p>
              <div className="flex flex-wrap gap-3 pt-2">
                <Link
                  href={getOtherRoleDashboard(currentUser.roles).href}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-white/10 border border-white/15 px-4 py-2 text-xs font-semibold text-white hover:bg-white/15 transition-colors"
                >
                  <span>{getOtherRoleDashboard(currentUser.roles).label}</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
                <button
                  type="button"
                  onClick={handleStudentSwitchLogout}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-sky-500 px-4 py-2 text-xs font-semibold text-white hover:bg-sky-400 transition-colors"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span>Chiqish va talaba sifatida kirish</span>
                </button>
              </div>
            </div>
          ) : (
            children
          )}
        </div>
      </div>
    </div>
  );
}
