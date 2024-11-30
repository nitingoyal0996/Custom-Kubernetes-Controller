import logging
from kubernetes import client, config

class MonitorNode:
    def __init__(self, node, target_node_util):
        self.node_name = node
        self.target_cpu_util = target_node_util
        self.current_util = 0.0
        
        config.load_kube_config()        
        self.custom_api = client.CustomObjectsApi()
        self.core_v1_api = client.CoreV1Api()
        
    def get_node_cpu_util(self):
        try:
            metrics = self.custom_api.get_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes",
                name=self.node_name
            )

            cpu_usage = metrics['usage']['cpu']
            if cpu_usage.endswith('n'):
                cpu_usage_nano = float(cpu_usage.rstrip('n'))
            elif cpu_usage.endswith('u'):
                cpu_usage_nano = float(cpu_usage.rstrip('u')) * 1000
            else:
                raise ValueError(f"Unsupported CPU metric unit: {cpu_usage}")

            node = self.core_v1_api.read_node(self.node_name)
            cpu_capacity = float(node.status.capacity['cpu']) * 1e9

            cpu_util = (cpu_usage_nano / cpu_capacity) * 100
            self.current_util = cpu_util
            logging.info(f"CPU utilization for node {self.node_name}: {cpu_util}%")
            return cpu_util

        except Exception as e:
            logging.error(f"Error getting metrics: {e}")
