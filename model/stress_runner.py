import argparse
from pathlib import Path
import csv
from typing import List, Dict
import numpy as np

from stressors.stress_cluster import ClusterStressor
from stressors.stress_node import NodeStressor

class StressRunner:
    def __init__(self, output_dir: str = "stress_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def write(self, file_name, data):
        with open(file_name, mode='w', newline='') as file:
            writer = csv.writer(file)
            for max_pods, cpu_util in data:
                writer.writerow(['Max Pods', 'CPU Utilization'])
                writer.writerow([max_pods, cpu_util])
        
    def run_test(self, StressClass, pods: List[int], duration: int = 300, interval: int = 5, node_name='all') -> Dict:
        results = []
        for pod_count in range(2, pods + 1):
            print(f"\nRunning stress test with {pod_count} pods...")
            stressor = StressClass(
                pods=pod_count,
                duration=duration,
                poll_every=interval,
                node_name=node_name
            )
            cpu_utils = stressor.run()
            if str.lower(stressor.type) == 'cluster':
                # take average of all the node cpu utilization
                cpu_utils = [sum(cpu_percent) / len(cpu_percent) for cpu_percent in cpu_utils.values()]
            else:
                cpu_utils = cpu_utils
            # append the average cpu utilization to the results
            cpu_utils = np.array(cpu_utils)
            results.append((pod_count, cpu_utils.mean()))
        self.write(f'{self.output_dir}/{stressor.type}_data.csv', results)
        print(f"\nAll results saved in: data/")

def main():
    parser = argparse.ArgumentParser(description='Run stress tests for the cluster or just a node')
    parser.add_argument('--type', choices=['cluster', 'node'], 
                       default='cluster', help='Type of system to stress')
    args = parser.parse_args()
    
    runner = StressRunner(output_dir='data')

    MAX_PODS = 5
    POLL_INTERVAL = 5
    TIME = 30
    
    if args.type == 'cluster':
        print("\nStarting Ubuntu stress tests...")
        runner.run_test(ClusterStressor, MAX_PODS, TIME, POLL_INTERVAL)
        print("\nUbuntu tests completed!")
        
    if args.type == 'node':
        print("\nStarting Docker stress tests...")
        runner.run_test(NodeStressor, MAX_PODS, TIME, POLL_INTERVAL, node_name='node1.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us')
        print("\nDocker tests completed!")

if __name__ == "__main__":
    main()