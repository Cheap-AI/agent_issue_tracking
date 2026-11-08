"use client";

import Link from "next/link";
import { useEffect, useId, useMemo, useState } from "react";
import { EMPTY_SELECTION, TagFilter, matchesTags, type TagSelection } from "../../components/tag-filter";

type Issue = {
  id: string;
  title: string;
  summary: string;
  why?: string;
  tags?: string[];
  geography?: string[];
  topics?: string[];
  affected_groups?: string[];
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

const formatScore = (score: number) => score.toFixed(1);

function Chevron() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M4 2l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

type IssueRowProps = {
  issue: Issue;
  ranked?: LeaderboardEntry;
  apiBaseUrl: string;
};

function IssueRow({ issue, ranked, apiBaseUrl }: IssueRowProps) {
  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const detailsId = useId();

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (!next || events !== null || loadingEvents) {
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
  const tags = (issue.tags || []).slice(0, 4);

  return (
    <tbody>
      <tr className={open ? "ledger__row--open" : undefined}>
        <td className="ledger__rank measured">
          {ranked ? `#${ranked.rank}` : <span className="visually-hidden">Unranked</span>}
        </td>
        <td>
          <Link href={`/issues/${issue.id}`} className="ledger__title">
            {issue.title}
          </Link>
          {tags.length > 0 ? (
            <ul className="ledger__tags" aria-label="Tags">
              {tags.map((tag) => (
                <li key={tag} className="tag">
                  {tag}
                </li>
              ))}
            </ul>
          ) : null}
          <button
            type="button"
            className="disclose"
            aria-expanded={open}
            aria-controls={detailsId}
            onClick={toggle}
          >
            <Chevron />
            {open ? "Hide details" : "Details"}
          </button>
        </td>
        <td className="ledger__score measured">{ranked ? formatScore(ranked.overall_score) : null}</td>
      </tr>
      {open ? (
        <tr className="ledger__row--open">
          <td />
          <td colSpan={2}>
            <div id={detailsId} className="details">
              <p>{issue.summary}</p>
              <div className="details__label">Recent events</div>
              {loadingEvents ? (
                <p className="muted">Loading…</p>
              ) : recentEvents.length === 0 ? (
                <p className="muted">No events collected yet.</p>
              ) : (
                <ul className="details__events">
                  {recentEvents.map((event) => (
                    <li key={event.id}>
                      <span className="event-date measured">{event.event_date || "Undated"}</span>
                      <span>{event.title}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </td>
        </tr>
      ) : null}
    </tbody>
  );
}

function LeaderboardPanel({ entries }: { entries: LeaderboardEntry[] }) {
  const shown = entries.slice(0, 20);
  const [lead, ...rest] = shown;
  const dimensions = lead?.dimension_scores ? Object.entries(lead.dimension_scores) : [];

  return (
    <section className="panel" aria-labelledby="leaderboard-heading">
      <div className="panel__head">
        <h2 id="leaderboard-heading">Leaderboard</h2>
      </div>
      {!lead ? (
        <p className="panel__empty">No ranked issues yet.</p>
      ) : (
        <>
          <div className="leader">
            <h3 className="leader__title">
              <Link href={`/issues/${lead.issue_id}`}>{lead.title}</Link>
            </h3>
            <div className="leader__score">
              <div className="reading" aria-label={`Overall score ${formatScore(lead.overall_score)}`}>
                {formatScore(lead.overall_score)}
              </div>
              <span className="leader__rank measured">Rank #{lead.rank}</span>
            </div>
            {dimensions.length > 0 ? (
              <dl className="dims">
                {dimensions.map(([name, value]) => (
                  <div key={name}>
                    <dt>{name.charAt(0).toUpperCase() + name.slice(1)}</dt>
                    <dd aria-hidden="true">
                      <span className="bar">
                        <span style={{ width: `${Math.max(0, Math.min(100, value * 10))}%` }} />
                      </span>
                    </dd>
                    <dd className="measured">{value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </div>
          {rest.length > 0 ? (
            <ol className="rank-list" start={rest[0].rank}>
              {rest.map((entry) => (
                <li key={entry.issue_id}>
                  <Link href={`/issues/${entry.issue_id}`}>
                    <span className="rank-list__rank measured">#{entry.rank}</span>
                    <span className="rank-list__title">{entry.title}</span>
                    <span className="measured">{formatScore(entry.overall_score)}</span>
                  </Link>
                </li>
              ))}
            </ol>
          ) : null}
        </>
      )}
    </section>
  );
}

export default function Home() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [tagSelection, setTagSelection] = useState<TagSelection>(EMPTY_SELECTION);
  const searchId = useId();

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

    filtered = filtered.filter((issue) => matchesTags(issue, tagSelection));

    return filtered;
  }, [issues, searchQuery, tagSelection]);

  const rankByIssue = useMemo(() => {
    const map = new Map<string, LeaderboardEntry>();
    leaderboard.forEach((entry) => map.set(entry.issue_id, entry));
    return map;
  }, [leaderboard]);

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
    <main className="container page">
      <header className="page-head">
        <h1>Discovered issues, ranked and tracked over time.</h1>
      </header>

      {error ? (
        <p className="notice notice--bad" role="alert">
          {error}
        </p>
      ) : null}

      <div className="workspace">
        <section className="panel" aria-labelledby="issues-heading">
          <div className="panel__head">
            <h2 id="issues-heading">Issues</h2>
            <span className="measured muted">
              {filteredIssues.length} of {issues.length}
            </span>
          </div>

          <div className="toolbar">
            <label htmlFor={searchId} className="visually-hidden">
              Search issues
            </label>
            <input
              id={searchId}
              name="search"
              type="search"
              autoComplete="off"
              className="input"
              placeholder="Search issues…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />

            {issues.length > 0 && (
              <TagFilter issues={issues} selection={tagSelection} onChange={setTagSelection} />
            )}
          </div>

          {filteredIssues.length === 0 ? (
            <p className="panel__empty">
              {issues.length === 0 ? "No issues yet." : "No issues match your filters."}
            </p>
          ) : (
            <table className="ledger">
              <thead>
                <tr>
                  <th scope="col" className="ledger__rank">Rank</th>
                  <th scope="col">Issue</th>
                  <th scope="col" className="ledger__score">Score</th>
                </tr>
              </thead>
              {filteredIssues.slice(0, 20).map((issue) => (
                <IssueRow
                  key={issue.id}
                  issue={issue}
                  ranked={rankByIssue.get(issue.id)}
                  apiBaseUrl={apiBaseUrl}
                />
              ))}
            </table>
          )}
        </section>

        <LeaderboardPanel entries={leaderboard} />
      </div>
    </main>
  );
}
