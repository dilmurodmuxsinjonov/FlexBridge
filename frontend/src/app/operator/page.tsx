"use client";

import { useState } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Lock,
  Unlock,
  Key,
  Search,
  Filter,
  Download,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileCode,
  Terminal,
  Activity,
  UserCheck,
} from "lucide-react";
import { SecurityAuditEvent } from "@/lib/api";

export default function OperatorPortal() {
  const [auditEvents, setAuditEvents] = useState<SecurityAuditEvent[]>([
    {
      event_id: "EVT-98412",
      timestamp: "15:42:01",
      actor_role: "Org HR (Uzum)",
      ip_address: "195.158.12.44",
      sha256_hash: "8f7e...912a",
      event_type: "BREAK_GLASS_REQUEST",
      details: "Talaba shaxsiy ma'lumotlariga favqulodda kirish (O'rganilmoqda)",
      status_badge: "warning",
    },
    {
      event_id: "EVT-98411",
      timestamp: "15:41:22",
      actor_role: "Student (TATU)",
      ip_address: "213.230.88.19",
      sha256_hash: "a7f8...3c2e",
      event_type: "CONTRACT_SIGN",
      details: "3 tomonlama shartnoma E-IMZO bilan imzolandi",
      status_badge: "verified",
    },
    {
      event_id: "EVT-98410",
      timestamp: "15:40:05",
      actor_role: "Anonim / Hujumchi",
      ip_address: "185.220.101.5",
      sha256_hash: "31ba...44fa",
      event_type: "WAF_BLOCK",
      details: "SQLi injection urinishi /api/v1/opportunities (Bloklandi: 400 Bad Request)",
      status_badge: "danger",
    },
    {
      event_id: "EVT-98409",
      timestamp: "15:38:19",
      actor_role: "Univ Koordinator",
      ip_address: "84.54.80.12",
      sha256_hash: "74cd...889b",
      event_type: "DIARY_VERIFICATION",
      details: "TATU kafedra o'qituvchisi amaliyot kundaligini tasdiqladi (95 ball)",
      status_badge: "info",
    },
    {
      event_id: "EVT-98408",
      timestamp: "15:35:40",
      actor_role: "Mehnat.uz Gateway",
      ip_address: "213.230.64.10",
      sha256_hash: "55be...112e",
      event_type: "REESTR_SYNC",
      details: "YAMMT orqali 14 ta yangi stajirovka shartnomasi xeshlandi",
      status_badge: "neutral",
    },
  ]);

  const [totpCode, setTotpCode] = useState("");
  const [breakGlassApproved, setBreakGlassApproved] = useState(false);
  const [breakGlassRejected, setBreakGlassRejected] = useState(false);

  const handleApprove = () => {
    if (totpCode.length >= 4) {
      setBreakGlassApproved(true);
      setBreakGlassRejected(false);
    } else {
      alert("Iltimos, 2-imzolovchi TOTP / YubiKey xavfsizlik kodini kiriting!");
    }
  };

  const handleReject = () => {
    setBreakGlassRejected(true);
    setBreakGlassApproved(false);
  };

  return (
    <main className="max-w-[1440px] w-full mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      {/* OPERATOR HEADER & ENVIRONMENT TELEMETRY */}
      <section className="w-full bg-surface-card border border-white/[0.08] rounded-lg p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                Security Operations Center (SOC)
              </span>
              <span className="text-zinc-500 text-xs">
                • Node: uz-tashkent-dc1 (Stage)
              </span>
              <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                132/132 API Sog&apos;lom
              </span>
            </div>
            <h1 className="font-heading text-lg md:text-xl font-bold text-zinc-100">
              Platforma Operatori va Xavfsizlik Boshqaruv Paneli
            </h1>
            <p className="text-xs text-zinc-400">
              Qat&apos;iy append-only SHA-256 audit oqimi • O&apos;RQ-547 va O&apos;RQ-764 talablariga to&apos;liq muvofiq
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="px-3.5 py-1.5 rounded bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-200 transition-all flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5 text-zinc-400" />
              <span>Audit Eksport (JSON)</span>
            </button>
            <button
              type="button"
              className="px-3.5 py-1.5 rounded bg-surface hover:bg-surface-high border border-white/[0.08] text-xs font-semibold text-zinc-200 transition-all flex items-center gap-1.5"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Kriptografik Verifikatsiya</span>
            </button>
          </div>
        </div>

        {/* SECURITY & OPERATIONS KPI SUMMARY */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 pt-4 border-t border-white/[0.06]">
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">24s Xavfsizlik hodisalari</span>
            <div className="font-mono text-base font-bold text-zinc-100 mt-0.5">
              4,891 ta <span className="text-[11px] text-zinc-500 font-normal">(0 kechikish)</span>
            </div>
          </div>
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">Bloklangan hujumlar (WAF)</span>
            <div className="font-mono text-base font-bold text-emerald-400 mt-0.5">
              342 ta <span className="text-[11px] text-emerald-500 font-normal">(100% himoya)</span>
            </div>
          </div>
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">Faol xavfsiz sessiyalar</span>
            <div className="font-mono text-base font-bold text-primary mt-0.5">
              1,280 ta <span className="text-[11px] text-zinc-500 font-normal">(842 talaba)</span>
            </div>
          </div>
          <div className="p-3 rounded bg-surface-lowest border border-white/[0.06]">
            <span className="text-[11px] text-zinc-400">Favqulodda kirish (Break-Glass)</span>
            <div className="font-mono text-base font-bold text-amber-400 mt-0.5">
              2 faol | 1 kutilmoqda
            </div>
          </div>
        </div>
      </section>

      {/* DUAL-PANEL WORKSPACE (60% Audit Stream + 40% Break-Glass Protocol) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* LEFT AUDIT STREAM (7 columns) */}
        <div className="xl:col-span-7 flex flex-col gap-4">
          <div className="rounded-lg bg-surface-card border border-white/[0.08] overflow-hidden">
            <div className="p-3.5 border-b border-white/[0.06] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-primary" />
                <span className="text-xs font-bold text-zinc-200">
                  Xavfsizlik va Tranzaksiyalar Audit Jurnali
                </span>
              </div>
              <span className="text-[10px] font-mono text-zinc-500">
                SHA-256 Merkle Block #1,842,910
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-white/[0.06] bg-surface-lowest text-zinc-400 font-semibold text-[11px]">
                    <th className="py-2.5 px-3">Event ID</th>
                    <th className="py-2.5 px-3">Vaqt</th>
                    <th className="py-2.5 px-3">Aktyor / IP</th>
                    <th className="py-2.5 px-3">Hodisa</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {auditEvents.map((evt) => (
                    <tr
                      key={evt.event_id}
                      className="hover:bg-white/[0.02] text-zinc-300 transition-colors"
                    >
                      <td className="py-3 px-3 font-mono text-zinc-200 font-semibold">
                        {evt.event_id}
                      </td>
                      <td className="py-3 px-3 font-mono text-[11px] text-zinc-400">
                        {evt.timestamp}
                      </td>
                      <td className="py-3 px-3">
                        <span className="text-zinc-200 block font-medium">
                          {evt.actor_role}
                        </span>
                        <span className="text-[10px] text-zinc-500 font-mono">
                          {evt.ip_address} ({evt.sha256_hash})
                        </span>
                      </td>
                      <td className="py-3 px-3 text-[11px] text-zinc-300">
                        {evt.details}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                            evt.status_badge === "warning"
                              ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                              : evt.status_badge === "verified"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : evt.status_badge === "danger"
                              ? "bg-red-500/10 text-red-400 border-red-500/20"
                              : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                          }`}
                        >
                          {evt.event_type}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-zinc-400">
              <span>Barcha yozuvlar Merkle daraxtiga muhrlangan</span>
              <span className="text-[10px] text-zinc-500 font-mono">
                Oxirgi sinx: 3 soniya oldin
              </span>
            </div>
          </div>
        </div>

        {/* RIGHT BREAK-GLASS INSPECTION PANEL (5 columns) */}
        <aside className="xl:col-span-5 flex flex-col gap-4">
          <div className="p-4 rounded-lg bg-surface-card border border-white/[0.08]">
            <div className="pb-3 border-b border-white/[0.06] flex items-start justify-between">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                <div>
                  <h3 className="font-heading text-sm font-bold text-zinc-100">
                    Break-Glass Ruxsat So&apos;rovi: #BG-2025-089
                  </h3>
                  <span className="text-[10px] text-zinc-400 font-mono">
                    4-Ko&apos;z (Dual Control) Protokoli Talab Qilinadi
                  </span>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-mono font-bold">
                KUTILMOQDA
              </span>
            </div>

            {/* Request Meta Card */}
            <div className="mt-4 p-3 rounded bg-surface-lowest border border-white/[0.06] flex flex-col gap-2 text-xs">
              <div>
                <span className="text-zinc-500 text-[11px] block">So&apos;rovchi:</span>
                <span className="text-zinc-200 font-semibold">
                  Jamshid Karimov (Uzum HR Xavfsizlik vakili)
                </span>
              </div>
              <div>
                <span className="text-zinc-500 text-[11px] block">Bog&apos;langan talaba:</span>
                <span className="text-zinc-200 font-semibold">
                  Azizbek Rahimov (TATU, ID: TATU-2022-0814)
                </span>
              </div>
              <div>
                <span className="text-zinc-500 text-[11px] block">Asos va Sabab:</span>
                <p className="text-zinc-300 text-[11px] mt-0.5 leading-relaxed bg-white/[0.02] p-2 rounded border border-white/[0.04]">
                  &quot;Talaba shartnomasidagi bank rekvizitlarini Mehnat.uz bilan moslashtirishdagi
                  ziddiyatni bartaraf etish va oylik stajirovka to&apos;lovini blokdan chiqarish.&quot;
                </p>
              </div>
              <div className="flex items-center justify-between text-[11px] text-zinc-400 pt-1">
                <span>Ruxsat doirasi: <strong className="text-zinc-200">Faqat o&apos;qish (Read-only PII)</strong></span>
                <span className="text-red-400 font-semibold">Max 2 soat</span>
              </div>
            </div>

            {/* 2nd Signer Verification */}
            <div className="mt-4 p-3 rounded bg-surface-lowest border border-white/[0.06]">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                  <Key className="w-3.5 h-3.5 text-primary" />
                  <span>2-Imzolovchi Operator Xavfsizlik Tasdig&apos;i</span>
                </span>
                <span className="text-[10px] text-zinc-400 font-mono">YubiKey L4</span>
              </div>
              <p className="text-[11px] text-zinc-400 mb-2">
                Operator S. Alimov (L4 Clearance) shaxsiy TOTP kodini kiriting:
              </p>
              <input
                type="text"
                maxLength={6}
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                placeholder="Kod: 482910"
                className="w-full px-3 py-2 bg-surface border border-white/[0.1] rounded text-xs font-mono tracking-widest text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-primary text-center font-bold"
              />
            </div>

            {/* Action buttons */}
            <div className="mt-4 flex flex-col gap-2">
              {breakGlassApproved ? (
                <div className="p-3 rounded bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-semibold flex items-center justify-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Break-Glass faollashtirildi! (Muddati: 2 soat)</span>
                </div>
              ) : breakGlassRejected ? (
                <div className="p-3 rounded bg-red-500/20 border border-red-500/40 text-red-300 text-xs font-semibold flex items-center justify-center gap-2">
                  <XCircle className="w-4 h-4 text-red-400" />
                  <span>So&apos;rov rad etildi va xavfsizlik auditiga yuborildi</span>
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  <button
                    type="button"
                    onClick={handleApprove}
                    className="w-full py-2.5 rounded bg-primary hover:bg-primary-hover text-white text-xs font-semibold flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
                  >
                    <Unlock className="w-4 h-4" />
                    <span>Ruxsat berish (Break-Glass faollashtirish)</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleReject}
                    className="w-full py-2 rounded bg-surface hover:bg-surface-high border border-red-500/30 text-red-400 hover:text-red-300 text-xs font-medium transition-all"
                  >
                    Rad etish va tekshiruvga yuborish
                  </button>
                </div>
              )}
            </div>

            <div className="mt-3 text-[10px] text-zinc-500 text-center">
              Har bir ochilgan ma&apos;lumot bayti O&apos;zbekiston Kiberxavfsizlik markazi reyestriga yuboriladi.
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
