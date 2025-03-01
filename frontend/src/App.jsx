import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ChatInterface from './components/ChatInterface';
import MinimizedCalendar from './components/MinimizedCalendar';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import UserProfile from './components/UserProfile';
import ProtectedRoute from './components/ProtectedRoute';
import ApiTest from './components/ApiTest';
import Header from './components/Header';
import ClearData from './components/ClearData';
import { CalendarProvider } from './context/CalendarContext';
import { AuthProvider } from './context/AuthContext';
import './styles/App.css';

/**
 * Main App component that sets up routing and context providers
 * Handles authentication and protected routes
 */
const App = () => {
    const [isCalendarExpanded, setIsCalendarExpanded] = useState(false);
    
    // Main dashboard view with chat and calendar
    const Dashboard = () => (
        <>
            <Header />
            <div className="app-container">
                <ChatInterface />
                <MinimizedCalendar 
                    isExpanded={isCalendarExpanded}
                    onToggle={() => setIsCalendarExpanded(!isCalendarExpanded)}
                />
            </div>
        </>
    );

    // Layout component that includes Header
    const Layout = ({ children }) => (
        <>
            <Header />
            <div className="main-content">
                {children}
            </div>
        </>
    );

    return (
        <Router>
            <AuthProvider>
                <CalendarProvider>
                    <Routes>
                        {/* Public routes */}
                        <Route path="/login" element={<LoginPage />} />
                        <Route path="/register" element={<RegisterPage />} />
                        <Route path="/api-test" element={<ApiTest />} />
                        
                        {/* Protected routes */}
                        <Route path="/" element={
                            <ProtectedRoute>
                                <Dashboard />
                            </ProtectedRoute>
                        } />
                        
                        <Route path="/profile" element={
                            <ProtectedRoute>
                                <Layout>
                                    <UserProfile />
                                </Layout>
                            </ProtectedRoute>
                        } />
                        
                        <Route path="/clear-data" element={
                            <ProtectedRoute>
                                <Layout>
                                    <ClearData />
                                </Layout>
                            </ProtectedRoute>
                        } />
                        
                        {/* Redirect all other routes to dashboard */}
                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                </CalendarProvider>
            </AuthProvider>
        </Router>
    );
};

export default App; 