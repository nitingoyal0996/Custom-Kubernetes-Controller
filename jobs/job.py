import logging
from kubernetes import client, config
import uuid

class JobSubmitter:
    def __init__(self, node_name, job_args):
        self.job_args = job_args
        self.node_name = node_name.split('.')[0]
        self.worker_number = self.node_name.replace('node', '')

        self.image = "polinux/stress-ng"
        self.namespace = 'jobs'

        config.load_kube_config()
        self.batch_v1_api = client.BatchV1Api()
        self.core_v1_api = client.CoreV1Api()

        self.create_namespace_if_not_exists()


    def create_namespace_if_not_exists(self):
        try:
            self.core_v1_api.read_namespace(name=self.namespace)
        except client.exceptions.ApiException as e:
            if e.status == 404:
                namespace = client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=self.namespace)
                )
                self.core_v1_api.create_namespace(body=namespace)
                print(f"Created namespace: {self.namespace}")

    def create_job(self):
        job_id = str(uuid.uuid4())[:8]
        job_name = f"job-node{self.worker_number}-{job_id}"

        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=job_name,
                namespace=self.namespace,
                labels={
                    "app": f"job-node{self.worker_number}",
                    "job-id": job_id
                }
            ),
            spec=client.V1JobSpec(
                ttl_seconds_after_finished=5,
                backoff_limit=0,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={
                            "app": f"job-node{self.worker_number}",
                            "job-id": job_id
                        }
                    ),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="job",
                                image=self.image,
                                args=self.job_args
                            )
                        ],
                        restart_policy="Never",
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
        return job

    def submit(self):
        logging.info(f"Job Queue: Submitting job: {self.job_args}")
        job = self.create_job()
        self.batch_v1_api.create_namespaced_job(namespace=self.namespace, body=job)

# Usage example
if __name__ == "__main__":
    job_submitter = JobSubmitter("node1", ["stress-ng", "--cpu", "2", "--timeout", "60s"])
    job_submitter.submit()