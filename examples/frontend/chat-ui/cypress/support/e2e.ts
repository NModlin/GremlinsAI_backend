// ***********************************************************
// This example support/e2e.ts is processed and
// loaded automatically before your test files.
//
// This is a great place to put global configuration and
// behavior that modifies Cypress.
//
// You can change the location of this file or turn off
// automatically serving support files with the
// 'supportFile' configuration option.
//
// You can read more here:
// https://on.cypress.io/configuration
// ***********************************************************

// Import commands.js using ES2015 syntax:
import './commands';

// Alternatively you can use CommonJS syntax:
// require('./commands')

// Add custom commands
declare global {
  namespace Cypress {
    interface Chainable {
      /**
       * Custom command to select DOM element by data-testid attribute.
       * @example cy.getByTestId('greeting')
       */
      getByTestId(testId: string): Chainable<JQuery<HTMLElement>>;
      
      /**
       * Custom command to tab to next focusable element
       * @example cy.tab()
       */
      tab(): Chainable<JQuery<HTMLElement>>;
      
      /**
       * Custom command to wait for API request and verify response
       * @example cy.waitForAPI('@getConversations', 200)
       */
      waitForAPI(alias: string, expectedStatus?: number): Chainable<any>;
    }
  }
}

// Prevent Cypress from failing on uncaught exceptions
Cypress.on('uncaught:exception', (err, runnable) => {
  // Returning false here prevents Cypress from failing the test
  // on uncaught exceptions that might occur in the application
  if (err.message.includes('ResizeObserver loop limit exceeded')) {
    return false;
  }
  if (err.message.includes('Non-Error promise rejection captured')) {
    return false;
  }
  return true;
});

// Set up global test data
beforeEach(() => {
  // Clear localStorage and sessionStorage before each test
  cy.clearLocalStorage();
  cy.clearCookies();
  
  // Set up default viewport
  cy.viewport(1280, 720);
});

// Add accessibility testing
import 'cypress-axe';

// Configure axe-core
beforeEach(() => {
  cy.injectAxe();
});

// Add custom command for accessibility testing
Cypress.Commands.add('checkA11y', (context?: string, options?: any) => {
  cy.checkA11y(context, {
    ...options,
    rules: {
      // Disable color-contrast rule for now (can be enabled when design system is finalized)
      'color-contrast': { enabled: false },
      // Disable landmark rules for components that might not need them
      'region': { enabled: false },
      ...options?.rules,
    },
  });
});
