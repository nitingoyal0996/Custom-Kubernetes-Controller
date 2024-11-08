import time
import kubernetes
from kubernetes import client, config
from kubernetes.client import CustomObjectsApi

class NodeStressor:
    def __init__(self, pods, duration, node_name, poll_every=5, image="polinux/stress-ng", namespace="default"):
        self.duration = duration
        self.pods = pods
        self.type = 'Node'
        self.image = image
        self.namespace = namespace
        self.node_name = node_name.split('.')[0]
        self.worker_number = self.node_name.replace('node', '')
        self.node_cluster_name = node_name
        print(f"Node name: {self.node_name}, Worker number: {self.worker_number}")
        self.poll_interval = poll_every
        
        # Load Kubernetes configuration
        config.load_kube_config()
        self.apps_v1_api = client.AppsV1Api()
        self.core_v1_api = client.CoreV1Api()
        self.custom_api = CustomObjectsApi()

    def create_stress_ng_deployment(self, cpu_workers=2):
        print(f"worker{self.worker_number}")
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name=f"stress-ng-node{self.worker_number}",
                namespace=self.namespace
            ),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={"app": f"stress-ng-node{self.worker_number}"}
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={"app": f"stress-ng-node{self.worker_number}"}
                    ),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="stress-ng",
                                image=self.image,
                                args=[
                                    "--cpu", str(cpu_workers),
                                    "--io", "2",
                                    "--vm", "8",
                                    "--vm-bytes", "4G",
                                    "--timeout", str(self.duration + 30),  # Add buffer time
                                    "--metrics-brief"
                                ]
                            )
                        ],
                        # Add node affinity to ensure pods run on specified node 
                        # Affects the pod placement on nodes
                        affinity=client.V1Affinity(
                            node_affinity=client.V1NodeAffinity(
                                required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                                    node_selector_terms=[
                                        client.V1NodeSelectorTerm(
                                            match_expressions=[
                                                client.V1NodeSelectorRequirement(
                                                    key="nodetype",
                                                    operator="In",
                                                    values=[f"worker{self.worker_number}"]
                                                )
                                            ]
                                        )
                                    ]
                                )
                            )
                        ),
                        tolerations=[
                            client.V1Toleration(
                                key="node-role.kubernetes.io/control-plane",
                                operator="Exists",
                                effect="NoSchedule"
                            )
                        ]
                    )
                )
            )
        )
        return deployment

    def deploy_stress_ng_pods(self):
        print(f"Deploying {self.pods} stress-ng pods on node {self.node_name}...")

        # Cleanup the environment before starting a new test
        try:
            self.apps_v1_api.read_namespaced_deployment(
                name=f"stress-ng-node{self.worker_number}",
                namespace=self.namespace
            )
            self.cleanup()
        except client.exceptions.ApiException as e:
            if e.status != 404:
                raise e

        # Deploy
        deployment = self.create_stress_ng_deployment()
        self.apps_v1_api.create_namespaced_deployment(
            body=deployment, namespace=self.namespace
        )
        # Scale
        self.apps_v1_api.patch_namespaced_deployment_scale(
            name=f"stress-ng-node{self.worker_number}",
            namespace=self.namespace,
            body=client.V1Scale(spec=client.V1ScaleSpec(replicas=self.pods))
        )

    def wait_for_pods_ready(self):
        print("Waiting for pods to be ready...")
        max_wait = 60
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            pods = self.core_v1_api.list_namespaced_pod(
                namespace=self.namespace, 
                label_selector=f"app=stress-ng-node{self.worker_number}"
            )
            
            running_pods = len([p for p in pods.items if p.status.phase == "Running"])
            
            if running_pods == self.pods:
                print(f"All {self.pods} pods are running on {self.node_name}")
                return True
            
            time.sleep(2)
        
        print(f"Timeout waiting for pods to be ready")
        return False

    def get_cpu_utilization(self):
        print(f"Collecting CPU utilization for {self.node_name}...")
        try:
            metrics = self.custom_api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"
            )
            
            for item in metrics['items']:
                if item['metadata']['name'] == self.node_cluster_name:
                    cpu_usage_nano = int(item['usage']['cpu'].rstrip('n'))
                    node = self.core_v1_api.read_node(self.node_cluster_name)
                    cpu_capacity = int(node.status.capacity['cpu']) * 1000000000  # Convert to nanocores
                    print('Node\'s CPU capacity: {cpu_capacity}')
                    cpu_percent = (cpu_usage_nano / cpu_capacity) * 100
                    
                    print(f"Node: {self.node_name}, CPU Utilization: {round(cpu_percent, 2)}%")
                    return round(cpu_percent, 2)
            
            print(f"No metrics found for node {self.node_cluster_name}")
            return []
            
        except Exception as e:
            print(f"Error getting CPU metrics: {e}")
            return []

    def cleanup(self):
        print("Cleaning up resources...")
        try:
            try:
                self.apps_v1_api.delete_namespaced_deployment(
                    name=f"stress-ng-node{self.worker_number}",
                    namespace=self.namespace,
                    propagation_policy="Foreground"
                )
            except client.exceptions.ApiException as e:
                if e.status != 404:
                    raise e
                
            # check if pods are deleted
            # Wait for deployment to be fully deleted
            while True:
                try:
                    self.apps_v1_api.read_namespaced_deployment(
                        name=f"stress-ng-node{self.worker_number}",
                        namespace=self.namespace
                    )
                    print("Waiting for deployment to be deleted...")
                    time.sleep(2)
                except kubernetes.client.rest.ApiException as e:
                    if e.status == 404:
                        break
                    raise

            # Double check and force delete any lingering pods
            try:
                pods = self.core_v1_api.list_namespaced_pod(
                    namespace=self.namespace,
                    label_selector=f"app=stress-ng-node{self.worker_number}"
                )
                for pod in pods.items:
                    print(f'Force deleting pod {pod.metadata.name}')
                    self.core_v1_api.delete_namespaced_pod(
                        name=pod.metadata.name,
                        namespace=self.namespace,
                        body=client.V1DeleteOptions(
                            grace_period_seconds=0,
                            propagation_policy='Background'
                        )
                    )
            except kubernetes.client.rest.ApiException as e:
                if e.status != 404:
                    raise

            print("Cleanup completed successfully")

        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
            raise

    def run(self):
        try:
            print(f"\nStarting experiment with {self.pods} pods on node {self.node_cluster_name}")
            self.deploy_stress_ng_pods()
            if not self.wait_for_pods_ready():
                print("Failed to start pods, cleaning up...")
                return []
            cpu_utils = self.monitor()
            return cpu_utils
        except Exception as e:
            print("An error occurred during the experiment")
            raise e
        finally:
            self.cleanup()
        
    def monitor(self):
        start_time = time.time()
        cpu_utils = {}
        cpu_utils[self.node_name] = []
        
        while time.time() - start_time < self.duration:
            try:
                utilization = self.get_cpu_utilization()
                if utilization:
                    cpu_utils[self.node_name].append(utilization)
                time.sleep(self.poll_interval)
            except Exception as e:
                print(f"Error during monitoring: {e}")
                
        print(f"Test completed. Recorded {len(cpu_utils)} data points.")
        return cpu_utils