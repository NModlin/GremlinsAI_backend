import {
  AgentResponse,
  ChatRequest,
  ConversationResponse,
  ConversationCreateRequest,
  MessageListResponse,
  ConversationListResponse,
  MultiAgentWorkflowRequest,
  GremlinsError,
} from './types';

class ErrorHandler {
  static handle(error: any): string {
    if (error.response?.data) {
      const errorData = error.response.data as GremlinsError;
      const status = error.response.status;

      // Handle specific HTTP status codes
      switch (status) {
        case 401:
          return 'Authentication failed. Please check your API key.';
        case 403:
          return 'Access forbidden. You do not have permission to perform this action.';
        case 404:
          return 'Resource not found. Please check the request URL.';
        case 429:
          return 'Too many requests. Please wait before trying again.';
        case 500:
          return 'Server error. Please try again later.';
        case 503:
          return 'Service temporarily unavailable. Please try again later.';
      }

      // Handle specific error codes
      switch (errorData.error_code) {
        case 'GREMLINS_1001':
          return 'Authentication failed. Please check your API key.';
        case 'GREMLINS_1003':
          return 'Invalid input. Please check your request data.';
        case 'GREMLINS_2001':
          return 'Agent processing failed. Please try again.';
        case 'GREMLINS_3001':
          return 'Database error. Please contact support.';
        case 'GREMLINS_4001':
          return 'External service unavailable. Please try again later.';
        default:
          return errorData.error_message || 'An unexpected error occurred.';
      }
    }

    // Handle network and other errors
    if (error.message?.includes('timeout')) {
      return 'Request timed out. Please check your connection and try again.';
    }

    return error.message || 'Network error occurred.';
  }

  static isRetryable(error: any): boolean {
    const retryableCodes = ['GREMLINS_4001', 'GREMLINS_5001'];
    return error.response?.data?.error_code && 
           retryableCodes.includes(error.response.data.error_code);
  }
}

class RateLimitHandler {
  private requestQueue: Array<{
    requestFn: () => Promise<any>;
    resolve: (value: any) => void;
    reject: (error: any) => void;
  }> = [];
  private isProcessing = false;

  async makeRequest<T>(requestFn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.requestQueue.push({ requestFn, resolve, reject });
      this.processQueue();
    });
  }

  private async processQueue(): Promise<void> {
    if (this.isProcessing || this.requestQueue.length === 0) {
      return;
    }

    this.isProcessing = true;

    while (this.requestQueue.length > 0) {
      const { requestFn, resolve, reject } = this.requestQueue.shift()!;

      try {
        const response = await requestFn();
        resolve(response);
      } catch (error: any) {
        if (error.status === 429) {
          // Rate limited, wait and retry
          const retryAfter = parseInt(error.headers?.['retry-after'] || '60');
          await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
          this.requestQueue.unshift({ requestFn, resolve, reject });
        } else {
          reject(error);
        }
      }
    }

    this.isProcessing = false;
  }
}

export class GremlinsAPIClient {
  private baseURL: string;
  private apiKey: string;
  private rateLimitHandler: RateLimitHandler;
  private requestTimeout: number;

  constructor(baseURL: string, apiKey: string, options?: { timeout?: number }) {
    // Validate required parameters
    if (!baseURL) {
      throw new Error('API base URL is required');
    }
    if (!apiKey || apiKey.trim() === '') {
      throw new Error('API key is required and cannot be empty');
    }

    this.baseURL = baseURL;
    this.apiKey = apiKey.trim();
    this.rateLimitHandler = new RateLimitHandler();
    this.requestTimeout = options?.timeout || 30000; // 30 seconds default
  }

  async invokeAgent(input: string): Promise<AgentResponse> {
    return this.rateLimitHandler.makeRequest(() =>
      this.makeRequest<AgentResponse>('POST', '/agent/invoke', { input })
    );
  }

  async chat(request: ChatRequest): Promise<AgentResponse> {
    return this.rateLimitHandler.makeRequest(() =>
      this.makeRequest<AgentResponse>('POST', '/agent/chat', request)
    );
  }

