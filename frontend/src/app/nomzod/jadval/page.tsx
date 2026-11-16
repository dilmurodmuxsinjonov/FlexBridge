"use client";

import React from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { fetchAuthMe } from "@/lib/api";
import { fetchMyTimetable } from "@/lib/timetable";
import { useAsyncData } from "@/lib/useAsyncData";
import StudentTimetable from "@/components/timetable/StudentTimetable";

export default function StudentTimetablePage() {
  const auth = useAsyncData("auth-me", fetchAuthMe);
  const user = auth.data ?? null;
  const timetable = useAsyncData(user ? `my-timetable:${user.user_id}` : null, fetchMyTimetable);

  if (auth.isLoading || (user && timetable.isLoading)) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-sm text-[var(--fb-ink-muted)]">
        <Loader2 className="h-4 w-4 animate-spin" /> Jadval yuklanmoqda…
      </div>
    );
  }
  if (!user) {
    return (
      <section className="fb-panel skeuo-card mx-auto my-10 flex max-w-md flex-col items-center gap-3 p-10 text-center">
        <h1 className="text-lg font-semibold text-[var(--fb-ink)]">O‘quv jadvalini ko‘rish uchun kiring</h1>
        <Link href="/talaba/kirish" className="rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold">Talaba kirishi</Link>
      </section>
    );
  }
  if (timetable.error || !timetable.data) {
    return (
      <section className="fb-panel skeuo-card mx-auto my-10 flex max-w-md flex-col items-center gap-3 p-10 text-center" role="alert">
        <h1 className="text-lg font-semibold text-[var(--fb-ink)]">Jadvalni yuklab bo‘lmadi</h1>
        <p className="text-sm text-[var(--fb-ink-secondary)]">{timetable.error?.message}</p>
        <button type="button" onClick={() => void timetable.reload()} className="rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold">Qayta urinish</button>
      </section>
    );
  }
  return <StudentTimetable data={timetable.data} />;
}
