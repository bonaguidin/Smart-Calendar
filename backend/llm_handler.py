# llm_handler.py

import os
import openai
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
import traceback
from json_validator import JSONSanitizer
from schemas import TASK_SCHEMA, EDIT_SCHEMA
import logging
from timezone_handler import TimezoneHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize timezone handler
tz_handler = TimezoneHandler()

def create_openai_client():
    """Create and return an OpenAI client using the SambaNova API."""
    try:
        logger.info("Creating OpenAI client with SambaNova configuration")
        client = openai.OpenAI(
            api_key="94b96a77-df5b-4135-9447-5a593812cf07",
            base_url="https://api.sambanova.ai/v1"
        )
        
        # Test the client
        test_response = client.chat.completions.create(
            model='Meta-Llama-3.2-1B-Instruct',
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.9,
            top_p=0.9
        )
        
        logger.info("OpenAI client created and tested successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {str(e)}")
        return None

# Initialize global client
client = create_openai_client()
logger.info(f"Global client initialized: {'Successfully' if client else 'Failed'}")

def generate_structured_response(prompt_template: str, schema: dict, context: dict = None) -> Union[dict, None]:
    """
    Generate a structured JSON response based on a prompt template.
    
    Args:
        prompt_template (str): The template for the system prompt
        schema (dict): JSON schema for validation
        context (dict, optional): Context information for logging
    
    Returns:
        Union[dict, None]: Structured response or None if generation fails
    """
    if context is None:
        context = {}
        
    sanitizer = JSONSanitizer()
    
    try:
        # Log minimally to reduce overhead
        logger.info(f"Generating structured response for: {context.get('operation', 'unknown')}")
        
        # Use a more efficient version of the response generation
        response = client.chat.completions.create(
            model='Meta-Llama-3.1-70B-Instruct',
            messages=[{"role": "system", "content": prompt_template}],
            temperature=0.2,
            max_tokens=400,
            response_format={"type": "json_object"}  # Request JSON directly from the API
        )
        
        if not response or not response.choices or not response.choices[0].message:
            logger.warning("Empty response from LLM")
            return None
            
        content = response.choices[0].message.content
        
        # Try to parse the response as JSON
        try:
            # Parse the content
            parsed_json = json.loads(content)
            
            # Validate against schema
            is_valid = sanitizer.validate_data(parsed_json, schema)
            
            if is_valid:
                return parsed_json
            else:
                logger.warning("Response failed schema validation")
                return {"error": "Generated response failed validation"}
                
        except json.JSONDecodeError:
            logger.warning("Failed to parse response as JSON")
            
            # Try extracting JSON from text as fallback
            extracted = sanitizer.extract_json(content)
            if extracted:
                # Validate the extracted JSON
                is_valid = sanitizer.validate_data(extracted, schema)
                if is_valid:
                    return extracted
            
            return {"error": "Could not parse response as valid JSON"}
            
    except Exception as e:
        logger.error(f"Error in generate_structured_response: {str(e)}")
        return {"error": str(e)}

def handle_edit_flow(user_input: str) -> dict:
    """
    Handle edit request flow with proper error handling and response formatting.
    
    Args:
        user_input (str): The user's edit request
        
    Returns:
        dict: Structured edit request data
    """
    logger.info("Handling edit request flow")
    
    # Create basic edit request structure
    edit_request = {
        "is_edit_request": True,
        "original_input": user_input,
        "description": user_input  # Preserve original input for error cases
    }
    
    return edit_request

