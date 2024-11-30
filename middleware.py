from monitor import MonitorNode
import time
import logging
from kubernetes import client, config

class Middleware:
    def __init__(self, target_cluster_util, controller_1, controller_2, controller_3):
        self.target_cluster_util = target_cluster_util
        self.MAX_PODS = 0
        self.current_node_index = 0
        # keeps track of the nodes in the cluster
        self.nodes = {
            0: {
                "name": "node0",
                "ip": "128.110.217.121",
                "label": {"role": "master"},
                "controller": controller_1,
                "can_remove": False,
                "is_active": True,
            },
            1: {
                "name": "node1.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us",
                "ip": "128.110.217.136",
                "label": {"role": "worker"},
                "controller": controller_2,
                "can_remove": True,
                "is_active": True,
            },
            2: {
                "name": "node2.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us",
                "ip": "128.110.217.157",
                "label": {"role": "worker"},
                "controller": controller_3,
                "can_remove": True,
                "is_active": True,
            }
        }

    def get_next_node(self):
        active_nodes = [node for node in self.nodes.values() if node["is_active"]]
        if not active_nodes:
            return None
        next_node = active_nodes[self.current_node_index % len(active_nodes)]
        self.current_node_index += 1
        return next_node["name"]

    def has_cluster_pod_capacity(self):
        total_pods = self.controller_1.MAX_PODS + self.controller_2.MAX_PODS + self.controller_3.MAX_PODS
        if total_pods < self.controller_1.MAX_PODS_LIMIT + self.controller_2.MAX_PODS_LIMIT + self.controller_3.MAX_PODS_LIMIT:
            logging.info(f"Cluster has capacity for {total_pods} pods.")
            return True
        return False

    def has_cluster_cpu_capacity(self):
        cpu_utils = []
        for controller in [self.controller_1, self.controller_2, self.controller_3]:
            cpu_utils.append(controller.monitor.current_util)
        avg_cpu_util = sum(cpu_utils) / len(cpu_utils)
        logging.info(f"Average CPU utilization for cluster: {avg_cpu_util}%")
        if avg_cpu_util < self.target_cluster_util:
            logging.info(f"Cluster has capacity. CPU utilization: {avg_cpu_util}%")
            return True
        logging.info(f"Cluster does not have capacity. CPU utilization: {avg_cpu_util}%")
        return False
    
    def cluster_has_capacity(self):
        return self.has_cluster_cpu_capacity() and self.has_cluster_pod_capacity()

    def update_local_states(self):
        for node in self.nodes.values():
            node["controller"].update_state()
        temp = 0
        for node in self.nodes.values():
            temp += node["controller"].state["max_pods"]
        self.MAX_PODS = temp
        
    def refresh_active_nodes(self):
        config.load_kube_config()
        core_v1_api = client.CoreV1Api()
        nodes = core_v1_api.list_node()
        node_info = [{"name": node.metadata.name, "role": node.metadata.labels.get("role", "unknown")} for node in nodes.items]
        # make cluster nodes active to allow for job submission
        active_node_names = [info["name"] for info in node_info]
        for node in self.nodes.values():
            if node["name"] in active_node_names:
                node["is_active"] = True
            for info in node_info:
                if node["name"] == info["name"]:
                    node["label"]["role"] = info["role"]
                if info["role"] == "master":
                    node["can_remove"] = False
            else:
                node["is_active"] = False

    def add_node(self, node_info):
        config.load_kube_config()
        core_v1_api = client.CoreV1Api()
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
            core_v1_api.create_node(body=node)
            print(f"Node {node_info['name']} created successfully")
        except client.rest.ApiException as e:
            print(f"Error creating node: {e}")
        
        while True:
            nodes = core_v1_api.list_node()
            if any(n.metadata.name == node_info["name"] for n in nodes.items):
                print(f"Node {node_info['name']} is now part of the cluster")
                break
            print(f"Waiting for node {node_info['name']} to be added to the cluster...")
            time.sleep(5)

    def remove_node(self, node_name):
        # remove a node from the cluster using kubernetes API
        config.load_kube_config()
        core_v1_api = client.CoreV1Api()
        try:
            # Delete the node
            core_v1_api.delete_node(name=node_name)
            print(f"Node {node_name} deleted successfully")
        except client.rest.ApiException as e:
            print(f"Error deleting node: {e}")

    def determine_next_node(self):
        """ 
        default: choose the next node from the list of active nodes
        
        make sure the node chosen has the capacity to run the job
        otherwise, choose the next node
        
        if no nodes have capacity, check if a node can be added to the system
        if so, add the node and choose it to deploy the job
        
        if no nodes can be added, return None
        """
        active_nodes = [node for node in self.nodes.values() if node["is_active"]]
        for node in active_nodes:
            if node["controller"].has_capacity():
                return node["name"]
            else:
                continue
        inactive_nodes = [node for node in self.nodes.values() if not node["is_active"]]
        if inactive_nodes:
            self.add_node(inactive_nodes[0])
            return inactive_nodes[0]["name"]
    
    def determine_node_to_remove(self):
        """ 
        if a node capacity is below 20% for 5 cycles, remove the node
        """
        pass