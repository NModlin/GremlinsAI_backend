import { useState, useEffect, useCallback } from 'react';
import apiClient from '../services/api';
import {
  ConversationResponse,
  MessageResponse,
  UseGremlinsAPIReturn,
  ChatState,
} from '../services/types';

const MESSAGES_PER_PAGE = parseInt(process.env.REACT_APP_MESSAGES_PER_PAGE || '50');
const DEFAULT_USER_ID = process.env.REACT_APP_DEFAULT_USER_ID || 'default-user';

export const useGremlinsAPI = (): UseGremlinsAPIReturn => {
  const [state, setState] = useState<ChatState>({
    conversations: [],
    currentConversation: null,
    messages: [],
    isLoading: false,
    error: null,
    connectionStatus: 'disconnected',
  });

  const [messagesOffset, setMessagesOffset] = useState(0);
  const [hasMoreMessages, setHasMoreMessages] = useState(true);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Load messages when current conversation changes
  useEffect(() => {
    if (state.currentConversation) {
      loadMessages(state.currentConversation.id, true);
    } else {
      setState(prev => ({ ...prev, messages: [] }));
    }
  }, [state.currentConversation]);

  const setLoading = useCallback((isLoading: boolean) => {
    setState(prev => ({ ...prev, isLoading }));
  }, []);

  const setError = useCallback((error: string | null) => {
    setState(prev => ({ ...prev, error }));
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, [setError]);

  const loadConversations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.getUserConversations(DEFAULT_USER_ID);
      
      setState(prev => ({
        ...prev,
        conversations: response.conversations,
        isLoading: false,
      }));
    } catch (error: any) {
      setError(error.message);
      setLoading(false);
    }
  }, [setLoading, setError]);

  const loadMessages = useCallback(async (conversationId: string, reset = false) => {
    try {
      setLoading(true);
      setError(null);
      
      const offset = reset ? 0 : messagesOffset;
      const response = await apiClient.getConversationMessages(
        conversationId,
        MESSAGES_PER_PAGE,
        offset
      );
      
      setState(prev => ({
        ...prev,
        messages: reset 
          ? response.messages 
          : [...prev.messages, ...response.messages],
        isLoading: false,
      }));
      
      setMessagesOffset(reset ? response.messages.length : offset + response.messages.length);
      setHasMoreMessages(response.messages.length === MESSAGES_PER_PAGE);
    } catch (error: any) {
      setError(error.message);
      setLoading(false);
    }
  }, [messagesOffset, setLoading, setError]);

  const sendMessage = useCallback(async (input: string, conversationId?: string) => {
    try {
      setLoading(true);
      setError(null);

      // Create optimistic user message
      const optimisticMessage: MessageResponse = {
        id: `temp_${Date.now()}`,
        conversation_id: conversationId || '',
        role: 'user',
        content: input,
        created_at: new Date().toISOString(),
      };

      // Add optimistic message to UI
      setState(prev => ({
        ...prev,
        messages: [...prev.messages, optimisticMessage],
      }));

      const response = await apiClient.chat({
        input,
        conversation_id: conversationId,
        save_conversation: true,
        use_multi_agent: false,
      });

      // Remove optimistic message and reload messages
      if (response.conversation_id) {
        await loadMessages(response.conversation_id, true);
        
        // Update current conversation if it changed
        if (!conversationId || conversationId !== response.conversation_id) {
          const conversation = state.conversations.find(c => c.id === response.conversation_id);
          if (conversation) {
            setState(prev => ({ ...prev, currentConversation: conversation }));
          } else {
            // Reload conversations to get the new one
            await loadConversations();
          }
        }
      }

      setLoading(false);
    } catch (error: any) {
      // Remove optimistic message on error
      setState(prev => ({
        ...prev,
        messages: prev.messages.filter(msg => msg.id !== `temp_${Date.now()}`),
      }));
      
      setError(error.message);
      setLoading(false);
    }
  }, [state.conversations, loadMessages, loadConversations, setLoading, setError]);

  const createConversation = useCallback(async (title: string): Promise<ConversationResponse> => {
    try {
      setLoading(true);
      setError(null);
      
      const conversation = await apiClient.createConversation({
        title,
        user_id: DEFAULT_USER_ID,
      });
      
      setState(prev => ({
        ...prev,
        conversations: [conversation, ...prev.conversations],
        currentConversation: conversation,
        messages: [],
        isLoading: false,
      }));
      
      setMessagesOffset(0);
      setHasMoreMessages(true);
      
      return conversation;
    } catch (error: any) {
      setError(error.message);
      setLoading(false);
      throw error;
    }
  }, [setLoading, setError]);

  const switchConversation = useCallback(async (conversationId: string) => {
    try {
      const conversation = state.conversations.find(c => c.id === conversationId);
      if (!conversation) {
        throw new Error('Conversation not found');
      }
      
      setState(prev => ({
        ...prev,
        currentConversation: conversation,
        messages: [],
      }));
      
      setMessagesOffset(0);
      setHasMoreMessages(true);
    } catch (error: any) {
      setError(error.message);
    }
  }, [state.conversations, setError]);

  const loadMoreMessages = useCallback(async () => {
    if (!state.currentConversation || !hasMoreMessages || state.isLoading) {
      return;
    }
    
    await loadMessages(state.currentConversation.id, false);
  }, [state.currentConversation, hasMoreMessages, state.isLoading, loadMessages]);

  const refreshConversations = useCallback(async () => {
    await loadConversations();
  }, [loadConversations]);

  return {
    conversations: state.conversations,
    currentConversation: state.currentConversation,
    messages: state.messages,
    isLoading: state.isLoading,
    error: state.error,
    sendMessage,
    createConversation,
    switchConversation,
    loadMoreMessages,
    refreshConversations,
    clearError,
  };
};
