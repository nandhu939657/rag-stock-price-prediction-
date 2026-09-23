export type RecommendationValue = "buy" | "sell" | "hold";
export type MlSignal = "up" | "down" | "flat";
export type RiskLevel = "low" | "medium" | "high";

export interface StrategyConsidered {
  book_title: string;
  author: string;
  topic: string;
  content: string;
  similarity: number;
}

export interface Recommendation {
  id: string;
  stock_id: string;
  ticker?: string;
  created_at: string;
  ml_signal: MlSignal | null;
  ml_predicted_return: number | null;
  ml_confidence: number | null;
  final_recommendation: RecommendationValue;
  reasoning: string;
  guardrails_applied: string[];
  triggered_by: "scheduled" | "on_demand";
  context_snapshot?: {
    has_price_data?: boolean;
    is_fallback?: boolean;
    fallback_reason?: "quota_exhausted" | "service_error" | "unparseable_response" | null;
    strategies_considered?: StrategyConsidered[];
    risk_level?: RiskLevel;
    risk_summary?: string;
    risk_factors?: string[];
    risk_score?: number;
    latest_indicators?: {
      return_1?: number | null;
      return_5?: number | null;
      return_10?: number | null;
      return_20?: number | null;
      [key: string]: unknown;
    };
  } | null;
}

export interface TrackedStock {
  stock_id: string;
  ticker: string;
  name: string;
  is_tracked: boolean;
  added_at: string;
  last_refreshed_at: string | null;
  latest_recommendation: Recommendation | null;
  recent_closes: number[];
}

export interface PriceBar {
  ts: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  sma_20?: number | null;
  ema_20?: number | null;
  rsi_14?: number | null;
  macd?: number | null;
  macd_signal?: number | null;
  bollinger_upper?: number | null;
  bollinger_lower?: number | null;
}

export interface NewsSource {
  id: string;
  source: "firecrawl" | "apify";
  source_url: string | null;
  title: string | null;
  published_at: string | null;
  chunk_text: string;
  scraped_at: string;
}

export interface StockHistory {
  ticker: string;
  price_history: PriceBar[];
  recommendations: Recommendation[];
  sources: NewsSource[];
}

export interface SymbolSearchResult {
  ticker: string;
  name: string;
  exchange?: string | null;
  has_price_data: boolean;
  alternative_ticker?: string | null;
}

export interface GuardrailRule {
  rule_key: string;
  category: "guardrail" | "domain_fact";
  content: string;
  severity: "hard" | "soft";
  is_active: boolean;
}

export interface Mover {
  stock_id: string;
  ticker: string;
  name: string;
  latest_close: number;
  previous_close: number;
  change_pct: number;
  latest_ts: string;
}

export interface MoversResponse {
  gainers: Mover[];
  losers: Mover[];
  total_analyzed: number;
}

export interface StrategyBook {
  book_title: string;
  author: string;
  principles: { topic: string; content: string }[];
}

export interface StrategiesResponse {
  books: StrategyBook[];
  total_principles: number;
}
