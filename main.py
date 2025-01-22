from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import json
from llm_handler import parse_tasks_from_input

app = Flask(__name__, static_folder='static')

# In-memory storage for tasks (in production, you'd use a database)
tasks = {}

@app.route('/')
def index():
    current_date = datetime.now()
    return render_template('index.html', current_date=current_date)

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    try:
        task = request.json
        print("Received task data:", task)
        date = task['date']
        
        if date not in tasks:
            tasks[date] = []
        
        # Create task with optional fields and recurrence
        new_task = {
            'group_id': task.get('group_id', str(datetime.now().timestamp())),  # Use only group_id
            'title': task['title'],
            'description': task['description'],
            'time': task.get('time', ''),
            'color': task.get('color', '#007bff'),
            'startDate': task.get('startDate', date),
            'endDate': task.get('endDate', ''),
            'recurrence': task.get('recurrence', None),
            'recurrenceEnd': task.get('recurrenceEnd', None)
        }
        
        # If this is a recurring task, create instances
        if new_task['recurrence']:
            create_recurring_instances(new_task)
        else:
            tasks[date].append(new_task)
        
        print("Stored task:", new_task)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in add_task: {str(e)}")
        return jsonify({'error': str(e)}), 500

def create_recurring_instances(task):
    """Create instances of recurring tasks based on the recurrence pattern."""
    try:
        start_date = datetime.strptime(task['startDate'], '%Y-%m-%d')
        end_date = datetime.strptime(task['recurrenceEnd'], '%Y-%m-%d') if task['recurrenceEnd'] else None
        
        # If no end date is specified, set it to 1 year from start
        if not end_date:
            end_date = start_date + timedelta(days=365)
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            if date_str not in tasks:
                tasks[date_str] = []
                
            # Create a copy of the task for this date
            task_instance = task.copy()
            task_instance['startDate'] = date_str
            tasks[date_str].append(task_instance)
            
            # Calculate next occurrence based on recurrence pattern
            next_date = calculate_next_occurrence(current_date, task['recurrence'])
            if not next_date:
                break
                
            current_date = next_date
            
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
        user_input = data.get('input')
        start_date = data.get('startDate')
        
        print("Received user input:", user_input)
        print("Start date:", start_date)
        
        if not user_input:
            return jsonify({'error': 'No input provided'}), 400

        # Parse the task using the LLM handler with start date
        task_details = parse_tasks_from_input(user_input, start_date)
        print("LLM parsed task details:", task_details)
        
        formatted_task = {
            'title': task_details['description'],
            'description': task_details['description'],
            'startDate': task_details['start_date'],
            'endDate': task_details.get('end_date', ''),
            'color': task_details['color'],
            'time': '',
            'recurrence': task_details.get('recurrence', ''),
            'recurrenceEnd': task_details.get('recurrence_end', ''),
            'group_id': task_details.get('group_id', str(datetime.now().timestamp()))
        }
        
        print("Formatted task response:", formatted_task)
        return jsonify(formatted_task)
    except Exception as e:
        print(f"Error in parse_task endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

if __name__ == '__main__':
    app.run(debug=True)