from queue import Queue
from typing import Optional
from dataclasses import dataclass, field
import re

@dataclass
class Job:
    cmd: str
    stressors: dict = field(default_factory=dict)
    duration: Optional[str] = None

    def __init__(self, cmd: str):
        self.cmd = cmd
        self.stressors = self.parse_stressors(cmd)
        
    def parse_stressors(self, cmd: str) -> dict:
        """Parse the stress-ng command options and store them in a dictionary."""
        args = cmd.split()
        stressors = {}
        i = 1               # Start after "stress-ng" command
        
        while i < len(args):
            if args[i] == "--cpu":
                stressors["cpu"] = int(args[i + 1])
                i += 2
            elif args[i] == "--io":
                stressors["io"] = int(args[i + 1])
                i += 2
            elif args[i] == "--vm":
                stressors["vm"] = int(args[i + 1])
                i += 2
            elif args[i] == "--vm-bytes":
                stressors["vm-bytes"] = args[i + 1]
                i += 2
            elif args[i] == "--timeout":
                stressors["timeout"] = args[i + 1]
                i += 2
            else:
                i += 1

        return stressors

    def to_args_list(self) -> list:
        args = []
        for key, value in self.stressors.items():
            if key == "metrics-brief" and value is True:
                args.append(f"--{key}")
            else:
                args.extend([f"--{key}", str(value)])
        args.append("--metrics-brief")
        return args

class JobQueue:
    def __init__(self, queue_file: str):
        self.queue_file = queue_file
        self.job_queue = Queue()
        self.load_jobs()
        
    def load_jobs(self):
        try:
            with open(self.queue_file, 'r') as f:
                for line in f:
                    # Convert each line into a Job object and enqueue
                    job = Job(cmd=line.strip())
                    self.job_queue.put(job)
        except Exception as e:
            print(f"Error loading job queue: {e}")
            
    def get_next_job(self) -> Optional[Job]:
        if not self.job_queue.empty():
            return self.job_queue.get()
        return None

    def has_next_job(self) -> bool:
        return not self.job_queue.empty()