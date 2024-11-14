from kubernetes import client, config
import time
import argparse
from args import Params
from typing import cast
import pandas as pd

class LocalController:
    def __init__(self, params: Params):
        self.node_name = params.node_name
        self.a  = params.a
        self.b  = params.b
        self.Kp = params.Kp
        self.Ki = params.Ki
        self.polling_interval = params.polling_interval

        config.load_kube_config()
        self.core_v1_api = client.CoreV1Api()
        self.custom_api  = client.CustomObjectsApi()

        self.TARGET_CPU_UTILIZATION = 80.0
        self.CPU_UTILIZATION_RANGE = (75.0, 85.0)
        self.MIN_PODS_LIMIT = 0
        self.MAX_PODS_LIMIT = 8
        
        # Initialize control and system state variables
        self.error_k = 0.0           # Error at time (k)
        self.error_k_1 = 0.0         # Error at time (k-1)
        self.control_input_k = 0.0   # Control input at time (k)
        self.control_input_k_1 = 0.0 # Control input at time (k-1)
        

    def get_node_metrics(self):
        try:
            metrics = self.custom_api.get_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes",
                name=self.node_name
            )
            print(f"Metrics: {metrics['usage']}")
            cpu_usage_nano = metrics['usage']['cpu'].rstrip('n')
            node = self.core_v1_api.read_node(self.node_name)
            cpu = int(node.status.capacity['cpu'])
            cpu_capacity = cpu * 1000000000
            cpu_usage = float(float(cpu_usage_nano) / cpu_capacity) * 100
            print(f"CPU Utilization: {cpu_usage:.2f}%")
            return cpu_usage
        except Exception as e:
            print(f"Error getting metrics: {e}")
            return None

    def run_continuously(self):

        print(f"Starting controller for node: {self.node_name}")
        print(f"Target CPU utilization: {self.TARGET_CPU_UTILIZATION}%")
        print(f"Polling interval: {self.polling_interval} seconds")
        print("Press Ctrl+C to stop...")

        metrics = []

        try:
            while True:
                measured_cpu_utilization = self.get_node_metrics()
                # save previous controller states
                self.error_k_1 = self.error_k
                self.control_input_k_1 = self.control_input_k
                
                self.error_k = self.TARGET_CPU_UTILIZATION - measured_cpu_utilization

                
                # u(k) = u(k − 1) + (Kp + Ki)*e(k) − Kp*e(k − 1)
                self.control_input_k = self.control_input_k_1 + (self.Kp + self.Ki) * self.error_k - self.Kp * self.error_k_1

                if self.control_input_k > self.MAX_PODS_LIMIT:
                    self.control_input_k = self.MAX_PODS_LIMIT
                elif self.control_input_k < self.MIN_PODS_LIMIT:
                    self.control_input_k = self.MIN_PODS_LIMIT

                print(f"Pods = {self.control_input_k}, Measured CPU Utilization = {measured_cpu_utilization:.2f}%, Error = {self.error_k:.2f}")
                metrics.append([self.control_input_k, measured_cpu_utilization, self.error_k])

                if self.CPU_UTILIZATION_RANGE[0] <= measured_cpu_utilization <= self.CPU_UTILIZATION_RANGE[1]:
                    print("CPU utilization is within the desired range.")
                else:
                    print("Adjusting Pods to bring utilization into range.")

                time.sleep(self.polling_interval)
        except KeyboardInterrupt:
            print("Simulation stopped by user.")
            data = pd.DataFrame(metrics, columns=['Pods (Control Input)', 'Measured CPU Utilization', 'Error'])
            data.to_csv('./data/controller_simulation_data.csv', index=False)
            print("Simulation data saved to 'controller_simulation_data.csv'.")
            
    def has_capacity() -> bool:
        # get current number of pods
        # check current max pods
        return True

if __name__ == "__main__":
    NODE_NAME = "node1.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us"

    # Create a new instance of the LocalController with Params
    parser = argparse.ArgumentParser("Submit controller parameters - a, b, Kp, Ki, polling_interval, node_name")
    parser.add_argument("--a", type=float, default=-0.001, help="Controller parameter a")
    parser.add_argument("--b", type=float, default=10.43, help="Controller parameter b")
    parser.add_argument("--Kp", type=float, default=0.0019, help="Controller parameter Kp")
    parser.add_argument("--Ki", type=float, default=0.088, help="Controller parameter Ki")
    parser.add_argument("--polling_interval", type=int, default=30, help="Polling interval in seconds")
    parser.add_argument("--node_name", type=str, default=NODE_NAME, help="Node name to control")
    args = parser.parse_args()
    params = cast(Params, args)
    controller = LocalController(params)

    controller.run_continuously()
