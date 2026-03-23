import { useCallback, useEffect, useRef } from "react";
import type { ActionPayload, ChatMessage, WsClientMessage, WsServerMessage } from "../types/agent";

export interface WebSocketHandlers {
  onToken: (token: string) => void;
  onMessage: (message: ChatMessage) => void;
  onAction: (action: ActionPayload) => void;
  onConnected: () => void;
  onDisconnected: () => void;
  onConversationId?: (conversationId: string) => void;
}

export interface UseAgentWebSocketReturn {
  send: (payload: WsClientMessage) => boolean;
  disconnect: () => void;
}

const RECONNECT_DELAY_MS = 3000;

export function useAgentWebSocket(url: string, handlers: WebSocketHandlers): UseAgentWebSocketReturn {
  const socketRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef(handlers);

  handlersRef.current = handlers;

  useEffect(() => {
    if (typeof WebSocket === "undefined") {
      handlersRef.current.onDisconnected();
      return undefined;
    }

    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let shouldReconnect = true;

    const connect = () => {
      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => {
        handlersRef.current.onConnected();
      };

      socket.onmessage = (event: MessageEvent) => {
        let payload: WsServerMessage;
        try {
          payload = JSON.parse(String(event.data)) as WsServerMessage;
        } catch {
          return;
        }

        const legacyConversationId =
          typeof event.data === "string"
            ? (() => {
                try {
                  const parsed = JSON.parse(event.data) as {
                    data?: { conversation_id?: string; messages?: ChatMessage[]; action?: ActionPayload };
                  };
                  return parsed.data?.conversation_id;
                } catch {
                  return undefined;
                }
              })()
            : undefined;

        const conversationId = payload.conversation_id ?? legacyConversationId;
        if (conversationId) {
          handlersRef.current.onConversationId?.(conversationId);
        }

        const legacyPayload =
          typeof event.data === "string"
            ? (() => {
                try {
                  return JSON.parse(event.data) as {
                    type?: string;
                    data?: {
                      conversation_id?: string;
                      messages?: ChatMessage[];
                      action?: ActionPayload;
                    };
                  };
                } catch {
                  return undefined;
                }
              })()
            : undefined;

        switch (payload.type) {
          case "token":
            if (payload.token) {
              handlersRef.current.onToken(payload.token);
            }
            break;
          case "message":
            if (payload.message) {
              handlersRef.current.onMessage(payload.message);
            } else if (legacyPayload?.data?.messages?.length) {
              const assistantMessage = [...legacyPayload.data.messages]
                .reverse()
                .find((message) => message.role === "assistant");
              if (assistantMessage) {
                handlersRef.current.onMessage(assistantMessage);
              }
            }
            break;
          case "action":
            if (payload.action) {
              handlersRef.current.onAction(payload.action);
            } else if (legacyPayload?.data?.action) {
              handlersRef.current.onAction(legacyPayload.data.action);
            }
            break;
          case "done":
            handlersRef.current.onToken("\u0000");
            break;
          case "error":
            break;
        }
      };

      socket.onclose = () => {
        handlersRef.current.onDisconnected();
        if (shouldReconnect) {
          reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();

    return () => {
      shouldReconnect = false;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      if (socketRef.current) {
        socketRef.current.onclose = null;
        socketRef.current.close();
      }
    };
  }, [url]);

  const send = useCallback((payload: WsClientMessage) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return false;
    }

    socket.send(JSON.stringify(payload));
    return true;
  }, []);

  const disconnect = useCallback(() => {
    socketRef.current?.close();
  }, []);

  return { send, disconnect };
}
