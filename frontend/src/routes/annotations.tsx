import { createFileRoute } from "@tanstack/react-router";
import { Highlighter, MessageSquare, Sparkle } from "lucide-react";
import { GlassCard, PageHeader, ConfidenceMeter, EvidenceLink } from "@/components/ui-kit";

export const Route = createFileRoute("/annotations")({
  head: () => ({
    meta: [
      { title: "PDF Annotation Workspace — GlobalRisk AI" },
      { name: "description", content: "Highlight filing passages, add comments and accept AI-suggested annotations." },
      { property: "og:title", content: "PDF Annotation Workspace — GlobalRisk AI" },
      { property: "og:description", content: "Collaborative PDF highlighting with AI suggestions." },
    ],
  }),
  component: Annotations,
});

function Annotations() {
  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Annotations"
        title="PDF annotation workspace"
        description="Kaveri_Energy_FY2025_Annual_Report.pdf · page 42 of 264 · 3 collaborators"
      />
      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <GlassCard delay={0}>
          <div className="rounded-xl border border-border bg-card p-6 text-sm leading-relaxed">
            <p className="num mb-3 text-[10px] uppercase tracking-wider text-muted-foreground">Item 1A — Risk Factors</p>
            <p className="text-muted-foreground">
              We face risks associated with the transition to lower-carbon energy sources, including changes in
              policy, technology and financing availability.
            </p>
            <p
              className="mt-3 rounded-lg px-2 py-1.5"
              style={{ background: "color-mix(in oklab, var(--severity-critical) 15%, transparent)", boxShadow: "inset 2px 0 0 var(--severity-critical)" }}
            >
              Our transition plan contemplates capital expenditure materially in excess of currently committed
              facilities, and there can be no assurance such financing will be available on acceptable terms.
            </p>
            <p
              className="mt-3 rounded-lg px-2 py-1.5"
              style={{ background: "color-mix(in oklab, var(--primary) 14%, transparent)", boxShadow: "inset 2px 0 0 var(--primary)" }}
            >
              Failure to secure such financing could require us to defer projects or dispose of assets.
            </p>
          </div>
        </GlassCard>

        <div className="space-y-4">
          <GlassCard delay={0.05}>
            <div className="mb-3 flex items-center gap-2">
              <MessageSquare className="size-4 text-primary" />
              <h2 className="text-sm font-semibold">Comments</h2>
            </div>
            <div className="space-y-2.5">
              {[
                ["A. Nair", "Flag for credit committee — check covenant schedule.", "2h"],
                ["R. Iyer", "Compare with FY24 wording; assurance clause removed.", "5h"],
              ].map(([who, text, when]) => (
                <div key={who} className="rounded-xl border border-border/60 bg-secondary/25 p-3">
                  <div className="num flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span className="text-primary">{who}</span> · {when}
                  </div>
                  <p className="mt-1 text-xs">{text}</p>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard delay={0.1}>
            <div className="mb-3 flex items-center gap-2">
              <Sparkle className="size-4 text-primary" />
              <h2 className="text-sm font-semibold">AI suggested highlights</h2>
            </div>
            <div className="space-y-2.5">
              {[
                ["Financing contingency clause", 0.94],
                ["Asset disposal consequence", 0.88],
              ].map(([t, c]) => (
                <div key={t as string} className="rounded-xl border border-primary/25 bg-primary/5 p-3">
                  <div className="flex items-center gap-2">
                    <Highlighter className="size-3.5 text-primary" />
                    <p className="text-xs font-medium">{t as string}</p>
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <ConfidenceMeter value={c as number} />
                    <EvidenceLink source="p.42" />
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
