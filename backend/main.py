from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json
from llm_handler import parse_tasks_from_input
from flask_cors import CORS
import traceback

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"]
    }
})

# In-memory storage for tasks (in production, you'd use a database)
tasks = {}

@app.route('/')
def index():
    # Instead of rendering template, return API status
    return jsonify({
        'status': 'online',
        'version': '1.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    try:
        task = request.json
        print("\n=== Task Duration Processing ===")
        print(f"Raw task data: {json.dumps(task, indent=2)}")
        
        # Parse start and end dates
        start_date = datetime.strptime(task['startDate'], '%Y-%m-%d')
        end_date = datetime.strptime(task.get('endDate', task['startDate']), '%Y-%m-%d')
        duration_days = (end_date - start_date).days + 1
        
        print(f"\n=== Task Duration Info ===")
        print(f"Start date: {start_date.strftime('%Y-%m-%d')}")
        print(f"End date: {end_date.strftime('%Y-%m-%d')}")
        print(f"Duration: {duration_days} days")
        
        # Initialize task storage if needed
        created_dates = []
        
        # Create instances for each day in the duration
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            created_dates.append(date_str)
            
            print(f"\nProcessing date: {date_str}")
            
            # Initialize the tasks list for this date if it doesn't exist
            if date_str not in tasks:
                tasks[date_str] = []
                print(f"Initialized task list for {date_str}")
            
            # Create the task instance for this date
            task_instance = {
                'group_id': task.get('group_id', str(datetime.now().timestamp())),
                'title': task['title'],
                'description': task.get('description', ''),
                'time': task.get('time', ''),
                'color': task.get('color', '#007bff'),
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'instanceDate': date_str,  # Add the specific date for this instance
                'isPartOfMultiDay': duration_days > 1,  # Flag for multi-day tasks
                'dayNumber': (current_date - start_date).days + 1,  # Which day in the sequence
                'totalDays': duration_days,
                'recurrence': task.get('recurrence', None),
                'recurrenceEnd': task.get('recurrenceEnd', None)
            }
            
            # Add the task instance to this date's task list
            tasks[date_str].append(task_instance)
            print(f"Added task instance to {date_str}")
            print(f"Current tasks for {date_str}: {len(tasks[date_str])}")
            
            # Move to next day
            current_date += timedelta(days=1)
        
        print(f"\n=== Task Creation Summary ===")
        print(f"Created task instances for dates: {created_dates}")
        print(f"Total instances created: {len(created_dates)}")
        
        # Return success response with created task info
        return jsonify({
            'success': True,
            'task': task_instance,
            'dates_created': created_dates,
            'duration_days': duration_days
        })
        
    except Exception as e:
        print(f"\n=== Error in add_task ===")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        print("Traceback:", traceback.format_exc())
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

def create_recurring_instances(task):
    """Create instances of recurring tasks based on the recurrence pattern."""
    try:
        start_date = datetime.strptime(task['startDate'], '%Y-%m-%d')
        end_date = datetime.strptime(task['endDate'], '%Y-%m-%d')
        recurrence_end = datetime.strptime(task['recurrenceEnd'], '%Y-%m-%d') if task['recurrenceEnd'] else None
        
        # If no recurrence end date is specified, set it to 1 year from start
        if not recurrence_end:
            recurrence_end = start_date + timedelta(days=365)
        
        current_start = start_date
        while current_start <= recurrence_end:
            # Calculate the duration of the task
            duration = (end_date - start_date).days
            current_end = current_start + timedelta(days=duration)
            
            # Create instances for each day in the duration
            current_date = current_start
            while current_date <= current_end:
                date_str = current_date.strftime('%Y-%m-%d')
                
                if date_str not in tasks:
                    tasks[date_str] = []
                    
                # Create a copy of the task for this date
                task_instance = task.copy()
                task_instance['startDate'] = current_start.strftime('%Y-%m-%d')
                task_instance['endDate'] = current_end.strftime('%Y-%m-%d')
                tasks[date_str].append(task_instance)
                
                current_date += timedelta(days=1)
            
            # Calculate next occurrence based on recurrence pattern
            next_start = calculate_next_occurrence(current_start, task['recurrence'])
            if not next_start:
                break
                
            current_start = next_start
            
    except Exception as e:
        print(f"Error in create_recurring_instances: {str(e)}")
        raise

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
        # Get today's date from the server
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = today.strftime('%Y-%m-%d')
        
        print("Received user input:", user_input)
        print("Server today's date:", start_date)
        
        if not user_input:
            return jsonify({'error': 'No input provided'}), 400

        # Parse the task using the LLM handler
        task_details = parse_tasks_from_input(user_input, start_date)
        print("LLM parsed task details:", task_details)
        
        if not task_details:
            return jsonify({'error': 'Failed to parse task details'}), 500

        # Use the date directly from task_details without adjusting
        formatted_task = {
            'title': task_details['description'],
            'description': task_details['description'],
            'startDate': task_details['start_date'],
            'endDate': task_details.get('end_date', task_details['start_date']),
            'color': task_details['color'],
            'time': '',
            'recurrence': task_details.get('recurrence', None),
            'recurrenceEnd': task_details.get('recurrence_end', None),
            'group_id': task_details.get('group_id', str(datetime.now().timestamp()))
        }
        
        print("Formatted task response:", formatted_task)
        return jsonify(formatted_task)
    except Exception as e:
        print(f"Error in parse_task endpoint: {str(e)}")
        print("Traceback:", traceback.format_exc())
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/tasks/<date>/<group_id>', methods=['PUT'])
def update_task(date, group_id):
    try:
        task = request.json
        print(f"Updating task with group_id {group_id} for date {date}")
        print("Update data:", task)
        
        if date in tasks:
            for t in tasks[date]:
                if str(t['group_id']) == str(group_id):  # Convert both to strings for comparison
                    t.update(task)
                    return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Task not found'}), 404
    except Exception as e:
        print(f"Error in update_task: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<group_id>', methods=['DELETE'])
def delete_task_group(group_id):
    try:
        print(f"Deleting task group: {group_id}")
        deleted = False
        for date in list(tasks.keys()):
            original_length = len(tasks[date])
            tasks[date] = [t for t in tasks[date] if str(t['group_id']) != str(group_id)]
            if len(tasks[date]) < original_length:
                deleted = True
            if not tasks[date]:
                del tasks[date]
        return jsonify({'success': deleted})
    except Exception as e:
        print(f"Error in delete_task_group: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/confirm-task', methods=['POST'])
def confirm_task():
    try:
        task = request.json
        if not task:
            return jsonify({'error': 'No task data received'}), 400

        # Validate required fields
        required_fields = ['title', 'startDate']
        for field in required_fields:
            if field not in task:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Format dates
        start_date = task['startDate']
        
        if start_date not in tasks:
            tasks[start_date] = []
        
        # Create task with all fields
        new_task = {
            'group_id': task.get('group_id', str(datetime.now().timestamp())),
            'title': task['title'],
            'description': task.get('description', ''),
            'time': task.get('time', ''),
            'color': task.get('color', '#007bff'),
            'startDate': start_date,
            'endDate': task.get('endDate', start_date),
            'recurrence': task.get('recurrence', None),
            'recurrenceEnd': task.get('recurrenceEnd', None)
        }
        
        # Handle recurring tasks
        if new_task['recurrence']:
            create_recurring_instances(new_task)
        else:
            tasks[start_date].append(new_task)
        
        print("Task confirmed and stored:", new_task)
        return jsonify({
            'success': True,
            'task': new_task
        })

    except Exception as e:
        print(f"Error in confirm_task: {str(e)}")
        print("Traceback:", traceback.format_exc())
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# Add error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)