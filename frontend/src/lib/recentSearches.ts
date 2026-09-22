const KEY = "rag-stock-recent-searches";
const MAX = 6;

export function getRecentSearches(): string[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

export function addRecentSearch(ticker: string): void {
  try {
    const current = getRecentSearches().filter((t) => t !== ticker);
    const next = [ticker, ...current].slice(0, MAX);
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // ignore - private browsing / blocked storage
  }
}
