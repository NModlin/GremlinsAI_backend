import React, { useState, useCallback } from 'react';
import { MessageList } from '../MessageList';
import { MessageInput } from '../MessageInput';
import { ConversationSidebar } from '../ConversationSidebar';
import { LoadingSpinner } from '../LoadingSpinner';
import { useGremlinsAPI } from '../../hooks/useGremlinsAPI';
import { ChatInterfaceProps, ConversationResponse } from '../../services/types';
import styles from './ChatInterface.module.css';

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  className,
  onConversationChange,
  onMessageSent,
  onError,
}) => {
  const {
    conversations,
    currentConversation,
    messages,
    isLoading,
    error,
    sendMessage,
    createConversation,
    switchConversation,
    loadMoreMessages,
    clearError,
  } = useGremlinsAPI();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [newConversationTitle, setNewConversationTitle] = useState('');

  // Handle message sending
  const handleSendMessage = useCallback(async (input: string) => {
    try {
      await sendMessage(input, currentConversation?.id);
      
      if (onMessageSent) {
        const newMessage = {
          id: `temp_${Date.now()}`,
          conversation_id: currentConversation?.id || '',
          role: 'user' as const,
          content: input,
          created_at: new Date().toISOString(),
        };
        onMessageSent(newMessage);
      }
    } catch (err: any) {
      if (onError) {
        onError(err.message);
      }
    }
  }, [sendMessage, currentConversation, onMessageSent, onError]);

  // Handle conversation selection
  const handleConversationSelect = useCallback(async (conversation: ConversationResponse) => {
    try {
      await switchConversation(conversation.id);
      setSidebarOpen(false);
      
      if (onConversationChange) {
        onConversationChange(conversation);
      }
    } catch (err: any) {
      if (onError) {
        onError(err.message);
      }
    }
  }, [switchConversation, onConversationChange, onError]);

  // Handle new conversation creation
  const handleNewConversation = useCallback(async () => {
    try {
      const title = newConversationTitle.trim() || `New Chat ${new Date().toLocaleDateString()}`;
      const conversation = await createConversation(title);
      setNewConversationTitle('');
      setSidebarOpen(false);
      
      if (onConversationChange) {
        onConversationChange(conversation);
      }
    } catch (err: any) {
      if (onError) {
        onError(err.message);
      }
    }
  }, [createConversation, newConversationTitle, onConversationChange, onError]);

  // Handle error dismissal
  const handleErrorDismiss = useCallback(() => {
    clearError();
  }, [clearError]);

  return (
    <div className={`${styles.chatInterface} ${className || ''}`}>
      {/* Mobile Header */}
      <div className={styles.mobileHeader}>
        <button
          className={styles.sidebarToggle}
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label="Toggle conversation list"
        >
          <span className={styles.hamburger}></span>
        </button>
        <h1 className={styles.title}>
          {currentConversation?.title || 'GremlinsAI Chat'}
        </h1>
      </div>

      {/* Sidebar */}
      <div className={`${styles.sidebar} ${sidebarOpen ? styles.sidebarOpen : ''}`}>
        <div className={styles.sidebarHeader}>
          <h2>Conversations</h2>
          <button
            className={styles.closeSidebar}
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            ×
          </button>
        </div>

        <div className={styles.newConversationForm}>
          <input
            type="text"
            placeholder="New conversation title..."
            value={newConversationTitle}
            onChange={(e) => setNewConversationTitle(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleNewConversation()}
            className={styles.newConversationInput}
          />
          <button
            onClick={handleNewConversation}
            className={styles.newConversationButton}
            disabled={isLoading}
          >
            Create
          </button>
        </div>

        <ConversationSidebar
          conversations={conversations}
          currentConversation={currentConversation}
          onConversationSelect={handleConversationSelect}
          onNewConversation={handleNewConversation}
          isLoading={isLoading}
          className={styles.conversationList}
        />
      </div>

      {/* Main Chat Area */}
      <div className={styles.mainContent}>
        {/* Error Banner */}
        {error && (
          <div className={styles.errorBanner}>
            <span className={styles.errorMessage}>{error}</span>
            <button
              onClick={handleErrorDismiss}
              className={styles.errorDismiss}
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
        )}

        {/* Chat Messages */}
        <div className={styles.messagesContainer}>
          {currentConversation ? (
            <MessageList
              messages={messages}
              isLoading={isLoading}
              onLoadMore={loadMoreMessages}
              hasMore={messages.length > 0}
              className={styles.messageList}
            />
          ) : (
            <div className={styles.welcomeScreen}>
              <div className={styles.welcomeContent}>
                <h2>Welcome to GremlinsAI</h2>
                <p>Start a new conversation or select an existing one from the sidebar.</p>
                <button
                  onClick={handleNewConversation}
                  className={styles.startChatButton}
                  disabled={isLoading}
                >
                  Start New Chat
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Message Input */}
        <div className={styles.inputContainer}>
          <MessageInput
            onSendMessage={handleSendMessage}
            disabled={isLoading}
            placeholder={
              currentConversation
                ? "Type your message..."
                : "Start a new conversation..."
            }
            className={styles.messageInput}
          />
        </div>

        {/* Loading Overlay */}
        {isLoading && (
          <div className={styles.loadingOverlay}>
            <LoadingSpinner />
          </div>
        )}
      </div>

      {/* Sidebar Backdrop */}
      {sidebarOpen && (
        <div
          className={styles.sidebarBackdrop}
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
};
