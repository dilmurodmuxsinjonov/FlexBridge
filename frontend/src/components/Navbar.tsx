"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldCheck,
  Search,
  Bell,
  Briefcase,
  GraduationCap,
  Building2,
  Lock,
  CheckCircle2,
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  const navLinks = [
    { href: "/", label: "Talaba Portali", icon: GraduationCap },
    { href: "/employer", label: "Ish Beruvchi (HR)", icon: Briefcase },
    { href: "/university", label: "Universitet (OTM)", icon: Building2 },
    { href: "/operator", label: "Operator (SOC)", icon: Lock },
  ];

  return (
    <header className="w-full h-14 px-4 md:px-8 flex items-center justify-between border-b border-white/[0.08] bg-surface sticky top-0 z-50 backdrop-blur-md">
      {/* Brand Identity */}
      <div className="flex items-center gap-6">
        <Link href="/" className="flex items-center gap-2.5 select-none group">
          <div className="w-7 h-7 rounded bg-primary flex items-center justify-center text-white shadow-sm font-bold text-sm tracking-wider">
            FB
          </div>
          <span className="font-heading font-bold text-base tracking-tight text-white group-hover:text-primary transition-colors">
            FlexBridge
          </span>
          <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-white/[0.06] text-primary border border-primary/20 tracking-wider">
            v1.4
          </span>
        </Link>

        {/* Portal Switcher Tabs */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname?.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-all ${
                  isActive
                    ? "bg-primary/10 text-primary border border-primary/30"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
                {isActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Trailing Controls & Live Status */}
      <div className="flex items-center gap-3">
        {/* Live HEMIS / API Status Dot */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container border border-white/[0.06] text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-zinc-300 font-mono text-[11px]">HEMIS v3.2 Sinx</span>
        </div>

        {/* Search Shortcut */}
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded bg-surface-container border border-white/[0.06] text-zinc-400 text-xs">
          <Search className="w-3.5 h-3.5" />
          <span>Izlash</span>
          <kbd className="px-1.5 py-0.5 rounded bg-zinc-800 text-[10px] font-mono text-zinc-300 border border-white/[0.08]">
            Ctrl+K
          </kbd>
        </div>

        {/* Notifications */}
        <button
          type="button"
          aria-label="Xabarlar"
          className="relative p-1.5 rounded text-zinc-400 hover:text-white hover:bg-white/[0.04] transition-colors"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-surface" />
        </button>

        <div className="h-4 w-px bg-white/[0.08]" />

        {/* Profile / Security Clearance Pill */}
        <div className="flex items-center gap-2 pl-1 cursor-pointer select-none">
          <div className="w-7 h-7 rounded bg-zinc-800 border border-white/[0.1] flex items-center justify-center text-xs font-semibold text-primary">
            DR
          </div>
          <div className="hidden xl:flex flex-col text-left">
            <span className="text-xs font-semibold text-zinc-200 leading-tight">
              D. Rustamov
            </span>
            <span className="text-[10px] text-zinc-400 font-mono flex items-center gap-0.5">
              <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" /> L4 Clearance
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
