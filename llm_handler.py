# llm_handler.py

import os
import openai
import json
import re
from datetime import datetime, timedelta

def create_openai_client():
    """Create and return an OpenAI client with error handling."""
    try:
        print("\n=== Starting OpenAI Client Creation ===")
        print("Creating client with API key and base URL...")
        
        # Create the client without any additional parameters
        client = openai.OpenAI(
            api_key="47ab7e59-0359-4c41-8ad9-cd29b55553f8",
            base_url="https://api.sambanova.ai/v1"
        )
        
        print("Client created successfully, testing connection...")
        
        # Simple test message
        test_messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        try:
            print("Attempting test API call...")
            test_response = client.chat.completions.create(
                model='Meta-Llama-3.1-70B-Instruct',
                messages=test_messages,
                temperature=0.1,
                top_p=0.1
            )
            print("Test API call successful!")
            print("Response received:", test_response.choices[0].message.content)
            return client
            
        except Exception as api_error:
            print("\n=== API Test Error ===")
            print(f"Type: {type(api_error)}")
            print(f"Error: {str(api_error)}")
            print(f"Args: {api_error.args}")
            return None
            
    except Exception as e:
        print("\n=== Client Creation Error ===")
        print(f"Type: {type(e)}")
        print(f"Error: {str(e)}")
        print(f"Args: {e.args}")
        return None

# Global client variable with single initialization attempt
client = create_openai_client()
print(f"\nGlobal client initialized: {'Successfully' if client else 'Failed'}")

def parse_tasks_from_input(user_input, start_date=None):
    """Parse tasks from a given user input string."""
    if client is None:
        print("\n=== Client Not Available ===")
        return create_fallback_task("AI service unavailable - Please try again later")

    try:
        print(f"\n=== Processing User Input ===")
        print(f"Input: {user_input}")
        
        # Use provided start_date or today's date
        today = datetime.today().strftime('%Y-%m-%d')
        current_date = start_date or today
        
        # Calculate some common relative dates
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
        end_of_week = (current_dt + timedelta(days=(6 - current_dt.weekday()))).strftime('%Y-%m-%d')
        next_week = (current_dt + timedelta(days=7)).strftime('%Y-%m-%d')
        
        system_prompt = f"""
        You are a helpful assistant that parses calendar tasks from user input.
        
        TEMPORAL CONTEXT:
        - Today's date is: {start_date}
        - End of this week: {end_of_week}
        - Next week: {next_week}
        
        When parsing dates from the input:
        - Use {current_date} as the default start_date if no specific date is mentioned
        - For phrases like "end of the week", use {end_of_week}
        - For phrases like "next week", use {next_week} as the end date
        - For phrases like "tomorrow", add one day to {current_date}
        - For phrases mentioning specific days (e.g., "next Monday"), calculate relative to {current_date}

        Extract the following details and return them in JSON format:
        - description: The task description
        - start_date: The start date in YYYY-MM-DD format (default to {current_date} if not specified)
        - end_date: The end date in YYYY-MM-DD format (default to start_date if not specified)
        - color: A hex color code based on task type:
          * #ff4444 (red) for urgent/important tasks
          * #4CAF50 (green) for routine/regular tasks
          * #2196F3 (blue) for meetings/appointments
          * #FF9800 (orange) for deadlines/due dates
          * #9C27B0 (purple) for personal/leisure tasks
          * #3498db (default blue) for other tasks

        Return the response as a single JSON object, not an array.
        """

        try:
            print("Making API call for task parsing...")
            response = client.chat.completions.create(
                model='Meta-Llama-3.1-70B-Instruct',
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.1,
                top_p=0.1
            )
            llm_response = response.choices[0].message.content
            print("API Response:", llm_response)
            
            # Try to parse JSON from the response
            try:
                # First try direct JSON parsing
                parsed_response = json.loads(llm_response)
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON from text
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    try:
                        parsed_response = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        return create_fallback_task("Failed to parse AI response")
                else:
                    return create_fallback_task("No valid JSON found in AI response")

            today = datetime.today().strftime('%Y-%m-%d')
            task_details = {
                "description": parsed_response.get("description", "Untitled Task"),
                "start_date": parsed_response.get("start_date", today),
                "end_date": parsed_response.get("end_date", parsed_response.get("start_date", today)),
                "color": parsed_response.get("color", "#3498db"),
            }

            # Validate dates
            try:
                datetime.strptime(task_details["start_date"], "%Y-%m-%d")
                datetime.strptime(task_details["end_date"], "%Y-%m-%d")
            except ValueError:
                task_details["start_date"] = today
                task_details["end_date"] = today

            return task_details

        except Exception as e:
            print(f"Detailed API error: {str(e)}")
            return create_fallback_task(f"API Error: {str(e)}")

    except Exception as e:
        print(f"Error in parse_tasks_from_input: {str(e)}")
        return create_fallback_task(f"Task parsing failed: {str(e)}")

def create_fallback_task(error_message):
    """Create a fallback task when there's an error."""
    today = datetime.today().strftime('%Y-%m-%d')
    return {
        "description": f"Error: {error_message}",
        "start_date": today,
        "end_date": today,
        "color": "#dc3545"  # Red color for error
    }

def parse_user_input(user_input):
    """
    Parses freeform user input describing a task and returns the task details in JSON format.
    Parameters:
        user_input (str): The user's input describing a task.
    Returns:
        dict: A JSON-formatted dictionary containing the task details.
    """
    try:
        task_details = {
            "description": "",
            "start_date": None,
            "end_date": None,
            "color": "Blue"
        }

        # Extract the task description
        description_match = re.search(
            r"^(.+?)(?:\s*by\s*the\s*end\s*of\s*the\s*week|\s*by\s*|\s*until\s*|$)", 
            user_input, re.IGNORECASE
        )
        if description_match:
            task_details["description"] = description_match.group(1).strip()

        # Extract the due date
        date_match = re.search(
            r"\bby\s*the\s*end\s*of\s*the\s*week|\bby\s*|\buntil\s*(\d{4}-\d{2}-\d{2})", 
            user_input, re.IGNORECASE
        )
        if date_match:
            date_str = date_match.group(1) if date_match.group(1) else (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')
            task_details["end_date"] = date_str

        # If no end date is provided, set to one week from today
        if not task_details["end_date"]:
            task_details["end_date"] = (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Set start date to today if not specified
        if not task_details["start_date"]:
            task_details["start_date"] = datetime.today().strftime('%Y-%m-%d')

        return task_details
    except Exception as e:
        print(f"Error in parse_user_input: {str(e)}")
        return create_fallback_task(f"Input parsing failed: {str(e)}")

