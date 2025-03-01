import React, { useEffect, useState } from 'react';
import { useCalendar } from '../context/CalendarContext';
import '../styles/MinimizedCalendar.css';
import TaskForm from './TaskForm';
import TaskEditor from './TaskEditor';

const MinimizedCalendar = () => {
    const { tasks, currentDate, setCurrentDate, isCalendarExpanded, setIsCalendarExpanded } = useCalendar();
    const [selectedDate, setSelectedDate] = useState(null);
    const [showTaskForm, setShowTaskForm] = useState(false);
    const [selectedTask, setSelectedTask] = useState(null);
    const [showTaskEditor, setShowTaskEditor] = useState(false);

    // Add debug logging
    useEffect(() => {
        console.log('Calendar State:', {
            isExpanded: isCalendarExpanded,
            selectedDate,
            currentDate,
            availableTasks: tasks
        });
    }, [isCalendarExpanded, selectedDate, currentDate, tasks]);

    const handleDateClick = (e, date) => {
        e.stopPropagation(); // Prevent calendar from collapsing
        console.log('Date clicked:', date);
        setSelectedDate(date);
        setShowTaskForm(true);
    };

    const toggleCalendar = (e) => {
        console.log('Calendar toggle called. Current state:', isCalendarExpanded);
        setIsCalendarExpanded(!isCalendarExpanded);
    };

    // Helper function to get days in month
    const getDaysInMonth = (date) => {
        return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
    };

    // Helper function to get day of week (0-6) for first day of month
    const getFirstDayOfMonth = (date) => {
        return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
    };

    // Handler for clicking on a task card
    const handleTaskClick = (e, task) => {
        e.stopPropagation();
        e.preventDefault(); // Add this
        setSelectedTask(task);
        setShowTaskForm(false); // Explicitly close form
        setShowTaskEditor(true);
    };
    
    // Add to your useEffect
    useEffect(() => {
        if (showTaskEditor) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'auto';
        }
    }, [showTaskEditor]);

    // Add month navigation handlers
    const handlePreviousMonth = (e) => {
        e.stopPropagation();
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
    };

    const handleNextMonth = (e) => {
        e.stopPropagation();
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
    };

    // Add click outside handler
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (isCalendarExpanded && !event.target.closest('.calendar-container')) {
                setIsCalendarExpanded(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isCalendarExpanded, setIsCalendarExpanded]);

    const renderCalendarGrid = () => {
        const daysInMonth = getDaysInMonth(currentDate);
        const firstDayOfMonth = getFirstDayOfMonth(currentDate);
        const weeks = [];
        let days = [];

        // Add empty cells for days before the first of the month
        for (let i = 0; i < firstDayOfMonth; i++) {
            days.push(<div key={`empty-${i}`} className="calendar-day empty"></div>);
        }

        // Add cells for each day of the month
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const dayTasks = tasks[dateStr] || [];
            
            days.push(
                <div 
                    key={day} 
                    className={`calendar-day ${dayTasks.length > 0 ? 'has-task' : ''}`}
                    onClick={(e) => handleDateClick(e, dateStr)}
                >
                    <span className="day-number">{day}</span>
                    <div className="task-cards">
                        {/* Render each task as a card */}
                        {dayTasks.map((task, index) => (
                            <div
                                key={task.group_id}
                                className="task-card"
                                style={{
                                    // Set background color with 0.8 alpha
                                    backgroundColor: `${task.color}CC`,
                                    // Slightly offset each card
                                    marginTop: `${index * 2}px`
                                }}
                                onClick={(e) => handleTaskClick(e, task)}
                            >
                                {task.title}
                            </div>
                        ))}
                    </div>
                </div>
            );

            // Start new week after Saturday (6)
            if ((firstDayOfMonth + day) % 7 === 0) {
                weeks.push(<div key={weeks.length} className="calendar-week">{days}</div>);
                days = [];
            }
        }

        // Add remaining days to last week
        if (days.length > 0) {
            weeks.push(<div key={weeks.length} className="calendar-week">{days}</div>);
        }

        return (
            <div className="calendar-grid">
                <div className="weekday-header">
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                        <div key={day} className="weekday">{day}</div>
                    ))}
                </div>
                {weeks}
            </div>
        );
    };

    return (
        <div 
            className={`calendar-container ${isCalendarExpanded ? 'expanded' : ''}`}
        >
            <div 
                className="calendar-header" 
                onClick={(e) => {
                    e.stopPropagation();
                    toggleCalendar(e);
                }}
            >
                {/* Wrap buttons and current month in a container */}
                <div className="month-nav-container">
                    <button 
                        className="month-nav-button"
                        onClick={handlePreviousMonth}
                    >
                        ◀
                    </button>
                    <span className="current-month">
                        {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
                    </span>
                    <button 
                        className="month-nav-button"
                        onClick={handleNextMonth}
                    >
                        ▶
                    </button>
                </div>
            </div>
            <div className="calendar-content" onClick={(e) => e.stopPropagation()}>
                {renderCalendarGrid()}
            </div>
            
            {showTaskForm && selectedDate && (
                <div 
                    className="task-form-overlay"
                    onClick={(e) => {
                        e.stopPropagation();
                        setShowTaskForm(false);
                    }}
                >
                    <TaskForm
                        selectedDate={selectedDate}
                        onClose={() => {
                            console.log('Closing task form');
                            setShowTaskForm(false);
                            setSelectedDate(null);
                        }}
                    />
                </div>
            )}

            {showTaskEditor && selectedTask && (
                <div 
                    className="task-form-overlay"
                    onClick={(e) => {
                        e.stopPropagation();
                        setShowTaskEditor(false);
                    }}
                >
                    <TaskEditor
                        task={selectedTask}
                        onClose={() => {
                            console.log('Closing task editor');
                            setShowTaskEditor(false);
                            setSelectedTask(null);
                        }}
                    />
                </div>
            )}
        </div>
    );
};

export default MinimizedCalendar; 