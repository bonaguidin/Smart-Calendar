import React, { useState, useEffect } from 'react';
import { useCalendar } from '../context/CalendarContext';
import '../styles/TaskEditor.css';  // Reuse the same styles

// Predefined color options matching our original design
const COLOR_OPTIONS = [
    { name: 'Blue', value: '#2196F3' },
    { name: 'Green', value: '#4CAF50' },
    { name: 'Purple', value: '#9C27B0' },
    { name: 'Orange', value: '#FF9800' },
    { name: 'Red', value: '#F44336' },
    { name: 'Teal', value: '#009688' },
    { name: 'Pink', value: '#E91E63' }
];

const TaskForm = ({ selectedDate, onClose }) => {
    const { addTask } = useCalendar();
    const [taskData, setTaskData] = useState({
        title: '',
        description: '',
        start_date: selectedDate,  // Changed to match LLM format
        end_date: selectedDate,    // Changed to match LLM format
        time: '',
        color: COLOR_OPTIONS[0].value,
        recurrence: null,          // Added to match LLM format
        recurrence_end: null       // Added to match LLM format
    });
    const [dateError, setDateError] = useState('');

    // Log when form is mounted with selected date
    useEffect(() => {
        console.log('TaskForm mounted with date:', selectedDate);
        setTaskData(prev => ({
            ...prev,
            start_date: selectedDate,
            end_date: selectedDate
        }));
    }, [selectedDate]);

    // Validate dates whenever they change
    useEffect(() => {
        if (taskData.start_date && taskData.end_date) {
            const start = new Date(taskData.start_date);
            const end = new Date(taskData.end_date);
            if (end < start) {
                setDateError('End date cannot be before start date');
            } else {
                setDateError('');
            }
        }
    }, [taskData.start_date, taskData.end_date]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        if (dateError) {
            alert(dateError);
            return;
        }
        
        console.log('Submitting task:', taskData);
        
        try {
            // Validate required fields
            if (!taskData.title) {
                throw new Error('Title is required');
            }
            if (!taskData.start_date) {
                throw new Error('Start date is required');
            }

            // Format task data to match both LLM and backend expectations
            const formattedTask = {
                description: taskData.title,
                start_date: taskData.start_date,
                end_date: taskData.end_date,
                time: taskData.time || '',
                color: taskData.color,
                recurrence: taskData.recurrence,
                recurrence_end: taskData.recurrence_end,
                // Add these fields for backend compatibility
                date: taskData.start_date,
                title: taskData.title
            };

            const result = await addTask(formattedTask, true);
            console.log('Task addition result:', result);
            onClose();
        } catch (error) {
            console.error('Failed to add task:', error);
            alert(`Failed to add task: ${error.message}`);
        }
    };

    return (
        <form onSubmit={handleSubmit} onClick={e => e.stopPropagation()} className="task-form">
            <h3>Add New Task</h3>
            
            <div className="form-group">
                <label>Title</label>
                <input
                    type="text"
                    value={taskData.title}
                    onChange={e => setTaskData(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="Enter task title"
                    required
                />
            </div>

            <div className="form-group">
                <label>Description</label>
                <textarea
                    value={taskData.description}
                    onChange={e => setTaskData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Add task details (optional)"
                />
            </div>

            <div className="form-row">
                <div className="form-group half-width">
                    <label>Start Date</label>
                    <input
                        type="date"
                        value={taskData.start_date}
                        onChange={e => setTaskData(prev => ({ 
                            ...prev, 
                            start_date: e.target.value,
                            // Update end date if it's before new start date
                            end_date: new Date(e.target.value) > new Date(prev.end_date) 
                                ? e.target.value 
                                : prev.end_date
                        }))}
                        required
                    />
                </div>

                <div className="form-group half-width">
                    <label>End Date</label>
                    <input
                        type="date"
                        value={taskData.end_date}
                        onChange={e => setTaskData(prev => ({ ...prev, end_date: e.target.value }))}
                        min={taskData.start_date}
                        required
                    />
                </div>
            </div>
            {dateError && <div className="error-message">{dateError}</div>}

            <div className="form-group">
                <label>Time</label>
                <input
                    type="time"
                    value={taskData.time}
                    onChange={e => setTaskData(prev => ({ ...prev, time: e.target.value }))}
                />
            </div>

            <div className="form-group">
                <label>Color</label>
                <div className="color-options">
                    {COLOR_OPTIONS.map(color => (
                        <button
                            key={color.value}
                            type="button"
                            className={`color-option ${taskData.color === color.value ? 'selected' : ''}`}
                            style={{ backgroundColor: color.value }}
                            onClick={() => setTaskData(prev => ({ ...prev, color: color.value }))}
                            title={color.name}
                        />
                    ))}
                </div>
            </div>

            <div className="form-buttons">
                <button type="submit" className="submit-button">Add Task</button>
                <button type="button" className="cancel-button" onClick={onClose}>Cancel</button>
            </div>
        </form>
    );
};

export default TaskForm; 