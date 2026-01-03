from typing import Dict, Optional
from datetime import datetime
import asyncio

class ProgressTracker:
    """Track processing progress for user tasks"""
    
    def __init__(self):
        self._tasks: Dict[str, Dict] = {}
    
    def start_task(self, task_id: str, total_steps: int, description: str = ""):
        """Start tracking a new task"""
        self._tasks[task_id] = {
            "status": "running",
            "current_step": 0,
            "total_steps": total_steps,
            "description": description,
            "current_file": "",
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "error": None
        }
    
    def update_progress(self, task_id: str, current_step: int, current_file: str = ""):
        """Update task progress"""
        if task_id in self._tasks:
            self._tasks[task_id]["current_step"] = current_step
            self._tasks[task_id]["current_file"] = current_file
    
    def complete_task(self, task_id: str):
        """Mark task as completed"""
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "completed"
            self._tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
    
    def fail_task(self, task_id: str, error: str):
        """Mark task as failed"""
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["error"] = error
            self._tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get current task status"""
        return self._tasks.get(task_id)
    
    def remove_task(self, task_id: str):
        """Remove task from tracking"""
        if task_id in self._tasks:
            del self._tasks[task_id]

# Global progress tracker instance
progress_tracker = ProgressTracker()