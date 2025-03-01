/**
 * Simple script to test connectivity to the backend server
 * This uses the same fetch API that the React app uses
 */
const API_URL = "http://localhost:5000";

// Try to connect to the backend root endpoint
console.log(`Testing connection to backend at ${API_URL}...`);

// Use the fetch API similar to what's in our React app
fetch(API_URL)
  .then(response => {
    console.log('Connection successful!');
    console.log(`Status code: ${response.status}`);
    return response.json();
  })
  .then(data => {
    console.log('Response data:', data);
    console.log('Backend is running and accessible.');
  })
  .catch(error => {
    console.error('Connection failed:', error.message);
    console.log('\nPossible issues:');
    console.log('1. The backend server is not running');
    console.log('2. The backend server is running on a different port');
    console.log('3. There might be a firewall blocking the connection');
    console.log('4. CORS might be preventing access (expected in browser but not in Node)');
    console.log('5. The backend might be listening only on localhost/127.0.0.1 and not 0.0.0.0');
  }); 