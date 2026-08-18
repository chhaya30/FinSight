import { useEffect, useState, type ReactNode } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import { AnimatePresence, motion } from "motion/react";
import {
  LayoutDashboard,
  FolderOpen,
  BrainCircuit,
  FileSearch,
  GitCompareArrows,
  LineChart,
  Newspaper,
  Building2,
  Compass,
  ScanSearch,
  FileDown,
  Bookmark,
  Highlighter,
  Moon,
  Sun,
  Command as CommandIcon,
  Search,
  Bell,
  PanelLeftClose,
  PanelLeft,
  Bot,
  Send,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

export const navGroups = [
  {
    label: "Intelligence",
    items: [
      { to: "/", label: "Executive Dashboard", icon: LayoutDashboard },
      { to: "/repository", label: "Document Repository", icon: FolderOpen },
      { to: "/engine", label: "Risk Engine", icon: BrainCircuit },
      { to: "/evidence", label: "Evidence Viewer", icon: FileSearch },
      { to: "/evolution", label: "Risk Evolution", icon: GitCompareArrows },
    ],
  },
  {
    label: "Markets",
    items: [
      { to: "/financials", label: "Financial Health", icon: LineChart },
      { to: "/market", label: "Market Intelligence", icon: Newspaper },
      { to: "/industry", label: "Industry Intelligence", icon: Building2 },
    ],
  },
  {
    label: "Discovery",
    items: [
      { to: "/explorer", label: "Risk Explorer", icon: Compass },
      { to: "/scanner", label: "Multi-Factor Scanner", icon: ScanSearch },
      { to: "/reports", label: "Report Generator", icon: FileDown },
    ],
  },
  {
    label: "Workspace",
    items: [
      { to: "/workspace", label: "Analyst Workspace", icon: Bookmark },
      { to: "/annotations", label: "PDF Annotations", icon: Highlighter },
    ],
  },
];

const allNav = navGroups.flatMap((g) => g.items);

function useTheme() {
  const [dark, setDark] = useState(true);
  useEffect(() => {
    const stored = localStorage.getItem("gr-theme");
    const isDark = stored ? stored === "dark" : true;
    setDark(isDark);
    document.documentElement.classList.toggle("dark", isDark);
  }, []);
  const toggle = () => {
    setDark((d) => {
      const next = !d;
      document.documentElement.classList.toggle("dark", next);
      localStorage.setItem("gr-theme", next ? "dark" : "light");
      return next;
    });
  };
  return { dark, toggle };
}

function AssistantPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          initial={{ x: 420, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 420, opacity: 0 }}
          transition={{ type: "spring", stiffness: 260, damping: 30 }}
          className="panel fixed bottom-4 right-4 top-20 z-50 flex w-[min(380px,calc(100vw-2rem))] flex-col overflow-hidden"
        >
          <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="grid size-7 place-items-center rounded-lg" style={{ background: "var(--gradient-primary)" }}>
                <Bot className="size-4 text-primary-foreground" />
              </span>
              <div>
                <p className="text-sm font-medium">Risk Copilot</p>
                <p className="num text-[10px] text-muted-foreground">grounded on 1,284 filings</p>
              </div>
            </div>
            <button onClick={onClose} className="rounded-md p-1 text-muted-foreground hover:bg-secondary">
              <X className="size-4" />
            </button>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto p-4 text-sm">
            <div className="rounded-xl bg-secondary/50 p-3">
              <p className="text-muted-foreground">
                Ask about any disclosure. Every answer cites the source page and a confidence score.
              </p>
            </div>
            <div className="rounded-xl border border-primary/25 bg-primary/5 p-3">
              <p className="font-medium">Which portfolio names added climate risk language in FY25?</p>
            </div>
            <div className="space-y-2 rounded-xl bg-secondary/40 p-3">
              <p>
                Two names introduced new climate disclosures: <b>Kaveri Energy</b> (transition capex financing,
                critical) and <b>Verdant Agri</b> (biological asset valuation, medium).
              </p>
              <div className="num flex flex-wrap gap-1.5 text-[10px] text-muted-foreground">
                <span className="rounded-md border border-border px-1.5 py-0.5">⧉ FY2025 AR p.42</span>
                <span className="rounded-md border border-border px-1.5 py-0.5">⧉ BRSR p.57</span>
                <span className="rounded-md border border-primary/40 px-1.5 py-0.5 text-primary">94% confidence</span>
              </div>
            </div>
          </div>
          <div className="border-t border-border/60 p-3">
            <div className="flex items-center gap-2 rounded-xl border border-border bg-background/60 px-3 py-2">
              <input
                placeholder="Ask the copilot…"
                className="num flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />
              <Send className="size-4 text-primary" />
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { dark, toggle } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [assistant, setAssistant] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j") {
        e.preventDefault();
        setAssistant((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (pathname.startsWith("/auth")) return <>{children}</>;

  return (
    <div className="relative min-h-screen">
      <div className="grid-bg pointer-events-none fixed inset-0 opacity-[0.35]" />
      <div
        className="pointer-events-none fixed inset-x-0 top-0 h-[420px]"
        style={{ background: "var(--gradient-hero)" }}
      />

      <div className="relative flex min-h-screen">
        <motion.aside
          animate={{ width: collapsed ? 76 : 256 }}
          transition={{ type: "spring", stiffness: 280, damping: 32 }}
          className="sticky top-0 hidden h-screen shrink-0 flex-col border-r border-border/60 bg-sidebar/70 backdrop-blur-xl lg:flex"
        >
          <div className="flex h-16 items-center gap-2.5 px-4">
            <span
              className="grid size-9 shrink-0 place-items-center rounded-xl text-sm font-bold"
              style={{ background: "var(--gradient-primary)", color: "var(--primary-foreground)" }}
            >
              GR
            </span>
            {!collapsed && (
              <div className="overflow-hidden">
                <p className="whitespace-nowrap text-sm font-semibold tracking-tight">GlobalRisk AI</p>
                <p className="num whitespace-nowrap text-[10px] text-muted-foreground">Risk Intelligence</p>
              </div>
            )}
          </div>

          <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-2">
            {navGroups.map((group) => (
              <div key={group.label}>
                {!collapsed && (
                  <p className="num mb-1.5 px-2 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                    {group.label}
                  </p>
                )}
                <div className="space-y-0.5">
                  {group.items.map((item) => {
                    const active = pathname === item.to;
                    return (
                      <Link
                        key={item.to}
                        to={item.to}
                        className={cn(
                          "group relative flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-colors",
                          active
                            ? "bg-sidebar-accent text-sidebar-accent-foreground"
                            : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
                        )}
                      >
                        {active && (
                          <motion.span
                            layoutId="nav-active"
                            className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary"
                          />
                        )}
                        <item.icon className={cn("size-4 shrink-0", active && "text-primary")} />
                        {!collapsed && <span className="truncate">{item.label}</span>}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </nav>

          <div className="border-t border-border/60 p-3">
            <button
              onClick={() => setCollapsed((c) => !c)}
              className="flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-sm text-muted-foreground hover:bg-sidebar-accent/60"
            >
              {collapsed ? <PanelLeft className="size-4" /> : <PanelLeftClose className="size-4" />}
              {!collapsed && <span>Collapse</span>}
            </button>
          </div>
        </motion.aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-40 flex h-16 items-center gap-3 border-b border-border/60 bg-background/70 px-4 backdrop-blur-xl md:px-6">
            <span className="grid size-8 place-items-center rounded-lg text-xs font-bold lg:hidden" style={{ background: "var(--gradient-primary)", color: "var(--primary-foreground)" }}>
              GR
            </span>
            <button
              onClick={() => setPaletteOpen(true)}
              className="flex flex-1 items-center gap-2 rounded-xl border border-border/70 bg-secondary/40 px-3 py-2 text-sm text-muted-foreground transition-colors hover:border-primary/40 md:max-w-md"
            >
              <Search className="size-4" />
              <span className="truncate">Search companies, risks, filings…</span>
              <span className="num ml-auto hidden items-center gap-1 rounded-md border border-border px-1.5 py-0.5 text-[10px] md:flex">
                <CommandIcon className="size-3" />K
              </span>
            </button>
            <div className="ml-auto flex items-center gap-1.5">
              <button
                onClick={() => setAssistant((a) => !a)}
                className="num hidden items-center gap-2 rounded-xl border border-primary/40 bg-primary/10 px-3 py-2 text-xs text-primary transition-colors hover:bg-primary/20 sm:flex"
              >
                <Bot className="size-4" /> Copilot
              </button>
              <button className="relative rounded-lg p-2 text-muted-foreground hover:bg-secondary">
                <Bell className="size-4" />
                <span className="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-destructive" />
              </button>
              <button onClick={toggle} className="rounded-lg p-2 text-muted-foreground hover:bg-secondary">
                {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
              </button>
              <Link
                to="/auth"
                className="ml-1 grid size-8 place-items-center rounded-full border border-border bg-secondary text-[11px] font-semibold"
              >
                AN
              </Link>
            </div>
          </header>

          <main className="min-w-0 flex-1 px-4 py-6 md:px-6 lg:px-8">{children}</main>

          <nav className="sticky bottom-0 z-40 flex gap-1 overflow-x-auto border-t border-border/60 bg-background/85 px-2 py-2 backdrop-blur-xl lg:hidden">
            {allNav.slice(0, 6).map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex min-w-16 flex-col items-center gap-1 rounded-lg px-2 py-1.5 text-[10px]",
                  pathname === item.to ? "text-primary" : "text-muted-foreground",
                )}
              >
                <item.icon className="size-4" />
                {item.label.split(" ")[0]}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      <AssistantPanel open={assistant} onClose={() => setAssistant(false)} />

      <CommandDialog open={paletteOpen} onOpenChange={setPaletteOpen}>
        <CommandInput placeholder="Jump to a module, company or risk…" />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          {navGroups.map((group) => (
            <CommandGroup key={group.label} heading={group.label}>
              {group.items.map((item) => (
                <CommandItem key={item.to} value={item.label} asChild>
                  <Link to={item.to} onClick={() => setPaletteOpen(false)}>
                    <item.icon className="mr-2 size-4" />
                    {item.label}
                  </Link>
                </CommandItem>
              ))}
            </CommandGroup>
          ))}
        </CommandList>
      </CommandDialog>
    </div>
  );
}
