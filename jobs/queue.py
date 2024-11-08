from queue import Queue
from .job import Job
from typing import Optional

class JobQueue:
    def __init__(self, queue_file: str):
        self.queue_file = queue_file
        self.job_queue = Queue()
        self.load_jobs()
        
    def load_jobs(self):
        try:
            with open(self.queue_file, 'r') as f:
                for line in f:
                    # Example: stress-ng --io 4 --vm 5 --vm-bytes 2G --timeout 5m
                    job = Job(line.strip())
                    self.job_queue.put(job)
        except Exception as e:
            print(f"Error loading job queue: {e}")
            
    def get_next_job(self) -> Optional[Job]:
        if not self.job_queue.empty():
            return self.job_queue.get()
        return None