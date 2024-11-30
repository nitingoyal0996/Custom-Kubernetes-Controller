from kubernetes import client, config
import math
from args import Params
from monitor import MonitorNode

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
        self.monitor = MonitorNode(self.node_name, 80.0)

        self.TARGET_CPU_UTILIZATION = 80.0
        self.CPU_UTILIZATION_RANGE = (75.0, 85.0)
        self.MIN_PODS_LIMIT = 0
        self.MAX_PODS_LIMIT = 8
        
        # Initialize control and system state variables
        self.error_k = 0.0           # Error at time (k)
        self.error_k_1 = 0.0         # Error at time (k-1)
        self.control_input_k = 0.0   # Control input at time (k)
        self.control_input_k_1 = 0.0 # Control input at time (k-1)
        
        self.state = {
            "max_pods": 0,
            "measured_cpu_util": 0.0,
        }

    def update_state(self):
        measured_cpu_util = self.monitor.get_node_cpu_util()
        self.state["measured_cpu_util"] = measured_cpu_util

        self.error_k_1 = self.error_k
        self.control_input_k_1 = self.control_input_k
        
        self.error_k = (self.TARGET_CPU_UTILIZATION - measured_cpu_util)

        # u(k) = u(k − 1) + (Kp + Ki)*e(k) − Kp*e(k − 1)
        adjustment = (self.Kp + self.Ki) * self.error_k - self.Kp * self.error_k_1
        self.control_input_k = adjustment + self.control_input_k_1
        print(f"Measured CPU Utilization = {measured_cpu_util:.2f}%, \nError = {self.error_k:.2f} \nError Adjustment: {adjustment:.2f} \nControl Input: {self.control_input_k:.2f}\n---------------------------------")

        if self.control_input_k > self.MAX_PODS_LIMIT:
            self.state["max_pods"] = self.MAX_PODS_LIMIT
        elif self.control_input_k < self.MIN_PODS_LIMIT:
            self.state["max_pods"] = self.MIN_PODS_LIMIT
        else:
            self.state["max_pods"] = math.floor(self.control_input_k)

        if self.CPU_UTILIZATION_RANGE[0] <= measured_cpu_util <= self.CPU_UTILIZATION_RANGE[1]:
            print("CPU utilization is within the desired range.")
        else:
            print("Adjusting Pods to bring utilization into range.\n---------------------------------")
    
    def has_capacity(self) -> bool:
        try:
            pod_list = self.core_v1_api.list_namespaced_pod(
                namespace="jobs",
                field_selector=f'spec.nodeName={self.node_name}'
            )
            running_pods = len([pod for pod in pod_list.items if pod.status.phase == 'Running'])
            MAX_PODS = self.state["max_pods"]
            print(f"Running pods: {running_pods}", f"Max pods: {MAX_PODS}")
            return running_pods < MAX_PODS

        except client.ApiException as e:
            print(f"Failed to check node capacity: {e}")
            return False


if __name__ == "__main__":
    controllerParams = {
        'a': 0.8709,
        'b': -0.6688,
        'Kp': 0.094,
        'Ki': 0.006,
        'polling_interval': 15,
        'node_name': "node1.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us"
    }
    params = controllerParams
    controller = LocalController(params)
    def run():
        import time
        while True:
            controller.update_state()
            controller.has_capacity()    
            time.sleep(5)
    run()