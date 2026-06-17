"use client";

import { useState, useRef, useEffect } from "react";
import { chatApi, ChatMessage } from "@/lib/api";

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await chatApi.send(sessionId, trimmed);
      setMessages((prev) => [...prev, response]);
    } catch (err) {
      const errorMessage: ChatMessage = {
        id: `msg-err-${Date.now()}`,
        role: "assistant",
        content: `Error: ${err instanceof Error ? err.message : "Failed to get response"}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full max-h-[calc(100vh-8rem)] animate-fade-in">
      <h2 className="text-xl font-bold mb-4">Chat</h2>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-[var(--muted-foreground)]">
            <p className="text-sm">
              Start a conversation with MiLyfe Brain...
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-4 py-3 rounded-xl text-sm ${
                msg.role === "user"
                  ? "bg-[var(--primary)] text-white rounded-br-sm"
                  : "bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] rounded-bl-sm"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              <p
                className={`text-[10px] mt-1 ${
                  msg.role === "user"
                    ? "text-white text-opacity-60"
                    : "text-[var(--muted-foreground)]"
                }`}
              >
                {new Date(msg.timestamp).toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] rounded-bl-sm">
              <div className="flex gap-1.5" aria-label="Loading response">
                <span
                  className="w-2 h-2 rounded-full bg-[var(--muted-foreground)]"
                  style={{ animation: "bounce-dot 1.4s infinite ease-in-out both", animationDelay: "0s" }}
                />
                <span
                  className="w-2 h-2 rounded-full bg-[var(--muted-foreground)]"
                  style={{ animation: "bounce-dot 1.4s infinite ease-in-out both", animationDelay: "0.2s" }}
                />
                <span
                  className="w-2 h-2 rounded-full bg-[var(--muted-foreground)]"
                  style={{ animation: "bounce-dot 1.4s infinite ease-in-out both", animationDelay: "0.4s" }}
                />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSend}
        className="flex gap-2 border-t border-[var(--border)] pt-4"
      >
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={loading}
          className="flex-1 px-4 py-3 rounded-lg bg-[var(--muted)] border border-[var(--border)] text-[var(--foreground)] placeholder-[var(--muted-foreground)] focus:outline-none focus:border-[var(--primary)] disabled:opacity-50 transition-colors"
          aria-label="Chat message input"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="px-5 py-3 rounded-lg bg-[var(--primary)] text-white font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          aria-label="Send message"
        >
          Send
        </button>
      </form>
    </div>
  );
}
