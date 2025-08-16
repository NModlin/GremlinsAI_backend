import React from 'react';
import { ChatInterface } from './components/ChatInterface/ChatInterface';
import { ConversationResponse, MessageResponse } from './services/types';
import './App.css';

function App() {
  const handleConversationChange = (conversation: ConversationResponse | null) => {
    console.log('Conversation changed:', conversation);
    
    // Update document title
    if (conversation) {
      document.title = `${conversation.title} - GremlinsAI Chat`;
    } else {
      document.title = 'GremlinsAI Chat';
    }
  };

  const handleMessageSent = (message: MessageResponse) => {
    console.log('Message sent:', message);
    
    // Could be used for analytics, notifications, etc.
  };

  const handleError = (error: string) => {
    console.error('Chat error:', error);
    
    // Could be used for error reporting, user notifications, etc.
  };

  return (
    <div className="App">
      <ChatInterface
        onConversationChange={handleConversationChange}
        onMessageSent={handleMessageSent}
        onError={handleError}
      />
    </div>
  );
}

export default App;
