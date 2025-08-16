import { useState, useCallback, useRef } from 'react';
import { MessageResponse, OptimisticMessage } from '../services/types';

interface UseOptimisticMessagesOptions {
  onOptimisticError?: (messageId: string, error: string) => void;
  onOptimisticSuccess?: (messageId: string, realMessage: MessageResponse) => void;
}

interface UseOptimisticMessagesReturn {
  messages: MessageResponse[];
  optimisticMessages: OptimisticMessage[];
  allMessages: MessageResponse[];
  
  // Actions
  setMessages: (messages: MessageResponse[]) => void;
  addOptimisticMessage: (content: string, conversationId: string) => string;
  updateOptimisticMessage: (messageId: string, updates: Partial<OptimisticMessage>) => void;
  removeOptimisticMessage: (messageId: string) => void;
  markOptimisticMessageAsPending: (messageId: string) => void;
  markOptimisticMessageAsError: (messageId: string, error: string) => void;
  replaceOptimisticMessage: (messageId: string, realMessage: MessageResponse) => void;
  clearOptimisticMessages: () => void;
  getOptimisticMessage: (messageId: string) => OptimisticMessage | undefined;
}

export const useOptimisticMessages = (
  options: UseOptimisticMessagesOptions = {}
): UseOptimisticMessagesReturn => {
  const { onOptimisticError, onOptimisticSuccess } = options;

  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [optimisticMessages, setOptimisticMessages] = useState<OptimisticMessage[]>([]);
  const optimisticIdCounter = useRef(0);

  const generateOptimisticId = useCallback((): string => {
    optimisticIdCounter.current += 1;
    return `optimistic_${Date.now()}_${optimisticIdCounter.current}`;
  }, []);

  const addOptimisticMessage = useCallback((content: string, conversationId: string): string => {
    const optimisticId = generateOptimisticId();
    
    const optimisticMessage: OptimisticMessage = {
      id: optimisticId,
      conversation_id: conversationId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      isOptimistic: true,
      isPending: false,
    };

    setOptimisticMessages(prev => [...prev, optimisticMessage]);
    return optimisticId;
  }, [generateOptimisticId]);

  const updateOptimisticMessage = useCallback((messageId: string, updates: Partial<OptimisticMessage>) => {
    setOptimisticMessages(prev =>
      prev.map(msg =>
        msg.id === messageId ? { ...msg, ...updates } : msg
      )
    );
  }, []);

  const removeOptimisticMessage = useCallback((messageId: string) => {
    setOptimisticMessages(prev => prev.filter(msg => msg.id !== messageId));
  }, []);

  const markOptimisticMessageAsPending = useCallback((messageId: string) => {
    updateOptimisticMessage(messageId, { isPending: true, error: undefined });
  }, [updateOptimisticMessage]);

  const markOptimisticMessageAsError = useCallback((messageId: string, error: string) => {
    updateOptimisticMessage(messageId, { 
      isPending: false, 
      error,
    });
    onOptimisticError?.(messageId, error);
  }, [updateOptimisticMessage, onOptimisticError]);

  const replaceOptimisticMessage = useCallback((messageId: string, realMessage: MessageResponse) => {
    // Remove the optimistic message
    removeOptimisticMessage(messageId);
    
    // Add the real message to the messages array if it's not already there
    setMessages(prev => {
      const exists = prev.some(msg => msg.id === realMessage.id);
      if (exists) {
        return prev;
      }
      
      // Insert in chronological order
      const newMessages = [...prev, realMessage];
      return newMessages.sort((a, b) => 
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
    });

    onOptimisticSuccess?.(messageId, realMessage);
  }, [removeOptimisticMessage, onOptimisticSuccess]);

  const clearOptimisticMessages = useCallback(() => {
    setOptimisticMessages([]);
  }, []);

  const getOptimisticMessage = useCallback((messageId: string): OptimisticMessage | undefined => {
    return optimisticMessages.find(msg => msg.id === messageId);
  }, [optimisticMessages]);

  // Combine real messages and optimistic messages, sorted by creation time
  const allMessages: MessageResponse[] = [...messages, ...optimisticMessages].sort((a, b) => 
    new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );

  return {
    messages,
    optimisticMessages,
    allMessages,
    setMessages,
    addOptimisticMessage,
    updateOptimisticMessage,
    removeOptimisticMessage,
    markOptimisticMessageAsPending,
    markOptimisticMessageAsError,
    replaceOptimisticMessage,
    clearOptimisticMessages,
    getOptimisticMessage,
  };
};
