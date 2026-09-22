import { ExternalLink } from "lucide-react";
import type { NewsSource } from "../types/db";
import { Chip } from "./ui/Badge";

export function NewsSourceCard({ source }: { source: NewsSource }) {
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
        <div style={{ fontWeight: 600, fontSize: 13.5, lineHeight: 1.4 }}>{source.title || "Untitled article"}</div>
        <Chip>{source.source}</Chip>
      </div>
      <p className="text-muted" style={{ fontSize: 13, lineHeight: 1.55, margin: 0 }}>
        {source.chunk_text.slice(0, 260)}
        {source.chunk_text.length > 260 ? "…" : ""}
      </p>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="text-faint" style={{ fontSize: 11 }}>
          Retrieved {new Date(source.scraped_at).toLocaleDateString()}
        </span>
        {source.source_url && (
          <a
            href={source.source_url}
            target="_blank"
            rel="noreferrer"
            style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "var(--color-accent)", textDecoration: "none" }}
          >
            Read source <ExternalLink size={11} />
          </a>
        )}
      </div>
    </div>
  );
}
