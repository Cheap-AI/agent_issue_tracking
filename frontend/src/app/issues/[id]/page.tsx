"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
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

type EventItem = {
  id: number;
  event_date: string | null;
  discovered_at: string;
  title: string;
  description: string;
  source_urls: string[];
};

const getApiBaseUrl = () => {
  if (typeof window === "undefined") {
    return "/api";
  }

  return process.env.NEXT_PUBLIC_API_BASE_URL || "/api";
};

export default function IssueDetailPage() {
  const params = useParams();
  const issueId = Array.isArray(params.id) ? params.id[0] : params.id;

  const [issue, setIssue] = useState<Issue | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);

  useEffect(() => {
    if (!issueId) {
      return;
    }

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [issueResponse, eventsResponse] = await Promise.all([
          fetch(`${apiBaseUrl}/issues/${issueId}`),
          fetch(`${apiBaseUrl}/issues/${issueId}/events`),
        ]);

        if (!issueResponse.ok) {
          throw new Error("Issue not found");
        }

        const issueData = await issueResponse.json();
        setIssue(issueData.issue);

        if (eventsResponse.ok) {
          const eventsData = await eventsResponse.json();
          setEvents(eventsData.events || []);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unexpected error");
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [apiBaseUrl, issueId]);

  return (
    <main style={{ minHeight: "100vh", padding: "1.25rem", paddingTop: "5rem", fontFamily: "Inter, sans-serif", background: "linear-gradient(135deg, #f7f8ff 0%, #fdfcf8 100%)", color: "#14213d" }}>
      <div style={{ maxWidth: "820px", margin: "0 auto", display: "grid", gap: "1.25rem" }}>
        <Link href="/" style={{ textDecoration: "none", color: "#6b7280", fontSize: "0.9rem" }}>
          ← Back to issues
        </Link>

        {error ? <div style={{ color: "crimson" }}>{error}</div> : null}

        {loading ? (
          <div style={{ color: "#6b7280" }}>Loading...</div>
        ) : issue ? (
          <>
            <motion.header
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35 }}
              style={{ borderRadius: 28, padding: "1.4rem", background: "rgba(255,255,255,0.82)", border: "1px solid rgba(20,33,61,0.08)", boxShadow: "0 18px 45px rgba(20,33,61,0.08)" }}
            >
              <h1 style={{ margin: "0 0 0.6rem", fontSize: "1.6rem" }}>{issue.title}</h1>
              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "0.9rem" }}>
                {(issue.tags || []).map((tag) => (
                  <span key={tag} style={{ background: "rgba(20,33,61,0.05)", padding: "0.3rem 0.6rem", borderRadius: "999px", fontSize: "0.78rem" }}>
                    {tag}
                  </span>
                ))}
              </div>
              <div style={{ color: "#374151", lineHeight: 1.6, marginBottom: issue.why ? "0.9rem" : 0 }}>{issue.summary}</div>
              {issue.why ? (
                <div style={{ color: "#5b6473", lineHeight: 1.6, fontSize: "0.92rem", borderTop: "1px solid rgba(20,33,61,0.08)", paddingTop: "0.8rem" }}>
                  <strong>Why it matters: </strong>
                  {issue.why}
                </div>
              ) : null}
            </motion.header>

            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.05 }}
              style={{ borderRadius: 28, padding: "1.4rem", background: "rgba(255,255,255,0.82)", border: "1px solid rgba(20,33,61,0.08)", boxShadow: "0 18px 45px rgba(20,33,61,0.08)" }}
            >
              <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.15em", fontWeight: 700, color: "#6b7280", marginBottom: "0.9rem" }}>
                Timeline ({events.length} events)
              </div>

              {events.length === 0 ? (
                <div style={{ color: "#6b7280" }}>No events collected for this issue yet.</div>
              ) : (
                <div style={{ display: "grid", gap: "1rem" }}>
                  {events.map((event) => (
                    <div key={event.id} style={{ borderLeft: "2px solid rgba(59,130,246,0.35)", paddingLeft: "1rem" }}>
                      <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "#3b82f6" }}>{event.event_date || "Date unknown"}</div>
                      <div style={{ fontSize: "1rem", fontWeight: 700, margin: "0.2rem 0" }}>{event.title}</div>
                      <div style={{ color: "#374151", lineHeight: 1.55, marginBottom: "0.4rem" }}>{event.description}</div>
                      {event.source_urls.length > 0 ? (
                        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                          {event.source_urls.map((url) => (
                            <a key={url} href={url} target="_blank" rel="noopener noreferrer" style={{ fontSize: "0.8rem", color: "#8b5cf6" }}>
                              Source
                            </a>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </motion.section>
          </>
        ) : null}
      </div>
    </main>
  );
}
