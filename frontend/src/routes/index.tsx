import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertTriangle, ArrowUpRight, FileSearch, RefreshCw, WalletCards } from "lucide-react";
import { GlassCard, PageHeader, StatCard } from "@/components/ui-kit";

type EvidenceReference = {
  side: "year_1" | "year_2";
  document_id: string;
  report_year?: number;
  page: number;
  chunk_id?: string;
};

type Claim = { text: string; evidence: EvidenceReference[] };
type FinancialMetric = {
  metric_name: string;
  value?: number;
  unit: string;
  report_year: number;
  document_id: string;
  page: number;
};
type FinancialChange = {
  metric_name: string;
  previous_value?: number;
  current_value?: number;
  percent_change?: number;
  direction: "INCREASED" | "DECREASED" | "UNCHANGED" | "UNAVAILABLE";
  supporting_evidence: EvidenceReference[];
};
type RiskChange = {
  year_1_risk_id?: string;
  year_2_risk_id?: string;
  title?: string;
  category?: string;
  severity_previous?: string;
  severity_current?: string;
  change_type: string;
  what_changed: { name: string; before?: unknown; after?: unknown }[];
  why_it_matters: Claim;
  confidence: number;
  evidence: EvidenceReference[];
};
type DashboardData = {
  company: { id: string; name: string; sector?: string };
  reports: { year: number; report_id: string; source_file: string }[];
  total_risks_previous: number;
  total_risks_current: number;
  risk_counts_by_status: Record<string, number>;
  key_risk_changes: RiskChange[];
  executive_summary: Claim;
  business_impact: Claim;
  financial_metrics: FinancialMetric[];
  financial_changes: FinancialChange[];
  risk_financial_correlations: {
    metric_name: string;
    explanation: string;
    supporting_evidence: EvidenceReference[];
  }[];
  evidence: EvidenceReference[];
};

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Executive Dashboard — GlobalRisk AI" },
      {
        name: "description",
        content: "Evidence-linked executive risk and financial intelligence.",
      },
    ],
  }),
  component: Dashboard,
});

const statuses = ["NEW", "REMOVED", "UNCHANGED", "MODIFIED", "ESCALATED", "DE-ESCALATED"];

function dashboardConfig() {
  const params = new URLSearchParams(typeof window === "undefined" ? "" : window.location.search);
  return {
    companyId: params.get("company_id") ?? import.meta.env.VITE_DASHBOARD_COMPANY_ID ?? "",
    previous: Number(
      params.get("year_previous") ?? import.meta.env.VITE_DASHBOARD_YEAR_PREVIOUS ?? 2024,
    ),
    current: Number(
      params.get("year_current") ?? import.meta.env.VITE_DASHBOARD_YEAR_CURRENT ?? 2025,
    ),
  };
}

function evidenceLabel(reference: EvidenceReference) {
  return `${reference.document_id} · p.${reference.page}${reference.chunk_id ? ` · ${reference.chunk_id}` : ""}`;
}

