import subprocess
import time

def run_command(command):
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Exception occurred: {str(e)}"

def main():
    while True:
        print("\n=== kubectl top nodes ===")
        top_nodes_output = run_command(["kubectl", "top", "nodes"])
        print(top_nodes_output)

        print("\n=== kubectl get pods --namespace=jobs ===")
        get_pods_output = run_command(["kubectl", "get", "pods", "--namespace=jobs"])
        print(get_pods_output)

        time.sleep(5)

if __name__ == "__main__":
    main()
