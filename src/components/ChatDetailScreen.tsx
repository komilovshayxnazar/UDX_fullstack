import { useState, useEffect, useRef } from 'react';
import { ArrowLeft, Send, MoreVertical, Phone, Video } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { api } from '../api';
import { toast } from 'sonner';

interface Message {
    id: string;
    chat_id: string;
    sender_id: string;
    text: string;
    timestamp: string;
}

interface ChatDetailScreenProps {
    chatId: string;
    onBack: () => void;
}

export function ChatDetailScreen({ chatId, onBack }: ChatDetailScreenProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [newMessage, setNewMessage] = useState('');
    const [loading, setLoading] = useState(true);
    const [sending, setSending] = useState(false);
    const [chatInfo, setChatInfo] = useState<any>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const token = localStorage.getItem('token');

    // Scroll to bottom when messages change
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Load chat messages and mark as read
    useEffect(() => {
        const loadChat = async () => {
            if (!token) {
                toast.error('Please login to view messages');
                onBack();
                return;
            }

            try {
                setLoading(true);

                // Get messages
                const messagesData = await api.getChatMessages(chatId, token);
                setMessages(messagesData);

                // Mark chat as read (reduces unread count)
                await api.markChatAsRead(chatId, token);

                setLoading(false);
            } catch (error) {
                console.error('Failed to load chat:', error);
                toast.error('Failed to load messages');
                setLoading(false);
            }
        };

        loadChat();
    }, [chatId, token, onBack]);

    const handleSendMessage = async () => {
        if (!newMessage.trim() || !token) return;

        try {
            setSending(true);
            const message = await api.sendMessage(chatId, newMessage, token);
            setMessages(prev => [...prev, message]);
            setNewMessage('');
        } catch (error) {
            console.error('Failed to send message:', error);
            toast.error('Failed to send message');
        } finally {
            setSending(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    // Get current user ID from token (simplified - in production, decode JWT)
    const currentUserId = 'current-user-id'; // TODO: Get from decoded token

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="text-center">
                    <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto"></div>
                    <p className="text-gray-600">Loading messages...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex h-screen flex-col bg-gray-50">
            {/* Header */}
            <div className="sticky top-0 z-10 bg-white px-4 py-3 shadow-sm">
                <div className="flex items-center gap-3">
                    <button onClick={onBack} className="rounded-full p-2 hover:bg-gray-100">
                        <ArrowLeft className="h-5 w-5" />
                    </button>

                    <Avatar className="h-10 w-10">
                        <AvatarImage src={chatInfo?.avatar} />
                        <AvatarFallback>{chatInfo?.name?.substring(0, 2) || 'U'}</AvatarFallback>
                    </Avatar>

                    <div className="flex-1">
                        <h3 className="font-semibold">{chatInfo?.name || 'Chat'}</h3>
                        <p className="text-xs text-gray-500">Online</p>
                    </div>

                    <button className="rounded-full p-2 hover:bg-gray-100">
                        <Phone className="h-5 w-5" />
                    </button>
                    <button className="rounded-full p-2 hover:bg-gray-100">
                        <Video className="h-5 w-5" />
                    </button>
                    <button className="rounded-full p-2 hover:bg-gray-100">
                        <MoreVertical className="h-5 w-5" />
                    </button>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4">
                {messages.length === 0 ? (
                    <div className="flex h-full items-center justify-center">
                        <p className="text-gray-500">No messages yet. Start the conversation!</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {messages.map((message) => {
                            const isCurrentUser = message.sender_id === currentUserId;
                            return (
                                <div
                                    key={message.id}
                                    className={`flex ${isCurrentUser ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div
                                        className={`max-w-[70%] rounded-2xl px-4 py-2 ${isCurrentUser
                                                ? 'bg-primary text-primary-foreground'
                                                : 'bg-white text-gray-900'
                                            }`}
                                    >
                                        <p className="break-words">{message.text}</p>
                                        <p
                                            className={`mt-1 text-xs ${isCurrentUser ? 'text-primary-foreground/70' : 'text-gray-500'
                                                }`}
                                        >
                                            {new Date(message.timestamp).toLocaleTimeString([], {
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })}
                                        </p>
                                    </div>
                                </div>
                            );
                        })}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input */}
            <div className="border-t bg-white px-4 py-3">
                <div className="flex items-end gap-2">
                    <Input
                        placeholder="Type a message..."
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        className="flex-1"
                        disabled={sending}
                    />
                    <Button
                        onClick={handleSendMessage}
                        disabled={!newMessage.trim() || sending}
                        size="icon"
                        className="flex-shrink-0"
                    >
                        <Send className="h-5 w-5" />
                    </Button>
                </div>
            </div>
        </div>
    );
}
