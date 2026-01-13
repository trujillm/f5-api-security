# F5 XC Registration Flow - Detailed Breakdown

This document provides a detailed explanation of the 5-step F5 Distributed Cloud (XC) Customer Edge registration process.

---

## Step 1: Generate Token in F5XC Console (SaaS)

### What Happens
An administrator logs into the **F5 Distributed Cloud Console** (https://console.ves.volterra.io) and generates a **Site Token**.

### Purpose
The token is a one-time credential that:
- Authenticates the cluster to F5's SaaS platform
- Links the new site to your F5 XC tenant/namespace
- Has a limited lifespan (~24 hours)

### Where It Goes
The token gets placed in the ConfigMap in `ce_ocp_gpu-ai.yml`:

```yaml
apiVersion: v1 
kind: ConfigMap 
metadata:
  name: vpm-cfg
  namespace: ves-system
data: 
 config.yaml: | 
  Vpm:
    # CHANGE ME
    ClusterName: ericji-gpu-ai-pod
    ClusterType: ce
    Config: /etc/vpm/config.yaml
    DisableModules: ["recruiter"]
    # CHANGE ME
    Latitude: 44
    # CHANGE ME
    Longitude: -122
    MauriceEndpoint: https://register.ves.volterra.io
    MauricePrivateEndpoint: https://register-tls.ves.volterra.io
    PrivateNIC: eth0
    SkipStages: ["osSetup", "etcd", "kubelet", "master", "pool", "voucher", "workload", "controlWorkload", "csi"]
    # CHANGE ME
    Token: xxxx
    CertifiedHardware: k8s-minikube-voltmesh
```

---

## Step 2: Deploy the Manifest to OpenShift

### What Gets Created

The `ce_ocp_gpu-ai.yml` manifest creates these resources in the `ves-system` namespace:

| Resource Type | Name | Purpose |
|---------------|------|---------|
| **Namespace** | `ves-system` | Isolated namespace for F5 components |
| **ServiceAccount** | `volterra-sa` | Identity for Volterra init container |
| **ServiceAccount** | `vpm-sa` | Identity for VP Manager |
| **Role/RoleBinding** | `volterra-admin-role` | Permissions within ves-system |
| **ClusterRole/Binding** | `vpm-cluster-role` | Read access to nodes |
| **ClusterRoleBinding** | `ver` | Cluster-admin for the `ver` (Volterra Edge Router) |
| **DaemonSet** | `volterra-ce-init` | Initializes host for F5 XC (privileged) |
| **ConfigMap** | `vpm-cfg` | Contains the Site Token and configuration |
| **StatefulSet** | `vp-manager` | The VP Manager that orchestrates everything |
| **Service** | `vpm` | NodePort service for VP Manager (port 65003) |

### The DaemonSet (`volterra-ce-init`)

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: volterra-ce-init 
  namespace: ves-system
spec:
  selector:
    matchLabels:
      name: volterra-ce-init
  template:
    metadata:
      labels:
        name: volterra-ce-init 
    spec:
      hostNetwork: true
      hostPID: true
      serviceAccountName: volterra-sa
      containers:
      - name: volterra-ce-init
        image: gcr.io/volterraio/volterra-ce-init
        volumeMounts:
        - name: hostroot 
          mountPath: /host
        securityContext:
          privileged: true
      volumes:
      - name: hostroot
        hostPath:
          path: /
```

This runs on every node with **privileged access** to prepare the host (kernel modules, network config, etc.).

---

## Step 3: vp-manager Contacts F5 SaaS

### The VP Manager StatefulSet

```yaml
apiVersion: apps/v1
kind: StatefulSet 
metadata:
  name: vp-manager
  namespace: ves-system
spec:
  replicas: 1
  selector:
    matchLabels:
      name: vpm
  serviceName: "vp-manager"
  template:
    metadata:
      labels:
        name: vpm
        statefulset: vp-manager
    spec:
      serviceAccountName: vpm-sa
      # ... init containers and main container ...
      containers:
      - name: vp-manager 
        image: gcr.io/volterraio/vpm
        imagePullPolicy: Always
        # ...
```

### What VP Manager Does

1. **Reads ConfigMap** - Gets the token and cluster configuration
2. **Contacts Maurice** - F5's registration service at:
   - `https://register.ves.volterra.io` (public endpoint)
   - `https://register-tls.ves.volterra.io` (private endpoint)
3. **Sends registration request** with:
   - Site Token
   - ClusterName (`ericji-gpu-ai-pod`)
   - ClusterType (`ce` = Customer Edge)
   - Latitude/Longitude
   - CertifiedHardware type

4. **Site appears as PENDING** in F5XC Console

---

## Step 4: Admin Approves in F5XC Console

### Manual Approval Required

In the F5XC Console:
1. Navigate to **Multi-Cloud Network Connect → Site Management → Registrations**
2. Find the pending site (e.g., `ericji-gpu-ai-pod`)
3. Click **Approve**

### Why Manual Approval?

Security measure to prevent:
- Rogue clusters from joining your tenant
- Leaked tokens from being exploited
- Unauthorized resource consumption

---

## Step 5: F5 SaaS Instructs vp-manager to Create Pods

### What Gets Created After Approval

| Pod | Containers | Purpose |
|-----|------------|---------|
| **etcd-0** | 2 | Distributed key-value store for F5 XC state |
| **prometheus-xxx** | 5 | Metrics collection and monitoring |
| **ver-0** | 17 | **Volterra Edge Router** - the actual data plane that handles traffic |
| **vp-manager-0** | 1 | Continues to manage the site lifecycle |
| **volterra-ce-init-xxx** | 1 | DaemonSet for host initialization |

### Final Running Status

```bash
oc get pod -n ves-system -o wide

NAME                          READY   STATUS    RESTARTS   AGE   IP             NODE
etcd-0                        2/2     Running   0          45m   10.128.1.214   api.gpu-ai.bd.f5.com
prometheus-57df68c9dd-qnbtn   5/5     Running   0          72s   10.128.1.237   api.gpu-ai.bd.f5.com
ver-0                         17/17   Running   0          45m   10.128.1.216   api.gpu-ai.bd.f5.com
volterra-ce-init-jm8tb        1/1     Running   0          48m   192.170.3.130  api.gpu-ai.bd.f5.com
vp-manager-0                  1/1     Running   3          47m   10.128.1.212   api.gpu-ai.bd.f5.com
```

### The VER Pod (17 containers!)

The `ver-0` pod is the **data plane** with 17 containers handling:
- Traffic proxying
- TLS termination
- WAF/Bot detection
- Rate limiting
- API validation
- Service mesh connectivity

---

## Prerequisites

Before deploying, the cluster needs:

1. **HugePages enabled** - Required for F5 XC performance
2. **Dynamic PVC provisioner** - For persistent storage (etcd, vpm data)
3. **Sufficient resources** - 4 vCPUs, 8GB RAM per node minimum

---

## Summary Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          F5 XC REGISTRATION FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

  F5XC Console                    Your OpenShift Cluster
  ────────────                    ──────────────────────
       │
  1. Generate Token ────────────────────────────────┐
       │                                            │
       │                                            ▼
       │                              2. oc create -f ce_ocp_gpu-ai.yml
       │                                            │
       │                                            ▼
       │                              ┌─────────────────────────┐
       │                              │  vp-manager-0 starts    │
       │                              │  volterra-ce-init runs  │
       │                              └───────────┬─────────────┘
       │                                          │
       │ ◄────── 3. Registration request ─────────┘
       │         (token + cluster info)
       │
       ▼
  Site shows PENDING
       │
  4. Admin clicks APPROVE
       │
       │ ─────── Approval signal ─────────────────►│
       │                                            ▼
       │                              ┌─────────────────────────┐
       │                              │  5. vp-manager creates: │
       │                              │     - etcd-0            │
       │                              │     - prometheus        │
       │                              │     - ver-0 (17 cont.)  │
       │                              └─────────────────────────┘
       │
  Site shows ONLINE ◄──────────────────────────────┘
```

---

## Related Files

- `deploy/ce_ocp_gpu-ai.yml` - The deployment manifest
- `docs/f5_xc_deployment.md` - Full deployment documentation
- `deploy/hugepages-tuned-boottime.yaml` - HugePages configuration
- `deploy/hugepages-mcp.yaml` - MachineConfigPool for HugePages

