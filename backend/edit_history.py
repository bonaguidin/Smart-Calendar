import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class EditOperation:
    """Represents a single edit operation on a task."""
    task_id: str
    attribute: str  # The attribute that was changed (title, date, etc.)
    old_value: Any  # The value before the change
    new_value: Any  # The value after the change
    timestamp: datetime
    user_id: Optional[str] = None  # If we want to track who made the change
    edit_type: str = "update"  # update, create, delete
    confidence_score: float = 1.0  # Confidence in the edit detection
    
    def to_dict(self) -> Dict:
        """Convert the edit operation to a dictionary for storage."""
        return {
            "task_id": self.task_id,
            "attribute": self.attribute,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "edit_type": self.edit_type,
            "confidence_score": self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EditOperation':
        """Create an EditOperation from a dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class EditHistory:
    """
    Manages the history of edits made to tasks.
    Supports tracking changes, undo/redo operations, and audit trails.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the EditHistory manager.
        
        Args:
            storage_path: Optional path to persist edit history
        """
        self.storage_path = storage_path
        # Dictionary to store edit history per task
        # Key: task_id, Value: list of EditOperation objects
        self.history: Dict[str, List[EditOperation]] = {}
        # Undo/redo stacks per task
        self.undo_stack: Dict[str, List[EditOperation]] = {}
        self.redo_stack: Dict[str, List[EditOperation]] = {}
        
        # Load history from storage if path provided
        if storage_path:
            self._load_history()
            
        logger.info("EditHistory initialized")
        
    def add_edit(self, edit: EditOperation) -> None:
        """
        Add a new edit operation to the history.
        
        Args:
            edit: The EditOperation to add
        """
        logger.info(f"Adding edit for task {edit.task_id}: {edit.attribute} = {edit.new_value}")
        
        # Initialize history list for task if it doesn't exist
        if edit.task_id not in self.history:
            self.history[edit.task_id] = []
            self.undo_stack[edit.task_id] = []
            self.redo_stack[edit.task_id] = []
            
        # Add to history
        self.history[edit.task_id].append(edit)
        # Clear redo stack as we have a new edit
        self.redo_stack[edit.task_id].clear()
        # Add to undo stack
        self.undo_stack[edit.task_id].append(edit)
        
        # Persist changes if storage path is set
        if self.storage_path:
            self._save_history()
            
    def get_task_history(self, task_id: str) -> List[EditOperation]:
        """Get the edit history for a specific task."""
        return self.history.get(task_id, [])
        
    def can_undo(self, task_id: str) -> bool:
        """Check if there are operations that can be undone for a task."""
        return bool(self.undo_stack.get(task_id, []))
        
    def can_redo(self, task_id: str) -> bool:
        """Check if there are operations that can be redone for a task."""
        return bool(self.redo_stack.get(task_id, []))
        
    def undo(self, task_id: str) -> Optional[EditOperation]:
        """
        Undo the last edit operation for a task.
        
        Returns:
            The undone EditOperation or None if no operations to undo
        """
        if not self.can_undo(task_id):
            logger.warning(f"No operations to undo for task {task_id}")
            return None
            
        # Pop the last operation from undo stack
        operation = self.undo_stack[task_id].pop()
        # Add to redo stack
        self.redo_stack[task_id].append(operation)
        
        logger.info(f"Undoing edit for task {task_id}: {operation.attribute}")
        return operation
        
    def redo(self, task_id: str) -> Optional[EditOperation]:
        """
        Redo the last undone edit operation for a task.
        
        Returns:
            The redone EditOperation or None if no operations to redo
        """
        if not self.can_redo(task_id):
            logger.warning(f"No operations to redo for task {task_id}")
            return None
            
        # Pop the last operation from redo stack
        operation = self.redo_stack[task_id].pop()
        # Add back to undo stack
        self.undo_stack[task_id].append(operation)
        
        logger.info(f"Redoing edit for task {task_id}: {operation.attribute}")
        return operation
        
    def get_recent_edits(self, task_id: str, limit: int = 5) -> List[EditOperation]:
        """Get the most recent edits for a task."""
        history = self.history.get(task_id, [])
        return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]
        
    def get_edit_summary(self, task_id: str) -> Dict[str, int]:
        """
        Get a summary of edits made to a task.
        
        Returns:
            Dictionary with count of edits per attribute
        """
        history = self.history.get(task_id, [])
        summary = {}
        for edit in history:
            summary[edit.attribute] = summary.get(edit.attribute, 0) + 1
        return summary
        
    def _save_history(self) -> None:
        """Save the edit history to storage."""
        if not self.storage_path:
            return
            
        try:
            # Convert history to serializable format
            serialized_history = {
                task_id: [edit.to_dict() for edit in edits]
                for task_id, edits in self.history.items()
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(serialized_history, f, indent=2)
                
            logger.info("Edit history saved successfully")
        except Exception as e:
            logger.error(f"Failed to save edit history: {e}")
            
    def _load_history(self) -> None:
        """Load the edit history from storage."""
        if not self.storage_path:
            return
            
        try:
            with open(self.storage_path, 'r') as f:
                serialized_history = json.load(f)
                
            # Convert back to EditOperation objects
            self.history = {
                task_id: [EditOperation.from_dict(edit) for edit in edits]
                for task_id, edits in serialized_history.items()
            }
            
            # Rebuild undo/redo stacks
            self.undo_stack = {
                task_id: list(edits) for task_id, edits in self.history.items()
            }
            self.redo_stack = {task_id: [] for task_id in self.history}
            
            logger.info("Edit history loaded successfully")
        except FileNotFoundError:
            logger.info("No existing edit history found")
        except Exception as e:
            logger.error(f"Failed to load edit history: {e}")
            
    def cleanup_old_history(self, days_to_keep: int = 30) -> None:
        """
        Clean up edit history older than specified days.
        
        Args:
            days_to_keep: Number of days of history to retain
        """
        cutoff_date = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        for task_id in list(self.history.keys()):
            self.history[task_id] = [
                edit for edit in self.history[task_id]
                if (cutoff_date - edit.timestamp).days <= days_to_keep
            ]
            
            # Remove empty history entries
            if not self.history[task_id]:
                del self.history[task_id]
                if task_id in self.undo_stack:
                    del self.undo_stack[task_id]
                if task_id in self.redo_stack:
                    del self.redo_stack[task_id]
                    
        logger.info(f"Cleaned up edit history older than {days_to_keep} days") 