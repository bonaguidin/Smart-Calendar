from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json
from llm_handler import parse_tasks_from_input, parse_edit_query, generate_conversational_response
from flask_cors import CORS
import traceback
import pytz
from timezone_handler import TimezoneHandler
from typing import Dict, List, Tuple, Optional
import logging
from schemas import TASK_SCHEMA, EDIT_SCHEMA
from json_validator import JSONSanitizer
from intent_detector import IntentDetector
import os
from dotenv import load_dotenv
import secrets
from flask_migrate import Migrate
import uuid

# Import new components
from database import db, init_db
from auth import auth_bp, token_required
from models import User, Task, UserPreference
from location_services import LocationServices

# Load environment variables
load_dotenv()

# Create the Flask app
app = Flask(__name__)

# Set application secret key for session and JWT
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Initialize database
init_db(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Configure CORS
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:5000", "*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
tz_handler = TimezoneHandler()
intent_detector = IntentDetector()
location_services = LocationServices()

# Register blueprints
app.register_blueprint(auth_bp)

# Legacy in-memory storage (for backward compatibility)
tasks = {}
task_history = {}

@app.route('/')
def index():
    # Show API status
    return jsonify({
        'status': 'online',
        'version': '1.1',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/tasks', methods=['GET'])
@token_required
def get_tasks(current_user):
    """
    Retrieve all tasks for the current user from the database.
    Returns tasks grouped by date for calendar display.
    
    Args:
        current_user: User object from token_required decorator
        
    Returns:
        JSON response with tasks grouped by date
    """
    try:
        logger.info(f"Retrieving tasks for user: {current_user.username}")
        
        # Get date range from query parameters (optional)
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Build query
        query = Task.query.filter_by(user_id=current_user.id)
        
        # Apply date filters if provided
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                query = query.filter(Task.start_date >= start_date)
            except ValueError:
                logger.warning(f"Invalid start_date format: {start_date_str}")
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                query = query.filter(Task.end_date <= end_date)
            except ValueError:
                logger.warning(f"Invalid end_date format: {end_date_str}")
        
        # Execute query and get all matching tasks
        db_tasks = query.all()
        logger.info(f"Found {len(db_tasks)} tasks")
        
        # Group tasks by date for calendar display
        result = {}
        for task in db_tasks:
            # Create instances for each day of multi-day tasks
            current_date = task.start_date
            while current_date <= task.end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                
                # Initialize date entry if it doesn't exist
                if date_str not in result:
                    result[date_str] = []
                
                # Calculate day info for multi-day tasks
                is_multi_day = task.start_date != task.end_date
                total_days = (task.end_date - task.start_date).days + 1
                day_number = (current_date - task.start_date).days + 1
                
                # Create instance for this date
                task_instance = task.to_dict()
                task_instance['instanceDate'] = date_str
                task_instance['isPartOfMultiDay'] = is_multi_day
                task_instance['dayNumber'] = day_number
                task_instance['totalDays'] = total_days
                
                result[date_str].append(task_instance)
                
                # Move to next day
                current_date += timedelta(days=1)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error retrieving tasks: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
@token_required
def add_task(current_user):
    """
    Create a new task in the database.
    
    Args:
        current_user: User object from token_required decorator
        
    Returns:
        JSON response with the created task
    """
    try:
        task_data = request.json
        logger.info(f"Received task data: {json.dumps(task_data, indent=2)}")
        
        # Handle both manual and AI-generated task formats
        start_date_str = task_data.get('startDate') or task_data.get('start_date')
        end_date_str = task_data.get('endDate') or task_data.get('end_date') or start_date_str
        
        if not start_date_str:
            return jsonify({'error': 'Start date is required'}), 400
            
        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError as e:
            logger.error(f"Date parsing error: {str(e)}")
            return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
        
        # Parse times if provided
        start_time = None
        end_time = None
        time_str = task_data.get('time')
        
        if time_str:
            try:
                start_time = datetime.strptime(time_str, '%H:%M').time()
                # Default end time is 1 hour after start if not provided
                end_time = datetime.strptime(time_str, '%H:%M').time()
                end_time = datetime.combine(datetime.today(), end_time)
                end_time = (end_time + timedelta(hours=1)).time()
            except ValueError:
                logger.warning(f"Could not parse time: {time_str}")
        
        # Create group ID for the task (used for recurring tasks and multi-day events)
        group_id = task_data.get('group_id', str(datetime.now().timestamp()))
        
        # Create the task in the database
        new_task = Task(
            user_id=current_user.id,
            uuid=str(uuid.uuid4()),
            group_id=group_id,
            title=task_data.get('title') or task_data.get('description', ''),
            description=task_data.get('description') or task_data.get('title', ''),
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            color=task_data.get('color', '#2196F3'),
            location=task_data.get('location'),
            is_part_of_multi_day=(start_date != end_date),
            day_number=1,
            total_days=(end_date - start_date).days + 1,
            recurrence_pattern=task_data.get('recurrence'),
            recurrence_end_date=datetime.strptime(task_data.get('recurrenceEnd'), '%Y-%m-%d').date() if task_data.get('recurrenceEnd') else None
        )
        
        # Add to database
        db.session.add(new_task)
        db.session.commit()
        
        logger.info(f"Successfully added task: {new_task.title} (ID: {new_task.uuid})")
        
        # Create task instance for response
        task_instance = new_task.to_dict()
        task_instance['instanceDate'] = start_date.strftime('%Y-%m-%d')
        
        return jsonify({'success': True, 'task': task_instance})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding task: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    
def find_relevant_task(user_query: str, tasks_dict: dict) -> tuple:
    """
    Find the most relevant task based on user's edit request.
    Uses task title, description, and dates to calculate relevance.
    
    Args:
        user_query (str): The user's edit request
        tasks_dict (dict): Dictionary of all tasks
        
    Returns:
        tuple: (most_relevant_task, task_date, relevance_score)
    """
    print("\n=== Finding Relevant Task ===")
    print(f"Query: {user_query}")
    
    # Extract key terms from the query
    query_terms = set(user_query.lower().split())
    
    # Remove common words that don't help with matching
    # Note: Keep action words like 'delete', 'remove', etc.
    stop_words = {'the', 'to', 'and', 'it', 'be', 'on', 'for', 'in', 'at', 'this', 'that', 'please', 'would', 'could'}
    query_terms = query_terms - stop_words
    
    print(f"Query terms: {query_terms}")
    
    best_match = None
    best_date = None
    highest_score = 0
    
    # Check if this is a delete request
    is_delete_request = any(word in query_terms for word in {'delete', 'remove', 'erase'})
    
    for date_str, date_tasks in tasks_dict.items():
        for task in date_tasks:
            score = 0
            task_terms = set(task['title'].lower().split())
            if 'description' in task and task['description']:
                task_terms.update(task['description'].lower().split())
            
            # Calculate term match score
            matching_terms = query_terms & task_terms
            score += len(matching_terms) * 2  # Weight term matches heavily
            
            # Boost score for exact substring matches
            if task['title'].lower() in user_query.lower():
                score += 5  # Higher boost for exact title match
            elif any(term in task['title'].lower() for term in query_terms):
                score += 3
            
            # Consider date proximity if dates are mentioned
            task_date = datetime.strptime(date_str, '%Y-%m-%d')
            current_date = datetime.now()
            days_diff = abs((task_date - current_date).days)
            if days_diff < 7:  # Boost score for recent tasks
                score += (7 - days_diff) * 0.5
            
            # For delete requests, boost score if task title is a close match
            if is_delete_request and task['title'].lower() in user_query.lower():
                score += 5
            
            print(f"Task: {task['title']}, Date: {date_str}, Score: {score}")
            
            if score > highest_score:
                highest_score = score
                best_match = task
                best_date = date_str
    
    # Lower the threshold for delete requests since they often have fewer matching terms
    min_score = 0.5 if is_delete_request else 1.0
    
    if best_match:
        print(f"\nBest match found:")
        print(f"Title: {best_match['title']}")
        print(f"Date: {best_date}")
        print(f"Score: {highest_score}")
    else:
        print("\nNo relevant task found")
    
    return best_match, best_date, highest_score

@app.route('/api/tasks/edit', methods=['POST'])
@token_required
def edit_task_with_ai(current_user):
    """
    Handle AI-based task editing requests using the database.
    
    Args:
        current_user: User object from token_required decorator
        
    Returns:
        JSON response with the edited task
    """
    try:
        logger.info("\n=== Processing AI Task Edit Request ===")
        data = request.json
        user_input = data.get('query')
        
        logger.info(f"User ID: {current_user.id}")
        logger.info(f"Edit query: {user_input}")
        
        # Get all user's tasks from the database
        user_tasks = Task.query.filter_by(user_id=current_user.id).all()
        
        if not user_tasks:
            logger.warning("No tasks found for user")
            return jsonify({
                'error': 'You do not have any tasks to edit.'
            }), 404
        
        # Convert tasks to a format that can be used by find_relevant_task
        # Create a dict grouped by date for compatibility
        tasks_dict = {}
        for task in user_tasks:
            # Create an entry for each day of multi-day tasks
            current_date = task.start_date
            while current_date <= task.end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                
                if date_str not in tasks_dict:
                    tasks_dict[date_str] = []
                
                # Create a dictionary representation that matches the expected format
                task_dict = {
                    'id': task.uuid,
                    'group_id': task.group_id,
                    'title': task.title,
                    'description': task.description,
                    'color': task.color,
                    'startDate': task.start_date.strftime('%Y-%m-%d'),
                    'endDate': task.end_date.strftime('%Y-%m-%d'),
                    'instanceDate': date_str,
                    'time': task.start_time.strftime('%H:%M') if task.start_time else '',
                    'isPartOfMultiDay': task.is_part_of_multi_day,
                    'dayNumber': (current_date - task.start_date).days + 1,
                    'totalDays': task.total_days
                }
                
                tasks_dict[date_str].append(task_dict)
                current_date += timedelta(days=1)
        
        # Find the most relevant task based on the query
        relevant_task, task_date, relevance_score = find_relevant_task(user_input, tasks_dict)
        
        if not relevant_task or relevance_score < 1:  # Minimum relevance threshold
            logger.warning("No sufficiently relevant task found")
            return jsonify({
                'error': 'Could not determine which task to edit. Please be more specific.'
            }), 404

        logger.info(f"\nSelected task to edit:")
        logger.info(f"Title: {relevant_task['title']}")
        logger.info(f"Date: {task_date}")
        logger.info(f"Group ID: {relevant_task['group_id']}")
        
        # Create context for edit
        today = datetime.now()
        edit_context = {
            'today': today.strftime('%Y-%m-%d'),
            'timezone': current_user.timezone
        }
        
        # Parse the edit request
        edit_instructions = parse_edit_query(
            user_input=user_input,
            original=relevant_task,
            context=edit_context
        )
        
        if not edit_instructions or "error" in edit_instructions:
            error_msg = edit_instructions.get("error", "Failed to parse edit request")
            logger.error(f"Edit parsing error: {error_msg}")
            return jsonify({'error': error_msg}), 500
        
        logger.info(f"\n=== Generated Edit Instructions ===")
        logger.info(json.dumps(edit_instructions, indent=2))
        
        # Find all tasks with this group_id that belong to the current user
        tasks_to_update = Task.query.filter_by(
            user_id=current_user.id,
            group_id=relevant_task['group_id']
        ).all()
        
        if not tasks_to_update:
            logger.warning(f"No tasks found with group_id: {relevant_task['group_id']}")
            return jsonify({'error': 'Task not found in database'}), 404
        
        # Apply the changes to the database records
        updated_task = None
        
        for task in tasks_to_update:
            # Apply each change from edit instructions
            for change in edit_instructions.get('operations', []):
                field = change.get('field')
                value = change.get('value')
                
                if field and value is not None:
                    logger.info(f"Applying change: {field} = {value}")
                    
                    # Map frontend field names to database model field names
                    field_mapping = {
                        'title': 'title',
                        'description': 'description',
                        'color': 'color',
                        'startDate': 'start_date',
                        'endDate': 'end_date',
                        'time': 'start_time',
                        'location': 'location'
                    }
                    
                    db_field = field_mapping.get(field)
                    if not db_field:
                        logger.warning(f"Unknown field: {field}")
                        continue
                    
                    # Handle special cases for date/time fields
                    if db_field == 'start_date' or db_field == 'end_date':
                        try:
                            date_value = datetime.strptime(value, '%Y-%m-%d').date()
                            setattr(task, db_field, date_value)
                        except ValueError:
                            logger.warning(f"Invalid date format: {value}")
                    elif db_field == 'start_time':
                        try:
                            time_value = datetime.strptime(value, '%H:%M').time()
                            setattr(task, db_field, time_value)
                        except ValueError:
                            logger.warning(f"Invalid time format: {value}")
                    else:
                        # For regular fields
                        setattr(task, db_field, value)
            
            # Update timestamp
            task.updated_at = datetime.utcnow()
            
            # Save the first task for response
            if not updated_task:
                updated_task = task
        
        # Commit the transaction
        db.session.commit()
        
        logger.info(f"Successfully updated {len(tasks_to_update)} task(s) with AI edit")
        
        # Convert updated task to dictionary for response
        response = updated_task.to_dict()
        
        return jsonify({
            'success': True,
            'task': response,
            'changes': edit_instructions.get('operations', []),
            'updated_count': len(tasks_to_update)
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in AI task editing: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def get_task_instances(task_id):
    """Find all instances of a task across dates"""
    instances = []
    found_dates = []
    for date_str, tasks_list in tasks.items():
        for task in tasks_list:
            if task['group_id'] == task_id:
                instances.append(task)
                found_dates.append(date_str)
    return (instances[0] if instances else None, found_dates)

def validate_task_changes(update_instructions):
    """Validate AI-generated changes"""
    errors = []
    for operation in update_instructions.get('operations', []):
        # Add validation logic for each field
        if operation['field'] == 'startDate':
            new_date = tz_handler.parse_date_string(operation['value'])
            if new_date < datetime.now(tz_handler.default_tz) - timedelta(days=1):
                errors.append('Cannot move tasks to the past')
        # Add more field validations
    return errors

def apply_task_update(original_task, update_instructions):
    """Apply validated changes to all task instances"""
    # Delete old instances
    delete_task_group(original_task['group_id'])
    
    # Create updated task
    updated_task = original_task.copy()
    for operation in update_instructions['operations']:
        updated_task[operation['field']] = operation['value']
    
    # Preserve original ID
    updated_task['group_id'] = original_task['group_id']
    
    # Re-add to storage
    if updated_task.get('recurrence'):
        create_recurring_instances(updated_task)
    else:
        start_date = tz_handler.parse_date_string(updated_task['startDate'])
        end_date = tz_handler.parse_date_string(updated_task['endDate'])
        current_date = start_date
        while current_date <= end_date:
            date_str = tz_handler.format_date_for_storage(current_date)
            tasks.setdefault(date_str, []).append(updated_task)
            current_date += timedelta(days=1)
    
    return updated_task

def create_recurring_instances(task):
    """Create instances of recurring tasks based on the recurrence pattern.
    
    Args:
        task: A Task model instance representing the base task
        
    Returns:
        List of created Task instances
    """
    logger.info(f"Creating recurring instances for task: {task.title} with pattern: {task.recurrence_pattern}")
    created_instances = []
    
    try:
        # Skip if no recurrence pattern
        if not task.recurrence_pattern:
            logger.warning("No recurrence pattern specified")
            return created_instances
        
        # Get start and end dates
        start_date = task.start_date
        end_date = task.end_date
        
        # Get or set recurrence end date (default: 3 months)
        recurrence_end = task.recurrence_end_date
        if not recurrence_end:
            recurrence_end = start_date + timedelta(days=90)  # Default: 3 months
            logger.info(f"No recurrence end date specified, defaulting to 3 months: {recurrence_end}")
        
        # Calculate the duration of the event in days
        duration = (end_date - start_date).days
        
        # Track current occurrence
        current_start = start_date
        
        # Create a list to store created instances
        created_instances = []
        
        # Generate occurrences until recurrence end date
        while current_start <= recurrence_end:
            # Skip the first occurrence as it matches the base task
            if current_start == start_date:
                # Calculate next occurrence based on recurrence pattern
                next_start = calculate_next_occurrence(current_start, task.recurrence_pattern)
                if not next_start:
                    break
                
                current_start = next_start
                continue
            
            # Calculate end date for this occurrence
            current_end = current_start + timedelta(days=duration)
            
            # Create a new instance for this occurrence
            new_instance = Task(
                user_id=task.user_id,
                uuid=str(uuid.uuid4()),
                group_id=task.group_id,
                title=task.title,
                description=task.description,
                start_date=current_start,
                end_date=current_end,
                start_time=task.start_time,
                end_time=task.end_time,
                color=task.color,
                location=task.location,
                recurrence_pattern=task.recurrence_pattern,
                recurrence_end_date=task.recurrence_end_date,
                is_part_of_multi_day=(current_start != current_end),
                day_number=1,
                total_days=(current_end - current_start).days + 1
            )
            
            # Add to our list of created instances
            created_instances.append(new_instance)
            logger.info(f"Created recurring instance: {new_instance.title} for {current_start}")
            
            # Calculate next occurrence based on recurrence pattern
            next_start = calculate_next_occurrence(current_start, task.recurrence_pattern)
            if not next_start:
                break
                
            current_start = next_start
        
        return created_instances
            
    except Exception as e:
        logger.error(f"Error creating recurring instances: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def calculate_next_occurrence(current_date, recurrence_pattern):
    """Calculate the next occurrence based on the recurrence pattern."""
    if not recurrence_pattern:
        return None
        
    pattern = recurrence_pattern.lower()
    
    if 'every day' in pattern:
        return current_date + timedelta(days=1)
    
    if 'every other day' in pattern:
        return current_date + timedelta(days=2)
    
    if 'every week' in pattern or 'weekly' in pattern:
        return current_date + timedelta(weeks=1)
    
    if 'every other week' in pattern:
        return current_date + timedelta(weeks=2)
    
    if 'every month' in pattern or 'monthly' in pattern:
        # Add one month
        if current_date.month == 12:
            return current_date.replace(year=current_date.year + 1, month=1)
        return current_date.replace(month=current_date.month + 1)
    
    # Handle specific days of the week
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for day in days:
        if f'every {day}' in pattern:
            next_date = current_date + timedelta(days=1)
            while next_date.strftime('%A').lower() != day:
                next_date += timedelta(days=1)
            return next_date
            
    # Handle "every third thursday" type patterns
    for ordinal in ['first', 'second', 'third', 'fourth', 'last']:
        for day in days:
            if f'every {ordinal} {day}' in pattern:
                return calculate_nth_weekday(current_date, day, ordinal)
    
    return None

def calculate_nth_weekday(current_date, weekday, ordinal):
    """Calculate the next nth weekday of the month."""
    # Move to the first day of next month
    if current_date.month == 12:
        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
    else:
        next_month = current_date.replace(month=current_date.month + 1, day=1)
    
    # Find the first occurrence of the weekday
    while next_month.strftime('%A').lower() != weekday.lower():
        next_month += timedelta(days=1)
    
    # Adjust based on ordinal
    if ordinal == 'last':
        # Keep going until we find the last occurrence in the month
        last_occurrence = next_month
        temp_date = next_month + timedelta(weeks=1)
        while temp_date.month == next_month.month:
            last_occurrence = temp_date
            temp_date += timedelta(weeks=1)
        return last_occurrence
    else:
        # Convert ordinal to number
        ordinal_map = {'first': 0, 'second': 1, 'third': 2, 'fourth': 3}
        weeks_to_add = ordinal_map.get(ordinal, 0)
        return next_month + timedelta(weeks=weeks_to_add)

@app.route('/api/parse-task', methods=['POST'])
def parse_task():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        user_input = data.get('input')
        if not user_input:
            return jsonify({'error': 'No input provided'}), 400

        # Get today's date from the server
        today = datetime.now(tz_handler.default_tz)
        start_date = today.strftime('%Y-%m-%d')
        
        logger.info(f"Processing input: {user_input}")
        
        # Detect user intent
        intent, confidence = intent_detector.detect_intent(user_input)
        logger.info(f"Detected intent: {intent} with confidence: {confidence}")
        
        # Handle conversational intent using the LLM
        if intent == 'conversational':
            logger.info("Routing to conversational response generator")
            # Generate AI response for conversational intent
            response = generate_conversational_response(user_input)
            logger.info(f"Conversational response generated with is_conversational={response.get('is_conversational', False)}")
            return jsonify(response)
        
        # For non-conversational intents (task creation, edits, inquiries)
        logger.info(f"Processing as task-related intent: {intent}")
        logger.debug(f"Using start date: {start_date}")

        # Parse the task using the LLM handler
        task_details = parse_tasks_from_input(user_input, start_date)
        logger.info(f"Task details generated: {json.dumps(task_details)[:200]}...")
        
        if not task_details:
            return jsonify({'error': 'Failed to parse task details'}), 500

        # If this is an edit request, handle it specially
        if task_details.get('is_edit_request'):
            logger.info("Processing as edit request")
            # Find relevant task based on user query
            matched_task, task_date, relevance_score = find_relevant_task(user_input, tasks)
            
            # Check if this is a delete request
            is_delete_request = any(word in user_input.lower() for word in {'delete', 'remove', 'erase'})
            min_score = 0.5 if is_delete_request else 1.0
            
            if not matched_task or relevance_score < min_score:
                logger.warning("No relevant task found for editing")
                return jsonify({
                    'error': 'Could not find a matching task to edit. Please be more specific.'
                }), 404
                
            logger.info(f"Found matching task: {matched_task['title']} on {task_date}")
            return jsonify({
                'is_edit_request': True,
                'matched_tasks': [matched_task],
                'original_input': user_input,
                'task_date': task_date
            })

        # For new tasks, format the response
        formatted_task = {
            'title': task_details.get('description', user_input),
            'description': task_details.get('description', user_input),
            'startDate': task_details.get('start_date', start_date),
            'endDate': task_details.get('end_date', start_date),
            'color': task_details.get('color', '#2196F3'),
            'time': '',
            'recurrence': task_details.get('recurrence', None),
            'recurrenceEnd': task_details.get('recurrence_end', None),
            'group_id': task_details.get('group_id', str(datetime.now().timestamp()))
        }
        
        logger.info(f"Formatted task response: {json.dumps(formatted_task, indent=2)}")
        return jsonify(formatted_task)
        
    except Exception as e:
        logger.error(f"Error in parse_task endpoint: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

def find_task_by_group_id(group_id: str) -> Tuple[Optional[dict], List[str]]:
    """
    Find all instances of a task across all dates.
    
    Args:
        group_id: The group ID to search for
        
    Returns:
        Tuple containing:
        - The task data if found, None otherwise
        - List of dates where the task appears
    """
    task_instances = []
    dates_found = []
    
    for date_str, date_tasks in tasks.items():
        for task in date_tasks:
            if str(task['group_id']) == str(group_id):
                task_instances.append(task)
                dates_found.append(date_str)
                
    return (task_instances[0] if task_instances else None, dates_found)

def update_task_instances(
    group_id: str,
    updated_data: dict,
    old_dates: List[str],
    new_dates: List[str]
) -> bool:
    """
    Update all instances of a task atomically.
    
    Args:
        group_id: Task group ID
        updated_data: New task data
        old_dates: Original dates where task appears
        new_dates: New dates where task should appear
        
    Returns:
        bool: Success status
    """
    try:
        # Store original state for rollback
        original_state = {
            date: tasks[date].copy() if date in tasks else []
            for date in set(old_dates + new_dates)
        }
        
        # Remove task from old dates
        for date in old_dates:
            if date in tasks:
                tasks[date] = [t for t in tasks[date] if str(t['group_id']) != str(group_id)]
                if not tasks[date]:
                    del tasks[date]
        
        # Add updated task to new dates
        for date in new_dates:
            if date not in tasks:
                tasks[date] = []
            
            # Create task instance for this date
            task_instance = {
                **updated_data,
                'instanceDate': date,
                'isPartOfMultiDay': len(new_dates) > 1,
                'dayNumber': new_dates.index(date) + 1,
                'totalDays': len(new_dates)
            }
            tasks[date].append(task_instance)
        
        return True
        
    except Exception as e:
        # Rollback on error
        logger.error(f"Error updating task: {str(e)}")
        for date, state in original_state.items():
            tasks[date] = state
        return False

@app.route('/api/tasks/<group_id>', methods=['PUT'])
@token_required
def update_task(current_user, group_id):
    """
    Update a task or task group in the database.
    
    Args:
        current_user: User object from token_required decorator
        group_id: Group ID of the task(s) to update
        
    Returns:
        JSON response with the updated task
    """
    try:
        logger.info(f"Updating task with group_id: {group_id}")
        task_data = request.json
        
        # Find all tasks with this group_id that belong to the current user
        tasks_to_update = Task.query.filter_by(
            user_id=current_user.id,
            group_id=group_id
        ).all()
        
        if not tasks_to_update:
            logger.warning(f"No tasks found with group_id: {group_id}")
            return jsonify({'error': 'Task not found'}), 404
        
        # Extract update fields
        updates = {}
        if 'title' in task_data:
            updates['title'] = task_data['title']
        if 'description' in task_data:
            updates['description'] = task_data['description']
        if 'color' in task_data:
            updates['color'] = task_data['color']
        if 'location' in task_data:
            updates['location'] = task_data['location']
        
        # Handle date updates
        start_date = None
        end_date = None
        
        if 'startDate' in task_data or 'start_date' in task_data:
            start_date_str = task_data.get('startDate') or task_data.get('start_date')
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                updates['start_date'] = start_date
            except ValueError:
                logger.warning(f"Invalid start date format: {start_date_str}")
        
        if 'endDate' in task_data or 'end_date' in task_data:
            end_date_str = task_data.get('endDate') or task_data.get('end_date')
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                updates['end_date'] = end_date
            except ValueError:
                logger.warning(f"Invalid end date format: {end_date_str}")
        
        # Handle time updates
        if 'startTime' in task_data or 'start_time' in task_data:
            time_str = task_data.get('startTime') or task_data.get('start_time')
            if time_str:
                try:
                    start_time = datetime.strptime(time_str, '%H:%M').time()
                    updates['start_time'] = start_time
                except ValueError:
                    logger.warning(f"Invalid start time format: {time_str}")
        
        if 'endTime' in task_data or 'end_time' in task_data:
            time_str = task_data.get('endTime') or task_data.get('end_time')
            if time_str:
                try:
                    end_time = datetime.strptime(time_str, '%H:%M').time()
                    updates['end_time'] = end_time
                except ValueError:
                    logger.warning(f"Invalid end time format: {time_str}")
        
        # Update multi-day properties if dates changed
        if start_date and end_date:
            updates['is_part_of_multi_day'] = (start_date != end_date)
            updates['total_days'] = (end_date - start_date).days + 1
        
        # Apply updates to all tasks in the group
        for task in tasks_to_update:
            for field, value in updates.items():
                setattr(task, field, value)
            
            # Update timestamp
            task.updated_at = datetime.utcnow()
        
        # Commit changes
        db.session.commit()
        
        # Get the first task for response
        updated_task = tasks_to_update[0]
        logger.info(f"Successfully updated task: {updated_task.title} (ID: {updated_task.uuid})")
        
        # Create response
        response = updated_task.to_dict()
        
        return jsonify({'success': True, 'task': response})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating task: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Mark the old endpoint as deprecated
@app.route('/api/tasks/<date>/<group_id>', methods=['PUT'])
def update_task_legacy(date, group_id):
    """
    DEPRECATED: Use /api/tasks/<group_id> instead.
    This endpoint will be removed in a future version.
    """
    logger.warning("Using deprecated update endpoint")
    return update_task(group_id)

# Modified delete function to preserve history 
@app.route('/api/tasks/<group_id>', methods=['DELETE'])
@token_required
def delete_task(current_user, group_id):
    """
    Delete a task or task group from the database.
    
    Args:
        current_user: User object from token_required decorator
        group_id: Group ID of the task(s) to delete
        
    Returns:
        JSON response indicating success or error
    """
    try:
        logger.info(f"Deleting task with group_id: {group_id}")
        
        # Find all tasks with this group_id that belong to the current user
        tasks_to_delete = Task.query.filter_by(
            user_id=current_user.id,
            group_id=group_id
        ).all()
        
        if not tasks_to_delete:
            logger.warning(f"No tasks found with group_id: {group_id}")
            return jsonify({'error': 'Task not found'}), 404
        
        # Count how many tasks we're deleting
        count = len(tasks_to_delete)
        
        # Delete all instances
        for task in tasks_to_delete:
            db.session.delete(task)
        
        # Commit the transaction
        db.session.commit()
        
        logger.info(f"Successfully deleted {count} task(s) with group_id: {group_id}")
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {count} task(s)',
            'deleted_count': count
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting task: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Add version history endpoint
@app.route('/api/tasks/history/<group_id>', methods=['GET'])
def get_task_history(group_id):
    return jsonify({
        'history': task_history.get(group_id, []),
        'current': get_task_instances(group_id)[0]
    })

@app.route('/api/confirm-task', methods=['POST'])
@token_required
def confirm_task(current_user):
    """
    Confirm and save a task to the database after user approval.
    
    Args:
        current_user: User object from token_required decorator
        
    Returns:
        JSON response with the created task
    """
    try:
        task_data = request.json
        if not task_data:
            return jsonify({'error': 'No task data received'}), 400

        # Validate required fields
        required_fields = ['title', 'startDate']
        for field in required_fields:
            if field not in task_data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Parse start and end dates
        start_date_str = task_data['startDate']
        end_date_str = task_data.get('endDate', start_date_str)
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError as e:
            logger.error(f"Date parsing error: {str(e)}")
            return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
        
        # Parse time if provided
        start_time = None
        end_time = None
        time_str = task_data.get('time')
        
        if time_str:
            try:
                start_time = datetime.strptime(time_str, '%H:%M').time()
                # Default end time is 1 hour after start
                end_time = datetime.combine(datetime.today(), start_time)
                end_time = (end_time + timedelta(hours=1)).time()
            except ValueError:
                logger.warning(f"Could not parse time: {time_str}")
        
        # Create group ID for the task
        group_id = task_data.get('group_id', str(datetime.now().timestamp()))
        
        # Handle recurring tasks
        recurrence_pattern = task_data.get('recurrence')
        recurrence_end_date = None
        
        if task_data.get('recurrenceEnd'):
            try:
                recurrence_end_date = datetime.strptime(task_data['recurrenceEnd'], '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f"Invalid recurrence end date: {task_data['recurrenceEnd']}")
        
        # Create base task
        new_task = Task(
            user_id=current_user.id,
            uuid=str(uuid.uuid4()),
            group_id=group_id,
            title=task_data['title'],
            description=task_data.get('description', ''),
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            color=task_data.get('color', '#2196F3'),
            location=task_data.get('location'),
            is_part_of_multi_day=(start_date != end_date),
            day_number=1,
            total_days=(end_date - start_date).days + 1,
            recurrence_pattern=recurrence_pattern,
            recurrence_end_date=recurrence_end_date
        )
        
        # Add the base task to the database
        db.session.add(new_task)
        
        # Handle recurring tasks - create instances
        if recurrence_pattern:
            instances = create_recurring_instances(new_task)
            # Add all instances to the database
            for instance in instances:
                db.session.add(instance)
        
        # Commit the transaction
        db.session.commit()
        
        # Create response
        task_instance = new_task.to_dict()
        task_instance['instanceDate'] = start_date.strftime('%Y-%m-%d')
        
        logger.info(f"Task confirmed and saved to database: {new_task.title} (ID: {new_task.uuid})")
        return jsonify({'success': True, 'task': task_instance})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error confirming task: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Add error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

# Add location-based API endpoints
@app.route('/api/weather', methods=['GET'])
@token_required
def get_weather(current_user):
    """Get weather data for a location."""
    try:
        # Get location parameter
        location = request.args.get('location')
        days = request.args.get('days', 5, type=int)
        
        if not location:
            # Use user's saved location if available
            if current_user.location:
                location = current_user.location
            else:
                return jsonify({'error': 'No location provided'}), 400
                
        # Get weather forecast
        weather_data = location_services.get_weather_forecast(location, days)
        
        if not weather_data:
            return jsonify({'error': 'Could not retrieve weather data'}), 404
            
        return jsonify(weather_data)
        
    except Exception as e:
        logger.error(f"Weather API error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/traffic', methods=['GET'])
@token_required
def get_traffic(current_user):
    """Get traffic data between two locations."""
    try:
        # Get origin and destination
        origin = request.args.get('origin')
        destination = request.args.get('destination')
        
        if not origin or not destination:
            return jsonify({'error': 'Origin and destination are required'}), 400
            
        # Get traffic estimate
        traffic_data = location_services.get_traffic_estimate(origin, destination)
        
        if not traffic_data:
            return jsonify({'error': 'Could not retrieve traffic data'}), 404
            
        return jsonify(traffic_data)
        
    except Exception as e:
        logger.error(f"Traffic API error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/location/search', methods=['GET'])
@token_required
def search_location(current_user):
    """Search for a location and get geocoding data."""
    try:
        # Get query parameter
        query = request.args.get('q')
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
            
        # Get location data
        location_data = location_services.geocode_location(query)
        
        if not location_data:
            return jsonify({'error': 'Location not found'}), 404
            
        return jsonify(location_data)
        
    except Exception as e:
        logger.error(f"Location search error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Add task location endpoint
@app.route('/api/tasks/<task_id>/location', methods=['GET'])
@token_required
def get_task_location_data(current_user, task_id):
    """Get location-based data for a task."""
    try:
        # Find task by UUID
        task = Task.query.filter_by(uuid=task_id, user_id=current_user.id).first()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
            
        if not task.location:
            return jsonify({'error': 'Task has no location'}), 400
            
        # Get date of task
        task_date = task.start_date
        if not task_date:
            task_date = datetime.now().date()
            
        # Get weather forecast for task location
        weather_data = location_services.get_weather_forecast(task.location)
        
        # Get traffic estimate if user has a location
        traffic_data = None
        if current_user.location and task.location:
            traffic_data = location_services.get_traffic_estimate(
                current_user.location, 
                task.location
            )
            
        return jsonify({
            'task_id': task_id,
            'location': task.location,
            'weather': weather_data,
            'traffic': traffic_data
        })
        
    except Exception as e:
        logger.error(f"Task location data error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Add a route to update user preferences for location features
@app.route('/api/preferences/location', methods=['PUT'])
@token_required
def update_location_preferences(current_user):
    """Update user preferences for location-based features."""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Get user preferences
        preferences = current_user.preferences
        if not preferences:
            preferences = UserPreference(user=current_user)
            db.session.add(preferences)
            
        # Update location preferences
        if 'weather_enabled' in data:
            preferences.weather_enabled = data['weather_enabled']
            
        if 'traffic_enabled' in data:
            preferences.traffic_enabled = data['traffic_enabled']
            
        # Update user location if provided
        if 'location' in data:
            current_user.location = data['location']
            
        # Save changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'preferences': preferences.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Update location preferences error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/clear-all', methods=['DELETE'])
@token_required
def clear_all_tasks(current_user):
    """
    Clear all tasks for the current user.
    
    Args:
        current_user: User object from token_required decorator
        
    Returns:
        JSON response with success/error message
    """
    try:
        logger.info(f"Clearing all tasks for user: {current_user.username}")
        
        # Using SQLAlchemy to delete all tasks for this user
        task_count = Task.query.filter_by(user_id=current_user.id).count()
        Task.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        logger.info(f"Successfully deleted {task_count} tasks for user: {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully cleared {task_count} tasks',
            'deleted_count': task_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing tasks for user {current_user.username}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error clearing tasks: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Run the Flask app on all interfaces (not just localhost)
    logger.info("Starting Flask server on 0.0.0.0:5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)