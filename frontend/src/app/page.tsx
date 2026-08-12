"use client";

import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useMemo, useState } from "react";

type Issue = {
  id: string;
  title: string;
  summary: string;
  why?: string;
  tags?: string[];
  is_active?: boolean;
  created_at?: string;
};

type LeaderboardEntry = {
  rank: number;
  issue_id: string;
  title: string;
  overall_score: number;
  dimension_scores?: Record<string, number>;
  last_updated?: string;
};

type EventItem = {
  id: number;
  event_date: string | null;
  discovered_at: string;
  title: string;
  description: string;
  source_urls: string[];
};

const getApiBaseUrl = () => {
  // In production, use the full backend URL (e.g., https://backend.com/api)
  // In development, use /api which is proxied to localhost:8000
  return process.env.NEXT_PUBLIC_API_BASE_URL || "/api";
};

const cardTones = [
  { bg: "linear-gradient(135deg, #eefcf7 0%, #dff8ee 100%)", accent: "#37b38b", text: "#134e3a" },
  { bg: "linear-gradient(135deg, #f5ecff 0%, #ece4ff 100%)", accent: "#8b5cf6", text: "#4c1d95" },
  { bg: "linear-gradient(135deg, #fff8e8 0%, #ffe9c2 100%)", accent: "#f59e0b", text: "#92400e" },
  { bg: "linear-gradient(135deg, #eef7ff 0%, #dceeff 100%)", accent: "#3b82f6", text: "#1d4ed8" },
];

type IssueCardProps = {
  issue: Issue;
  tone: (typeof cardTones)[number];
  apiBaseUrl: string;
};

