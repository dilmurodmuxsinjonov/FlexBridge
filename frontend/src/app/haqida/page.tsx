"use client";

import { useEffect, useState } from "react";
import SimpleMarkdown from "@/components/SimpleMarkdown";
import Link from "next/link";
import {
  Compass,
  User,
  Briefcase,
  Building2,
  CalendarCheck,
  Layers,
  Calendar,
  ArrowLeft,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Cpu,
  GraduationCap,
} from "lucide-react";
import { fetchPublicHelp, HelpDocumentResponse } from "@/lib/api";

type HelpDocSlug =
  | "onboarding"
  | "candidate-guide"
  | "employer-guide"
  | "academic-guide"
  | "schedule-matching";

export default function AboutAndHelpPage() {
  const [activeTab, setActiveTab] = useState<HelpDocSlug>("onboarding");
  const [helpData, setHelpData] = useState<HelpDocumentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectTab = (tab: HelpDocSlug) => {
    if (tab === activeTab) return;
    setIsLoading(true);
    setErrorMessage(null);
    setActiveTab(tab);
  };

  useEffect(() => {
    let isMounted = true;

    fetchPublicHelp(activeTab)
      .then((data) => {
        if (isMounted) setHelpData(data);
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setErrorMessage(err instanceof Error ? err.message : "Qo‘llanmani yuklashda xatolik yuz berdi.");
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
          <span className="text-zinc-200 font-medium">Platforma Haqida & Qo‘llanmalar</span>
        </div>

        {/* Page Header */}
        <div className="border-b border-white/[0.08] pb-6">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Compass className="w-7 h-7 text-primary" />
            FlexBridge v1.4: Tizim Me&apos;morchiligi & Foydalanuvchi Qo&apos;llanmalari
          </h1>
          <p className="text-xs sm:text-sm text-zinc-400 mt-2 max-w-3xl leading-relaxed">
            Talabalarning dars va ish jadvallarini daqiqama-daqiqa muvofiqlashtiruvchi, O&apos;zR Mehnat Kodeksi
            118-moddasi (kunlik 8-soatlik chegara) va Oliy ta&apos;lim HEMIS tizimi bilan integratsiyalashgan ekotizim.
          </p>
        </div>

        {/* Document Selector Tabs */}
        <div className="flex items-center gap-2 border-b border-white/[0.08] pb-1 overflow-x-auto text-xs">
          <button
            onClick={() => selectTab("onboarding")}
            className={`px-3.5 py-2.5 rounded-lg font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "onboarding"
                ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
            }`}
          >
            <Compass className="w-4 h-4 text-primary" />
            <span>Ish Boshlash (Onboarding)</span>
          </button>

          <button
            onClick={() => selectTab("candidate-guide")}
            className={`px-3.5 py-2.5 rounded-lg font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "candidate-guide"
                ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
            }`}
          >
            <User className="w-4 h-4 text-sky-400" />
            <span>Nomzodlar Uchun</span>
          </button>

          <button
            onClick={() => selectTab("employer-guide")}
            className={`px-3.5 py-2.5 rounded-lg font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "employer-guide"
                ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
            }`}
          >
            <Briefcase className="w-4 h-4 text-emerald-400" />
            <span>Ish Beruvchilar Uchun</span>
          </button>

          <button
            onClick={() => selectTab("academic-guide")}
            className={`px-3.5 py-2.5 rounded-lg font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "academic-guide"
                ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
            }`}
          >
            <Building2 className="w-4 h-4 text-amber-400" />
            <span>OTM Koordinatorlari</span>
          </button>

          <button
            onClick={() => selectTab("schedule-matching")}
            className={`px-3.5 py-2.5 rounded-lg font-semibold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === "schedule-matching"
                ? "bg-white/[0.08] text-white border border-white/[0.12] shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
            }`}
          >
            <CalendarCheck className="w-4 h-4 text-violet-400" />
            <span>Dars jadvaliga moslik</span>
          </button>
        </div>

        {/* 3 Architecture Pillar Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] space-y-2">
            <div className="flex items-center gap-2 text-primary">
              <Cpu className="w-4 h-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">Moslik algoritmi</h3>
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Talabaning dars jadvali, qatnov buferi (commute buffer) va ish smenalarining daqiqama-daqiqa kesishmasligini 100% kafolatlaydi.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] space-y-2">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">O‘zR MK 118-modda</h3>
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Talabalar kunlik 8 soatdan ortiq ishlamasligi va ta&apos;lim jarayoniga zarar yetkazmasligi qat&apos;iy avtomatlashtirilgan.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] space-y-2">
            <div className="flex items-center gap-2 text-sky-400">
              <GraduationCap className="w-4 h-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">HEMIS Integratsiyasi</h3>
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Oliy ta&apos;lim muassasalari buyruqlari, amaliyot bazalari va raqamli kundaliklar yagona tizimda tasdiqlanadi.
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
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
            <span>Qo‘llanma yuklanmoqda...</span>
          </div>
        ) : helpData ? (
          <div className="space-y-6">
            {/* Metadata Telemetry Banner */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 text-primary">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Hujjat Versiyasi</span>
                  <p className="text-sm font-bold font-mono text-white mt-0.5">{helpData.version}</p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm flex items-start gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  <Calendar className="w-4 h-4" />
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Kuchga Kirish Sanasi</span>
                  <p className="text-sm font-bold font-mono text-white mt-0.5">{helpData.effective_date}</p>
                </div>
              </div>
            </div>

            {/* Document Sections Overview */}
            {helpData.sections && helpData.sections.length > 0 && (
              <div className="p-5 md:p-6 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm space-y-3">
                <h2 className="text-sm font-semibold text-white uppercase tracking-wider text-zinc-400">
                  Ushbu Qo&apos;llanma Bo&apos;limlari
                </h2>
                <div className="flex flex-wrap gap-2">
                  {helpData.sections.map((section, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-xs text-zinc-300 font-medium"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                      <span>{section.heading}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Document Content */}
            <div className="p-6 md:p-8 rounded-xl bg-[#121214] border border-white/[0.08] shadow-sm space-y-4">
              <h2 className="text-lg font-bold text-white border-b border-white/[0.08] pb-3">
                {helpData.title}
              </h2>
              <SimpleMarkdown source={helpData.content_markdown} skipFirstHeading />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
