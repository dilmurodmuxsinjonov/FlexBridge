"use client";

import React, { Suspense, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { fetchAuthMe } from "@/lib/api";
import { useAsyncData } from "@/lib/useAsyncData";
import ChatApp from "@/components/chat/ChatApp";

function Messenger() {
  const auth = useAsyncData("auth-me", fetchAuthMe);
  const params = useSearchParams();
  const router = useRouter();
  const joinToken = params.get("qoshilish");
  const clearJoin = useCallback(() => router.replace("/xabarlar"), [router]);

  if (auth.isLoading) {
    return (
      <p className="flex items-center justify-center gap-2 py-24 text-sm text-[var(--fb-ink-muted)]">
        <Loader2 className="h-4 w-4 animate-spin" /> Yuklanmoqda…
      </p>
    );
  }
  if (!auth.data) {
    const back = joinToken ? `/xabarlar?qoshilish=${encodeURIComponent(joinToken)}` : "/xabarlar";
    return (
      <section className="fb-panel skeuo-card mx-auto my-10 flex max-w-md flex-col items-center gap-3 p-10 text-center">
        <h1 className="text-lg font-semibold text-[var(--fb-ink)]">Xabarlarni ko‘rish uchun kiring</h1>
        <p className="text-sm text-[var(--fb-ink-secondary)]">{joinToken ? "Kirgandan keyin guruhga avtomatik qo‘shilasiz." : "Suhbatlaringiz va guruhlaringiz shu yerda."}</p>
        <Link href={`/kirish?next=${encodeURIComponent(back)}`} className="rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold">Kirish</Link>
      </section>
    );
  }
  return <ChatApp meId={auth.data.user_id} joinToken={joinToken} onJoinHandled={clearJoin} />;
}

export default function MessagesPage() {
  return (
    <main className="mx-auto w-full max-w-[1440px] px-4 py-6 md:px-8">
      <Suspense fallback={null}>
        <Messenger />
      </Suspense>
    </main>
  );
}
