import { useState } from "react";
import { Plus, Loader2 } from "lucide-react";
import { api, ApiError } from "../lib/apiClient";
import { useToast } from "./ui/Toast";

export function AddToWatchlistButton({ ticker, onTracked }: { ticker: string; onTracked?: () => void }) {
  const [loading, setLoading] = useState(false);
  const { push } = useToast();

  const handleClick = async () => {
    setLoading(true);
    try {
      await api.track(ticker);
      push(`${ticker} added to your watchlist`, "success");
      onTracked?.();
    } catch (e) {
      push(e instanceof ApiError ? e.message : "Failed to add to watchlist", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button onClick={handleClick} disabled={loading} className="btn btn-primary">
      {loading ? <Loader2 size={14} className="spin" /> : <Plus size={14} />}
      {loading ? "Adding…" : "Add to Watchlist"}
    </button>
  );
}
