# PowerShell script to start the React frontend server
Write-Host "Starting Smart Calendar frontend server..." -ForegroundColor Cyan

# Navigate to the frontend directory
Set-Location -Path ".\smart-calendar\frontend"

# Start the React development server
Write-Host "Running npm start..." -ForegroundColor Green
npm start 