"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { authFetch, useSession } from "@/lib/supabase";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

class RateLimitError extends Error {}

function getOrCreateSessionId(userId: string): string {
  // Per-user key so a shared browser doesn't reuse another account's session id.
  const key = `chat_session_id:${userId}`;
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

export function ChatWidget() {
  const { session, loading } = useSession();
  const userId = session?.user.id ?? null;
  const [open, setOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!userId) {
      setSessionId(null);
      setMessages([]);
      return;
    }
    const id = getOrCreateSessionId(userId);
    setSessionId(id);
    authFetch(`/chat/sessions/${id}/messages`)
      .then((response) => (response.ok ? response.json() : { messages: [] }))
      .then((data) => {
        const history: ChatMessage[] = (data.messages || [])
          .filter((m: { role: string }) => m.role === "user" || m.role === "assistant")
          .map((m: { role: string; content: string }) => ({ role: m.role, content: m.content }));
        setMessages(history);
      })
      .catch(() => setMessages([]));
  }, [userId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, open]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || !sessionId || sending) return;

    setInput("");
    setSending(true);
    setStatus(null);
    setMessages((prev) => [...prev, { role: "user", content: text }, { role: "assistant", content: "" }]);

    try {
      const response = await authFetch(`/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (response.status === 429) {
        const wait = response.headers.get("Retry-After");
        throw new RateLimitError(wait ? `You're sending messages too fast. Try again in ${wait}s.` : "Rate limit reached. Try again later.");
      }
      if (!response.ok || !response.body) {
        throw new Error("Chat request failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);
          if (event.type === "token") {
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = {
                role: "assistant",
                content: next[next.length - 1].content + event.text,
              };
              return next;
            });
          } else if (event.type === "tool_call") {
            setStatus(`using tool: ${event.name}…`);
          } else if (event.type === "done") {
            setStatus(null);
          }
        }
      }
    } catch (err) {
      const content = err instanceof RateLimitError ? err.message : "Sorry, something went wrong.";
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { role: "assistant", content };
        return next;
      });
    } finally {
      setSending(false);
      setStatus(null);
    }
  };

  return (
    <div className="chat">
      {open && (
        <section className="chat__panel" aria-label="Assistant">
          <div className="chat__head">
            <span>Assistant</span>
            <button type="button" className="chat__close" onClick={() => setOpen(false)} aria-label="Close assistant">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>

          <div ref={scrollRef} className="chat__log" aria-live="polite">
            {!loading && !session && (
              <p className="chat__hint">
                <Link href="/login">Sign in</Link> to chat with the assistant.
              </p>
            )}
            {session && messages.length === 0 && (
              <p className="chat__hint">Ask me about issues, the leaderboard, or reports.</p>
            )}
            {messages.map((message, index) => (
              <div key={index} className={`msg msg--${message.role}`}>
                {message.content || (sending && index === messages.length - 1 ? "…" : "")}
              </div>
            ))}
            {status && <p className="chat__status">{status}</p>}
          </div>

          <div className="chat__form">
            <label htmlFor="chat-input" className="visually-hidden">
              Message
            </label>
            <input
              id="chat-input"
              name="message"
              autoComplete="off"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Ask something…"
              className="input"
            />
            <button
              type="button"
              onClick={sendMessage}
              disabled={sending || !input.trim() || !session}
              className="btn btn--primary"
            >
              Send
            </button>
          </div>
        </section>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="btn chat__toggle"
        aria-expanded={open}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path
            d="M2.5 3.5h11v7h-6l-3 2.5v-2.5h-2z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </svg>
        {open ? "Close" : "Assistant"}
      </button>
    </div>
  );
}
