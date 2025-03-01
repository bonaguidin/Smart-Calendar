import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/AuthForms.css';

/**
 * Registration Page component that handles new user sign up
 * Provides form for username, email, password and other fields with validation
 */
const RegisterPage = () => {
  // Form state
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    displayName: '',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    termsAccepted: false
  });
  const [fieldErrors, setFieldErrors] = useState({});
  
  // Get authentication context
  const { register, loading, error } = useAuth();
  
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
    
    // Username validation
    if (!formData.username.trim()) {
      errors.username = 'Username is required';
    } else if (formData.username.length < 3) {
      errors.username = 'Username must be at least 3 characters';
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
      errors.username = 'Username can only contain letters, numbers, and underscores';
    }
    
    // Email validation
    if (!formData.email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address';
    }
    
    // Password validation
    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters';
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/.test(formData.password)) {
      errors.password = 'Password must include uppercase, lowercase, number and special character';
    }
    
    // Confirm password validation
    if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }
    
    // Terms and conditions validation
    if (!formData.termsAccepted) {
      errors.termsAccepted = 'You must accept the terms and conditions';
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
      // Prepare user data object for registration
      const userData = {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        display_name: formData.displayName || formData.username,
        timezone: formData.timezone
      };
      
      // Attempt registration
      await register(userData);
    }
  };
  
  return (
    <div className="auth-container">
      <div className="auth-form-container register-form-container">
        <h1 className="auth-title">Create an Account</h1>
        <p className="auth-subtitle">Sign up to start using Smart Calendar</p>
        
        {error && <div className="auth-error">{error}</div>}
        
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="Choose a username"
              disabled={loading}
              className={fieldErrors.username ? 'input-error' : ''}
            />
            {fieldErrors.username && (
              <span className="error-message">{fieldErrors.username}</span>
            )}
          </div>
          
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="Enter your email address"
              disabled={loading}
              className={fieldErrors.email ? 'input-error' : ''}
            />
            {fieldErrors.email && (
              <span className="error-message">{fieldErrors.email}</span>
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
              placeholder="Create a password"
              disabled={loading}
              className={fieldErrors.password ? 'input-error' : ''}
            />
            {fieldErrors.password && (
              <span className="error-message">{fieldErrors.password}</span>
            )}
          </div>
          
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Confirm your password"
              disabled={loading}
              className={fieldErrors.confirmPassword ? 'input-error' : ''}
            />
            {fieldErrors.confirmPassword && (
              <span className="error-message">{fieldErrors.confirmPassword}</span>
            )}
          </div>
          
          <div className="form-group">
            <label htmlFor="displayName">Display Name (Optional)</label>
            <input
              type="text"
              id="displayName"
              name="displayName"
              value={formData.displayName}
              onChange={handleChange}
              placeholder="How would you like to be called?"
              disabled={loading}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="timezone">Timezone</label>
            <select
              id="timezone"
              name="timezone"
              value={formData.timezone}
              onChange={handleChange}
              disabled={loading}
            >
              <option value="UTC">UTC (Coordinated Universal Time)</option>
              <option value="America/New_York">Eastern Time (US & Canada)</option>
              <option value="America/Chicago">Central Time (US & Canada)</option>
              <option value="America/Denver">Mountain Time (US & Canada)</option>
              <option value="America/Los_Angeles">Pacific Time (US & Canada)</option>
              <option value="Europe/London">London</option>
              <option value="Europe/Paris">Paris</option>
              <option value="Asia/Tokyo">Tokyo</option>
              <option value="Australia/Sydney">Sydney</option>
            </select>
          </div>
          
          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                name="termsAccepted"
                checked={formData.termsAccepted}
                onChange={handleChange}
                disabled={loading}
                className={fieldErrors.termsAccepted ? 'input-error' : ''}
              />
              <span>
                I agree to the{' '}
                <Link to="/terms" className="auth-link">
                  Terms of Service
                </Link>{' '}
                and{' '}
                <Link to="/privacy" className="auth-link">
                  Privacy Policy
                </Link>
              </span>
            </label>
            {fieldErrors.termsAccepted && (
              <span className="error-message">{fieldErrors.termsAccepted}</span>
            )}
          </div>
          
          <button 
            type="submit" 
            className="auth-button" 
            disabled={loading}
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>
        
        <div className="auth-links">
          <p>
            Already have an account?{' '}
            <Link to="/login" className="auth-link">
              Log In
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage; 