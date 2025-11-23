"""
Batch Generation Service
Handles batch processing of multiple curriculum generation requests
"""

import os
import sys
import uuid
import time
import json
import threading
from queue import Queue, Empty
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from enum import Enum

# Platform-specific file locking
if sys.platform == 'win32':
    import msvcrt
    FCNTL_AVAILABLE = False
else:
    import fcntl
    FCNTL_AVAILABLE = True


def _lock_file(file_obj, exclusive: bool = True):
    """Cross-platform file locking
    
    Args:
        file_obj: File object to lock
        exclusive: If True, exclusive lock; if False, shared lock
    """
    if FCNTL_AVAILABLE:
        # Unix/Linux/macOS: use fcntl
        lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fcntl.flock(file_obj.fileno(), lock_type)
    elif sys.platform == 'win32':
        # Windows: use msvcrt
        try:
            if exclusive:
                # Lock entire file (max 32-bit signed int)
                msvcrt.locking(file_obj.fileno(), msvcrt.LK_LOCK, 0x7FFFFFFF)
            else:
                # Windows doesn't have shared locks, use exclusive
                msvcrt.locking(file_obj.fileno(), msvcrt.LK_LOCK, 0x7FFFFFFF)
        except (OSError, IOError) as e:
            # Lock failed, log warning and continue without locking
            print(f"Warning: File lock failed: {e}")


def _unlock_file(file_obj):
    """Cross-platform file unlocking
    
    Args:
        file_obj: File object to unlock
    """
    if FCNTL_AVAILABLE:
        # Unix/Linux/macOS: lock is released automatically on close
        pass
    elif sys.platform == 'win32':
        # Windows: explicitly unlock
        try:
            # Unlock entire file (must match lock size)
            msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 0x7FFFFFFF)
        except (OSError, IOError):
            pass


