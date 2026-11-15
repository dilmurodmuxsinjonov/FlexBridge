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
  GraduationCap,
  Lock,
  LogOut,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";
import { fetchAuthMe, logoutUser, type AuthUser } from "@/lib/api";
import { isStudentOnlyRoles, resolvePortalDashboard } from "@/lib/roles";

function getOtherRoleDashboard(roles: string[]): { href: string; label: string } {
  const dash = resolvePortalDashboard(roles);
  return { href: dash.href, label: dash.label };
}

interface SidebarGroup {
  title: string;
  items: {
    href: string;
    label: string;
    icon: typeof User;
    exact?: boolean;
  }[];
}

const STUDENT_NAV_GROUPS: SidebarGroup[] = [
  {
    title: "Karyera & Rezyume",
    items: [
      { href: "/nomzod", label: "Profil & Rezyume", icon: User, exact: true },
      { href: "/", label: "E’lonlar Katalogi", icon: Search, exact: true },
    ],
  },
  {
    title: "Arizalar & Shartnomalar",
    items: [
      { href: "/nomzod/arizalar", label: "Mening Arizalarim", icon: FileText },
      { href: "/nomzod/saqlanganlar", label: "Saqlangan E’lonlar", icon: Bookmark },
      { href: "/nomzod/shartnomalar", label: "Shartnomalar & Amaliyot", icon: FileCheck2 },
    ],
  },
  {
    title: "Amaliyot & Natijalar",
    items: [
      { href: "/nomzod/kundalik", label: "Kundalik & E-Imzo", icon: BookOpen },
      { href: "/nomzod/baholar", label: "Baholar & Apellyatsiya", icon: Award },
    ],
  },
  {
    title: "Hisob & Aloqa",
    items: [
      { href: "/nomzod/bildirishnomalar", label: "Bildirishnomalar", icon: Bell },
      { href: "/nomzod/xavfsizlik", label: "Xavfsizlik & MFA", icon: Shield },
      { href: "/nomzod/yordam", label: "Yordam & Maxfiylik", icon: LifeBuoy },
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
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-4 py-5 md:px-8 lg:flex-row lg:items-start">
        {/* Desktop Student Workspace Rail */}
        <aside
          aria-label="Talaba kabineti navigatsiyasi"
          className="hidden lg:flex lg:w-[252px] shrink-0 flex-col gap-4 sticky top-20"
        >
          {/* Student Persona Identity Card */}
          <div className="rounded-3xl skeuo-card p-4">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/15 border border-sky-500/25 text-sky-400">
                <GraduationCap className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-white tracking-tight truncate">
                  Talaba & Nomzod
                </p>
                <p className="text-[11px] text-sky-400 font-medium truncate">
                  Karyera va Amaliyot Kabineti
                </p>
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-white/[0.06] text-[11px] text-zinc-400 leading-relaxed">
              HEMIS jadvali asosida mos smenali ishlar va elektron imzoli amaliyot kundaligi.
            </div>
            {authResolved && (
              <div className="mt-3 pt-3 border-t border-white/[0.06] space-y-2">
                {currentUser && isCandidate ? (
                  <div className="flex items-center justify-between gap-2 text-[11px]">
                    <span className="inline-flex items-center gap-1.5 text-emerald-400 font-medium truncate">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0" />
                      <span>Talaba sessiyasi faol</span>
                    </span>
                    <button
                      type="button"
                      onClick={handleStudentSwitchLogout}
                      className="inline-flex items-center gap-1 text-zinc-400 hover:text-rose-300 transition-colors"
                    >
                      <LogOut className="h-3 w-3" />
                      <span>Chiqish</span>
                    </button>
                  </div>
                ) : !currentUser ? (
                  <div className="flex flex-col gap-1.5">
                    <Link
                      href="/talaba/kirish"
                      className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-sky-500 px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-sky-400 transition-colors"
                    >
                      <Lock className="h-3 w-3" />
                      <span>Talaba kirishi</span>
                    </Link>
                    <Link
                      href="/talaba/royxatdan-otish"
                      className="inline-flex items-center justify-center rounded-lg border border-sky-500/25 bg-sky-500/10 px-3 py-1.5 text-[11px] font-medium text-sky-300 hover:bg-sky-500/20 transition-colors"
                    >
                      Talaba ro‘yxatdan o‘tishi
                    </Link>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          {/* Grouped Vertical Navigation */}
          <nav className="rounded-3xl skeuo-card p-3 space-y-4">
            {STUDENT_NAV_GROUPS.map((group) => (
              <div key={group.title} className="space-y-1">
                <div className="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                  {group.title}
                </div>
                {group.items.map((item) => {
                  const isActive = item.exact
                    ? pathname === item.href
                    : pathname?.startsWith(item.href);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={isActive ? "page" : undefined}
                      className={`flex items-center gap-2.5 rounded-lg border-l-2 px-2.5 py-2 text-xs font-medium transition-colors ${
                        isActive
                          ? "border-sky-400 bg-sky-500/10 text-sky-300 font-semibold"
                          : "border-transparent text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200"
                      }`}
                    >
                      <Icon
                        className={`h-3.5 w-3.5 shrink-0 ${
                          isActive ? "text-sky-400" : "text-zinc-500"
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            ))}
          </nav>
        </aside>

        {/* Mobile / Tablet Compact Horizontal Navigation */}
        <nav
          aria-label="Talaba bo‘limlari"
          className="flex lg:hidden items-center gap-1.5 overflow-x-auto pb-2 border-b border-white/[0.08] text-xs"
        >
          {flatItems.map((item) => {
            const isActive = item.exact
              ? pathname === item.href
              : pathname?.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg border px-3 py-1.5 font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? "border-sky-500/35 bg-sky-500/10 text-sky-300"
                    : "border-white/[0.06] bg-surface-card text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Main Workspace Content */}
        <div className="min-w-0 flex-1">
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