def parse_user_input(user_input: str, start_date: str) -> dict:
    """
    Extract task details from freeform user input using regex patterns.
    
    Args:
        user_input (str): The user's natural language input.
        start_date (str): The default start date (today) in YYYY-MM-DD format.
    
    Returns:
        dict: A dictionary containing the parsed task details.
    """
    try:
        # Initialize task details with default values
        task_details = {
            "description": user_input,
            "start_date": start_date,
            "end_date": start_date,
            "color": "#2196F3",
            "response_type": "confirmation",
            "ai_message": f"I've scheduled \"{user_input}\" for today.",
            "follow_up_questions": [
                "Would you like to add more details?",
                "Should I set a reminder for this task?"
            ],
            "suggestions": ["Add details", "Set reminder"]
        }

        # Check for color mentions
        color_map = {
            'red': '#F44336',
            'blue': '#2196F3',
            'green': '#4CAF50',
            'purple': '#9C27B0',
            'orange': '#FF9800',
            'teal': '#009688',
            'pink': '#E91E63'
        }
        for color_name, hex_code in color_map.items():
            if re.search(r'\b' + color_name + r'\b', user_input.lower()):
                task_details["color"] = hex_code
                break

        # Extract common date patterns
        today = datetime.strptime(start_date, '%Y-%m-%d')
        
        # Check for "tomorrow"
        if re.search(r'\btomorrow\b', user_input, re.IGNORECASE):
            tomorrow = today + timedelta(days=1)
            task_details["start_date"] = tomorrow.strftime('%Y-%m-%d')
            task_details["end_date"] = tomorrow.strftime('%Y-%m-%d')
            task_details["ai_message"] = f"I've scheduled \"{task_details['description']}\" for tomorrow."
        
        # Check for "next week"
        elif re.search(r'\bnext\s+week\b', user_input, re.IGNORECASE):
            next_week = today + timedelta(days=7)
            task_details["start_date"] = next_week.strftime('%Y-%m-%d')
            task_details["end_date"] = next_week.strftime('%Y-%m-%d')
            task_details["ai_message"] = f"I've scheduled \"{task_details['description']}\" for next week."
        
        # Check for day of week (e.g., "on Monday")
        days_of_week = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
                        'friday': 4, 'saturday': 5, 'sunday': 6}
        for day, day_num in days_of_week.items():
            if re.search(r'\b' + day + r'\b', user_input, re.IGNORECASE):
                # Calculate days to add
                current_day_num = today.weekday()
                days_to_add = (day_num - current_day_num) % 7
                if days_to_add == 0:
                    days_to_add = 7  # If it's the same day, assume next week
                
                target_date = today + timedelta(days=days_to_add)
                task_details["start_date"] = target_date.strftime('%Y-%m-%d')
                task_details["end_date"] = target_date.strftime('%Y-%m-%d')
                task_details["ai_message"] = f"I've scheduled \"{task_details['description']}\" for {day.capitalize()}."
                break
        
        # Extract task description - remove date and time references
        description = user_input
        date_patterns = [
            r'\btomorrow\b',
            r'\bnext\s+week\b',
            r'\bon\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\btoday\b',
            r'\bthis\s+(?:morning|afternoon|evening)\b',
            r'\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b'
        ]
        
        for pattern in date_patterns:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        
        # Common task action verbs to clean up
        task_verbs = [
            r'^(?:please\s+)?(?:schedule|add|create|set\s+up|remind\s+me\s+to|remind\s+me\s+about)\s+',
            r'^(?:i\s+need\s+to|i\s+want\s+to|i\s+have\s+to)\s+'
        ]
        
        for pattern in task_verbs:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        
        # Clean up extra whitespace and store cleaned description
        description = re.sub(r'\s+', ' ', description).strip()
        if description:
            task_details["description"] = description

        # Check if this looks like a simple task (has date pattern and task description)
        is_simple_task = any(re.search(pattern, user_input, re.IGNORECASE) for pattern in date_patterns)
        
        return task_details, is_simple_task
        
    except Exception as e:
        logger.error(f"Error in parse_user_input: {str(e)}")
        return create_fallback_task(f"Input parsing failed: {str(e)}"), False

