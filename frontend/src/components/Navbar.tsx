"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Briefcase,
  Search,
  User,
  GraduationCap,
  ShieldAlert,
  Lock,
  ChevronDown,
  FileText,
  BookOpen,
  LogOut,
  Compass,
  FileCheck2,
  ArrowUpRight,
  Sun,
  Moon,
  ArrowUp,
  Bookmark,
  Award,
  Bell,
  ShieldCheck,
  HelpCircle,
  Users,
  Building2,
  CreditCard,
  CalendarDays,
  BarChart3,
  Download,
  KeyRound,
  LifeBuoy,
  Sparkles,
  LayoutDashboard,
  MessageCircle,
} from "lucide-react";
import { initials, uzDate } from "@/lib/person";
import { AuthUser, fetchAuthMe, logoutUser } from "@/lib/api";
import ChatNavButton from "@/components/chat/ChatNavButton";
import {
  isAcademicOnlyRoles,
  isEmployerOnlyRoles,
  isOperatorOnlyRoles,
  isStudentOnlyRoles,
  resolvePortalDashboard,
} from "@/lib/roles";
import { useSkeuoTheme } from "@/components/ThemeProvider";
import { useGlider } from "@/lib/motion";

type WorkspacePersona = "PUBLIC" | "CANDIDATE" | "EMPLOYER" | "UNIVERSITY" | "OPERATOR";

interface NavItem {
  id: string;
  href: string;
  label: string;
  shortLabel: string;
  icon: typeof Search;
  exact?: boolean;
  tabId?: string;
}

interface PersonaTheme {
  id: WorkspacePersona;
  label: string;
  greetingPrefix: string;
  brandName: string;
  brandAccent: string;
  subtitle: string;
  badgeText: string;
  badgeClass: string;
  accentHex: string;
  islandDotClass: string;
  icon: typeof Briefcase;
  links: NavItem[];
  dockTools: NavItem[];
}

