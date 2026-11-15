"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  Cookie,
  Mail,
  Calendar,
  Layers,
  ArrowLeft,
  Loader2,
  AlertCircle,
  Lock,
  EyeOff,
  UserCheck,
} from "lucide-react";
import { fetchPublicPolicy, PolicyDocumentResponse } from "@/lib/api";

type PrivacyTab = "privacy" | "cookies";

export default function PrivacyPolicyPage() {
  const [activeTab, setActiveTab] = useState<PrivacyTab>("privacy");
  const [policyData, setPolicyData] = useState<PolicyDocumentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectTab = (tab: PrivacyTab) => {
    if (tab === activeTab) return;
    setIsLoading(true);
    setErrorMessage(null);
    setActiveTab(tab);
  };

  useEffect(() => {
    let isMounted = true;

    fetchPublicPolicy(activeTab)
      .then((data) => {
        if (isMounted) setPolicyData(data);
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setErrorMessage(err instanceof Error ? err.message : "Maxfiylik hujjatini yuklashda xatolik yuz berdi.");
        }
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [activeTab]);

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <Link href="/" className="hover:text-white transition flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Asosiy Sahifa</span>
          </Link>
          <span>/</span>
          <span className="text-zinc-200 font-medium">Maxfiylik & Shaxsiy Ma&apos;lumotlar</span>
        </div>

        {/* Page Header */}
        <div className="border-b border-white/[0.08] pb-6">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <ShieldCheck className="w-7 h-7 text-emerald-400" />
            Maxfiylik Siyosati & Shaxsiy Ma&apos;lumotlar Himoyasi
          </h1>
          <p className="text-xs sm:text-sm text-zinc-400 mt-2 max-w-3xl leading-relaxed">
            FlexBridge foydalanuvchilarining shaxsiy ma&apos;lumotlari O&apos;zbekiston Respublikasi &quot;Shaxsiy ma&apos;lumotlar to&apos;g&apos;risida&quot;gi
            Qonuni va xalqaro GDPR standartlariga binoan shifrlangan holatda himoya qilinadi.
          </p>
        </div>

        {/* Document Selector Tabs */}
        <div className="flex items-center gap-2 border-b border-white/[0.08] pb-1 overflow-x-auto text-xs">
          <button
            onClick={() => selectTab("privacy")}
            className={`px-4 py-2.5 rounded-lg font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "privacy"
                ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
            }`}
          >
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Maxfiylik Siyosati (Privacy Policy)</span>
          </button>

          <button
            onClick={() => selectTab("cookies")}
            className={`px-4 py-2.5 rounded-lg font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "cookies"
                ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
            }`}
          >
            <Cookie className="w-4 h-4 text-amber-400" />
            <span>Cookie Fayllari Siyosati (Cookie Policy)</span>
          </button>
        </div>

        {/* Core Principles Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] space-y-2">
            <div className="flex items-center gap-2 text-emerald-400">
              <Lock className="w-4 h-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">End-to-End Shifrlash</h3>
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Barcha sessiya va autentifikatsiya ma&apos;lumotlari AES-256-GCM va SHA-256 kriptografiyasi orqali himoyalangan.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] space-y-2">
            <div className="flex items-center gap-2 text-primary">
              <EyeOff className="w-4 h-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">AC-023 Differensial Maxfiylik</h3>
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Tashkilot yoki talaba reytinglari 5 tadan kam bo&apos;lganda, ma&apos;lumotlar anonimlashtirilib maxfiy tutiladi.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] space-y-2">
            <div className="flex items-center gap-2 text-violet-400">
              <UserCheck className="w-4 h-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">Tijoriy Sotish Taqiqlangan</h3>
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Foydalanuvchilarning telefon raqamlari yoki rezyumelari hech qachon uchinchi shaxslarga tijoriy maqsadda sotilmaydi.
            </p>
          </div>
        </div>

        {/* Error Notification */}
        {errorMessage && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Loading State */}
        {isLoading ? (
          <div className="p-16 text-center text-xs text-zinc-400 flex items-center justify-center gap-2 bg-[#121214] border border-white/[0.08] rounded-xl">
            <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
            <span>Maxfiylik hujjati yuklanmoqda...</span>
          </div>
        ) : policyData ? (
          <div className="space-y-6">
            {/* Metadata Telemetry Banner */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm flex items-start gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Versiya</span>
                  <p className="text-sm font-bold font-mono text-white mt-0.5">{policyData.version}</p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 text-primary">
                  <Calendar className="w-4 h-4" />
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Kuchga Kirish Sanasi</span>
                  <p className="text-sm font-bold font-mono text-white mt-0.5">{policyData.effective_date}</p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm flex items-start gap-3">
                <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
                  <Mail className="w-4 h-4" />
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Maxfiylik Aloqasi</span>
                  <p className="text-sm font-bold font-mono text-white mt-0.5">{policyData.contact_email}</p>
                </div>
              </div>
            </div>

            {/* Document Clauses Overview */}
            {policyData.clauses && policyData.clauses.length > 0 && (
              <div className="p-5 md:p-6 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm space-y-4">
                <h2 className="text-sm font-semibold text-white uppercase tracking-wider text-zinc-400">
                  Maxfiylik Kafolatlari va Bandlari
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {policyData.clauses.map((clause) => (
                    <div
                      key={clause.id}
                      className="p-3.5 rounded-lg bg-white/[0.02] border border-white/[0.06] space-y-1.5"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {clause.id}
                        </span>
                        <h3 className="text-xs font-semibold text-white truncate">{clause.title}</h3>
                      </div>
                      <p className="text-[11px] text-zinc-400 leading-relaxed">{clause.summary}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Document Content */}
            <div className="p-6 md:p-8 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm space-y-4">
              <h2 className="text-lg font-bold text-white border-b border-white/[0.08] pb-3">
                {policyData.title}
              </h2>
              <div className="prose prose-invert prose-xs sm:prose-sm max-w-none text-zinc-300 whitespace-pre-line leading-relaxed font-sans">
                {policyData.content_markdown}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
