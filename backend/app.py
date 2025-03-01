from main import app

# No need to initialize the database here as it's already done in main.py
# We just need this file to expose the app for Flask-Migrate to find it

if __name__ == '__main__':
    # Run the Flask app on all interfaces (not just localhost)
    print("Starting Flask server on 0.0.0.0:5000...")
    app.run(host='0.0.0.0', port=5000, debug=True) 