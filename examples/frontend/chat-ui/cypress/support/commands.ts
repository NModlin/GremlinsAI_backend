/// <reference types="cypress" />

// Custom command to select elements by data-testid
Cypress.Commands.add('getByTestId', (testId: string) => {
  return cy.get(`[data-testid="${testId}"]`);
});

// Custom command for keyboard navigation
Cypress.Commands.add('tab', { prevSubject: 'optional' }, (subject) => {
  if (subject) {
    return cy.wrap(subject).trigger('keydown', { key: 'Tab' });
  } else {
    return cy.focused().trigger('keydown', { key: 'Tab' });
  }
});

// Custom command to wait for API calls and verify status
Cypress.Commands.add('waitForAPI', (alias: string, expectedStatus = 200) => {
  return cy.wait(alias).then((interception) => {
    expect(interception.response?.statusCode).to.equal(expectedStatus);
    return cy.wrap(interception);
  });
});

// Custom command to mock successful API responses
Cypress.Commands.add('mockAPISuccess', () => {
  // Mock all common API endpoints with success responses
  cy.intercept('GET', '/api/v1/history/conversations*', {
    statusCode: 200,
    body: {
      conversations: [],
      total: 0,
      limit: 20,
      offset: 0,
    }
  }).as('getConversations');

  cy.intercept('POST', '/api/v1/history/conversations', {
    statusCode: 200,
    body: {
      id: 'test-conv-id',
      title: 'Test Conversation',
      user_id: 'test-user',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      message_count: 0,
    }
  }).as('createConversation');

  cy.intercept('POST', '/api/v1/agent/chat', {
    statusCode: 200,
    body: {
      output: 'Test response from AI',
      conversation_id: 'test-conv-id',
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
      conversation_id: 'test-conv-id',
      messages: [],
      total: 0,
      limit: 50,
      offset: 0,
    }
  }).as('getMessages');
});

// Custom command to simulate typing with realistic delays
Cypress.Commands.add('typeRealistic', { prevSubject: true }, (subject, text, options = {}) => {
  const defaultOptions = {
    delay: 50, // milliseconds between keystrokes
    ...options,
  };
  
  return cy.wrap(subject).type(text, defaultOptions);
});

// Custom command to wait for element to be stable (not moving/changing)
Cypress.Commands.add('waitForStable', { prevSubject: true }, (subject, timeout = 1000) => {
  let previousPosition: { top: number; left: number } | null = null;
  let stableCount = 0;
  const requiredStableChecks = 3;
  
  return cy.wrap(subject).should(($el) => {
    const rect = $el[0].getBoundingClientRect();
    const currentPosition = { top: rect.top, left: rect.left };
    
    if (previousPosition && 
        Math.abs(currentPosition.top - previousPosition.top) < 1 &&
        Math.abs(currentPosition.left - previousPosition.left) < 1) {
      stableCount++;
    } else {
      stableCount = 0;
    }
    
    previousPosition = currentPosition;
    
    if (stableCount < requiredStableChecks) {
      throw new Error('Element is still moving');
    }
  });
});

// Custom command to check if element is in viewport
Cypress.Commands.add('isInViewport', { prevSubject: true }, (subject) => {
  return cy.wrap(subject).should(($el) => {
    const rect = $el[0].getBoundingClientRect();
    const windowHeight = Cypress.config('viewportHeight');
    const windowWidth = Cypress.config('viewportWidth');
    
    expect(rect.top).to.be.at.least(0);
    expect(rect.left).to.be.at.least(0);
    expect(rect.bottom).to.be.at.most(windowHeight);
    expect(rect.right).to.be.at.most(windowWidth);
  });
});

// Custom command to simulate mobile device
Cypress.Commands.add('setMobileViewport', () => {
  cy.viewport('iphone-x');
});

// Custom command to simulate tablet device
Cypress.Commands.add('setTabletViewport', () => {
  cy.viewport('ipad-2');
});

// Custom command to simulate desktop device
Cypress.Commands.add('setDesktopViewport', () => {
  cy.viewport(1280, 720);
});

// Extend Cypress namespace with custom commands
declare global {
  namespace Cypress {
    interface Chainable {
      getByTestId(testId: string): Chainable<JQuery<HTMLElement>>;
      tab(): Chainable<JQuery<HTMLElement>>;
      waitForAPI(alias: string, expectedStatus?: number): Chainable<any>;
      mockAPISuccess(): Chainable<void>;
      typeRealistic(text: string, options?: Partial<Cypress.TypeOptions>): Chainable<JQuery<HTMLElement>>;
      waitForStable(timeout?: number): Chainable<JQuery<HTMLElement>>;
      isInViewport(): Chainable<JQuery<HTMLElement>>;
      setMobileViewport(): Chainable<void>;
      setTabletViewport(): Chainable<void>;
      setDesktopViewport(): Chainable<void>;
      checkA11y(context?: string, options?: any): Chainable<void>;
    }
  }
}
