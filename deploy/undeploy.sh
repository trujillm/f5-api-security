#!/bin/bash

set -e

# Function to display usage information
usage() {
    echo "F5 AI Security Undeploy Script"
    echo "=============================================="
    echo ""
    echo "USAGE:"
    echo "  $0 [namespace]"
    echo "  $0 --help | -h"
    echo ""
    echo "PARAMETERS:"
    echo "  namespace    OpenShift namespace to undeploy from (optional)"
    echo "               Default: f5-ai-security"
    echo "  --help, -h   Show this help message and exit"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                    # Undeploy from default namespace (f5-ai-security)"
    echo "  $0 my-namespace       # Undeploy from custom namespace"
    echo "  $0 production-f5      # Undeploy from production namespace"
    echo ""
    echo "WHAT THIS SCRIPT REMOVES:"
    echo "  - Helm release 'f5-ai-security'"
    echo "  - All pods, services, routes, and PVCs"
    echo "  - ConfigMaps and secrets"
    echo "  - The entire OpenShift namespace/project"
    echo ""
    echo "WARNING:"
    echo "  This operation is IRREVERSIBLE!"
    echo "  All data in the namespace will be permanently deleted."
    echo ""
}

# Check for help option first
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    usage
    exit 0
fi

# Parse command line arguments, default namespace to f5-ai-security if not provided.
NAMESPACE="${1:-f5-ai-security}"

# Display undeploy info
echo "F5 AI Security Undeploy"
echo "======================="
echo "Target namespace: ${NAMESPACE}"
echo ""

# Function to check if a command exists
check_command() {
    local cmd=$1
    local description=$2
    
    if command -v "$cmd" &> /dev/null; then
        echo "$description - $(which $cmd)"
        return 0
    else
        echo "$description not found"
        return 1
    fi
}

# Function to check OpenShift login status
check_openshift_login() {
    if oc whoami &> /dev/null; then
        local user=$(oc whoami)
        local server=$(oc whoami --show-server 2>/dev/null || echo "unknown")
        echo "OpenShift Login - User: $user"
        echo "Server: $server"
        return 0
    else
        echo "Not logged into OpenShift"
        echo "Login with: oc login --server=<your-cluster> --token=<your-token>"
        return 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    echo ""
    echo "Checking Prerequisites..."
    echo "----------------------------------------"

    local PREREQS_OK=true

    # Check required CLI tools
    check_command "oc" "OpenShift CLI (oc)" || PREREQS_OK=false
    check_command "helm" "Helm CLI" || PREREQS_OK=false

    # Check OpenShift login
    check_openshift_login || PREREQS_OK=false

    if [ "$PREREQS_OK" = false ]; then
        echo ""
        echo "Prerequisites check failed!"
        echo "Please install missing tools and login to OpenShift before running this script."
        exit 1
    fi

    echo "Proceeding with undeploy..."
}


# Run prerequisites check
check_prerequisites

# Check if namespace exists
if ! oc get namespace "${NAMESPACE}" &> /dev/null; then
    echo ""
    echo "Namespace '${NAMESPACE}' does not exist."
    echo "Nothing to undeploy."
    exit 0
fi


echo ""
echo "Starting undeploy process..."
echo "=========================================="

# Uninstall Helm release
echo ""
echo "Uninstalling Helm release 'f5-ai-security'..."
if helm list -n "${NAMESPACE}" | grep -q "f5-ai-security"; then
    helm uninstall f5-ai-security -n "${NAMESPACE}"
    echo "Helm release uninstalled successfully."
else
    echo "Helm release 'f5-ai-security' not found in namespace '${NAMESPACE}'."
fi

# Wait for resources to be cleaned up
echo ""
echo "Waiting for resources to be cleaned up..."
echo "This may take a few moments..."

# Wait for pods to terminate
timeout=60
counter=0
while [ $counter -lt $timeout ]; do
    pod_count=$(oc get pods -n "${NAMESPACE}" --no-headers 2>/dev/null | wc -l)
    if [ "$pod_count" -eq 0 ]; then
        echo "All pods have been terminated."
        break
    fi
    echo "Waiting for ${pod_count} pod(s) to terminate..."
    sleep 5
    counter=$((counter + 5))
done

if [ $counter -ge $timeout ]; then
    echo "Warning: Some pods may still be terminating. Proceeding with namespace deletion."
fi

# Force delete any remaining resources (if needed)
echo ""
echo "Checking for any remaining resources..."
remaining_resources=$(oc get all -n "${NAMESPACE}" --no-headers 2>/dev/null | wc -l)
if [ "$remaining_resources" -gt 0 ]; then
    echo "Found ${remaining_resources} remaining resource(s). Force deleting..."
    oc delete all --all -n "${NAMESPACE}" --force --grace-period=0 2>/dev/null || true
    
    # Also delete PVCs, ConfigMaps, Secrets
    oc delete pvc --all -n "${NAMESPACE}" --force --grace-period=0 2>/dev/null || true
    oc delete configmap --all -n "${NAMESPACE}" --force --grace-period=0 2>/dev/null || true
    oc delete secret --all -n "${NAMESPACE}" --force --grace-period=0 2>/dev/null || true
else
    echo "No remaining resources found."
fi

# Delete the namespace
echo ""
echo "Deleting namespace '${NAMESPACE}'..."
oc delete namespace "${NAMESPACE}" --wait=false

# Wait for namespace to be fully deleted
echo ""
echo "Waiting for namespace to be fully deleted..."
timeout=120
counter=0
while [ $counter -lt $timeout ]; do
    if ! oc get namespace "${NAMESPACE}" &> /dev/null; then
        echo "Namespace '${NAMESPACE}' has been fully deleted."
        break
    fi
    echo "Waiting for namespace deletion to complete..."
    sleep 5
    counter=$((counter + 5))
done

if [ $counter -ge $timeout ]; then
    echo "Warning: Namespace deletion is taking longer than expected."
    echo "The namespace may still be in 'Terminating' state."
    echo "You can check the status with: oc get namespace ${NAMESPACE}"
fi

echo ""
echo "=========================================="
echo "Undeploy Complete!"

