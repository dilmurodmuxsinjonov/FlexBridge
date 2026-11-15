"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  ShieldAlert,
  Star,
  CheckCircle2,
  Mail,
  Calendar,
  Layers,
  ArrowLeft,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { fetchPublicPolicy, PolicyDocumentResponse } from "@/lib/api";

type PolicyTab = "terms" | "acceptable-use" | "rating-guidelines";

export default function TermsAndPoliciesPage() {
  const [activeTab, setActiveTab] = useState<PolicyTab>("terms");
  const [policyData, setPolicyData] = useState<PolicyDocumentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectTab = (tab: PolicyTab) => {
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
          setErrorMessage(err instanceof Error ? err.message : "Hujjatni yuklashda xatolik yuz berdi.");
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
    <div className="min-h-screen text-[var(--fb-ink)] py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <Link href="/" className="hover:text-white transition flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Asosiy Sahifa</span>
          </Link>
          <span>/</span>
          <span className="text-zinc-200 font-medium">Qonuniy Hujjatlar & Shartlar</span>
        </div>

        {/* Page Header */}
        <div className="border-b border-white/[0.08] pb-6">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <FileText className="w-7 h-7 text-primary" />
            Platformadan Foydalanish Shartlari & Qoidalari
          </h1>
          <p className="text-xs sm:text-sm text-zinc-400 mt-2 max-w-3xl leading-relaxed">
            FlexBridge 1.4 platformasida talabalar, ish beruvchi tashkilotlar va oliy ta&apos;lim muassasalari
            o&apos;rtasidagi huquqiy munosabatlar, O&apos;zbekiston Respublikasi Mehnat Kodeksi va ta&apos;lim qonunchiligiga
            muvofiq tartibga solinadi.
          </p>
        </div>

        {/* Document Selector Tabs */}
        <div className="flex items-center gap-2 border-b border-white/[0.08] pb-1 overflow-x-auto text-xs">
          <button
            onClick={() => selectTab("terms")}
            className={`px-4 py-2.5 rounded-lg font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "terms"
                ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
            }`}
          >
            <FileText className="w-4 h-4 text-primary" />
            <span>Foydalanish Shartlari (Terms)</span>
          </button>

          <button
            onClick={() => selectTab("acceptable-use")}
            className={`px-4 py-2.5 rounded-lg font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "acceptable-use"
                ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
            }`}
          >
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <span>Maqbul Foydalanish Qoidalari (AUP)</span>
          </button>

          <button
            onClick={() => selectTab("rating-guidelines")}
            className={`px-4 py-2.5 rounded-lg font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "rating-guidelines"
                ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
            }`}
          >
            <Star className="w-4 h-4 text-emerald-400" />
            <span>Xolis Baholash Qoidalari (Ratings)</span>
          </button>
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
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
            <span>Hujjat yuklanmoqda...</span>
          </div>
        ) : policyData ? (
          <div className="space-y-6">
            {/* Metadata Telemetry Banner */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 text-primary">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Hujjat Versiyasi</span>
                  <p className="text-sm font-bold font-mono text-white mt-0.5">{policyData.version}</p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm flex items-start gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
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
                  <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Rasmiy Aloqa</span>
                  <p className="text-sm font-bold font-mono text-white mt-0.5">{policyData.contact_email}</p>
                </div>
              </div>
            </div>

            {/* Document Clauses Overview */}
            {policyData.clauses && policyData.clauses.length > 0 && (
              <div className="p-5 md:p-6 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm space-y-4">
                <h2 className="text-sm font-semibold text-white uppercase tracking-wider text-zinc-400">
                  Asosiy Moddalar va Talablar
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {policyData.clauses.map((clause) => (
                    <div
                      key={clause.id}
                      className="p-3.5 rounded-lg bg-white/[0.02] border border-white/[0.06] space-y-1.5"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
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

            {/* Legal Safeguard Footnote */}
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] text-xs text-zinc-400 flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-primary shrink-0 mt-0.5" />
              <p className="leading-relaxed">
                Ushbu shartlar FlexBridge 1.4 rasmiy kelishuvi asosida versiyalangan va platforma barcha ishtirokchilari (nomzod, ish beruvchi, OTM) uchun yuridik jihatdan majburiy hisoblanadi.
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
