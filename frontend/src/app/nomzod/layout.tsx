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
import ProfileCard from "@/components/profile/ProfileCard";

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
        {/* Desktop Student Workspace Rail: white panel, ink active pill, identity card at the bottom */}
        <aside
          aria-label="Talaba kabineti navigatsiyasi"
          className="hidden lg:flex lg:w-[248px] shrink-0 flex-col gap-4 sticky top-20"
        >
          <nav className="fb-panel skeuo-card p-3 space-y-3">
            {STUDENT_NAV_GROUPS.map((group) => (
              <div key={group.title} className="space-y-0.5">
                <div className="px-3 pb-1 pt-1.5 text-[11px] font-medium text-[var(--fb-ink-muted)]">
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
                      className="fb-nav-item"
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            ))}
          </nav>

          {authResolved && currentUser && isCandidate ? (
            <ProfileCard
              name={currentUser.display_name}
              roleLabel="Talaba · nomzod"
              securityHref="/nomzod/xavfsizlik"
              onLogout={handleStudentSwitchLogout}
            />
          ) : authResolved && !currentUser ? (
            <div className="fb-panel skeuo-card p-4 flex flex-col gap-2 text-center">
              <span className="fb-avatar mx-auto h-12 w-12 text-sm" aria-hidden="true">
                <GraduationCap className="h-5 w-5" />
              </span>
              <p className="text-xs text-[var(--fb-ink-muted)]">Profilingizni ko‘rish uchun kiring</p>
              <Link
                href="/talaba/kirish"
                className="inline-flex items-center justify-center gap-1.5 rounded-full skeuo-btn-obsidian px-3 py-2 text-xs font-semibold"
              >
                <Lock className="h-3.5 w-3.5" />
                <span>Talaba kirishi</span>
              </Link>
              <Link
                href="/talaba/royxatdan-otish"
                className="inline-flex items-center justify-center rounded-full skeuo-btn-secondary px-3 py-2 text-xs font-semibold"
              >
                Ro‘yxatdan o‘tish
              </Link>
            </div>
          ) : null}
        </aside>

        {/* Mobile / Tablet Compact Horizontal Navigation */}
        <nav
          aria-label="Talaba bo‘limlari"
          className="flex lg:hidden items-center gap-1.5 overflow-x-auto pb-2 border-b border-[var(--fb-border)] text-xs no-scrollbar"
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
                className="fb-nav-item shrink-0 !py-1.5 text-xs"
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
