const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export interface DocumentStatusResponse {
  document_id: string;
  status: "pending" | "processing" | "completed" | "failed" | string;
  progress?: number | null;
  chunks_created?: number | null;
  risks_extracted?: number | null;
  message?: string | null;
}

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(text || `Request failed (${response.status})`, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  documents: {
    upload: (file: File, data: { company_id: string; fiscal_year: number; market?: string; country?: string; report_type?: string; ticker?: string; sector?: string; exchange?: string; currency?: string; source_url?: string }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("company_id", data.company_id);
      formData.append("fiscal_year", String(data.fiscal_year));
      if (data.market) formData.append("market", data.market);
      if (data.country) formData.append("country", data.country);
      if (data.report_type) formData.append("report_type", data.report_type);
      if (data.ticker) formData.append("ticker", data.ticker);
      if (data.sector) formData.append("sector", data.sector);
      if (data.exchange) formData.append("exchange", data.exchange);
      if (data.currency) formData.append("currency", data.currency);
      if (data.source_url) formData.append("source_url", data.source_url);

      return fetch(`${API_BASE}/documents/upload`, {
        method: "POST",
        body: formData,
      }).then(async (res) => {
        if (!res.ok) throw new ApiError(await res.text(), res.status);
        return res.json();
      });
    },

    list: (params?: { company_id?: string; fiscal_year?: number; status?: string; page?: number; page_size?: number }) => {
      const search = new URLSearchParams();
      if (params?.company_id) search.set("company_id", params.company_id);
      if (params?.fiscal_year) search.set("fiscal_year", String(params.fiscal_year));
      if (params?.status) search.set("status", params.status);
      if (params?.page) search.set("page", String(params.page));
      if (params?.page_size) search.set("page_size", String(params.page_size));
      return request(`/documents?${search}`);
    },

    get: (document_id: string) => request(`/documents/${document_id}`),

    status: (document_id: string) => request<DocumentStatusResponse>(`/documents/${document_id}/status`),

    delete: (document_id: string) => request(`/documents/${document_id}`, { method: "DELETE" }),

    reprocess: (document_id: string) => request(`/documents/${document_id}/reprocess`, { method: "POST" }),
  },

  companies: {
    list: (params?: { page?: number; page_size?: number; search?: string }) => {
      const search = new URLSearchParams();
      if (params?.page) search.set("page", String(params.page));
      if (params?.page_size) search.set("page_size", String(params.page_size));
      if (params?.search) search.set("search", params.search);
      return request(`/companies?${search}`);
    },

    get: (company_id: string) => request(`/companies/${company_id}`),

    create: (data: { name: string; sector?: string; ticker_symbol?: string; listed_exchange?: string; country?: string; market_cap?: number; currency?: string; website_url?: string; logo_url?: string }) =>
      request("/companies", { method: "POST", body: JSON.stringify(data) }),

    update: (company_id: string, data: Partial<{ name: string; sector: string; ticker_symbol: string; listed_exchange: string; market_cap: number; currency: string; website_url: string; logo_url: string }>) =>
      request(`/companies/${company_id}`, { method: "PATCH", body: JSON.stringify(data) }),

    delete: (company_id: string) => request(`/companies/${company_id}`, { method: "DELETE" }),

    reports: (company_id: string) => request(`/companies/${company_id}/reports`),
  },

  comparison: {
    compare: (data: { company_id: string; year_current: number; year_previous: number; similarity_threshold?: number }) =>
      request("/comparison/compare", { method: "POST", body: JSON.stringify(data) }),

    getEvolution: (company_id: string, year_current: number, year_previous: number) =>
      request(`/comparison/evolution?company_id=${company_id}&year_current=${year_current}&year_previous=${year_previous}`),

    getEvidence: (comparison_id: string) => request(`/comparison/${comparison_id}/evidence`),

    getRiskEvidence: (risk_id: string) => request(`/comparison/evidence/${risk_id}`),
  },

  dashboard: {
    getExecutive: (company_id: string, year_previous: number, year_current: number) =>
      request(`/dashboard/executive?company_id=${company_id}&year_previous=${year_previous}&year_current=${year_current}`),

    getRiskEvolution: (company_id: string) => request(`/dashboard/risk-evolution?company_id=${company_id}`),

    getHeatmap: (company_id: string, year?: number) => {
      const search = new URLSearchParams({ company_id });
      if (year) search.set("year", String(year));
      return request(`/dashboard/heatmap?${search}`);
    },

    getFinancialHealth: (company_id: string, year: number) =>
      request(`/dashboard/financial-health?company_id=${company_id}&year=${year}`),
  },

  risks: {
    list: (params?: { company_id?: string; report_id?: string; fiscal_year?: number; category?: string; severity?: string; min_confidence?: number; page?: number; page_size?: number }) => {
      const search = new URLSearchParams();
      if (params?.company_id) search.set("company_id", params.company_id);
      if (params?.report_id) search.set("report_id", params.report_id);
      if (params?.fiscal_year) search.set("fiscal_year", String(params.fiscal_year));
      if (params?.category) search.set("category", params.category);
      if (params?.severity) search.set("severity", params.severity);
      if (params?.min_confidence) search.set("min_confidence", String(params.min_confidence));
      if (params?.page) search.set("page", String(params.page));
      if (params?.page_size) search.set("page_size", String(params.page_size));
      return request(`/risks?${search}`);
    },

    get: (risk_id: string) => request(`/risks/${risk_id}`),

    getEvolution: (risk_id: string) => request(`/risks/${risk_id}/evolution`),

    extract: (report_id: string, force_reprocess?: boolean) =>
      request("/analysis/extract", { method: "POST", body: JSON.stringify({ report_id, force_reprocess }) }),
  },

  reports: {
    list: (params?: { company_id?: string; fiscal_year?: number; page?: number; page_size?: number }) => {
      const search = new URLSearchParams();
      if (params?.company_id) search.set("company_id", params.company_id);
      if (params?.fiscal_year) search.set("fiscal_year", String(params.fiscal_year));
      if (params?.page) search.set("page", String(params.page));
      if (params?.page_size) search.set("page_size", String(params.page_size));
      return request(`/reports?${search}`);
    },

    generateExecutiveSummary: (data: { company_id: string; year?: number; include_evolution?: boolean; include_financial?: boolean; include_news?: boolean }) =>
      request("/reports/executive-summary", { method: "POST", body: JSON.stringify(data) }),

    downloadExecutiveSummary: (data: { company_id: string; year?: number; include_evolution?: boolean; include_financial?: boolean; include_news?: boolean }) =>
      fetch(`${API_BASE}/reports/executive-summary/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }).then(async (res) => {
        if (!res.ok) throw new ApiError(await res.text(), res.status);
        return res.blob();
      }),
  },

  marketIntelligence: {
    get: (company_id: string) => request(`/market-intelligence?company_id=${company_id}`),
  },

  industryIntelligence: {
    get: (company_id: string) => request(`/industry-intelligence?company_id=${company_id}`),
  },

  riskExplorer: {
    list: (params?: { company_id?: string; category?: string; severity?: string; status?: string; year?: number; page?: number; page_size?: number }) => {
      const search = new URLSearchParams();
      if (params?.company_id) search.set("company_id", params.company_id);
      if (params?.category) search.set("category", params.category);
      if (params?.severity) search.set("severity", params.severity);
      if (params?.status) search.set("status", params.status);
      if (params?.year) search.set("year", String(params.year));
      if (params?.page) search.set("page", String(params.page));
      if (params?.page_size) search.set("page_size", String(params.page_size));
      return request(`/risk-explorer?${search}`);
    },

    getDetail: (company_id: string, risk_id: string, year?: number) => {
      const search = new URLSearchParams({ risk_id });
      if (year) search.set("year", String(year));
      return request(`/risk-explorer/${company_id}/detail?${search}`);
    },

    getCompanies: () => request("/risk-explorer/companies"),
  },

  scanner: {
    scan: (data: { company_ids?: string[]; sectors?: string[]; year_current?: number; year_previous?: number; logic?: "AND" | "OR"; criteria?: Array<{ factor: string; operator: string; value: string | number | boolean }>; page?: number; page_size?: number }) =>
      request("/scanner/scan", { method: "POST", body: JSON.stringify(data) }),

    getOptions: () => request("/scanner/options"),
  },

  financialHealth: {
    get: (company_id: string, year: number) => request(`/financial-health?company_id=${company_id}&year=${year}`),
  },

  explainability: {
    explain: (records: Array<Record<string, unknown>>) =>
      request("/explainability/explain", { method: "POST", body: JSON.stringify({ records }) }),
  },

  health: () => request("/health"),
};

export type { ApiError };
