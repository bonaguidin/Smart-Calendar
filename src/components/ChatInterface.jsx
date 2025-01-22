import React, { useState, useRef, useEffect } from 'react';
import { useCalendar } from '../context/CalendarContext';
import '../styles/ChatInterface.css';

const ChatInterface = () => {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const messagesEndRef = useRef(null);
    const { addTask } = useCalendar();

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!inputValue.trim()) return;

        // Add user message
        const userMessage = {
            type: 'user',
            content: inputValue,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setInputValue('');

        try {
            // Send to backend for processing
            const response = await fetch('/api/parse-task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: inputValue })
            });

            const data = await response.json();

            // Add AI response
            const aiMessage = {
                type: 'assistant',
                content: formatAIResponse(data),
                timestamp: new Date(),
                suggestions: generateSuggestions(data)
            };

            setMessages(prev => [...prev, aiMessage]);
        } catch (error) {
            console.error('Error processing message:', error);
        }
    };

    return (
        <div className="chat-container">
            <div className="chat-messages">
                {messages.map((message, index) => (
                    <div key={index} className={`message ${message.type}`}>
                        <div className="message-content">{message.content}</div>
                        {message.suggestions && (
                            <div className="message-suggestions">
                                {message.suggestions.map((suggestion, i) => (
                                    <button 
                                        key={i} 
                                        onClick={() => handleSuggestionClick(suggestion)}
                                        className="suggestion-button"
                                    >
                                        {suggestion}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>
            <form onSubmit={handleSubmit} className="chat-input-form">
                <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Type your message here..."
                    className="chat-input"
                />
                <button type="submit" className="send-button">
                    <svg viewBox="0 0 24 24" className="send-icon">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                    </svg>
                </button>
            </form>
        </div>
    );
};

export default ChatInterface; 