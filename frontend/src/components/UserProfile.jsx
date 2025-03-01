import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import '../styles/UserProfile.css';

/**
 * User Profile component for displaying and editing user information
 * Provides forms for updating profile details and changing password
 */
const UserProfile = () => {
  // Profile state
  const [profileData, setProfileData] = useState({
    display_name: '',
    timezone: '',
    location: '',
    preferences: {
      color_theme: 'light',
      default_view: 'month',
      notifications_enabled: true,
      weather_enabled: true,
      traffic_enabled: true,
      default_task_color: '#2196F3'
    }
  });
  
  // Password change state
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  
  // UI state
  const [activeTab, setActiveTab] = useState('profile');
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [profileErrors, setProfileErrors] = useState({});
  const [passwordErrors, setPasswordErrors] = useState({});
  
  // Get authentication context
  const { user, updateProfile, changePassword, loading, error, setError } = useAuth();
  
  // Initialize form with user data
  useEffect(() => {
    if (user) {
      setProfileData({
        display_name: user.display_name || '',
        timezone: user.timezone || 'UTC',
        location: user.location || '',
        preferences: user.preferences || {
          color_theme: 'light',
          default_view: 'month',
          notifications_enabled: true,
          weather_enabled: true,
          traffic_enabled: true,
          default_task_color: '#2196F3'
        }
      });
    }
  }, [user]);
  
  /**
   * Handle profile form input changes
   * @param {Event} e - Input change event
   */
  const handleProfileChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    // Check if this is a preference field
    if (name.startsWith('pref_')) {
      const prefName = name.replace('pref_', '');
      setProfileData({
        ...profileData,
        preferences: {
          ...profileData.preferences,
          [prefName]: type === 'checkbox' ? checked : value
        }
      });
    } else {
      setProfileData({
        ...profileData,
        [name]: value
      });
    }
    
    // Clear field error
    if (profileErrors[name]) {
      setProfileErrors({
        ...profileErrors,
        [name]: ''
      });
    }
  };
  
  /**
   * Handle password change form input
   * @param {Event} e - Input change event
   */
  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData({
      ...passwordData,
      [name]: value
    });
    
    // Clear field error
    if (passwordErrors[name]) {
      setPasswordErrors({
        ...passwordErrors,
        [name]: ''
      });
    }
  };
  
  /**
   * Validate profile form
   * @returns {boolean} Whether the form is valid
   */
  const validateProfileForm = () => {
    const errors = {};
    
    if (!profileData.display_name.trim()) {
      errors.display_name = 'Display name is required';
    }
    
    setProfileErrors(errors);
    return Object.keys(errors).length === 0;
  };
  
  /**
   * Validate password change form
   * @returns {boolean} Whether the form is valid
   */
  const validatePasswordForm = () => {
    const errors = {};
    
    if (!passwordData.current_password) {
      errors.current_password = 'Current password is required';
    }
    
    if (!passwordData.new_password) {
      errors.new_password = 'New password is required';
    } else if (passwordData.new_password.length < 8) {
      errors.new_password = 'Password must be at least 8 characters';
    }
    
    if (passwordData.new_password !== passwordData.confirm_password) {
      errors.confirm_password = 'Passwords do not match';
    }
    
    setPasswordErrors(errors);
    return Object.keys(errors).length === 0;
  };
  
  /**
   * Handle profile update submission
   * @param {Event} e - Form submission event
   */
  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    
    if (validateProfileForm()) {
      setError('');
      const success = await updateProfile(profileData);
      
      if (success) {
        setSuccessMessage('Profile updated successfully!');
        setIsEditingProfile(false);
        
        // Clear success message after 3 seconds
        setTimeout(() => {
          setSuccessMessage('');
        }, 3000);
      }
    }
  };
  
  /**
   * Handle password change submission
   * @param {Event} e - Form submission event
   */
  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    
    if (validatePasswordForm()) {
      setError('');
      const success = await changePassword({
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });
      
      if (success) {
        setSuccessMessage('Password changed successfully!');
        setPasswordData({
          current_password: '',
          new_password: '',
          confirm_password: ''
        });
        
        // Clear success message after 3 seconds
        setTimeout(() => {
          setSuccessMessage('');
        }, 3000);
      }
    }
  };
  
  if (!user) {
    return (
      <div className="profile-container">
        <div className="profile-loading">Loading profile...</div>
      </div>
    );
  }
  
  return (
    <div className="profile-container">
      <div className="profile-header">
        <h1>User Profile</h1>
        <div className="profile-tabs">
          <button 
            className={`profile-tab ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            Profile
          </button>
          <button 
            className={`profile-tab ${activeTab === 'password' ? 'active' : ''}`}
            onClick={() => setActiveTab('password')}
          >
            Change Password
          </button>
          <button 
            className={`profile-tab ${activeTab === 'preferences' ? 'active' : ''}`}
            onClick={() => setActiveTab('preferences')}
          >
            Preferences
          </button>
        </div>
      </div>
      
      {/* Success message */}
      {successMessage && (
        <div className="profile-success-message">{successMessage}</div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="profile-error-message">{error}</div>
      )}
      
      {/* Profile Tab */}
      {activeTab === 'profile' && (
        <div className="profile-tab-content">
          {!isEditingProfile ? (
            <div className="profile-info">
              <div className="profile-field">
                <span className="profile-label">Username:</span>
                <span className="profile-value">{user.username}</span>
              </div>
              <div className="profile-field">
                <span className="profile-label">Email:</span>
                <span className="profile-value">{user.email}</span>
              </div>
              <div className="profile-field">
                <span className="profile-label">Display Name:</span>
                <span className="profile-value">{user.display_name || user.username}</span>
              </div>
              <div className="profile-field">
                <span className="profile-label">Timezone:</span>
                <span className="profile-value">{user.timezone || 'UTC'}</span>
              </div>
              <div className="profile-field">
                <span className="profile-label">Location:</span>
                <span className="profile-value">{user.location || 'Not specified'}</span>
              </div>
              <div className="profile-field">
                <span className="profile-label">Joined:</span>
                <span className="profile-value">
                  {new Date(user.created_at).toLocaleDateString()}
                </span>
              </div>
              
              <button 
                className="profile-edit-button"
                onClick={() => setIsEditingProfile(true)}
              >
                Edit Profile
              </button>
            </div>
          ) : (
            <form className="profile-form" onSubmit={handleProfileSubmit}>
              <div className="form-group">
                <label htmlFor="display_name">Display Name</label>
                <input
                  type="text"
                  id="display_name"
                  name="display_name"
                  value={profileData.display_name}
                  onChange={handleProfileChange}
                  disabled={loading}
                  className={profileErrors.display_name ? 'input-error' : ''}
                />
                {profileErrors.display_name && (
                  <span className="error-message">{profileErrors.display_name}</span>
                )}
              </div>
              
              <div className="form-group">
                <label htmlFor="timezone">Timezone</label>
                <select
                  id="timezone"
                  name="timezone"
                  value={profileData.timezone}
                  onChange={handleProfileChange}
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
              
              <div className="form-group">
                <label htmlFor="location">Location (optional)</label>
                <input
                  type="text"
                  id="location"
                  name="location"
                  value={profileData.location}
                  onChange={handleProfileChange}
                  placeholder="e.g. New York, NY"
                  disabled={loading}
                />
              </div>
              
              <div className="profile-form-buttons">
                <button 
                  type="button" 
                  className="cancel-button"
                  onClick={() => setIsEditingProfile(false)}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="save-button"
                  disabled={loading}
                >
                  {loading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
      
      {/* Password Tab */}
      {activeTab === 'password' && (
        <div className="profile-tab-content">
          <form className="profile-form" onSubmit={handlePasswordSubmit}>
            <div className="form-group">
              <label htmlFor="current_password">Current Password</label>
              <input
                type="password"
                id="current_password"
                name="current_password"
                value={passwordData.current_password}
                onChange={handlePasswordChange}
                disabled={loading}
                className={passwordErrors.current_password ? 'input-error' : ''}
              />
              {passwordErrors.current_password && (
                <span className="error-message">{passwordErrors.current_password}</span>
              )}
            </div>
            
            <div className="form-group">
              <label htmlFor="new_password">New Password</label>
              <input
                type="password"
                id="new_password"
                name="new_password"
                value={passwordData.new_password}
                onChange={handlePasswordChange}
                disabled={loading}
                className={passwordErrors.new_password ? 'input-error' : ''}
              />
              {passwordErrors.new_password && (
                <span className="error-message">{passwordErrors.new_password}</span>
              )}
            </div>
            
            <div className="form-group">
              <label htmlFor="confirm_password">Confirm New Password</label>
              <input
                type="password"
                id="confirm_password"
                name="confirm_password"
                value={passwordData.confirm_password}
                onChange={handlePasswordChange}
                disabled={loading}
                className={passwordErrors.confirm_password ? 'input-error' : ''}
              />
              {passwordErrors.confirm_password && (
                <span className="error-message">{passwordErrors.confirm_password}</span>
              )}
            </div>
            
            <button 
              type="submit" 
              className="save-button full-width"
              disabled={loading}
            >
              {loading ? 'Changing Password...' : 'Change Password'}
            </button>
          </form>
        </div>
      )}
      
      {/* Preferences Tab */}
      {activeTab === 'preferences' && (
        <div className="profile-tab-content">
          <form className="profile-form" onSubmit={handleProfileSubmit}>
            <div className="form-group">
              <label htmlFor="pref_color_theme">Theme</label>
              <select
                id="pref_color_theme"
                name="pref_color_theme"
                value={profileData.preferences.color_theme}
                onChange={handleProfileChange}
                disabled={loading}
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="system">System (Auto)</option>
              </select>
            </div>
            
            <div className="form-group">
              <label htmlFor="pref_default_view">Default Calendar View</label>
              <select
                id="pref_default_view"
                name="pref_default_view"
                value={profileData.preferences.default_view}
                onChange={handleProfileChange}
                disabled={loading}
              >
                <option value="day">Day</option>
                <option value="week">Week</option>
                <option value="month">Month</option>
                <option value="agenda">Agenda</option>
              </select>
            </div>
            
            <div className="form-group">
              <label htmlFor="pref_default_task_color">Default Task Color</label>
              <input
                type="color"
                id="pref_default_task_color"
                name="pref_default_task_color"
                value={profileData.preferences.default_task_color}
                onChange={handleProfileChange}
                disabled={loading}
              />
            </div>
            
            <div className="form-group checkbox-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="pref_notifications_enabled"
                  checked={profileData.preferences.notifications_enabled}
                  onChange={handleProfileChange}
                  disabled={loading}
                />
                <span>Enable Notifications</span>
              </label>
            </div>
            
            <div className="form-group checkbox-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="pref_weather_enabled"
                  checked={profileData.preferences.weather_enabled}
                  onChange={handleProfileChange}
                  disabled={loading}
                />
                <span>Show Weather Information</span>
              </label>
            </div>
            
            <div className="form-group checkbox-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="pref_traffic_enabled"
                  checked={profileData.preferences.traffic_enabled}
                  onChange={handleProfileChange}
                  disabled={loading}
                />
                <span>Show Traffic Information</span>
              </label>
            </div>
            
            <button 
              type="submit" 
              className="save-button full-width"
              disabled={loading}
            >
              {loading ? 'Saving...' : 'Save Preferences'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default UserProfile; 