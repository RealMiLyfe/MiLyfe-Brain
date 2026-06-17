"use client";

import { useEffect, useRef, useCallback } from "react";
import { useStore } from "@/lib/store";
import type { StreamEvent } from "@/lib/api";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8200/api/stream/ws";
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

/**
 * WebSocket hook for real-time agent event streaming.
 *
 * Connects to the backend WebSocket endpoint, handles reconnection,
 * and dispatches events to the Zustand store.
 */
export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);

  const setConnected = useStore((s) => s.setConnected);
  const addEvent = useStore((s) => s.addEvent);
  const addApproval = useStore((s) => s.addApproval);
  const setPlaybook = useStore((s) => s.setPlaybook);

  const connect = useCallback(() => {
    // Don't reconnect if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          // Map to StreamEvent format
          const streamEvent: StreamEvent = {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            type: msg.event || "update",
            content: JSON.stringify(msg.data || {}),
            timestamp: new Date(msg.timestamp * 1000).toISOString(),
            agent_role: msg.data?.agent_role,
            metadata: msg.data,
          };

          addEvent(streamEvent);

          // Handle specific event types
          if (msg.event === "approval_required" && msg.data) {
            addApproval({
              id: msg.data.id || streamEvent.id,
              action: msg.data.action_type || "unknown",
              description: msg.data.description || "",
              agent_role: msg.data.agent_role || "",
              created_at: streamEvent.timestamp,
              risk_level: msg.data.risk_level || "medium",
            });
          }

          if (msg.event === "playbook_completed" || msg.event === "playbook_failed") {
            // Trigger a refetch of playbook status
            // The Dashboard component can react to this event
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;

        // Attempt reconnection
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1;
          reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
        }
      };

      ws.onerror = () => {
        // onclose will fire after this — reconnect handled there
        ws.close();
      };
    } catch {
      setConnected(false);
    }
  }, [setConnected, addEvent, addApproval]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, [setConnected]);

  const sendMessage = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // Auto-connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    isConnected: useStore((s) => s.isConnected),
    sendMessage,
    reconnect: connect,
    disconnect,
  };
}
