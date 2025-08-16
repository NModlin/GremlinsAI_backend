import { useState, useEffect, useCallback, useRef } from 'react';
import { WebSocketMessage, WebSocketConfig, UseWebSocketReturn } from '../services/types';

export const useWebSocket = (
  url: string,
  options: {
    apiKey?: string;
    reconnectAttempts?: number;
    reconnectDelay?: number;
    heartbeatInterval?: number;
    onMessage?: (message: WebSocketMessage) => void;
    onError?: (error: Event) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
  } = {}
): UseWebSocketReturn => {
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const heartbeatInterval = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  const {
    apiKey = process.env.REACT_APP_API_KEY,
    reconnectAttempts: maxReconnectAttempts = 5,
    reconnectDelay = 1000,
    heartbeatInterval: heartbeatMs = 30000,
    onMessage,
    onError,
    onConnect,
    onDisconnect,
  } = options;

  const cleanup = useCallback(() => {
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current);
      heartbeatInterval.current = null;
    }
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    cleanup();
    heartbeatInterval.current = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        sendMessage({
          type: 'ping',
          data: {},
          timestamp: new Date().toISOString(),
        });
      }
    }, heartbeatMs);
  }, [heartbeatMs]);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    cleanup();
    setConnectionStatus('connecting');

    try {
      const wsUrl = apiKey ? `${url}?token=${encodeURIComponent(apiKey)}` : url;
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
        startHeartbeat();
        onConnect?.();
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          
          // Handle pong messages internally
          if (message.type === 'pong') {
            return;
          }
          
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.current.onclose = (event) => {
        cleanup();
        setConnectionStatus('disconnected');
        onDisconnect?.();

        // Auto-reconnect logic (don't reconnect if closed intentionally)
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = reconnectDelay * Math.pow(2, reconnectAttempts.current); // Exponential backoff
          reconnectTimeout.current = setTimeout(() => {
            reconnectAttempts.current++;
            console.log(`Reconnecting... Attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`);
            connect();
          }, delay);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
        onError?.(error);
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('error');
    }
  }, [url, apiKey, maxReconnectAttempts, reconnectDelay, startHeartbeat, onConnect, onMessage, onDisconnect, onError, cleanup]);

  const sendMessage = useCallback((message: Omit<WebSocketMessage, 'timestamp'>) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      const fullMessage: WebSocketMessage = {
        ...message,
        timestamp: new Date().toISOString(),
      };
      ws.current.send(JSON.stringify(fullMessage));
    } else {
      throw new Error('WebSocket is not connected');
    }
  }, []);

  const disconnect = useCallback(() => {
    cleanup();
    reconnectAttempts.current = maxReconnectAttempts; // Prevent auto-reconnect
    if (ws.current) {
      ws.current.close(1000, 'Intentional disconnect');
    }
  }, [maxReconnectAttempts, cleanup]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connectionStatus,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
  };
};
