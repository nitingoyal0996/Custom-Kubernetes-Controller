# Kubernetes Job Orchestrator

This project was developed as part of a Cloud System Management (Software Defined Systems) class.

It implements custom controllers for Kubernetes to automatically scale resources and assign pods for running stress jobs on a cluster. The architecture includes local controllers for each node, middleware for coordination, a global controller for cluster-wide scaling, and a job queue for managing stress jobs.

## What We Did

- Designed and implemented a custom Kubernetes control plane for stress job management.
- Developed a job queue system that holds incoming stress jobs.
- Built local controllers for each node to monitor workloads and report status.
- Created middleware to coordinate between local and global controllers.
- Implemented a global controller to manage scaling and job assignments across the cluster.
- Integrated pod assignment and dynamic scaling logic tailored for stress testing scenarios.

## What We Learned

- Practical application of Kubernetes internals and custom controller design.
- Communication mechanisms between distributed system components.
- Creating middleware for dynamic resource allocation and job scheduling in cloud environments.
- Real-world challenges of horizontal scaling, workload distribution, and monitoring.


## High-Level Architecture

```mermaid
flowchart TD
    subgraph Cluster
        GC[Global Controller]
        MW[Middleware]
        JQ[Job Queue]
        GC --> MW
        MW --> LC1
        MW --> LC2
        JQ --> GC
        subgraph Node1
            LC1[Local Controller 1]
            JOBS1[Pods/Jobs 1]
            LC1 --> JOBS1
        end
        subgraph Node2
            LC2[Local Controller 2]
            JOBS2[Pods/Jobs 2]
            LC2 --> JOBS2
        end
    end
```


## UML

```mermaid
classDiagram
    class Middleware {
        +int target_cluster_util
        +int MAX_CLUSTER_PODS
        +int current_node_index
        +int node_added_before
        +int failure_cool_down
        +dict nodes
        +dict cluster_metrics
        +core_v1_api
        +__init__(controller_1, controller_2, controller_3)
        +refresh_active_nodes()
        +update_local_states()
        +avg_cluster_cpu_capacity()
        +check_metrics_availability()
        +add_node(node_name)
        +remove_node(node_name)
        +find_inactive_nodes()
        +determine_next_node()
        +determine_node_to_remove()
        +get_total_pods()
        +cleanup_node(node_name)
        +cleanup_cluster()
        +save_metrics()
    }

    class LocalController {
        +state
        +monitor : MonitorNode
        +update_state()
        ...
    }

    class GlobalController {
        +middleware : Middleware
        +DESIRED_CPU_UTILIZATION_RANGE
        +OPERATING_POINT
        +SCALE_DOWN_THRESHOLD
        +polling_interval
        +LOW_CYCLE_COUNT
        +low_cluster_util_count_down
        +run(queue)
        ...
    }

    class MonitorNode {
        +current_util
        +get_running_pod_count()
        +has_pod_capacity(max_pods)
        ...
    }

    class Job {
        +str cmd
        +dict stressors
        +str duration
        +__init__(cmd)
        +parse_stressors(cmd)
        +to_args_list()
    }

    class JobQueue {
        +str queue_file
        +Queue job_queue
        +__init__(queue_file)
        +load_jobs()
        +get_next_job()
        +has_next_job()
    }

    class JobSubmitter {
        +str node_name
        +str worker_number
        +str image
        +str namespace
        +BatchV1Api batch_v1_api
        +CoreV1Api core_v1_api
        +__init__(node_name, job_args)
        +create_namespace_if_not_exists()
        +create_job()
        +submit()
    }

    Middleware "1" o-- "1..*" LocalController : manages
    Middleware "1" o-- "1" GlobalController : used by
    LocalController "1" o-- "1" MonitorNode : monitors
    GlobalController "1" o-- "1" JobQueue : uses
    JobQueue "1" o-- "many" Job : contains
    GlobalController "1" o-- "many" JobSubmitter : creates
```

**Entities:**
- **LocalController**: Manages a node, monitors CPU, and decides pod scaling.
- **MonitorNode**: Fetches node metrics (like CPU usage).
- **GlobalController**: Top-level manager for job assignment and scaling.
- **Middleware**: Handles communication between global and local controllers.
- **JobQueue**: Stores pending jobs.
- **Job**: Represents a workload or stress job.


## Usage

1. Clone the repository:
   ```bash
   git clone https://github.com/nitingoyal0996/Custom-Kubernetes-Controller.git
   cd Custom-Kubernetes-Controller
   ```
2. Set up the environment:
   ```bash
   cd scripts/setup
   bash install.sh
   ```
3. Start the master and worker nodes:
   ```bash
   bash scripts/setup/start_master.sh
   bash scripts/setup/start_worker.sh
   ```
4. Launch the main controller:
   ```bash
   python main.py
   ```
5. Define stress jobs in `static/jobs.txt`. The system will manage scaling and assignment automatically.

