import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import { ShieldCheck, Users } from "lucide-react";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — GlobalRisk AI" },
      { name: "description", content: "Sign in to your GlobalRisk AI team workspace to access risk intelligence." },
      { property: "og:title", content: "Sign in — GlobalRisk AI" },
      { property: "og:description", content: "Access your GlobalRisk AI team workspace." },
    ],
  }),
  component: Auth,
});

function Auth() {
  return (
    <div className="relative grid min-h-screen place-items-center px-4 py-10">
      <div className="grid-bg pointer-events-none absolute inset-0 opacity-30" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[420px]" style={{ background: "var(--gradient-hero)" }} />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="panel relative w-full max-w-md p-8"
      >
        <div className="flex items-center gap-2.5">
          <span className="grid size-10 place-items-center rounded-xl text-sm font-bold" style={{ background: "var(--gradient-primary)", color: "var(--primary-foreground)" }}>
            GR
          </span>
          <div>
            <p className="text-sm font-semibold">GlobalRisk AI</p>
            <p className="num text-[10px] text-muted-foreground">Financial Risk Intelligence</p>
          </div>
        </div>
        <h1 className="mt-6 text-xl font-semibold">Sign in to your workspace</h1>
        <p className="mt-1 text-xs text-muted-foreground">Use your corporate account to access team intelligence.</p>

        <div className="mt-6 space-y-3">
          <input placeholder="Work email" className="w-full rounded-xl border border-border bg-secondary/30 px-3 py-2.5 text-sm outline-none focus:border-primary/50" />
          <input type="password" placeholder="Password" className="w-full rounded-xl border border-border bg-secondary/30 px-3 py-2.5 text-sm outline-none focus:border-primary/50" />
          <div className="flex items-center gap-2 rounded-xl border border-border bg-secondary/30 px-3 py-2.5 text-sm">
            <Users className="size-4 text-primary" />
            <select className="flex-1 bg-transparent text-sm outline-none">
              <option>Credit Research — Mumbai</option>
              <option>Global Macro — London</option>
              <option>ESG Team — Singapore</option>
            </select>
          </div>
          <Link
            to="/"
            className="num block rounded-xl px-4 py-2.5 text-center text-sm font-medium"
            style={{ background: "var(--gradient-primary)", color: "var(--primary-foreground)", boxShadow: "var(--shadow-glow)" }}
          >
            Continue to dashboard
          </Link>
        </div>

        <p className="num mt-5 flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <ShieldCheck className="size-3.5 text-primary" /> SSO, SOC 2 Type II and audit logging enabled
        </p>
      </motion.div>
    </div>
  );
}
