# !/bin/bash
# if the swap is enabled, you can disable it by running the following command:
# sudo swapoff -a

# remove the following directories and files:
sudo rm -rf /etc/cni/net.d/*
sudo rm -rf /var/lib/kubelet/*
sudo rm -rf /etc/kubernetes/
sudo iptables -F && sudo iptables -t nat -F && sudo iptables -t mangle -F && sudo iptables -X

# reset the kubeadm configuration:
sudo kubeadm reset --force

# Now, re-join the cluster