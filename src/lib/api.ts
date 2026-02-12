const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface FetchOptions extends RequestInit {
  token?: string;
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { token, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  // Don't set Content-Type for FormData — browser adds multipart boundary automatically
  if (!(fetchOptions.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface InternalPrice {
  id: number;
  product_raw: string;
  product_id: number | null;
  price_value: number;
  price_currency: string;
  price_unit: string;
  price_raw: string | null;
  specs: string | null;
  delivery_term: string | null;
  location: string | null;
  packaging: string | null;
  quantity: string | null;
  producer: string | null;
  custom_fields: Record<string, string> | null;
  source_format: string;
  confidence: number | null;
  created_at: string;
  updated_at: string;
}

export interface MarketPrice {
  id: number;
  time: string;
  product_raw: string;
  price_value: number;
  price_currency: string;
  price_unit: string;
  location: string | null;
  price_type: string | null;
  source: string;
  created_at: string;
}

export interface User {
  id: string;
  org_id: string;
  email: string;
  name: string | null;
  role: string;
  created_at: string;
}

// Extraction types (matches backend ExtractionResult schema)
export interface MendelFact {
  value: string | number | null;
  unit: string | null;
  source_section: string;
  raw_string: string;
  confidence: "high" | "medium" | "low";
  is_specification: boolean;
  test_method: string | null;
}

export interface ExtractionResult {
  document_info: {
    document_type: "TDS" | "SDS" | "RPI" | "CoA" | "Brochure" | "unknown";
    language: string;
    manufacturer: string | null;
    brand: string | null;
    revision_date: string | null;
    page_count: number;
  };
  identity: {
    product_name: string;
    product_line: string | null;
    wacker_sku: string | null;
    material_numbers: string[];
    product_url: string | null;
    grade: MendelFact | null;
  };
  chemical: {
    cas_numbers: MendelFact;
    chemical_components: string[];
    chemical_synonyms: string[];
    purity: MendelFact | null;
  };
  physical: {
    physical_form: MendelFact | null;
    density: MendelFact | null;
    flash_point: MendelFact | null;
    temperature_range: MendelFact | null;
    shelf_life: MendelFact | null;
    cure_system: MendelFact | null;
  };
  application: {
    main_application: string | null;
    usage_restrictions: string[];
    packaging_options: string[];
  };
  safety: {
    ghs_statements: string[];
    un_number: MendelFact | null;
    certifications: string[];
    global_inventories: string[];
    blocked_countries: string[];
    blocked_industries: string[];
  };
  compliance: {
    wiaw_status: "GREEN LIGHT" | "ATTENTION" | "RED FLAG" | null;
    sales_advisory: string | null;
  };
  missing_attributes: string[];
  extraction_warnings: string[];
}

export interface ExtractionResponse {
  success: boolean;
  result: ExtractionResult | null;
  error: string | null;
  processing_time_ms: number;
  provider: string | null;
  model: string | null;
  cascade: {
    cascade_triggered: boolean;
    primary_provider: string | null;
    primary_model: string | null;
    primary_missing_count: number | null;
    fallback_provider: string | null;
    fallback_model: string | null;
  } | null;
  markdown_preview: string | null;
}

// Batch extraction types
export interface BatchExtractionResult {
  filename: string;
  success: boolean;
  result: ExtractionResult | null;
  error: string | null;
  processing_time_ms: number;
}

export interface BatchExtractionResponse {
  success: boolean;
  results: BatchExtractionResult[];
  total_processing_time_ms: number;
  provider: string | null;
  successful_count: number;
  failed_count: number;
}

// Confirm extraction types
export interface ConfirmExtractionRequest {
  results: BatchExtractionResult[];
  total_processing_time_ms: number;
}

export interface ConfirmExtractionResponse {
  run_id: number;
  golden_records_created: number;
}

// History types
export interface ExtractionRunSummary {
  id: number;
  started_at: string;
  finished_at: string | null;
  pdf_count: number | null;
  golden_records_count: number | null;
  status: string;
  total_cost: number | null;
}

export interface GoldenRecordSummary {
  id: number;
  product_name: string;
  brand: string | null;
  source_files: string[];
  source_count: number | null;
  missing_count: number | null;
  completeness: number | null;
  created_at: string;
  // Versioning & regional variant fields
  region: string;
  doc_language: string | null;
  revision_date: string | null;
  document_type: string | null;
  version: number;
  is_latest: boolean;
}

export interface ExtractionRunDetail extends ExtractionRunSummary {
  golden_records: GoldenRecordSummary[];
}

export interface GoldenRecordDetail extends GoldenRecordSummary {
  golden_record: ExtractionResult;
}

// Version diff types
export interface DiffEntry {
  field: string;
  change_type: "added" | "removed" | "changed";
  old_value: string | number | string[] | Record<string, unknown> | null;
  new_value: string | number | string[] | Record<string, unknown> | null;
  old_unit: string | null;
  new_unit: string | null;
  old_confidence: string | null;
  new_confidence: string | null;
}

export interface SectionDiff {
  section: string;
  changes: DiffEntry[];
}

export interface VersionDiffResponse {
  record_a: GoldenRecordSummary;
  record_b: GoldenRecordSummary;
  sections: SectionDiff[];
  total_changes: number;
  summary: string;
}

// API functions
export const api = {
  // Auth
  getMe: (token: string) =>
    apiFetch<User>("/users/me", { token }),

  // Prices
  listPrices: (token: string, page = 1, pageSize = 50) =>
    apiFetch<PaginatedResponse<InternalPrice>>(
      `/prices?page=${page}&page_size=${pageSize}`,
      { token }
    ),

  createPrice: (token: string, data: Partial<InternalPrice>) =>
    apiFetch<InternalPrice>("/prices", {
      token,
      method: "POST",
      body: JSON.stringify(data),
    }),

  createPricesBulk: (token: string, items: Partial<InternalPrice>[]) =>
    apiFetch<InternalPrice[]>("/prices/bulk", {
      token,
      method: "POST",
      body: JSON.stringify(items),
    }),

  updatePrice: (token: string, id: number, data: Partial<InternalPrice>) =>
    apiFetch<InternalPrice>(`/prices/${id}`, {
      token,
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deletePrice: (token: string, id: number) =>
    apiFetch<void>(`/prices/${id}`, { token, method: "DELETE" }),

  // Market data
  listMarketPrices: (
    token: string,
    params: {
      start_date: string;
      end_date: string;
      source?: string;
      unit?: string;
      product?: string;
      page?: number;
      page_size?: number;
    }
  ) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.set(key, String(value));
    });
    return apiFetch<PaginatedResponse<MarketPrice>>(
      `/market-data?${searchParams.toString()}`,
      { token }
    );
  },

  // Favorites
  getFavorites: (token: string) =>
    apiFetch<number[]>("/users/me/favorites", { token }),

  addFavorite: (token: string, productId: number) =>
    apiFetch<{ status: string }>(`/users/me/favorites/${productId}`, {
      token,
      method: "POST",
    }),

  removeFavorite: (token: string, productId: number) =>
    apiFetch<void>(`/users/me/favorites/${productId}`, {
      token,
      method: "DELETE",
    }),

  // Extraction — single PDF
  extractPdf: (file: File, signal?: AbortSignal) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch<ExtractionResponse>("/extraction/extract-agent", {
      method: "POST",
      body: formData,
      signal,
    });
  },

  // Extraction — multiple PDFs
  extractPdfBatch: (files: File[], signal?: AbortSignal) => {
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    return apiFetch<BatchExtractionResponse>("/extraction/extract-batch", {
      method: "POST",
      body: formData,
      signal,
    });
  },

  // Confirm extraction results → persist to database
  confirmExtraction: (data: ConfirmExtractionRequest) =>
    apiFetch<ConfirmExtractionResponse>("/extraction/confirm", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // History — extraction runs & golden records
  listRuns: (page = 1, pageSize = 20) =>
    apiFetch<PaginatedResponse<ExtractionRunSummary>>(
      `/extraction/runs?page=${page}&page_size=${pageSize}`
    ),

  getRunDetail: (runId: number) =>
    apiFetch<ExtractionRunDetail>(`/extraction/runs/${runId}`),

  listGoldenRecords: (
    runId?: number,
    page = 1,
    pageSize = 50,
    latestOnly = false
  ) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (runId !== undefined) params.set("run_id", String(runId));
    if (latestOnly) params.set("latest_only", "true");
    return apiFetch<PaginatedResponse<GoldenRecordSummary>>(
      `/extraction/golden-records?${params}`
    );
  },

  // Version history for a specific golden record
  getRecordVersions: (recordId: number) =>
    apiFetch<GoldenRecordSummary[]>(
      `/extraction/golden-records/${recordId}/versions`
    ),

  // Golden record detail (full JSONB data)
  getGoldenRecordDetail: (recordId: number) =>
    apiFetch<GoldenRecordDetail>(
      `/extraction/golden-records/${recordId}`
    ),

  // Version diff between two golden records
  getVersionDiff: (id1: number, id2: number) =>
    apiFetch<VersionDiffResponse>(
      `/extraction/golden-records/${id1}/diff/${id2}`
    ),

  // Export URL builder (returns URL string for direct download)
  exportGoldenRecordsUrl: (params: {
    format: "csv" | "xlsx";
    runId?: number;
    latestOnly?: boolean;
  }): string => {
    const searchParams = new URLSearchParams({
      format: params.format,
    });
    if (params.runId !== undefined) searchParams.set("run_id", String(params.runId));
    if (params.latestOnly) searchParams.set("latest_only", "true");
    return `${API_BASE}/extraction/golden-records/export?${searchParams}`;
  },
};