const PERSONA_THEMES: Record<WorkspacePersona, PersonaTheme> = {
  PUBLIC: {
    id: "PUBLIC",
    label: "Karyera Katalogi",
    greetingPrefix: "FlexBridge",
    brandName: "FlexBridge",
    brandAccent: "text-[#D95F2B]",
    subtitle: "Dual ta’lim & amaliyot ekotizimi",
    badgeText: "Ommaviy",
    badgeClass: "border-[#D95F2B]/30 bg-[#D95F2B]/12 text-[#D95F2B]",
    accentHex: "#D95F2B",
    islandDotClass: "bg-[#D95F2B] shadow-[0_0_8px_rgba(217,95,43,0.8)]",
    icon: Briefcase,
    links: [
      { id: "pub-home", href: "/", label: "E’lonlar", shortLabel: "E’lonlar", icon: Search, exact: true },
      { id: "pub-about", href: "/haqida", label: "Platforma haqida", shortLabel: "Platforma", icon: Compass },
      { id: "pub-privacy", href: "/maxfiylik", label: "Maxfiylik", shortLabel: "Maxfiylik", icon: FileCheck2 },
      { id: "pub-terms", href: "/shartlar", label: "Shartlar", shortLabel: "Shartlar", icon: FileText },
    ],
    dockTools: [
      { id: "pub-home", href: "/", label: "E’lonlar katalogi", shortLabel: "Katalog", icon: Search, exact: true },
      { id: "pub-about", href: "/haqida", label: "Platforma haqida", shortLabel: "Haqida", icon: Compass },
      { id: "pub-privacy", href: "/maxfiylik", label: "Maxfiylik siyosati", shortLabel: "Maxfiylik", icon: FileCheck2 },
      { id: "pub-terms", href: "/shartlar", label: "Foydalanish shartlari", shortLabel: "Shartlar", icon: FileText },
    ],
  },
  CANDIDATE: {
    id: "CANDIDATE",
    label: "Talaba Kabineti",
    greetingPrefix: "Salom",
    brandName: "FlexBridge",
    brandAccent: "text-[#0EA5E9]",
    subtitle: "Amaliyot, E-Imzo & Shartnomalar",
    badgeText: "Talaba",
    badgeClass: "border-sky-500/35 bg-sky-500/12 text-sky-600 dark:text-sky-300",
    accentHex: "#0EA5E9",
    islandDotClass: "bg-sky-400 shadow-[0_0_8px_rgba(56,189,248,0.85)]",
    icon: User,
    links: [
      { id: "cand-home", href: "/nomzod", label: "Kabinetim", shortLabel: "Kabinet", icon: User, exact: true },
      { id: "cand-apps", href: "/nomzod/arizalar", label: "Arizalar", shortLabel: "Arizalar", icon: FileText },
      { id: "cand-log", href: "/nomzod/kundalik", label: "Kundalik & E-Imzo", shortLabel: "Kundalik", icon: BookOpen },
      { id: "cand-contracts", href: "/nomzod/shartnomalar", label: "Shartnomalar", shortLabel: "Shartnoma", icon: FileCheck2 },
      { id: "cand-jobs", href: "/", label: "E’lonlar", shortLabel: "E’lonlar", icon: Search, exact: true },
    ],
    dockTools: [
      { id: "cand-home", href: "/nomzod", label: "Asosiy kabinet", shortLabel: "Kabinet", icon: User, exact: true },
      { id: "cand-apps", href: "/nomzod/arizalar", label: "Arizalarim", shortLabel: "Arizalar", icon: FileText },
      { id: "cand-saved", href: "/nomzod/saqlanganlar", label: "Saqlangan vakansiyalar", shortLabel: "Saqlangan", icon: Bookmark },
      { id: "cand-log", href: "/nomzod/kundalik", label: "Amaliyot kundaligi", shortLabel: "Kundalik", icon: BookOpen },
      { id: "cand-contracts", href: "/nomzod/shartnomalar", label: "Shartnomalar", shortLabel: "Shartnoma", icon: FileCheck2 },
      { id: "cand-grades", href: "/nomzod/baholar", label: "Kredit & Baholar", shortLabel: "Baholar", icon: Award },
      { id: "cand-alerts", href: "/nomzod/bildirishnomalar", label: "Bildirishnomalar", shortLabel: "Xabarlar", icon: Bell },
      { id: "cand-sec", href: "/nomzod/xavfsizlik", label: "Xavfsizlik", shortLabel: "Himoya", icon: ShieldCheck },
      { id: "cand-help", href: "/nomzod/yordam", label: "Yordam markazi", shortLabel: "Yordam", icon: HelpCircle },
    ],
  },
  EMPLOYER: {
    id: "EMPLOYER",
    label: "Korxona HR",
    greetingPrefix: "HR Studio",
    brandName: "FlexBridge",
    brandAccent: "text-[#10B981]",
    subtitle: "Nomzodlar Kanban, Mentorlik & Moliya",
    badgeText: "Ish beruvchi",
    badgeClass: "border-emerald-500/35 bg-emerald-500/12 text-emerald-700 dark:text-emerald-300",
    accentHex: "#10B981",
    islandDotClass: "bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.85)]",
    icon: Briefcase,
    links: [
      { id: "emp-kanban", href: "/employer", tabId: "KANBAN", label: "Kanban & Nomzodlar", shortLabel: "Kanban", icon: Briefcase, exact: true },
      { id: "emp-search", href: "/employer", tabId: "SEARCH_HUB", label: "Talaba Qidirish", shortLabel: "Qidiruv", icon: Users },
      { id: "emp-mentor", href: "/employer", tabId: "MENTOR_HUB", label: "Mentor & Hujjatlar", shortLabel: "Mentorlik", icon: BookOpen },
      { id: "emp-org", href: "/employer", tabId: "ORG_HUB", label: "Tashkilot & Filial", shortLabel: "Tashkilot", icon: Building2 },
      { id: "emp-billing", href: "/employer", tabId: "BILLING_HUB", label: "Tarif & Hisob", shortLabel: "Hisob", icon: CreditCard },
    ],
    dockTools: [
      { id: "emp-kanban", href: "/employer", tabId: "KANBAN", label: "Kanban & Vakansiyalar", shortLabel: "Kanban", icon: Briefcase, exact: true },
      { id: "emp-search", href: "/employer", tabId: "SEARCH_HUB", label: "Talabalar bazasi", shortLabel: "Talabalar", icon: Users },
      { id: "emp-mentor", href: "/employer", tabId: "MENTOR_HUB", label: "Mentor & Amaliyot nazorati", shortLabel: "Mentor", icon: BookOpen },
      { id: "emp-org", href: "/employer", tabId: "ORG_HUB", label: "Tashkilot, KYB va filiallar", shortLabel: "Tashkilot", icon: Building2 },
      { id: "emp-billing", href: "/employer", tabId: "BILLING_HUB", label: "Tariflar va Billing", shortLabel: "Moliya", icon: CreditCard },
      { id: "emp-public", href: "/", label: "Ommaviy e’lonlar", shortLabel: "Katalog", icon: Search, exact: true },
    ],
  },
  UNIVERSITY: {
    id: "UNIVERSITY",
    label: "OTM Dekanat",
    greetingPrefix: "Dekanat",
    brandName: "FlexBridge",
    brandAccent: "text-[#6366F1]",
    subtitle: "Akademik Nazorat, E-Imzo & Dars Jadvali",
    badgeText: "OTM Nazorat",
    badgeClass: "border-indigo-500/35 bg-indigo-500/12 text-indigo-700 dark:text-indigo-300",
    accentHex: "#6366F1",
    islandDotClass: "bg-indigo-400 shadow-[0_0_8px_rgba(99,102,241,0.85)]",
    icon: GraduationCap,
    links: [
      { id: "uni-queue", href: "/university", tabId: "queue", label: "Tasdiqlash navbati", shortLabel: "Navbat", icon: GraduationCap, exact: true },
      { id: "uni-assign", href: "/university", tabId: "assignments", label: "Biriktirishlar", shortLabel: "Biriktirish", icon: FileCheck2 },
      { id: "uni-docs", href: "/university", tabId: "documents", label: "Kundalik & E-Imzo", shortLabel: "Hujjatlar", icon: BookOpen },
      { id: "uni-timetable", href: "/university", tabId: "timetable", label: "Dars jadvali", shortLabel: "Jadval", icon: CalendarDays },
      { id: "uni-analytics", href: "/university", tabId: "analytics", label: "Analitika", shortLabel: "Analitika", icon: BarChart3 },
    ],
    dockTools: [
      { id: "uni-queue", href: "/university", tabId: "queue", label: "Tasdiqlash navbati", shortLabel: "Navbat", icon: GraduationCap, exact: true },
      { id: "uni-assign", href: "/university", tabId: "assignments", label: "Amaliyot biriktirishlari", shortLabel: "Biriktirish", icon: FileCheck2 },
      { id: "uni-docs", href: "/university", tabId: "documents", label: "Amaliyot hujjatlari & E-Imzo", shortLabel: "Hujjatlar", icon: BookOpen },
      { id: "uni-coord", href: "/university", tabId: "coordinator", label: "Kafedra rahbarlari", shortLabel: "Rahbarlar", icon: Users },
      { id: "uni-timetable", href: "/university", tabId: "timetable", label: "Dars jadvali boshqaruvi", shortLabel: "Jadval", icon: CalendarDays },
      { id: "uni-exports", href: "/university", tabId: "exports", label: "Eksport & HEMIS", shortLabel: "Eksport", icon: Download },
      { id: "uni-analytics", href: "/university", tabId: "analytics", label: "Dekanat analitikasi", shortLabel: "Analitika", icon: BarChart3 },
    ],
  },
  OPERATOR: {
    id: "OPERATOR",
    label: "Nazorat Markazi",
    greetingPrefix: "Operator Markazi",
    brandName: "FlexBridge",
    brandAccent: "text-[#F59E0B]",
    subtitle: "Audit, KYB Tasdiqlash & Xavfsizlik",
    badgeText: "Operator",
    badgeClass: "border-amber-500/35 bg-amber-500/12 text-amber-700 dark:text-amber-300",
    accentHex: "#F59E0B",
    islandDotClass: "bg-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.85)]",
    icon: ShieldAlert,
    links: [
      { id: "op-audit", href: "/operator", tabId: "AUDIT", label: "Audit Jurnali", shortLabel: "Audit", icon: ShieldAlert, exact: true },
      { id: "op-verif", href: "/operator", tabId: "VERIFICATION", label: "KYB Tasdiqlash", shortLabel: "KYB", icon: FileCheck2 },
      { id: "op-bg", href: "/operator", tabId: "BREAK_GLASS", label: "Favqulodda Ruxsat", shortLabel: "Favqulodda", icon: KeyRound },
      { id: "op-sup", href: "/operator", tabId: "SUPPORT_OPS", label: "Murojaatlar Markazi", shortLabel: "Murojaat", icon: LifeBuoy },
      { id: "op-fin", href: "/operator", tabId: "FINANCE", label: "Moliya Nazorati", shortLabel: "Moliya", icon: CreditCard },
    ],
    dockTools: [
      { id: "op-audit", href: "/operator", tabId: "AUDIT", label: "Tizim Audit Jurnali", shortLabel: "Audit", icon: ShieldAlert, exact: true },
      { id: "op-verif", href: "/operator", tabId: "VERIFICATION", label: "Tashkilot KYB Tekshiruvi", shortLabel: "KYB", icon: FileCheck2 },
      { id: "op-bg", href: "/operator", tabId: "BREAK_GLASS", label: "Favqulodda Kirish Nazorati", shortLabel: "Favqulodda", icon: KeyRound },
      { id: "op-sup", href: "/operator", tabId: "SUPPORT_OPS", label: "Murojaatlar & Yordam Markazi", shortLabel: "Murojaatlar", icon: LifeBuoy },
      { id: "op-fin", href: "/operator", tabId: "FINANCE", label: "Moliya va To‘lov nazorati", shortLabel: "Moliya", icon: CreditCard },
    ],
  },
};

