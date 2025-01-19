from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json

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
    date = task['date']
    if date not in tasks:
        tasks[date] = []
    tasks[date].append({
        'id': len(tasks[date]),
        'title': task['title'],
        'description': task['description'],
        'time': task['time'],
        'color': task.get('color', '#007bff'),  # Add default color if none provided
        'startDate': task.get('startDate', date),
        'endDate': task.get('endDate', date)
    })
    return jsonify({'success': True})

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