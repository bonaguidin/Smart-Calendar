import React, { createContext, useContext, useState, useEffect } from 'react';

const CalendarContext = createContext();

export const CalendarProvider = ({ children }) => {
    const [tasks, setTasks] = useState({});
    const [currentDate, setCurrentDate] = useState(new Date());

    const addTask = async (task) => {
        // Implementation for adding tasks
    };

    const value = {
        tasks,
        currentDate,
        setCurrentDate,
        addTask
    };

    return (
        <CalendarContext.Provider value={value}>
            {children}
        </CalendarContext.Provider>
    );
};

export const useCalendar = () => {
    const context = useContext(CalendarContext);
    if (!context) {
        throw new Error('useCalendar must be used within a CalendarProvider');
    }
    return context;
}; 