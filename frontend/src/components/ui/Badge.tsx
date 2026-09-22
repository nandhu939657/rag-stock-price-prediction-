import type { ReactNode } from "react";
import type { RecommendationValue } from "../../types/db";

export function RecommendationBadge({ value }: { value: RecommendationValue }) {
  return <span className={`badge badge-${value}`}>{value}</span>;
}

export function Chip({ children }: { children: ReactNode }) {
  return <span className="chip">{children}</span>;
}
