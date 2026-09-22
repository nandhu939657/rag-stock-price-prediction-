import type { Recommendation } from "../types/db";
import { RecommendationBadge } from "./ui/Badge";

export function HistoryTable({ recommendations }: { recommendations: Recommendation[] }) {
  if (recommendations.length === 0) {
    return <div className="empty-state">No recommendation history yet.</div>;
  }

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid var(--color-border)" }}>
            <th style={{ padding: "10px 14px", color: "var(--color-text-faint)", fontWeight: 600, fontSize: 11.5, textTransform: "uppercase" }}>When</th>
            <th style={{ padding: "10px 14px", color: "var(--color-text-faint)", fontWeight: 600, fontSize: 11.5, textTransform: "uppercase" }}>Call</th>
            <th style={{ padding: "10px 14px", color: "var(--color-text-faint)", fontWeight: 600, fontSize: 11.5, textTransform: "uppercase" }}>ML signal</th>
            <th style={{ padding: "10px 14px", color: "var(--color-text-faint)", fontWeight: 600, fontSize: 11.5, textTransform: "uppercase" }}>Confidence</th>
            <th style={{ padding: "10px 14px", color: "var(--color-text-faint)", fontWeight: 600, fontSize: 11.5, textTransform: "uppercase" }}>Trigger</th>
          </tr>
        </thead>
        <tbody>
          {recommendations.map((r) => (
            <tr key={r.id} style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
              <td style={{ padding: "10px 14px", whiteSpace: "nowrap" }}>{new Date(r.created_at).toLocaleString()}</td>
              <td style={{ padding: "10px 14px" }}>
                <RecommendationBadge value={r.final_recommendation} />
              </td>
              <td style={{ padding: "10px 14px" }} className="text-muted">{r.ml_signal ?? "—"}</td>
              <td style={{ padding: "10px 14px" }} className="text-muted">
                {r.ml_confidence != null ? `${Math.round(r.ml_confidence * 100)}%` : "—"}
              </td>
              <td style={{ padding: "10px 14px" }} className="text-faint">{r.triggered_by === "scheduled" ? "auto" : "manual"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
