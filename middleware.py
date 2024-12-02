from monitor import MonitorNode
import time
import logging
from kubernetes import client, config

class Middleware:
    def __init__(self, controller_1, controller_2, controller_3):
        self.target_cluster_util = 80
        self.MAX_CLUSTER_PODS = 0
        self.current_node_index = 0
        self.node_added_before = 0      # seconds
        self.failure_cool_down = 0      # seconds
        
        config.load_kube_config()
        self.core_v1_api = client.CoreV1Api()
        
        # keeps track of the nodes in the cluster
        self.nodes = {
            0: {
                "name": "node0",
                "ip": "128.110.217.121",
                "label": {"nodetype": "worker0", "role": "master"},
                "controller": controller_1,
                "can_remove": False,
                "was_removed": False,
                "failure_detected": False,
                "is_active": True,
                "low_util_count": 0
            },
            1: {
                "name": "node1.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us",
                "ip": "128.110.217.136",
                "label": {"nodetype": "worker1", "role": "worker"},
                "controller": controller_2,
                "can_remove": True,
                "was_removed": False,
                "failure_detected": False,
                "is_active": False,
                "low_util_count": 0
            },
            2: {
                "name": "node2.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us",
                "ip": "128.110.217.157",
                "label": {"nodetype": "worker2", "role": "worker"},
                "controller": controller_3,
                "can_remove": True,
                "was_removed": False,
                "failure_detected": False,
                "is_active": False,
                "low_util_count": 0
            }
        }
        self.cluster_metrics = {}

    # make sure the nodes in the middleware are active
    def refresh_active_nodes(self):
        print('####################################')
        logging.info("Heartbeat...")
        nodes = self.core_v1_api.list_node()
        node_info = [{"name": node.metadata.name, "role": node.metadata.labels.get("role", "unknown")} for node in nodes.items]
        # make cluster nodes active to allow for job submission
        active_node_names = [info["name"] for info in node_info]
        # log active_node_count into to cluster_metrics
        if "active_node_count" not in self.cluster_metrics:
            self.cluster_metrics["active_node_count"] = []
        self.cluster_metrics["active_node_count"].append({
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            "value": len(active_node_names)
        })
        
        for node in self.nodes.values():
            if node["name"] in active_node_names:
                node["is_active"] = True
                for info in node_info:
                    if node["name"] == info["name"]:
                        node["label"]["role"] = info["role"]
                    if info["role"] == "master":
                        node["can_remove"] = False
            else:
                if node["is_active"] and not node["was_removed"]:
                    logging.info(f"Middleware: Node {node['name']} failure detected.")
                    node["failure_detected"] = True
                    self.failure_cool_down = time.time()
                node["is_active"] = False
        # log the self.nodes dictionary in well formatted way
        for node in self.nodes.values():
            logging.info(f"Middleware: Node State: {node['name']}, is_active: {node['is_active']}, can_remove: {node['can_remove']}, was_removed: {node['was_removed']}, failure_detected: {node['failure_detected']}")

    def update_local_states(self):
        print('------------------------------------')
        logging.info("Local States...")
        self.get_total_pods()  # record metric
        for node in self.nodes.values():
            if node["is_active"]:
                node["controller"].update_state()
        # current total_pods running and then add the allowed pods on each node.
        # self.MAX_CLUSTER_PODS = self.get_total_pods()
        self.MAX_CLUSTER_PODS = 0
        for node in self.nodes.values():
            if node["is_active"]:
                max_nodes_allowed = node["controller"].state["max_pods"]
                max_pod_on_node = max_nodes_allowed + node["controller"].monitor.get_running_pod_count()
                self.MAX_CLUSTER_PODS += max_pod_on_node
        logging.info(f"Middleware: Updated cluster max_pods: {self.MAX_CLUSTER_PODS}")
        if "max_pods" not in self.cluster_metrics:
            self.cluster_metrics["max_pods"] = []
        self.cluster_metrics["max_pods"].append({
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            "value": self.MAX_CLUSTER_PODS
        })
        print('------------------------------------')

    def avg_cluster_cpu_capacity(self):
        cpu_utils = [node["controller"].monitor.current_util for node in self.nodes.values() if node["is_active"]]
        if not cpu_utils:
            logging.info("Middleware: No active nodes to calculate CPU utilization.")
            return 0
        avg_cpu_util = sum(cpu_utils) / len(cpu_utils)
        logging.info(f"Middleware: Average CPU utilization for cluster is {avg_cpu_util}%")
        return avg_cpu_util
    
    def check_metrics_availability(self):
        retries = 5
        for _ in range(retries):
            try:
                metrics = self.core_v1_api.list_node()  # Or any other metrics call
                if metrics:
                    logging.info("Metrics API is available.")
                    return True
            except client.rest.ApiException as e:
                logging.error(f"Error accessing metrics API: {e}")
            time.sleep(5)
        logging.error("Failed to access metrics API after retries.")
        return False
    
    def add_node(self, node_name):
        node_info = next(node for node in self.nodes.values() if node["name"] == node_name)
        node = client.V1Node(
            api_version="v1",
            kind="Node",
            metadata=client.V1ObjectMeta(
                name=node_info["name"],
                labels=node_info["label"]
            ),
            status=client.V1NodeStatus(
                addresses=[
                    client.V1NodeAddress(
                    type="InternalIP",
                    address=node_info["ip"]
                    )
                ]
            )
        )
        try:
            if self.node_added_before and time.time() - self.node_added_before < 60:
                logging.info("Middleware: A new node was added in the last 1 minutes. Skipping node addition.")
                return
            self.core_v1_api.create_node(body=node)
            logging.info(f"Middleware: Node {node_info['name']} created successfully")
        except client.rest.ApiException as e:
            logging.error(f"Middleware: Error creating node: {e}")
        
        while True:
            nodes = self.core_v1_api.list_node()
            if any(n.metadata.name == node_info["name"] for n in nodes.items):
                logging.info(f"Middleware: Node {node_info['name']} is now part of the cluster")
                # make node available
                node_info["is_active"] = True
                node_info["can_remove"] = True
                node_info["was_removed"] = False
                node_info["low_util_count"] = 0
                self.node_added_before = time.time()
                break
            logging.info(f"Middleware: Waiting for node {node_info['name']} to be added to the cluster...")
            time.sleep(5)

    def remove_node(self, node_name):
        node_info = next(node for node in self.nodes.values() if node["name"] == node_name)
        try:
            # Delete the node
            self.core_v1_api.delete_node(name=node_name)
            logging.info(f"Middleware: {node_name} removed successfully")
            node_info["is_active"] = False
            node_info["can_remove"] = True
            node_info["was_removed"] = True
        except client.rest.ApiException as e:
            logging.error(f"Middleware: Error deleting node: {e}")

    def find_inactive_nodes(self):
        for node in self.nodes.values():
            if not node["is_active"]:
                if node["failure_detected"] and time.time() - self.failure_cool_down < 60:
                    logging.info("Middleware: Node failure was detected in the last 1 minutes. Skipping node addition for now.")
                    continue
                else:
                    return node["name"]
        return None

    # fill the nodes in orde
    def determine_next_node(self):
        active_nodes = [node for node in self.nodes.values() if node["is_active"]]
        for node in active_nodes:
            # validate if selected node has capacity
            if node["controller"].monitor.has_pod_capacity(node["controller"].state["max_pods"]):
                return node["name"]
        logging.info("Middleware: No active nodes have available pod capacity. Checking for inactive nodes to add.")
        return None

    def determine_node_to_remove(self):
        # determine the node with lowest CPU utilization
        active_nodes = [node for node in self.nodes.values() if node["is_active"] and node["can_remove"]]
        if not active_nodes:
            return None
        node = min(active_nodes, key=lambda x: x["controller"].monitor.current_util)
        return node["name"]

    def get_total_pods(self):
        try:
            pod_list = self.core_v1_api.list_namespaced_pod(
                namespace="jobs"
            )
            running_pods = len([pod for pod in pod_list.items if pod.status.phase == 'Running'])
            if "total_pods" not in self.cluster_metrics:
                self.cluster_metrics["total_pods"] = []
            self.cluster_metrics["total_pods"].append({
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                "value": running_pods
            })
            return running_pods
        except client.ApiException as e:
            print(f"Failed to check node capacity: {e}")
            return None

    # remove all jobs when removing a node
    def cleanup_node(self, node_name):
        try:
            pod_list = self.core_v1_api.list_namespaced_pod(
                namespace="jobs", 
                field_selector=f'spec.nodeName={node_name}'
            )
            for pod in pod_list.items:
                self.core_v1_api.delete_namespaced_pod(name=pod.metadata.name, namespace=pod.metadata.namespace)
        except client.ApiException as e:
            logging.error(f"Failed to delete pods: {e}")
    
    # remove all jobs from the cluster when stopping the global controller
    def cleanup_cluster(self): 
        for node in self.nodes.values():
            if node["is_active"]:
                self.cleanup_node(node["name"])
    
    def save_metrics(self):
        # save the cluster_metric to csv file
        import csv
        with open('cluster_metrics.csv', mode='w') as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "active_node_count", "max_pods", "total_pods"])
            for i in range(len(self.cluster_metrics["active_node_count"])):
                writer.writerow([
                    self.cluster_metrics["active_node_count"][i]["timestamp"],
                    self.cluster_metrics["active_node_count"][i]["value"],
                    self.cluster_metrics["max_pods"][i]["value"],
                    self.cluster_metrics["total_pods"][i]["value"]
                ])
