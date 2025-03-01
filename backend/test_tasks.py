"""
Script to test task management endpoints.
"""
import requests
import json
import sys
from datetime import datetime, timedelta

# Base URL for API
BASE_URL = "http://localhost:5000/api"

# Store auth token and user data
token = None
user_data = None

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

def login():
    """Login to get authentication token"""
    global token, user_data
    
    print("\nLogging in...")
    
    # Login data - using the test user we created
    # You may need to update these credentials if they've changed
    data = {
        "username": "testuser_1740716590",
        "password": "NewPassword123!"
    }
    
    # Send login request
    response = requests.post(f"{BASE_URL}/auth/login", json=data)
    if response.status_code != 200:
        print("Login failed with the default user. Creating a new test user...")
        
        # Generate unique username using timestamp
        timestamp = int(datetime.now().timestamp())
        username = f"testuser_{timestamp}"
        
        # Registration data
        reg_data = {
            "username": username,
            "email": f"{username}@example.com",
            "password": "Password123!",
            "display_name": "Test User",
            "timezone": "America/New_York"
        }
        
        # Register new user
        reg_response = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
        if reg_response.status_code != 200:
            print("Failed to create test user")
            print_response(reg_response, "Registration Failed")
            sys.exit(1)
            
        # Update login data with new user
        data = {
            "username": username,
            "password": "Password123!"
        }
        
        # Try login again
        response = requests.post(f"{BASE_URL}/auth/login", json=data)
        
    print_response(response, "Login Response")
    
    # Extract token
    if response.status_code == 200:
        token = response.json().get("token")
        user_data = response.json().get("user")
        print(f"Login successful! User ID: {user_data.get('id')}")
        return True
    else:
        print("Login failed!")
        return False

def test_create_task():
    """Test task creation endpoint"""
    global token
    
    print("\nTesting Task Creation...")
    
    # Set auth header
    headers = {"Authorization": f"Bearer {token}"}
    
    # Today's date
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Task data
    data = {
        "title": "Test Task",
        "description": "This is a test task created for testing purposes",
        "startDate": today,
        "endDate": tomorrow,
        "color": "#FF5722",
        "time": "14:00"
    }
    
    # Send create task request
    response = requests.post(f"{BASE_URL}/parse-task", json={"input": "Create a test task for today and tomorrow"})
    print_response(response, "Parse Task Response")
    
    # Get task details from response
    if response.status_code == 200:
        task_data = response.json()
        
        # Confirm task
        confirm_response = requests.post(f"{BASE_URL}/confirm-task", json=task_data, headers=headers)
        print_response(confirm_response, "Confirm Task Response")
        
        if confirm_response.status_code == 200:
            print("Task creation successful!")
            return confirm_response.json().get("task", {}).get("group_id")
        else:
            print("Task confirmation failed!")
            return None
    else:
        print("Task parsing failed!")
        return None

def test_get_tasks():
    """Test task retrieval endpoint"""
    global token
    
    print("\nTesting Task Retrieval...")
    
    # Set auth header
    headers = {"Authorization": f"Bearer {token}"}
    
    # Send get tasks request
    response = requests.get(f"{BASE_URL}/tasks", headers=headers)
    print_response(response, "Get Tasks Response")
    
    # Check if get tasks was successful
    if response.status_code == 200:
        print("Task retrieval successful!")
        return True
    else:
        print("Task retrieval failed!")
        return False

def test_update_task(task_id):
    """Test task update endpoint"""
    global token
    
    if not task_id:
        print("No task ID provided for update")
        return False
    
    print(f"\nTesting Task Update for ID: {task_id}...")
    
    # Set auth header
    headers = {"Authorization": f"Bearer {token}"}
    
    # Today's date
    today = datetime.now().strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Updated task data
    data = {
        "title": "Updated Test Task",
        "description": "This task was updated for testing purposes",
        "startDate": today,
        "endDate": next_week,
        "color": "#4CAF50"
    }
    
    # Send update task request
    response = requests.put(f"{BASE_URL}/tasks/{task_id}", json=data, headers=headers)
    print_response(response, "Update Task Response")
    
    # Check if update was successful
    if response.status_code == 200:
        print("Task update successful!")
        return True
    else:
        print("Task update failed!")
        return False

def test_delete_task(task_id):
    """Test task deletion endpoint"""
    global token
    
    if not task_id:
        print("No task ID provided for deletion")
        return False
    
    print(f"\nTesting Task Deletion for ID: {task_id}...")
    
    # Set auth header
    headers = {"Authorization": f"Bearer {token}"}
    
    # Send delete task request
    response = requests.delete(f"{BASE_URL}/tasks/{task_id}", headers=headers)
    print_response(response, "Delete Task Response")
    
    # Check if deletion was successful
    if response.status_code == 200:
        print("Task deletion successful!")
        return True
    else:
        print("Task deletion failed!")
        return False

def test_ai_task_edit():
    """Test AI-based task editing"""
    global token
    
    print("\nTesting AI Task Editing...")
    
    # Create a task first
    task_id = test_create_task()
    if not task_id:
        print("Failed to create task for AI editing")
        return False
    
    # Set auth header
    headers = {"Authorization": f"Bearer {token}"}
    
    # Send AI edit request
    data = {
        "query": f"Change the color of my test task to blue"
    }
    
    response = requests.post(f"{BASE_URL}/tasks/edit", json=data, headers=headers)
    print_response(response, "AI Edit Response")
    
    # Check if edit was successful
    if response.status_code == 200:
        print("AI task editing successful!")
        
        # Clean up - delete the task
        test_delete_task(task_id)
        return True
    else:
        print("AI task editing failed!")
        return False

def main():
    """Run all tasks tests"""
    
    # Login first
    if not login():
        sys.exit(1)
    
    # Test creating a task
    task_id = test_create_task()
    if not task_id:
        print("Task creation test failed")
        sys.exit(1)
    
    # Test getting tasks
    if not test_get_tasks():
        print("Task retrieval test failed")
        sys.exit(1)
    
    # Test updating a task
    if not test_update_task(task_id):
        print("Task update test failed")
        sys.exit(1)
    
    # Test AI task editing
    if not test_ai_task_edit():
        print("AI task editing test failed")
        # No exit here, continue with the remaining tests
    
    # Test deleting a task
    if not test_delete_task(task_id):
        print("Task deletion test failed")
        sys.exit(1)
    
    print("\nAll task tests completed successfully!")

if __name__ == "__main__":
    main() 