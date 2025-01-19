class Calendar {
    constructor() {
        this.currentDate = new Date();
        this.monthDisplay = document.getElementById('monthDisplay');
        this.calendarDays = document.getElementById('calendar-days');
        this.tasks = {};
        
        this.setupEventListeners();
        this.loadTasks();
        
        // Setup theme
        this.theme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', this.theme);
        
        // Additional event listeners
        document.getElementById('themeToggle').addEventListener('click', () => this.toggleTheme());
        this.setupColorPicker();
    }

    setupEventListeners() {
        document.getElementById('prevMonth').addEventListener('click', () => this.previousMonth());
        document.getElementById('nextMonth').addEventListener('click', () => this.nextMonth());
        
        // Modal elements
        this.modal = document.getElementById('taskModal');
        this.closeBtn = document.querySelector('.close');
        this.taskForm = document.getElementById('taskForm');
        this.deleteBtn = document.getElementById('deleteTask');

        this.closeBtn.onclick = () => this.modal.style.display = "none";
        this.taskForm.onsubmit = (e) => this.handleTaskSubmit(e);
        this.deleteBtn.onclick = () => this.handleTaskDelete();

        window.onclick = (e) => {
            if (e.target == this.modal) {
                this.modal.style.display = "none";
            }
        };

        // Add natural language parsing
        document.getElementById('parseTask').addEventListener('click', () => this.handleNaturalLanguageInput());
    }

    async loadTasks() {
        try {
            const response = await fetch('/api/tasks');
            this.tasks = await response.json();
            this.updateCalendar();
        } catch (error) {
            console.error('Error loading tasks:', error);
        }
    }

    updateCalendar() {
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
    
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
    
        this.monthDisplay.textContent = `${firstDay.toLocaleString('default', { month: 'long' })} ${year}`;
    
        this.calendarDays.innerHTML = '';
    
        for (let i = 0; i < firstDay.getDay(); i++) {
            const div = document.createElement('div');
            div.classList.add('other-month');
            this.calendarDays.appendChild(div);
        }
    
        const today = new Date();
        for (let day = 1; day <= lastDay.getDate(); day++) {
            const div = document.createElement('div');
            const dateStr = this.formatDate(year, month, day);
    
            div.innerHTML = `
                <span>${day}</span>
                <div class="task-list" data-date="${dateStr}"></div>
            `;
    
            if (year === today.getFullYear() && month === today.getMonth() && day === today.getDate()) {
                div.classList.add('today');
            }
    
            div.onclick = () => this.showTaskModal(dateStr);
    
            this.calendarDays.appendChild(div);
            this.updateTasksForDate(dateStr);
        }
    }

    updateTasksForDate(dateStr) {
        const taskList = document.querySelector(`.task-list[data-date="${dateStr}"]`);
        if (this.tasks[dateStr]) {
            taskList.innerHTML = this.tasks[dateStr]
                .map(task => {
                    const taskColor = task.color || '#007bff';
                    const rgbColor = this.hexToRGB(taskColor);
                    return `
                        <div class="task-item" 
                             onclick="event.stopPropagation(); calendar.showTaskModal('${dateStr}', ${task.id})"
                             style="--task-color: ${taskColor}; --task-rgb: ${rgbColor}; --task-text-color: ${this.getContrastColor(taskColor)}">
                            ${task.title}
                        </div>
                    `;
                }).join('');
        }
    }

    showTaskModal(date, taskId = null) {
        event.stopPropagation();
        console.log("Opening modal for date:", date, "taskId:", taskId); // Debug log
        const task = taskId !== null ? this.tasks[date].find(t => t.id === taskId) : null;
        
        document.getElementById('modalTitle').textContent = task ? 'Edit Task' : 'Add Task';
        document.getElementById('taskId').value = taskId !== null ? taskId : '';
        
        // Use the date directly without formatting
        document.getElementById('taskStartDate').value = task ? task.startDate : date;
        document.getElementById('taskEndDate').value = task ? task.endDate : date;
        
        document.getElementById('taskTitle').value = task ? task.title : '';
        document.getElementById('taskTime').value = task ? task.time : '';
        document.getElementById('taskDescription').value = task ? task.description : '';
        document.getElementById('taskColor').value = task ? task.color : '#007bff';
        
        // Update color picker selection
        document.querySelectorAll('.color-option').forEach(option => {
            option.classList.toggle('selected', option.dataset.color === (task ? task.color : '#007bff'));
        });
        
        document.getElementById('deleteTask').style.display = task ? 'block' : 'none';
        this.modal.style.display = "block";
    }

    async handleTaskSubmit(e) {
        e.preventDefault();
        console.log("Form submission started");

        const taskId = document.getElementById('taskId').value;
        const startDate = new Date(document.getElementById('taskStartDate').value);
        const endDate = document.getElementById('taskEndDate').value 
            ? new Date(document.getElementById('taskEndDate').value) 
            : startDate;
        const time = document.getElementById('taskTime').value || '';

        startDate.setDate(startDate.getDate() + 1);
        endDate.setDate(endDate.getDate() + 1);

        console.log("Form values:", { startDate, endDate, time, taskId });

        const task = {
            title: document.getElementById('taskTitle').value,
            time: time,
            description: document.getElementById('taskDescription').value,
            color: document.getElementById('taskColor').value,
            startDate: startDate.toISOString().split('T')[0], // YYYY-MM-DD in local time
            endDate: endDate.toISOString().split('T')[0]
        };

        console.log("Task object created:", task);

        try {
            const dates = endDate ? this.getDatesBetween(startDate, endDate) : [startDate];
            console.log("Dates to create tasks for:", dates);

            for (const date of dates) {
                const url = taskId ? 
                    `/api/tasks/${date}/${taskId}` : 
                    '/api/tasks';
                const method = taskId ? 'PUT' : 'POST';

                console.log(`Making ${method} request to ${url}`);
                
                const response = await fetch(url, {
                    method: method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        ...task,
                        date: date,  // Use the same date for both storage and display
                        startDate: date,  // Ensure startDate matches the current date
                        endDate: endDate || date  // If no endDate, use the current date
                    })
                });

                const result = await response.json();
                console.log(`Server response for ${date}:`, result);
            }

            await this.loadTasks();
            this.modal.style.display = "none";
        } catch (error) {
            console.error('Error saving task:', error);
        }
    }

    async handleTaskDelete() {
        const taskId = document.getElementById('taskId').value;
        // Get the date from the tasks object where the task actually exists
        let taskDate = null;
        
        // Find the actual date where the task exists
        for (const [date, tasks] of Object.entries(this.tasks)) {
            if (tasks.find(t => t.id === parseInt(taskId))) {
                taskDate = date;
                break;
            }
        }
        
        console.log("Found task to delete:", { taskDate, taskId }); // Debug log
        
        if (!taskDate || !taskId) {
            console.error('Missing required data for deletion');
            return;
        }

        if (confirm('Are you sure you want to delete this task?')) {
            try {
                // Handle single task deletion
                console.log(`Attempting to delete task for date: ${taskDate}`);
                const response = await fetch(`/api/tasks/${taskDate}/${taskId}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to delete task. Server returned ${response.status}`);
                }
                
                await this.loadTasks();
                this.modal.style.display = "none";
            } catch (error) {
                console.error('Error deleting task:', error);
                alert('Failed to delete task. Please try again.');
            }
        }
    }

    formatDate(year, month, day) {
        // Use the local time to create a date string
        const localDate = new Date(year, month, day);
        return localDate.toISOString().split('T')[0]; // Returns YYYY-MM-DD in local time
    }

    previousMonth() {
        this.currentDate.setMonth(this.currentDate.getMonth() - 1);
        this.updateCalendar();
    }

    nextMonth() {
        this.currentDate.setMonth(this.currentDate.getMonth() + 1);
        this.updateCalendar();
    }

    setupColorPicker() {
        const colorOptions = document.querySelectorAll('.color-option');
        colorOptions.forEach(option => {
            option.addEventListener('click', () => {
                colorOptions.forEach(opt => opt.classList.remove('selected'));
                option.classList.add('selected');
                document.getElementById('taskColor').value = option.dataset.color;
            });
        });
    }

    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', this.theme);
        localStorage.setItem('theme', this.theme);
    }

    getDatesBetween(startDate, endDate) {
        const dates = [];
        let currentDate = new Date(startDate);
        const end = new Date(endDate);
        
        while (currentDate <= end) {
            dates.push(this.formatDate(
                currentDate.getFullYear(),
                currentDate.getMonth(),
                currentDate.getDate()
            ));
            currentDate.setDate(currentDate.getDate() + 1);
        }
        
        return dates;
    }

    getContrastColor(hexcolor) {
        // If no color provided, return default black
        if (!hexcolor) return '#000000';
        
        try {
            // Convert hex to RGB
            const r = parseInt(hexcolor.slice(1,3), 16);
            const g = parseInt(hexcolor.slice(3,5), 16);
            const b = parseInt(hexcolor.slice(5,7), 16);
            
            // Check if conversion was successful
            if (isNaN(r) || isNaN(g) || isNaN(b)) {
                return '#000000';
            }
            
            // Calculate luminance
            const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
            
            // Return black or white based on luminance
            return luminance > 0.5 ? '#000000' : '#ffffff';
        } catch (error) {
            console.error('Error calculating contrast color:', error);
            return '#000000'; // Return black as fallback
        }
    }

    // Simplify formatDateForInput to handle the date correctly
    formatDateForInput(dateStr) {
        // Ensure the date string remains in local time
        const localDate = new Date(dateStr);
        return localDate.toISOString().split('T')[0];
    }

    // Simplify adjustDateForStorage to just return the formatted date
    adjustDateForStorage(dateStr) {
        return dateStr;  // No adjustment needed anymore
    }

    // Add helper method to convert hex to RGB
    hexToRGB(hex) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `${r}, ${g}, ${b}`;
    }

    async handleNaturalLanguageInput() {
        const input = document.getElementById('nlInput').value;
        if (!input) return;

        console.log("Natural language input:", input);

        try {
            // Get the currently selected start date from the form
            const startDate = document.getElementById('taskStartDate').value;
            
            const response = await fetch('/api/parse-task', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    input,
                    startDate  // Include the start date in the request
                })
            });

            const taskDetails = await response.json();
            console.log("Parsed task details:", taskDetails);  // Debug log

            if (taskDetails.error) {
                throw new Error(taskDetails.error);
            }

            if (taskDetails.description && taskDetails.description.startsWith('Error:')) {
                console.error("LLM processing error:", taskDetails.description);
                alert(`AI Processing Error: ${taskDetails.description.substring(7)}`);
                return;
            }

            // Fill in the form with the parsed details
            document.getElementById('taskTitle').value = taskDetails.title || taskDetails.description;
            document.getElementById('taskStartDate').value = taskDetails.startDate;
            document.getElementById('taskEndDate').value = taskDetails.endDate || '';
            document.getElementById('taskDescription').value = taskDetails.description;
            document.getElementById('taskTime').value = taskDetails.time || '';
            
            // Update color picker
            const colorInput = document.getElementById('taskColor');
            colorInput.value = taskDetails.color;
            document.querySelectorAll('.color-option').forEach(option => {
                option.classList.toggle('selected', option.dataset.color === taskDetails.color);
            });

            // Clear the natural language input
            document.getElementById('nlInput').value = '';
        } catch (error) {
            console.error('Error parsing task:', error);
            alert(`Failed to parse task: ${error.message}. Please try again or fill in the form manually.`);
        }
    }
}

// Initialize the calendar when the page loads
let calendar;
document.addEventListener('DOMContentLoaded', () => {
    calendar = new Calendar();
}); 