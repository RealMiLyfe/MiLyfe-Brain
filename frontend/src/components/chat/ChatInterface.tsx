"use client";

import { useState, useEffect, useRef } from "react";
import { chatSend, getChatHistory, listSessions } from "@/lib/api";
import type { ChatMessage, ChatSession } from "@/lib/api";
import { Send, Bot, User, Wrench, Loader2, Plus } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";
import { toast } from "sonner";

const MODELS = [
  { id: "phi3:mini", label: "Phi-3 Mini" },
  { id: "llama3.1:8b", label: "Llama 3.1 8B" },
  { id: "qwen2.5:14b", label: "Qwen 2.5 14B" },
  { id: "hermes3:latest", label: "Hermes 3" },
];

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("llama3.1:8b");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch sessions
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const data = await listSessions();
        setSessions(data);
        if (data.length > 0 && !currentSession) {
          setCurrentSession(data[0].id);
        }
      } catch {
        // Sessions may not be available
      }
    };
    fetchSessions();
  }, [currentSession]);

  // Fetch chat history when session changes
  useEffect(() => {
    if (!currentSession) return;
    const fetchHistory = async () => {
      try {
        const history = await getChatHistory(currentSession);
        setMessages(history);
      } catch {
        setMessages([]);
      }
    };
    fetchHistory();
  }, [currentSession]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
      session_id: currentSession || "default",
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    try {
      const response = await chatSend({
        message: userMessage.content,
        session_id: currentSession || undefined,
        model,
      });
      setMessages((prev) => [...prev, response]);
      if (!currentSession && response.session_id) {
        setCurrentSession(response.session_id);
      }
    } catch (error) {
      toast.error("Failed to send message");
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
    } finally {
      setIsTyping(false);
    }
  };

  const handleNewSession = () => {
    setCurrentSession(null);
    setMessages([]);
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* Sessions sidebar */}
      <div className="w-56 flex-shrink-0 card overflow-hidden flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            Sessions
          </h3>
          <button
            onClick={handleNewSession}
            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700"
            title="New session"
          >
            <Plus className="w-4 h-4 text-slate-500" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin space-y-1">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => setCurrentSession(session.id)}
              className={clsx(
                "w-full text-left px-3 py-2 rounded-lg text-xs transition-colors",
                currentSession === session.id
                  ? "bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700/50"
              )}
            >
              <p className="font-medium truncate">{session.title}</p>
              <p className="text-[10px] text-slate-400 mt-0.5">
                {session.message_count} messages
              </p>
            </button>
          ))}
          {sessions.length === 0 && (
            <p className="text-xs text-slate-400 text-center py-4">
              No sessions yet
            </p>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 card flex flex-col overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto scrollbar-thin px-4 py-3 space-y-4">
          <AnimatePresence>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </AnimatePresence>

          {/* Typing indicator */}
          {isTyping && (
            <motion.div
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 text-sm text-slate-500"
            >
              <Bot className="w-4 h-4" />
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </motion.div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div className="border-t border-slate-200 dark:border-slate-700 p-3">
          <div className="flex items-center gap-2">
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="px-2 py-1.5 text-xs bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-md focus:outline-none"
            >
              {MODELS.map((m) => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                placeholder="Type a message..."
                className="input-field pr-10"
                disabled={isTyping}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isTyping}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 disabled:opacity-30"
              >
                {isTyping ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const isTool = message.role === "tool";

  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx("flex gap-3", isUser && "flex-row-reverse")}
    >
      <div
        className={clsx(
          "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0",
          isUser
            ? "bg-primary-100 dark:bg-primary-900/30"
            : isTool
            ? "bg-amber-100 dark:bg-amber-900/30"
            : "bg-slate-100 dark:bg-slate-700"
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-primary-600 dark:text-primary-400" />
        ) : isTool ? (
          <Wrench className="w-4 h-4 text-amber-600 dark:text-amber-400" />
        ) : (
          <Bot className="w-4 h-4 text-slate-600 dark:text-slate-400" />
        )}
      </div>
      <div
        className={clsx(
          "max-w-[75%] px-4 py-2.5 rounded-2xl text-sm",
          isUser
            ? "bg-primary-600 text-white rounded-br-md"
            : isTool
            ? "bg-amber-50 dark:bg-amber-900/10 text-slate-700 dark:text-slate-300 border border-amber-200 dark:border-amber-800 rounded-bl-md font-mono text-xs"
            : "bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-bl-md"
        )}
      >
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
        {/* Tool calls */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-2 space-y-1 border-t border-slate-200 dark:border-slate-600 pt-2">
            {message.tool_calls.map((tc) => (
              <div key={tc.id} className="text-xs font-mono text-slate-500 dark:text-slate-400">
                <span className="text-amber-600 dark:text-amber-400">{tc.name}</span>
                ({JSON.stringify(tc.arguments).slice(0, 100)})
              </div>
            ))}
          </div>
        )}
        <span className="block text-[10px] mt-1 opacity-50">
          {new Date(message.timestamp).toLocaleTimeString()}
        </span>
      </div>
    </motion.div>
  );
}
