import { ServerCrash } from "lucide-react";

const REASON_TEXT: Record<string, string> = {
  quota_exhausted: "The AI service's daily usage limit was reached during this refresh.",
  service_error: "The AI service didn't respond during this refresh.",
  unparseable_response: "The AI service's response couldn't be read during this refresh.",
};

/** Shown instead of a normal recommendation whenever the backend genuinely couldn't
 * get a real answer from Groq (rate limit, outage, bad response) - the recommendation
 * badge still says "hold" as a safe default, but this makes clear that's a fallback,
 * not a real analysis, rather than letting the generic reasoning text pass as one. */
export function FallbackNotice({ reason, compact = false }: { reason?: string | null; compact?: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 8,
        background: "var(--color-warn-bg)",
        color: "var(--color-warn)",
        borderRadius: "var(--radius-sm)",
        padding: compact ? "8px 10px" : "10px 12px",
        fontSize: compact ? 11.5 : 12.5,
      }}
    >
      <ServerCrash size={compact ? 14 : 16} style={{ flexShrink: 0, marginTop: 1 }} />
      <span>
        <strong>Analysis unavailable this cycle.</strong> {reason ? REASON_TEXT[reason] || REASON_TEXT.service_error : REASON_TEXT.service_error}{" "}
        "Hold" is shown as a safe default, not a real recommendation — it will retry automatically next refresh.
      </span>
    </div>
  );
}
