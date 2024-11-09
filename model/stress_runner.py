import argparse
from pathlib import Path
import csv
from typing import List, Dict
import numpy as np
import time

from stressors.stress_cluster import ClusterStressor
from stressors.stress_node import NodeStressor

class StressRunner:
    def __init__(self, output_dir: str = "stress_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def write(self, file_name, data):
        with open(file_name, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Max Pods', 'CPU Utilization'])
            for max_pods, cpu_util in data:
                writer.writerow([max_pods, cpu_util])
        
    def run_test(self, StressClass, pods: List[int], duration: int = 300, interval: int = 5, stressors=2, node_name='all') -> Dict:
        results = []
        for pod_count in range(1, pods + 1):
            print(f"Running stress test with {pod_count} pods...")
            stressor = StressClass(
                pods=pod_count,
                duration=duration,
                poll_every=interval,
                node_name=node_name,
                stressors=stressors
            )
            cpu_utils = stressor.run()
            cpu_utils = np.array([sum(cpu_percent) / len(cpu_percent) for cpu_percent in cpu_utils.values()])
            results.append((pod_count, cpu_utils.mean()))
            time.sleep(30)
        self.write(f'{self.output_dir}/{stressor.type}_data.csv', results)
        print(f"\nAll results saved in: data/")

def main():
    parser = argparse.ArgumentParser(description='Run stress tests for the cluster or just a node')
    parser.add_argument('--type', choices=['cluster', 'node'], 
                       default='cluster', help='Type of system to stress')
    parser.add_argument('--interval', type=int, default=5, help='Interval to poll CPU utilization')
    parser.add_argument('--time', type=int, default=60, help='Duration of the stress test (Seconds)')
    parser.add_argument('--max-pods', type=int, default=2, help='Maximum number of pods to stress')
    parser.add_argument('--max-stressors', type=int, default=1, help='Maximum number of stressors to run')
    args = parser.parse_args()
    
    runner = StressRunner(output_dir='data')
    
    if args.type == 'cluster':
        print("\nStarting Ubuntu stress tests...")
        runner.run_test(ClusterStressor, args.max_pods, args.time, args.interval, args.max_stressors)
        print("\nUbuntu tests completed!")
        
    if args.type == 'node':
        print("\nStarting Docker stress tests...")
        runner.run_test(NodeStressor, args.max_pods, args.time, args.interval, args.max_stressors, node_name='node1.goyal-project.ufl-eel6871-fa24-pg0.utah.cloudlab.us')
        print("\nDocker tests completed!")

if __name__ == "__main__":
    main()