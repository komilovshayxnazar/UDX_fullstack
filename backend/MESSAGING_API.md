# Messaging API Documentation

## Overview

Complete messaging/chat API with support for:
- ✅ Listing all chats for a user
- ✅ Getting messages in a chat
- ✅ Sending messages
- ✅ Marking chats as read (reduces unread count)
- ✅ Creating new chats

## API Endpoints

### 1. Get All Chats
**GET** `/chats/`

**Auth**: Required

**Response**:
```json
[
  {
    "id": "chat-uuid",
    "other_user": {
      "id": "user-uuid",
      "name": "John Farmer",
      "avatar": "https://...",
      "role": "seller"
    },
    "last_message": "Hello, is this still available?",
    "last_message_time": "2024-02-10T14:30:00",
    "unread_count": 3,
    "product_id": "product-uuid"
  }
]
```

### 2. Get Chat Messages
**GET** `/chats/{chat_id}/messages`

**Auth**: Required

**Response**:
```json
[
  {
    "id": "message-uuid",
    "chat_id": "chat-uuid",
    "sender_id": "user-uuid",
    "text": "Hello!",
    "timestamp": "2024-02-10T14:30:00"
  }
]
```

### 3. Send Message
**POST** `/chats/{chat_id}/messages`

**Auth**: Required

**Body**:
```json
{
  "message_text": "Hello, is this still available?"
}
```

**Response**: Returns the created message object

**Side Effects**:
- Updates chat's `last_message` and `last_message_time`
- Increments `unread_count` for the other user

### 4. Mark Chat as Read ⭐
**POST** `/chats/{chat_id}/mark-read`

**Auth**: Required

**Response**:
```json
{
  "message": "Chat marked as read",
  "previous_unread_count": 3
}
```

**Effect**: Sets `unread_count` to 0 for this chat

### 5. Create Chat
**POST** `/chats/`

**Auth**: Required

**Body**:
```json
{
  "other_user_id": "user-uuid",
  "product_id": "product-uuid",  // optional
  "initial_message": "Hi, I'm interested in this product"  // optional
}
```

**Response**:
```json
{
  "chat_id": "chat-uuid",
  "existing": false  // true if chat already existed
}
```

## Frontend Integration

### Fixing the Navigation Issue

The browser test showed that clicking on chat threads logs `Open chat: 1` but doesn't navigate. You need to update your frontend routing:

```typescript
// In your Messages component
const handleChatClick = (chatId: string) => {
  console.log('Open chat:', chatId);
  
  // ADD THIS: Actually navigate to the chat
  navigate(`/messages/${chatId}`);
  // OR if using state management:
  setSelectedChatId(chatId);
  setView('chat-detail');
};
```

### Fetching Chats

```typescript
const fetchChats = async () => {
  const token = localStorage.getItem('auth_token');
  
  const response = await fetch('http://localhost:8000/chats/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const chats = await response.json();
  setChats(chats);
};
```

### Opening a Chat and Marking as Read

```typescript
const openChat = async (chatId: string) => {
  const token = localStorage.getItem('auth_token');
  
  // 1. Fetch messages
  const messagesResponse = await fetch(
    `http://localhost:8000/chats/${chatId}/messages`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  const messages = await messagesResponse.json();
  setMessages(messages);
  
  // 2. Mark as read (reduces unread count)
  await fetch(`http://localhost:8000/chats/${chatId}/mark-read`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  // 3. Update local state to reflect unread count = 0
  setChats(prevChats => 
    prevChats.map(chat => 
      chat.id === chatId 
        ? { ...chat, unread_count: 0 }
        : chat
    )
  );
  
  // 4. Navigate to chat view
  setSelectedChatId(chatId);
};
```

### Sending a Message

```typescript
const sendMessage = async (chatId: string, messageText: string) => {
  const token = localStorage.getItem('auth_token');
  
  const response = await fetch(
    `http://localhost:8000/chats/${chatId}/messages`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message_text: messageText })
    }
  );
  
  const newMessage = await response.json();
  
  // Add to messages list
  setMessages(prev => [...prev, newMessage]);
  
  // Clear input
  setMessageInput('');
};
```

### Complete Chat Component Example

```typescript
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

export const ChatDetail = () => {
  const { chatId } = useParams();
  const [messages, setMessages] = useState([]);
  const [messageInput, setMessageInput] = useState('');
  const [chat, setChat] = useState(null);
  
  useEffect(() => {
    if (chatId) {
      loadChat(chatId);
    }
  }, [chatId]);
  
  const loadChat = async (id: string) => {
    const token = localStorage.getItem('auth_token');
    
    // Get messages
    const messagesRes = await fetch(
      `http://localhost:8000/chats/${id}/messages`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const msgs = await messagesRes.json();
    setMessages(msgs);
    
    // Mark as read
    await fetch(`http://localhost:8000/chats/${id}/mark-read`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
  };
  
  const handleSend = async () => {
    if (!messageInput.trim()) return;
    
    const token = localStorage.getItem('auth_token');
    const res = await fetch(
      `http://localhost:8000/chats/${chatId}/messages`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message_text: messageInput })
      }
    );
    
    const newMsg = await res.json();
    setMessages(prev => [...prev, newMsg]);
    setMessageInput('');
  };
  
  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map(msg => (
          <div key={msg.id} className={msg.sender_id === currentUserId ? 'sent' : 'received'}>
            {msg.text}
          </div>
        ))}
      </div>
      
      <div className="input-area">
        <input
          value={messageInput}
          onChange={(e) => setMessageInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type a message..."
        />
        <button onClick={handleSend}>Send</button>
      </div>
    </div>
  );
};
```

## Unread Count Logic

### How it Works

1. **When a message is sent**:
   - If the sender is NOT the chat owner, `unread_count` is incremented
   - This ensures the chat owner sees the unread badge

2. **When a chat is opened**:
   - Call `POST /chats/{chat_id}/mark-read`
   - `unread_count` is reset to 0
   - Update your local state to reflect this

3. **In the chat list**:
   - Display `unread_count` as a badge
   - Only show for chats where `unread_count > 0`

### Example Unread Badge

```typescript
{chat.unread_count > 0 && (
  <span className="unread-badge">
    {chat.unread_count}
  </span>
)}
```

## Testing

### 1. Create a Test Chat
```bash
curl -X POST http://localhost:8000/chats/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "other_user_id": "user-uuid",
    "initial_message": "Hello!"
  }'
```

### 2. Get Chats
```bash
curl http://localhost:8000/chats/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Send a Message
```bash
curl -X POST http://localhost:8000/chats/CHAT_ID/messages \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message_text": "Test message"}'
```

### 4. Mark as Read
```bash
curl -X POST http://localhost:8000/chats/CHAT_ID/mark-read \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Summary

✅ **Backend API is complete** - All endpoints are working
⏳ **Frontend needs fixing** - Update navigation logic to actually change views when clicking chat threads
⏳ **Add mark-as-read call** - Call the endpoint when opening a chat to reduce unread count
