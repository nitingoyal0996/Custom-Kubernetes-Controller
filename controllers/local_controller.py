from kubernetes import client, config
import time
import math
from .args import Params
import pandas as pd
from jobs.job import JobSubmitter as Job

class LocalController:
    def __init__(self, params: Params):
        print(params)
        self.node_name = params['node_name']
        self.a  = params['a']
        self.b  = params['b']
        self.Kp = params['Kp']
        self.Ki = params['Ki']
        self.polling_interval = params['polling_interval']

        config.load_kube_config()
        self.core_v1_api = client.CoreV1Api()
        self.custom_api  = client.CustomObjectsApi()

        self.TARGET_CPU_UTILIZATION = 80.0
        self.CPU_UTILIZATION_RANGE = (75.0, 85.0)
        self.MIN_PODS_LIMIT = 0
        self.MAX_PODS_LIMIT = 8

        self.MAX_PODS = 0
        
        # Initialize control and system state variables
        self.error_k = 0.0           # Error at time (k)
        self.error_k_1 = 0.0         # Error at time (k-1)
        self.control_input_k = 0.0   # Control input at time (k)
        self.control_input_k_1 = 0.0 # Control input at time (k-1)
        
        self.metrics = []
        

    def get_node_metrics(self):
        try:
            # Fetch node metrics
            metrics = self.custom_api.get_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes",
                name=self.node_name
            )

            # Handle CPU usage with different units
            cpu_usage = metrics['usage']['cpu']
            if cpu_usage.endswith('n'):  # Nanoseconds
                cpu_usage_nano = float(cpu_usage.rstrip('n'))
            elif cpu_usage.endswith('u'):  # Microseconds
                cpu_usage_nano = float(cpu_usage.rstrip('u')) * 1000
            else:
                raise ValueError(f"Unsupported CPU metric unit: {cpu_usage}")

            # Fetch node capacity
            node = self.core_v1_api.read_node(self.node_name)
            cpu_capacity = float(node.status.capacity['cpu']) * 1e9  # Convert to nanoseconds

            # Calculate CPU usage percentage
            cpu_utilization = (cpu_usage_nano / cpu_capacity) * 100
            return cpu_utilization

        except Exception as e:
            print(f"Error getting metrics: {e}")
            return None


    def update(self):

        measured_cpu_utilization = self.get_node_metrics()

        self.error_k_1 = self.error_k
        self.control_input_k_1 = self.control_input_k
        
        self.error_k = (self.TARGET_CPU_UTILIZATION - measured_cpu_utilization)

        # u(k) = u(k − 1) + (Kp + Ki)*e(k) − Kp*e(k − 1)
        adjustment = (self.Kp + self.Ki) * self.error_k - self.Kp * self.error_k_1
        self.control_input_k = adjustment + self.control_input_k_1
        print(f"Measured CPU Utilization = {measured_cpu_utilization:.2f}%, \nError = {self.error_k:.2f} \nError Adjustment: {adjustment:.2f} \nControl Input: {self.control_input_k:.2f}")

        if self.control_input_k > self.MAX_PODS_LIMIT:
            self.MAX_PODS = self.MAX_PODS_LIMIT
        elif self.control_input_k < self.MIN_PODS_LIMIT:
            self.MAX_PODS = self.MIN_PODS_LIMIT
        else:
            self.MAX_PODS = math.floor(self.control_input_k)

        self.metrics.append([self.MAX_PODS, measured_cpu_utilization, self.error_k])

        if self.CPU_UTILIZATION_RANGE[0] <= measured_cpu_utilization <= self.CPU_UTILIZATION_RANGE[1]:
            print("CPU utilization is within the desired range.")
        else:
            print("Adjusting Pods to bring utilization into range.")

    def has_capacity(self) -> bool:
        try:
            pod_list = self.core_v1_api.list_namespaced_pod(
                namespace="jobs",
                field_selector=f'spec.nodeName={self.node_name}'
            )
            running_pods = len([pod for pod in pod_list.items if pod.status.phase == 'Running'])
            print(f"Running pods: {running_pods}", f"Max pods: {self.MAX_PODS}")
            return running_pods < self.MAX_PODS

        except client.ApiException as e:
            print(f"Failed to check node capacity: {e}")
            return False
        
    def cleanup(self):
        # remove all jobs
        try:
            pod_list = self.core_v1_api.list_namespaced_pod(
                namespace="jobs", 
                field_selector=f'spec.nodeName={self.node_name}'
            )
            for pod in pod_list.items:
                self.core_v1_api.delete_namespaced_pod(name=pod.metadata.name, namespace=pod.metadata.namespace)
        except client.ApiException as e:
            print(f"Failed to delete pods: {e}")

    def draw_and_save_plot_over_time(self, data):
        import matplotlib.pyplot as plt

        # create subplots
        fig, ax1 = plt.subplots(2, 1, figsize=(12, 12))

        # plot Pods (Control Input)
        ax1[0].plot(data['Pods (Control Input)'], label='Pods (Control Input)', marker='o', color='blue')
        ax1[0].set_xlabel('Time (5s intervals)')
        ax1[0].set_ylabel('Pods')
        ax1[0].set_title('Controller Simulation: Pods vs CPU Utilization')
        ax1[0].legend()
        ax1[0].grid()

        # plot Measured CPU Utilization
        ax1[1].plot(data['Measured CPU Utilization'], label='Measured CPU Utilization', marker='o', color='green')
        ax1[1].set_xlabel('Time (5s intervals)')
        ax1[1].set_ylabel('CPU Utilization (%)')
        ax1[1].legend()
        ax1[1].grid()

        plt.tight_layout()
        plt.savefig('controller_simulation.png')
        plt.show()

    def run(self, queue):
        last_job_submission_time = 0
        try:
            while True:
                self.update()
                print('Adjusted max_pods: ', self.MAX_PODS)
                current_time = time.time()
                if self.has_capacity():
                    if queue.has_next_job() and current_time - last_job_submission_time >= 15:
                        job_args = queue.get_next_job().to_args_list()
                        job = Job(self.node_name, job_args)
                        job.submit()
                        last_job_submission_time = current_time
                    else:
                        print("No more jobs in the queue.")
                else:
                    print("No capacity to run more jobs.")

                time.sleep(self.polling_interval)
        except KeyboardInterrupt:
            print("Simulation stopped by user.")
            data = pd.DataFrame(self.metrics, columns=['Pods (Control Input)', 'Measured CPU Utilization', 'Error'])
            data.to_csv('./local_controller_run.csv', index=False)
            print("Simulation data saved to 'controller_simulation_data.csv'.")
            self.draw_and_save_plot_over_time(data)
            self.cleanup()