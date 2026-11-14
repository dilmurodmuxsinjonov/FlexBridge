import { CircleHelp } from "lucide-react";

export default function Footer() {
  return (
    <footer className="mt-auto w-full border-t border-white/[0.08] bg-surface-lowest px-4 py-6 text-xs text-zinc-400 md:px-8">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="font-heading font-semibold text-zinc-200">FlexBridge v1.4</p>
          <p className="mt-1">Ommaviy e’lonlar sahifasi backend javobini ko‘rsatadi.</p>
        </div>
        <p className="inline-flex items-center gap-2 text-zinc-400">
          <CircleHelp className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
          Ish beruvchi, universitet va operator bo‘limlari hozircha maket.
        </p>
      </div>
    </footer>
  );
}
