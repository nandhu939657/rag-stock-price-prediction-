import type { GuardrailRule, MoversResponse, Recommendation, StockHistory, StrategiesResponse, SymbolSearchResult, TrackedStock } from "../types/db";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore parse failure, use statusText
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  searchSymbol: (q: string) => request<SymbolSearchResult[]>(`/api/stocks/search?q=${encodeURIComponent(q)}`),

  analyze: (ticker: string, name?: string) =>
    request<Recommendation>("/api/stocks/analyze", {
      method: "POST",
      body: JSON.stringify({ ticker, name }),
    }),

  track: (ticker: string) => request<{ status: string; ticker: string; stock_id: string }>(`/api/stocks/${ticker}/track`, { method: "POST" }),

  untrack: (ticker: string) => request<{ status: string; ticker: string }>(`/api/stocks/${ticker}/track`, { method: "DELETE" }),

  listTracked: () => request<TrackedStock[]>("/api/stocks/tracked"),

  history: (ticker: string) => request<StockHistory>(`/api/stocks/${ticker}/history`),

  health: () => request<{ status: string; scheduler_running: boolean; last_run_at: string | null; tracked_stock_count: number }>("/api/health"),

  guardrails: () => request<GuardrailRule[]>("/api/guardrails"),

  movers: (limit = 5) => request<MoversResponse>(`/api/stocks/movers?limit=${limit}`),

  strategies: () => request<StrategiesResponse>("/api/strategies"),
};

export { ApiError };
