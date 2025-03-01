import React, { useState, useRef, useEffect } from 'react';
import { useCalendar } from '../context/CalendarContext';
import '../styles/ChatInterface.css';

// Color mapping constants
const COLOR_MAP = {
    '#2196F3': 'Blue',
    '#4CAF50': 'Green',
    '#9C27B0': 'Purple',
    '#FF9800': 'Orange',
    '#F44336': 'Red',
    '#009688': 'Teal',
    '#E91E63': 'Pink'
};

const REVERSE_COLOR_MAP = {
    'blue': '#2196F3',
    'green': '#4CAF50',
    'purple': '#9C27B0',
    'orange': '#FF9800',
    'red': '#F44336',
    'teal': '#009688',
    'pink': '#E91E63'
};

const ChatInterface = () => {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [pendingTask, setPendingTask] = useState(null);
    const [pendingEdit, setPendingEdit] = useState(null);
    const messagesEndRef = useRef(null);
    const { addTask, updateTask, setIsCalendarExpanded, deleteTask } = useCalendar();

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Add helper function to get color name
    const getColorName = (hexCode) => {
        return COLOR_MAP[hexCode] || hexCode;
    };

    // Add helper function to format color in message
    const formatColorInText = (text) => {
        return text.replace(/(#[0-9A-F]{6})/gi, (match) => getColorName(match));
    };

    const formatAIResponse = (data) => {
        if (data.error) return `Sorry, I couldn't process that. ${data.error}`;
        
        // Handle conversational responses
        if (data.is_conversational) {
            return data.ai_message;
        }
        
        if (data.ai_message) {
            return formatColorInText(data.ai_message);
        }
        
        // Fallback to default formatting if no AI message
        const startDate = data.start_date || data.startDate;
        if (!startDate) {
            return `I've scheduled "${data.description}". Would you like to add more details?`;
        }

        const [year, month, day] = startDate.split('-').map(Number);
        const date = new Date(year, month - 1, day);
        
        const formattedDate = date.toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });

        // Log the dates for debugging
        console.log('Original startDate:', startDate);
        console.log('Parsed date object:', date);
        console.log('Formatted date string:', formattedDate);

        return `I've scheduled "${data.description}" for ${formattedDate}. Would you like me to: 1. Add more details to this task 2. Set up a reminder 3. Make it a recurring event`;
    };

    const generateSuggestions = (data) => {
        // Use dynamic suggestions if available
        if (data.suggestions && Array.isArray(data.suggestions)) {
            return data.suggestions;
        }

        // Fallback to default suggestions
        const suggestions = [
            "Add more details",
            "Set a reminder",
            "Make it recurring"
        ];

        if (data.recurrence) {
            suggestions.push("Change recurrence pattern");
        }

        return suggestions;
    };

    const handleSuggestionClick = (suggestion) => {
        switch (suggestion) {
            case "Add more details":
                setInputValue("Add more details to the task");
                break;
            case "Set a reminder":
                setInputValue("Set a reminder for this task");
                break;
            case "Make it recurring":
                setInputValue("Make this task recurring");
                break;
            default:
                setInputValue(suggestion);
        }
    };

    const handleTaskConfirmation = async () => {
        if (!pendingTask) return;

        try {
            // Ensure we have a start date, default to today if not provided
            const today = new Date().toISOString().split('T')[0];
            const formattedTask = {
                ...pendingTask,
                start_date: pendingTask.startDate || today,
                end_date: pendingTask.endDate || pendingTask.startDate || today,
                date: pendingTask.startDate || today,  // Add this for backend compatibility
                // Ensure all required fields are present
                title: pendingTask.title || pendingTask.description,
                description: pendingTask.description || pendingTask.title,
                time: pendingTask.time || '',
                color: pendingTask.color || '#2196F3'
            };

            console.log('Confirming task with data:', formattedTask);
            
            // Add task to calendar
            await addTask(formattedTask, false);
            
            // Add confirmation message
            setMessages(prev => [...prev, {
                type: 'assistant',
                content: `✅ Task "${formattedTask.title}" has been added to your calendar!`,
                timestamp: new Date()
            }]);

            // Expand calendar and highlight new task
            setIsCalendarExpanded(true);
            setPendingTask(null);

        } catch (error) {
            console.error('Error in task confirmation:', error);
            setMessages(prev => [...prev, {
                type: 'assistant',
                content: `Failed to confirm task: ${error.message}. Please try again.`,
                timestamp: new Date()
            }]);
        }
    };

    const handleEditRequest = async (editData) => {
        try {
            // First, get the matched task from the initial response
            const matchedTask = editData.matched_tasks?.[0];
            if (!matchedTask) {
                throw new Error('No matching task found');
            }

            // Check if this is a delete request
            const deleteKeywords = ['delete', 'remove', 'get rid of', 'erase'];
            const isDeleteRequest = deleteKeywords.some(keyword => 
                editData.original_input.toLowerCase().includes(keyword)
            );

            if (isDeleteRequest) {
                // Add confirmation message for deletion
                const aiMessage = {
                    type: 'assistant',
                    content: `Are you sure you want to delete "${matchedTask.title}"?`,
                    timestamp: new Date(),
                    confirmButton: true,
                    confirmationType: 'delete',
                    taskToEdit: matchedTask
                };
                setMessages(prev => [...prev, aiMessage]);
                setPendingEdit({
                    task_to_edit: matchedTask,
                    is_delete: true
                });
                return;
            }

            // Store the task information for the edit
            const editContext = {
                task: matchedTask,
                date: editData.task_date,
                original_input: editData.original_input
            };

            // Send edit request to backend
            const response = await fetch('http://localhost:5000/api/tasks/edit', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ 
                    query: editData.original_input,
                    task_id: matchedTask.group_id
                })
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const result = await response.json();
            console.log('Edit response:', result);

            if (result.error) {
                throw new Error(result.error);
            }

            // Store both the edit instructions and the task to be edited
            setPendingEdit({
                ...result,
                task_to_edit: matchedTask,
                original_input: editData.original_input,
                matched_tasks: editData.matched_tasks // Store the matched tasks array
            });

            // Format the changes for display
            const changeDescriptions = result.changes.map(change => {
                const fieldMap = {
                    'dates': 'date',
                    'startDate': 'start date',
                    'endDate': 'end date',
                    'color': 'color'
                };
                const fieldName = fieldMap[change.field] || change.field;
                let value = change.value;
                
                // Format color values to show color names
                if (change.field === 'color') {
                    value = getColorName(change.value);
                }
                
                return `- ${fieldName}: ${value}`;
            });

            // Add AI response for edit confirmation with confirm button
            const aiMessage = {
                type: 'assistant',
                content: `I'll help you edit "${matchedTask.title}". Here's what I'm going to change:\n${changeDescriptions.join('\n')}\n\nWould you like me to apply these changes?`,
                timestamp: new Date(),
                editDetails: result,
                confirmButton: true,
                confirmationType: 'edit',
                taskToEdit: matchedTask
            };

            setMessages(prev => [...prev, aiMessage]);
        } catch (error) {
            console.error('Error processing edit:', error);
            setMessages(prev => [...prev, {
                type: 'assistant',
                content: `Error: ${error.message}. Please try again or rephrase your request.`,
                timestamp: new Date()
            }]);
        }
    };

    const handleEditConfirmation = async () => {
        if (!pendingEdit || !pendingEdit.task_to_edit) {
            console.error('Missing edit data or selected task');
            setMessages(prev => [...prev, {
                type: 'assistant',
                content: 'Sorry, I lost track of the edit details. Please try again.',
                timestamp: new Date()
            }]);
            setPendingEdit(null);
            return;
        }

        try {
            const taskToEdit = pendingEdit.task_to_edit;

            // Handle deletion request
            if (pendingEdit.is_delete) {
                await deleteTask(taskToEdit.group_id);
                setMessages(prev => [...prev, {
                    type: 'assistant',
                    content: `✅ Task "${taskToEdit.title}" has been deleted.`,
                    timestamp: new Date()
                }]);
                setPendingEdit(null);
                setIsCalendarExpanded(true);
                return;
            }

            // Handle regular edit request
            console.log('Updating task:', taskToEdit.group_id);
            console.log('Update data:', pendingEdit);

            // Helper function to format date strings
            const formatDateString = (dateStr) => {
                if (!dateStr) return null;
                // If the date includes time/timezone info, extract just the date part
                if (dateStr.includes('T')) {
                    return dateStr.split('T')[0];
                }
                return dateStr;
            };

            // Apply the changes from the edit response
            const updatedTask = {
                ...taskToEdit,
                ...pendingEdit.changes.reduce((acc, change) => {
                    if (change.field === 'dates') {
                        // If setting a single date, update both start and end
                        acc.start_date = formatDateString(change.value);
                        acc.end_date = formatDateString(change.value);
                    } else if (change.field === 'startDate') {
                        // Update start date while preserving duration if end date exists
                        acc.start_date = formatDateString(change.value);
                        if (taskToEdit.end_date) {
                            const startDate = new Date(formatDateString(change.value));
                            const endDate = new Date(formatDateString(taskToEdit.end_date));
                            if (startDate > endDate) {
                                acc.end_date = formatDateString(change.value);
                            }
                        }
                    } else if (change.field === 'endDate') {
                        // Update end date while preserving start date
                        acc.end_date = formatDateString(change.value);
                        // Ensure we preserve the original start date
                        acc.start_date = formatDateString(taskToEdit.start_date || taskToEdit.startDate);
                    } else {
                        acc[change.field] = change.value;
                    }
                    return acc;
                }, {})
            };

            // Log the date changes for debugging
            console.log('Original task dates:', {
                start: taskToEdit.start_date || taskToEdit.startDate,
                end: taskToEdit.end_date || taskToEdit.endDate
            });
            console.log('Updated task dates:', {
                start: updatedTask.start_date,
                end: updatedTask.end_date
            });

            // Ensure all required fields are present with consistent naming
            const formattedTask = {
                ...updatedTask,
                start_date: formatDateString(updatedTask.start_date || updatedTask.startDate),
                end_date: formatDateString(updatedTask.end_date || updatedTask.endDate),
                title: updatedTask.title || updatedTask.description,
                description: updatedTask.description || updatedTask.title,
                time: updatedTask.time || '',
                color: updatedTask.color || '#2196F3',
                group_id: taskToEdit.group_id
            };

            // Update task through CalendarContext with the correct parameters
            await updateTask(formattedTask.start_date, formattedTask.group_id, formattedTask);

            // Add success message
            setMessages(prev => [...prev, {
                type: 'assistant',
                content: `✅ Task "${formattedTask.title}" has been updated!`,
                timestamp: new Date()
            }]);

            // Clear pending edit
            setPendingEdit(null);

            // Expand calendar to show changes
            setIsCalendarExpanded(true);

        } catch (error) {
            console.error('Error updating task:', error);
            setMessages(prev => [...prev, {
                type: 'assistant',
                content: `Failed to update task: ${error.message}. Please try again.`,
                timestamp: new Date()
            }]);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!inputValue.trim()) return;

        const userMessage = {
            type: 'user',
            content: inputValue,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setInputValue('');

        try {
            const response = await fetch('http://localhost:5000/api/parse-task', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ 
                    input: inputValue
                })
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            console.log('Parsed response:', data);
            
            // Handle conversational responses
            if (data.is_conversational) {
                setMessages(prev => [...prev, {
                    type: 'assistant',
                    content: formatAIResponse(data),
                    timestamp: new Date()
                }]);
                return;
            }

            // Check if this is an edit request
            if (data.is_edit_request) {
                await handleEditRequest(data);
                return;
            }

            // Store the pending task
            setPendingTask(data);

            const aiMessage = {
                type: 'assistant',
                content: formatAIResponse(data),
                timestamp: new Date(),
                taskDetails: data,
                confirmButton: true,
                confirmationType: 'add',
                suggestions: generateSuggestions(data),
                followUpQuestions: data.follow_up_questions
            };

            setMessages(prev => [...prev, aiMessage]);
        } catch (error) {
            console.error('Error processing message:', error);
            setMessages(prev => [...prev, {
                type: 'assistant',
                content: `Error: ${error.message}. Please try again or rephrase your request.`,
                timestamp: new Date()
            }]);
        }
    };

    return (
        <div className="chat-container">
            <div className="chat-messages">
                {messages.map((message, index) => (
                    <div key={index} className={`message ${message.type}`}>
                        <div className="message-content">{message.content}</div>
                        {message.taskDetails && (
                            <div className="task-preview">
                                <div className="task-details">
                                    <div className="task-title">
                                        {message.taskDetails.description || message.taskDetails.title || 'Untitled Task'}
                                    </div>
                                    <div className="task-date">
                                        {(() => {
                                            const startDate = message.taskDetails.start_date || message.taskDetails.startDate;
                                            if (!startDate) return 'Date not set';
                                            
                                            try {
                                                const [year, month, day] = startDate.split('-').map(Number);
                                                const date = new Date(year, month - 1, day);
                                                return date.toLocaleDateString('en-US', {
                                                    year: 'numeric',
                                                    month: 'numeric',
                                                    day: 'numeric'
                                                });
                                            } catch (error) {
                                                console.error('Error formatting date:', error);
                                                return 'Invalid date';
                                            }
                                        })()}
                                    </div>
                                </div>
                                {message.confirmButton && message.confirmationType === 'add' && (
                                    <button 
                                        className="confirm-button"
                                        onClick={handleTaskConfirmation}
                                    >
                                        Confirm Task
                                    </button>
                                )}
                            </div>
                        )}
                        {message.confirmButton && (message.confirmationType === 'edit' || message.confirmationType === 'delete') && message.taskToEdit && (
                            <div className="task-preview">
                                <div className="task-details">
                                    <div className="task-title">
                                        {message.taskToEdit.title || 'Untitled Task'}
                                    </div>
                                </div>
                                <button 
                                    className={`confirm-button ${message.confirmationType === 'delete' ? 'delete-confirm' : 'edit-confirm'}`}
                                    onClick={handleEditConfirmation}
                                >
                                    {message.confirmationType === 'delete' ? 'Confirm Delete' : 'Confirm Edit'}
                                </button>
                            </div>
                        )}
                        {message.followUpQuestions && (
                            <div className="follow-up-questions">
                                {message.followUpQuestions.map((question, i) => (
                                    <div key={i} className="follow-up-question" onClick={() => setInputValue(question)}>
                                        {question}
                                    </div>
                                ))}
                            </div>
                        )}
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