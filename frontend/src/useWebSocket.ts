import { useEffect, useRef, useState } from 'react';
import type { WebSocketEvent } from './types';

export function useWebSocket(onEvent?: (event: WebSocketEvent) => void) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const onEventRef = useRef(onEvent);

  // Keep ref up to date without triggering reconnection loops
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    let isMounted = true;

    function connect() {
      if (!isMounted) return;
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/api/ws/events`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isMounted) setIsConnected(true);
        };

        ws.onmessage = (e) => {
          try {
            if (e.data === 'pong') return;
            const parsed = JSON.parse(e.data) as WebSocketEvent;
            if (onEventRef.current) {
              onEventRef.current(parsed);
            }
          } catch {
            // ignore non-json messages
          }
        };

        ws.onclose = () => {
          if (isMounted) {
            setIsConnected(false);
            // Reconnect after 3 seconds
            reconnectTimeoutRef.current = window.setTimeout(() => {
              connect();
            }, 3000);
          }
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        if (isMounted) setIsConnected(false);
      }
    }

    connect();

    // Heartbeat ping interval
    const pingInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, 25000);

    return () => {
      isMounted = false;
      clearInterval(pingInterval);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return { isConnected };
}
