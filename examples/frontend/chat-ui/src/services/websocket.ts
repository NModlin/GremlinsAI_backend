import { WebSocketMessage, WebSocketConfig } from './types';

export class GremlinsWebSocketService {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private messageQueue: WebSocketMessage[] = [];
  private eventListeners: Map<string, Set<(data: any) => void>> = new Map();

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectAttempts: 5,
      reconnectDelay: 1000,
      heartbeatInterval: 30000,
      ...config,
    };
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      this.cleanup();

      try {
        const wsUrl = `${this.config.url}?token=${encodeURIComponent(this.config.apiKey)}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.processMessageQueue();
          this.emit('connect', {});
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected', event.code, event.reason);
          this.cleanup();
          this.emit('disconnect', { code: event.code, reason: event.reason });
          
          // Auto-reconnect if not intentionally closed
          if (event.code !== 1000 && this.reconnectAttempts < (this.config.reconnectAttempts || 5)) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.emit('error', error);
          reject(error);
        };

      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        reject(error);
      }
    });
  }

  disconnect(): void {
    this.cleanup();
    this.reconnectAttempts = this.config.reconnectAttempts || 5; // Prevent auto-reconnect
    if (this.ws) {
      this.ws.close(1000, 'Intentional disconnect');
    }
  }

  sendMessage(message: Omit<WebSocketMessage, 'timestamp'>): void {
    const fullMessage: WebSocketMessage = {
      ...message,
      timestamp: new Date().toISOString(),
    };

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(fullMessage));
    } else {
      // Queue message for when connection is restored
      this.messageQueue.push(fullMessage);
      
      // Try to reconnect if not already connecting
      if (this.ws?.readyState !== WebSocket.CONNECTING) {
        this.connect().catch(console.error);
      }
    }
  }

  // Event subscription methods
  on(event: string, callback: (data: any) => void): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback);
  }

  off(event: string, callback: (data: any) => void): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.delete(callback);
      if (listeners.size === 0) {
        this.eventListeners.delete(event);
      }
    }
  }

  // Convenience methods for common events
  onMessage(callback: (message: WebSocketMessage) => void): void {
    this.on('message', callback);
  }

  onConnect(callback: () => void): void {
    this.on('connect', callback);
  }

  onDisconnect(callback: (event: { code: number; reason: string }) => void): void {
    this.on('disconnect', callback);
  }

  onError(callback: (error: Event) => void): void {
    this.on('error', callback);
  }

  // Get connection status
  get connectionStatus(): 'connecting' | 'connected' | 'disconnected' | 'error' {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'error';
    }
  }

  private handleMessage(message: WebSocketMessage): void {
    // Handle internal messages
    switch (message.type) {
      case 'pong':
        // Heartbeat response - no action needed
        return;
      case 'error':
        console.error('WebSocket server error:', message.data);
        this.emit('error', message.data);
        return;
      default:
        // Emit to subscribers
        this.emit('message', message);
        this.emit(message.type, message.data);
    }
  }

  private emit(event: string, data: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in WebSocket event listener for ${event}:`, error);
        }
      });
    }
  }

  private startHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.sendMessage({
          type: 'ping',
          data: {},
        });
      }
    }, this.config.heartbeatInterval || 30000);
  }

  private scheduleReconnect(): void {
    const delay = (this.config.reconnectDelay || 1000) * Math.pow(2, this.reconnectAttempts);
    
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      console.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${this.config.reconnectAttempts}`);
      this.connect().catch(console.error);
    }, delay);
  }

  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift()!;
      this.ws.send(JSON.stringify(message));
    }
  }

  private cleanup(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }
}

// Create a singleton instance
let webSocketService: GremlinsWebSocketService | null = null;

export const createWebSocketService = (config?: Partial<WebSocketConfig>): GremlinsWebSocketService => {
  const fullConfig: WebSocketConfig = {
    url: process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8000/api/v1/ws',
    apiKey: process.env.REACT_APP_API_KEY || '',
    ...config,
  };

  if (!fullConfig.apiKey) {
    throw new Error('WebSocket API key is required');
  }

  webSocketService = new GremlinsWebSocketService(fullConfig);
  return webSocketService;
};

export const getWebSocketService = (): GremlinsWebSocketService => {
  if (!webSocketService) {
    return createWebSocketService();
  }
  return webSocketService;
};

export default GremlinsWebSocketService;
