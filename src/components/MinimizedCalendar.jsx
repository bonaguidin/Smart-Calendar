import React, { useEffect, useRef } from 'react';
import { useCalendar } from '../context/CalendarContext';
import '../styles/MinimizedCalendar.css';

const MinimizedCalendar = ({ isExpanded, onToggle }) => {
    const { tasks, currentDate } = useCalendar();
    const calendarRef = useRef(null);

    return (
        <div 
            ref={calendarRef}
            className={`calendar-container ${isExpanded ? 'expanded' : ''}`}
            onClick={onToggle}
        >
            <div className="calendar-header">
                <span className="current-month">
                    {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
                </span>
                <button className="toggle-button">
                    {isExpanded ? '▼' : '▲'}
                </button>
            </div>
            <div className="calendar-content">
                {/* Calendar grid implementation */}
            </div>
        </div>
    );
};

export default MinimizedCalendar; 