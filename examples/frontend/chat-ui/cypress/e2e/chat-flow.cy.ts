describe('Chat Flow', () => {
  beforeEach(() => {
    // Mock API responses
    cy.intercept('GET', '/api/v1/history/conversations*', {
      statusCode: 200,
      body: {
        conversations: [
          {
            id: 'conv-1',
            title: 'Previous Chat',
            user_id: 'user-1',
            created_at: '2023-01-01T00:00:00Z',
            updated_at: '2023-01-01T00:00:00Z',
            message_count: 5,
          }
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }
    }).as('getConversations');

    cy.intercept('POST', '/api/v1/history/conversations', {
      statusCode: 200,
      body: {
        id: 'new-conv-id',
        title: 'New Chat',
        user_id: 'user-1',
        created_at: '2023-01-01T01:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        message_count: 0,
      }
    }).as('createConversation');

    cy.intercept('POST', '/api/v1/agent/chat', {
      statusCode: 200,
      body: {
        output: 'Hello! How can I help you today?',
        conversation_id: 'new-conv-id',
        context_used: false,
        execution_time: 0.5,
        metadata: {
          agent_used: true,
          context_used: false,
          execution_time: 0.5,
        }
      }
    }).as('sendMessage');

    cy.intercept('GET', '/api/v1/history/conversations/*/messages*', {
      statusCode: 200,
      body: {
        conversation_id: 'new-conv-id',
        messages: [
          {
            id: 'msg-1',
            conversation_id: 'new-conv-id',
            role: 'user',
            content: 'Hello AI',
            created_at: '2023-01-01T01:00:01Z',
          },
          {
            id: 'msg-2',
            conversation_id: 'new-conv-id',
            role: 'assistant',
            content: 'Hello! How can I help you today?',
            created_at: '2023-01-01T01:00:02Z',
          }
        ],
        total: 2,
        limit: 50,
        offset: 0,
      }
    }).as('getMessages');

    cy.visit('/');
  });

  it('completes full chat flow', () => {
    // Wait for initial load
    cy.wait('@getConversations');

    // Verify welcome screen is shown
    cy.get('[data-testid="welcome-screen"]').should('be.visible');
    cy.contains('Welcome to GremlinsAI').should('be.visible');

    // Start new conversation
    cy.get('[data-testid="start-chat-button"]').click();

    // Wait for conversation creation
    cy.wait('@createConversation');

    // Verify chat interface is now visible
    cy.get('[data-testid="chat-interface"]').should('be.visible');
    cy.get('[data-testid="message-input"]').should('be.visible');

    // Send a message
    cy.get('[data-testid="message-input"]').type('Hello AI');
    cy.get('[data-testid="send-button"]').click();

    // Wait for message to be sent
    cy.wait('@sendMessage');

    // Verify message appears in the chat
    cy.get('[data-testid="message-list"]').should('contain', 'Hello AI');
    cy.get('[data-testid="message-list"]').should('contain', 'Hello! How can I help you today?');

    // Verify conversation appears in sidebar
    cy.get('[data-testid="conversation-sidebar"]').should('contain', 'New Chat');
  });

  it('handles API errors gracefully', () => {
    // Mock error response
    cy.intercept('POST', '/api/v1/agent/chat', {
      statusCode: 500,
      body: {
        error_code: 'GREMLINS_2001',
        error_message: 'Agent processing failed',
        severity: 'HIGH',
      }
    }).as('sendMessageError');

    // Start new conversation
    cy.get('[data-testid="start-chat-button"]').click();
    cy.wait('@createConversation');

    // Send message that will fail
    cy.get('[data-testid="message-input"]').type('Test message');
    cy.get('[data-testid="send-button"]').click();

    cy.wait('@sendMessageError');

    // Verify error message is displayed
    cy.get('[data-testid="error-banner"]').should('be.visible');
    cy.get('[data-testid="error-message"]').should('contain', 'Agent processing failed');

    // Verify error can be dismissed
    cy.get('[data-testid="error-dismiss"]').click();
    cy.get('[data-testid="error-banner"]').should('not.exist');
  });

  it('supports keyboard navigation', () => {
    // Start new conversation
    cy.get('[data-testid="start-chat-button"]').click();
    cy.wait('@createConversation');

    // Test tab navigation
    cy.get('body').tab();
    cy.focused().should('have.attr', 'data-testid', 'sidebar-toggle');

    cy.focused().tab();
    cy.focused().should('have.attr', 'data-testid', 'message-input');

    cy.focused().tab();
    cy.focused().should('have.attr', 'data-testid', 'send-button');

    // Test Enter key to send message
    cy.get('[data-testid="message-input"]').focus().type('Hello{enter}');
    cy.wait('@sendMessage');

    cy.get('[data-testid="message-list"]').should('contain', 'Hello');
  });

  it('handles long conversations with scrolling', () => {
    // Mock a conversation with many messages
    const manyMessages = Array.from({ length: 50 }, (_, i) => ({
      id: `msg-${i}`,
      conversation_id: 'conv-1',
      role: i % 2 === 0 ? 'user' : 'assistant',
      content: `Message ${i + 1}`,
      created_at: new Date(Date.now() + i * 1000).toISOString(),
    }));

    cy.intercept('GET', '/api/v1/history/conversations/conv-1/messages*', {
      statusCode: 200,
      body: {
        conversation_id: 'conv-1',
        messages: manyMessages,
        total: 50,
        limit: 50,
        offset: 0,
      }
    }).as('getManyMessages');

    // Select existing conversation
    cy.get('[data-testid="conversation-item"]').first().click();
    cy.wait('@getManyMessages');

    // Verify messages are loaded
    cy.get('[data-testid="message-list"]').should('contain', 'Message 1');
    cy.get('[data-testid="message-list"]').should('contain', 'Message 50');

    // Verify auto-scroll to bottom
    cy.get('[data-testid="message-list"]').should('be.scrolledTo', 'bottom');

    // Send new message and verify it scrolls to bottom
    cy.get('[data-testid="message-input"]').type('New message');
    cy.get('[data-testid="send-button"]').click();
    cy.wait('@sendMessage');

    cy.get('[data-testid="message-list"]').should('be.scrolledTo', 'bottom');
  });

  it('works on mobile viewport', () => {
    cy.viewport('iphone-x');

    // Verify mobile layout
    cy.get('[data-testid="mobile-header"]').should('be.visible');
    cy.get('[data-testid="sidebar"]').should('not.be.visible');

    // Toggle sidebar
    cy.get('[data-testid="sidebar-toggle"]').click();
    cy.get('[data-testid="sidebar"]').should('be.visible');

    // Start new conversation
    cy.get('[data-testid="start-chat-button"]').click();
    cy.wait('@createConversation');

    // Sidebar should close after starting conversation
    cy.get('[data-testid="sidebar"]').should('not.be.visible');

    // Verify message input is accessible
    cy.get('[data-testid="message-input"]').should('be.visible');
    cy.get('[data-testid="send-button"]').should('be.visible');

    // Send message
    cy.get('[data-testid="message-input"]').type('Mobile test');
    cy.get('[data-testid="send-button"]').click();
    cy.wait('@sendMessage');

    cy.get('[data-testid="message-list"]').should('contain', 'Mobile test');
  });

  it('handles network connectivity issues', () => {
    // Start new conversation
    cy.get('[data-testid="start-chat-button"]').click();
    cy.wait('@createConversation');

    // Simulate network failure
    cy.intercept('POST', '/api/v1/agent/chat', { forceNetworkError: true }).as('networkError');

    cy.get('[data-testid="message-input"]').type('Test message');
    cy.get('[data-testid="send-button"]').click();

    cy.wait('@networkError');

    // Verify network error is handled
    cy.get('[data-testid="error-banner"]').should('be.visible');
    cy.get('[data-testid="error-message"]').should('contain', 'Network error');

    // Verify retry functionality
    cy.intercept('POST', '/api/v1/agent/chat', {
      statusCode: 200,
      body: {
        output: 'Message sent successfully',
        conversation_id: 'new-conv-id',
      }
    }).as('retrySuccess');

    cy.get('[data-testid="retry-button"]').click();
    cy.wait('@retrySuccess');

    cy.get('[data-testid="message-list"]').should('contain', 'Message sent successfully');
    cy.get('[data-testid="error-banner"]').should('not.exist');
  });
});
