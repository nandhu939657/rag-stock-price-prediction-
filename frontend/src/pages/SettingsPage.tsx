import { useEffect, useState } from "react";
import { ShieldCheck, Activity, Info, BookOpen, ChevronDown, ChevronRight } from "lucide-react";
import { api } from "../lib/apiClient";
import type { GuardrailRule, StrategiesResponse } from "../types/db";
import { Chip } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";

interface Health {
  status: string;
  scheduler_running: boolean;
  last_run_at: string | null;
  tracked_stock_count: number;
}

export function SettingsPage() {
  const [guardrails, setGuardrails] = useState<GuardrailRule[] | null>(null);
  const [strategies, setStrategies] = useState<StrategiesResponse | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [expandedBooks, setExpandedBooks] = useState<Set<string>>(new Set());

  useEffect(() => {
    api.guardrails().then(setGuardrails).catch(() => setGuardrails([]));
    api.strategies().then(setStrategies).catch(() => setStrategies({ books: [], total_principles: 0 }));
    api.health().then(setHealth).catch(() => setHealth(null));
    const interval = setInterval(() => {
      api.health().then(setHealth).catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const toggleBook = (title: string) => {
    setExpandedBooks((prev) => {
      const next = new Set(prev);
      next.has(title) ? next.delete(title) : next.add(title);
      return next;
    });
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings &amp; About</h1>
          <p className="page-subtitle">System status and the guardrails applied to every recommendation.</p>
        </div>
      </div>

      <section style={{ marginBottom: 28 }}>
        <h2 className="kicker" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Activity size={13} /> System status
        </h2>
        {!health ? (
          <div className="card"><Skeleton height={40} /></div>
        ) : (
          <div className="stat-row">
            <div className="stat-tile">
              <div className="stat-tile-label">Scheduler</div>
              <div className="stat-tile-value" style={{ fontSize: 16, color: health.scheduler_running ? "var(--color-buy)" : "var(--color-sell)" }}>
                {health.scheduler_running ? "Running" : "Stopped"}
              </div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Tracked stocks</div>
              <div className="stat-tile-value">{health.tracked_stock_count}</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Last refresh cycle</div>
              <div className="stat-tile-value" style={{ fontSize: 14 }}>
                {health.last_run_at ? new Date(health.last_run_at).toLocaleTimeString() : "—"}
              </div>
            </div>
          </div>
        )}
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 className="kicker" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <ShieldCheck size={13} /> Active guardrails
        </h2>
        <p className="text-muted" style={{ fontSize: 13, marginTop: -4, marginBottom: 12 }}>
          These rules are injected into every Groq prompt and checked again after generation, before a
          recommendation is stored.
        </p>
        {guardrails === null ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <Skeleton height={50} />
            <Skeleton height={50} />
          </div>
        ) : guardrails.length === 0 ? (
          <div className="empty-state">No guardrail rules found — check that the database seed ran.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {guardrails.map((g) => (
              <div key={g.rule_key} className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13.5, marginBottom: 3 }}>{g.rule_key.replace(/_/g, " ")}</div>
                  <div className="text-muted" style={{ fontSize: 13 }}>{g.content}</div>
                </div>
                <Chip>{g.severity}</Chip>
              </div>
            ))}
          </div>
        )}
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 className="kicker" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <BookOpen size={13} /> Strategy library
        </h2>
        <p className="text-muted" style={{ fontSize: 13, marginTop: -4, marginBottom: 12 }}>
          Principles distilled from {strategies?.books.length ?? "…"} well-known investing and trading books, embedded
          and retrieved via RAG based on each stock's current technical situation — not dumped into every prompt, only
          pulled in when genuinely relevant. See a recommendation's "Principles considered" chips to know which ones
          were used for that specific call.
        </p>
        {strategies === null ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <Skeleton height={44} />
            <Skeleton height={44} />
          </div>
        ) : strategies.books.length === 0 ? (
          <div className="empty-state">No strategy knowledge found — run scripts/seed_strategy_knowledge.py.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {strategies.books.map((book) => {
              const expanded = expandedBooks.has(book.book_title);
              return (
                <div key={book.book_title} className="card" style={{ padding: 0, overflow: "hidden" }}>
                  <button
                    onClick={() => toggleBook(book.book_title)}
                    className="btn btn-ghost"
                    style={{ width: "100%", justifyContent: "space-between", padding: "10px 14px", borderRadius: 0 }}
                  >
                    <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      <span style={{ textAlign: "left" }}>
                        <div style={{ fontWeight: 600, fontSize: 13.5 }}>{book.book_title}</div>
                        <div className="text-faint" style={{ fontSize: 11.5 }}>{book.author}</div>
                      </span>
                    </span>
                    <Chip>{book.principles.length} principle{book.principles.length === 1 ? "" : "s"}</Chip>
                  </button>
                  {expanded && (
                    <div style={{ padding: "0 14px 14px", display: "flex", flexDirection: "column", gap: 10 }}>
                      {book.principles.map((p, i) => (
                        <div key={i} style={{ borderTop: "1px solid var(--color-border-subtle)", paddingTop: 10 }}>
                          <Chip>{p.topic.replace(/_/g, " ")}</Chip>
                          <p className="text-muted" style={{ fontSize: 12.5, lineHeight: 1.55, margin: "6px 0 0" }}>
                            {p.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section>
        <h2 className="kicker" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Info size={13} /> About
        </h2>
        <div className="card text-muted" style={{ fontSize: 13, lineHeight: 1.6 }}>
          Every recommendation closes a loop: live price data feeds a trained ML model for a quantitative signal,
          which combines with RAG-retrieved live news (via Firecrawl and Apify) and RAG-retrieved principles from
          the strategy library above, all synthesized by a Groq-hosted LLM under the guardrails above. This is a
          personal research tool — recommendations are not financial advice.
        </div>
      </section>
    </div>
  );
}
