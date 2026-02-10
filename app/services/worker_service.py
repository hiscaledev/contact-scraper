"""Worker service for managing job queue with concurrency control."""
import threading
import queue
from typing import Callable, Any
from datetime import datetime
from app.core.config import get_settings


settings = get_settings()


class WorkerPool:
    """
    A worker pool that processes jobs with a maximum concurrency limit.
    """
    
    def __init__(self, max_workers: int = 2):
        """
        Initialize the worker pool.
        
        Args:
            max_workers: Maximum number of concurrent jobs (default: 2)
        """
        self.max_workers = max_workers
        self.job_queue = queue.Queue()
        self.active_workers = 0
        self.lock = threading.Lock()
        self.running = True
        
        # Start the dispatcher thread
        self.dispatcher_thread = threading.Thread(
            target=self._dispatcher,
            daemon=True
        )
        self.dispatcher_thread.start()
        
        print(f"[WorkerPool] Initialized with {max_workers} max concurrent workers")
    
    def _dispatcher(self):
        """
        Dispatcher thread that manages job assignment to workers.
        """
        while self.running:
            try:
                # Wait for a job to be available
                job_data = self.job_queue.get(timeout=1)
                
                # Wait until a worker slot is available
                while True:
                    with self.lock:
                        if self.active_workers < self.max_workers:
                            self.active_workers += 1
                            break
                    threading.Event().wait(0.5)  # Sleep briefly
                
                # Start the job in a new thread
                worker_thread = threading.Thread(
                    target=self._execute_job,
                    args=(job_data,),
                    daemon=True
                )
                worker_thread.start()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[WorkerPool] Dispatcher error: {e}")
    
    def _execute_job(self, job_data: dict):
        """
        Execute a single job.
        
        Args:
            job_data: Dictionary containing job_func, args, and kwargs
        """
        job_func = job_data["job_func"]
        args = job_data.get("args", ())
        kwargs = job_data.get("kwargs", {})
        
        try:
            print(f"[WorkerPool] Starting job (active: {self.active_workers}/{self.max_workers})")
            job_func(*args, **kwargs)
        except Exception as e:
            print(f"[WorkerPool] Job execution error: {e}")
        finally:
            with self.lock:
                self.active_workers -= 1
            print(f"[WorkerPool] Job completed (active: {self.active_workers}/{self.max_workers})")
    
    def submit_job(self, job_func: Callable, *args, **kwargs):
        """
        Submit a job to the queue.
        
        Args:
            job_func: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        job_data = {
            "job_func": job_func,
            "args": args,
            "kwargs": kwargs,
            "submitted_at": datetime.now()
        }
        self.job_queue.put(job_data)
        print(f"[WorkerPool] Job queued (queue size: {self.job_queue.qsize()})")
    
    def get_stats(self) -> dict:
        """
        Get current statistics about the worker pool.
        
        Returns:
            Dictionary with pool statistics
        """
        return {
            "max_workers": self.max_workers,
            "active_workers": self.active_workers,
            "queued_jobs": self.job_queue.qsize(),
            "available_slots": self.max_workers - self.active_workers
        }
    
    def shutdown(self):
        """
        Shutdown the worker pool gracefully.
        """
        print("[WorkerPool] Shutting down...")
        self.running = False
        self.dispatcher_thread.join(timeout=5)


# Global worker pool instance - uses max_workers from config
worker_pool = WorkerPool(max_workers=settings.max_workers)


def submit_csv_job(job_func: Callable, *args, **kwargs):
    """
    Submit a CSV processing job to the worker pool.
    
    Args:
        job_func: The processing function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments
    """
    worker_pool.submit_job(job_func, *args, **kwargs)


def get_worker_stats() -> dict:
    """
    Get current worker pool statistics.
    
    Returns:
        Dictionary with statistics
    """
    return worker_pool.get_stats()
