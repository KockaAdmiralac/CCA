#!/bin/bash
set -e

if [ ! -d ~/memcache-perf ]
then
    echo "deb-src http://europe-west3.gce.archive.ubuntu.com/ubuntu/ jammy main restricted" | sudo tee -a /etc/apt/sources.list
    sudo apt-get update
    sudo apt-get install libevent-dev libzmq3-dev git make g++ tmux --yes
    sudo apt-get build-dep memcached --yes
    git clone https://github.com/eth-easl/memcache-perf-dynamic.git ~/memcache-perf
    cd ~/memcache-perf
    make
fi
