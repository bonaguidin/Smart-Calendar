import React, { createContext, useContext, useState, useEffect } from 'react';
import dayjs from 'dayjs';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';
import { useAuth } from './AuthContext';

dayjs.extend(timezone);
dayjs.extend(utc);

// Set default timezone to Chicago (adjust to user's timezone later)
dayjs.tz.setDefault('America/Chicago');


const CalendarContext = createContext();

export const CalendarProvider = ({ children }) => {
    const { token } = useAuth();
    const [tasks, setTasks] = useState({});
    const [currentDate, setCurrentDate] = useState(new Date());
    const [isCalendarExpanded, setIsCalendarExpanded] = useState(false);
    const [selectedTask, setSelectedTask] = useState(null);
    const [isUpdating, setIsUpdating] = useState(false);
    const [updateQueue, setUpdateQueue] = useState([]);

    // Add debug logging for state changes
    useEffect(() => {
        console.log('Calendar Context State:', {
            taskCount: Object.keys(tasks).reduce((acc, date) => acc + tasks[date].length, 0),
            currentDate,
            isCalendarExpanded,
            selectedTask
        });
    }, [tasks, currentDate, isCalendarExpanded, selectedTask]);

    // Helper function to parse server dates
    const parseServerDate = (dateStr) => {
        const [year, month, day] = dateStr.split('-').map(Number);
        return new Date(year, month - 1, day);
    };

    // Helper to format dates for API
    const formatDateForAPI = (date) => {
        return date.toISOString().split('T')[0];
    };

    // Load initial tasks from the server
    useEffect(() => {
        if (token) {
            const fetchTasks = async () => {
                try {
                    const response = await fetch('http://localhost:5000/api/tasks', {
                        headers: {
                            'Accept': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });

                    if (!response.ok) {
                        console.error('Failed to fetch tasks:', response.status);
                        return;
                    }

                    const data = await response.json();
                    if (data.tasks) {
                        console.log('Fetched tasks from server:', data.tasks);
                        // Transform tasks into our date-based format
                        const tasksByDate = {};
                        data.tasks.forEach(task => {
                            const start = new Date(task.start_date);
                            const end = new Date(task.end_date);
                            const totalDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
                            
                            let dayNumber = 1;
                            for (let date = new Date(start); date <= end; date.setDate(date.getDate() + 1)) {
                                const dateStr = date.toISOString().split('T')[0];
                                
                                if (!tasksByDate[dateStr]) {
                                    tasksByDate[dateStr] = [];
                                }
                                
                                tasksByDate[dateStr].push({
                                    ...task,
                                    instanceDate: dateStr,
                                    isPartOfMultiDay: totalDays > 1,
                                    dayNumber,
                                    totalDays,
                                    isFirstDay: dayNumber === 1,
                                    isLastDay: dayNumber === totalDays
                                });
                                
                                dayNumber++;
                            }
                        });
                        
                        setTasks(tasksByDate);
                    }
                } catch (error) {
                    console.error('Error fetching tasks:', error);
                }
            };

            fetchTasks();
        }
    }, [token]);

    const updateTaskByGroupId = async (groupId, updatedTaskData) => {
        console.log('Updating task with group ID:', groupId, updatedTaskData);
        
        try {
            const response = await fetch(`http://localhost:5000/api/tasks/${groupId}`, {
                method: 'PUT',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(updatedTaskData)
            });

            if (!response.ok) {
                console.error('Server error:', response.status);
                throw new Error(`Failed to update task: ${response.status}`);
            }

            const result = await response.json();
            
            // Update local state with new task instances
            setTasks(prev => {
                const newTasks = { ...prev };
                
                // Remove task from all dates
                Object.keys(newTasks).forEach(date => {
                    newTasks[date] = newTasks[date].filter(t => 
                        t.group_id !== groupId
                    );
                    if (newTasks[date].length === 0) {
                        delete newTasks[date];
                    }
                });
                
                // Add updated task to new dates
                result.dates.forEach(date => {
                    if (!newTasks[date]) {
                        newTasks[date] = [];
                    }
                    newTasks[date].push({
                        ...result.task,
                        instanceDate: date,
                        isPartOfMultiDay: result.dates.length > 1,
                        dayNumber: result.dates.indexOf(date) + 1,
                        totalDays: result.dates.length
                    });
                });
                
                return newTasks;
            });

            return result;
            
        } catch (error) {
            console.error('Error updating task:', error);
            throw error;
        }
    };

    // Update the existing updateTask function to use the new endpoint
    const updateTask = async (date, groupId, updatedTask) => {
        console.log('Updating task by group ID:', { groupId, updatedTask });
        
        try {
            // Helper function to format date strings
            const formatDateString = (dateStr) => {
                if (!dateStr) return null;
                // If the date includes time/timezone info, extract just the date part
                if (dateStr.includes('T')) {
                    return dateStr.split('T')[0];
                }
                return dateStr;
            };

            // Log the incoming dates for debugging
            console.log('Incoming dates:', {
                date,
                start: updatedTask.start_date,
                end: updatedTask.end_date
            });

            // Ensure the task data is properly formatted
            const taskData = {
                ...updatedTask,
                date: formatDateString(updatedTask.start_date),  // Use start_date as the primary date
                startDate: formatDateString(updatedTask.start_date),
                endDate: formatDateString(updatedTask.end_date),
                title: updatedTask.title || updatedTask.description,
                description: updatedTask.description || updatedTask.title,
                time: updatedTask.time || '',
                color: updatedTask.color || '#2196F3',
                group_id: groupId,
                is_multi_day: updatedTask.start_date !== updatedTask.end_date
            };

            // Log the formatted task data for debugging
            console.log('Formatted task data:', taskData);

            // Send update request to backend
            const response = await fetch(`http://localhost:5000/api/tasks/${groupId}`, {
                method: 'PUT',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(taskData)
            });

            if (!response.ok) {
                throw new Error(`Failed to update task: ${response.status}`);
            }

            const result = await response.json();
            console.log('Server response:', result);

            if (result.success) {
                // Update tasks state
                setTasks(prevTasks => {
                    const newTasks = { ...prevTasks };
                    
                    // Remove old task instances
                    Object.keys(newTasks).forEach(date => {
                        newTasks[date] = newTasks[date].filter(t => t.group_id !== groupId);
                    });
                    
                    // Add updated task instances
                    const dates = [];
                    const start = new Date(formatDateString(taskData.startDate));
                    const end = new Date(formatDateString(taskData.endDate));
                    
                    // Calculate total days for the task
                    const totalDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
                    
                    // Add task instances for each day in the range
                    for (let date = new Date(start); date <= end; date.setDate(date.getDate() + 1)) {
                        const dateStr = date.toISOString().split('T')[0];
                        dates.push(dateStr);
                        
                        if (!newTasks[dateStr]) {
                            newTasks[dateStr] = [];
                        }
                        
                        const dayNumber = dates.length;
                        
                        newTasks[dateStr].push({
                            ...taskData,
                            instanceDate: dateStr,
                            isPartOfMultiDay: totalDays > 1,
                            dayNumber,
                            totalDays,
                            // Add visual indicators for multi-day tasks
                            isFirstDay: dayNumber === 1,
                            isLastDay: dayNumber === totalDays,
                            displayTitle: dayNumber === 1 ? taskData.title : `${taskData.title} (Day ${dayNumber}/${totalDays})`
                        });
                    }
                    
                    return newTasks;
                });

                return result;
            } else {
                throw new Error('Failed to update task');
            }
        } catch (error) {
            console.error('Error updating task:', error);
            throw error;
        }
    };

    const addTask = async (task, isManualAdd = false) => {
        console.log('Adding task:', { task, isManualAdd });

        try {
            // Ensure we have a default date
            const today = new Date().toISOString().split('T')[0];
            
            // Log incoming task data
            console.log('Incoming task data:', task);
            
            // Determine the actual start and end dates
            const startDate = task.start_date || task.startDate || today;
            const endDate = task.end_date || task.endDate || startDate;
            
            // Format the task data to match backend expectations
            const taskData = {
                date: startDate,  // Use startDate as the primary date
                startDate: startDate,
                endDate: endDate,  // Don't fallback to startDate
                title: task.title || task.description,
                description: task.description || task.title,
                time: task.time || '',
                color: task.color || '#2196F3',
                recurrence: task.recurrence || null,
                recurrenceEnd: task.recurrence_end || task.recurrenceEnd || null,
                group_id: task.group_id || String(Date.now())
            };

            console.log('Task duration:', {
                start: taskData.startDate,
                end: taskData.endDate,
                isDurationTask: taskData.startDate !== taskData.endDate
            });

            // For manual adds, we don't need to confirm through the AI endpoint
            const endpoint = isManualAdd ? '/api/tasks' : '/api/confirm-task';
            
            const response = await fetch(`http://localhost:5000${endpoint}`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(taskData)
            });

            if (!response.ok) {
                throw new Error('Failed to add task');
            }

            const result = await response.json();
            console.log('Server response:', result);

            if (result.success) {
                // Generate dates array if not provided by backend
                const dates = [];
                const start = parseServerDate(taskData.startDate);
                const end = parseServerDate(taskData.endDate);
                
                for (let date = new Date(start); date <= end; date.setDate(date.getDate() + 1)) {
                    dates.push(date.toISOString().split('T')[0]);
                }
                
                // Update tasks state for each date in the duration
                setTasks(prevTasks => {
                    const newTasks = { ...prevTasks };
                    
                    // Add task instances for each date in the range
                    dates.forEach(date => {
                        if (!newTasks[date]) {
                            newTasks[date] = [];
                        }
                        newTasks[date].push({
                            ...taskData,
                            instanceDate: date,
                            isPartOfMultiDay: dates.length > 1,
                            dayNumber: dates.indexOf(date) + 1,
                            totalDays: dates.length
                        });
                    });

                    console.log('Updated tasks state:', newTasks);
                    return newTasks;
                });
            }

            return result;
        } catch (error) {
            console.error('Error adding task:', error);
            throw error;
        }
    };

    const deleteTask = async (groupId) => {
        console.log('Deleting task:', groupId);
        try {
            const response = await fetch(`http://localhost:5000/api/tasks/${groupId}`, {
                method: 'DELETE',
                headers: {
                    'Accept': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to delete task');
            }

            // Update local state
            setTasks(prev => {
                const updatedTasks = { ...prev };
                for (const date in updatedTasks) {
                    updatedTasks[date] = updatedTasks[date].filter(t => t.group_id !== groupId);
                    if (updatedTasks[date].length === 0) {
                        delete updatedTasks[date];
                    }
                }
                return updatedTasks;
            });

            return true;
        } catch (error) {
            console.error('Error deleting task:', error);
            throw error;
        }
    };

    // Add a helper function to get tasks for a specific date
    const getTasksForDate = (date) => {
        const dateStr = date.toISOString().split('T')[0];
        const tasksForDate = tasks[dateStr] || [];
        
        console.log('Getting tasks for date:', {
            date: dateStr,
            tasksFound: tasksForDate.length,
            tasks: tasksForDate
        });
        
        return tasksForDate;
    };

    const value = {
        tasks,
        currentDate,
        setCurrentDate,
        addTask,
        updateTask,
        updateTaskByGroupId,
        deleteTask,
        isCalendarExpanded,
        setIsCalendarExpanded,
        selectedTask,
        setSelectedTask,
        getTasksForDate
    };

    return (
        <CalendarContext.Provider value={value}>
            {children}
        </CalendarContext.Provider>
    );
};

export const useCalendar = () => useContext(CalendarContext);

export default CalendarContext; 