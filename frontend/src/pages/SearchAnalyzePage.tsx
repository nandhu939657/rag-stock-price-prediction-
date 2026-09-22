import { useEffect, useRef, useState } from "react";
import { Search as SearchIcon, Loader2, Clock, CircleAlert, ArrowRight } from "lucide-react";
import { api, ApiError } from "../lib/apiClient";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { addRecentSearch, getRecentSearches } from "../lib/recentSearches";
import type { PriceBar, Recommendation, SymbolSearchResult } from "../types/db";
import { AddToWatchlistButton } from "../components/AddToWatchlistButton";
import { DisclaimerBanner, ReasoningPanel } from "../components/ReasoningPanel";
import { PriceChart } from "../components/PriceChart";
import { IndicatorPanel } from "../components/IndicatorPanel";
import { useToast } from "../components/ui/Toast";

export function SearchAnalyzePage() {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 300);
  const [results, setResults] = useState<SymbolSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [selected, setSelected] = useState<SymbolSearchResult | null>(null);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [priceHistory, setPriceHistory] = useState<PriceBar[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<string[]>(getRecentSearches);
  const boxRef = useRef<HTMLDivElement>(null);
  const { push } = useToast();

  useEffect(() => {
    if (!debouncedQuery.trim() || debouncedQuery.length < 1) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setSearching(true);
    api
      .searchSymbol(debouncedQuery.trim())
      .then((data) => {
        if (!cancelled) setResults(data);
      })
      .catch(() => {
        if (!cancelled) setResults([]);
      })
      .finally(() => {
        if (!cancelled) setSearching(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setShowDropdown(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const runAnalysis = async (symbol: SymbolSearchResult) => {
    setSelected(symbol);
    setShowDropdown(false);
    setAnalyzing(true);
    setError(null);
    setRecommendation(null);
    setPriceHistory([]);
    try {
      const rec = await api.analyze(symbol.ticker, symbol.name);
      setRecommendation(rec);
      addRecentSearch(symbol.ticker);
      setRecent(getRecentSearches());
      // Best-effort - the recommendation itself is already usable even if this fails.
      api
        .history(symbol.ticker)
        .then((h) => setPriceHistory(h.price_history))
        .catch(() => {});
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "Analysis failed";
      setError(message);
      push(message, "error");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleAnalyzeTyped = () => {
    const ticker = query.trim().toUpperCase();
    if (!ticker) return;
    // has_price_data is unknown until the pipeline actually tries the symbol - optimistic
    // true here just controls dropdown styling, which is moot since this bypasses it;
    // the real answer comes back on the recommendation itself and is shown there.
    runAnalysis({ ticker, name: ticker, has_price_data: true, exchange: null, alternative_ticker: null });
  };

  return (
    <div>
      <DisclaimerBanner />
      <div className="page-header">
        <div>
          <h1 className="page-title">Search &amp; Analyze</h1>
          <p className="page-subtitle">Look up any US, China, Hong Kong, India, or Japan-listed stock and get a live buy/sell/hold recommendation.</p>
        </div>
      </div>

      <div ref={boxRef} style={{ position: "relative", marginBottom: 24 }}>
        <div style={{ position: "relative" }}>
          <SearchIcon size={15} style={{ position: "absolute", left: 12, top: 11, color: "var(--color-text-faint)" }} />
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setShowDropdown(true);
            }}
            onFocus={() => setShowDropdown(true)}
            onKeyDown={(e) => {
              if (e.key !== "Enter") return;
              const best = results.find((r) => r.has_price_data) ?? results[0];
              best ? runAnalysis(best) : handleAnalyzeTyped();
            }}
            placeholder="Search by ticker or company name (e.g. AAPL, Tata Steel, Toyota)"
            className="input"
            style={{ paddingLeft: 34 }}
          />
          {searching && <Loader2 size={15} className="spin" style={{ position: "absolute", right: 12, top: 11, color: "var(--color-text-faint)" }} />}
        </div>

        {showDropdown && (
          <div className="card" style={{ position: "absolute", top: "calc(100% + 6px)", left: 0, right: 0, zIndex: 20, padding: 6, maxHeight: 340, overflowY: "auto", boxShadow: "var(--shadow-lg)" }}>
            {query.trim().length === 0 && recent.length > 0 && (
              <>
                <div className="kicker" style={{ padding: "6px 8px 2px" }}>Recent</div>
                {recent.map((ticker) => (
                  <button
                    key={ticker}
                    onClick={() => runAnalysis({ ticker, name: ticker, has_price_data: true, exchange: null, alternative_ticker: null })}
                    className="btn btn-ghost"
                    style={{ width: "100%", justifyContent: "flex-start" }}
                  >
                    <Clock size={13} /> {ticker}
                  </button>
                ))}
              </>
            )}

            {results.map((r) => (
              <div key={`${r.ticker}-${r.exchange}`} style={{ opacity: r.has_price_data ? 1 : 0.72 }}>
                <button
                  onClick={() => runAnalysis(r)}
                  className="btn btn-ghost"
                  style={{ width: "100%", justifyContent: "space-between", padding: "10px 10px" }}
                >
                  <span style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                    <strong>{r.ticker}</strong>
                    <span className="text-muted" style={{ fontSize: 12 }}>{r.name}</span>
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {!r.has_price_data && (
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 3,
                          fontSize: 10.5,
                          fontWeight: 600,
                          color: "var(--color-sell)",
                          background: "var(--color-sell-bg)",
                          padding: "2px 6px",
                          borderRadius: 999,
                        }}
                      >
                        <CircleAlert size={10} /> No price data
                      </span>
                    )}
                    {r.exchange && <span className="text-faint" style={{ fontSize: 11 }}>{r.exchange}</span>}
                  </span>
                </button>
                {!r.has_price_data && r.alternative_ticker && (
                  <button
                    onClick={() => runAnalysis({ ...r, ticker: r.alternative_ticker!, has_price_data: true, alternative_ticker: null })}
                    className="btn btn-ghost btn-sm"
                    style={{ width: "100%", justifyContent: "flex-start", color: "var(--color-accent)", marginTop: -4, marginBottom: 2 }}
                  >
                    <ArrowRight size={12} /> Try {r.alternative_ticker} instead — has real price data
                  </button>
                )}
              </div>
            ))}

            {query.trim().length > 0 && !searching && results.length === 0 && (
              <div style={{ padding: 10 }}>
                <div className="text-muted" style={{ fontSize: 12.5, marginBottom: 6 }}>
                  No company matched "{query.trim()}". Check the spelling, or try the full company name.
                </div>
                <button onClick={handleAnalyzeTyped} className="btn btn-secondary btn-sm">
                  Try analyzing "{query.trim().toUpperCase()}" as a literal ticker
                </button>
              </div>
            )}

            {query.trim().length > 0 && !searching && results.length > 0 && results.every((r) => !r.has_price_data) && (
              <div className="text-muted" style={{ fontSize: 11.5, padding: "8px 10px 2px", borderTop: "1px solid var(--color-border-subtle)" }}>
                None of these have price data available on the current plan — analysis would be news-only.
              </div>
            )}
          </div>
        )}
      </div>

      {analyzing && (
        <div className="empty-state" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          <Loader2 size={15} className="spin" />
          Running the analysis pipeline (price data, news retrieval, ML signal, Groq synthesis)…
        </div>
      )}

      {!analyzing && error && <div className="empty-state" style={{ borderColor: "var(--color-sell)", color: "var(--color-sell)" }}>{error}</div>}

      {!analyzing && recommendation && selected && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ fontSize: 18, margin: 0 }}>
              {selected.ticker} <span className="text-muted" style={{ fontWeight: 400 }}>— {selected.name}</span>
            </h2>
            <AddToWatchlistButton ticker={selected.ticker} />
          </div>
          <ReasoningPanel recommendation={recommendation} />

          {priceHistory.length > 0 && (
            <>
              <h3 className="kicker" style={{ marginTop: 8 }}>Price</h3>
              <PriceChart bars={priceHistory} />
              <h3 className="kicker">Indicators</h3>
              <IndicatorPanel latest={priceHistory[priceHistory.length - 1]} />
            </>
          )}
        </div>
      )}
    </div>
  );
}
