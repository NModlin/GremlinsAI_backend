import { useState, useEffect, useCallback } from 'react';
import apiClient from '../services/api';
import { ConversationResponse, ConversationCreateRequest } from '../services/types';

interface UseConversationsOptions {
  userId?: string;
  autoLoad?: boolean;
  limit?: number;
}

interface UseConversationsReturn {
  conversations: ConversationResponse[];
  currentConversation: ConversationResponse | null;
  isLoading: boolean;
  error: string | null;
  hasMore: boolean;
  
  // Actions
  loadConversations: (reset?: boolean) => Promise<void>;
  createConversation: (title: string) => Promise<ConversationResponse>;
  selectConversation: (conversation: ConversationResponse) => void;
  deleteConversation: (conversationId: string) => Promise<void>;
  updateConversationTitle: (conversationId: string, title: string) => Promise<void>;
  refreshConversations: () => Promise<void>;
  loadMoreConversations: () => Promise<void>;
  clearError: () => void;
}

export const useConversations = (options: UseConversationsOptions = {}): UseConversationsReturn => {
  const {
    userId = process.env.REACT_APP_DEFAULT_USER_ID || 'default-user',
    autoLoad = true,
    limit = 20,
  } = options;

  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [currentConversation, setCurrentConversation] = useState<ConversationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const loadConversations = useCallback(async (reset = false) => {
    try {
      setIsLoading(true);
      setError(null);

      const currentOffset = reset ? 0 : offset;
      const response = await apiClient.getUserConversations(userId, limit, currentOffset);

      if (reset) {
        setConversations(response.conversations);
        setOffset(response.conversations.length);
      } else {
        setConversations(prev => [...prev, ...response.conversations]);
        setOffset(prev => prev + response.conversations.length);
      }

      setHasMore(response.conversations.length === limit);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [userId, limit, offset]);

  const createConversation = useCallback(async (title: string): Promise<ConversationResponse> => {
    try {
      setIsLoading(true);
      setError(null);

      const request: ConversationCreateRequest = {
        title: title.trim() || `New Chat ${new Date().toLocaleDateString()}`,
        user_id: userId,
      };

      const conversation = await apiClient.createConversation(request);

      // Add to the beginning of the list
      setConversations(prev => [conversation, ...prev]);
      setCurrentConversation(conversation);

      return conversation;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  const selectConversation = useCallback((conversation: ConversationResponse) => {
    setCurrentConversation(conversation);
  }, []);

  const deleteConversation = useCallback(async (conversationId: string) => {
    try {
      setIsLoading(true);
      setError(null);

      await apiClient.deleteConversation(conversationId);

      // Remove from list
      setConversations(prev => prev.filter(conv => conv.id !== conversationId));

      // Clear current conversation if it was deleted
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
      }
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [currentConversation]);

  const updateConversationTitle = useCallback(async (conversationId: string, title: string) => {
    try {
      setError(null);

      // Optimistically update the title
      const updatedConversations = conversations.map(conv =>
        conv.id === conversationId ? { ...conv, title } : conv
      );
      setConversations(updatedConversations);

      if (currentConversation?.id === conversationId) {
        setCurrentConversation({ ...currentConversation, title });
      }

      // Note: This would require a backend endpoint for updating conversation titles
      // For now, we'll just update locally
      console.warn('Conversation title update is local only - backend endpoint needed');
    } catch (err: any) {
      setError(err.message);
      // Revert optimistic update on error
      await refreshConversations();
      throw err;
    }
  }, [conversations, currentConversation]);

  const refreshConversations = useCallback(async () => {
    setOffset(0);
    await loadConversations(true);
  }, [loadConversations]);

  const loadMoreConversations = useCallback(async () => {
    if (!hasMore || isLoading) return;
    await loadConversations(false);
  }, [hasMore, isLoading, loadConversations]);

  // Auto-load conversations on mount
  useEffect(() => {
    if (autoLoad) {
      loadConversations(true);
    }
  }, [autoLoad, loadConversations]);

  return {
    conversations,
    currentConversation,
    isLoading,
    error,
    hasMore,
    loadConversations,
    createConversation,
    selectConversation,
    deleteConversation,
    updateConversationTitle,
    refreshConversations,
    loadMoreConversations,
    clearError,
  };
};