  async createConversation(request: ConversationCreateRequest): Promise<ConversationResponse> {
    return this.rateLimitHandler.makeRequest(() =>
      this.makeRequest<ConversationResponse>('POST', '/history/conversations', request)
    );
  }

  async getConversationMessages(
    conversationId: string,
    limit = 50,
    offset = 0
  ): Promise<MessageListResponse> {
    return this.rateLimitHandler.makeRequest(() =>
      this.makeRequest<MessageListResponse>(
        'GET',
        `/history/conversations/${conversationId}/messages`,
        null,
        { limit, offset }
      )
    );
  }

  async getUserConversations(
    userId = 'default-user',
    limit = 20,
    offset = 0
  ): Promise<ConversationListResponse> {
    return this.rateLimitHandler.makeRequest(() =>
      this.makeRequest<ConversationListResponse>(
        'GET',
        '/history/conversations',
        null,
        { user_id: userId, limit, offset }
      )
    );
  }

  async executeMultiAgentWorkflow(request: MultiAgentWorkflowRequest): Promise<AgentResponse> {
    return this.rateLimitHandler.makeRequest(() =>
      this.makeRequest<AgentResponse>('POST', '/multi-agent/workflow', request)
    );
  }

  async deleteConversation(conversationId: string): Promise<void> {
    return this.rateLimitHandler.makeRequest(() =>
      this.makeRequest<void>('DELETE', `/history/conversations/${conversationId}`)
    );
  }

  private async makeRequest<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    endpoint: string,
    data?: any,
    params?: Record<string, any>
  ): Promise<T> {
    const url = new URL(endpoint, this.baseURL);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, String(value));
      });
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.requestTimeout);

    try {
      // Sanitize request data if present
      const sanitizedData = data ? this.sanitizeRequestData(data) : undefined;

      const response = await fetch(url.toString(), {
        method,
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
          'X-Request-ID': this.generateRequestId(),
          'X-Client-Version': '1.0.0',
        },
        body: sanitizedData ? JSON.stringify(sanitizedData) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(ErrorHandler.handle({ response: { data: errorData, status: response.status } }));
      }

      // Handle empty responses for DELETE requests
      if (method === 'DELETE' && response.status === 204) {
        return undefined as T;
      }

      return response.json();
    } catch (error: any) {
      clearTimeout(timeoutId);

      if (error.name === 'AbortError') {
        throw new Error('Request timeout - please try again');
      }

      // Re-throw other errors
      throw error;
    }
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private sanitizeRequestData(data: any): any {
    if (typeof data === 'string') {
      return this.sanitizeInput(data);
    }

    if (Array.isArray(data)) {
      return data.map(item => this.sanitizeRequestData(item));
    }

    if (data && typeof data === 'object') {
      const sanitized: any = {};
      for (const [key, value] of Object.entries(data)) {
        sanitized[key] = this.sanitizeRequestData(value);
      }
      return sanitized;
    }

    return data;
  }

  private sanitizeInput(input: string): string {
    if (typeof input !== 'string') return input;

    return input
      // Remove script tags and their content
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '[SCRIPT_REMOVED]')
      // Remove javascript: protocols
      .replace(/javascript:/gi, 'javascript_removed:')
      // Remove event handlers
      .replace(/on\w+\s*=/gi, 'event_removed=')
      // Remove data: URLs that could contain scripts
      .replace(/data:text\/html/gi, 'data_removed:text/html')
      .trim();
  }
}

// Create a singleton instance with proper validation
const createAPIClient = (): GremlinsAPIClient => {
  const baseURL = process.env.REACT_APP_API_BASE_URL;
  const apiKey = process.env.REACT_APP_API_KEY;

  if (!baseURL) {
    throw new Error('REACT_APP_API_BASE_URL environment variable is required');
  }

  if (!apiKey) {
    throw new Error('REACT_APP_API_KEY environment variable is required');
  }

  return new GremlinsAPIClient(baseURL, apiKey, {
    timeout: parseInt(process.env.REACT_APP_REQUEST_TIMEOUT || '30000', 10)
  });
};

const apiClient = createAPIClient();

export default apiClient;
