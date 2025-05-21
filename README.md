# MLOps
This is the first phase of mlops project with totally built on open-source <br />
For full version, please check it out on my Gitlab: https://gitlab.com/mlops-oss/mlops-pipeline#

# Kubernetes and Kubeflow MLOps Platform Setup Guide

## Setting Up Kubernetes with Kind (K8s in Docker)

### Install Kind

```bash
[ $(uname -m) = x86_64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.27.0/kind-linux-amd64
sudo mv ./kind /usr/local/bin/kind
chmod +x /usr/local/bin/kind
```

### Create Kind Cluster Configuration

Create a `kind-cluster.yaml` file:

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  image: kindest/node:v1.32.2@sha256:f226345927d7e348497136874b6d207e0b32cc52154ad8323129352923a3142f
  kubeadmConfigPatches:
  - |
    kind: ClusterConfiguration
    apiServer:
      extraArgs:
        "service-account-issuer": "https://kubernetes.default.svc"
        "service-account-signing-key-file": "/etc/kubernetes/pki/sa.key"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
- role: worker
  image: kindest/node:v1.32.2@sha256:f226345927d7e348497136874b6d207e0b32cc52154ad8323129352923a3142f
  extraMounts:
  - hostPath: ./shared-storage
    containerPath: /var/local-path-provisioner
- role: worker
  image: kindest/node:v1.32.2@sha256:f226345927d7e348497136874b6d207e0b32cc52154ad8323129352923a3142f
  extraMounts:
  - hostPath: ./shared-storage
    containerPath: /var/local-path-provisioner
```

### Create Cluster and Configure Kubectl

```bash
kind create cluster -n mlops-kind --config kind-cluster.yaml 
kind get kubeconfig --name mlops-kind > /tmp/kubeflow-config
kind get kubeconfig --name mlops-kind > /home/ec2-user/kubeconfig-mlops.yaml
export KUBECONFIG=/tmp/kubeflow-config
```

### Update Bash Profile for Persistence

Add to `~/.bashrc`:

```bash
if [ ! -f ~/kubeconfig-mlops.yaml ]; then
    echo "Get kind kubectl config"
    kind get kubeconfig --name mlops-kind > $HOME/kubeconfig-mlops.yaml
fi

KUBECONFIG=$HOME/kubeconfig-mlops.yaml
export KUBECONFIG
source <(kubectl completion bash)
```

### Setup Kubectl Autocompletion

```bash
echo 'source <(kubectl completion bash)' >> ~/.bashrc
echo 'alias k=kubectl' >> ~/.bashrc
echo 'complete -F __start_kubectl k' >> ~/.bashrc
source ~/.bashrc
```

---

## Installing and Configuring Kubeflow

### 1. Get Manifests Files

```bash
git clone https://github.com/kubeflow/manifests.git
# Use tag 1.9.1
```

### 2. Install Tools 
#### Install Helm (if needed)

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

#### Install Storage Class

```bash
helm repo add rimusz https://charts.rimusz.net
helm install my-hostpath-provisioner rimusz/hostpath-provisioner --version 0.2.13

# Verify installation
kubectl get storageclass
```

#### Install Kustomize

```bash
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
mv kustomize /usr/local/bin/
chmod +x /usr/local/bin/kustomize
kustomize version
```

### 3. CSRF Security Note

If you absolutely need to expose Kubeflow over HTTP, you can disable the `Secure Cookies` feature by setting the `APP_SECURE_COOKIES` environment variable to `false` in every relevant web app. This is not recommended, as it poses security risks.

### 4. Apply Kubeflow Manifests

```bash
cd manifests
while ! kubectl kustomize example | kubectl apply --server-side --force-conflicts -f -; do 
  echo "Retrying to apply resources"; 
  sleep 20; 
done
```

### 5. Troubleshooting: "Too Many Open Files"

```bash
sudo sysctl fs.inotify.max_user_instances=1280
sudo sysctl fs.inotify.max_user_watches=655360
```

### 6. Forward Kubeflow Dashboard

```bash
export ISTIO_NAMESPACE=istio-system
kubectl port-forward svc/istio-ingressgateway -n istio-system 8080:80 --address 0.0.0.0
```

---

## Installing MLflow

### 1. Create Values File

Create `values.yaml`:

```yaml
tracking:
  resourcesPreset: none
  auth:
    enabled: true
    username: mlflow
    password: mlflow
  service:
    type: ClusterIP
    ports:
      http: 5000

run:
  resourcesPreset: none

