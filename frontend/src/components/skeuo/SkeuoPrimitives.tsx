"use client";

import React, { useId, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, ArrowDownRight, type LucideIcon } from "lucide-react";

type SkeuoSurface = "raised" | "recessed" | "obsidian";

export interface SkeuoCardProps {
  children: React.ReactNode;
  surface?: SkeuoSurface;
  className?: string;
  padding?: string;
}

export function SkeuoCard({
  children,
  surface = "raised",
  className = "",
  padding = "p-5",
}: SkeuoCardProps) {
  const surfaceClass =
    surface === "obsidian"
      ? "skeuo-obsidian"
      : surface === "recessed"
        ? "skeuo-well"
        : "skeuo-card";

  return (
    <div
      data-skeuo-dark={surface === "obsidian" ? "true" : undefined}
      className={`rounded-2xl ${surfaceClass} ${padding} ${className}`}
    >
      {children}
    </div>
  );
}

export type StatTone = "orange" | "emerald" | "sky" | "indigo" | "amber" | "slate";

const TONE_MAP: Record<
  StatTone,
  { badgeBg: string; iconText: string; barFill: string; accentLine: string }
> = {
  orange: {
    badgeBg: "bg-[#D95F2B]/14 border-[#D95F2B]/30",
    iconText: "text-[#C2410C] dark:text-orange-400",
    barFill: "from-[#FF8243] via-[#EA580C] to-[#C2410C]",
    accentLine: "bg-[#D95F2B]",
  },
  emerald: {
    badgeBg: "bg-emerald-600/14 border-emerald-600/30",
    iconText: "text-emerald-700 dark:text-emerald-400",
    barFill: "from-emerald-400 via-emerald-500 to-emerald-700",
    accentLine: "bg-emerald-500",
  },
  sky: {
    badgeBg: "bg-sky-600/14 border-sky-600/30",
    iconText: "text-sky-700 dark:text-sky-400",
    barFill: "from-sky-400 via-sky-500 to-sky-700",
    accentLine: "bg-sky-500",
  },
  indigo: {
    badgeBg: "bg-indigo-600/14 border-indigo-600/30",
    iconText: "text-indigo-700 dark:text-indigo-400",
    barFill: "from-indigo-400 via-indigo-500 to-indigo-700",
    accentLine: "bg-indigo-500",
  },
  amber: {
    badgeBg: "bg-amber-600/14 border-amber-600/30",
    iconText: "text-amber-700 dark:text-amber-400",
    barFill: "from-amber-300 via-amber-500 to-amber-700",
    accentLine: "bg-amber-500",
  },
  slate: {
    badgeBg: "bg-zinc-500/14 border-zinc-500/30",
    iconText: "text-zinc-700 dark:text-zinc-300",
    barFill: "from-zinc-400 via-zinc-600 to-zinc-800",
    accentLine: "bg-zinc-500",
  },
};

export interface SkeuoStatCardProps {
  title: string;
  value: string | number;
  delta?: string;
  deltaPositive?: boolean;
  subtitle?: string;
  icon: LucideIcon;
  tone?: StatTone;
  onClick?: () => void;
  active?: boolean;
}