class BatchStatus(Enum):
    """Status of batch generation jobs"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """Individual job in a batch"""
    id: str
    name: str
    params: Dict[str, Any]
    status: BatchStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    progress: float = 0.0


@dataclass
class BatchRequest:
    """Batch generation request"""
    id: str
    name: str
    description: str
    jobs: List[BatchJob]
    status: BatchStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    estimated_cost: float = 0.0


class BatchQueue:
    """Queue manager for batch jobs
    
    IMPORTANT: This class uses background threads for job processing.
    Streamlit is NOT thread-safe, so worker threads MUST NOT:
    - Write to st.session_state
    - Call any Streamlit UI functions
    - Modify shared objects that may be accessed by the UI thread
    
    Instead, use file-based status tracking:
    - Worker threads write status to JSON files
    - UI thread reads status from JSON files
    - This ensures complete thread isolation
    """
    
    def __init__(self, max_concurrent: int = 2, max_completed_jobs: int = 1000, status_dir: str = "batch_status"):
        """Initialize batch queue
        
        Args:
            max_concurrent: Maximum number of concurrent jobs
            max_completed_jobs: Maximum number of completed jobs to keep in memory
            status_dir: Directory to store job status files
        """
        self.max_concurrent = max_concurrent
        self.max_completed_jobs = max_completed_jobs
        self.job_queue = Queue()
        self.active_jobs: Dict[str, threading.Thread] = {}
        self.completed_jobs: Dict[str, BatchJob] = {}
        self.job_lock = threading.Lock()
        self.running = True
        
        # Initialize status directory for file-based status tracking
        self.status_dir = Path(status_dir)
        self.status_dir.mkdir(exist_ok=True)
        
        # Clean up old status files on startup
        self._cleanup_old_status_files()
        
        # Start worker threads
        self.workers = []
        for i in range(max_concurrent):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def add_job(self, job: BatchJob, generator_func: Callable):
        """Add a job to the queue
        
        Args:
            job: Job to add
            generator_func: Function to generate curriculum
        """
        self.job_queue.put((job, generator_func))
    
    def _worker_loop(self):
        """Worker thread loop"""
        while self.running:
            try:
                # Get job from queue (timeout to allow checking running flag)
                job, generator_func = self.job_queue.get(timeout=1.0)
                
                # Execute job
                self._execute_job(job, generator_func)
                
                # Mark task as done
                self.job_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")
    
    def _write_job_status(self, job: BatchJob):
        """Write job status to file (thread-safe, no session_state access)
        
        Args:
            job: Job to write status for
        """
        status_file = self.status_dir / f"{job.id}.json"
        
        try:
            # Convert job to dict for serialization
            job_data = asdict(job)
            job_data["status"] = job.status.value
            
            # Use file locking for concurrent access safety
            with open(status_file, 'w', encoding='utf-8') as f:
                try:
                    # Acquire exclusive lock (cross-platform)
                    _lock_file(f, exclusive=True)

                    json.dump(job_data, f, indent=2)

                finally:
                    # Unlock before closing (important for Windows)
                    _unlock_file(f)
                
        except Exception as e:
            print(f"Error writing job status for {job.id}: {e}")
    
    def _read_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Read job status from file
        
        Args:
            job_id: Job ID to read status for
            
        Returns:
            BatchJob object or None if not found
        """
        status_file = self.status_dir / f"{job_id}.json"
        
        if not status_file.exists():
            return None
        
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                try:
                    # Acquire shared lock for reading (cross-platform)
                    _lock_file(f, exclusive=False)

                    job_data = json.load(f)

                    # Validate required fields before creating BatchJob
                    required_fields = ['id', 'name', 'params', 'status', 'created_at']
                    if not all(field in job_data for field in required_fields):
                        raise ValueError(f"Missing required fields in job data for {job_id}")

                    # Convert status back to enum
                    job_data["status"] = BatchStatus(job_data["status"])

                    return BatchJob(**job_data)

                finally:
                    # Unlock before closing (important for Windows)
                    _unlock_file(f)
                
        except Exception as e:
            print(f"Error reading job status for {job_id}: {e}")
            return None
    
    def _cleanup_old_status_files(self, max_age_hours: int = 24):
        """Clean up old status files
        
        Args:
            max_age_hours: Maximum age of status files to keep (default 24 hours)
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for status_file in self.status_dir.glob("*.json"):
                try:
                    # Check file modification time
                    file_mtime = datetime.fromtimestamp(status_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        status_file.unlink()
                        print(f"Cleaned up old status file: {status_file.name}")
                        
                except Exception as e:
                    print(f"Error checking/deleting status file {status_file}: {e}")
                    
        except Exception as e:
            print(f"Error during status file cleanup: {e}")
    
    def _execute_job(self, job: BatchJob, generator_func: Callable):
        """Execute a single job with file-based status tracking (NO session_state access)
        
        Args:
            job: Job to execute
            generator_func: Function to generate curriculum
        """
        # Thread-safe status update for job start
        with self.job_lock:
            self.active_jobs[job.id] = threading.current_thread()
            job.status = BatchStatus.RUNNING
            job.started_at = datetime.now().isoformat()
        
        # Write initial status to file (thread-safe, no session_state)
        self._write_job_status(job)
        
        try:
            # Execute generation (this is the long-running operation)
            result = generator_func(job.params)
            
            # Thread-safe status update for job completion
            with self.job_lock:
                job.status = BatchStatus.COMPLETED
                job.completed_at = datetime.now().isoformat()
                job.result = result
                job.progress = 1.0
            
            # Write completion status to file
            self._write_job_status(job)
            
        except Exception as e:
            # Thread-safe status update for job failure
            with self.job_lock:
                job.status = BatchStatus.FAILED
                job.completed_at = datetime.now().isoformat()
                job.error_message = str(e)
                job.progress = 0.0
            
            # Write failure status to file
            self._write_job_status(job)
                
        finally:
            # Thread-safe cleanup
            with self.job_lock:
                self.active_jobs.pop(job.id, None)
                # Store completed job
                self.completed_jobs[job.id] = job
                # Cleanup old jobs to prevent memory leaks
                self._cleanup_completed_jobs()
    
    def _cleanup_completed_jobs(self):
        """Clean up old completed jobs to prevent memory leaks
        
        Note: This method should be called with job_lock held
        """
        if len(self.completed_jobs) > self.max_completed_jobs:
            # Keep only the most recent jobs
            sorted_jobs = sorted(
                self.completed_jobs.items(),
                key=lambda x: x[1].completed_at or x[1].created_at,
                reverse=True
            )
            
            # Keep only max_completed_jobs
            jobs_to_keep = dict(sorted_jobs[:self.max_completed_jobs])
            removed_count = len(self.completed_jobs) - len(jobs_to_keep)
            self.completed_jobs = jobs_to_keep
            
            print(f"Cleaned up {removed_count} old batch jobs, keeping {len(jobs_to_keep)}")
    
    def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Get status of a specific job (reads from file, safe for UI thread)

        Args:
            job_id: ID of job to check

        Returns:
            Job status or None if not found
        """
        # Read from file system first (authoritative source)
        file_job = self._read_job_status(job_id)
        if file_job:
            return file_job

        # Fallback to memory with lock protection
        with self.job_lock:
            return self.completed_jobs.get(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job
        
        Args:
            job_id: ID of job to cancel
            
        Returns:
            True if cancelled successfully
        """
        with self.job_lock:
            if job_id in self.active_jobs:
                # Note: Python threading doesn't support forced termination
                # This would need to be implemented within the generator function
                return False
        
        return True
    
    def shutdown(self):
        """Shutdown the queue"""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5.0)


class BatchManager:
    """Manages batch generation requests"""
    
    def __init__(self, batch_dir: str = "batches", max_concurrent: int = 2, status_dir: str = "batch_status"):
        """Initialize batch manager
        
        Args:
            batch_dir: Directory to store batch data
            max_concurrent: Maximum concurrent jobs
            status_dir: Directory to store job status files
        """
        self.batch_dir = Path(batch_dir)
        self.batch_dir.mkdir(exist_ok=True)
        self.max_concurrent = max_concurrent
        
        # Initialize queue with status directory
        self.queue = BatchQueue(max_concurrent, status_dir=status_dir)
        
        # Track active batches
        self.active_batches: Dict[str, BatchRequest] = {}
        
        # Load existing batches
        self._load_existing_batches()
    
    def _load_existing_batches(self):
        """Load existing batch requests from disk"""
        try:
            for batch_file in self.batch_dir.glob("batch_*.json"):
                try:
                    with open(batch_file, 'r', encoding='utf-8') as f:
                        batch_data = json.load(f)
                    
                    # Convert back to dataclass
                    jobs = [BatchJob(**job_data) for job_data in batch_data["jobs"]]
                    batch_request = BatchRequest(
                        id=batch_data["id"],
                        name=batch_data["name"],
                        description=batch_data["description"],
                        jobs=jobs,
                        status=BatchStatus(batch_data["status"]),
                        created_at=batch_data["created_at"],
                        started_at=batch_data.get("started_at"),
                        completed_at=batch_data.get("completed_at"),
                        total_jobs=batch_data["total_jobs"],
                        completed_jobs=batch_data["completed_jobs"],
                        failed_jobs=batch_data["failed_jobs"],
                        estimated_cost=batch_data.get("estimated_cost", 0.0)
                    )
                    
                    self.active_batches[batch_request.id] = batch_request
                    
                except Exception as e:
                    print(f"Error loading batch file {batch_file}: {e}")
                    
        except Exception as e:
            print(f"Error loading existing batches: {e}")
    
    def _save_batch(self, batch_request: BatchRequest):
        """Save batch request to disk
        
        Args:
            batch_request: Batch request to save
        """
        try:
            batch_file = self.batch_dir / f"batch_{batch_request.id}.json"
            
            # Convert to serializable format
            batch_data = asdict(batch_request)
            
            # Convert enums to strings
            batch_data["status"] = batch_request.status.value
            for job_data in batch_data["jobs"]:
                job_data["status"] = BatchStatus(job_data["status"]).value
            
            with open(batch_file, 'w', encoding='utf-8') as f:
                json.dump(batch_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving batch {batch_request.id}: {e}")
    
    def create_batch_from_template(self, 
                                  template_id: str,
                                  subjects: List[str],
                                  grades: List[str],
                                  template_manager,
                                  name: str = None,
                                  description: str = None) -> str:
        """Create a batch request from a template applied to multiple subjects/grades
        
        Args:
            template_id: Template to use
            subjects: List of subjects
            grades: List of grades  
            template_manager: Template manager instance
            name: Optional batch name
            description: Optional batch description
            
        Returns:
            Batch request ID
        """
        if not name:
            name = f"Batch from template {template_id}"
        if not description:
            description = f"Batch generation using template {template_id} for {len(subjects)} subjects and {len(grades)} grades"
        
        # Generate all combinations
        jobs = []
        for subject in subjects:
            for grade in grades:
                try:
                    # Apply template to get parameters
                    params = template_manager.apply_template(template_id, subject, grade)
                    
                    # Create job
                    job = BatchJob(
                        id=f"job_{uuid.uuid4().hex[:8]}",
                        name=f"{subject} Grade {grade}",
                        params=params,
                        status=BatchStatus.PENDING,
                        created_at=datetime.now().isoformat()
                    )
                    jobs.append(job)
                    
                except Exception as e:
                    print(f"Error creating job for {subject} Grade {grade}: {e}")
        
        return self._create_batch_request(name, description, jobs)
    
    def create_custom_batch(self,
                           job_configs: List[Dict[str, Any]],
                           name: str,
                           description: str = None) -> str:
        """Create a batch request from custom job configurations
        
        Args:
            job_configs: List of job configuration dictionaries
            name: Batch name
            description: Optional batch description
            
        Returns:
            Batch request ID
        """
        if not description:
            description = f"Custom batch with {len(job_configs)} jobs"
        
        jobs = []
        for i, config in enumerate(job_configs):
            job = BatchJob(
                id=f"job_{uuid.uuid4().hex[:8]}",
                name=config.get("name", f"Job {i+1}"),
                params=config,
                status=BatchStatus.PENDING,
                created_at=datetime.now().isoformat()
            )
            jobs.append(job)
        
        return self._create_batch_request(name, description, jobs)
    
    def _create_batch_request(self, name: str, description: str, jobs: List[BatchJob]) -> str:
        """Create a batch request
        
        Args:
            name: Batch name
            description: Batch description
            jobs: List of jobs
            
        Returns:
            Batch request ID
        """
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        
        batch_request = BatchRequest(
            id=batch_id,
            name=name,
            description=description,
            jobs=jobs,
            status=BatchStatus.PENDING,
            created_at=datetime.now().isoformat(),
            total_jobs=len(jobs),
            completed_jobs=0,
            failed_jobs=0
        )
        
        # Store batch
        self.active_batches[batch_id] = batch_request
        self._save_batch(batch_request)
        
        return batch_id
    
    def start_batch(self, batch_id: str, generator_func: Callable) -> bool:
        """Start processing a batch
        
        Args:
            batch_id: Batch to start
            generator_func: Function to generate curricula
            
        Returns:
            True if started successfully
        """
        if batch_id not in self.active_batches:
            return False
        
        batch_request = self.active_batches[batch_id]
        
        if batch_request.status != BatchStatus.PENDING:
            return False
        
        # Update batch status
        batch_request.status = BatchStatus.RUNNING
        batch_request.started_at = datetime.now().isoformat()
        
        # Add jobs to queue
        for job in batch_request.jobs:
            self.queue.add_job(job, generator_func)
        
        # Save updated batch
        self._save_batch(batch_request)
        
        return True
    
    def get_batch_status(self, batch_id: str) -> Optional[BatchRequest]:
        """Get batch status (reads from files, safe for UI thread)
        
        This method reads job statuses from the file system, making it safe
        to call from the main Streamlit thread without threading violations.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Batch status or None if not found
        """
        if batch_id not in self.active_batches:
            return None
        
        batch_request = self.active_batches[batch_id]
        
        # Update job statuses by reading from files (thread-safe)
        completed = 0
        failed = 0
        
        for job in batch_request.jobs:
            # Read from file system (safe for UI thread)
            updated_job = self.queue.get_job_status(job.id)
            if updated_job:
                # Update job in batch
                job.status = updated_job.status
                job.started_at = updated_job.started_at
                job.completed_at = updated_job.completed_at
                job.error_message = updated_job.error_message
                job.result = updated_job.result
                job.progress = updated_job.progress
            
            if job.status == BatchStatus.COMPLETED:
                completed += 1
            elif job.status == BatchStatus.FAILED:
                failed += 1
        
        # Update batch counters
        batch_request.completed_jobs = completed
        batch_request.failed_jobs = failed
        
        # Check if batch is complete
        if completed + failed == batch_request.total_jobs:
            if batch_request.status == BatchStatus.RUNNING:
                batch_request.status = BatchStatus.COMPLETED
                batch_request.completed_at = datetime.now().isoformat()
        
        # Save updated batch
        self._save_batch(batch_request)
        
        return batch_request
    
    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a batch
        
        Args:
            batch_id: Batch to cancel
            
        Returns:
            True if cancelled successfully
        """
        if batch_id not in self.active_batches:
            return False
        
        batch_request = self.active_batches[batch_id]
        
        if batch_request.status not in [BatchStatus.PENDING, BatchStatus.RUNNING]:
            return False
        
        # Update status
        batch_request.status = BatchStatus.CANCELLED
        batch_request.completed_at = datetime.now().isoformat()
        
        # Cancel individual jobs
        for job in batch_request.jobs:
            if job.status in [BatchStatus.PENDING, BatchStatus.RUNNING]:
                job.status = BatchStatus.CANCELLED
                self.queue.cancel_job(job.id)
        
        # Save updated batch
        self._save_batch(batch_request)
        
        return True
    
    def list_batches(self, status_filter: Optional[BatchStatus] = None) -> List[BatchRequest]:
        """List all batches
        
        Args:
            status_filter: Optional status filter
            
        Returns:
            List of batch requests
        """
        batches = list(self.active_batches.values())
        
        if status_filter:
            batches = [b for b in batches if b.status == status_filter]
        
        # Sort by creation date (newest first)
        batches.sort(key=lambda b: b.created_at, reverse=True)
        
        return batches
    
    def delete_batch(self, batch_id: str) -> bool:
        """Delete a batch
        
        Args:
            batch_id: Batch to delete
            
        Returns:
            True if deleted successfully
        """
        if batch_id not in self.active_batches:
            return False
        
        # Only allow deletion of completed, failed, or cancelled batches
        batch_request = self.active_batches[batch_id]
        if batch_request.status in [BatchStatus.PENDING, BatchStatus.RUNNING]:
            return False
        
        # Remove from memory
        del self.active_batches[batch_id]
        
        # Remove file
        try:
            batch_file = self.batch_dir / f"batch_{batch_id}.json"
            if batch_file.exists():
                batch_file.unlink()
            return True
        except Exception as e:
            print(f"Error deleting batch file: {e}")
            return False
    
    def get_batch_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get results from completed batch jobs
        
        Args:
            batch_id: Batch ID
            
        Returns:
            List of job results
        """
        if batch_id not in self.active_batches:
            return []
        
        batch_request = self.active_batches[batch_id]
        results = []
        
        for job in batch_request.jobs:
            if job.status == BatchStatus.COMPLETED and job.result:
                results.append({
                    "job_id": job.id,
                    "job_name": job.name,
                    "result": job.result
                })
        
        return results
    
    def estimate_batch_cost(self, batch_id: str, curriculum_service) -> float:
        """Estimate cost for a batch
        
        Args:
            batch_id: Batch ID
            curriculum_service: Curriculum service for cost estimation
            
        Returns:
            Estimated total cost
        """
        if batch_id not in self.active_batches:
            return 0.0
        
        batch_request = self.active_batches[batch_id]
        total_cost = 0.0
        
        for job in batch_request.jobs:
            try:
                cost_estimate = curriculum_service.estimate_costs(job.params)
                total_cost += cost_estimate.get("total_cost", 0.0)
            except Exception as e:
                print(f"Error estimating cost for job {job.id}: {e}")
        
        # Update batch with estimated cost
        batch_request.estimated_cost = total_cost
        self._save_batch(batch_request)
        
        return total_cost