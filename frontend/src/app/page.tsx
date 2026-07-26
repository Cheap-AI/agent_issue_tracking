"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { FormEvent, useEffect, useMemo, useState } from "react";

type HealthResponse = {
  status: string;
  service: string;
  message: string;
};

type Issue = {
  id: string;
  title: string;
  summary: string;
};

type ResearchResponse = {
  topic: string;
  status: string;
  summary: string;
  sources: string[];
};

type TicketTone = "mint" | "violet" | "amber" | "sky";

type TicketCardProps = {
  issue: Issue;
  tone: TicketTone;
  onClick: () => void;
};

const getApiBaseUrl = () => {
  if (typeof window === "undefined") {
    return "/api";
  }

  return process.env.NEXT_PUBLIC_API_BASE_URL || "/api";
};

const ticketStyles: Record<TicketTone, { bg: string; accent: string; text: string }> = {
  mint: { bg: "linear-gradient(135deg, #eefcf7 0%, #dff8ee 100%)", accent: "#37b38b", text: "#134e3a" },
  violet: { bg: "linear-gradient(135deg, #f5ecff 0%, #ece4ff 100%)", accent: "#8b5cf6", text: "#4c1d95" },
  amber: { bg: "linear-gradient(135deg, #fff8e8 0%, #ffe9c2 100%)", accent: "#f59e0b", text: "#92400e" },
  sky: { bg: "linear-gradient(135deg, #eef7ff 0%, #dceeff 100%)", accent: "#3b82f6", text: "#1d4ed8" },
};

