"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Search,
  Briefcase,
  Building2,
  Lock,
  FileText,
  BookOpen,
  User,
  GraduationCap,
  ShieldAlert,
  ChevronDown,
  LogOut,
  Compass,
  FileCheck2,
  ArrowUpRight,
} from "lucide-react";
import { AuthUser, fetchAuthMe, logoutUser } from "@/lib/api";
import {
  isAcademicOnlyRoles,
  isEmployerOnlyRoles,
  isOperatorOnlyRoles,
  isStudentOnlyRoles,
  resolvePortalDashboard,
} from "@/lib/roles";

type WorkspacePersona = "PUBLIC" | "CANDIDATE" | "EMPLOYER" | "UNIVERSITY" | "OPERATOR";

interface NavItem {
  href: string;
  label: string;
  icon: typeof Search;
  exact?: boolean;
}

interface PersonaTheme {
  id: WorkspacePersona;
  label: string;
  badgeText: string;
  badgeClass: string;
  brandBoxClass: string;
  activeNavClass: string;
  accentTopBorder: string;
  homeHref: string;
  links: NavItem[];
}

const PERSONA_THEMES: Record<WorkspacePersona, PersonaTheme> = {
  PUBLIC: {
    id: "PUBLIC",
    label: "Karyera Katalogi",
    badgeText: "v1.4",
    badgeClass: "bg-white/[0.06] text-primary border-primary/25",
    brandBoxClass: "bg-primary text-white",
    activeNavClass: "border-primary/30 bg-primary/10 text-primary",
    accentTopBorder: "border-b border-white/[0.08]",
    homeHref: "/",
    links: [
      { href: "/", label: "E’lonlar", icon: Search, exact: true },
      { href: "/haqida", label: "Platforma haqida", icon: Compass },
      { href: "/maxfiylik", label: "Maxfiylik", icon: FileCheck2 },
      { href: "/shartlar", label: "Shartlar", icon: FileText },
    ],
  },
  CANDIDATE: {
    id: "CANDIDATE",
    label: "Talaba Kabineti",
    badgeText: "Talaba & Nomzod",
    badgeClass: "bg-sky-500/10 text-sky-400 border-sky-500/25",
    brandBoxClass: "bg-sky-600 text-white",
    activeNavClass: "border-sky-500/30 bg-sky-500/10 text-sky-400",
    accentTopBorder: "border-b border-sky-500/20",
    homeHref: "/nomzod",
    links: [
      { href: "/nomzod", label: "Kabinetim", icon: User, exact: true },
      { href: "/nomzod/arizalar", label: "Arizalar", icon: FileText },
      { href: "/nomzod/kundalik", label: "Kundalik & E-Imzo", icon: BookOpen },
      { href: "/nomzod/shartnomalar", label: "Shartnomalar", icon: FileCheck2 },
      { href: "/", label: "E’lonlar", icon: Search, exact: true },
    ],
  },
  EMPLOYER: {
    id: "EMPLOYER",
    label: "Korxona HR",
    badgeText: "Korxona HR & Mentor",
    badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/25",
    brandBoxClass: "bg-emerald-600 text-white",
    activeNavClass: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    accentTopBorder: "border-b border-emerald-500/25",
    homeHref: "/employer",
    links: [
      { href: "/employer", label: "HR Boshqaruv Markazi", icon: Briefcase, exact: true },
      { href: "/", label: "Ommaviy E’lonlar", icon: Search, exact: true },
      { href: "/haqida", label: "Korxona Qo‘llanmasi", icon: Compass },
    ],
  },
  UNIVERSITY: {
    id: "UNIVERSITY",
    label: "OTM Dekanat",
    badgeText: "OTM Akademik Portal",
    badgeClass: "bg-indigo-500/10 text-indigo-400 border-indigo-500/25",
    brandBoxClass: "bg-indigo-600 text-white",
    activeNavClass: "border-indigo-500/30 bg-indigo-500/10 text-indigo-400",
    accentTopBorder: "border-b border-indigo-500/25",
    homeHref: "/university",
    links: [
      { href: "/university", label: "Dekanat & Nazorat", icon: GraduationCap, exact: true },
      { href: "/", label: "Katalog", icon: Search, exact: true },
      { href: "/shartlar", label: "Reglament", icon: FileText },
    ],
  },
  OPERATOR: {
    id: "OPERATOR",
    label: "SOC Terminal",
    badgeText: "SOC AUDIT",
    badgeClass: "bg-amber-500/10 text-amber-400 border-amber-500/30 font-mono",
    brandBoxClass: "bg-amber-600 text-zinc-950",
    activeNavClass: "border-amber-500/35 bg-amber-500/10 text-amber-400",
    accentTopBorder: "border-b border-amber-500/25",
    homeHref: "/operator",
    links: [
      { href: "/operator", label: "SOC Nazorat", icon: ShieldAlert, exact: true },
      { href: "/", label: "Katalog", icon: Search, exact: true },
      { href: "/maxfiylik", label: "Maxfiylik", icon: Lock },
    ],
  },
};

