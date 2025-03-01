# PowerShell script to start the Flask backend server
Write-Host "Starting Smart Calendar backend server..." -ForegroundColor Cyan

# Navigate to the backend directory
Set-Location -Path ".\smart-calendar\backend"

# Run the Flask server directly with Python
Write-Host "Running Flask app..." -ForegroundColor Green
python -c "from main import app; app.run(host='0.0.0.0', port=5000, debug=True)" 