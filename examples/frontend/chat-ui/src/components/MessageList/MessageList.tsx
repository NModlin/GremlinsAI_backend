import React, { useEffect, useRef, useCallback } from 'react';
import { MessageListProps, MessageResponse } from '../../services/types';
import { LoadingSpinner } from '../LoadingSpinner';
import styles from './MessageList.module.css';

interface MessageItemProps {
  message: MessageResponse;
}

const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const timestamp = new Date(message.created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className={`${styles.messageItem} ${isUser ? styles.userMessage : styles.assistantMessage}`}>
      <div className={styles.messageContent}>
        <div className={styles.messageText}>
          {message.content}
        </div>
        <div className={styles.messageMetadata}>
          <span className={styles.messageTime}>{timestamp}</span>
          {message.extra_data?.execution_time && (
            <span className={styles.executionTime}>
              {(message.extra_data.execution_time * 1000).toFixed(0)}ms
            </span>
          )}
        </div>
      </div>
      {!isUser && (
        <div className={styles.messageAvatar}>
          <span className={styles.avatarIcon}>🤖</span>
        </div>
      )}
      {isUser && (
        <div className={styles.messageAvatar}>
          <span className={styles.avatarIcon}>👤</span>
        </div>
      )}
    </div>
  );
};

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading = false,
  onLoadMore,
  hasMore = false,
  className,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = React.useState(true);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (shouldAutoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, shouldAutoScroll]);

  // Handle scroll events to determine if user has scrolled up
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    
    setShouldAutoScroll(isNearBottom);

    // Load more messages when scrolled to top
    if (scrollTop === 0 && hasMore && onLoadMore && !isLoading) {
      onLoadMore();
    }
  }, [hasMore, onLoadMore, isLoading]);

  // Attach scroll listener
  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className={`${styles.messageList} ${className || ''}`}>
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>💬</div>
          <h3>No messages yet</h3>
          <p>Start the conversation by sending a message below.</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className={`${styles.messageList} ${className || ''}`}
      role="log"
      aria-label="Chat messages"
      aria-live="polite"
    >
      {/* Load more indicator */}
      {hasMore && (
        <div className={styles.loadMoreContainer}>
          {isLoading ? (
            <LoadingSpinner size="small" />
          ) : (
            <button
              onClick={onLoadMore}
              className={styles.loadMoreButton}
              aria-label="Load more messages"
            >
              Load more messages
            </button>
          )}
        </div>
      )}

      {/* Messages */}
      <div className={styles.messagesContainer}>
        {messages.map((message, index) => (
          <MessageItem
            key={message.id}
            message={message}
          />
        ))}
        
        {/* Loading indicator for new messages */}
        {isLoading && messages.length > 0 && (
          <div className={styles.messageItem}>
            <div className={styles.typingIndicator}>
              <div className={styles.typingDots}>
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span className={styles.typingText}>AI is thinking...</span>
            </div>
          </div>
        )}
      </div>

      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  );
};
