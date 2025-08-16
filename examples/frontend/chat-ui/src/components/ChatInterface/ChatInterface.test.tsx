import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInterface } from './ChatInterface';
import * as useGremlinsAPIModule from '../../hooks/useGremlinsAPI';

// Mock the useGremlinsAPI hook
const mockUseGremlinsAPI = {
  conversations: [],
  currentConversation: null,
  messages: [],
  isLoading: false,
  error: null,
  sendMessage: jest.fn(),
  createConversation: jest.fn(),
  switchConversation: jest.fn(),
  loadMoreMessages: jest.fn(),
  clearError: jest.fn(),
};

jest.mock('../../hooks/useGremlinsAPI', () => ({
  useGremlinsAPI: () => mockUseGremlinsAPI,
}));

// Mock CSS modules
jest.mock('./ChatInterface.module.css', () => ({
  chatInterface: 'chatInterface',
  mobileHeader: 'mobileHeader',
  sidebarToggle: 'sidebarToggle',
  title: 'title',
  sidebar: 'sidebar',
  mainContent: 'mainContent',
  welcomeScreen: 'welcomeScreen',
  welcomeContent: 'welcomeContent',
  startChatButton: 'startChatButton',
  messagesContainer: 'messagesContainer',
  inputContainer: 'inputContainer',
  errorBanner: 'errorBanner',
  errorMessage: 'errorMessage',
  errorDismiss: 'errorDismiss',
}));

describe('ChatInterface', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    jest.clearAllMocks();
    // Reset mock implementation
    Object.assign(mockUseGremlinsAPI, {
      conversations: [],
      currentConversation: null,
      messages: [],
      isLoading: false,
      error: null,
      sendMessage: jest.fn(),
      createConversation: jest.fn(),
      switchConversation: jest.fn(),
      loadMoreMessages: jest.fn(),
      clearError: jest.fn(),
    });
  });

  it('renders welcome screen when no current conversation', () => {
    render(<ChatInterface />);
    
    expect(screen.getByText('Welcome to GremlinsAI')).toBeInTheDocument();
    expect(screen.getByText('Start a new conversation or select an existing one from the sidebar.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start new chat/i })).toBeInTheDocument();
  });

  it('renders chat interface when conversation is selected', () => {
    const mockConversation = {
      id: 'conv-1',
      title: 'Test Conversation',
      user_id: 'user-1',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      message_count: 2,
    };

    mockUseGremlinsAPI.currentConversation = mockConversation;
    mockUseGremlinsAPI.messages = [
      {
        id: 'msg-1',
        conversation_id: 'conv-1',
        role: 'user',
        content: 'Hello',
        created_at: '2023-01-01T00:00:00Z',
      },
      {
        id: 'msg-2',
        conversation_id: 'conv-1',
        role: 'assistant',
        content: 'Hi there!',
        created_at: '2023-01-01T00:00:01Z',
      },
    ];

    render(<ChatInterface />);
    
    expect(screen.getByText('Test Conversation')).toBeInTheDocument();
    expect(screen.queryByText('Welcome to GremlinsAI')).not.toBeInTheDocument();
  });

  it('displays error banner when error exists', () => {
    mockUseGremlinsAPI.error = 'Test error message';

    render(<ChatInterface />);
    
    expect(screen.getByText('Test error message')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /dismiss error/i })).toBeInTheDocument();
  });

  it('clears error when dismiss button is clicked', async () => {
    mockUseGremlinsAPI.error = 'Test error message';

    render(<ChatInterface />);
    
    const dismissButton = screen.getByRole('button', { name: /dismiss error/i });
    await user.click(dismissButton);
    
    expect(mockUseGremlinsAPI.clearError).toHaveBeenCalledTimes(1);
  });

  it('creates new conversation when start chat button is clicked', async () => {
    const mockCreateConversation = jest.fn().mockResolvedValue({
      id: 'new-conv',
      title: 'New Chat',
      user_id: 'user-1',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      message_count: 0,
    });

    mockUseGremlinsAPI.createConversation = mockCreateConversation;

    render(<ChatInterface />);
    
    const startChatButton = screen.getByRole('button', { name: /start new chat/i });
    await user.click(startChatButton);
    
    expect(mockCreateConversation).toHaveBeenCalledWith(expect.stringContaining('New Chat'));
  });

  it('handles conversation creation error', async () => {
    const mockCreateConversation = jest.fn().mockRejectedValue(new Error('Creation failed'));
    const mockOnError = jest.fn();

    mockUseGremlinsAPI.createConversation = mockCreateConversation;

    render(<ChatInterface onError={mockOnError} />);
    
    const startChatButton = screen.getByRole('button', { name: /start new chat/i });
    await user.click(startChatButton);
    
    await waitFor(() => {
      expect(mockOnError).toHaveBeenCalledWith('Creation failed');
    });
  });

  it('shows loading state when isLoading is true', () => {
    mockUseGremlinsAPI.isLoading = true;

    render(<ChatInterface />);
    
    // Check if loading spinner or loading state is displayed
    // This depends on your LoadingSpinner component implementation
    expect(document.querySelector('.loadingOverlay')).toBeInTheDocument();
  });

  it('toggles sidebar on mobile header button click', async () => {
    render(<ChatInterface />);
    
    const sidebarToggle = screen.getByRole('button', { name: /toggle conversation list/i });
    await user.click(sidebarToggle);
    
    // Check if sidebar has the open class
    const sidebar = document.querySelector('.sidebar');
    expect(sidebar).toHaveClass('sidebarOpen');
  });

  it('calls onConversationChange when conversation changes', async () => {
    const mockOnConversationChange = jest.fn();
    const mockConversation = {
      id: 'conv-1',
      title: 'Test Conversation',
      user_id: 'user-1',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      message_count: 2,
    };

    mockUseGremlinsAPI.createConversation = jest.fn().mockResolvedValue(mockConversation);

    render(<ChatInterface onConversationChange={mockOnConversationChange} />);
    
    const startChatButton = screen.getByRole('button', { name: /start new chat/i });
    await user.click(startChatButton);
    
    await waitFor(() => {
      expect(mockOnConversationChange).toHaveBeenCalledWith(mockConversation);
    });
  });

  it('handles keyboard navigation', async () => {
    render(<ChatInterface />);
    
    const sidebarToggle = screen.getByRole('button', { name: /toggle conversation list/i });
    
    // Test keyboard navigation
    sidebarToggle.focus();
    expect(sidebarToggle).toHaveFocus();
    
    await user.keyboard('{Enter}');
    
    // Check if sidebar opened
    const sidebar = document.querySelector('.sidebar');
    expect(sidebar).toHaveClass('sidebarOpen');
  });

  it('renders with custom className', () => {
    const { container } = render(<ChatInterface className="custom-class" />);
    
    expect(container.firstChild).toHaveClass('chatInterface', 'custom-class');
  });

  it('handles new conversation with custom title', async () => {
    const mockCreateConversation = jest.fn().mockResolvedValue({
      id: 'new-conv',
      title: 'Custom Title',
      user_id: 'user-1',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      message_count: 0,
    });

    mockUseGremlinsAPI.createConversation = mockCreateConversation;

    render(<ChatInterface />);
    
    // Find and fill the new conversation input
    const titleInput = screen.getByPlaceholderText('New conversation title...');
    await user.type(titleInput, 'Custom Title');
    
    const createButton = screen.getByRole('button', { name: /create/i });
    await user.click(createButton);
    
    expect(mockCreateConversation).toHaveBeenCalledWith('Custom Title');
  });
});
