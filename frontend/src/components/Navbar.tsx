"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Search,
  Briefcase,
  Building2,
  Lock,
  FileText,
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  const navLinks = [
    { href: "/", label: "E’lonlar", icon: Search },
    { href: "/nomzod/arizalar", label: "Arizalarim", icon: FileText },
    { href: "/employer", label: "Ish beruvchi", icon: Briefcase },
    { href: "/university", label: "Universitet", icon: Building2 },
    { href: "/operator", label: "Operator", icon: Lock },
  ];

  return (
    <>
    <header className="sticky top-0 z-50 flex min-h-14 w-full flex-wrap items-center justify-between gap-2 border-b border-white/[0.08] bg-surface px-4 py-2 backdrop-blur-md md:px-8">
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
      </div>

      <nav aria-label="Asosiy bo‘limlar" className="order-3 flex w-full items-center gap-1 overflow-x-auto md:order-none md:w-auto">
        {navLinks.map((item) => {
          const isActive = item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href} aria-current={isActive ? "page" : undefined}
              className={`inline-flex shrink-0 items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors ${isActive ? "border border-primary/30 bg-primary/10 text-primary" : "text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200"}`}>
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <span className="hidden rounded border border-white/[0.08] px-2.5 py-1 text-[11px] text-zinc-400 lg:inline-flex">R1 sinov interfeysi</span>
    </header>
    </>
  );
}
