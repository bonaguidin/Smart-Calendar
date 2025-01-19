from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json
from llm_handler import parse_tasks_from_input

app = Flask(__name__)

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
    task = request.json
    print("Received task data:", task)  # Debug log
    date = task['date']
    if date not in tasks:
        tasks[date] = []
    
    # Create task with optional fields
    new_task = {
        'id': len(tasks[date]),
        'title': task['title'],
        'description': task['description'],
        'time': task.get('time', ''),  # Optional time
        'color': task.get('color', '#007bff'),
        'startDate': task.get('startDate', date),
        'endDate': task.get('endDate', '')  # Optional end date
    }
    
    tasks[date].append(new_task)
    print("Stored task:", new_task)  # Debug log
    return jsonify({'success': True})

@app.route('/api/parse-task', methods=['POST'])
def parse_task():
    try:
        data = request.json
        user_input = data.get('input')
        start_date = data.get('startDate')  # Get start date from request
        
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
            'time': ''
        }
        
        print("Formatted task response:", formatted_task)
        return jsonify(formatted_task)
    except Exception as e:
        print(f"Error in parse_task endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<date>/<int:task_id>', methods=['PUT'])
def update_task(date, task_id):
    task = request.json
    if date in tasks:
        for t in tasks[date]:
            if t['id'] == task_id:
                t.update(task)
                return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/tasks/<date>/<int:task_id>', methods=['DELETE'])
def delete_task(date, task_id):
    if date in tasks:
        tasks[date] = [t for t in tasks[date] if t['id'] != task_id]
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

if __name__ == '__main__':
    app.run(debug=True)