def parse_tasks_from_input(user_input: str, start_date: str) -> dict:
    """
    Parse natural language input into structured task data with dynamic responses.
    Uses a hybrid approach - local parsing for simple tasks, LLM for complex ones.
    
    Args:
        user_input: User's natural language request
        start_date: Default start date in YYYY-MM-DD format
        
    Returns:
        dict: Structured task data or edit request with dynamic response
    """
    try:
        # First check if this is an edit request
        if is_edit_request(user_input):
            logger.info("=== Detected Edit Request ===")
            return handle_edit_flow(user_input)
        
        # Try local parsing first for simple cases
        task_details, is_simple_task = parse_user_input(user_input, start_date)
        
        # If it's a simple task that our parser can handle, return it directly
        if is_simple_task:
            logger.info("Using local parser for simple task")
            return task_details
        
        # For more complex tasks, use the LLM
        logger.info("Using LLM for complex task parsing")
        
        # Simplified prompt with just the essential information
        prompt = f"""Create a calendar task from this input. Return ONLY valid JSON with:
        - description: task description
        - start_date: YYYY-MM-DD
        - end_date: YYYY-MM-DD
        - color: #hex_color
        - ai_message: brief response confirming the task
        Today is {start_date}.
        
        User Input: {user_input}"""
        
        response = generate_structured_response(
            prompt_template=prompt,
            schema=TASK_SCHEMA,
            context={"operation": "create_task", "input": user_input}
        )
        
        # Handle None response
        if not response:
            logger.warning("No response from LLM, using locally parsed task")
            return task_details
            
        # Handle error response
        if "error" in response:
            logger.warning(f"Error in LLM response: {response['error']}, using locally parsed task")
            return task_details
            
        # Ensure all required fields are present with proper names
        if "startDate" in response:
            response["start_date"] = response.pop("startDate")
        if "endDate" in response:
            response["end_date"] = response.pop("endDate")
        
        # Add dynamic response fields if not present
        if "response_type" not in response:
            response["response_type"] = "confirmation"
        if "ai_message" not in response:
            response["ai_message"] = f"I've scheduled \"{response['description']}\" for {response['start_date']}"
        if "follow_up_questions" not in response:
            response["follow_up_questions"] = [
                "Would you like to add more details?",
                "Should I set a reminder?",
                "Would you like to make this a recurring task?"
            ]
        if "suggestions" not in response:
            response["suggestions"] = ["Add details", "Set reminder", "Make recurring"]
            
        # Ensure dates are present
        if "start_date" not in response:
            response["start_date"] = start_date
        if "end_date" not in response:
            response["end_date"] = response["start_date"]
            
        return response
        
    except Exception as e:
        logger.error(f"Error parsing task input: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a simple fallback task using our local parser
        fallback_task, _ = parse_user_input(user_input, start_date)
        fallback_task["ai_message"] = "I encountered an error but created a basic task for you."
        return fallback_task

def parse_edit_query(user_input: str, original: dict, context: dict) -> dict:
    """
    Parse a natural language edit request into structured operations.
    
    Args:
        user_input (str): User's natural language edit request
        original (dict): Original task data to be edited
        context (dict): Context data including today's date and timezone
        
    Returns:
        dict: Dict containing structured edit operations or error object
    """
    try:
        # Create a streamlined prompt with just essential information
        prompt = f"""
        TASK EDIT PROTOCOL
        Original task: {json.dumps(original)}
        Today's date: {context.get('today', 'Not specified')}
        User edit request: {user_input}
        
        Return a JSON object with these fields:
        - operations: array of changes to make
        - ai_message: confirmation message
        
        Each operation needs:
        - field: field to change (description/start_date/end_date/color)
        - operation: set
        - value: new value
        
        All dates must be in YYYY-MM-DD format.
        """
        
        response = generate_structured_response(
            prompt_template=prompt,
            schema=EDIT_SCHEMA,
            context={"operation": "edit_task", "input": user_input}
        )
        
        if not response:
            logger.warning("No response from LLM for edit query")
            return {
                "error": "Failed to parse edit request",
                "ai_message": "I couldn't understand how to edit your task. Could you try again with different wording?"
            }
            
        return response
        
    except Exception as e:
        logger.error(f"Error parsing edit query: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "error": f"Failed to parse edit request: {str(e)}",
            "ai_message": "I encountered an error while trying to update your task. Could you try again?"
        }

def create_fallback_task(error_message: str) -> dict:
    """Create a fallback task object for error cases."""
    today = datetime.today().strftime('%Y-%m-%d')
    return {
        "description": f"Error: {error_message}",
        "start_date": today,
        "end_date": today,
        "color": "#dc3545",
        "group_id": str(datetime.now().timestamp())
    }

def is_edit_request(user_input: str) -> bool:
    """
    Detect if the user input is requesting to edit an existing task.
    
    Args:
        user_input (str): The user's natural language input
        
    Returns:
        bool: True if this is an edit request, False otherwise
    """
    # List of words/phrases that indicate an edit request
    edit_indicators = [
        'change', 'edit', 'modify', 'update', 'move', 'reschedule',
        'switch', 'shift', 'postpone', 'delay'
    ]
    
    # Convert input to lowercase for case-insensitive matching
    input_lower = user_input.lower()
    
    # Special case for "make it" - only consider it an edit if it's not part of a new task creation
    if "make it" in input_lower and not input_lower.startswith(("add", "create", "schedule", "new")):
        return True
    
    # Check if any edit indicators are present and the input doesn't start with task creation words
    return any(indicator in input_lower for indicator in edit_indicators) and \
           not input_lower.startswith(("add", "create", "schedule", "new"))

def generate_conversational_response(user_input: str) -> Dict[str, Any]:
    """
    Generate a natural language response to user input using LLM.
    
    Args:
        user_input (str): The user's query or message
        
    Returns:
        Dict[str, Any]: Response containing ai_message and other fields
    """
    try:
        # Create a simple, concise prompt that maintains core functionality
        prompt = f"""You are a helpful calendar assistant. Be concise but friendly.
        Respond to: {user_input}
        
        Return your response as plain text without any JSON formatting.
        """
        
        logger.info("Generating conversational response")
        
        response = client.chat.completions.create(
            model='Meta-Llama-3.1-70B-Instruct',
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
            max_tokens=250
        )
        
        # Extract the response content
        if response and response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            
            # Return with is_conversational flag 
            return {
                "is_conversational": True,
                "ai_message": content,
                "success": True,
                "suggestions": ["Add task", "View calendar", "Help"]
            }
        
        # Fallback if no response
        return {
            "is_conversational": True,
            "ai_message": "I'm here to help with your calendar. What would you like to do?",
            "suggestions": ["Add task", "View calendar", "Help"],
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error generating conversational response: {str(e)}")
        return {
            "is_conversational": True,
            "ai_message": "I'm sorry, I encountered an error. How can I assist you with your calendar?",
            "suggestions": ["Add task", "View calendar", "Help"],
            "error": str(e)
        }

