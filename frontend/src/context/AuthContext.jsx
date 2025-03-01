import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// Create the authentication context
const AuthContext = createContext();

// API URL configuration - FORCE direct URL for troubleshooting
const API_BASE_URL = 'http://localhost:5000/api';
console.log('Using FORCED API base URL:', API_BASE_URL);

// Custom hook to use the auth context
export const useAuth = () => useContext(AuthContext);

// Provider component for the auth context
export const AuthProvider = ({ children }) => {
  // State management for user authentication
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('auth_token'));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const navigate = useNavigate();
  
  // Check if user is authenticated on initial load
  useEffect(() => {
    const checkLoggedIn = async () => {
      if (token) {
        try {
          // Fetch user profile with the stored token
          const response = await fetch(`${API_BASE_URL}/auth/profile`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (response.ok) {
            const data = await response.json();
            setUser(data.user);
          } else {
            // Token is invalid or expired
            logout();
          }
        } catch (err) {
          console.error('Error checking authentication:', err);
          console.error('Error details:', err.message);
          logout();
        }
      }
      
      setLoading(false);
    };
    
    checkLoggedIn();
  }, [token]);
  
  // Login function
  const login = async (credentials) => {
    setLoading(true);
    setError('');
    
    try {
      console.log('Logging in with credentials:', {
        ...credentials, 
        password: credentials.password ? '******' : undefined
      });
      
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(credentials)
      });
      
      // Log the full response for debugging
      console.log('Login response status:', response.status);
      
      // For non-JSON responses
      if (!response.ok) {
        let errorMessage = '';
        try {
          const errorText = await response.text();
          console.error('Login error response:', errorText);
          errorMessage = errorText;
        } catch (e) {
          errorMessage = response.statusText;
        }
        
        if (response.status === 500) {
          setError('Server error. Please check if the backend server is running.');
        } else if (response.status === 401) {
          setError('Invalid credentials. Please check your username/email and password.');
        } else if (response.status === 504) {
          setError('Timeout connecting to server. Please check if the backend is running.');
        } else {
          setError(`Login failed: ${errorMessage}`);
        }
        return false;
      }
      
      // Parse JSON for successful responses
      const data = await response.json();
      console.log('Login response data:', data);
      
      localStorage.setItem('auth_token', data.token);
      setToken(data.token);
      setUser(data.user);
      navigate('/');
      return true;
    } catch (err) {
      console.error('Login error:', err);
      console.error('Error details:', err.message);
      setError(`Connection error: ${err.message}. Please check if the backend server is running at ${API_BASE_URL}.`);
      return false;
    } finally {
      setLoading(false);
    }
  };
  
  // Register function
  const register = async (userData) => {
    setLoading(true);
    setError('');
    
    try {
      console.log('Registering user with data:', userData);
      
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
      });
      
      // Log the full response for debugging
      console.log('Registration response status:', response.status);
      
      // For non-JSON responses (like HTML error pages)
      if (!response.ok) {
        let errorMessage = '';
        try {
          const errorText = await response.text();
          console.error('Registration error response:', errorText);
          errorMessage = errorText;
        } catch (e) {
          errorMessage = response.statusText;
        }
        
        if (response.status === 500) {
          setError('Server error. Please check if the backend server is running.');
        } else if (response.status === 409) {
          setError('Username or email already exists.');
        } else if (response.status === 504) {
          setError('Timeout connecting to server. Please check if the backend is running.');
        } else {
          setError(`Registration failed: ${errorMessage}`);
        }
        return false;
      }
      
      // Parse JSON for successful responses
      const data = await response.json();
      console.log('Registration response data:', data);
      
      localStorage.setItem('auth_token', data.token);
      setToken(data.token);
      setUser(data.user);
      navigate('/');
      return true;
    } catch (err) {
      console.error('Registration error:', err);
      console.error('Error details:', err.message);
      setError(`Connection error: ${err.message}. Please check if the backend server is running at ${API_BASE_URL}.`);
      return false;
    } finally {
      setLoading(false);
    }
  };
  
  // Logout function
  const logout = () => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
    navigate('/login');
  };
  
  // Update user profile
  const updateProfile = async (profileData) => {
    if (!token) return false;
    
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(profileData)
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setUser(data.user);
        return true;
      } else {
        setError(data.error || 'Failed to update profile.');
        return false;
      }
    } catch (err) {
      console.error('Profile update error:', err);
      console.error('Error details:', err.message);
      setError(`Connection error: ${err.message}. Please check if the backend server is running.`);
      return false;
    } finally {
      setLoading(false);
    }
  };
  
  // Change password
  const changePassword = async (passwordData) => {
    if (!token) return false;
    
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(passwordData)
      });
      
      const data = await response.json();
      
      if (response.ok) {
        return true;
      } else {
        setError(data.error || 'Failed to change password.');
        return false;
      }
    } catch (err) {
      console.error('Password change error:', err);
      console.error('Error details:', err.message);
      setError(`Connection error: ${err.message}. Please check if the backend server is running.`);
      return false;
    } finally {
      setLoading(false);
    }
  };
  
  // Context value that will be provided to consumers
  const contextValue = {
    user,
    token,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    updateProfile,
    changePassword,
    setError
  };
  
  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext; 