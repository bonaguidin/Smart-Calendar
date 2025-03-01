import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/Header.css';

/**
 * Header component with navigation and user account dropdown
 * Displays user information and account management options
 */
const Header = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Handle logout action
  const handleLogout = () => {
    logout();
    navigate('/login');
    setDropdownOpen(false);
  };

  // Toggle dropdown visibility
  const toggleDropdown = () => {
    setDropdownOpen(!dropdownOpen);
  };

  return (
    <header className="app-header">
      <div className="header-logo">
        <Link to="/">
          <h1>Smart Calendar</h1>
        </Link>
      </div>

      <nav className="header-nav">
        {isAuthenticated ? (
          <div className="user-menu" ref={dropdownRef}>
            <button 
              className="user-menu-button" 
              onClick={toggleDropdown}
              aria-label="Account menu"
            >
              <div className="user-avatar">
                {user?.display_name?.charAt(0) || user?.username?.charAt(0) || '?'}
              </div>
              <span className="user-name">{user?.display_name || user?.username}</span>
              <span className={`dropdown-arrow ${dropdownOpen ? 'open' : ''}`}>▼</span>
            </button>

            {dropdownOpen && (
              <div className="user-dropdown">
                <div className="dropdown-header">
                  <strong>{user?.display_name || user?.username}</strong>
                  <span>{user?.email}</span>
                </div>

                <ul className="dropdown-menu">
                  <li>
                    <Link to="/profile" onClick={() => setDropdownOpen(false)}>
                      <i className="icon">👤</i> Profile Settings
                    </Link>
                  </li>
                  <li>
                    <Link to="/profile?tab=password" onClick={() => setDropdownOpen(false)}>
                      <i className="icon">🔑</i> Change Password
                    </Link>
                  </li>
                  <li>
                    <Link to="/profile?tab=preferences" onClick={() => setDropdownOpen(false)}>
                      <i className="icon">⚙️</i> Preferences
                    </Link>
                  </li>
                  <li className="dropdown-divider"></li>
                  <li>
                    <Link to="/clear-data" onClick={() => setDropdownOpen(false)}>
                      <i className="icon">🗑️</i> Clear Calendar Data
                    </Link>
                  </li>
                  <li className="dropdown-divider"></li>
                  <li>
                    <button className="logout-button" onClick={handleLogout}>
                      <i className="icon">🚪</i> Log Out
                    </button>
                  </li>
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="auth-links">
            <Link to="/login" className="nav-link">Log In</Link>
            <Link to="/register" className="nav-link register-link">Sign Up</Link>
          </div>
        )}
      </nav>
    </header>
  );
};

export default Header; 