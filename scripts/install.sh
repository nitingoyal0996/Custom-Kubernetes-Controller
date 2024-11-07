#!/bin/bash

# Exit on any error
set -e

# Function to check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    # Check if running as root or with sudo
    if [[ $EUID -ne 0 ]]; then
        echo "This script must be run as root or with sudo privileges"
        exit 1
    fi
    # Check system resources
    MEMORY_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    CPU_COUNT=$(nproc)
    if [[ $MEMORY_KB -lt 1572864 ]]; then    # Less than 2GB
        echo "Error: At least 2GB of RAM is required"
        exit 1
    fi
    if [[ $CPU_COUNT -lt 2 ]]; then
        echo "Error: At least 2 CPU cores are required"
        exit 1
    fi
    # Check if Kubernetes is already installed
    if command -v kubectl >/dev/null 2>&1; then
        echo "Error: Kubernetes appears to be already installed. Please remove it first."
        exit 1
    fi
}

# Function to check and configure system settings
configure_system() {
    echo "Configuring system settings..."

    # Setup IP Tables to see bridged traffic
    cat <<EOF | tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

    modprobe overlay
    modprobe br_netfilter

    # sysctl params required by setup, params persist across reboots
    cat <<EOF | tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

    sysctl --system

    # Verify modules are loaded
    if ! lsmod | grep -q "^overlay\|^br_netfilter"; then
        echo "Error: Required modules failed to load"
        exit 1
    fi
}

# Function to install CRI-O
install_crio() {
    echo "Installing CRI-O..."
    
    # Define versions
    KUBERNETES_VERSION="1.30"  # Latest stable as of April 2024
    CRIO_VERSION="1.30"       # Match with Kubernetes version

    apt-get update -y
    apt-get install -y software-properties-common gpg curl apt-transport-https ca-certificates

    # Clean up any old repositories
    rm -f /etc/apt/sources.list.d/crio.list

    # Add CRI-O repository
    curl -fsSL https://pkgs.k8s.io/addons:/cri-o:/stable:/v${CRIO_VERSION}/deb/Release.key | \
        gpg --dearmor -o /etc/apt/keyrings/cri-o-apt-keyring.gpg
    echo "deb [signed-by=/etc/apt/keyrings/cri-o-apt-keyring.gpg] https://pkgs.k8s.io/addons:/cri-o:/stable:/v${CRIO_VERSION}/deb/ /" | \
        tee /etc/apt/sources.list.d/cri-o.list

    apt-get update -y
    apt-get install -y cri-o

    systemctl daemon-reload
    systemctl enable crio --now
    
    # Verify CRI-O is running
    if ! systemctl is-active --quiet crio; then
        echo "Error: CRI-O installation failed"
        exit 1
    fi

    # Install crictl with matching version
    CRICTL_VERSION="v1.30.0"  # Match with kubernetes version
    wget https://github.com/kubernetes-sigs/cri-tools/releases/download/$CRICTL_VERSION/crictl-$CRICTL_VERSION-linux-amd64.tar.gz
    tar zxvf crictl-$CRICTL_VERSION-linux-amd64.tar.gz -C /usr/local/bin
    rm -f crictl-$CRICTL_VERSION-linux-amd64.tar.gz

    # Configure crictl to work with CRI-O
    cat <<EOF | tee /etc/crictl.yaml
runtime-endpoint: unix:///var/run/crio/crio.sock
image-endpoint: unix:///var/run/crio/crio.sock
timeout: 30
debug: false
EOF
}

# Function to install Kubernetes components
install_kubernetes() {
    echo "Installing Kubernetes components..."
    
    KUBERNETES_VERSION="1.30"

    # Cleanup any old configurations
    rm -f /etc/apt/sources.list.d/kubernetes.list
    
    # Create required directories
    mkdir -p -m 755 /etc/apt/keyrings

    # Add Kubernetes repository
    curl -fsSL https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/Release.key | \
        gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
    chmod 644 /etc/apt/keyrings/kubernetes-apt-keyring.gpg

    echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/ /" | \
        tee /etc/apt/sources.list.d/kubernetes.list
    chmod 644 /etc/apt/sources.list.d/kubernetes.list

    apt-get update -y
    apt-get install -y kubelet=1.30.6-1.1 kubeadm kubectl
    apt-mark hold kubelet kubeadm kubectl

    # Verify installation
    if ! command -v kubectl >/dev/null 2>&1; then
        echo "Error: Kubernetes installation failed"
        exit 1
    fi
}

setup_kubeextraargs() {

    # Disable swap
    sudo swapoff -a

    # Install jq, a command-line JSON processor
    sudo apt-get install -y jq

    # Configure kubelet
    local_ip="$(ip --json addr show eno1 | jq -r '.[0].addr_info[] | select(.family == "inet") | .local')"
    if [ -z "$local_ip" ]; then
        echo "Error: Could not determine node IP address"
        exit 1
    fi

    # Set kubelet node IP
    cat > /etc/default/kubelet << EOF
KUBELET_EXTRA_ARGS=--node-ip=$local_ip
EOF

    NODENAME=$(hostname -s)
    POD_CIDR="192.168.0.0/16"  # Calico default

}

# Main execution
echo "Starting Kubernetes installation..."
check_prerequisites
configure_system
install_crio
install_kubernetes
setup_kubeextraargs

echo "Kubernetes installation completed successfully!"
