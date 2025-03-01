# PowerShell script to test backend connectivity
Write-Host "Testing connection to backend server..." -ForegroundColor Cyan

$backendUrl = "http://localhost:5000"
Write-Host "Attempting to connect to: $backendUrl" -ForegroundColor Yellow

try {
    # Make the request to the backend
    $response = Invoke-WebRequest -Uri $backendUrl -Method Get -TimeoutSec 5
    
    # Display the response
    Write-Host "Connection successful!" -ForegroundColor Green
    Write-Host "Status code: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response content:"
    $response.Content
} catch {
    # Handle errors
    Write-Host "Connection failed: $_" -ForegroundColor Red
    Write-Host "`nPossible issues:" -ForegroundColor Yellow
    Write-Host "1. The backend server is not running"
    Write-Host "2. The backend server is running on a different port"
    Write-Host "3. There might be a firewall blocking the connection"
    Write-Host "4. The backend might be listening only on localhost/127.0.0.1 and not on 0.0.0.0"
} 