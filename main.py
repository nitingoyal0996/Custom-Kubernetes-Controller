import time 
from jobs.queue import JobQueue
from jobs.job import Job
from controllers.local_controller import LocalController

def main():
    job_queue = JobQueue('./static/jobs.txt')
    controllerParams = {
        'target_utilization': 80
        }
    controller = LocalController()
    JOB_INTERVAL = 1   # seconds
    NODE_NAME = "node1.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us"
    
    while job_queue.has_next_job():
        # controller check if we could submit new job or skip it
        
        job_args = job_queue.get_next_job().to_args_list()
        print(job_args)
        
        job = Job(NODE_NAME, job_args)
        job.submit()
        
        time.sleep(JOB_INTERVAL)
        
    print("No more jobs in the queue.")


if __name__ == "__main__":
    main()