
from kubernetes import client, config
import sys

def add_node(node_info):
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
        print(f"Middleware: Node {node_info['name']} created successfully")
    except client.rest.ApiException as e:
        print(f"Middleware: Error creating node: {e}")
        
def remove_node(node_name):
    try:
        config.load_kube_config()
        core_v1_api = client.CoreV1Api()
        core_v1_api.delete_node(name=node_name)
        print(f"Middleware: {node_name} removed successfully")
    except client.rest.ApiException as e:
        print(f"Middleware: Error deleting node: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python forced_cutoff.py <add/remove> <node_number>")
        sys.exit(1)

    action = sys.argv[1]
    node_number = sys.argv[2]

    if action not in ["add", "remove"]:
        print("Invalid action. Use 'add' or 'remove'.")
        sys.exit(1)

    node_1 = {
        "name": "node1.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us",
        "ip": "128.110.217.136",
        "label": {"role": "worker", "nodetype": "worker1"}
    }
    node_2 = {
        "name": "node2.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us",
        "ip": "128.110.217.157",
        "label": {"role": "worker", "nodetype": "worker2"}
    }

    if node_number == "1":
        node_info = node_1
    elif node_number == "2":
        node_info = node_2
    else:
        print("Invalid node number. Use '1' or '2'.")
        sys.exit(1)

    if action == "add":
        add_node(node_info)
    elif action == "remove":
        remove_node(node_info['name'])
