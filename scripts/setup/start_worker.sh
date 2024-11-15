# receive an argument with values either 'worker' or 'master'

type=$1 # either 'worker' or 'master'
join=$2 # join command for worker nodes

if [[ $type == "worker" ]]; then
    echo "Setting up Worker Node"
    echo "Joining the cluster"
    sudo $join
elif [[ $type == "master" ]]; then
    echo "Fetching the join command"
    # print the join command
    sudo kubeadm token create --print-join-command
fi