#!/bin/bash
# GPU Driver Setup Script (Ubuntu/Debian)
set -e

echo "=== GPU Driver Setup ==="

# Detect GPU vendor
if lspci | grep -i nvidia > /dev/null; then
    echo "NVIDIA GPU detected. Installing NVIDIA drivers..."
    sudo apt-get update
    sudo apt-get install -y nvidia-driver-535 nvidia-utils-535
    echo "NVIDIA Container Toolkit..."
    distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
        sed "s#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g" | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker

elif lspci | grep -i amd > /dev/null; then
    echo "AMD GPU detected. Installing ROCm..."
    sudo apt-get update
    sudo apt-get install -y rocm-hip-sdk rocm-dev
    echo "export PATH=$PATH:/opt/rocm/bin" >> ~/.bashrc
    echo "export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/rocm/lib" >> ~/.bashrc
fi

echo "=== Setup Complete ==="
echo "Please reboot your system."
