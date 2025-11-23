"""
Thread Manager for InstaSchool Application
Provides safe thread lifecycle management and cancellation
"""
import threading
import time
from typing import Dict, Optional, Callable, Any
from contextlib import contextmanager
import weakref

class ManagedThread(threading.Thread):
    """Thread with cancellation support"""
    
    def __init__(self, target: Callable, args: tuple = (), kwargs: dict = None):
        super().__init__(target=self._wrapped_target, args=args, kwargs=kwargs or {})
        self._target = target
        self._cancelled = threading.Event()
        self._completed = threading.Event()
        self._exception = None
        
    def _wrapped_target(self, *args, **kwargs):
        """Wrapper that checks for cancellation"""
        try:
            # Pass cancellation event to target if it accepts it
            if 'cancellation_event' in self._target.__code__.co_varnames:
                kwargs['cancellation_event'] = self._cancelled
            
            self._target(*args, **kwargs)
            self._completed.set()
        except Exception as e:
            self._exception = e
            self._completed.set()
            raise
    
    def cancel(self):
        """Request cancellation"""
        self._cancelled.set()
    
    def is_cancelled(self) -> bool:
        """Check if cancellation requested"""
        return self._cancelled.is_set()
    
    def is_completed(self) -> bool:
        """Check if thread completed"""
        return self._completed.is_set()
    
    def get_exception(self) -> Optional[Exception]:
        """Get exception if thread failed"""
        return self._exception
    
    def join_with_timeout(self, timeout: float = 5.0) -> bool:
        """Join with timeout and return success status"""
        self.join(timeout=timeout)
        return not self.is_alive()


class ThreadManager:
    """Manages thread lifecycle and cleanup"""
    
    def __init__(self):
        self._threads: Dict[str, weakref.ref] = {}
        self._lock = threading.Lock()
    
    def create_thread(self, thread_id: str, target: Callable, *args, **kwargs) -> ManagedThread:
        """Create and register a managed thread"""
        thread = ManagedThread(target, args, kwargs)
        
        with self._lock:
            self._threads[thread_id] = weakref.ref(thread)
            # Clean up dead references
            self._cleanup_dead_threads()
        
        return thread
    
    def start_thread(self, thread_id: str, target: Callable, *args, **kwargs) -> ManagedThread:
        """Create and start a managed thread"""
        thread = self.create_thread(thread_id, target, *args, **kwargs)
        thread.start()
        return thread
    
    def cancel_thread(self, thread_id: str) -> bool:
        """Cancel a thread by ID"""
        with self._lock:
            thread_ref = self._threads.get(thread_id)
            if thread_ref:
                thread = thread_ref()
                if thread and thread.is_alive():
                    thread.cancel()
                    return True
        return False
    
    def wait_for_thread(self, thread_id: str, timeout: float = 5.0) -> bool:
        """Wait for a thread to complete"""
        with self._lock:
            thread_ref = self._threads.get(thread_id)
            if thread_ref:
                thread = thread_ref()
                if thread:
                    return thread.join_with_timeout(timeout)
        return True
    
    def get_thread_status(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a thread"""
        with self._lock:
            thread_ref = self._threads.get(thread_id)
            if thread_ref:
                thread = thread_ref()
                if thread:
                    return {
                        'alive': thread.is_alive(),
                        'cancelled': thread.is_cancelled(),
                        'completed': thread.is_completed(),
                        'exception': thread.get_exception()
                    }
        return None
    
    def _cleanup_dead_threads(self):
        """Remove references to dead threads"""
        dead_ids = [tid for tid, ref in self._threads.items() if ref() is None]
        for tid in dead_ids:
            del self._threads[tid]
    
    def shutdown(self, timeout: float = 10.0):
        """Cancel all threads and wait for completion"""
        with self._lock:
            # Cancel all active threads
            for thread_ref in self._threads.values():
                thread = thread_ref()
                if thread and thread.is_alive():
                    thread.cancel()
            
            # Wait for all threads to complete
            deadline = time.time() + timeout
            for thread_ref in list(self._threads.values()):
                thread = thread_ref()
                if thread and thread.is_alive():
                    remaining = deadline - time.time()
                    if remaining > 0:
                        thread.join(timeout=remaining)
    
    @contextmanager
    def managed_thread(self, thread_id: str, target: Callable, *args, **kwargs):
        """Context manager for thread lifecycle"""
        thread = self.start_thread(thread_id, target, *args, **kwargs)
        try:
            yield thread
        finally:
            if thread.is_alive():
                thread.cancel()
                thread.join_with_timeout()


# Global thread manager instance
thread_manager = ThreadManager()