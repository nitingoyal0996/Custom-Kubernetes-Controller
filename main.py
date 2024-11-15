import time 
from typing import cast
from controllers.args import Params
from controllers.local_controller import LocalController
from jobs.queue import JobQueue
from jobs.job import JobSubmitter as Job

def main():
    # JOB_INTERVAL = 15   # seconds
    try:
        job_queue = JobQueue('./static/jobs.txt')
        controllerParams = {
            'a': 0.8709,
            'b': -0.6688,
            'Kp': 0.094,
            'Ki': 0.006,
            'polling_interval': 15,
            'node_name': "node1.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us"
        }
        params = cast(Params, controllerParams)
        
        controller = LocalController(params)
        controller.run(job_queue)

        print("No more jobs in the queue.")
    except KeyboardInterrupt:
        print("Controller stopped.")


if __name__ == "__main__":
    main()