volumePermission:
  resourcesPreset: none

minio:
  resourcesPreset: none

postgresql:
  enabled: true
  auth:
    username: bn_mlflow
    password: bn_mlflow
    database: bitnami_mlflow
  architecture: standalone
```

### 2. Install with Helm

```bash
cd /engn001/mlflow
helm repo add bitnami https://charts.bitnami.com/bitnami 
helm upgrade --install mlflow bitnami/mlflow --version 2.5.5 -n mlflow --create-namespace -f values.yaml
```

### 3. Expose MLflow Interface

```bash
kubectl port-forward -n mlflow svc/mlflow-tracking 5000:5000 --address 0.0.0.0
```

---

## Installing MinIO (External Storage Simulation)

### 1. Create Values File

Create `values.yaml`:

```yaml
resourcesPreset: none
volumePermission:
  resourcesPreset: none
provisioning:
  resourcesPreset: none
auth:
  rootUser: minioadmin
  rootPassword: minioadmin
```

### 2. Install with Helm

```bash
cd /engn001/minio
helm repo add bitnami https://charts.bitnami.com/bitnami 
helm upgrade --install minio bitnami/minio --version 15.0.7 -n minio --create-namespace -f values.yaml 
```

### 3. Expose MinIO UI

```bash
kubectl port-forward -n minio svc/minio 9001:9001 --address 0.0.0.0
```

---

## Installing Gitea for Source Control

### 1. Install Using Helm

```bash
cd /engn001/gitea
helm repo add gitea-charts https://dl.gitea.io/charts/
helm upgrade --install gitea gitea-charts/gitea -f gitea-values.yaml -n gitea --create-namespace
```

### 2. Expose Gitea Service

```bash
kubectl port-forward svc/gitea-http -n gitea 3000:3000 --address 0.0.0.0
```

---

## Installing ArgoCD

### 1. Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### 2. Expose ArgoCD Service

```bash
kubectl port-forward svc/argocd-server -n argocd 8088:80 --address 0.0.0.0
```

### 3. App of Apps Pattern

Reference: https://argo-cd.readthedocs.io/en/latest/operator-manual/cluster-bootstrapping/

---

## Development Environment Preparation

### 1. Install Python and Dependencies

```bash
# Install pip if needed
python3 -m ensurepip --default-pip
python3 -m pip install --upgrade pip

# Install ipykernel for Jupyter notebooks
python3 -m pip install ipykernel -U --user --force-reinstall

# Install required Python packages
pip install -r requirements.txt
```

---

## KServe Inference Service Usage Guide

### Interacting with KServe

#### With JWT Token (if authentication enabled)

```bash
# Generate token
TOKEN=$(kubectl create token default-editor -n kubeflow-user-example-com --audience=istio-ingressgateway.istio-system.svc.cluster.local --duration=24h)

# Make prediction request
curl -v -H "Host: sklearn-iris.kubeflow-user-example-com.svc.cluster.local" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @./iris-input.json \
  http://localhost:8080/v1/models/sklearn-iris:predict
```

#### Local Access Options

```bash
# V1 API
curl -v -H "Content-Type: application/json" \
  -d @./data/test_schema.json \
  "http://bike-model-1-predictor-00001-private.kubeflow-user-example-com.svc.cluster.local/v1/models/model.joblib:predict"

# V2 API
curl -v -H "Content-Type: application/json" \
  -d @./data/test_schema_short.json \
  "http://mlflow-v2-bsd-predictor-00001-private.kubeflow-user-example-com.svc.cluster.local/v2/models/mlflow-v2-bsd/infer"
```
> **Note**: Default KServe model name should be `model.joblib`
---

## Useful Kubernetes Commands

### KServe Resource Management

```bash
# Delete inference service
kubectl delete inferenceservice.serving.kserve.io/sklearn-iris -n kubeflow-user-example-com

# List virtual services
kubectl get virtualservice -n kubeflow-user-example-com

# List inference services
kubectl get InferenceService -n kubeflow-user-example-com
```

### Pipeline Resource Management

```bash
# Delete completed pipeline pods
kubectl get pods -n kubeflow-user-example-com --no-headers | grep '^bike-sharing-pipeline-' | awk '{print $1}' | xargs kubectl delete pod -n kubeflow-user-example-com

# Delete resources using Kustomize
kubectl delete -k example
```

### Creating Secrets and Service Accounts

```bash
# Create MinIO credentials secret
kubectl create secret generic aws-credentials -n kubeflow-user-example-com \
  --from-literal=AWS_ACCESS_KEY_ID= \
  --from-literal=AWS_SECRET_ACCESS_KEY= \
  --from-literal=AWS_REGION=

