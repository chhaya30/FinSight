import { useState, useEffect, useCallback, useRef } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "motion/react";
import {
  UploadCloud,
  FileText,
  ScanLine,
  Search,
  CheckCircle2,
  Loader2,
  Clock,
  XCircle,
  AlertCircle,
  RefreshCw,
  ChevronRight,
  Building2,
  Globe,
  Calendar,
  FileCheck,
  RotateCcw,
  ArrowRight,
  Check,
  Plus,
} from "lucide-react";
import { GlassCard, PageHeader } from "@/components/ui-kit";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type DocumentStatusResponse } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Company = {
  id: string;
  name: string;
  ticker_symbol: string | null;
  sector: string | null;
  listed_exchange: string | null;
  country: string | null;
  market_cap: number | null;
  currency: string | null;
  created_at: string;
  updated_at: string;
};

export const Route = createFileRoute("/repository")({
  head: () => ({
    meta: [
      { title: "Corporate Intelligence Repository — GlobalRisk AI" },
      { name: "description", content: "Drag-and-drop filing ingestion with OCR, versioning, metadata and processing status." },
      { property: "og:title", content: "Corporate Intelligence Repository — GlobalRisk AI" },
      { property: "og:description", content: "Ingest, OCR and version multi-company, multi-year filings." },
    ],
  }),
  component: Repository,
});

const MARKETS = [
  { value: "SEC", label: "SEC (US)" },
  { value: "BSE", label: "BSE (India)" },
  { value: "NSE", label: "NSE (India)" },
  { value: "LSE", label: "LSE (UK)" },
  { value: "HKEX", label: "HKEX (Hong Kong)" },
  { value: "TSX", label: "TSX (Canada)" },
  { value: "ASX", label: "ASX (Australia)" },
  { value: "SGX", label: "SGX (Singapore)" },
  { value: "TSE", label: "TSE (Japan)" },
  { value: "FWB", label: "FWB (Germany)" },
  { value: "EURONEXT", label: "Euronext (EU)" },
];

const REPORT_TYPES = [
  { value: "10-K", label: "10-K (SEC)" },
  { value: "10-Q", label: "10-Q (SEC)" },
  { value: "20-F", label: "20-F (SEC Foreign)" },
  { value: "annual_report", label: "Annual Report" },
  { value: "brsr", label: "BRSR (India)" },
  { value: "esg_report", label: "ESG/Sustainability Report" },
];

const statusMeta: Record<string, { icon: typeof Clock; color: string; label: string }> = {
  completed: { icon: CheckCircle2, color: "var(--positive)", label: "Completed" },
  processing: { icon: Loader2, color: "var(--severity-medium)", label: "Processing" },
  pending: { icon: Clock, color: "var(--muted-foreground)", label: "Pending" },
  failed: { icon: XCircle, color: "var(--severity-critical)", label: "Failed" },
  uploaded: { icon: Clock, color: "var(--muted-foreground)", label: "Uploaded" },
};

interface UploadFileState {
  file: File | null;
  documentId: string | null;
  status: "idle" | "uploading" | "processing" | "completed" | "failed";
  progress: number;
  error: string | null;
  chunksCreated: number | null;
  risksExtracted: number | null;
}

interface UploadSlot {
  year: number | null;
  fileState: UploadFileState;
}

