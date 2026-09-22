import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown } from "lucide-react";
import { api } from "../lib/apiClient";
import type { MoversResponse } from "../types/db";
import { DisclaimerBanner } from "../components/ReasoningPanel";
import { MoversChart, MoversList } from "../components/MoversTable";
import { Skeleton } from "../components/ui/Skeleton";

export function OverviewPage() {
  const [data, setData] = useState<MoversResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .movers(6)
      .then(setData)
      .catch(() => setError("Failed to load movers"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <DisclaimerBanner />
      <div className="page-header">
        <div>
          <h1 className="page-title">Overview</h1>
          <p className="page-subtitle">
            Biggest recent movers among the stocks analyzed in this app — not a full market scan, just what you and
            the scheduler have looked at so far.
          </p>
        </div>
      </div>

      {loading && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <Skeleton height={180} />
          <Skeleton height={180} />
        </div>
      )}

      {error && <div className="empty-state" style={{ borderColor: "var(--color-sell)", color: "var(--color-sell)" }}>{error}</div>}

      {data && (
        <>
          {data.total_analyzed < 2 && (
            <div className="empty-state" style={{ marginBottom: 20 }}>
              Not enough analyzed stocks yet to compute movers — analyze a few from the Search page and check back
              once they've refreshed at least twice.
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 24 }}>
            <section>
              <h2 className="kicker" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <TrendingUp size={13} color="var(--color-buy)" /> Top gainers
              </h2>
              <MoversChart movers={data.gainers} kind="gainers" />
              <div style={{ marginTop: 12 }}>
                <MoversList movers={data.gainers} />
              </div>
            </section>

            <section>
              <h2 className="kicker" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <TrendingDown size={13} color="var(--color-sell)" /> Top losers
              </h2>
              <MoversChart movers={data.losers} kind="losers" />
              <div style={{ marginTop: 12 }}>
                <MoversList movers={data.losers} />
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
