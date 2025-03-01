import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/ClearData.css';

/**
 * Component for clearing user's calendar data
 * Includes confirmation dialog and success/error feedback
 */
const ClearData = () => {
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [isConfirming, setIsConfirming] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState({ success: false, message: '' });
  const [confirmText, setConfirmText] = useState('');
  
  // API URL configuration
  const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000/api';

  /**
   * Handle initial clear data button click
   * Shows confirmation dialog
   */
  const handleClearRequest = () => {
    setIsConfirming(true);
    setResult({ success: false, message: '' });
  };

  /**
   * Handle confirmation dialog cancel
   * Resets the confirmation state
   */
  const handleCancel = () => {
    setIsConfirming(false);
    setConfirmText('');
  };

  /**
   * Perform the actual data clearing operation
   * Makes API call to delete all user tasks
   */
  const handleConfirmClear = async () => {
    // Verify confirmation text
    if (confirmText !== 'DELETE') {
      setResult({
        success: false,
        message: 'Please type DELETE to confirm'
      });
      return;
    }

    setIsProcessing(true);
    
    try {
      // Call the API to delete all tasks
      const response = await fetch(`${API_BASE_URL}/tasks/clear-all`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        setResult({
          success: true,
          message: 'All calendar data has been successfully cleared!'
        });
        setIsConfirming(false);
        setConfirmText('');
      } else {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to clear calendar data');
      }
    } catch (error) {
      console.error('Error clearing calendar data:', error);
      setResult({
        success: false,
        message: `Error: ${error.message || 'Something went wrong'}`
      });
    } finally {
      setIsProcessing(false);
    }
  };

  /**
   * Navigate back to dashboard
   */
  const handleGoBack = () => {
    navigate('/');
  };

  return (
    <div className="clear-data-container">
      <h1>Clear Calendar Data</h1>
      <p className="description">
        This action will permanently delete all your calendar tasks and events.
        This cannot be undone.
      </p>

      {result.message && (
        <div className={`result-message ${result.success ? 'success' : 'error'}`}>
          {result.message}
        </div>
      )}

      {!isConfirming ? (
        <div className="action-buttons">
          <button 
            className="clear-button danger" 
            onClick={handleClearRequest}
            disabled={isProcessing}
          >
            Clear All Calendar Data
          </button>
          <button 
            className="back-button" 
            onClick={handleGoBack}
          >
            Back to Dashboard
          </button>
        </div>
      ) : (
        <div className="confirmation-dialog">
          <h3>Are you absolutely sure?</h3>
          <p>
            This will permanently delete <strong>all tasks and events</strong> for your account:{' '}
            <strong>{user?.email}</strong>
          </p>
          <p>
            Please type <strong>DELETE</strong> to confirm:
          </p>
          <input
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="Type DELETE here"
            className="confirm-input"
          />
          <div className="confirmation-buttons">
            <button 
              className="confirm-button danger" 
              onClick={handleConfirmClear}
              disabled={isProcessing}
            >
              {isProcessing ? 'Deleting...' : 'Yes, Delete Everything'}
            </button>
            <button 
              className="cancel-button" 
              onClick={handleCancel}
              disabled={isProcessing}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClearData; 