import React, { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';
import { useCalendar } from '../context/CalendarContext';
import { FaGlobeAmericas } from 'react-icons/fa';

// Initialize dayjs plugins
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('America/Chicago');

const TimezoneAwareCalendar = () => {
    const { tasks, currentDate } = useCalendar();
    const [showTimezoneInfo, setShowTimezoneInfo] = useState(false);
    const [localTzOffset, setLocalTzOffset] = useState(0);

    useEffect(() => {
        // Calculate local timezone offset
        const offset = dayjs().tz('America/Chicago').utcOffset() / 60;
        setLocalTzOffset(offset);
    }, []);

    const formatTaskTime = (task) => {
        const taskDate = dayjs.tz(task.startDate, 'America/Chicago');
        return taskDate.format('h:mm A z');
    };

    const isDSTTransition = (date) => {
        const prevDay = dayjs(date).subtract(1, 'day');
        const nextDay = dayjs(date).add(1, 'day');
        return prevDay.utcOffset() !== date.utcOffset() || 
               date.utcOffset() !== nextDay.utcOffset();
    };

    return (
        <div className="timezone-aware-calendar">
            <div className="timezone-header">
                <button 
                    className="timezone-toggle"
                    onClick={() => setShowTimezoneInfo(!showTimezoneInfo)}
                >
                    <FaGlobeAmericas />
                    {showTimezoneInfo ? 'Hide Timezone Info' : 'Show Timezone Info'}
                </button>
                {showTimezoneInfo && (
                    <div className="timezone-info">
                        <p>Calendar Timezone: America/Chicago (UTC{localTzOffset >= 0 ? '+' : ''}{localTzOffset})</p>
                        <p>Current Time: {dayjs().tz('America/Chicago').format('h:mm A z')}</p>
                    </div>
                )}
            </div>
            
            {/* Calendar Grid with Timezone Indicators */}
            <div className="calendar-grid">
                {renderCalendarDays().map((day, index) => (
                    <div 
                        key={index} 
                        className={`calendar-day ${isDSTTransition(day) ? 'dst-transition' : ''}`}
                    >
                        <div className="day-header">
                            <span className="day-number">{day.format('D')}</span>
                            {isDSTTransition(day) && (
                                <span className="dst-indicator">DST</span>
                            )}
                        </div>
                        {/* Render tasks with timezone-aware times */}
                        {tasks[day.format('YYYY-MM-DD')]?.map(task => (
                            <div key={task.id} className="task-item">
                                <span className="task-title">{task.title}</span>
                                <span className="task-time">{formatTaskTime(task)}</span>
                            </div>
                        ))}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TimezoneAwareCalendar; 