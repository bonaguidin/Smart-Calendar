import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/AuthForms.css';

/**
 * Login Page component that handles user authentication
 * Provides form for username/email and password input with validation
 */
const LoginPage = () => {
  // Form state
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    rememberMe: false
  });
  const [fieldErrors, setFieldErrors] = useState({});
  
  // Get authentication context
  const { login, loading, error } = useAuth();
  
  /**
   * Handle input changes and update form state
   * @param {Event} e - Input change event
   */
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
    
    // Clear field error when user starts typing
    if (fieldErrors[name]) {
      setFieldErrors({
        ...fieldErrors,
        [name]: ''
      });
    }
  };
  
  /**
   * Validate form fields before submission
   * @returns {boolean} Whether the form is valid
   */
  const validateForm = () => {
    const errors = {};
    
    if (!formData.username.trim()) {
      errors.username = 'Username or email is required';
    }
    
    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters';
    }
    
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };
  
  /**
   * Handle form submission
   * @param {Event} e - Form submission event
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (validateForm()) {
      // Determine if input is email or username
      const isEmail = formData.username.includes('@');
      
      // Prepare credentials object based on input type
      const credentials = isEmail 
        ? { email: formData.username, password: formData.password }
        : { username: formData.username, password: formData.password };
      
      // If remember me is checked, store preference
      if (formData.rememberMe) {
        localStorage.setItem('remember_user', 'true');
      } else {
        localStorage.removeItem('remember_user');
      }
      
      // Attempt login
      await login(credentials);
    }
  };
  
  return (
    <div className="auth-container">
      <div className="auth-form-container">
        <h1 className="auth-title">Log In to Smart Calendar</h1>
        <p className="auth-subtitle">Enter your credentials to access your calendar</p>
        
        {error && <div className="auth-error">{error}</div>}
        
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username or Email</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="Enter your username or email"
              disabled={loading}
              className={fieldErrors.username ? 'input-error' : ''}
            />
            {fieldErrors.username && (
              <span className="error-message">{fieldErrors.username}</span>
            )}
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Enter your password"
              disabled={loading}
              className={fieldErrors.password ? 'input-error' : ''}
            />
            {fieldErrors.password && (
              <span className="error-message">{fieldErrors.password}</span>
            )}
          </div>
          
          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                name="rememberMe"
                checked={formData.rememberMe}
                onChange={handleChange}
                disabled={loading}
              />
              <span>Remember me</span>
            </label>
            <Link to="/forgot-password" className="forgot-password-link">
              Forgot Password?
            </Link>
          </div>
          
          <button 
            type="submit" 
            className="auth-button" 
            disabled={loading}
          >
            {loading ? 'Logging in...' : 'Log In'}
          </button>
        </form>
        
        <div className="auth-links">
          <p>
            Don't have an account?{' '}
            <Link to="/register" className="auth-link">
              Sign Up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage; 