export function SkeuoStatCard({
  title,
  value,
  delta,
  deltaPositive = true,
  subtitle,
  icon: Icon,
  tone = "orange",
  onClick,
  active = false,
}: SkeuoStatCardProps) {
  const palette = TONE_MAP[tone];
  const Wrapper = onClick ? motion.button : motion.div;

  return (
    <Wrapper
      type={onClick ? "button" : undefined}
      onClick={onClick}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.16, ease: [0.23, 1, 0.32, 1] }}
      className={`skeuo-card relative overflow-hidden w-full rounded-[22px] p-4 text-left flex flex-col justify-between gap-2.5 transition-all ${
        active ? "ring-2 ring-[var(--fb-accent)]" : ""
      } ${onClick ? "cursor-pointer active:scale-[0.985]" : ""}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--fb-ink-muted)] truncate">
            {title}
          </p>
          <p className="font-heading text-2xl sm:text-[28px] leading-none font-bold tracking-tight text-[var(--fb-ink)] tabular-nums pt-0.5">
            {value}
          </p>
        </div>
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border skeuo-well-sm ${palette.badgeBg} ${palette.iconText}`}
        >
          <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
        </div>
      </div>

      {(delta || subtitle) && (
        <div className="pt-2.5 border-t border-[var(--fb-hairline)] flex flex-wrap items-center justify-between gap-2 text-[11px]">
          {delta ? (
            <span
              className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 font-mono text-[10px] font-bold tabular-nums ${
                deltaPositive
                  ? "bg-emerald-600/14 text-emerald-700 dark:text-emerald-400"
                  : "bg-rose-600/14 text-rose-700 dark:text-rose-400"
              }`}
            >
              {deltaPositive ? (
                <ArrowUpRight className="h-3 w-3" aria-hidden="true" />
              ) : (
                <ArrowDownRight className="h-3 w-3" aria-hidden="true" />
              )}
              {delta}
            </span>
          ) : (
            <span className={`h-1.5 w-6 rounded-full opacity-75 ${palette.accentLine}`} />
          )}
          {subtitle && (
            <span className="text-[var(--fb-ink-secondary)] font-medium truncate">{subtitle}</span>
          )}
        </div>
      )}
    </Wrapper>
  );
}

export interface SkeuoToggleProps {
  checked: boolean;
  onChange: (next: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  tone?: StatTone;
}

export function SkeuoToggle({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  tone = "orange",
}: SkeuoToggleProps) {
  const ledColor =
    tone === "emerald"
      ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.75)]"
      : tone === "sky"
        ? "bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.75)]"
        : tone === "indigo"
          ? "bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.75)]"
          : tone === "amber"
            ? "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.75)]"
            : "bg-[#EA580C] shadow-[0_0_8px_rgba(234,88,12,0.75)]";

  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl skeuo-well px-3.5 py-2.5">
      {(label || description) && (
        <div className="min-w-0">
          {label && (
            <div className="text-xs font-semibold text-[var(--fb-ink)]">{label}</div>
          )}
          {description && (
            <div className="text-[11px] text-[var(--fb-ink-muted)] leading-snug">
              {description}
            </div>
          )}
        </div>
      )}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label || "Holatni almashtirish"}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-7 shrink-0 items-center rounded-full p-1 transition-colors skeuo-well-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--fb-accent)] disabled:opacity-50 ${
          checked
            ? "bg-[#1A1A1D] dark:bg-white/20"
            : "bg-[var(--fb-well-deep)]"
        }`}
        style={{ width: "52px" }}
      >
        <motion.span
          layout
          transition={{ type: "spring", stiffness: 520, damping: 32 }}
          className={`flex h-5 w-5 items-center justify-center rounded-full bg-white shadow-[0_2px_6px_rgba(0,0,0,0.32),inset_0_1px_0_rgba(255,255,255,1)] ${
            checked ? "ml-auto" : "mr-auto"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full transition-colors ${
              checked ? ledColor : "bg-stone-300"
            }`}
          />
        </motion.span>
      </button>
    </div>
  );
}

export interface SkeuoVerticalMeterProps {
  title: string;
  percentage: number;
  amountLabel: string;
  subtitle?: string;
  tone?: StatTone;
  onAction?: () => void;
  actionLabel?: string;
  compact?: boolean;
}

export function SkeuoVerticalMeter({
  title,
  percentage,
  amountLabel,
  subtitle,
  tone = "orange",
  onAction,
  actionLabel,
  compact = false,
}: SkeuoVerticalMeterProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(percentage)));
  const palette = TONE_MAP[tone];
  // Position the frosted percentage badge cleanly near liquid level without ever clipping the bottom rim
  const badgeBottomPct = Math.min(64, Math.max(12, clamped - 14));

  return (
    <div
      className={`skeuo-card rounded-[22px] flex flex-col items-center text-center ${
        compact ? "p-3 gap-2.5" : "p-4 gap-3"
      }`}
    >
      {/* 3D Brushed Glass Cylindrical Vessel with Glossy Specular Highlight */}
      <div
        className={`relative rounded-full p-1.5 skeuo-well overflow-hidden flex items-end justify-center ${
          compact ? "h-28 w-12" : "h-36 w-14"
        }`}
      >
        {/* Convex Glass Cylinder Specular Reflection */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 rounded-full z-20"
          style={{
            background:
              "linear-gradient(90deg, rgba(255,255,255,0.28) 0%, rgba(255,255,255,0.04) 36%, rgba(0,0,0,0.08) 100%)",
          }}
        />
        {clamped > 0 && (
          <motion.div
            initial={{ height: "0%" }}
            animate={{ height: `${Math.max(14, clamped)}%` }}
            transition={{ type: "spring", stiffness: 120, damping: 20 }}
            className={`w-full rounded-full bg-gradient-to-b ${palette.barFill} shadow-[0_2px_10px_rgba(0,0,0,0.2),inset_0_1.5px_1px_rgba(255,255,255,0.5)] relative`}
          />
        )}
        {/* Floating Frosted Percentage Medallion */}
        <motion.div
          initial={false}
          animate={{ bottom: `${badgeBottomPct}%` }}
          transition={{ type: "spring", stiffness: 140, damping: 20 }}
          className={`absolute left-1/2 -translate-x-1/2 z-30 rounded-full skeuo-card flex items-center justify-center shadow-[0_4px_12px_rgba(24,20,14,0.22)] ${
            compact ? "h-8 w-8" : "h-9 w-9"
          }`}
        >
          <span className="font-mono text-[10px] sm:text-[11px] font-bold text-[var(--fb-ink)] tabular-nums">
            {clamped}%
          </span>
        </motion.div>
      </div>

      <div className="space-y-0.5 w-full min-w-0">
        <div className="text-xs font-bold text-[var(--fb-ink)] truncate">{title}</div>
        <div className="font-mono text-[11px] font-semibold text-[var(--fb-ink-secondary)] tabular-nums truncate">
          {amountLabel}
        </div>
        {subtitle && (
          <div className="text-[10px] text-[var(--fb-ink-muted)] truncate">{subtitle}</div>
        )}
      </div>

      {onAction && actionLabel && (
        <button
          type="button"
          onClick={onAction}
          className="w-full rounded-xl skeuo-btn-secondary px-2.5 py-1.5 text-[11px] font-semibold transition active:scale-[0.97]"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export interface SegmentedOption<T extends string> {
  id: T;
  label: string;
  icon?: LucideIcon;
  badge?: string | number;
}

export function SkeuoSegmented<T extends string>({
  options,
  value,
  onChange,
  layoutName = "seg",
  className = "",
}: {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (next: T) => void;
  layoutName?: string;
  className?: string;
}) {
  const uid = useId();
  return (
    <div
      className={`inline-flex flex-wrap items-center gap-1 rounded-2xl p-1.5 skeuo-well ${className}`}
      role="tablist"
    >
      {options.map((opt) => {
        const isActive = opt.id === value;
        const Icon = opt.icon;
        return (
          <button
            key={opt.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(opt.id)}
            className={`relative inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-semibold transition-colors ${
              isActive
                ? "text-[var(--fb-ink)]"
                : "text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]"
            }`}
          >
            {isActive && (
              <motion.span
                layoutId={`skeuo-seg-${layoutName}-${uid}`}
                transition={{ type: "spring", stiffness: 420, damping: 32 }}
                className="absolute inset-0 rounded-xl skeuo-card shadow-[0_3px_10px_rgba(24,20,14,0.12)]"
              />
            )}
            <span className="relative z-10 inline-flex items-center gap-1.5">
              {Icon && <Icon className="h-3.5 w-3.5" aria-hidden="true" />}
              <span>{opt.label}</span>
              {opt.badge !== undefined && (
                <span className="rounded-full bg-[var(--fb-well)] px-1.5 py-0.5 font-mono text-[10px] tabular-nums">
                  {opt.badge}
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export interface LiveFeedItem {
  id: string;
  title: string;
  meta: string;
  time: string;
  status?: "ok" | "warn" | "info";
}

export function SkeuoLiveFeed({
  title,
  items,
  emptyText = "Hozircha faoliyat yozuvlari yo‘q.",
}: {
  title: string;
  items: LiveFeedItem[];
  emptyText?: string;
}) {
  return (
    <div className="skeuo-card rounded-[22px] p-5 flex flex-col gap-3.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.75)] animate-pulse" />
          <h3 className="font-heading text-sm font-bold text-[var(--fb-ink)]">{title}</h3>
        </div>
        <span className="rounded-full skeuo-well-sm px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-[var(--fb-ink-muted)]">
          Live Stream
        </span>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl skeuo-well p-4 text-xs text-[var(--fb-ink-muted)] text-center">
          {emptyText}
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => {
            const dotClass =
              item.status === "warn"
                ? "bg-amber-500 shadow-[0_0_6px_rgba(245,158,11,0.6)]"
                : item.status === "ok"
                  ? "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]"
                  : "bg-[#D95F2B] shadow-[0_0_6px_rgba(217,95,43,0.6)]";
            return (
              <div
                key={item.id}
                className="rounded-xl skeuo-well px-3.5 py-2.5 flex items-start justify-between gap-3 transition-transform hover:translate-x-0.5"
              >
                <div className="flex items-start gap-2.5 min-w-0">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dotClass}`} />
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-[var(--fb-ink)] truncate">
                      {item.title}
                    </div>
                    <div className="text-[11px] text-[var(--fb-ink-muted)] truncate">
                      {item.meta}
                    </div>
                  </div>
                </div>
                <span className="shrink-0 font-mono text-[10px] text-[var(--fb-ink-muted)] tabular-nums">
                  {item.time}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function buildSmoothSpline(pts: { x: number; y: number }[]): string {
  if (pts.length === 0) return "";
  if (pts.length === 1) return `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`;
  let d = `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
  }
  return d;
}

export function SkeuoAreaChart({
  title,
  subtitle,
  series,
  accentHex = "#D95F2B",
}: {
  title: string;
  subtitle?: string;
  series: { label: string; value: number }[];
  accentHex?: string;
}) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const gradId = useId();
  const safeSeries =
    series.length >= 2
      ? series
      : [
          { label: "Dush", value: 0 },
          { label: "Sesh", value: 0 },
        ];
  const maxVal = Math.max(1, ...safeSeries.map((s) => s.value));
  const w = 640;
  const h = 190;
  const padX = 28;
  const padY = 22;
  const plotW = w - padX * 2;
  const plotH = h - padY * 2;

  const points = safeSeries.map((item, idx) => {
    const x = padX + (idx / Math.max(1, safeSeries.length - 1)) * plotW;
    const y = padY + plotH - (item.value / maxVal) * plotH;
    return { x, y, ...item };
  });

  const linePath = buildSmoothSpline(points);
  const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${(padY + plotH).toFixed(1)} L ${points[0].x.toFixed(1)} ${(padY + plotH).toFixed(1)} Z`;

  return (
    <div className="skeuo-card rounded-[22px] p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-heading text-sm font-bold text-[var(--fb-ink)]">{title}</h3>
          {subtitle && (
            <p className="text-[11px] text-[var(--fb-ink-muted)]">{subtitle}</p>
          )}
        </div>
        {hoveredIdx !== null && points[hoveredIdx] ? (
          <div
            data-skeuo-dark="true"
            className="rounded-full skeuo-obsidian px-3 py-1 font-mono text-[11px] text-white tabular-nums"
          >
            {points[hoveredIdx].label}: {points[hoveredIdx].value}
          </div>
        ) : (
          <div className="rounded-full skeuo-well-sm px-2.5 py-0.5 font-mono text-[10px] text-[var(--fb-ink-muted)] tabular-nums">
            Spline • {safeSeries.length} nuqta
          </div>
        )}
      </div>

      <div className="rounded-2xl skeuo-well p-3">
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-44 overflow-visible" role="img" aria-label={title}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={accentHex} stopOpacity="0.34" />
              <stop offset="70%" stopColor={accentHex} stopOpacity="0.08" />
              <stop offset="100%" stopColor={accentHex} stopOpacity="0.0" />
            </linearGradient>
          </defs>
          {[0.25, 0.5, 0.75, 1].map((step) => {
            const gy = padY + plotH * step;
            return (
              <line
                key={step}
                x1={padX}
                x2={w - padX}
                y1={gy}
                y2={gy}
                stroke="currentColor"
                strokeOpacity="0.1"
                strokeDasharray="4 4"
              />
            );
          })}
          {hoveredIdx !== null && points[hoveredIdx] && (
            <line
              x1={points[hoveredIdx].x}
              x2={points[hoveredIdx].x}
              y1={padY}
              y2={padY + plotH}
              stroke={accentHex}
              strokeOpacity="0.45"
              strokeWidth="1.5"
              strokeDasharray="3 3"
            />
          )}
          <path d={areaPath} fill={`url(#${gradId})`} />
          <motion.path
            d={linePath}
            fill="none"
            stroke={accentHex}
            strokeWidth="2.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0.2, opacity: 0.4 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          />
          {points.map((pt, idx) => (
            <g
              key={pt.label}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              className="cursor-pointer"
            >
              {hoveredIdx === idx && (
                <circle cx={pt.x} cy={pt.y} r="10" fill={accentHex} fillOpacity="0.16" />
              )}
              <circle
                cx={pt.x}
                cy={pt.y}
                r={hoveredIdx === idx ? 5.5 : 3.5}
                fill="#FFFFFF"
                stroke={accentHex}
                strokeWidth="2.2"
              />
              <text
                x={pt.x}
                y={h - 2}
                textAnchor="middle"
                className="fill-[var(--fb-ink-muted)] text-[10px] font-mono"
              >
                {pt.label}
              </text>
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}
