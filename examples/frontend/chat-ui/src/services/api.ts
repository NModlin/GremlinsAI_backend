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

  constructor(baseURL: string, apiKey: string) {
    this.baseURL = baseURL;
    this.apiKey = apiKey;
    this.rateLimitHandler = new RateLimitHandler();
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

    const response = await fetch(url.toString(), {
      method,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        'X-Request-ID': this.generateRequestId(),
      },
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(ErrorHandler.handle({ response: { data: errorData } }));
    }

    // Handle empty responses for DELETE requests
    if (method === 'DELETE' && response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Create a singleton instance
const apiClient = new GremlinsAPIClient(
  process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1',
  process.env.REACT_APP_API_KEY || ''
);

export default apiClient;