function Repository() {
  const [step, setStep] = useState<"company" | "upload" | "processing" | "ready">("company");
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);
  const [selectedMarket, setSelectedMarket] = useState<string>("SEC");
  const [selectedReportType, setSelectedReportType] = useState<string>("10-K");
  const [yearA, setYearA] = useState<number | null>(new Date().getFullYear());
  const [yearB, setYearB] = useState<number | null>(new Date().getFullYear() - 1);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companiesLoading, setCompaniesLoading] = useState(true);
  
  const [slots, setSlots] = useState<Record<number, UploadSlot>>({});
  const slotsRef = useRef(slots);
  const [isPolling, setIsPolling] = useState(false);
  const [compareEnabled, setCompareEnabled] = useState(false);
  
  const [showCompanyModal, setShowCompanyModal] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState("");
  const [newCompanySector, setNewCompanySector] = useState("");
  const [newCompanyTicker, setNewCompanyTicker] = useState("");
  const [newCompanyExchange, setNewCompanyExchange] = useState("");
  const [newCompanyCountry, setNewCompanyCountry] = useState("USA");
  const [creatingCompany, setCreatingCompany] = useState(false);

  useEffect(() => {
    api.companies.list({ page_size: 100 })
      .then((data: { companies: Company[] }) => {
        setCompanies(data.companies);
        setCompaniesLoading(false);
      })
      .catch(() => setCompaniesLoading(false));
  }, []);

  const initializeSlots = useCallback(() => {
    const newSlots: Record<number, UploadSlot> = {};
    if (yearA) {
      newSlots[yearA] = {
        year: yearA,
        fileState: { file: null, documentId: null, status: "idle", progress: 0, error: null, chunksCreated: null, risksExtracted: null },
      };
    }
    if (yearB && yearB !== yearA) {
      newSlots[yearB] = {
        year: yearB,
        fileState: { file: null, documentId: null, status: "idle", progress: 0, error: null, chunksCreated: null, risksExtracted: null },
      };
    }
    setSlots(newSlots);
  }, [yearA, yearB]);

  useEffect(() => {
    initializeSlots();
  }, [initializeSlots]);

  useEffect(() => {
    slotsRef.current = slots;
  }, [slots]);

  const pollAllStatuses = useCallback(async () => {
    let allCompleted = true;
    let hasFailed = false;
    let documentsFound = false;

    const currentSlots = slotsRef.current;
    for (const year of Object.keys(currentSlots)) {
      const slot = currentSlots[Number(year)];
      if (slot.fileState.documentId) {
        documentsFound = true;
      }
      if (slot.fileState.documentId && (slot.fileState.status === "processing" || slot.fileState.status === "uploaded" || slot.fileState.status === "pending")) {
        try {
          const status: DocumentStatusResponse = await api.documents.status(slot.fileState.documentId);
          setSlots(prev => ({
            ...prev,
            [slot.year]: {
              ...prev[slot.year],
              fileState: {
                ...slot.fileState,
                status: status.status as UploadFileState["status"],
                progress: status.progress ?? (status.status === "completed" ? 100 : status.status === "processing" ? 50 : status.status === "pending" ? 10 : 0),
                chunksCreated: status.chunks_created ?? slot.fileState.chunksCreated,
                risksExtracted: status.risks_extracted ?? slot.fileState.risksExtracted,
                error: status.message ?? slot.fileState.error,
              },
            },
          }));

          if (status.status !== "completed") {
            allCompleted = false;
          }
          if (status.status === "failed") {
            hasFailed = true;
          }
        } catch (err) {
          allCompleted = false;
          console.error("Failed to poll status:", err);
        }
      } else if (!slot.fileState.documentId || slot.fileState.status !== "completed") {
        allCompleted = false;
      }
    }

    if (hasFailed) {
      setStep("upload");
      toast.error("One or more documents failed to process");
    } else if (documentsFound && allCompleted && Object.keys(currentSlots).length > 0) {
      setStep("ready");
      setCompareEnabled(true);
    }
  }, []);

  useEffect(() => {
    if (step !== "processing") {
      setIsPolling(false);
      return;
    }

    setIsPolling(true);
    void pollAllStatuses();
    const interval = window.setInterval(() => void pollAllStatuses(), 2000);
    return () => {
      window.clearInterval(interval);
      setIsPolling(false);
    };
  }, [step, pollAllStatuses]);

  const handleFileSelect = (year: number, file: File) => {
    if (!file.name.endsWith(".pdf")) {
      toast.error("Only PDF files are allowed");
      return;
    }
    if (file.size > 100 * 1024 * 1024) {
      toast.error("File too large. Max size: 100MB");
      return;
    }

    setSlots(prev => ({
      ...prev,
      [year]: {
        ...prev[year],
        fileState: { ...prev[year].fileState, file, status: "idle", progress: 0, error: null },
      },
    }));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.add("border-primary", "bg-primary/5");
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove("border-primary", "bg-primary/5");
  };

  const handleDrop = (e: React.DragEvent, year: number) => {
    e.preventDefault();
    e.currentTarget.classList.remove("border-primary", "bg-primary/5");
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(year, file);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>, year: number) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(year, file);
    }
  };

  const uploadFile = async (year: number) => {
    const slot = slots[year];
    if (!slot.fileState.file || !selectedCompany) return;

    setSlots(prev => ({
      ...prev,
      [year]: {
        ...prev[year],
        fileState: { ...prev[year].fileState, status: "uploading", progress: 20 },
      },
    }));

    try {
      const result = await api.documents.upload(slot.fileState.file, {
        company_id: selectedCompany,
        fiscal_year: year,
        market: selectedMarket,
        report_type: selectedReportType,
      });

      setSlots(prev => ({
        ...prev,
        [year]: {
          ...prev[year],
          fileState: {
            ...prev[year].fileState,
            documentId: result.document_id,
            status: "processing",
            progress: 40,
          },
        },
      }));

      toast.success(`${slot.fileState.file.name} uploaded successfully`);
    } catch (err: unknown) {
      const error = err as { status?: number; message?: string };
      setSlots(prev => ({
        ...prev,
        [year]: {
          ...prev[year],
          fileState: {
            ...prev[year].fileState,
            status: "failed",
            progress: 0,
            error: error.message || "Upload failed",
          },
        },
      }));
      toast.error(error.message || "Upload failed");
    }
  };

  const uploadAllFiles = async () => {
    if (!selectedCompany) {
      toast.error("Please select a company first");
      return;
    }

    const yearsWithFiles = Object.entries(slots)
      .filter(([_, slot]) => slot.fileState.file)
      .map(([year]) => Number(year));

    if (yearsWithFiles.length === 0) {
      toast.error("Please select at least one PDF file");
      return;
    }

    setCompareEnabled(false);
    for (const year of yearsWithFiles) {
      await uploadFile(year);
    }
    setStep("processing");
  };

  const retryUpload = (year: number) => {
    setSlots(prev => ({
      ...prev,
      [year]: {
        ...prev[year],
        fileState: { ...prev[year].fileState, status: "idle", progress: 0, error: null },
      },
    }));
  };

  const reprocessDocument = async (year: number) => {
    const slot = slots[year];
    if (!slot.fileState.documentId) return;

    setSlots(prev => ({
      ...prev,
      [year]: {
        ...prev[year],
        fileState: { ...prev[year].fileState, status: "processing", progress: 40, error: null },
      },
    }));

    try {
      await api.documents.reprocess(slot.fileState.documentId);
      toast.success("Reprocessing started");
      setStep("processing");
    } catch (err: unknown) {
      const error = err as { status?: number; message?: string };
      setSlots(prev => ({
        ...prev,
        [year]: {
          ...prev[year],
          fileState: { ...prev[year].fileState, status: "failed", error: error.message || "Reprocessing failed" },
        },
      }));
      toast.error(error.message || "Reprocessing failed");
    }
  };

  const handleCreateCompany = async () => {
    if (!newCompanyName.trim()) {
      toast.error("Company name is required");
      return;
    }

    setCreatingCompany(true);
    try {
      const company = await api.companies.create({
        name: newCompanyName.trim(),
        sector: newCompanySector.trim() || undefined,
        ticker_symbol: newCompanyTicker.trim() || undefined,
        listed_exchange: newCompanyExchange.trim() || undefined,
        country: newCompanyCountry,
      });
      
      const companyId = (company as { id: string }).id;
      setSelectedCompany(companyId);
      setShowCompanyModal(false);
      toast.success("Company created successfully");
    } catch (err: unknown) {
      const error = err as { status?: number; message?: string };
      toast.error(error.message || "Failed to create company");
    } finally {
      setCreatingCompany(false);
    }
  };

  const allFilesUploaded = Object.values(slots).every(slot => slot.fileState.file !== null);
  const allProcessingComplete = Object.values(slots).every(slot => slot.fileState.status === "completed");
  const canCompare = allFilesUploaded && allProcessingComplete && selectedCompany !== null;

  const progressStages = [
    { label: "Uploading PDF", progress: 20 },
    { label: "Extracting text", progress: 40 },
    { label: "Creating chunks", progress: 60 },
    { label: "Extracting risks", progress: 80 },
    { label: "Ready", progress: 100 },
  ];

  const getCurrentStage = (progress: number) => {
    for (let i = progressStages.length - 1; i >= 0; i--) {
      if (progress >= progressStages[i].progress) {
        return progressStages[i];
      }
    }
    return progressStages[0];
  };

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Repository"
        title="Corporate intelligence repository"
        description="Upload and process annual reports for risk analysis. Select a company, upload two years of filings, then compare."
      />

      {step === "company" && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <GlassCard className="max-w-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="size-5" />
                Step 1: Select Company
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="company-select">Company</Label>
                  <Select value={selectedCompany || ""} onValueChange={setSelectedCompany} disabled={companiesLoading}>
                    <SelectTrigger id="company-select" className="w-full">
                      <SelectValue placeholder={companiesLoading ? "Loading companies..." : "Select a company"} />
                    </SelectTrigger>
                    <SelectContent>
                      {companiesLoading ? (
                        <SelectItem disabled>
                          Loading...
                        </SelectItem>
                      ) : (
                        <>
                          {companies.map((c) => (
                            <SelectItem key={c.id} value={c.id}>
                              {c.name} ({c.ticker_symbol ?? "N/A"})
                            </SelectItem>
                          ))}
                          <SelectItem value="__create_new__" className="flex items-center gap-2 text-primary">
                            <Plus className="size-4" />
                            Create new company
                          </SelectItem>
                        </>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <AnimatePresence mode="wait">
                {selectedCompany === "__create_new__" && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-4 p-4 border border-border/60 rounded-xl bg-secondary/30"
                  >
                    <h4 className="font-medium">Create New Company</h4>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <Label htmlFor="new-company-name">Company Name *</Label>
                        <Input
                          id="new-company-name"
                          value={newCompanyName}
                          onChange={(e) => setNewCompanyName(e.target.value)}
                          placeholder="e.g., Apple Inc."
                        />
                      </div>
                      <div>
                        <Label htmlFor="new-company-sector">Sector</Label>
                        <Input
                          id="new-company-sector"
                          value={newCompanySector}
                          onChange={(e) => setNewCompanySector(e.target.value)}
                          placeholder="e.g., Technology"
                        />
                      </div>
                      <div>
                        <Label htmlFor="new-company-ticker">Ticker Symbol</Label>
                        <Input
                          id="new-company-ticker"
                          value={newCompanyTicker}
                          onChange={(e) => setNewCompanyTicker(e.target.value)}
                          placeholder="e.g., AAPL"
                        />
                      </div>
                      <div>
                        <Label htmlFor="new-company-exchange">Exchange</Label>
                        <Input
                          id="new-company-exchange"
                          value={newCompanyExchange}
                          onChange={(e) => setNewCompanyExchange(e.target.value)}
                          placeholder="e.g., NASDAQ"
                        />
                      </div>
                      <div>
                        <Label htmlFor="new-company-country">Country</Label>
                        <Select value={newCompanyCountry} onValueChange={setNewCompanyCountry}>
                          <SelectTrigger id="new-company-country">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="USA">USA</SelectItem>
                            <SelectItem value="India">India</SelectItem>
                            <SelectItem value="UK">UK</SelectItem>
                            <SelectItem value="Canada">Canada</SelectItem>
                            <SelectItem value="Australia">Australia</SelectItem>
                            <SelectItem value="Singapore">Singapore</SelectItem>
                            <SelectItem value="Japan">Japan</SelectItem>
                            <SelectItem value="Germany">Germany</SelectItem>
                            <SelectItem value="Hong Kong">Hong Kong</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <Button onClick={handleCreateCompany} disabled={creatingCompany || !newCompanyName.trim()}>
                      {creatingCompany ? <Loader2 className="size-4 animate-spin" /> : "Create Company"}
                    </Button>
                  </motion.div>
                )}
              </AnimatePresence>

              {selectedCompany && selectedCompany !== "__create_new__" && (
                <Button
                  className="w-full"
                  size="lg"
                  onClick={() => setStep("upload")}
                  disabled={!selectedCompany}
                >
                  <ChevronRight className="size-4 mr-2" />
                  Continue to Upload
                </Button>
              )}
            </CardContent>
          </GlassCard>
        </motion.div>
      )}

      {step === "upload" && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <GlassCard className="max-w-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="size-5" />
                Step 2: Configure Upload
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <Label htmlFor="market-select">Market / Exchange</Label>
                  <Select value={selectedMarket} onValueChange={setSelectedMarket}>
                    <SelectTrigger id="market-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MARKETS.map((m) => (
                        <SelectItem key={m.value} value={m.value}>
                          {m.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="report-type-select">Report Type</Label>
                  <Select value={selectedReportType} onValueChange={setSelectedReportType}>
                    <SelectTrigger id="report-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {REPORT_TYPES.map((r) => (
                        <SelectItem key={r.value} value={r.value}>
                          {r.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="year-a">Year A (Current)</Label>
                  <Input
                    id="year-a"
                    type="number"
                    value={yearA ?? ""}
                    onChange={(e) => setYearA(e.target.value ? Number(e.target.value) : null)}
                    min={1990}
                    max={new Date().getFullYear() + 1}
                    className="text-right"
                  />
                </div>
                <div>
                  <Label htmlFor="year-b">Year B (Previous)</Label>
                  <Input
                    id="year-b"
                    type="number"
                    value={yearB ?? ""}
                    onChange={(e) => setYearB(e.target.value ? Number(e.target.value) : null)}
                    min={1990}
                    max={new Date().getFullYear()}
                    className="text-right"
                  />
                </div>
              </div>

              <Button
                className="w-full"
                size="lg"
                onClick={() => setStep("processing")}
                disabled={!yearA || !yearB || yearA === yearB}
              >
                <ChevronRight className="size-4 mr-2" />
                Upload Documents
              </Button>

              {yearA === yearB && yearA && (
                <p className="text-xs text-destructive">Years must be different</p>
              )}
            </CardContent>
          </GlassCard>
        </motion.div>
      )}

      {step === "processing" && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <GlassCard className="max-w-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Loader2 className="size-5 animate-spin" />
                Step 3: Processing Documents
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                {Object.entries(slots).map(([yearStr, slot]) => {
                  const year = Number(yearStr);
                  const fs = slot.fileState;
                  const s = statusMeta[fs.status] ?? statusMeta["pending"]!;
                  const stage = getCurrentStage(fs.progress);

                  return (
                    <Card key={yearStr} className="relative overflow-hidden">
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-base">{fs.file ? fs.file.name : `Year ${year} — No file`}</CardTitle>
                          <Badge variant={fs.status === "completed" ? "default" : fs.status === "failed" ? "destructive" : "secondary"}>
                            <s.icon className={`size-3 mr-1 ${fs.status === "processing" ? "animate-spin" : ""}`} />
                            {s.label}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span>{stage.label}</span>
                            <span className="num">{fs.progress}%</span>
                          </div>
                          <Progress value={fs.progress} className="h-2" />
                        </div>

                        {fs.chunksCreated !== null && (
                          <div className="text-xs text-muted-foreground flex gap-4">
                            <span>Chunks: {fs.chunksCreated}</span>
                            <span>Risks: {fs.risksExtracted ?? 0}</span>
                          </div>
                        )}

                        {fs.error && (
                          <AlertCircle className="size-4 text-destructive" />
                        )}

                        <div className="flex gap-2 pt-2">
                          {fs.status === "failed" && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="flex-1"
                              onClick={() => retryUpload(year)}
                            >
                              <RotateCcw className="size-3 mr-1" />
                              Retry
                            </Button>
                          )}
                          {fs.status === "completed" && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="flex-1"
                              onClick={() => reprocessDocument(year)}
                            >
                              <RotateCcw className="size-3 mr-1" />
                              Reprocess
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              <div className="rounded-xl border border-border/60 bg-secondary/25 p-4">
                <h4 className="font-medium mb-3">Processing Pipeline</h4>
                <div className="grid gap-3 md:grid-cols-5">
                  {progressStages.map((stage, i) => (
                    <div
                      key={stage.label}
                      className={`rounded-xl border border-border/60 bg-secondary/25 p-3 transition-all ${
                        Object.values(slots).some(s => s.fileState.progress >= stage.progress)
                          ? "border-primary/50 bg-primary/5"
                          : ""
                      }`}
                    >
                      <p className="num text-[10px] text-primary">STEP {i + 1}</p>
                      <p className="mt-1 text-xs font-medium">{stage.label}</p>
                      <Progress
                        value={
                          Object.values(slots).every(s => s.fileState.progress >= stage.progress)
                            ? 100
                            : Object.values(slots).some(s => s.fileState.progress >= stage.progress)
                            ? 50
                            : 0
                        }
                        className="mt-3 h-1.5 w-full"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </GlassCard>
        </motion.div>
      )}

      {step === "ready" && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <GlassCard className="max-w-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileCheck className="size-5 text-positive" />
                Step 4: Ready to Compare
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-xl border border-positive/30 bg-positive/5 p-4">
                <p className="text-sm font-medium text-positive">Both documents processed successfully!</p>
                <p className="text-xs text-muted-foreground mt-1">
                  You can now run a year-over-year risk comparison.
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                {Object.entries(slots).map(([yearStr, slot]) => {
                  const fs = slot.fileState;
                  return (
                    <Card key={yearStr} className="border-positive/30">
                      <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                          <Check className="size-4 text-positive" />
                          Year {yearStr}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <p className="text-xs text-muted-foreground">{fs.file?.name}</p>
                        <div className="flex gap-4 text-xs text-muted-foreground">
                          <span>Chunks: {fs.chunksCreated ?? 0}</span>
                          <span>Risks: {fs.risksExtracted ?? 0}</span>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              <Button
                className="w-full"
                size="lg"
                onClick={() => {
                  // Navigate to comparison page with the selected company and years
                  window.location.href = `/comparison?company=${selectedCompany}&yearA=${yearA}&yearB=${yearB}`;
                }}
              >
                <ArrowRight className="size-4 mr-2" />
                Run Comparison
              </Button>
            </CardContent>
          </GlassCard>
        </motion.div>
      )}

      <AnimatePresence mode="wait">
        {showCompanyModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
            onClick={() => setShowCompanyModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="w-full max-w-md bg-background rounded-2xl border border-border/60 p-6 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold mb-4">Create New Company</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <Label htmlFor="new-company-name">Company Name *</Label>
                  <Input
                    id="new-company-name"
                    value={newCompanyName}
                    onChange={(e) => setNewCompanyName(e.target.value)}
                    placeholder="e.g., Apple Inc."
                  />
                </div>
                <div>
                  <Label htmlFor="new-company-sector">Sector</Label>
                  <Input
                    id="new-company-sector"
                    value={newCompanySector}
                    onChange={(e) => setNewCompanySector(e.target.value)}
                    placeholder="e.g., Technology"
                  />
                </div>
                <div>
                  <Label htmlFor="new-company-ticker">Ticker Symbol</Label>
                  <Input
                    id="new-company-ticker"
                    value={newCompanyTicker}
                    onChange={(e) => setNewCompanyTicker(e.target.value)}
                    placeholder="e.g., AAPL"
                  />
                </div>
                <div>
                  <Label htmlFor="new-company-exchange">Exchange</Label>
                  <Input
                    id="new-company-exchange"
                    value={newCompanyExchange}
                    onChange={(e) => setNewCompanyExchange(e.target.value)}
                    placeholder="e.g., NASDAQ"
                  />
                </div>
                <div className="sm:col-span-2">
                  <Label htmlFor="new-company-country">Country</Label>
                  <Select value={newCompanyCountry} onValueChange={setNewCompanyCountry}>
                    <SelectTrigger id="new-company-country">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="USA">USA</SelectItem>
                      <SelectItem value="India">India</SelectItem>
                      <SelectItem value="UK">UK</SelectItem>
                      <SelectItem value="Canada">Canada</SelectItem>
                      <SelectItem value="Australia">Australia</SelectItem>
                      <SelectItem value="Singapore">Singapore</SelectItem>
                      <SelectItem value="Japan">Japan</SelectItem>
                      <SelectItem value="Germany">Germany</SelectItem>
                      <SelectItem value="Hong Kong">Hong Kong</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex gap-2 mt-6">
                <Button variant="outline" className="flex-1" onClick={() => setShowCompanyModal(false)}>
                  Cancel
                </Button>
                <Button className="flex-1" onClick={handleCreateCompany} disabled={creatingCompany || !newCompanyName.trim()}>
                  {creatingCompany ? <Loader2 className="size-4 animate-spin mx-auto" /> : "Create Company"}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
