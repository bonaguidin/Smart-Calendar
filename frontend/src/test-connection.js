/**
 * Simple script to test connectivity to the backend server
 * Run with: node test-connection.js
 */
const http = require('http');

// Send a simple GET request to the backend root endpoint
const options = {
  hostname: 'localhost',
  port: 5000,
  path: '/',
  method: 'GET'
};

console.log('Attempting to connect to backend server at http://localhost:5000...');
const req = http.request(options, (res) => {
  console.log(`STATUS: ${res.statusCode}`);
  console.log(`HEADERS: ${JSON.stringify(res.headers)}`);
  
  res.on('data', (chunk) => {
    console.log(`BODY: ${chunk}`);
  });
});

req.on('error', (e) => {
  console.error(`Connection failed: ${e.message}`);
  console.log('\nPossible issues:');
  console.log('1. The backend server is not running');
  console.log('2. The backend server is running on a different port');
  console.log('3. There might be a firewall blocking the connection');
  console.log('4. The backend is listening only on 127.0.0.1 and not 0.0.0.0');
});

req.end(); 