// API Response Types
export interface AgentResponse {
  output: string;
  conversation_id?: string;
  message_id?: string;
  context_used: boolean;
  execution_time: number;
  extra_data?: {
    agent_used: boolean;
    context_used: boolean;
    execution_time: number;
  };
}

export interface ConversationResponse {
  id: string;
  title: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_at?: string;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  tool_calls?: Record<string, any>;
  extra_data?: Record<string, any>;
}

export interface MessageListResponse {
  conversation_id: string;
  messages: MessageResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface ConversationListResponse {
  conversations: ConversationResponse[];
  total: number;
  limit: number;
  offset: number;
}

// Request Types
export interface ChatRequest {
  input: string;
  conversation_id?: string;
  save_conversation?: boolean;
  use_multi_agent?: boolean;
}

export interface ConversationCreateRequest {
  title: string;
  user_id?: string;
}

export interface MultiAgentWorkflowRequest {
  input: string;
  workflow_type: 'research_analyze_write' | 'simple_research' | 'complex_analysis';
  save_conversation?: boolean;
}

// Error Types
export interface GremlinsError {
  error_code: string;
  error_message: string;
  error_details?: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  category: string;
  suggested_action: string;
  documentation_url: string;
  request_id: string;
  timestamp: string;
  affected_services: string[];
  validation_errors?: ValidationError[];
}

export interface ValidationError {
  field: string;
  message: string;
  invalid_value: any;
  expected_type: string;
}

// UI State Types
export interface ChatState {
  conversations: ConversationResponse[];
  currentConversation: ConversationResponse | null;
  messages: MessageResponse[];
  isLoading: boolean;
  error: string | null;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
}

export interface OptimisticMessage extends Omit<MessageResponse, 'id'> {
  id: string;
  isOptimistic?: boolean;
  isPending?: boolean;
  error?: string;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'chat' | 'agent_response' | 'error' | 'status';
  data: any;
  timestamp: string;
  request_id?: string;
}

export interface WebSocketConfig {
  url: string;
  apiKey: string;
  reconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
}

// Hook Types
export interface UseGremlinsAPIReturn {
  // State
  conversations: ConversationResponse[];
  currentConversation: ConversationResponse | null;
  messages: MessageResponse[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  sendMessage: (input: string, conversationId?: string) => Promise<void>;
  createConversation: (title: string) => Promise<ConversationResponse>;
  switchConversation: (conversationId: string) => Promise<void>;
  loadMoreMessages: () => Promise<void>;
  refreshConversations: () => Promise<void>;
  clearError: () => void;
}

export interface UseWebSocketReturn {
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: any) => void;
  connect: () => void;
  disconnect: () => void;
}

// Component Props Types
export interface ChatInterfaceProps {
  className?: string;
  onConversationChange?: (conversation: ConversationResponse | null) => void;
  onMessageSent?: (message: MessageResponse) => void;
  onError?: (error: string) => void;
}

export interface MessageListProps {
  messages: MessageResponse[];
  isLoading?: boolean;
  onLoadMore?: () => void;
  hasMore?: boolean;
  className?: string;
}

export interface MessageInputProps {
  onSendMessage: (input: string) => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  className?: string;
}

export interface ConversationSidebarProps {
  conversations: ConversationResponse[];
  currentConversation: ConversationResponse | null;
  onConversationSelect: (conversation: ConversationResponse) => void;
  onNewConversation: () => void;
  isLoading?: boolean;
  className?: string;
}

// Utility Types
export type MessageRole = 'user' | 'assistant';
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

// Configuration Types
export interface AppConfig {
  apiBaseUrl: string;
  wsBaseUrl: string;
  apiKey: string;
  defaultUserId: string;
  maxMessageLength: number;
  messagesPerPage: number;
  autoScrollThreshold: number;
  debounceDelay: number;
  virtualScrollThreshold: number;
  cacheTtl: number;
  enableWebSockets: boolean;
  enableMultiAgent: boolean;
  enableVoiceInput: boolean;
  debugMode: boolean;
  mockApi: boolean;
}
