import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from './useWebSocket';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(public url: string) {
    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 10);
  }

  send = jest.fn();
  close = jest.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: 1000 }));
  });
}

global.WebSocket = MockWebSocket as any;

describe('useWebSocket', () => {
  const mockUrl = 'ws://localhost:8000/ws';
  const mockApiKey = 'test-api-key';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('initializes with disconnected status', () => {
    const { result } = renderHook(() => useWebSocket(mockUrl, { apiKey: mockApiKey }));

    expect(result.current.connectionStatus).toBe('disconnected');
    expect(result.current.lastMessage).toBeNull();
  });

  it('connects to WebSocket when connect is called', async () => {
    const { result } = renderHook(() => useWebSocket(mockUrl, { apiKey: mockApiKey }));

    act(() => {
      result.current.connect();
    });

    expect(result.current.connectionStatus).toBe('connecting');

    // Wait for connection to open
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    expect(result.current.connectionStatus).toBe('connected');
  });

  it('sends messages when connected', async () => {
    const { result } = renderHook(() => useWebSocket(mockUrl, { apiKey: mockApiKey }));

    act(() => {
      result.current.connect();
    });

    // Wait for connection
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    const testMessage = {
      type: 'chat' as const,
      data: { input: 'Hello' },
    };

    act(() => {
      result.current.sendMessage(testMessage);
    });

    expect(MockWebSocket.prototype.send).toHaveBeenCalledWith(
      JSON.stringify({
        ...testMessage,
        timestamp: expect.any(String),
      })
    );
  });

  it('throws error when sending message while disconnected', () => {
    const { result } = renderHook(() => useWebSocket(mockUrl, { apiKey: mockApiKey }));

    const testMessage = {
      type: 'chat' as const,
      data: { input: 'Hello' },
    };

    expect(() => {
      result.current.sendMessage(testMessage);
    }).toThrow('WebSocket is not connected');
  });

  it('handles incoming messages', async () => {
    const onMessage = jest.fn();
    const { result } = renderHook(() => 
      useWebSocket(mockUrl, { apiKey: mockApiKey, onMessage })
    );

    act(() => {
      result.current.connect();
    });

    // Wait for connection
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    // Simulate incoming message
    const mockMessage = {
      type: 'agent_response',
      data: { output: 'Hello there!' },
      timestamp: new Date().toISOString(),
    };

    act(() => {
      // Access the WebSocket instance and trigger onmessage
      const wsInstance = (global.WebSocket as any).mock.instances[0];
      wsInstance.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify(mockMessage)
      }));
    });

    expect(onMessage).toHaveBeenCalledWith(mockMessage);
    expect(result.current.lastMessage).toEqual(mockMessage);
  });

  it('disconnects WebSocket when disconnect is called', async () => {
    const { result } = renderHook(() => useWebSocket(mockUrl, { apiKey: mockApiKey }));

    act(() => {
      result.current.connect();
    });

    // Wait for connection
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    act(() => {
      result.current.disconnect();
    });

    expect(MockWebSocket.prototype.close).toHaveBeenCalledWith(1000, 'Intentional disconnect');
    expect(result.current.connectionStatus).toBe('disconnected');
  });

  it('handles connection errors', async () => {
    const onError = jest.fn();
    const { result } = renderHook(() => 
      useWebSocket(mockUrl, { apiKey: mockApiKey, onError })
    );

    act(() => {
      result.current.connect();
    });

    // Simulate error
    act(() => {
      const wsInstance = (global.WebSocket as any).mock.instances[0];
      wsInstance.onerror?.(new Event('error'));
    });

    expect(result.current.connectionStatus).toBe('error');
    expect(onError).toHaveBeenCalled();
  });

  it('attempts to reconnect on unexpected disconnection', async () => {
    const { result } = renderHook(() => 
      useWebSocket(mockUrl, { 
        apiKey: mockApiKey, 
        reconnectAttempts: 2,
        reconnectDelay: 100 
      })
    );

    act(() => {
      result.current.connect();
    });

    // Wait for connection
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    // Simulate unexpected disconnection (not code 1000)
    act(() => {
      const wsInstance = (global.WebSocket as any).mock.instances[0];
      wsInstance.readyState = MockWebSocket.CLOSED;
      wsInstance.onclose?.(new CloseEvent('close', { code: 1006 }));
    });

    expect(result.current.connectionStatus).toBe('disconnected');

    // Wait for reconnection attempt
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });

    // Should have created a new WebSocket instance for reconnection
    expect((global.WebSocket as any).mock.instances.length).toBeGreaterThan(1);
  });

  it('filters out pong messages from onMessage callback', async () => {
    const onMessage = jest.fn();
    const { result } = renderHook(() => 
      useWebSocket(mockUrl, { apiKey: mockApiKey, onMessage })
    );

    act(() => {
      result.current.connect();
    });

    // Wait for connection
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    // Simulate pong message
    const pongMessage = {
      type: 'pong',
      data: {},
      timestamp: new Date().toISOString(),
    };

    act(() => {
      const wsInstance = (global.WebSocket as any).mock.instances[0];
      wsInstance.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify(pongMessage)
      }));
    });

    // onMessage should not be called for pong messages
    expect(onMessage).not.toHaveBeenCalled();
    // But lastMessage should still be updated
    expect(result.current.lastMessage).toEqual(pongMessage);
  });

  it('cleans up on unmount', () => {
    const { result, unmount } = renderHook(() => useWebSocket(mockUrl, { apiKey: mockApiKey }));

    act(() => {
      result.current.connect();
    });

    unmount();

    expect(MockWebSocket.prototype.close).toHaveBeenCalled();
  });
});
