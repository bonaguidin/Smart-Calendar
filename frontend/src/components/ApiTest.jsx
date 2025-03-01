import React, { useState, useEffect } from 'react';

/**
 * API Test Component
 * Tests direct connectivity to the backend API
 */
const ApiTest = () => {
  const [status, setStatus] = useState('Testing...');
  const [error, setError] = useState(null);
  const [response, setResponse] = useState(null);
  
  // Get API URL from environment or use default
  const apiUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000/api';
  
  useEffect(() => {
    const testApi = async () => {
      try {
        console.log('Testing direct API connection to:', apiUrl);
        
        // Test the root endpoint
        const response = await fetch(`${apiUrl.replace('/api', '')}/`);
        
        if (response.ok) {
          const data = await response.json();
          setStatus('Connected');
          setResponse(data);
          console.log('API connection successful:', data);
        } else {
          setStatus('Failed');
          setError(`Status: ${response.status} ${response.statusText}`);
          console.error('API connection failed:', response.statusText);
        }
      } catch (err) {
        setStatus('Error');
        setError(err.message);
        console.error('API connection error:', err);
      }
    };
    
    testApi();
  }, [apiUrl]);
  
  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto' }}>
      <h2>API Connection Test</h2>
      
      <div style={{ marginBottom: '20px' }}>
        <strong>Environment Variables:</strong>
        <pre style={{ background: '#f5f5f5', padding: '10px', borderRadius: '4px' }}>
          {JSON.stringify(process.env, null, 2)}
        </pre>
      </div>
      
      <div style={{ marginBottom: '20px' }}>
        <strong>Testing API URL:</strong> {apiUrl}
      </div>
      
      <div style={{ 
        padding: '15px', 
        borderRadius: '4px',
        background: status === 'Connected' ? '#e6ffe6' : status === 'Failed' || status === 'Error' ? '#ffe6e6' : '#f0f0f0'
      }}>
        <strong>Status:</strong> {status}
        {error && (
          <div style={{ marginTop: '10px', color: 'red' }}>
            <strong>Error:</strong> {error}
          </div>
        )}
        {response && (
          <div style={{ marginTop: '10px' }}>
            <strong>Response:</strong>
            <pre style={{ background: '#f5f5f5', padding: '10px', borderRadius: '4px' }}>
              {JSON.stringify(response, null, 2)}
            </pre>
          </div>
        )}
      </div>
      
      <div style={{ marginTop: '20px' }}>
        <h3>Troubleshooting Tips:</h3>
        <ul>
          <li>Make sure the backend server is running on port 5000</li>
          <li>Check for CORS issues in the browser console</li>
          <li>Verify network connectivity between frontend and backend</li>
          <li>Try accessing the API directly in a browser: <a href="http://localhost:5000/" target="_blank" rel="noopener noreferrer">http://localhost:5000/</a></li>
        </ul>
      </div>
    </div>
  );
};

export default ApiTest; 