function TicketCard({ issue, tone, onClick }: TicketCardProps) {
  const style = ticketStyles[tone];

  return (
    <motion.button
      whileHover={{ y: -4, scale: 1.01, rotate: -0.5 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 260, damping: 20 }}
      onClick={onClick}
      style={{
        border: "1px solid rgba(15, 23, 42, 0.08)",
        borderRadius: 24,
        padding: "1rem",
        textAlign: "left",
        background: style.bg,
        color: style.text,
        cursor: "pointer",
        boxShadow: "0 12px 30px rgba(15, 23, 42, 0.08)",
        display: "grid",
        gap: "0.75rem",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", opacity: 0.75 }}>
          Ticket
        </span>
        <span style={{ width: 10, height: 10, borderRadius: "999px", background: style.accent }} />
      </div>
      <div>
        <div style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.35rem" }}>{issue.title}</div>
        <div style={{ fontSize: "0.95rem", lineHeight: 1.5, opacity: 0.85 }}>{issue.summary}</div>
      </div>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <span style={{ background: "rgba(255,255,255,0.7)", padding: "0.35rem 0.6rem", borderRadius: "999px", fontSize: "0.78rem" }}>
          Learn
        </span>
        <span style={{ background: "rgba(255,255,255,0.7)", padding: "0.35rem 0.6rem", borderRadius: "999px", fontSize: "0.78rem" }}>
          Review
        </span>
      </div>
    </motion.button>
  );
}

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [researchTopic, setResearchTopic] = useState("");
  const [researchResult, setResearchResult] = useState<ResearchResponse | null>(null);
  const [researchLoading, setResearchLoading] = useState(false);
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);

  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);

  const loadIssues = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/issues`);
      if (!response.ok) {
        throw new Error("Failed to load issues");
      }
      const data = await response.json();
      setIssues(data.issues || []);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  };

  const loadHealth = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/health`);
      if (!response.ok) {
        throw new Error("Failed to load health data");
      }
      const data = await response.json();
      setHealth(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  };

  useEffect(() => {
    void loadHealth();
    void loadIssues();
  }, [apiBaseUrl]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${apiBaseUrl}/issues`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, summary }),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || "Failed to create issue");
      }

      setTitle("");
      setSummary("");
      await loadIssues();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  };

  const handleResearch = async () => {
    if (!researchTopic.trim()) {
      setError("Please enter a topic");
      return;
    }

    setResearchLoading(true);
    setError("");

    try {
      const response = await fetch(`${apiBaseUrl}/agent/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: researchTopic }),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || "Failed to generate research draft");
      }

      const data = await response.json();
      setResearchResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setResearchLoading(false);
    }
  };

  const selectedIssue = issues.find((issue) => issue.id === selectedIssueId) || null;
  const toneCycle: TicketTone[] = ["mint", "violet", "amber", "sky"];

  return (
    <main style={{ minHeight: "100vh", padding: "1.25rem", paddingTop: "5rem", fontFamily: "Inter, sans-serif", background: "linear-gradient(135deg, #f7f8ff 0%, #fdfcf8 100%)", color: "#14213d" }}>
      <div style={{ maxWidth: "1200px", margin: "0 auto", display: "grid", gap: "1.25rem" }}>
        <motion.header
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          style={{ borderRadius: 28, padding: "1.25rem 1.4rem", background: "rgba(255,255,255,0.82)", border: "1px solid rgba(20,33,61,0.08)", boxShadow: "0 18px 45px rgba(20,33,61,0.08)" }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, color: "#6b7280" }}>Learning Pulse</div>
              <h1 style={{ margin: "0.25rem 0", fontSize: "1.7rem" }}>Cute, calm, and ready for your next breakthrough.</h1>
              <p style={{ margin: 0, color: "#5b6473", maxWidth: "720px" }}>A playful bento-style board for tracking issues, research drafts, and study momentum.</p>
            </div>
            <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
              <Link href="/about" style={{ textDecoration: "none", color: "#14213d", padding: "0.7rem 1rem", borderRadius: "999px", background: "#fff", border: "1px solid rgba(20,33,61,0.08)" }}>About</Link>
              <button style={{ border: "none", padding: "0.7rem 1rem", borderRadius: "999px", background: "linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)", color: "white", cursor: "pointer" }}>New issue</button>
            </div>
          </div>
        </motion.header>

        <section style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "1.25rem" }}>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} style={{ borderRadius: 28, padding: "1.2rem", background: "rgba(255,255,255,0.82)", border: "1px solid rgba(20,33,61,0.08)", boxShadow: "0 18px 45px rgba(20,33,61,0.08)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.95rem" }}>
              <div>
                <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, color: "#6b7280" }}>Today’s focus</div>
                <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>Build a calm student-ready workflow.</div>
              </div>
              <div style={{ padding: "0.45rem 0.7rem", borderRadius: "999px", background: "#eefcf7", color: "#13795c", fontWeight: 700 }}>Live</div>
            </div>
            <div style={{ color: "#5b6473", lineHeight: 1.6 }}>A friendly issue board that feels like an educational workspace instead of a rigid admin panel.</div>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} style={{ borderRadius: 28, padding: "1.2rem", background: "linear-gradient(135deg, #f6f2ff 0%, #eef7ff 100%)", border: "1px solid rgba(20,33,61,0.08)", boxShadow: "0 18px 45px rgba(20,33,61,0.08)" }}>
            <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, color: "#6b7280", marginBottom: "0.4rem" }}>Research draft</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "0.4rem" }}>Turn a topic into a starter memo</div>
            <input value={researchTopic} onChange={(event) => setResearchTopic(event.target.value)} placeholder="Enter a topic" style={{ width: "100%", border: "1px solid rgba(20,33,61,0.08)", borderRadius: "999px", padding: "0.8rem 0.95rem", marginBottom: "0.75rem" }} />
            <button onClick={() => { void handleResearch(); }} disabled={researchLoading} style={{ border: "none", borderRadius: "999px", padding: "0.75rem 1rem", background: "#14213d", color: "white", cursor: "pointer" }}>
              {researchLoading ? "Generating..." : "Generate draft"}
            </button>
            {researchResult ? (
              <div style={{ marginTop: "0.85rem", fontSize: "0.95rem", color: "#374151", lineHeight: 1.6 }}>
                <strong>{researchResult.topic}</strong>
                <div>{researchResult.summary}</div>
              </div>
            ) : null}
          </motion.div>
        </section>

        <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} style={{ borderRadius: 28, padding: "1.2rem", background: "rgba(255,255,255,0.82)", border: "1px solid rgba(20,33,61,0.08)", boxShadow: "0 18px 45px rgba(20,33,61,0.08)" }}>
            <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, color: "#6b7280", marginBottom: "0.75rem" }}>Create issue</div>
            <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.75rem" }}>
              <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Issue title" style={{ border: "1px solid rgba(20,33,61,0.08)", borderRadius: "16px", padding: "0.8rem 0.95rem" }} />
              <textarea value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Issue summary" rows={4} style={{ border: "1px solid rgba(20,33,61,0.08)", borderRadius: "16px", padding: "0.8rem 0.95rem", resize: "vertical" }} />
              <button type="submit" disabled={loading} style={{ border: "none", borderRadius: "999px", padding: "0.75rem 1rem", background: "linear-gradient(135deg, #37b38b 0%, #14b8a6 100%)", color: "white", cursor: "pointer" }}>
                {loading ? "Creating..." : "Create issue"}
              </button>
            </form>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} style={{ borderRadius: 28, padding: "1.2rem", background: "rgba(255,255,255,0.82)", border: "1px solid rgba(20,33,61,0.08)", boxShadow: "0 18px 45px rgba(20,33,61,0.08)" }}>
            <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, color: "#6b7280", marginBottom: "0.75rem" }}>Backend health</div>
            <button onClick={() => { void loadHealth(); }} style={{ border: "none", borderRadius: "999px", padding: "0.65rem 0.95rem", background: "#fef3c7", color: "#92400e", cursor: "pointer", marginBottom: "0.8rem" }}>
              Check backend health
            </button>
            {health ? (
              <div style={{ color: "#374151", lineHeight: 1.6 }}>
                <div><strong>Status:</strong> {health.status}</div>
                <div><strong>Service:</strong> {health.service}</div>
                <div><strong>Message:</strong> {health.message}</div>
              </div>
            ) : (
              <div style={{ color: "#6b7280" }}>Loading backend status...</div>
            )}
          </motion.div>
        </section>

        <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }} style={{ borderRadius: 28, padding: "1.2rem", background: "rgba(255,255,255,0.82)", border: "1px solid rgba(20,33,61,0.08)", boxShadow: "0 18px 45px rgba(20,33,61,0.08)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.95rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <div>
              <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, color: "#6b7280" }}>Issue timeline</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>Clickable tickets with room for richer content later</div>
            </div>
            <div style={{ color: "#6b7280", fontSize: "0.95rem" }}>{issues.length} tickets</div>
          </div>

          {error ? <div style={{ color: "crimson", marginBottom: "0.85rem" }}>{error}</div> : null}

          {issues.length === 0 ? (
            <div style={{ color: "#6b7280" }}>No issues yet. Create one to see your first ticket.</div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
              {issues.map((issue, index) => (
                <TicketCard key={issue.id} issue={issue} tone={toneCycle[index % toneCycle.length]} onClick={() => setSelectedIssueId(issue.id)} />
              ))}
            </div>
          )}

          {selectedIssue ? (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }} style={{ marginTop: "1rem", borderRadius: 24, padding: "1rem", background: "linear-gradient(135deg, #fdfcf8 0%, #f6f2ff 100%)", border: "1px solid rgba(20,33,61,0.08)" }}>
              <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, color: "#6b7280" }}>Selected ticket</div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, marginTop: "0.25rem" }}>{selectedIssue.title}</div>
              <div style={{ marginTop: "0.45rem", color: "#374151", lineHeight: 1.6 }}>{selectedIssue.summary}</div>
              <div style={{ marginTop: "0.8rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <span style={{ padding: "0.35rem 0.6rem", borderRadius: "999px", background: "white", border: "1px solid rgba(20,33,61,0.08)" }}>Summary block</span>
                <span style={{ padding: "0.35rem 0.6rem", borderRadius: "999px", background: "white", border: "1px solid rgba(20,33,61,0.08)" }}>Image slot</span>
                <span style={{ padding: "0.35rem 0.6rem", borderRadius: "999px", background: "white", border: "1px solid rgba(20,33,61,0.08)" }}>Checklist slot</span>
              </div>
            </motion.div>
          ) : null}
        </motion.section>
      </div>
    </main>
  );
}
