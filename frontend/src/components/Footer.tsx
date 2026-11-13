import { ShieldCheck, Cpu, Database, FileText } from "lucide-react";

export default function Footer() {
  return (
    <footer className="w-full border-t border-white/[0.08] bg-surface-lowest text-zinc-400 text-xs py-8 px-4 md:px-8 mt-auto">
      <div className="max-w-[1440px] mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Compliance statement */}
        <div className="flex flex-col gap-1 text-center md:text-left">
          <div className="flex items-center justify-center md:justify-start gap-2 text-zinc-200 font-medium">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>O‘zbekiston Respublikasi Qonunchiligi bilan 100% himoyalangan</span>
          </div>
          <p className="text-[11px] text-zinc-500">
            «Shaxsga doir ma'lumotlar to'g'risida»gi Qonun (№O‘RQ-547) va «Kiberxavfsizlik to'g'risida»gi Qonun (№O‘RQ-764).
            Mehnat Kodeksi 118-moddasi (Haftalik 20 soatlik talaba kafolati).
          </p>
        </div>

        {/* Telemetry metadata */}
        <div className="flex flex-wrap items-center justify-center gap-4 text-[11px] font-mono text-zinc-400">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface border border-white/[0.06]">
            <Database className="w-3 h-3 text-primary" />
            <span>HEMIS v3.2 API: Sinxron</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface border border-white/[0.06]">
            <Cpu className="w-3 h-3 text-emerald-400" />
            <span>SHA-256 Merkle Block: #1,842,910</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface border border-white/[0.06]">
            <FileText className="w-3 h-3 text-amber-400" />
            <span>Mehnat.uz YAMMT: Faol</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
