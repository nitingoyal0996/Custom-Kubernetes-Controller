import math
from monitor import MonitorNode

class LocalController:
    def __init__(self, node_name: str):
        self.node_name = node_name
        self.monitor = MonitorNode(self.node_name)

        self.Kp = 0.12
        self.OPERATING_POINT = 80.0
        self.CPU_UTILIZATION_RANGE = (75.0, 85.0)
        self.MIN_PODS_LIMIT = 0
        self.MAX_PODS_LIMIT = 8
        
        self.error_k = 0.0
        self.control_input_k = 0.0
        self.state = {
            "max_pods": 0,
            "measured_cpu_util": 0.0,
        }

    def update_state(self):
        measured_cpu_util = self.monitor.get_node_cpu_util()
        if not measured_cpu_util:
            return

        self.state["measured_cpu_util"] = measured_cpu_util
        self.error_k = (self.OPERATING_POINT - measured_cpu_util)
        # u(k) = Kp * e(k)
        self.control_input_k = self.Kp * self.error_k

        if self.control_input_k > self.MAX_PODS_LIMIT:
            self.state["max_pods"] = self.MAX_PODS_LIMIT
        elif self.control_input_k < self.MIN_PODS_LIMIT:
            self.state["max_pods"] = self.MIN_PODS_LIMIT
        else:
            self.state["max_pods"] = math.floor(self.control_input_k)