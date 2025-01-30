# llm_handler.py

import os
import openai
import json
import re
from datetime import datetime, timedelta

def create_openai_client():
    """   Create and return an OpenAI client using the SambaNova API.
        - Handles potential errors during client creation or testing.
        - Performs a test API call to ensure the client is properly set up."""
    try:
        print("\n=== Starting OpenAI Client Creation ===")
        print("Creating client with API key and base URL...")
        
        # Initialize the OpenAI client with the specified API key and base URL
        client = openai.OpenAI(
            api_key="a491a5c1-ea8c-44c3-bd21-ca6aef6f5454", # API key for authentication
            base_url="https://api.sambanova.ai/v1"          # Base URL for the API endpoint
        )
        
        print("Client created successfully, testing connection...")
        
        # Send a test message to verify the client connection
        test_messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        try:
            print("Attempting test API call...")
            test_response = client.chat.completions.create(
                model='Meta-Llama-3.1-70B-Instruct',  # Specify the model being used
                messages=test_messages,               # Provide the input message(s)
                temperature=0.3,                      # Control response randomness
                top_p=0.3                             # Control response diversity
            )
            print("Test API call successful!")
            print("Response received:", test_response.choices[0].message.content)
            return client
            
        except Exception as api_error:
            # Log any errors encountered during the API test call
            print("\n=== API Test Error ===")
            print(f"Type: {type(api_error)}")
            print(f"Error: {str(api_error)}")
            print(f"Args: {api_error.args}")
            return None
            
    except Exception as e:
        # Log errors during client initialization
        print("\n=== Client Creation Error ===")
        print(f"Type: {type(e)}")
        print(f"Error: {str(e)}")
        print(f"Args: {e.args}")
        return None


# Global client variable to store the initialized OpenAI client
client = create_openai_client()
print(f"\nGlobal client initialized: {'Successfully' if client else 'Failed'}")


