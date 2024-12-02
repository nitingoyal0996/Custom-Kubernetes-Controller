import logging
from kubernetes import client, config

class MonitorNode:
    def __init__(self, node):
        self.node_name = node
        self.current_util = 0.0
        
        config.load_kube_config()
        self.core_v1_api = client.CoreV1Api()
        # metric api
        self.custom_api = client.CustomObjectsApi()
        
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
            logging.info(f"Node: {self.node_name}: CPU utilization: {cpu_util}%")
            return cpu_util

        except Exception as e:
            logging.error(f"Node: {self.node_name}: Error getting metrics: {e}")
    
    def get_running_pod_count(self):
        pod_list = self.core_v1_api.list_namespaced_pod(
            namespace="jobs",
            field_selector=f'spec.nodeName={self.node_name}'
        )
        running_pods = len([pod for pod in pod_list.items if pod.status.phase == 'Running'])
        return running_pods
    
    def has_pod_capacity(self, max_pods_allowed_by_ctrlr) -> bool:
        try:
            running_pods = self.get_running_pod_count()
            max_pods = running_pods + max_pods_allowed_by_ctrlr
            logging.info(f"Node: {self.node_name}: Running {running_pods} out of {max_pods}")
            return running_pods < max_pods

        except client.ApiException as e:
            logging.error(f"Node: {self.node_name}: Failed to check node capacity: {e}")
            return False