function Dashboard() {
  const { companyId, previous, current } = dashboardConfig();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(Boolean(companyId));
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(() => {
    if (!companyId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    const base = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
    const query = new URLSearchParams({
      company_id: companyId,
      year_previous: String(previous),
      year_current: String(current),
    });
    fetch(`${base}/dashboard/executive?${query}`)
      .then(async (response) => {
        if (!response.ok)
          throw new Error(
            (await response.text()) || `Dashboard request failed (${response.status})`,
          );
        return response.json() as Promise<DashboardData>;
      })
      .then(setData)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Dashboard request failed"),
      )
      .finally(() => setLoading(false));
  }, [companyId, current, previous]);

  useEffect(() => loadDashboard(), [loadDashboard]);

  const chartData = useMemo(
    () => statuses.map((status) => ({ status, count: data?.risk_counts_by_status[status] ?? 0 })),
    [data],
  );

  if (loading)
    return (
      <DashboardState
        icon={<RefreshCw className="size-5 animate-spin" />}
        title="Loading dashboard"
        detail="Composing evidence-linked risk and financial intelligence."
      />
    );
  if (error)
    return (
      <DashboardState
        icon={<AlertTriangle className="size-5" />}
        title="Dashboard unavailable"
        detail={error}
        action={loadDashboard}
      />
    );
  if (!data)
    return (
      <DashboardState
        icon={<FileSearch className="size-5" />}
        title="Dashboard needs a company"
        detail="Open this page with company_id, year_previous, and year_current query parameters or configure the dashboard environment."
      />
    );

  const counts = data.risk_counts_by_status;
  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Executive Dashboard"
        title={data.company.name}
        description={`${data.company.sector ?? "Company risk intelligence"} · FY${previous} to FY${current} · source-linked analysis`}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard
          label="Current risks"
          value={String(data.total_risks_current)}
          hint={`FY${current}`}
        />
        <StatCard label="New" value={String(counts.NEW ?? 0)} hint="disclosures" />
        <StatCard label="Removed" value={String(counts.REMOVED ?? 0)} hint="disclosures" />
        <StatCard label="Escalated" value={String(counts.ESCALATED ?? 0)} hint="severity" />
        <StatCard label="Modified" value={String(counts.MODIFIED ?? 0)} hint="disclosures" />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <GlassCard className="xl:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Risk evolution</h2>
              <p className="text-xs text-muted-foreground">
                Phase 2.1 records, grouped by deterministic status
              </p>
            </div>
            <span className="num text-xs text-muted-foreground">
              {data.total_risks_previous} → {data.total_risks_current}
            </span>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData} margin={{ left: -20, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="status"
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: "var(--muted)", opacity: 0.25 }}
                contentStyle={{
                  background: "var(--popover)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  fontSize: 12,
                }}
              />
              <Bar dataKey="count" fill="var(--chart-1)" radius={[5, 5, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>
        <ClaimCard title="Executive summary" claim={data.executive_summary} />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <ClaimCard title="Business impact" claim={data.business_impact} />
        <GlassCard>
          <div className="mb-4 flex items-center gap-2">
            <WalletCards className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Financial health</h2>
          </div>
          {data.financial_changes.length === 0 ? (
            <EmptyText text="No persisted financial comparison is available for these reports." />
          ) : (
            <div className="space-y-2.5">
              {data.financial_changes.map((change) => (
                <div
                  key={change.metric_name}
                  className="flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-secondary/25 p-3"
                >
                  <div>
                    <p className="text-xs font-medium">{change.metric_name.replaceAll("_", " ")}</p>
                    <p className="num text-[10px] text-muted-foreground">
                      {formatValue(change.previous_value)} → {formatValue(change.current_value)}
                    </p>
                  </div>
                  <span
                    className="num text-xs"
                    style={{
                      color:
                        change.direction === "DECREASED" ? "var(--negative)" : "var(--positive)",
                    }}
                  >
                    {change.percent_change === undefined || change.percent_change === null
                      ? change.direction
                      : `${change.percent_change > 0 ? "+" : ""}${change.percent_change}%`}
                  </span>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>

      <GlassCard className="mt-4 overflow-x-auto">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Key risk changes</h2>
          <span className="num text-xs text-muted-foreground">
            {data.key_risk_changes.length} records
          </span>
        </div>
        {data.key_risk_changes.length === 0 ? (
          <EmptyText text="No evolution records were returned." />
        ) : (
          <div className="min-w-[760px] divide-y divide-border/60">
            {data.key_risk_changes.map((change, index) => (
              <div
                key={`${change.year_1_risk_id ?? "new"}-${change.year_2_risk_id ?? "removed"}-${index}`}
                className="grid grid-cols-[1.5fr_0.8fr_1.8fr_1fr] gap-4 py-3"
              >
                <div>
                  <p className="text-xs font-medium">{change.title ?? "Untitled risk"}</p>
                  <p className="mt-1 text-[10px] text-muted-foreground">
                    {change.category ?? "Uncategorized"} · {change.severity_previous ?? "—"} →{" "}
                    {change.severity_current ?? "—"}
                  </p>
                </div>
                <div>
                  <span className="num rounded-md border border-primary/30 px-2 py-1 text-[10px] text-primary">
                    {change.change_type}
                  </span>
                  <p className="mt-2 num text-[10px] text-muted-foreground">
                    {Math.round(change.confidence * 100)}% confidence
                  </p>
                </div>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  {change.why_it_matters.text}
                </p>
                <div className="space-y-1">
                  {change.evidence.map((reference) => (
                    <p
                      key={`${reference.side}-${reference.document_id}-${reference.page}`}
                      className="num flex items-center gap-1 text-[10px] text-muted-foreground"
                    >
                      <FileSearch className="size-3 text-primary" />
                      {evidenceLabel(reference)}
                    </p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>

      <GlassCard className="mt-4">
        <div className="mb-3 flex items-center gap-2">
          <FileSearch className="size-4 text-primary" />
          <h2 className="text-sm font-semibold">Source coverage</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {data.evidence.length === 0 ? (
            <EmptyText text="No source references returned." />
          ) : (
            data.evidence.map((reference) => (
              <span
                key={`${reference.side}-${reference.document_id}-${reference.page}-${reference.chunk_id ?? ""}`}
                className="num rounded-md border border-border bg-secondary/40 px-2 py-1 text-[10px] text-muted-foreground"
              >
                {evidenceLabel(reference)}
              </span>
            ))
          )}
        </div>
      </GlassCard>
      <div className="mt-4 flex justify-end">
        <a href="/evolution" className="inline-flex items-center gap-1 text-xs text-primary">
          Open full evolution view <ArrowUpRight className="size-3" />
        </a>
      </div>
    </div>
  );
}

function ClaimCard({ title, claim }: { title: string; claim: Claim }) {
  return (
    <GlassCard>
      <h2 className="mb-3 text-sm font-semibold">{title}</h2>
      <p className="text-sm leading-relaxed text-muted-foreground">{claim.text}</p>
      <div className="mt-4 flex flex-wrap gap-1.5">
        {claim.evidence.length === 0 ? (
          <EmptyText text="No evidence references" />
        ) : (
          claim.evidence.map((reference) => (
            <span
              key={`${reference.side}-${reference.document_id}-${reference.page}`}
              className="num rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground"
            >
              {evidenceLabel(reference)}
            </span>
          ))
        )}
      </div>
    </GlassCard>
  );
}

function DashboardState({
  icon,
  title,
  detail,
  action,
}: {
  icon: ReactNode;
  title: string;
  detail: string;
  action?: () => void;
}) {
  return (
    <div className="mx-auto flex min-h-[55vh] max-w-xl items-center justify-center">
      <GlassCard interactive={false} className="w-full text-center">
        <div className="mx-auto grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
          {icon}
        </div>
        <h1 className="mt-4 text-lg font-semibold">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{detail}</p>
        {action && (
          <button
            onClick={action}
            className="mt-5 inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs hover:border-primary/50"
          >
            <RefreshCw className="size-3" /> Retry
          </button>
        )}
      </GlassCard>
    </div>
  );
}

function EmptyText({ text }: { text: string }) {
  return <span className="text-xs text-muted-foreground">{text}</span>;
}
function formatValue(value?: number) {
  return value === undefined || value === null
    ? "—"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
}
