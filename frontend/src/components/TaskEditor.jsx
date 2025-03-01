import React, { useState, useEffect } from 'react';
import { useCalendar } from '../context/CalendarContext';
import '../styles/TaskEditor.css';

// Use the same color options as TaskForm
const COLOR_OPTIONS = [
    { name: 'Blue', value: '#2196F3' },
    { name: 'Green', value: '#4CAF50' },
    { name: 'Purple', value: '#9C27B0' },
    { name: 'Orange', value: '#FF9800' },
    { name: 'Red', value: '#F44336' },
    { name: 'Teal', value: '#009688' },
    { name: 'Pink', value: '#E91E63' }
];

const TaskEditor = ({ task, onClose, selectedDate }) => {
    const { updateTask, deleteTask } = useCalendar();
    const [editedTask, setEditedTask] = useState({
        ...task,
        start_date: task.start_date || task.startDate || selectedDate,
        end_date: task.end_date || task.endDate || selectedDate
    });
    const [dateError, setDateError] = useState('');

    // Validate dates whenever they change
    useEffect(() => {
        if (editedTask.start_date && editedTask.end_date) {
            const start = new Date(editedTask.start_date);
            const end = new Date(editedTask.end_date);
            if (end < start) {
                setDateError('End date cannot be before start date');
            } else {
                setDateError('');
            }
        }
    }, [editedTask.start_date, editedTask.end_date]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        if (dateError) {
            alert(dateError);
            return;
        }
        
        try {
            const formattedTask = {
                description: editedTask.title,
                start_date: editedTask.start_date,
                end_date: editedTask.end_date,
                time: editedTask.time || '',
                color: editedTask.color,
                recurrence: editedTask.recurrence,
                recurrence_end: editedTask.recurrence_end,
                date: editedTask.start_date,
                title: editedTask.title
            };

            // Log the task data for debugging
            console.log('Submitting task:', formattedTask);

            await updateTask(editedTask.start_date, task.group_id, formattedTask);
            onClose();
        } catch (error) {
            console.error('Failed to update task:', error);
            alert(`Failed to update task: ${error.message}`);
        }
    };

    const handleDelete = async (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        if (window.confirm('Are you sure you want to delete this task?')) {
            try {
                await deleteTask(task.group_id);
                console.log('Task deleted successfully');
                onClose();
            } catch (error) {
                console.error('Failed to delete task:', error);
                alert(`Failed to delete task: ${error.message}`);
            }
        }
    };

    return (
        <form onSubmit={handleSubmit} onClick={e => e.stopPropagation()} className="task-form">
            <h3>Edit Task</h3>
            
            <div className="form-group">
                <label>Title</label>
                <input
                    type="text"
                    value={editedTask.title}
                    onChange={e => setEditedTask(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="Enter task title"
                    required
                />
            </div>

            <div className="form-group">
                <label>Description</label>
                <textarea
                    value={editedTask.description}
                    onChange={e => setEditedTask(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Add task details (optional)"
                />
            </div>

            <div className="form-row">
                <div className="form-group half-width">
                    <label>Start Date</label>
                    <input
                        type="date"
                        value={editedTask.start_date}
                        onChange={e => setEditedTask(prev => ({ 
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
                        value={editedTask.end_date}
                        onChange={e => setEditedTask(prev => ({ ...prev, end_date: e.target.value }))}
                        min={editedTask.start_date}
                        required
                    />
                </div>
            </div>
            {dateError && <div className="error-message">{dateError}</div>}

            <div className="form-group">
                <label>Time</label>
                <input
                    type="time"
                    value={editedTask.time}
                    onChange={e => setEditedTask(prev => ({ ...prev, time: e.target.value }))}
                />
            </div>

            <div className="form-group">
                <label>Color</label>
                <div className="color-options">
                    {COLOR_OPTIONS.map(color => (
                        <button
                            key={color.value}
                            type="button"
                            className={`color-option ${editedTask.color === color.value ? 'selected' : ''}`}
                            style={{ backgroundColor: color.value }}
                            onClick={() => setEditedTask(prev => ({ ...prev, color: color.value }))}
                            title={color.name}
                        />
                    ))}
                </div>
            </div>

            <div className="form-buttons">
                <button type="submit" className="submit-button">Save Changes</button>
                <button 
                    type="button" 
                    className="delete-button"
                    onClick={handleDelete}
                >
                    Delete Task
                </button>
                <button type="button" className="cancel-button" onClick={onClose}>Cancel</button>
            </div>
        </form>
    );
};

export default TaskEditor; 