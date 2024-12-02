import time
import logging
from jobs.job import JobSubmitter as Job

class GlobalController:
    def __init__(self, middleware):
        self.middleware = middleware
        
        self.DESIRED_CPU_UTILIZATION_RANGE = (75, 85)
        self.OPERATING_POINT = 80.0
        self.SCALE_DOWN_THRESHOLD = 0.2
        self.polling_interval = 15
        
        self.LOW_CYCLE_COUNT = 4
        self.low_cluster_util_count_down = self.LOW_CYCLE_COUNT

    def run(self, queue):
        last_job_submission_time = 0
        try:
            while True:
                if not self.middleware.check_metrics_availability():
                    logging.error("Global Controller: Metrics not available... skipping cycle.")
                    time.sleep(self.polling_interval)
                    continue
                current_time = time.time()
                # heartbeat
                self.middleware.refresh_active_nodes()
                # call local controllers to update their states based on local metrics
                self.middleware.update_local_states()
                # determine average cluster CPU utilization
                avg_cluster_cpu_util = self.middleware.avg_cluster_cpu_capacity()

                # rule based global controller
                if avg_cluster_cpu_util > self.OPERATING_POINT:
                    # UPSCALE
                    # wait until either - a node is available to add to the cluster or CPU utilization decreases
                    logging.critical("Global Controller: Attempting to scale up...")
                    node_name = self.middleware.find_inactive_nodes()
                    if node_name:
                        self.middleware.add_node(node_name)
                    else:
                        logging.info("Global Controller: No more available nodes to add.")
                    self.low_cluster_util_count_down = self.LOW_CYCLE_COUNT
                elif avg_cluster_cpu_util < self.SCALE_DOWN_THRESHOLD * self.OPERATING_POINT:
                    # DOWNSCALE
                    # wait for at least 5 continuous cycles before scaling down
                    self.low_cluster_util_count_down -= 1
                    logging.critical(f"Global Controller: Attempting to scale down in...{self.low_cluster_util_count_down} cycles")
                    if self.low_cluster_util_count_down == 0:
                        # look for unused nodes and remove them
                        remove_node_name = self.middleware.determine_node_to_remove()
                        if remove_node_name:
                            self.middleware.remove_node(remove_node_name)
                        self.low_cluster_util_count_down = self.LOW_CYCLE_COUNT # reset
                
                # default case
                # MAINTAIN and SUBMIT JOBS
                node_name = self.middleware.determine_next_node()
                logging.info('Global Controller: Next node to submit job: %s', node_name)
                if node_name:
                    if queue.has_next_job() and current_time - last_job_submission_time >= 15:
                        job_args = queue.get_next_job().to_args_list()
                        job = Job(node_name, job_args)
                        job.submit()
                        last_job_submission_time = current_time
                    else:
                        logging.info("Global Controller: No more jobs in the queue.")
                        # exit the program
                        self.middleware.save_metrics()
                else:
                    logging.info("Global Controller: All nodes have reached max pod capacity.")
                time.sleep(self.polling_interval)

        except KeyboardInterrupt:
            print("\nGlobal Controller: Simulation stopped by user.")
            self.middleware.cleanup_cluster()
