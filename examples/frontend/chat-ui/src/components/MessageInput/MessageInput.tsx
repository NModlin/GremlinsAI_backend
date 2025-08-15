import React, { useState, useRef, useCallback, useEffect } from 'react';
import { MessageInputProps } from '../../services/types';
import styles from './MessageInput.module.css';

const MAX_MESSAGE_LENGTH = parseInt(process.env.REACT_APP_MAX_MESSAGE_LENGTH || '4000');

export const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = "Type your message...",
  maxLength = MAX_MESSAGE_LENGTH,
  className,
}) => {
  const [input, setInput] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
  }, [input, adjustTextareaHeight]);

  // Handle input change
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length <= maxLength) {
      setInput(value);
    }
  }, [maxLength]);

  // Handle key press
  const handleKeyPress = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSend();
    }
  }, [isComposing]);

  // Handle composition events (for IME input)
  const handleCompositionStart = useCallback(() => {
    setIsComposing(true);
  }, []);

  const handleCompositionEnd = useCallback(() => {
    setIsComposing(false);
  }, []);

  // Handle send
  const handleSend = useCallback(() => {
    const trimmedInput = input.trim();
    if (trimmedInput && !disabled) {
      onSendMessage(trimmedInput);
      setInput('');
      
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [input, disabled, onSendMessage]);

  // Handle paste
  const handlePaste = useCallback((e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const pastedText = e.clipboardData.getData('text');
    const currentLength = input.length;
    const availableLength = maxLength - currentLength;
    
    if (pastedText.length > availableLength) {
      e.preventDefault();
      const truncatedText = pastedText.substring(0, availableLength);
      setInput(prev => prev + truncatedText);
    }
  }, [input.length, maxLength]);

  const remainingChars = maxLength - input.length;
  const isNearLimit = remainingChars < 100;
  const canSend = input.trim().length > 0 && !disabled;

  return (
    <div className={`${styles.messageInput} ${className || ''}`}>
      <div className={styles.inputContainer}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          onCompositionStart={handleCompositionStart}
          onCompositionEnd={handleCompositionEnd}
          onPaste={handlePaste}
          placeholder={placeholder}
          disabled={disabled}
          className={styles.textarea}
          rows={1}
          aria-label="Message input"
          aria-describedby="char-count send-button"
        />
        
        <button
          onClick={handleSend}
          disabled={!canSend}
          className={`${styles.sendButton} ${canSend ? styles.sendButtonActive : ''}`}
          aria-label="Send message"
          id="send-button"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22,2 15,22 11,13 2,9"></polygon>
          </svg>
        </button>
      </div>
      
      <div className={styles.inputFooter}>
        <div className={styles.inputHints}>
          <span className={styles.hint}>
            Press Enter to send, Shift+Enter for new line
          </span>
        </div>
        
        {isNearLimit && (
          <div 
            className={`${styles.charCount} ${remainingChars < 20 ? styles.charCountWarning : ''}`}
            id="char-count"
            aria-live="polite"
          >
            {remainingChars} characters remaining
          </div>
        )}
      </div>
    </div>
  );
};
