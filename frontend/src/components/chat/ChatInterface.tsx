"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User } from "lucide-react";
import { chatApi } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  tool_calls?: any[];
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const result = await chatApi.send(userMsg, sessionId || undefined);
      setSessionId(result.session_id);
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: result.response,
        tool_calls: result.tool_calls,
      }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", content: "Error: Failed to get response" }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-20">
            <Bot className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">Start a conversation with the AI assistant</p>
            <p className="text-gray-600 text-sm mt-1">Tools, code execution, and file access enabled</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}>
            {msg.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-brain-600 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-white" />
              </div>
            )}
            <div className={`max-w-[70%] rounded-xl px-4 py-3 ${
              msg.role === "user" ? "bg-brain-600 text-white" : "bg-gray-800 text-gray-200"
            }`}>
              <pre className="whitespace-pre-wrap text-sm font-sans">{msg.content}</pre>
              {msg.tool_calls && msg.tool_calls.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-700">
                  <p className="text-xs text-gray-400 mb-1">Tools used:</p>
                  {msg.tool_calls.map((tc, j) => (
                    <span key={j} className="inline-block text-xs bg-gray-700 rounded px-1.5 py-0.5 mr-1">{tc.name || tc.tool}</span>
                  ))}
                </div>
              )}
            </div>
            {msg.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center shrink-0">
                <User className="w-4 h-4 text-white" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-brain-600 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white animate-pulse" />
            </div>
            <div className="bg-gray-800 rounded-xl px-4 py-3">
              <div className="flex gap-1"><div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" /><div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100" /><div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200" /></div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Type a message..."
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-brain-500"
          />
          <button onClick={send} disabled={loading || !input.trim()} className="px-4 py-2.5 bg-brain-600 text-white rounded-lg hover:bg-brain-700 disabled:opacity-50">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