function isStudentOnlyUser(user: AuthUser | null): boolean {
  return Boolean(user && isStudentOnlyRoles(user.roles));
}

function resolvePersonaFromRouteAndUser(
  pathname: string | null,
  currentUser: AuthUser | null
): WorkspacePersona {
  if (pathname?.startsWith("/nomzod") || pathname?.startsWith("/talaba")) return "CANDIDATE";
  if (pathname?.startsWith("/employer") || pathname?.startsWith("/korxona")) return "EMPLOYER";
  if (pathname?.startsWith("/university") || pathname?.startsWith("/universitet")) return "UNIVERSITY";
  if (pathname?.startsWith("/operator")) return "OPERATOR";

  if (currentUser) {
    if (isStudentOnlyUser(currentUser)) return "CANDIDATE";
    if (isOperatorOnlyRoles(currentUser.roles)) return "OPERATOR";
    if (isEmployerOnlyRoles(currentUser.roles)) return "EMPLOYER";
    if (isAcademicOnlyRoles(currentUser.roles)) return "UNIVERSITY";
  }
  return "PUBLIC";
}

function getDashboardForRoles(roles: string[]): { href: string; label: string; badgeClass: string } {
  // Same priority and role codes as sign-in routing (lib/roles), so staff land in their own portal.
  const dash = resolvePortalDashboard(roles);
  return { href: dash.href, label: dash.label, badgeClass: dash.badgeClass };
}

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { theme: colorMode, toggleTheme } = useSkeuoTheme();

  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [portalsOpenPath, setPortalsOpenPath] = useState<string | null>(null);
  const [portalTabState, setPortalTabState] = useState<{ path: string | null; tab: string } | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const railRef = useRef<HTMLElement>(null);
  const railGliderRef = useRef<HTMLSpanElement>(null);
  const dockRef = useRef<HTMLDivElement>(null);
  const dockGliderRef = useRef<HTMLSpanElement>(null);
  useGlider(railRef, railGliderRef);

  const portalsOpen = portalsOpenPath === pathname;
  const activePortalTab = portalTabState?.path === pathname ? portalTabState.tab : null;

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
    const onTabChanged = (ev: Event) => {
      const detail = (ev as CustomEvent<{ tab?: string }>).detail;
      if (detail?.tab) {
        setPortalTabState({ path: pathname, tab: detail.tab });
      }
    };
    window.addEventListener("flexbridge:portal-tab-changed", onTabChanged);
    return () => window.removeEventListener("flexbridge:portal-tab-changed", onTabChanged);
  }, [pathname]);

  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setPortalsOpenPath(null);
      }
    };
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  const isAuthPage =
    pathname === "/kirish" ||
    pathname === "/royxatdan-otish" ||
    Boolean(pathname?.startsWith("/talaba/")) ||
    Boolean(pathname?.startsWith("/korxona/")) ||
    Boolean(pathname?.startsWith("/universitet/")) ||
    Boolean(pathname?.startsWith("/operator/"));
  // The mobile dock only exists off the sign-in pages; attach its glider when it does.
  useGlider(dockRef, dockGliderRef, '[data-active="true"]', !isAuthPage);

  const personaKey = resolvePersonaFromRouteAndUser(pathname, currentUser);
  const theme = PERSONA_THEMES[personaKey];
  const BrandIcon = theme.icon;
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

  const defaultTabForPersona = useMemo(() => {
    if (pathname?.startsWith("/employer")) return "KANBAN";
    if (pathname?.startsWith("/university")) return "queue";
    if (pathname?.startsWith("/operator")) return "AUDIT";
    return null;
  }, [pathname]);

  const resolvedTab = activePortalTab || defaultTabForPersona;

  const isNavItemActive = (item: NavItem) => {
    if (item.tabId) {
      if (pathname !== item.href) return false;
      return resolvedTab === item.tabId;
    }
    if (item.exact) return pathname === item.href;
    return Boolean(pathname?.startsWith(item.href));
  };

  const handleNavAction = (item: NavItem) => {
    if (item.tabId) {
      setPortalTabState({ path: pathname, tab: item.tabId });
      if (pathname !== item.href) {
        router.push(item.href);
        return;
      }
      window.dispatchEvent(
        new CustomEvent("flexbridge:dock-tab", { detail: { tab: item.tabId } })
      );
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    router.push(item.href);
  };

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    window.dispatchEvent(new Event("flexbridge:auth-changed"));
    router.refresh();
  };

  // Left rail: quick destinations that exist for this kind of visitor.
  const railItems: { href: string; label: string; icon: typeof Search; exact?: boolean }[] = currentUser
    ? [
        ...(userDashboard ? [{ href: userDashboard.href, label: userDashboard.label, icon: LayoutDashboard, exact: true }] : []),
        { href: "/", label: "E’lonlar katalogi", icon: Search, exact: true },
        { href: "/xabarlar", label: "Xabarlar", icon: MessageCircle },
        ...(isStudentOnlyUser(currentUser)
          ? [
              { href: "/nomzod/jadval", label: "O‘quv jadvali", icon: CalendarDays },
              { href: "/nomzod/bildirishnomalar", label: "Bildirishnomalar", icon: Bell },
            ]
          : []),
      ]
    : [
        { href: "/", label: "E’lonlar katalogi", icon: Search, exact: true },
        { href: "/haqida", label: "Platforma haqida", icon: Compass },
        { href: "/maxfiylik", label: "Maxfiylik siyosati", icon: FileCheck2 },
        { href: "/shartlar", label: "Foydalanish shartlari", icon: FileText },
      ];
  const statusText = currentUser ? `${theme.label} · ${uzDate()}` : `${theme.label} · ochiq katalog`;

  // Guests (including on role-specific sign-in pages) just see the brand.
  const ownFirstName = currentUser?.display_name?.trim().split(/\s+/)[0];
  const headerGreeting = currentUser
    ? `${theme.greetingPrefix}, ${theme.greetingPrefix === "Salom" && ownFirstName ? ownFirstName : theme.badgeText}`
    : "FlexBridge";

  return (
    <>
      {/* Device shell top capsule (Issue #263): identity left, inset status well, chrome knobs right */}
      <header className="sticky top-0 z-40 w-full px-3 pt-3 pb-3 sm:px-6 lg:pl-[6.5rem]">
        <div data-skeuo-dark="true" className="fb-topbar skeuo-obsidian">
          <Link href={currentUser && userDashboard ? userDashboard.href : "/"} className="group flex min-w-0 items-center gap-2.5 pr-2">
            <span className="fb-topbar-avatar transition-transform group-hover:scale-105" aria-hidden="true">
              {currentUser ? initials(currentUser.display_name, theme.badgeText.slice(0, 2)) : <BrandIcon className="h-4 w-4" />}
            </span>
            <span className="flex min-w-0 flex-col leading-none">
              <span className="truncate font-display text-sm font-semibold tracking-tight text-white">{headerGreeting}</span>
              <span className="mt-1 hidden truncate text-[10px] font-medium text-zinc-400 sm:block">{theme.subtitle}</span>
            </span>
          </Link>

          <div className="hidden min-w-0 flex-1 justify-center md:flex">
            <div className="fb-topbar-well w-full max-w-[480px]">
              <span className="fb-orb" aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate font-mono text-[11.5px] text-zinc-200">
                {statusText}
                <span className="ml-0.5 inline-block h-3 w-px animate-pulse bg-zinc-300 align-middle" aria-hidden="true" />
              </span>
                {!isAuthPage && !hidePortalSwitcher && (
                  <div className="relative pl-2 border-l border-white/10" ref={dropdownRef}>
                    <motion.button
                      type="button"
                      whileTap={{ scale: 0.96 }}
                      onClick={() => setPortalsOpenPath((prev) => (prev === pathname ? null : pathname))}
                      aria-expanded={portalsOpen}
                      className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold text-zinc-200 hover:text-white hover:bg-white/10 transition-colors"
                    >
                      <Sparkles className="w-3 h-3 text-[#D95F2B]" />
                      <span>Portallar</span>
                      <ChevronDown
                        className={`h-3 w-3 transition-transform duration-200 ${portalsOpen ? "rotate-180" : ""}`}
                      />
                    </motion.button>

                    <AnimatePresence>
                      {portalsOpen && (
                        <motion.div
                          initial={{ opacity: 0, y: 6, scale: 0.97 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: 6, scale: 0.97 }}
                          transition={{ duration: 0.16 }}
                          className="absolute left-1/2 -translate-x-1/2 top-full mt-3 w-64 rounded-2xl skeuo-card p-2 z-50 text-left"
                          data-skeuo-dark={colorMode === "dark" ? "true" : undefined}
                        >
                          <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-[var(--fb-ink-muted)]">
                            Maxsus Rol Kabinetlari
                          </div>
                          <Link
                            href="/nomzod"
                            onClick={() => setPortalsOpenPath(null)}
                            className="flex items-center justify-between px-3 py-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                          >
                            <span className="flex items-center gap-2 text-xs font-semibold text-[var(--fb-ink)]">
                              <User className="h-3.5 w-3.5 text-sky-500" />
                              Talaba Kabineti
                            </span>
                            <ArrowUpRight className="h-3.5 w-3.5 text-[var(--fb-ink-muted)]" />
                          </Link>
                          <Link
                            href="/employer"
                            onClick={() => setPortalsOpenPath(null)}
                            className="flex items-center justify-between px-3 py-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                          >
                            <span className="flex items-center gap-2 text-xs font-semibold text-[var(--fb-ink)]">
                              <Briefcase className="h-3.5 w-3.5 text-emerald-500" />
                              Korxona HR Kabineti
                            </span>
                            <ArrowUpRight className="h-3.5 w-3.5 text-[var(--fb-ink-muted)]" />
                          </Link>
                          <Link
                            href="/university"
                            onClick={() => setPortalsOpenPath(null)}
                            className="flex items-center justify-between px-3 py-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                          >
                            <span className="flex items-center gap-2 text-xs font-semibold text-[var(--fb-ink)]">
                              <GraduationCap className="h-3.5 w-3.5 text-indigo-500" />
                              Universitet Dekanati
                            </span>
                            <ArrowUpRight className="h-3.5 w-3.5 text-[var(--fb-ink-muted)]" />
                          </Link>
                          <div className="my-1 border-t border-[var(--fb-border)]" />
                          <Link
                            href="/operator"
                            onClick={() => setPortalsOpenPath(null)}
                            className="flex items-center justify-between px-3 py-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                          >
                            <span className="flex items-center gap-2 text-xs font-semibold text-[var(--fb-ink)]">
                              <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
                              Platforma Operator Terminal
                            </span>
                            <ArrowUpRight className="h-3.5 w-3.5 text-[var(--fb-ink-muted)]" />
                          </Link>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
            <button
              type="button"
              onClick={toggleTheme}
              title={colorMode === "light" ? "Qorong‘i rejimga o‘tish" : "Yorug‘ rejimga o‘tish"}
              aria-label="Rang mavzusini almashtirish"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full skeuo-btn-secondary lg:hidden"
            >
              {colorMode === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            </button>

            {currentUser && <ChatNavButton active={pathname?.startsWith("/xabarlar") ?? false} />}

            {currentUser && userDashboard ? (
              <>
                {pathname !== userDashboard.href && (
                  <Link href={userDashboard.href} className="fb-topbar-chip hidden items-center sm:inline-flex">
                    <LayoutDashboard className="h-3.5 w-3.5" />
                    <span>{userDashboard.label}</span>
                  </Link>
                )}
                <button
                  type="button"
                  onClick={handleLogout}
                  title="Tizimdan chiqish"
                  aria-label="Tizimdan chiqish"
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full skeuo-btn-secondary lg:hidden"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </>
            ) : (
              <>
                <Link href={loginHref} className="fb-topbar-chip inline-flex items-center">
                  <Lock className="h-3.5 w-3.5" />
                  <span>Kirish</span>
                </Link>
                {personaKey !== "OPERATOR" && (
                  <Link href={registerHref} className="fb-topbar-chip fb-topbar-chip-accent inline-flex items-center">
                    <span>Ro‘yxatdan o‘tish</span>
                  </Link>
                )}
              </>
            )}
          </div>
        </div>
      </header>

      {/* Floating left rail with chrome knobs (desktop) */}
      <nav ref={railRef} aria-label="Tezkor amallar" data-skeuo-dark="true" className="fb-rail skeuo-obsidian hidden lg:flex">
        <span className="fb-goo" aria-hidden="true">
          <span ref={railGliderRef} className="fb-glider fb-glider-knob" />
        </span>
        {railItems.map((item) => {
          const Icon = item.icon;
          const active = item.exact ? pathname === item.href : Boolean(pathname?.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-label={item.label}
              data-tip={item.label}
              aria-current={active ? "page" : undefined}
              className="fb-rail-btn"
            >
              <Icon className="h-4 w-4" />
            </Link>
          );
        })}
        <span className="fb-rail-sep" aria-hidden="true" />
        <button
          type="button"
          onClick={toggleTheme}
          aria-label="Rang mavzusini almashtirish"
          data-tip={colorMode === "light" ? "Qorong‘i rejim" : "Yorug‘ rejim"}
          className="fb-rail-btn"
        >
          {colorMode === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        </button>
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          aria-label="Sahifa yuqorisiga chiqish"
          data-tip="Yuqoriga"
          className="fb-rail-btn"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
        {currentUser && (
          <button type="button" onClick={handleLogout} aria-label="Tizimdan chiqish" data-tip="Chiqish" className="fb-rail-btn">
            <LogOut className="h-4 w-4" />
          </button>
        )}
      </nav>

      {/* Bottom navigation capsule: phones and tablets only. Desktop portals use their own sidebar. */}
      {!isAuthPage && (
        <nav
          aria-label="Asosiy navigatsiya"
          className="fb-main-dock lg:hidden fixed bottom-4 left-1/2 -translate-x-1/2 z-40 flex items-center gap-1.5 sm:gap-2 max-w-[98vw] pointer-events-auto"
        >
          <div
            data-skeuo-dark="true"
            ref={dockRef}
            className="relative skeuo-obsidian rounded-full p-1 sm:p-1.5 flex items-center gap-0.5 sm:gap-1 overflow-x-auto no-scrollbar max-w-[calc(100vw-60px)] sm:max-w-none"
          >
            <span className="fb-goo" aria-hidden="true">
              <span ref={dockGliderRef} className="fb-glider fb-glider-pill" />
            </span>
            {theme.links.map((item) => {
              const Icon = item.icon;
              const active = isNavItemActive(item);
              const content = (
                <>
                  <Icon className="relative z-10 w-3.5 h-3.5 shrink-0" />
                  <span className="relative z-10 whitespace-nowrap">{item.shortLabel}</span>
                </>
              );

              if (item.tabId) {
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleNavAction(item)}
                    data-active={active ? "true" : undefined}
                    className={`relative inline-flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3.5 py-1.5 sm:py-2 rounded-full text-[10.5px] sm:text-xs font-semibold transition-colors ${
                      active ? "text-white" : "text-zinc-300 hover:text-white"
                    }`}
                  >
                    {content}
                  </button>
                );
              }

              return (
                <Link
                  key={item.id}
                  href={item.href}
                  data-active={active ? "true" : undefined}
                  aria-current={active ? "page" : undefined}
                  className={`relative inline-flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3.5 py-1.5 sm:py-2 rounded-full text-[10.5px] sm:text-xs font-semibold transition-colors ${
                    active ? "text-white" : "text-zinc-300 hover:text-white"
                  }`}
                >
                  {content}
                </Link>
              );
            })}
          </div>

          {/* Detached Circular Utility Button (Matches Video Bottom-Right Obsidian Orb) */}
          <button
            type="button"
            onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            title="Sahifa yuqorisiga chiqish"
            aria-label="Yuqoriga chiqish"
            data-skeuo-dark="true"
            className="w-10 h-10 sm:w-11 sm:h-11 rounded-full skeuo-obsidian flex items-center justify-center text-white shrink-0"
          >
            <ArrowUp className="w-4 h-4 text-white" />
          </button>
        </nav>
      )}
    </>
  );
}
