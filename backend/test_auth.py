"""
Script to test authentication endpoints.
"""
import requests
import json
import sys
from datetime import datetime

# Base URL for API
BASE_URL = "http://localhost:5000/api"

# Store auth token
token = None

def print_response(response, message=None):
    """Print formatted response"""
    print("\n" + "="*50)
    if message:
        print(f"{message}")
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print("="*50 + "\n")

def test_register():
    """Test user registration endpoint"""
    global token
    
    print("\nTesting User Registration...")
    
    # Generate unique username using timestamp
    timestamp = int(datetime.now().timestamp())
    username = f"testuser_{timestamp}"
    
    # Registration data
    data = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "Password123!",
        "display_name": "Test User",
        "timezone": "America/New_York"
    }
    
    # Send registration request
    response = requests.post(f"{BASE_URL}/auth/register", json=data)
    print_response(response, "Registration Response")
    
    # Check if registration was successful
    if response.status_code == 200:
        token = response.json().get("token")
        print(f"Registration successful! Token: {token[:10]}...")
        return username
    else:
        print("Registration failed!")
        return None

def test_login(username, password="Password123!"):
    """Test user login endpoint"""
    global token
    
    print("\nTesting User Login...")
    
    # Login data
    data = {
        "username": username,
        "password": password
    }
    
    # Send login request
    response = requests.post(f"{BASE_URL}/auth/login", json=data)
    print_response(response, "Login Response")
    
    # Check if login was successful
    if response.status_code == 200:
        token = response.json().get("token")
        print(f"Login successful! Token: {token[:10]}...")
        return True
    else:
        print("Login failed!")
        return False

def test_get_profile():
    """Test get profile endpoint"""
    global token
    
    print("\nTesting Get Profile...")
    
    # Set auth header
    headers = {"Authorization": f"Bearer {token}"}
    
    # Send get profile request
    response = requests.get(f"{BASE_URL}/auth/profile", headers=headers)
    print_response(response, "Get Profile Response")
    
    # Check if get profile was successful
    if response.status_code == 200:
        print("Get profile successful!")
        return True
    else:
        print("Get profile failed!")
        return False

def test_update_profile():
    """Test update profile endpoint"""
    global token
    
    print("\nTesting Update Profile...")
    
    # Set auth header
    headers = {"Authorization": f"Bearer {token}"}
    
    # Update profile data
    data = {
        "display_name": "Updated Test User",
        "timezone": "Europe/London",
        "preferences": {
            "color_theme": "dark",
            "default_view": "week",
            "notifications_enabled": True
        }
    }
    
    # Send update profile request
    response = requests.put(f"{BASE_URL}/auth/profile", json=data, headers=headers)
    print_response(response, "Update Profile Response")
    
    # Check if update profile was successful
    if response.status_code == 200:
        print("Update profile successful!")
        return True
    else:
        print("Update profile failed!")
        return False

def test_change_password():
    """Test change password endpoint"""
    global token
    
    print("\nTesting Change Password...")
    
    # Set auth header
    headers = {"Authorization": f"Bearer {token}"}
    
    # Change password data
    data = {
        "current_password": "Password123!",
        "new_password": "NewPassword123!"
    }
    
    # Send change password request
    response = requests.post(f"{BASE_URL}/auth/change-password", json=data, headers=headers)
    print_response(response, "Change Password Response")
    
    # Check if change password was successful
    if response.status_code == 200:
        print("Change password successful!")
        # Try to login with new password
        return test_login(last_username, "NewPassword123!")
    else:
        print("Change password failed!")
        return False

def main():
    """Run all tests"""
    global last_username
    
    # Test registration
    last_username = test_register()
    if not last_username:
        sys.exit(1)
    
    # Test login
    if not test_login(last_username):
        sys.exit(1)
    
    # Test get profile
    if not test_get_profile():
        sys.exit(1)
    
    # Test update profile
    if not test_update_profile():
        sys.exit(1)
    
    # Test change password
    if not test_change_password():
        sys.exit(1)
    
    print("\nAll authentication tests passed successfully!")

if __name__ == "__main__":
    main() 