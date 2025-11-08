# F5XC Deployment – My Deployment

## Objective
The goal is to integrate **F5 Distributed Cloud Mesh (Mesh)** capabilities with an existing Red Hat OpenShift (OCP) cluster by deploying the site as pods within the cluster. This configuration supports Mesh functionalities and automatically discovers services running in the OCP cluster by querying the kube-API.

---

## Prerequisites

Before deployment, the OCP environment must meet specific requirements:

1. **Distributed Cloud Services Account and Site Token**  
   A Distributed Cloud Services Account is required. Site tokens are generated in the Console under:  
   `Multi-Cloud Network Connect > Manage > Site Management > Site Tokens`

2. **OCP Cluster Readiness**  
   - An OCP K8s cluster must be available (OCP version 4.7 is supported, though the observed deployment used a newer version).  
   - **Node Requirements:** Minimum 4 vCPUs and 8 GB of memory per node.  
   - **Observed Cluster Details:** The deployment uses a node named `api.gpu-ai.bd.f5.com` running Kubernetes version `v1.31.6`.

3. **StorageClass and Dynamic PV**  
   - A Kubernetes StorageClass with Dynamic Persistent Volume Provisioner (PVC) enabled, needing at least 1 GB of space.  
   - **Observed Storage Details:**  
     The cluster has two StorageClasses: `localblock-sc` and `lvms-vg1 (default)`.  
     The presence of `(default)` indicates dynamic PVC provisioning is enabled for that class.

---

## Step 1: OCP Environment Configuration

This step ensures that kernel hugepages are available and storage is configured for F5XC deployment.

### 1.1 Storage Class Verification
```bash
oc get sc
NAME              PROVISIONER                  RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
localblock-sc     kubernetes.io/no-provisioner Delete          WaitForFirstConsumer   false                  221d
lvms-vg1 (default) topolvm.io                  Delete          WaitForFirstConsumer   true                   221d
```

### 1.2 Enable Kernel HugePages

HugePages configuration is necessary when deploying Mesh as OCP pods.

1. **Label the node:**  
   The node `api.gpu-ai.bd.f5.com` was labeled with the custom role `worker-hp`.

2. **Apply Tuned and MachineConfigPool (MCP):**  
   Configuration files `hugepages-tuned-boottime.yaml` and `hugepages-mcp.yaml` were applied to enable HugePages.

3. **Verification:**  
   The allocation of HugePages (2Mi) was verified on the labeled node.

---

## Step 2: Deploy Cloud Mesh Pod (F5XC Site)

The F5XC site deployment (`CE on K8S site manifest`) was applied using the manifest file `ce_ocp_gpu-ai.yml`.

### 2.1 Deployment Execution

Applying the manifest created resources in the `ves-system` namespace, including:
- Service accounts: `volterra-sa`, `vpm-sa`
- Roles and role bindings
- DaemonSet: `volterra-ce-init`
- StatefulSet: `vp-manager`

### 2.2 Persistent Volume Claim (PVC) Verification

PVCs for the `vp-manager-0` pod were bound using the `lvms-vg1` StorageClass, confirming persistence setup.

---

## Step 3: Registration and Verification

After deployment, site registration must be approved in the F5XC Console.

### 3.1 Initial Pod Status (Pre-Fix)

Initially, several F5XC pods were not running correctly:

| Pod Name | Status | Notes |
|-----------|---------|-------|
| etcd-0 | Running | OK |
| prometheus | CrashLoopBackOff | Issue found |
| ver-0 | PodInitializing | Pending startup |
| vp-manager-0 | Running | OK |

### 3.2 Troubleshooting and Remediation (Prometheus Deployment)

Inspection of the Prometheus deployment revealed specific container ports (`65210–65221`) configured with `hostPort` settings.  
These entries were removed using:

```bash
oc -n ves-system edit deploy/prometheus
```

Remaining ports after fix:
- 65210 (TCP)  
- 65211 (TCP)  
- 65220 (TCP)  
- 65221 (TCP)

### 3.3 Final Site Status

After removing the `hostPort` entries, all components reached **Running** status:

| Pod | READY | STATUS | NODE |
|------|--------|---------|------|
| etcd-0 | 2/2 | Running | api.gpu-ai.bd.f5.com |
| prometheus | 5/5 | Running | api.gpu-ai.bd.f5.com |
| ver-0 | 17/17 | Running | api.gpu-ai.bd.f5.com |
| vp-manager-0 | 1/1 | Running | api.gpu-ai.bd.f5.com |

---

## Step 4: Application Deployment and Service Advertising

With the F5XC site operational inside OCP, test applications were deployed, and services were advertised.

### 4.1 Deploy Application

1. **Create Namespace:**  
   ```bash
   oc new-project z-ji
   ```

2. **Deploy Apps:**  
   The Hipster Shop application was deployed into the `z-ji` namespace (includes `emailservice`, `paymentservice`, `frontend`, `redis-cart`, etc.).

3. **Verify App Status:**  
   Ensure all pods reach **Running** status.

### 4.2 Advertising Services

When Mesh is deployed as pods inside OCP, service discovery is automatic. Applications can use `ClusterIP` type services.

#### Steps to Advertise a Service

1. **Create Origin Pool** (in F5XC Console → Multi-Cloud App Connect)  
   - Type: *K8s Service Name of Origin Server on given Sites*  
   - Format: `<servicename>.<namespace>` (e.g., `frontend.z-ji`)  
   - Select the Mesh site and choose *Outside Network*

2. **Create HTTP Load Balancer**  
   - Define a domain name  
   - Reference the Origin Pool created above  

After configuration, the Load Balancer dashboard should display the application pods as origin servers.

---

## Summary

Integrating **F5XC Mesh** into OpenShift via the “Deploy as OCP Pods” method is like installing a **traffic control center directly inside the factory floor** (the OCP cluster).  
Unlike an external gateway that requires kubeconfig access and NodePort services, the internal mesh pods natively interact with the kube-API for **automatic discovery** and **ClusterIP-based service advertisement**, simplifying microservice exposure and management.

