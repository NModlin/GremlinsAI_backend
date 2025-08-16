import React, { useCallback } from 'react';
import { ConversationSidebarProps, ConversationResponse } from '../../services/types';
import { LoadingSpinner } from '../LoadingSpinner';
import styles from './ConversationSidebar.module.css';

interface ConversationItemProps {
  conversation: ConversationResponse;
  isActive: boolean;
  onClick: (conversation: ConversationResponse) => void;
}

const ConversationItem: React.FC<ConversationItemProps> = ({
  conversation,
  isActive,
  onClick,
}) => {
  const handleClick = useCallback(() => {
    onClick(conversation);
  }, [conversation, onClick]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick(conversation);
    }
  }, [conversation, onClick]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);

    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffInHours < 24 * 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div
      className={`${styles.conversationItem} ${isActive ? styles.conversationItemActive : ''}`}
      onClick={handleClick}
      onKeyPress={handleKeyPress}
      tabIndex={0}
      role="button"
      aria-label={`Select conversation: ${conversation.title}`}
    >
      <div className={styles.conversationContent}>
        <div className={styles.conversationTitle}>
          {conversation.title}
        </div>
        <div className={styles.conversationMeta}>
          <span className={styles.messageCount}>
            {conversation.message_count} messages
          </span>
          <span className={styles.conversationDate}>
            {formatDate(conversation.updated_at)}
          </span>
        </div>
      </div>
      <div className={styles.conversationIndicator}>
        {isActive && <div className={styles.activeIndicator} />}
      </div>
    </div>
  );
};

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  currentConversation,
  onConversationSelect,
  onNewConversation,
  isLoading = false,
  className,
}) => {
  const handleConversationClick = useCallback((conversation: ConversationResponse) => {
    onConversationSelect(conversation);
  }, [onConversationSelect]);

  const handleNewConversationClick = useCallback(() => {
    onNewConversation();
  }, [onNewConversation]);

  if (isLoading && conversations.length === 0) {
    return (
      <div className={`${styles.conversationSidebar} ${className || ''}`}>
        <div className={styles.loadingContainer}>
          <LoadingSpinner />
          <span>Loading conversations...</span>
        </div>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className={`${styles.conversationSidebar} ${className || ''}`}>
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>💬</div>
          <h3>No conversations yet</h3>
          <p>Start your first conversation with the AI.</p>
          <button
            onClick={handleNewConversationClick}
            className={styles.newConversationButton}
            disabled={isLoading}
          >
            Start New Chat
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.conversationSidebar} ${className || ''}`}>
      <div className={styles.conversationList} role="list">
        {conversations.map((conversation) => (
          <ConversationItem
            key={conversation.id}
            conversation={conversation}
            isActive={currentConversation?.id === conversation.id}
            onClick={handleConversationClick}
          />
        ))}
      </div>
      
      {isLoading && (
        <div className={styles.loadingFooter}>
          <LoadingSpinner size="small" />
          <span>Loading...</span>
        </div>
      )}
    </div>
  );
};
