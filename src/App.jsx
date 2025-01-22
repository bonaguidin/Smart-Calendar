import React, { useState } from 'react';
import ChatInterface from './components/ChatInterface';
import MinimizedCalendar from './components/MinimizedCalendar';
import { CalendarProvider } from './context/CalendarContext';
import './styles/App.css';

const App = () => {
    const [isCalendarExpanded, setIsCalendarExpanded] = useState(false);

    return (
        <CalendarProvider>
            <div className="app-container">
                <ChatInterface />
                <MinimizedCalendar 
                    isExpanded={isCalendarExpanded}
                    onToggle={() => setIsCalendarExpanded(!isCalendarExpanded)}
                />
            </div>
        </CalendarProvider>
    );
};

export default App; 