"use client";

import Link from "next/link";
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

const getApiBaseUrl = () => {
  if (typeof window === "undefined") {
    return "/api";
  }

  return process.env.NEXT_PUBLIC_API_BASE_URL || "/api";
};

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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

  return (
    <main style={{ minHeight: "100vh", padding: "1rem", fontFamily: "sans-serif" }}>
      <nav style={{ display: "flex", gap: "1rem", marginBottom: "2rem" }}>
        <Link href="/">Home</Link>
        <Link href="/about">About</Link>
      </nav>

      <div style={{ maxWidth: "900px", margin: "0 auto", display: "grid", gap: "1.5rem" }}>
        <section>
          <h1>Issue Tracking Starter</h1>
          <p>This page now calls the FastAPI backend and renders live issue data.</p>
        </section>

        <section style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "1rem" }}>
          <h2 style={{ marginTop: 0 }}>Backend health</h2>
          <button onClick={() => { void loadHealth(); }} style={{ marginBottom: "1rem" }}>
            Check backend health
          </button>

          {health ? (
            <div>
              <p><strong>Status:</strong> {health.status}</p>
              <p><strong>Service:</strong> {health.service}</p>
              <p><strong>Message:</strong> {health.message}</p>
            </div>
          ) : (
            <p>Loading backend status...</p>
          )}
        </section>

        <section style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "1rem" }}>
          <h2 style={{ marginTop: 0 }}>Create issue</h2>
          <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.75rem" }}>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Issue title"
              style={{ padding: "0.6rem" }}
            />
            <textarea
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
              placeholder="Issue summary"
              rows={4}
              style={{ padding: "0.6rem" }}
            />
            <button type="submit" disabled={loading}>
              {loading ? "Creating..." : "Create issue"}
            </button>
          </form>
        </section>

        <section style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "1rem" }}>
          <h2 style={{ marginTop: 0 }}>Current issues</h2>
          {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
          {issues.length === 0 ? (
            <p>No issues yet.</p>
          ) : (
            <ul style={{ paddingLeft: "1.2rem" }}>
              {issues.map((issue) => (
                <li key={issue.id} style={{ marginBottom: "0.75rem" }}>
                  <strong>{issue.title}</strong>
                  <div>{issue.summary}</div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