function isStudentOnlyUser(user: AuthUser | null): boolean {
  return Boolean(user && isStudentOnlyRoles(user.roles));
}

function resolvePersonaFromRouteAndUser(
  pathname: string | null,
  user: AuthUser | null
): WorkspacePersona {
  if (pathname?.startsWith("/nomzod") || pathname?.startsWith("/talaba")) return "CANDIDATE";
  if (pathname?.startsWith("/employer") || pathname?.startsWith("/korxona")) return "EMPLOYER";
  if (pathname?.startsWith("/university") || pathname?.startsWith("/universitet")) return "UNIVERSITY";
  if (pathname?.startsWith("/operator")) return "OPERATOR";

  // Keep public storefront clean when browsing public pages,
  // while still letting resolveUserDashboard give a smart shortcut.
  void user;
  return "PUBLIC";
}

function getDashboardForRoles(roles: string[]): { href: string; label: string; badgeClass: string } {
  return resolvePortalDashboard(roles);
}

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [portalsOpen, setPortalsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;
    const syncAuth = () => {
      fetchAuthMe()
        .then((u) => {
          if (mounted) setCurrentUser(u);
        })
        .catch(() => {
          if (mounted) setCurrentUser(null);
        });
    };

    syncAuth();
    window.addEventListener("flexbridge:auth-changed", syncAuth);
    window.addEventListener("focus", syncAuth);
    return () => {
      mounted = false;
      window.removeEventListener("flexbridge:auth-changed", syncAuth);
      window.removeEventListener("focus", syncAuth);
    };
  }, [pathname]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setPortalsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const isAuthPage =
    pathname === "/kirish" ||
    pathname === "/royxatdan-otish" ||
    Boolean(pathname?.startsWith("/talaba/")) ||
    Boolean(pathname?.startsWith("/korxona/")) ||
    Boolean(pathname?.startsWith("/universitet/")) ||
    Boolean(pathname?.startsWith("/operator/"));
  const personaKey = resolvePersonaFromRouteAndUser(pathname, currentUser);
  const theme = PERSONA_THEMES[personaKey];
  const userDashboard = currentUser ? getDashboardForRoles(currentUser.roles) : null;
  const hidePortalSwitcher =
    personaKey === "CANDIDATE" ||
    isStudentOnlyUser(currentUser) ||
    personaKey === "EMPLOYER" ||
    Boolean(currentUser && isEmployerOnlyRoles(currentUser.roles)) ||
    personaKey === "UNIVERSITY" ||
    Boolean(currentUser && isAcademicOnlyRoles(currentUser.roles)) ||
    personaKey === "OPERATOR" ||
    Boolean(currentUser && isOperatorOnlyRoles(currentUser.roles));
  const loginHref =
    personaKey === "CANDIDATE"
      ? "/talaba/kirish"
      : personaKey === "EMPLOYER"
        ? "/korxona/kirish"
        : personaKey === "UNIVERSITY"
          ? "/universitet/kirish"
          : personaKey === "OPERATOR"
            ? "/operator/kirish"
            : "/kirish";
  const registerHref =
    personaKey === "CANDIDATE"
      ? "/talaba/royxatdan-otish"
      : personaKey === "EMPLOYER"
        ? "/korxona/royxatdan-otish"
        : personaKey === "UNIVERSITY"
          ? "/universitet/royxatdan-otish"
          : "/royxatdan-otish";

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    window.dispatchEvent(new Event("flexbridge:auth-changed"));
    router.refresh();
  };

  return (
    <header
      className={`sticky top-0 z-50 flex min-h-14 w-full flex-wrap items-center justify-between gap-2 ${theme.accentTopBorder} bg-surface/95 px-4 py-2 backdrop-blur-md md:px-8`}
    >
      {/* Left: Role-Branded Identity */}
      <div className="flex items-center gap-4">
        <Link href="/" className="flex items-center gap-2.5 select-none group">
          <div
            className={`w-7 h-7 rounded flex items-center justify-center shadow-sm font-bold text-xs tracking-wider transition-colors ${theme.brandBoxClass}`}
          >
            FB
          </div>
          <span className="font-heading font-bold text-base tracking-tight text-white group-hover:text-zinc-200 transition-colors">
            FlexBridge
          </span>
        </Link>
        <span
          className={`hidden sm:inline-flex items-center text-[10px] font-semibold uppercase px-2 py-0.5 rounded border tracking-wider ${theme.badgeClass}`}
        >
          {theme.badgeText}
        </span>
      </div>

      {/* Center: Persona-Specific Navigation */}
      {!isAuthPage ? (
        <nav
          aria-label="Asosiy bo‘limlar"
          className="order-3 flex w-full items-center gap-1 overflow-x-auto md:order-none md:w-auto"
        >
          {theme.links.map((item) => {
            const isActive = item.exact
              ? pathname === item.href
              : pathname?.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                  isActive
                    ? theme.activeNavClass
                    : "border-transparent text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200"
                }`}
              >
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}

          {/* Portal Switcher Dropdown for non-student & public visitors */}
          {!hidePortalSwitcher && (
          <div className="relative shrink-0" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setPortalsOpen((prev) => !prev)}
              aria-expanded={portalsOpen}
              className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors ${
                portalsOpen
                  ? "border-white/20 bg-white/[0.08] text-white"
                  : "border-transparent text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200"
              }`}
            >
              <span>Portallar</span>
              <ChevronDown
                className={`h-3.5 w-3.5 transition-transform ${portalsOpen ? "rotate-180" : ""}`}
              />
            </button>

            {portalsOpen && (
              <div className="absolute left-0 md:right-0 md:left-auto mt-2 w-60 rounded-xl border border-white/[0.1] bg-[#121214] p-1.5 shadow-2xl z-50">
                <div className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                  Rol bo‘yicha portallar
                </div>
                <Link
                  href="/nomzod"
                  onClick={() => setPortalsOpen(false)}
                  className="flex items-center justify-between rounded-lg px-2.5 py-2 text-xs text-zinc-300 hover:bg-sky-500/10 hover:text-sky-300 transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <User className="h-3.5 w-3.5 text-sky-400" />
                    <span>Talaba / Nomzod</span>
                  </span>
                  <ArrowUpRight className="h-3 w-3 opacity-50" />
                </Link>
                <Link
                  href="/employer"
                  onClick={() => setPortalsOpen(false)}
                  className="flex items-center justify-between rounded-lg px-2.5 py-2 text-xs text-zinc-300 hover:bg-emerald-500/10 hover:text-emerald-300 transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <Briefcase className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Korxona / Ish Beruvchi</span>
                  </span>
                  <ArrowUpRight className="h-3 w-3 opacity-50" />
                </Link>
                <Link
                  href="/university"
                  onClick={() => setPortalsOpen(false)}
                  className="flex items-center justify-between rounded-lg px-2.5 py-2 text-xs text-zinc-300 hover:bg-indigo-500/10 hover:text-indigo-300 transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <Building2 className="h-3.5 w-3.5 text-indigo-400" />
                    <span>Universitet / OTM</span>
                  </span>
                  <ArrowUpRight className="h-3 w-3 opacity-50" />
                </Link>
                <div className="my-1 border-t border-white/[0.06]" />
                <Link
                  href="/operator"
                  onClick={() => setPortalsOpen(false)}
                  className="flex items-center justify-between rounded-lg px-2.5 py-2 text-xs text-zinc-400 hover:bg-amber-500/10 hover:text-amber-300 transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <Lock className="h-3.5 w-3.5 text-amber-400" />
                    <span>Operator SOC</span>
                  </span>
                  <ArrowUpRight className="h-3 w-3 opacity-50" />
                </Link>
              </div>
            )}
          </div>
          )}
        </nav>
      ) : (
        <nav aria-label="Avtorizatsiya havolalari" className="hidden md:flex items-center gap-2">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200 transition-colors"
          >
            <Search className="h-3.5 w-3.5" />
            <span>E’lonlar katalogi</span>
          </Link>
          <Link
            href="/haqida"
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200 transition-colors"
          >
            <Compass className="h-3.5 w-3.5" />
            <span>Yordam</span>
          </Link>
        </nav>
      )}

      {/* Right: Auth / Session Controls */}
      <div className="flex items-center gap-2">
        {currentUser && userDashboard ? (
          <>
            {pathname !== userDashboard.href && (
              <Link
                href={userDashboard.href}
                className={`hidden sm:inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-colors ${userDashboard.badgeClass}`}
              >
                <span>{userDashboard.label}</span>
              </Link>
            )}
            <span className="hidden md:inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.03] px-2.5 py-1.5 text-[11px] font-mono text-zinc-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              <span>{currentUser.roles[0] || "USER"}</span>
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-rose-500/10 hover:border-rose-500/25 hover:text-rose-300 transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Chiqish</span>
            </button>
          </>
        ) : (
          <>
            <Link
              href={loginHref}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-300 hover:text-white hover:bg-white/[0.04] transition-colors"
            >
              <Lock className="h-3.5 w-3.5" />
              <span>Kirish</span>
            </Link>
            {personaKey !== "OPERATOR" && (
              <Link
                href={registerHref}
                className="inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary-hover transition-colors shadow-sm"
              >
                <span>Ro‘yxatdan o‘tish</span>
              </Link>
            )}
          </>
        )}
      </div>
    </header>
  );
}
