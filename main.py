import logging
from local_controller import LocalController
from jobs.queue import JobQueue
from middleware import Middleware
from global_controller import GlobalController

def main():

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        job_queue = JobQueue('./static/jobs.txt')

        # node 2
        # controllerParams = {
        #     'a': 0.8709,
        #     'b': -0.6688,
        #     'Kp': 0.8,
        #     'Ki': 0.006,
        #     'node_name': "node2.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us"
        # }
        controller1 = LocalController("node0")
        controller2 = LocalController("node1.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us")
        controller3 = LocalController("node2.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us")
        middleware = Middleware(controller1, controller2, controller3)
        globalController = GlobalController(middleware)

        globalController.run(job_queue)
        print("No more jobs in the queue.")
    except KeyboardInterrupt:
        print("Controller stopped.")


if __name__ == "__main__":
    main()