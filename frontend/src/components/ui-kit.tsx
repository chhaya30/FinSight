import { type ReactNode } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";
import { severityMeta, type Severity } from "@/lib/mock-data";

export function GlassCard({
  className,
  children,
  delay = 0,
  interactive = true,
}: {
  className?: string;
  children: ReactNode;
  delay?: number;
  interactive?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "panel p-5",
        interactive && "transition-colors duration-300 hover:border-primary/40",
        className,
      )}
    >
      {children}
    </motion.div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        {eyebrow && (
          <p className="num mb-2 text-[11px] uppercase tracking-[0.22em] text-primary">{eyebrow}</p>
        )}
        <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">{title}</h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const meta = severityMeta[severity];
  return (
    <span
      className="num inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider"
      style={{
        color: meta.color,
        background: `color-mix(in oklab, ${meta.color} 14%, transparent)`,
        border: `1px solid color-mix(in oklab, ${meta.color} 34%, transparent)`,
      }}
    >
      <span className="size-1.5 rounded-full" style={{ background: meta.color }} />
      {meta.label}
    </span>
  );
}

export function ConfidenceMeter({ value, label = "confidence" }: { value: number; label?: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="h-full rounded-full"
          style={{ background: "var(--gradient-primary)" }}
        />
      </div>
      <span className="num text-[11px] text-muted-foreground">
        {pct}% {label}
      </span>
    </div>
  );
}

export function StatCard({
  label,
  value,
  delta,
  hint,
  delay = 0,
}: {
  label: string;
  value: string;
  delta?: number;
  hint?: string;
  delay?: number;
}) {
  return (
    <GlassCard delay={delay} className="relative overflow-hidden">
      <div
        className="pointer-events-none absolute -right-10 -top-10 size-28 rounded-full opacity-40 blur-2xl"
        style={{ background: "var(--gradient-primary)" }}
      />
      <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="num mt-3 text-3xl font-semibold">{value}</p>
      <div className="mt-2 flex items-center gap-2 text-xs">
        {delta !== undefined && (
          <span
            className="num font-medium"
            style={{ color: delta >= 0 ? "var(--negative)" : "var(--positive)" }}
          >
            {delta >= 0 ? "▲" : "▼"} {Math.abs(delta)}%
          </span>
        )}
        {hint && <span className="text-muted-foreground">{hint}</span>}
      </div>
    </GlassCard>
  );
}

export function EvidenceLink({ source }: { source: string }) {
  return (
    <button className="num inline-flex items-center gap-1 rounded-md border border-border/70 bg-secondary/40 px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:border-primary/50 hover:text-primary">
      ⧉ {source}
    </button>
  );
}

export function Sparkline({ points, color = "var(--primary)" }: { points: number[]; color?: string }) {
  const max = Math.max(...points);
  const min = Math.min(...points);
  const d = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * 100;
      const y = 30 - ((p - min) / (max - min || 1)) * 28;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 100 30" className="h-8 w-full" preserveAspectRatio="none">
      <motion.path
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.1, ease: "easeOut" }}
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={1.6}
        strokeLinecap="round"
      />
    </svg>
  );
}