# Create service account for KServe S3 access
kubectl create serviceaccount kserve-s3-sa -n kubeflow-user-example-com --dry-run=client -o yaml | kubectl apply -f -
kubectl patch serviceaccount kserve-s3-sa -n kubeflow-user-example-com -p '{"secrets": [{"name": "s3-credentials"}]}'
```

---

## Kubeflow Model Registry (Optional)

### 1. Install Model Registry

```bash
git clone --depth 1 -b v0.2.15 https://github.com/kubeflow/model-registry.git
cd model-registry/manifests/kustomize

# Set profile name
PROFILE_NAME=kubeflow-user-example-com

# Update namespaces in kustomize files
for DIR in options/istio overlays/db ; do 
  (cd $DIR; kustomize edit set namespace $PROFILE_NAME); 
done
```

### 2. Apply Manifests

```bash
kubectl apply -k overlays/db
kubectl apply -k options/istio
kubectl apply -k options/ui/overlays/istio
```

### 3. Configure Model Registry Link in Kubeflow Dashboard

```bash
kubectl get configmap centraldashboard-config -n kubeflow -o json | \
  jq '.data.links |= (fromjson | .menuLinks += [{"icon": "assignment", "link": "/model-registry/", "text": "Model Registry", "type": "item"}] | tojson)' | \
  kubectl apply -f - -n kubeflow
```

---

## PodDefault Configuration

Reference: https://github.com/kubeflow/kubeflow/blob/master/components/admission-webhook/README.md

### Apply PodDefault Outside Kubeflow Namespace

1. Create namespace with required label:

```bash
kubectl create ns gitops
kubectl label ns gitops app.kubernetes.io/part-of=kubeflow-profile --overwrite
```

2. Apply PodDefault to pods using labels:

```bash
# If PodDefault has selector.matchLabels: access-ml-pipeline="true"
kubectl run nginx --image=nginx -n gitops -l access-ml-pipeline="true"
```

### ML Pipeline Authentication Strategy

For pods that need to access ML Pipeline API:

1. Create PodDefault manifest to:
   - Mount a token as volume
   - Declare environment variable `KF_PIPELINES_SA_TOKEN_PATH` with token path

> **Note**: The kfp.Client() automatically reads the KF_PIPELINES_SA_TOKEN_PATH environment variable and uses the token to authenticate with the ml-pipeline service.

---

## Istio in Kubeflow

### Istio's Role in Kubeflow

Istio is a service mesh that Kubeflow uses to manage and secure communication between components.

#### Traffic Management
- Uses `VirtualService` and `DestinationRule` to route requests
- Provides load balancing, retries, and timeouts

#### Security
- Authentication: Enforces identity verification (JWT tokens)
- Authorization: Restricts access with `AuthorizationPolicy` and `RequestAuthentication`

#### Observability
- Provides metrics, logs, and traces for monitoring

#### Ingress Gateway
- Acts as entry point for external traffic
- Handles HTTP/HTTPS requests and routes to internal services

#### Multi-Tenancy
- Isolates traffic between namespaces or user profiles

---

## Additional Notes

### Security: Service Account Permissions

To allow a pod to interact with Kubeflow Pipelines:
1. Create Service Account (if needed)
2. Create ClusterRoleBinding with ClusterRole: `kubeflow-pipelines-edit`

View available ClusterRoles:
```bash
kubectl get clusterrole -n kubeflow
```

### Kubernetes Tokens

- ServiceAccount tokens in Kubernetes are JWTs
- Structure: Header, Payload, Signature
- Key payload fields:
  - `iss` (issuer): Kubernetes API server
  - `sub` (subject): ServiceAccount identity
  - `aud` (audience): Intended service

Example command:
```bash
kubectl create token default-editor -n kubeflow-user-example-com --audience=istio-ingressgateway.istio-system.svc.cluster.local --duration=24h
```

### Kubeflow-Specific Information

- Kubeflow audience format: `<component>.kubeflow.org` (e.g., `pipeline.kubeflow.org`)
- Kubeflow secret path: `/var/run/secrets/kubeflow/<component>` (e.g., `/var/run/secrets/kubeflow/pipeline`)

### External Cluster Access

For connecting to Kubeflow from outside the cluster, refer to:
https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/connect-api/#kubeflow-platform---outside-the-cluster
