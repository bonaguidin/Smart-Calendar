import re
import dateparser
from datetime import datetime, timedelta, timezone
import pytz
from typing import Dict, List, Optional, Union, Tuple
import json
import logging
from dataclasses import dataclass

from .edit_detector import EditDetector
from .task_matcher import TaskMatcher
from .edit_history import EditHistory, EditOperation
from .database import Database  # We'll create this later
from .websocket_manager import WebsocketManager  # We'll create this later

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class EditRequest:
    """Represents an edit request from either AI or manual input."""
    query: str  # The original query/request
    task_id: Optional[str] = None  # If task is already identified
    edit_type: Optional[str] = None  # If edit type is already known
    new_value: Optional[str] = None  # If new value is already known
    is_ai_edit: bool = False  # Whether this is an AI-suggested edit
    confidence_score: float = 1.0  # Confidence in the edit (always 1.0 for manual)

@dataclass
class EditResult:
    """Result of an edit operation."""
    success: bool
    task: Optional[Dict] = None  # Updated task if successful
    error: Optional[str] = None  # Error message if failed
    edit_operation: Optional[EditOperation] = None  # The recorded edit
    confidence_score: float = 1.0  # Confidence in the edit

class TaskEditor:
    """
    Unified task editor that handles both AI and manual edits.
    Coordinates between EditDetector, TaskMatcher, and EditHistory.
    """
    
    def __init__(self, db_path: str, history_path: str):
        """Initialize the TaskEditor with necessary components."""
        self.edit_detector = EditDetector()
        self.task_matcher = TaskMatcher()
        self.edit_history = EditHistory(storage_path=history_path)
        self.db = Database(db_path)
        self.websocket_manager = WebsocketManager()
        
        # Validation rules for different edit types
        self.validators = {
            'date': self._validate_date,
            'priority': self._validate_priority,
            # Add more validators as needed
        }
        
    async def process_edit(self, request: EditRequest) -> EditResult:
        """
        Process an edit request from either AI or manual input.
        
        Args:
            request: The edit request to process
            
        Returns:
            EditResult containing the result of the operation
        """
        logger.info(f"Processing edit request: {request}")
        
        try:
            # 1. Identify the task if not provided
            task, task_date = None, None
            if not request.task_id:
                task, task_date, score = self.task_matcher.find_task(request.query)
                if not task:
                    return EditResult(
                        success=False,
                        error="Could not identify which task to edit"
                    )
                request.task_id = task['id']
            else:
                task = await self.db.get_task(request.task_id)
                if not task:
                    return EditResult(
                        success=False,
                        error=f"Task {request.task_id} not found"
                    )
                    
            # 2. Detect edit type and new value if not provided
            if not request.edit_type or not request.new_value:
                edit_type, new_value, confidence = self.edit_detector.detect_edit_type(
                    request.query
                )
                if not edit_type:
                    return EditResult(
                        success=False,
                        error="Could not determine what to edit"
                    )
                request.edit_type = edit_type
                request.new_value = new_value
                request.confidence_score = confidence
                
            # 3. Validate the edit
            if request.edit_type in self.validators:
                validation_result = self.validators[request.edit_type](request.new_value)
                if not validation_result[0]:
                    return EditResult(
                        success=False,
                        error=validation_result[1]
                    )
                    
            # 4. Handle recurring tasks
            if task.get('is_recurring'):
                # Ask user whether to edit all instances or just this one
                # For now, we'll just edit this instance
                logger.info("Editing single instance of recurring task")
                
            # 5. Create edit operation
            edit_op = EditOperation(
                task_id=request.task_id,
                attribute=request.edit_type,
                old_value=task.get(request.edit_type),
                new_value=request.new_value,
                timestamp=datetime.now(),
                edit_type="update",
                confidence_score=request.confidence_score
            )
            
            # 6. Apply the edit
            task[request.edit_type] = request.new_value
            await self.db.update_task(task)
            
            # 7. Record in history
            self.edit_history.add_edit(edit_op)
            
            # 8. Notify clients of update
            await self.websocket_manager.broadcast_task_update(task)
            
            return EditResult(
                success=True,
                task=task,
                edit_operation=edit_op,
                confidence_score=request.confidence_score
            )
            
        except Exception as e:
            logger.error(f"Error processing edit: {e}", exc_info=True)
            return EditResult(
                success=False,
                error=f"Internal error: {str(e)}"
            )
            
    def _validate_date(self, date_str: str) -> Tuple[bool, Optional[str]]:
        """Validate a date value."""
        try:
            # Add date parsing logic here
            return True, None
        except ValueError as e:
            return False, f"Invalid date format: {str(e)}"
            
    def _validate_priority(self, priority: str) -> Tuple[bool, Optional[str]]:
        """Validate a priority value."""
        valid_priorities = {'low', 'medium', 'high'}
        if priority.lower() not in valid_priorities:
            return False, f"Priority must be one of: {', '.join(valid_priorities)}"
        return True, None
        
    async def undo_edit(self, task_id: str) -> EditResult:
        """Undo the last edit for a task."""
        operation = self.edit_history.undo(task_id)
        if not operation:
            return EditResult(
                success=False,
                error="No edits to undo"
            )
            
        # Revert the change in the database
        task = await self.db.get_task(task_id)
        if not task:
            return EditResult(
                success=False,
                error="Task not found"
            )
            
        task[operation.attribute] = operation.old_value
        await self.db.update_task(task)
        
        # Notify clients
        await self.websocket_manager.broadcast_task_update(task)
        
        return EditResult(
            success=True,
            task=task,
            edit_operation=operation
        )
        
    async def redo_edit(self, task_id: str) -> EditResult:
        """Redo the last undone edit for a task."""
        operation = self.edit_history.redo(task_id)
        if not operation:
            return EditResult(
                success=False,
                error="No edits to redo"
            )
            
        # Apply the change in the database
        task = await self.db.get_task(task_id)
        if not task:
            return EditResult(
                success=False,
                error="Task not found"
            )
            
        task[operation.attribute] = operation.new_value
        await self.db.update_task(task)
        
        # Notify clients
        await self.websocket_manager.broadcast_task_update(task)
        
        return EditResult(
            success=True,
            task=task,
            edit_operation=operation
        )
        
    async def get_edit_history(self, task_id: str, limit: int = 5) -> List[EditOperation]:
        """Get recent edits for a task."""
        return self.edit_history.get_recent_edits(task_id, limit)

    def parse_edit_request(self, input_text: str, original_task: Dict) -> Dict:
        """
        Parse natural language edit request and return structured changes.
        
        Args:
            input_text: Natural language edit request
            original_task: Original task data
            
        Returns:
            Dict containing structured edit operations
        """
        self.logger.info(f"Parsing edit request: {input_text}")
        self.logger.debug(f"Original task: {json.dumps(original_task, indent=2)}")
        
        edit_ops = {
            'type': None,
            'changes': {},
            'affects_all_instances': False
        }
        
        try:
            # Check for global modifications
            if 'all instances' in input_text.lower():
                edit_ops['affects_all_instances'] = True
            
            # Parse time changes
            if time_match := self.time_patterns['absolute'].search(input_text):
                edit_ops.update(self._handle_absolute_time(time_match.group(1), original_task))
            
            elif rel_match := self.time_patterns['relative'].search(input_text):
                edit_ops.update(self._handle_relative_time(
                    rel_match.group(1),  # direction
                    int(rel_match.group(2)),  # amount
                    rel_match.group(3),  # unit
                    original_task
                ))
            
            elif dur_match := self.time_patterns['duration'].search(input_text):
                edit_ops.update(self._handle_duration_change(
                    int(dur_match.group(1)),  # amount
                    dur_match.group(2),  # unit
                    original_task
                ))
            
            elif multi_match := self.time_patterns['multi_day'].search(input_text):
                edit_ops.update(self._handle_multi_day(multi_match.group(1), original_task))
            
            # Validate changes
            self._validate_changes(edit_ops, original_task)
            
            self.logger.info(f"Generated edit operations: {json.dumps(edit_ops, indent=2)}")
            return edit_ops
            
        except Exception as e:
            self.logger.error(f"Error parsing edit request: {str(e)}")
            raise
    
    def _handle_absolute_time(self, time_str: str, original_task: Dict) -> Dict:
        """Handle absolute time change requests."""
        parsed_time = dateparser.parse(
            time_str,
            settings={'TIMEZONE': str(self.default_tz)}
        )
        
        if not parsed_time:
            raise ValueError(f"Could not parse time: {time_str}")
            
        changes = {
            'type': 'absolute_time',
            'changes': {
                'start_date': parsed_time.date().isoformat(),
                'time': parsed_time.strftime('%H:%M')
            }
        }
        
        self.logger.debug(f"Parsed absolute time change: {changes}")
        return changes
    
    def _handle_relative_time(self, direction: str, amount: int, unit: str, original_task: Dict) -> Dict:
        """Handle relative time shift requests."""
        multiplier = -1 if direction.lower() in ['back', 'backward', 'backwards'] else 1
        
        delta = self._calculate_time_delta(amount * multiplier, unit)
        start_dt = datetime.fromisoformat(original_task['start_date'])
        
        changes = {
            'type': 'relative_time',
            'changes': {
                'start_date': (start_dt + delta).date().isoformat()
            }
        }
        
        if 'end_date' in original_task:
            end_dt = datetime.fromisoformat(original_task['end_date'])
            changes['changes']['end_date'] = (end_dt + delta).date().isoformat()
        
        self.logger.debug(f"Parsed relative time change: {changes}")
        return changes
    
    def _handle_duration_change(self, amount: int, unit: str, original_task: Dict) -> Dict:
        """Handle duration extension requests."""
        delta = self._calculate_time_delta(amount, unit)
        end_dt = datetime.fromisoformat(original_task['end_date'])
        
        changes = {
            'type': 'duration',
            'changes': {
                'end_date': (end_dt + delta).date().isoformat()
            }
        }
        
        self.logger.debug(f"Parsed duration change: {changes}")
        return changes
    
    def _handle_multi_day(self, days_str: str, original_task: Dict) -> Dict:
        """Handle multi-day expansion requests."""
        days = [day.strip() for day in re.split(r',|\sand\s', days_str)]
        current_start = datetime.fromisoformat(original_task['start_date'])
        
        new_dates = []
        for day in days:
            parsed_day = dateparser.parse(day)
            if parsed_day:
                new_dates.append(parsed_day.date().isoformat())
        
        changes = {
            'type': 'multi_day',
            'changes': {
                'additional_dates': new_dates
            }
        }
        
        self.logger.debug(f"Parsed multi-day change: {changes}")
        return changes
    
    def _calculate_time_delta(self, amount: int, unit: str) -> timedelta:
        """Calculate timedelta based on amount and unit."""
        unit = unit.lower()
        if unit in ['hour', 'hours']:
            return timedelta(hours=amount)
        elif unit in ['minute', 'minutes']:
            return timedelta(minutes=amount)
        elif unit in ['day', 'days']:
            return timedelta(days=amount)
        elif unit in ['week', 'weeks']:
            return timedelta(weeks=amount)
        else:
            raise ValueError(f"Unsupported time unit: {unit}")
    
    def _validate_changes(self, edit_ops: Dict, original_task: Dict) -> None:
        """Validate proposed changes against task schema and constraints."""
        if not edit_ops.get('changes'):
            raise ValueError("No changes specified in edit operations")
            
        changes = edit_ops['changes']
        
        # Validate dates
        if 'start_date' in changes:
            try:
                datetime.fromisoformat(changes['start_date'])
            except ValueError:
                raise ValueError(f"Invalid start_date format: {changes['start_date']}")
                
        if 'end_date' in changes:
            try:
                datetime.fromisoformat(changes['end_date'])
            except ValueError:
                raise ValueError(f"Invalid end_date format: {changes['end_date']}")
                
        # Validate date order
        if 'start_date' in changes and 'end_date' in changes:
            if changes['start_date'] > changes['end_date']:
                raise ValueError("Start date cannot be after end date") 