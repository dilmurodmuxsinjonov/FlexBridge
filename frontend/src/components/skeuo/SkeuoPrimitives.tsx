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

const TONE_MAP: Record<StatTone, { badgeBg: string; iconText: string; barFill: string }> = {
  orange: {
    badgeBg: "bg-[#D95F2B]/12 border-[#D95F2B]/25",
    iconText: "text-[#D95F2B] dark:text-orange-400",
    barFill: "from-[#EA6A32] to-[#C84B18]",
  },
  emerald: {
    badgeBg: "bg-emerald-600/12 border-emerald-600/25",
    iconText: "text-emerald-700 dark:text-emerald-400",
    barFill: "from-emerald-500 to-emerald-700",
  },
  sky: {
    badgeBg: "bg-sky-600/12 border-sky-600/25",
    iconText: "text-sky-700 dark:text-sky-400",
    barFill: "from-sky-400 to-sky-600",
  },
  indigo: {
    badgeBg: "bg-indigo-600/12 border-indigo-600/25",
    iconText: "text-indigo-700 dark:text-indigo-400",
    barFill: "from-indigo-400 to-indigo-600",
  },
  amber: {
    badgeBg: "bg-amber-600/12 border-amber-600/25",
    iconText: "text-amber-700 dark:text-amber-400",
    barFill: "from-amber-400 to-amber-600",
  },
  slate: {
    badgeBg: "bg-zinc-500/12 border-zinc-500/25",
    iconText: "text-zinc-700 dark:text-zinc-300",
    barFill: "from-zinc-500 to-zinc-700",
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
      className={`skeuo-card w-full rounded-2xl p-4 sm:p-5 text-left transition-all ${
        active ? "ring-2 ring-[var(--fb-accent)]" : ""
      } ${onClick ? "cursor-pointer active:scale-[0.985]" : ""}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <p className="text-xs font-medium text-[var(--fb-ink-secondary)] truncate">{title}</p>
          <p className="font-heading text-2xl sm:text-[26px] font-bold tracking-tight text-[var(--fb-ink)] tabular-nums">
            {value}
          </p>
        </div>
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border skeuo-well-sm ${palette.badgeBg} ${palette.iconText}`}
        >
          <Icon className="h-4.5 w-4.5" aria-hidden="true" />
        </div>
      </div>

      {(delta || subtitle) && (
        <div className="mt-3.5 pt-3 border-t border-[var(--fb-hairline)] flex flex-wrap items-center justify-between gap-2 text-[11px]">
          {delta ? (
            <span
              className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 font-mono font-semibold tabular-nums ${
                deltaPositive
                  ? "bg-emerald-600/12 text-emerald-700 dark:text-emerald-400"
                  : "bg-rose-600/12 text-rose-700 dark:text-rose-400"
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
            <span />
          )}
          {subtitle && (
            <span className="text-[var(--fb-ink-muted)] truncate">{subtitle}</span>
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
    <div className="flex items-center justify-between gap-3">
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
        className={`relative inline-flex h-7 w-13 shrink-0 items-center rounded-full p-1 transition-colors skeuo-well focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--fb-accent)] disabled:opacity-50 ${
          checked
            ? "bg-[#1C1B19] dark:bg-white/15"
            : "bg-[var(--fb-well-deep)]"
        }`}
        style={{ width: "50px" }}
      >
        <motion.span
          layout
          transition={{ type: "spring", stiffness: 500, damping: 32 }}
          className={`flex h-5 w-5 items-center justify-center rounded-full bg-white shadow-[0_2px_6px_rgba(0,0,0,0.28),inset_0_1px_0_rgba(255,255,255,1)] ${
            checked ? "ml-auto" : "mr-auto"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full transition-colors ${
              checked ? ledColor : "bg-zinc-300"
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
}

export function SkeuoVerticalMeter({
  title,
  percentage,
  amountLabel,
  subtitle,
  tone = "orange",
  onAction,
  actionLabel,
}: SkeuoVerticalMeterProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(percentage)));
  const palette = TONE_MAP[tone];

  return (
    <div className="skeuo-card rounded-2xl p-4 flex flex-col items-center text-center gap-3">
      {/* Vertical Recessed Trough with Liquid Capsule Fill (from video 00:04) */}
      <div className="relative h-32 w-14 rounded-full p-1.5 skeuo-well overflow-hidden flex items-end justify-center">
        <motion.div
          initial={{ height: "0%" }}
          animate={{ height: `${Math.max(18, clamped)}%` }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
          className={`w-full rounded-full bg-gradient-to-b ${palette.barFill} shadow-[0_2px_8px_rgba(0,0,0,0.18),inset_0_1px_1px_rgba(255,255,255,0.45)] relative`}
        />
        {/* Floating Raised Percentage Medallion */}
        <div
          className="absolute inset-0 m-auto h-9 w-9 rounded-full skeuo-card flex items-center justify-center shadow-[0_4px_12px_rgba(24,20,14,0.18)]"
          style={{
            top: clamped > 55 ? "28%" : "52%",
          }}
        >
          <span className="font-mono text-[11px] font-bold text-[var(--fb-ink)] tabular-nums">
            {clamped}%
          </span>
        </div>
      </div>

      <div className="space-y-0.5 w-full min-w-0">
        <div className="text-xs font-semibold text-[var(--fb-ink)] truncate">{title}</div>
        <div className="font-mono text-[11px] font-medium text-[var(--fb-ink-secondary)] tabular-nums truncate">
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
                className="absolute inset-0 rounded-xl skeuo-card shadow-[0_3px_10px_rgba(24,20,14,0.10)]"
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
    <div className="skeuo-card rounded-2xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <h3 className="font-heading text-sm font-bold text-[var(--fb-ink)]">{title}</h3>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--fb-ink-muted)]">
          Live Stream
        </span>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl skeuo-well p-4 text-xs text-[var(--fb-ink-muted)] text-center">
          {emptyText}
        </div>
      ) : (
        <div className="space-y-2.5">
          {items.map((item) => {
            const dotClass =
              item.status === "warn"
                ? "bg-amber-500"
                : item.status === "ok"
                  ? "bg-emerald-500"
                  : "bg-[#D95F2B]";
            return (
              <div
                key={item.id}
                className="rounded-xl skeuo-well px-3.5 py-2.5 flex items-start justify-between gap-3"
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
  const h = 180;
  const padX = 24;
  const padY = 20;
  const plotW = w - padX * 2;
  const plotH = h - padY * 2;

  const points = safeSeries.map((item, idx) => {
    const x = padX + (idx / Math.max(1, safeSeries.length - 1)) * plotW;
    const y = padY + plotH - (item.value / maxVal) * plotH;
    return { x, y, ...item };
  });

  const linePath = points
    .map((pt, i) => `${i === 0 ? "M" : "L"} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`)
    .join(" ");
  const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${(padY + plotH).toFixed(1)} L ${points[0].x.toFixed(1)} ${(padY + plotH).toFixed(1)} Z`;

  return (
    <div className="skeuo-card rounded-2xl p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-heading text-sm font-bold text-[var(--fb-ink)]">{title}</h3>
          {subtitle && (
            <p className="text-[11px] text-[var(--fb-ink-muted)]">{subtitle}</p>
          )}
        </div>
        {hoveredIdx !== null && points[hoveredIdx] && (
          <div className="rounded-full bg-[#161618] text-white px-3 py-1 font-mono text-[11px] tabular-nums shadow">
            {points[hoveredIdx].label}: {points[hoveredIdx].value}
          </div>
        )}
      </div>

      <div className="rounded-xl skeuo-well p-3">
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-44 overflow-visible" role="img" aria-label={title}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={accentHex} stopOpacity="0.32" />
              <stop offset="100%" stopColor={accentHex} stopOpacity="0.02" />
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
          <path d={areaPath} fill={`url(#${gradId})`} />
          <path
            d={linePath}
            fill="none"
            stroke={accentHex}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {points.map((pt, idx) => (
            <g
              key={pt.label}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              className="cursor-pointer"
            >
              <circle
                cx={pt.x}
                cy={pt.y}
                r={hoveredIdx === idx ? 5.5 : 3.5}
                fill="#FFFFFF"
                stroke={accentHex}
                strokeWidth="2"
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
