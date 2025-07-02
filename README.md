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


## Architecture

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

- **Job Queue**: Manages incoming stress jobs and feeds them to the global controller.
- **Global Controller**: Makes scaling decisions and assigns jobs to nodes.
- **Middleware**: Facilitates communication between global and local controllers.
- **Local Controllers**: Manage jobs and resources on each node, report node status.
- **Pods/Jobs**: Actual stress jobs running on individual nodes.

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


Here is the directory structure - 

- **model**: Directory provides a way to run stressors and model individual nodes.
- **jobs**: Manages the job queue
- **middleware.py** - Manages the job assignments
- **monitor.py** - Applies monitoring to each node

```bash
- model / 
    - stressors /
    - stress_runner.py
    - model_system.py
    - design_controller.py
- scripts/setup
    - install.sh
    - start_master.sh
    - start_worker.sh
- jobs /
    - queue.py
    - job.py
- static /
    - jobs.txt
- global_controller.py
- middleware.py
- local_controller.py
- monitor.py
- metric-config.yaml
- main.py
```
