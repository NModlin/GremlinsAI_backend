import { GremlinsAPIClient } from './api';

// Mock fetch
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

describe('GremlinsAPIClient', () => {
  let apiClient: GremlinsAPIClient;
  const mockBaseURL = 'https://api.test.com/v1';
  const mockApiKey = 'test-api-key';

  beforeEach(() => {
    jest.clearAllMocks();
    apiClient = new GremlinsAPIClient(mockBaseURL, mockApiKey);
  });

  describe('constructor', () => {
    it('creates instance with valid parameters', () => {
      expect(apiClient).toBeInstanceOf(GremlinsAPIClient);
    });

    it('throws error when baseURL is empty', () => {
      expect(() => new GremlinsAPIClient('', mockApiKey)).toThrow('API base URL is required');
    });

    it('throws error when apiKey is empty', () => {
      expect(() => new GremlinsAPIClient(mockBaseURL, '')).toThrow('API key is required and cannot be empty');
    });

    it('throws error when apiKey is only whitespace', () => {
      expect(() => new GremlinsAPIClient(mockBaseURL, '   ')).toThrow('API key is required and cannot be empty');
    });

    it('accepts custom timeout option', () => {
      const customClient = new GremlinsAPIClient(mockBaseURL, mockApiKey, { timeout: 60000 });
      expect(customClient).toBeInstanceOf(GremlinsAPIClient);
    });
  });

  describe('invokeAgent', () => {
    it('makes POST request to /agent/invoke', async () => {
      const mockResponse = {
        output: 'Test response',
        context_used: false,
        execution_time: 0.5,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await apiClient.invokeAgent('Test input');

      expect(mockFetch).toHaveBeenCalledWith(
        `${mockBaseURL}/agent/invoke`,
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockApiKey}`,
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({ input: 'Test input' }),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('sanitizes input before sending', async () => {
      const maliciousInput = '<script>alert("xss")</script>Hello';
      const expectedSanitizedInput = '[SCRIPT_REMOVED]Hello';

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ output: 'Response' }),
      } as Response);

      await apiClient.invokeAgent(maliciousInput);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify({ input: expectedSanitizedInput }),
        })
      );
    });
  });

  describe('chat', () => {
    it('makes POST request to /agent/chat with correct payload', async () => {
      const chatRequest = {
        input: 'Hello',
        conversation_id: 'conv-123',
        save_conversation: true,
        use_multi_agent: false,
      };

      const mockResponse = {
        output: 'Hi there!',
        conversation_id: 'conv-123',
        context_used: true,
        execution_time: 1.2,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await apiClient.chat(chatRequest);

      expect(mockFetch).toHaveBeenCalledWith(
        `${mockBaseURL}/agent/chat`,
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(chatRequest),
        })
      );

      expect(result).toEqual(mockResponse);
    });
  });

  describe('createConversation', () => {
    it('makes POST request to /history/conversations', async () => {
      const request = {
        title: 'New Conversation',
        user_id: 'user-123',
      };

      const mockResponse = {
        id: 'conv-456',
        title: 'New Conversation',
        user_id: 'user-123',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z',
        message_count: 0,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await apiClient.createConversation(request);

      expect(mockFetch).toHaveBeenCalledWith(
        `${mockBaseURL}/history/conversations`,
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(request),
        })
      );

      expect(result).toEqual(mockResponse);
    });
  });

  describe('error handling', () => {
    it('handles 401 authentication errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ error_code: 'GREMLINS_1001' }),
      } as Response);

      await expect(apiClient.invokeAgent('test')).rejects.toThrow('Authentication failed');
    });

    it('handles 429 rate limit errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        json: async () => ({ error_code: 'RATE_LIMIT' }),
      } as Response);

      await expect(apiClient.invokeAgent('test')).rejects.toThrow('Too many requests');
    });

    it('handles network timeout errors', async () => {
      mockFetch.mockImplementationOnce(() => 
        new Promise((_, reject) => {
          setTimeout(() => reject(new Error('AbortError')), 100);
        })
      );

      // Mock AbortError
      const abortError = new Error('Request timeout');
      abortError.name = 'AbortError';
      mockFetch.mockRejectedValueOnce(abortError);

      await expect(apiClient.invokeAgent('test')).rejects.toThrow('Request timeout - please try again');
    });

    it('handles JSON parsing errors gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      } as Response);

      await expect(apiClient.invokeAgent('test')).rejects.toThrow();
    });
  });

  describe('request timeout', () => {
    it('aborts request after timeout', async () => {
      const shortTimeoutClient = new GremlinsAPIClient(mockBaseURL, mockApiKey, { timeout: 100 });

      // Mock a slow response
      mockFetch.mockImplementationOnce(() => 
        new Promise(resolve => setTimeout(resolve, 200))
      );

      const abortError = new Error('Request timeout');
      abortError.name = 'AbortError';
      mockFetch.mockRejectedValueOnce(abortError);

      await expect(shortTimeoutClient.invokeAgent('test')).rejects.toThrow('Request timeout - please try again');
    });
  });

  describe('input sanitization', () => {
    it('removes script tags from input', async () => {
      const maliciousInput = 'Hello <script>alert("xss")</script> world';
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ output: 'Response' }),
      } as Response);

      await apiClient.invokeAgent(maliciousInput);

      const callArgs = mockFetch.mock.calls[0][1];
      const body = JSON.parse(callArgs?.body as string);
      
      expect(body.input).toBe('Hello [SCRIPT_REMOVED] world');
    });

    it('removes javascript: protocols', async () => {
      const maliciousInput = 'Click javascript:alert("xss") here';
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ output: 'Response' }),
      } as Response);

      await apiClient.invokeAgent(maliciousInput);

      const callArgs = mockFetch.mock.calls[0][1];
      const body = JSON.parse(callArgs?.body as string);
      
      expect(body.input).toBe('Click javascript_removed:alert("xss") here');
    });

    it('removes event handlers', async () => {
      const maliciousInput = 'Text with onclick="alert()" handler';
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ output: 'Response' }),
      } as Response);

      await apiClient.invokeAgent(maliciousInput);

      const callArgs = mockFetch.mock.calls[0][1];
      const body = JSON.parse(callArgs?.body as string);
      
      expect(body.input).toBe('Text with event_removed="alert()" handler');
    });

    it('sanitizes nested objects', async () => {
      const chatRequest = {
        input: 'Safe input',
        metadata: {
          title: '<script>alert("xss")</script>Title',
          description: 'Safe description',
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ output: 'Response' }),
      } as Response);

      await apiClient.chat(chatRequest);

      const callArgs = mockFetch.mock.calls[0][1];
      const body = JSON.parse(callArgs?.body as string);
      
      expect(body.metadata.title).toBe('[SCRIPT_REMOVED]Title');
      expect(body.metadata.description).toBe('Safe description');
    });
  });

  describe('request headers', () => {
    it('includes required headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ output: 'Response' }),
      } as Response);

      await apiClient.invokeAgent('test');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockApiKey}`,
            'Content-Type': 'application/json',
            'X-Client-Version': '1.0.0',
            'X-Request-ID': expect.stringMatching(/^req_\d+_[a-z0-9]+$/),
          }),
        })
      );
    });
  });
});