function IssueCard({ issue, tone, apiBaseUrl }: IssueCardProps) {
  const router = useRouter();
  const [hovered, setHovered] = useState(false);
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [loadingEvents, setLoadingEvents] = useState(false);

  const handleMouseEnter = () => {
    setHovered(true);
    if (events !== null || loadingEvents) {
      return;
    }
    setLoadingEvents(true);
    fetch(`${apiBaseUrl}/issues/${issue.id}/events`)
      .then((response) => (response.ok ? response.json() : { events: [] }))
      .then((data) => setEvents(data.events || []))
      .catch(() => setEvents([]))
      .finally(() => setLoadingEvents(false));
  };

  const recentEvents = (events || []).slice(-4).reverse();

  return (
    <div style={{ position: "relative" }}>
      <motion.button
        whileHover={{ y: -4, scale: 1.01 }}
        whileTap={{ scale: 0.98 }}
        transition={{ type: "spring", stiffness: 260, damping: 20 }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={() => setHovered(false)}
        onClick={() => router.push(`/issues/${issue.id}`)}
        style={{
          border: "1px solid rgba(15, 23, 42, 0.08)",
          borderRadius: 24,
          padding: "1rem",
          width: "100%",
          textAlign: "left",
          background: tone.bg,
          color: tone.text,
          cursor: "pointer",
          boxShadow: "0 12px 30px rgba(15, 23, 42, 0.08)",
          display: "grid",
          gap: "0.6rem",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", opacity: 0.75 }}>
            Issue
          </span>
          <span style={{ width: 10, height: 10, borderRadius: "999px", background: tone.accent }} />
        </div>
        <div style={{ fontSize: "1.02rem", fontWeight: 700, lineHeight: 1.35 }}>{issue.title}</div>
        <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
          {(issue.tags || []).slice(0, 4).map((tag) => (
            <span key={tag} style={{ background: "rgba(255,255,255,0.7)", padding: "0.3rem 0.55rem", borderRadius: "999px", fontSize: "0.72rem" }}>
              {tag}
            </span>
          ))}
        </div>
      </motion.button>

      <AnimatePresence>
        {hovered ? (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
            style={{
              position: "absolute",
              top: "calc(100% + 0.5rem)",
              left: 0,
              right: 0,
              zIndex: 20,
              borderRadius: 18,
              padding: "0.9rem 1rem",
              background: "white",
              border: "1px solid rgba(20,33,61,0.1)",
              boxShadow: "0 18px 40px rgba(20,33,61,0.18)",
              pointerEvents: "none",
            }}
          >
            <div style={{ fontSize: "0.85rem", color: "#374151", lineHeight: 1.5, marginBottom: "0.6rem" }}>
              {issue.summary}
            </div>
            <div style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#6b7280", marginBottom: "0.35rem" }}>
              Recent events
            </div>
            {loadingEvents ? (
              <div style={{ fontSize: "0.82rem", color: "#9ca3af" }}>Loading...</div>
            ) : recentEvents.length === 0 ? (
              <div style={{ fontSize: "0.82rem", color: "#9ca3af" }}>No events collected yet.</div>
            ) : (
              <div style={{ display: "grid", gap: "0.35rem" }}>
                {recentEvents.map((event) => (
                  <div key={event.id} style={{ fontSize: "0.82rem", color: "#374151" }}>
                    <strong>{event.event_date || "Undated"}</strong> — {event.title}
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function LeaderboardPanel({ entries }: { entries: LeaderboardEntry[] }) {
  const router = useRouter();
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <div style={{ borderRadius: 28, padding: "1.2rem", background: "rgba(255,255,255,0.82)", border: "1px solid rgba(20,33,61,0.08)", boxShadow: "0 18px 45px rgba(20,33,61,0.08)" }}>
      <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, color: "#6b7280", marginBottom: "0.9rem" }}>
        Leaderboard
      </div>
      {entries.length === 0 ? (
        <div style={{ color: "#6b7280", fontSize: "0.9rem" }}>No ranked issues yet.</div>
      ) : (
        <div style={{ display: "grid", gap: "0.6rem" }}>
          {entries.map((entry) => (
            <button
              key={entry.issue_id}
              onClick={() => router.push(`/issues/${entry.issue_id}`)}
              onMouseEnter={() => setHoveredId(entry.issue_id)}
              onMouseLeave={() => setHoveredId(null)}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "0.6rem",
                padding: "0.55rem 0.7rem",
                borderRadius: 14,
                background: hoveredId === entry.issue_id ? "rgba(20,33,61,0.06)" : "rgba(20,33,61,0.03)",
                border: "none",
                cursor: "pointer",
                width: "100%",
                transition: "background 0.15s",
                textAlign: "left",
              }}
            >
              <div style={{ display: "flex", gap: "0.6rem", alignItems: "center", minWidth: 0 }}>
                <span style={{ fontWeight: 700, color: "#6b7280", fontSize: "0.85rem", flexShrink: 0 }}>#{entry.rank}</span>
                <span style={{ fontSize: "0.85rem", color: "#14213d", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{entry.title}</span>
              </div>
              <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "#3b82f6", flexShrink: 0 }}>{entry.overall_score}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);

  const filteredIssues = useMemo(() => {
    let filtered = issues;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((issue) =>
        issue.title.toLowerCase().includes(query) ||
        issue.summary.toLowerCase().includes(query)
      );
    }

    if (selectedTag) {
      filtered = filtered.filter((issue) =>
        issue.tags?.includes(selectedTag)
      );
    }

    return filtered;
  }, [issues, searchQuery, selectedTag]);

  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    issues.forEach((issue) => {
      issue.tags?.forEach((tag) => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [issues]);

  useEffect(() => {
    const loadIssues = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/issues`);
        if (!response.ok) {
          throw new Error("Failed to load issues");
        }
        const data = await response.json();
        setIssues(data.issues || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unexpected error");
      }
    };

    const loadLeaderboard = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/leaderboard`);
        if (!response.ok) {
          throw new Error("Failed to load leaderboard");
        }
        const data = await response.json();
        setLeaderboard(data.leaderboard || []);
      } catch {
        setLeaderboard([]);
      }
    };

    void loadIssues();
    void loadLeaderboard();
  }, [apiBaseUrl]);

  return (
    <main style={{ minHeight: "100vh", padding: "1.25rem", paddingTop: "5rem", fontFamily: "Inter, sans-serif", background: "linear-gradient(135deg, #f7f8ff 0%, #fdfcf8 100%)", color: "#14213d" }}>
      <div style={{ maxWidth: "1200px", margin: "0 auto", display: "grid", gap: "1.25rem" }}>
        <motion.header
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          style={{ borderRadius: 28, padding: "1.25rem 1.4rem", background: "rgba(255,255,255,0.82)", border: "1px solid rgba(20,33,61,0.08)", boxShadow: "0 18px 45px rgba(20,33,61,0.08)" }}
        >
          <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, color: "#6b7280" }}>Issue Tracker</div>
          <h1 style={{ margin: "0.25rem 0", fontSize: "1.7rem" }}>Discovered issues, ranked and tracked over time.</h1>
          <p style={{ margin: 0, color: "#5b6473", maxWidth: "720px" }}>Hover a card for a quick preview, or click through for the full timeline of events.</p>
        </motion.header>

        {error ? <div style={{ color: "crimson" }}>{error}</div> : null}

        <section style={{ display: "grid", gridTemplateColumns: "minmax(0, 2.2fr) minmax(260px, 1fr)", gap: "1.25rem", alignItems: "start" }}>
          <div style={{ borderRadius: 28, padding: "1.2rem", background: "rgba(255,255,255,0.82)", border: "1px solid rgba(20,33,61,0.08)", boxShadow: "0 18px 45px rgba(20,33,61,0.08)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.95rem" }}>
              <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, color: "#6b7280" }}>Issues</div>
              <div style={{ color: "#6b7280", fontSize: "0.95rem" }}>{filteredIssues.length} of {issues.length}</div>
            </div>

            <input
              type="text"
              placeholder="Search issues..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "0.7rem 1rem",
                borderRadius: 16,
                border: "1px solid rgba(20,33,61,0.12)",
                fontSize: "0.9rem",
                marginBottom: "0.9rem",
                background: "rgba(255,255,255,0.8)",
                outline: "none",
              }}
            />

            {allTags.length > 0 && (
              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "0.9rem" }}>
                <button
                  onClick={() => setSelectedTag(null)}
                  style={{
                    padding: "0.35rem 0.7rem",
                    borderRadius: "999px",
                    fontSize: "0.75rem",
                    border: selectedTag === null ? "1px solid #3b82f6" : "1px solid rgba(20,33,61,0.12)",
                    background: selectedTag === null ? "#3b82f6" : "rgba(255,255,255,0.9)",
                    color: selectedTag === null ? "white" : "#6b7280",
                    cursor: "pointer",
                    fontWeight: selectedTag === null ? 700 : 500,
                  }}
                >
                  All
                </button>
                {allTags.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => setSelectedTag(tag === selectedTag ? null : tag)}
                    style={{
                      padding: "0.35rem 0.7rem",
                      borderRadius: "999px",
                      fontSize: "0.75rem",
                      border: tag === selectedTag ? "1px solid #3b82f6" : "1px solid rgba(20,33,61,0.12)",
                      background: tag === selectedTag ? "#3b82f6" : "rgba(255,255,255,0.9)",
                      color: tag === selectedTag ? "white" : "#6b7280",
                      cursor: "pointer",
                      fontWeight: tag === selectedTag ? 700 : 500,
                    }}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            )}

            {filteredIssues.length === 0 ? (
              <div style={{ color: "#6b7280" }}>
                {issues.length === 0 ? "No issues yet." : "No issues match your filters."}
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
                {filteredIssues.map((issue, index) => (
                  <IssueCard key={issue.id} issue={issue} tone={cardTones[index % cardTones.length]} apiBaseUrl={apiBaseUrl} />
                ))}
              </div>
            )}
          </div>

          <LeaderboardPanel entries={leaderboard} />
        </section>
      </div>
    </main>
  );
}
