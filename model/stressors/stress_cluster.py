import time
import kubernetes
from kubernetes import client, config
from kubernetes.client import CustomObjectsApi

class ClusterStressor:
    def __init__(self, pods, duration=300, poll_every=5, image="polinux/stress-ng", namespace="default", node_name='all'):
        self.duration = duration
        self.pods = pods
        self.type = 'Cluster'
        self.image = image
        self.namespace = namespace
        self.poll_interval = poll_every
        
        # Load Kubernetes configuration
        config.load_kube_config()
        self.apps_v1_api = client.AppsV1Api()
        self.core_v1_api = client.CoreV1Api()
        self.metric_api = CustomObjectsApi()

    def create_stress_ng_deployment(self, cpu_workers=2):
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name="stress-ng",
                namespace=self.namespace
            ),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={"app": "stress-ng"}
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={"app": "stress-ng"}
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
                                    "--timeout", str(self.duration),  # Add buffer time
                                    "--metrics-brief"
                                ]
                            )
                        ]
                    )
                )
            )
        )
        return deployment

    def deploy_stress_ng_pods(self):
        print(f"Deploying {self.pods} stress-ng pods...")
        deployment = self.create_stress_ng_deployment()
        self.apps_v1_api.create_namespaced_deployment(
            body=deployment, 
            namespace=self.namespace
        )

        # Scale to desired number of pods
        self.apps_v1_api.patch_namespaced_deployment_scale(
            name="stress-ng",
            namespace=self.namespace,
            body=client.V1Scale(spec=client.V1ScaleSpec(replicas=self.pods))
        )

    def wait_for_pods_ready(self):
        print("Waiting for pods to be ready...")
        max_wait = 60  # Maximum wait time in seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            pods = self.core_v1_api.list_namespaced_pod(
                namespace=self.namespace, 
                label_selector="app=stress-ng"
            )
            
            running_pods = len([p for p in pods.items if p.status.phase == "Running"])
            
            if running_pods == self.pods:
                print(f"All {self.pods} pods are running")
                return True
            
            time.sleep(2)
        
        print(f"Timeout waiting for pods to be ready")
        return False
    
    def cleanup(self):
        print("Cleaning up resources...")
        try:
            # Delete deployment first
            try:
                self.apps_v1_api.delete_namespaced_deployment(
                    name="stress-ng",
                    namespace=self.namespace,
                    body=client.V1DeleteOptions(
                        propagation_policy='Foreground'
                    )
                )
            except kubernetes.client.rest.ApiException as e:
                if e.status != 404:  # Ignore if deployment doesn't exist
                    raise

            # Wait for deployment to be fully deleted
            while True:
                try:
                    self.apps_v1_api.read_namespaced_deployment(
                        name="stress-ng",
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
                    label_selector="app=stress-ng"
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
    def get_cpu_utilization(self):
        print("Collecting CPU utilization...")
        try:
            # Get metrics from the metrics.k8s.io API
            metrics = self.metric_api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"
            )
            
            cpu_usage = []
            for item in metrics['items']:
                node_name = item['metadata']['name']
                
                # Get CPU usage in nanocores
                cpu_usage_nano = int(item['usage']['cpu'].rstrip('n'))
                
                # Get node's CPU capacity
                node = self.core_v1_api.read_node(node_name)
                cpu_capacity = int(node.status.capacity['cpu']) * 1000000000  # Convert to nanocores
                
                # Calculate CPU utilization percentage
                cpu_percent = (cpu_usage_nano / cpu_capacity) * 100
                
                cpu_usage.append((node_name, round(cpu_percent, 2)))
                print(f"Node: {node_name}, CPU Utilization: {round(cpu_percent, 2)}%")
                
            return cpu_usage
        except Exception as e:
            print(f"Error getting CPU utilization: {e}")
            return []

    def run(self):
        try:
            print(f"\nStarting experiment with {self.pods} pods")
            self.deploy_stress_ng_pods()
            self.wait_for_pods_ready()
            cpu_utils = self.monitor()
            print(f"Test completed. Recorded {len(cpu_utils)} data points.")
            return cpu_utils
        finally:
            self.cleanup()

    def monitor(self):
        start_time = time.time()
        cpu_utils = {}
        # Monitor CPU utilization during the experiment duration
        while time.time() - start_time < self.duration:
            try:
                cpu_utilization = self.get_cpu_utilization()
                for node_name, cpu_percent in cpu_utilization:
                    if cpu_utils.get(node_name) is None:
                        cpu_utils[node_name] = []
                    cpu_utils[node_name].append(cpu_percent)
            except Exception as e:
                print(f"Error during monitoring: {e}")
            time.sleep(self.poll_interval)
        print(cpu_utils)
        return cpu_utils
