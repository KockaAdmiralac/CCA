#!/bin/bash

GenerateSSHKey() {
    if [ ! -f cloud-computing ]
    then
        echo "Generating SSH key..."
        ssh-keygen -t rsa -b 4096 -f cloud-computing -N ''
    fi
}

CreateKubernetesCluster() {
    if [ "$(kubectl config current-context 2>/dev/null || echo none)" == "$1.k8s.local" ]
    then
        echo "Cluster already exists -- not creating"
    else
        echo "Creating cluster..."
        source profile.sh
        sed -i "s|gs://<your-gs-bucket>/|$KOPS_STATE_STORE|" part*.yaml
        sed -i "s/<your-cloud-computing-architecture-gcp-project>/$PROJECT/" part*.yaml
        kops create -f "$1.yaml"
        kops create secret --name "$1.k8s.local" sshpublickey admin -i cloud-computing.pub
        kops update cluster --name "$1.k8s.local" --yes --admin
        echo "Validating cluster..."
        kops validate cluster --wait 10m
    fi
}

DeleteKubernetesCluster() {
    source profile.sh
    kops delete cluster $1.k8s.local --yes
}

RunCommand() {
    ssh -oStrictHostKeyChecking=no -i cloud-computing "ubuntu@$1" "$2"
}

CopyToVM() {
    scp -oStrictHostKeyChecking=no -i cloud-computing "$1" "ubuntu@$2"
}

CopyFromVM() {
    scp -oStrictHostKeyChecking=no -i cloud-computing "ubuntu@$1" "$2"
}

SetupMcperf() {
    CopyToVM make-mcperf.sh "$1:"
    RunCommand "$1" "bash make-mcperf.sh" > /dev/null
}

TerminalBell() {
    printf '\a'
}
