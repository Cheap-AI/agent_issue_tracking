"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
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
  // In production, use the full backend URL (e.g., https://backend.com/api)
  // In development, use /api which is proxied to localhost:8000
  return process.env.NEXT_PUBLIC_API_BASE_URL || "/api";
};

const hostOf = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
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
    <main className="container page">
      <Link href="/dashboard" className="backlink">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path d="M8 2L4 6l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Back to issues
      </Link>

      {error ? (
        <p className="notice notice--bad" role="alert">
          {error}
        </p>
      ) : null}

      {loading ? (
        <div className="detail" aria-busy="true">
          <div className="detail__main">
            <span className="skeleton" style={{ height: "2.4rem", width: "70%" }} />
            <span className="skeleton" style={{ height: "5rem" }} />
            <span className="skeleton" style={{ height: "12rem" }} />
          </div>
          <span className="skeleton" style={{ height: "7rem" }} />
          <span className="visually-hidden">Loading…</span>
        </div>
      ) : issue ? (
        <div className="detail">
          <div className="detail__main">
            <header className="page-head">
              <h1 className="detail__title">{issue.title}</h1>
              {(issue.tags || []).length > 0 ? (
                <ul className="ledger__tags" aria-label="Tags">
                  {(issue.tags || []).map((tag) => (
                    <li key={tag} className="tag">
                      {tag}
                    </li>
                  ))}
                </ul>
              ) : null}
            </header>

            <p className="detail__summary">{issue.summary}</p>

            {issue.why ? (
              <section className="why">
                <h2>Why it matters</h2>
                <p>{issue.why}</p>
              </section>
            ) : null}

            <section aria-labelledby="timeline-heading">
              <div className="trail-head">
                <h2 id="timeline-heading">Timeline</h2>
                <span className="measured muted">{events.length} events</span>
              </div>

              {events.length === 0 ? (
                <p className="panel__empty" style={{ paddingInline: 0 }}>
                  No events collected for this issue yet.
                </p>
              ) : (
                <ol className="trail" style={{ marginTop: "var(--space-lg)" }}>
                  {events.map((event) => (
                    <li key={event.id} className="trail__entry">
                      <span className="trail__date measured">{event.event_date || "Date unknown"}</span>
                      <h3 className="trail__title">{event.title}</h3>
                      <p className="trail__body">{event.description}</p>
                      {event.source_urls.length > 0 ? (
                        <div className="trail__sources">
                          {event.source_urls.map((url) => (
                            <a
                              key={url}
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              aria-label={`Source: ${hostOf(url)}`}
                            >
                              Source
                            </a>
                          ))}
                        </div>
                      ) : null}
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </div>

          <aside className="panel" aria-label="Record">
            <dl className="record">
              <div>
                <dt>Issue</dt>
                <dd className="measured">{issue.id}</dd>
              </div>
              <div>
                <dt>Events</dt>
                <dd className="measured">{events.length}</dd>
              </div>
            </dl>
          </aside>
        </div>
      ) : null}
    </main>
  );
}
