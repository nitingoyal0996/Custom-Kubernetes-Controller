# service jobs to kubernetes node
import time
from kubernetes import client, config

# TODO: Implement job-id to provide unique pod names
class Job:
    def __init__(self, node_name, job_args):
        self.job_args = job_args
        self.node_name = node_name.split('.')[0]
        self.worker_number = self.node_name.replace('node', '')

        self.image = "polinux/stress-ng"
        self.namespace = 'jobs'
        
        # Load Kubernetes configuration
        config.load_kube_config()
        self.apps_v1_api = client.AppsV1Api()
        self.core_v1_api = client.CoreV1Api()
        
        print(f"Node name: {self.node_name}, Worker number: {self.worker_number} started...")

    def create_job_deployment(self):
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name=f"job-node{self.worker_number}",
                namespace=self.namespace
            ),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={"app": f"job-node{self.worker_number}"}
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={"app": f"job-node{self.worker_number}"}
                    ),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="job",
                                image=self.image,
                                args=self.job_args
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

    def deploy_job(self):
        print(f"Deploying job on node {self.node_name}...")

        # Cleanup the environment before starting a new test
        try:
            self.apps_v1_api.read_namespaced_deployment(
                name=f"job-node{self.worker_number}",
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
            name=f"job-node{self.worker_number}",
            namespace=self.namespace,
            body=client.V1Scale(spec=client.V1ScaleSpec(replicas=1))
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
            
            if running_pods == 1:
                print(f"Job is submitted to {self.node_name}")
                return True
            
            time.sleep(2)
        
        print(f"Timeout waiting for pods to be ready")
        return False

    def submit(self):
        try:
            print(f"Starting job {self.job_args}")
            self.deploy_stress_ng_pods()
            if not self.wait_for_pods_ready():
                print("Failed to start pods, cleaning up...")
                return []
        except:
            print("An error occurred during the experiment")
