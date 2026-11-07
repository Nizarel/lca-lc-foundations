# Private H100 Spot VM

Deploys one H100 Spot VM into the existing AgentzMaint VNet. Only the new
`gpu-subnet` is managed; the VPN gateway and existing subnets are not modified.
The VM has no public IP. A separate NAT Gateway provides outbound access.

## Approved configuration

- Subscription: `da9dea7f-1fc8-44de-93da-ce5c58314cdb`
- Tenant: `16b3c013-d300-468d-ac64-7eda0820b6d3`
- Resource group: `rg-AgentzMaint-southcentralus`
- VM: `vm-agentzmaint-h100-spot`, `Standard_NC40ads_H100_v5`
- OS: Ubuntu 24.04 LTS, image `24.04.202610210`
- Subnet: `gpu-subnet`, `10.0.32.0/24`, private VM IP `10.0.32.4`
- SSH: `azureuser`, public-key authentication, VPN clients `172.16.201.0/24` only
- Disk: 128 GiB Standard SSD, retained on VM deletion
- Spot: deallocate on eviction; maximum price `-1` allows up to on-demand pricing
- Identity: system-assigned, with no additional role assignments

Preflight found 100 available regional Spot vCPUs; this VM requires 40.
Linux Spot compute was approximately USD 1.93/hour at the time of approval.
Spot prices vary. NAT, its public IP, disk storage, and traffic are billed
separately and can remain billable when the VM is deallocated.

## Deploy from PowerShell

Run from the repository root with Azure CLI and Bicep installed. Supply only
the public key; never use a private SSH key as a deployment parameter.

```powershell
az login --tenant 16b3c013-d300-468d-ac64-7eda0820b6d3
az account set --subscription da9dea7f-1fc8-44de-93da-ce5c58314cdb
$publicKey = (Get-Content -Raw "$HOME/.ssh/id_ed25519.pub").Trim()
az bicep build --file infra/h100-spot/main.bicep --stdout
az deployment group validate --name h100-spot --resource-group rg-AgentzMaint-southcentralus --template-file infra/h100-spot/main.bicep --parameters "adminPublicKey=$publicKey" --validation-level Provider
az deployment group what-if --resource-group rg-AgentzMaint-southcentralus --template-file infra/h100-spot/main.bicep --parameters "adminPublicKey=$publicKey" --validation-level Provider
az deployment group create --name h100-spot --resource-group rg-AgentzMaint-southcentralus --template-file infra/h100-spot/main.bicep --parameters "adminPublicKey=$publicKey"
```

Review the preview: it should create the VM, NIC, NSG, outbound public IP,
NAT Gateway, and the new subnet, without updating other subnets or the gateway.
Allocation is subject to live Spot capacity; quota and SKU availability do not
guarantee allocation. Regional deployment is the default; `zone` can optionally
be set to an eligible zone after a capacity failure.

## Access and GPU setup

Connect using the existing OpenVPN profile, then:

```powershell
ssh -i "$HOME/.ssh/id_ed25519" azureuser@10.0.32.4
```

Verified on 2026-11-05 UTC: deployment succeeded, the VM is running as Spot,
and public-key SSH works through the existing VPN from `172.16.201.2`.
All five original subnets and the VPN gateway remain intact. After installing
the NVIDIA driver and rebooting, `nvidia-smi` detected an NVIDIA H100 NVL with
95,830 MiB of GPU memory and driver `620.70.06`.

Driver installation is a post-deployment step, not part of the Bicep template.
The CUDA driver extension's documented OS list does not include Ubuntu 24.04
for CUDA, so this deployment uses NVIDIA's Ubuntu 24.04 repository directly:

```bash
sudo apt-get update
sudo apt-get install -y linux-headers-$(uname -r) curl ca-certificates
curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb -o /tmp/cuda-keyring.deb
sudo dpkg -i /tmp/cuda-keyring.deb
sudo apt-get update
sudo apt-get install -y nvidia-open
sudo reboot
```

Reconnect over SSH and run `nvidia-smi`. Repository driver versions can change.
The CUDA toolkit and ML frameworks have not been installed; the CUDA version
shown by `nvidia-smi` describes driver capability, not an installed toolkit.

References:

- <https://learn.microsoft.com/azure/virtual-machines/linux/n-series-driver-setup>
- <https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/ubuntu.html>
- <https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html>
- <https://learn.microsoft.com/azure/quotas/spot-quota>

## Cleanup

Do not delete the shared resource group or VNet. Remove only this VM, its
retained OS disk and NIC, the `gpu-subnet`, its NSG, NAT Gateway, and outbound
public IP. Check dependencies before removing the subnet or NAT resources.
