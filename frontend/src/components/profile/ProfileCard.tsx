"use client";

import React, { useId, useState } from "react";
import Link from "next/link";
import { ChevronDown, LogOut, Shield } from "lucide-react";
import { initials } from "@/lib/person";

export interface ProfileCardProps {
  name?: string | null;
  roleLabel: string;
  securityHref?: string;
  onLogout?: () => void;
}

/**
 * Sidebar identity card: large initials avatar, name, role and a small
 * account menu. The menu is a disclosure (button + region), not a popover,
 * so it works the same with keyboard, touch and screen readers.
 */
export default function ProfileCard({ name, roleLabel, securityHref, onLogout }: ProfileCardProps) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const shown = name?.trim() || "Mening hisobim";

  return (
    <div className="fb-panel skeuo-card px-4 pb-3 pt-5 text-center">
      <span className="fb-avatar mx-auto h-16 w-16 text-xl" aria-hidden="true">
        {initials(name)}
      </span>
      <p className="mt-3 truncate text-sm font-bold text-[var(--fb-ink)]" title={shown}>
        {shown}
      </p>
      <p className="truncate text-xs text-[var(--fb-ink-muted)]">{roleLabel}</p>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={open ? "Hisob menyusini yopish" : "Hisob menyusini ochish"}
        className="mx-auto mt-1.5 flex h-7 w-7 items-center justify-center rounded-full text-[var(--fb-ink-muted)] hover:bg-[var(--fb-well-deep)] hover:text-[var(--fb-ink)]"
      >
        <ChevronDown className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div id={menuId} className="mt-2 flex flex-col gap-1 border-t border-[var(--fb-border)] pt-2 text-left">
          {securityHref && (
            <Link href={securityHref} className="fb-nav-item">
              <Shield className="h-4 w-4 shrink-0" />
              <span>Xavfsizlik</span>
            </Link>
          )}
          {onLogout && (
            <button type="button" onClick={onLogout} className="fb-nav-item w-full text-left">
              <LogOut className="h-4 w-4 shrink-0" />
              <span>Chiqish</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
