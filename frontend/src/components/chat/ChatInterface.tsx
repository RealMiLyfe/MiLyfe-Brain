"use client";

import { useState, useRef, useEffect } from "react";
import { chatApi } from "@/lib/api";

interface Message {
  role: string;
  content: string;
  timestamp?: string;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res: any = await chatApi.send({
        message: input,
        session_id: sessionId || undefined,
      });
      if (res.session_id) setSessionId(res.session_id);
      const assistantMsg: Message = {
        role: "assistant",
        content: res.content || "No response",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e: any) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] animate-fadeIn">
      {/* Messages */}
      <div className="flex-1 overflow-auto space-y-4 mb-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-[var(--muted-foreground)]">
            <div className="text-center">
              <p className="text-lg mb-2">Chat with MiLyfe Brain</p>
              <p className="text-sm">Ask questions, run commands, or use /review, /fix, /explain</p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] px-4 py-2.5 rounded-lg text-sm ${
                msg.role === "user"
                  ? "bg-[var(--primary)] text-white"
                  : "bg-[var(--card)] border border-[var(--border)]"
              }`}
            >
              <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[var(--card)] border border-[var(--border)] px-4 py-2.5 rounded-lg">
              <div className="flex gap-1">
                <span className="w-2 h-2 rounded-full bg-[var(--muted-foreground)] animate-bounce" />
                <span className="w-2 h-2 rounded-full bg-[var(--muted-foreground)] animate-bounce delay-100" />
                <span className="w-2 h-2 rounded-full bg-[var(--muted-foreground)] animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
          placeholder="Type a message or /command..."
          className="flex-1 px-4 py-2.5 bg-[var(--card)] border border-[var(--border)] rounded-lg text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-[var(--primary)]"
        />
        <button
          onClick={sendMessage}
          disabled={!input.trim() || loading}
          className="px-6 py-2.5 bg-[var(--primary)] text-white rounded-lg hover:opacity-90 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
