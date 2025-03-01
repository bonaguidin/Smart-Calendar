/**
 * React proxy configuration 
 * This file is automatically loaded by react-scripts
 * Currently disabled to use direct API calls instead
 */
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  console.log('Proxy middleware is DISABLED - using direct API calls');
  
  // Proxy middleware is disabled to use direct API calls
  // Uncomment to re-enable proxy
  /*
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:5000',
      changeOrigin: true,
      pathRewrite: {
        '^/api': '/api'
      },
      onProxyReq: (proxyReq, req, res) => {
        console.log(`Proxying ${req.method} request to: ${proxyReq.path}`);
      },
      onError: (err, req, res) => {
        console.error('Proxy error:', err);
      }
    })
  );
  */
}; 