def parse_tasks_from_input(user_input, start_date=None):
    """
    Parse tasks from the user's input string and generate a structured response.
    - Makes an API call to the LLM to interpret the input.
    - Processes relative dates and task details for better context.
    
    Args:
        user_input (str): The user's natural language input.
        start_date (str): Required; the starting date in YYYY-MM-DD format.
    
    Returns:
        dict: Parsed task details or an error fallback.
    """
    if client is None:
        # Handle the case where the OpenAI client is unavailable
        print("\n=== Client Not Available ===")
        return create_fallback_task("AI service unavailable - Please try again later")

    try:
        print("\n=== Date Context Setup ===")
        # Get the true local date
        true_local_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        true_local_date_str = true_local_date.strftime('%Y-%m-%d')
        
        print(f"System local time: {datetime.now()}")
        print(f"True local date: {true_local_date_str}")
        print(f"Provided start_date parameter: {start_date}")
        
        # If user input mentions "today", always use true local date
        if "today" in user_input.lower():
            current_date = true_local_date_str
            print(f"User mentioned 'today', using true local date: {current_date}")
        else:
            # For explicit dates, use the provided start_date or true local date
            current_date = start_date or true_local_date_str
            print(f"Using date for prompt: {current_date}")
        
        # Validate that current_date is not accidentally set to tomorrow
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
        if current_dt.date() > true_local_date.date() and "today" in user_input.lower():
            print("Warning: Correcting future date back to today")
            current_date = true_local_date_str
        
        # Calculate relative dates using the local timezone
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
        end_of_week = (current_dt + timedelta(days=(6 - current_dt.weekday()))).strftime('%Y-%m-%d')
        next_week = (current_dt + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Modify the system prompt to be more explicit about date handling
        system_prompt = f"""
        You are a conversational assistant who helps with scheduling tasks and managing a calendar.
        
        IMPORTANT DATE HANDLING RULES:
        1. Today's exact date is: {current_date}
        2. When "today" is mentioned, ALWAYS use exactly {current_date}
        3. All dates must be in YYYY-MM-DD format
        4. Never adjust or shift dates unless explicitly requested
        5. For tasks without a specified date, use exactly {current_date}
        
        IMPORTANT DURATION HANDLING RULES:
        1. For tasks with explicit durations (e.g., "for the next 3 days"):
           - Set start_date to {current_date}
           - Calculate end_date by adding the duration to start_date
           Example: "for the next 3 days" → end_date = start_date + 3 days
        
        2. For tasks with deadlines (e.g., "by Friday", "by the end of the week"):
           - Set start_date to {current_date}
           - Set end_date to the deadline date
           Example: "by the end of the week" → end_date = {end_of_week}
        
        3. ALWAYS set both start_date AND end_date for duration-based tasks
        
        4. NEVER default end_date to start_date for tasks with duration keywords
        
        Current Context:
        - Today: {current_date}
        - End of week: {end_of_week}
        - Next week: {next_week}

        **How to interpret dates and durations:**
        - If no specific date is mentioned, use {start_date} as the default start date.
        - For phrases like "end of the week," use {end_of_week} as the end date.
        - For specific days like "next Monday," calculate the date based on {current_date}.
        - For tasks with a duration (e.g., "for 3 days" or "until Friday"):
            * Set start_date to the earliest date mentioned or {start_date}
            * Set end_date to the final date of the duration
            * Do NOT set recurrence unless explicitly requested

        **Recognize recurring patterns, such as:**
        - Daily, every other day, or weekly
        - Bi-weekly, monthly, or specific days (e.g., "every Monday")
        - Ordinal patterns (e.g., "every first Monday") or "last [day of week]"

        When processing a task, extract these details in JSON format:
        - **description**: A brief summary of the task  
        - **start_date**: YYYY-MM-DD (earliest date or default)
        - **end_date**: YYYY-MM-DD (latest date or same as start_date)  
        - **recurrence**: Exact phrasing from the list above (only if explicitly requested)  
        - **recurrence_end**: YYYY-MM-DD (only if recurrence specified)  
        - **color**: A hex color code based on task type:  
            - Urgent/important: #ff4444 (red)  
            - Routine: #4CAF50 (green)  
            - Meetings: #2196F3 (blue)  
            - Deadlines: #FF9800 (orange)  
            - Personal: #9C27B0 (purple)  
            - Other: #3498db (default blue)  

        **For multi-day tasks:**
        - Always set both start_date and end_date
        - Do not set recurrence unless explicitly requested
        - For phrases like "by Friday", set:
            * start_date to current date
            * end_date to the mentioned deadline
        - For phrases like "for the next 3 days", set:
            * start_date to current date
            * end_date to current date + duration

        Always respond with a single JSON object.
        """

        print("\n=== Making API Call ===")
        print(f"User input: {user_input}")
        
        try:
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
            print("\n=== Raw LLM Response ===")
            print(llm_response)
            
            # Parse JSON response
            try:
                parsed_response = json.loads(llm_response)
                print("\n=== Parsed JSON Response ===")
                print(json.dumps(parsed_response, indent=2))
            except json.JSONDecodeError as je:
                print(f"JSON parsing error: {je}")
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if not json_match:
                    raise ValueError("No JSON found in response")
                parsed_response = json.loads(json_match.group(0))
            
            # Build task details with explicit date logging
            local_today = true_local_date.strftime('%Y-%m-%d')
            print("\n=== Building Task Details ===")
            print(f"Local today: {local_today}")
            print(f"Response start_date: {parsed_response.get('start_date')}")
            print(f"Response end_date: {parsed_response.get('end_date')}")
            
            task_details = {
                "description": parsed_response.get("description", "Untitled Task"),
                "start_date": parsed_response.get("start_date", local_today),
                "end_date": parsed_response.get("end_date", parsed_response.get("start_date", local_today)),
                "color": parsed_response.get("color", "#3498db"),
                "recurrence": parsed_response.get("recurrence", None),
                "recurrence_end": parsed_response.get("recurrence_end", None),
                "group_id": str(datetime.now().timestamp())
            }
            
            print("\n=== Final Task Details ===")
            print(json.dumps(task_details, indent=2))
            
            # After getting LLM response, validate duration handling
            print("\n=== LLM Duration Response ===")
            print(f"Start date: {task_details['start_date']}")
            print(f"End date: {task_details['end_date']}")
            print(f"Duration spans multiple days: {task_details['start_date'] != task_details['end_date']}")
            
            return task_details
            
        except Exception as e:
            print(f"API or parsing error: {str(e)}")
            return create_fallback_task(str(e))
            
    except Exception as e:
        print(f"Overall error: {str(e)}")
        return create_fallback_task(str(e))

def create_fallback_task(error_message):
    """
    Create a fallback task object in case of an error.
    - Uses a default description and today's date.
    - Highlights the error with a red color code.
    """
    today = datetime.today().strftime('%Y-%m-%d')
    return {
        "description": f"Error: {error_message}",
        "start_date": today,
        "end_date": today,
        "color": "#dc3545",  # Red color for error
        "group_id": str(datetime.now().timestamp())  # Add group_id to fallback tasks too
    }

def parse_user_input(user_input):
    """
    Extract task details from freeform user input.
    - Uses regex to parse task descriptions and due dates.
    - Returns default values for incomplete inputs.
    
    Args:
        user_input (str): The user's natural language input.
    
    Returns:
        dict: A dictionary containing the parsed task details.
    """
    try:
        # Initialize a dictionary to store task details
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
            # Extract the task description using regex
            task_details["description"] = description_match.group(1).strip()

        # Extract the due date using regex
        date_match = re.search(
            r"\bby\s*the\s*end\s*of\s*the\s*week|\bby\s*|\buntil\s*(\d{4}-\d{2}-\d{2})", 
            user_input, re.IGNORECASE
        )
        if date_match:
            # Use the matched date or default to one week from today
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
        # Log errors during input parsing
        print(f"Error in parse_user_input: {str(e)}")
        return create_fallback_task(f"Input parsing failed: {str(e)}")

