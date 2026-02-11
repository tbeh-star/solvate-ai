const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface FetchOptions extends RequestInit {
  token?: string;
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { token, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

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
};
