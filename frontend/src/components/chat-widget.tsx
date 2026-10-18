"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/lib/utils";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

const SESSION_STORAGE_KEY = "chat_session_id";

function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "/api";
}

function getOrCreateSessionId(): string {
  let id = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(SESSION_STORAGE_KEY, id);
  }
  return id;
}

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const id = getOrCreateSessionId();
    setSessionId(id);
    fetch(`${getApiBaseUrl()}/chat/sessions/${id}/messages`)
      .then((response) => (response.ok ? response.json() : { messages: [] }))
      .then((data) => {
        const history: ChatMessage[] = (data.messages || [])
          .filter((m: { role: string }) => m.role === "user" || m.role === "assistant")
          .map((m: { role: string; content: string }) => ({ role: m.role, content: m.content }));
        setMessages(history);
      })
      .catch(() => setMessages([]));
  }, []);

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
      const response = await fetch(`${getApiBaseUrl()}/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
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
            setStatus(`using tool: ${event.name}...`);
          } else if (event.type === "done") {
            setStatus(null);
          }
        }
      }
    } catch {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { role: "assistant", content: "Sorry, something went wrong." };
        return next;
      });
    } finally {
      setSending(false);
      setStatus(null);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: "spring", duration: 0.3 }}
            className="mb-3 flex h-[480px] w-[360px] flex-col rounded-2xl border border-black/10 bg-white shadow-xl"
          >
            <div className="flex items-center justify-between rounded-t-2xl border-b border-black/10 px-4 py-3">
              <span className="text-sm font-semibold">Assistant</span>
              <button onClick={() => setOpen(false)} className="text-sm text-black/50 hover:text-black">
                ✕
              </button>
            </div>

            <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
              {messages.length === 0 && (
                <p className="text-sm text-black/40">Ask me about issues, the leaderboard, or reports.</p>
              )}
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={cn(
                    "max-w-[85%] whitespace-pre-wrap rounded-xl px-3 py-2 text-sm",
                    message.role === "user"
                      ? "ml-auto bg-black text-white"
                      : "bg-black/5 text-black"
                  )}
                >
                  {message.content || (sending && index === messages.length - 1 ? "..." : "")}
                </div>
              ))}
              {status && <p className="text-xs italic text-black/40">{status}</p>}
            </div>

            <div className="flex items-center gap-2 border-t border-black/10 p-3">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="Ask something..."
                className="flex-1 rounded-full border border-black/10 px-3 py-2 text-sm outline-none focus:border-black/30"
              />
              <button
                onClick={sendMessage}
                disabled={sending || !input.trim()}
                className="rounded-full bg-black px-3 py-2 text-sm text-white disabled:opacity-40"
              >
                Send
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onClick={() => setOpen((v) => !v)}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-black text-white shadow-lg"
      >
        {open ? "✕" : "💬"}
      </button>
    </div>
  );
}
