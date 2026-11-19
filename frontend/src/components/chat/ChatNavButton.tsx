"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { MessageCircle } from "lucide-react";
import { fetchConversations } from "@/lib/chat";

/** Navbar entry to /xabarlar with the unread count (polled while the tab is visible). */
export default function ChatNavButton({ active }: { active: boolean }) {
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    let alive = true;
    const tick = () => {
      if (document.visibilityState !== "visible") return;
      fetchConversations()
        .then((r) => alive && setUnread(r.unread_total))
        .catch(() => undefined);
    };
    tick();
    const id = window.setInterval(tick, 30_000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);
  return (
    <Link
      href="/xabarlar"
      prefetch={false}
      aria-label={unread ? `Xabarlar, ${unread} ta o‘qilmagan` : "Xabarlar"}
      aria-current={active ? "page" : undefined}
      className={`relative flex h-8 w-8 sm:h-10 sm:w-10 shrink-0 items-center justify-center rounded-full ${active ? "fb-nav-active" : "skeuo-btn-secondary"}`}
    >
      <MessageCircle className="h-4 w-4" />
      {unread > 0 && (
        <span className="absolute -right-0.5 -top-0.5 min-w-[18px] rounded-full bg-[var(--fb-accent)] px-1 text-center text-[10px] font-bold leading-[18px] text-white tabular-nums">
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </Link>
  );
}
