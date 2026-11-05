targetScope = 'resourceGroup'

param location string = 'southcentralus'
param vmName string = 'vm-agentzmaint-h100-spot'
param vmSize string = 'Standard_NC40ads_H100_v5'
param adminUsername string = 'azureuser'
@secure()
param adminPublicKey string
param virtualNetworkName string = 'vnet-nyuwyhzhjriuu'
param subnetName string = 'gpu-subnet'
param subnetPrefix string = '10.0.32.0/24'
param privateIpAddress string = '10.0.32.4'
param vpnClientPrefix string = '172.16.201.0/24'
param imageVersion string = '24.04.202610210'
param zone string = ''
param maxPrice int = -1

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2026-05-01' existing = {
  name: virtualNetworkName
}

resource outboundPublicIp 'Microsoft.Network/publicIPAddresses@2026-07-01' = {
  name: '${vmName}-nat-pip'
  location: location
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
  }
}

resource natGateway 'Microsoft.Network/natGateways@2026-07-01' = {
  name: '${vmName}-nat'
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    idleTimeoutInMinutes: 10
    publicIpAddresses: [
      { id: outboundPublicIp.id }
    ]
  }
}

resource networkSecurityGroup 'Microsoft.Network/networkSecurityGroups@2026-07-01' = {
  name: '${vmName}-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowSshFromVpnClients'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '22'
          sourceAddressPrefix: vpnClientPrefix
          destinationAddressPrefix: privateIpAddress
        }
      }
      {
        name: 'DenyOtherInbound'
        properties: {
          priority: 200
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

resource subnet 'Microsoft.Network/virtualNetworks/subnets@2026-05-01' = {
  parent: virtualNetwork
  name: subnetName
  properties: {
    addressPrefix: subnetPrefix
    defaultOutboundAccess: false
    networkSecurityGroup: { id: networkSecurityGroup.id }
    natGateway: { id: natGateway.id }
  }
}

resource networkInterface 'Microsoft.Network/networkInterfaces@2026-07-01' = {
  name: '${vmName}-nic'
  location: location
  properties: {
    enableAcceleratedNetworking: true
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          primary: true
          privateIPAddress: privateIpAddress
          privateIPAllocationMethod: 'Static'
          privateIPAddressVersion: 'IPv4'
          subnet: { id: subnet.id }
        }
      }
    ]
  }
}

resource virtualMachine 'Microsoft.Compute/virtualMachines@2026-04-01' = {
  name: vmName
  location: location
  zones: empty(zone) ? null : [zone]
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    priority: 'Spot'
    evictionPolicy: 'Deallocate'
    billingProfile: {
      maxPrice: maxPrice
    }
    securityProfile: {
      securityType: 'Standard'
    }
    osProfile: {
      computerName: vmName
      adminUsername: adminUsername
      linuxConfiguration: {
        disablePasswordAuthentication: true
        provisionVMAgent: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: adminPublicKey
            }
          ]
        }
      }
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: 'ubuntu-24_04-lts'
        sku: 'server'
        version: imageVersion
      }
      osDisk: {
        name: '${vmName}-osdisk'
        createOption: 'FromImage'
        diskSizeGB: 128
        deleteOption: 'Detach'
        managedDisk: {
          storageAccountType: 'StandardSSD_LRS'
        }
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: networkInterface.id
          properties: {
            primary: true
            deleteOption: 'Detach'
          }
        }
      ]
    }
    diagnosticsProfile: {
      bootDiagnostics: {
        enabled: true
      }
    }
  }
}

output vmId string = virtualMachine.id
output privateIp string = privateIpAddress
output sshCommand string = 'ssh ${adminUsername}@${privateIpAddress}'
output natGatewayId string = natGateway.id